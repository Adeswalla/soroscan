"""
Tests for contract state snapshots and state-diff tracking.
"""
import json
from datetime import datetime, timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from ..models import TrackedContract, ContractSnapshot, StateChange
from ..tasks import snapshot_contract_state, _compute_state_diff

User = get_user_model()


class ContractSnapshotModelTests(TestCase):
    """Test ContractSnapshot and StateChange models."""

    def setUp(self):
        """Create test user and contract."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.contract = TrackedContract.objects.create(
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4",
            name="Test Contract",
            owner=self.user,
            is_active=True,
            last_indexed_ledger=1000,
        )

    def test_create_contract_snapshot(self):
        """Test creating a contract snapshot."""
        state_data = {
            "total_supply": "1000000",
            "paused": False,
            "admin": "GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWHF",
        }

        snapshot = ContractSnapshot.objects.create(
            contract=self.contract,
            ledger_sequence=1000,
            state_data=state_data,
        )

        self.assertEqual(snapshot.contract, self.contract)
        self.assertEqual(snapshot.ledger_sequence, 1000)
        self.assertEqual(snapshot.state_data, state_data)
        self.assertIsNotNone(snapshot.captured_at)

    def test_unique_contract_ledger_constraint(self):
        """Test that contract + ledger_sequence is unique."""
        state_data = {"total_supply": "1000000"}

        ContractSnapshot.objects.create(
            contract=self.contract,
            ledger_sequence=1000,
            state_data=state_data,
        )

        # Attempting to create another snapshot at the same ledger should fail
        with self.assertRaises(Exception):
            ContractSnapshot.objects.create(
                contract=self.contract,
                ledger_sequence=1000,
                state_data=state_data,
            )

    def test_state_change_tracking(self):
        """Test tracking state changes between snapshots."""
        old_state = {
            "total_supply": "1000000",
            "paused": False,
        }
        new_state = {
            "total_supply": "2000000",
            "paused": True,
        }

        old_snapshot = ContractSnapshot.objects.create(
            contract=self.contract,
            ledger_sequence=1000,
            state_data=old_state,
        )

        new_snapshot = ContractSnapshot.objects.create(
            contract=self.contract,
            ledger_sequence=2000,
            state_data=new_state,
        )

        # Create state changes
        StateChange.objects.create(
            snapshot=new_snapshot,
            previous_snapshot=old_snapshot,
            field_name="total_supply",
            old_value="1000000",
            new_value="2000000",
        )
        StateChange.objects.create(
            snapshot=new_snapshot,
            previous_snapshot=old_snapshot,
            field_name="paused",
            old_value=False,
            new_value=True,
        )

        # Verify changes were recorded
        changes = StateChange.objects.filter(snapshot=new_snapshot)
        self.assertEqual(changes.count(), 2)

        change_dict = {c.field_name: c for c in changes}
        self.assertEqual(change_dict["total_supply"].old_value, "1000000")
        self.assertEqual(change_dict["total_supply"].new_value, "2000000")
        self.assertEqual(change_dict["paused"].old_value, False)
        self.assertEqual(change_dict["paused"].new_value, True)

    def test_snapshot_ordering(self):
        """Test that snapshots are ordered by ledger_sequence descending."""
        ContractSnapshot.objects.create(
            contract=self.contract,
            ledger_sequence=1000,
            state_data={"value": 1},
        )
        ContractSnapshot.objects.create(
            contract=self.contract,
            ledger_sequence=2000,
            state_data={"value": 2},
        )
        ContractSnapshot.objects.create(
            contract=self.contract,
            ledger_sequence=3000,
            state_data={"value": 3},
        )

        snapshots = list(ContractSnapshot.objects.filter(contract=self.contract))
        self.assertEqual(snapshots[0].ledger_sequence, 3000)
        self.assertEqual(snapshots[1].ledger_sequence, 2000)
        self.assertEqual(snapshots[2].ledger_sequence, 1000)


class StateDiffComputationTests(TestCase):
    """Test state diff computation logic."""

    def test_compute_state_diff_simple(self):
        """Test computing diff for simple field changes."""
        old_state = {"a": 1, "b": 2}
        new_state = {"a": 1, "b": 3}

        changes = _compute_state_diff(old_state, new_state)

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["field_name"], "b")
        self.assertEqual(changes[0]["old_value"], 2)
        self.assertEqual(changes[0]["new_value"], 3)

    def test_compute_state_diff_added_field(self):
        """Test detecting newly added fields."""
        old_state = {"a": 1}
        new_state = {"a": 1, "b": 2}

        changes = _compute_state_diff(old_state, new_state)

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["field_name"], "b")
        self.assertIsNone(changes[0]["old_value"])
        self.assertEqual(changes[0]["new_value"], 2)

    def test_compute_state_diff_removed_field(self):
        """Test detecting removed fields."""
        old_state = {"a": 1, "b": 2}
        new_state = {"a": 1}

        changes = _compute_state_diff(old_state, new_state)

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["field_name"], "b")
        self.assertEqual(changes[0]["old_value"], 2)
        self.assertIsNone(changes[0]["new_value"])

    def test_compute_state_diff_no_changes(self):
        """Test when state hasn't changed."""
        state = {"a": 1, "b": 2}

        changes = _compute_state_diff(state, state)

        self.assertEqual(len(changes), 0)

    def test_compute_state_diff_complex_values(self):
        """Test diff with complex nested values."""
        old_state = {
            "balances": {"user1": "100", "user2": "200"},
            "metadata": {"version": 1},
        }
        new_state = {
            "balances": {"user1": "150", "user2": "200"},
            "metadata": {"version": 2},
        }

        changes = _compute_state_diff(old_state, new_state)

        self.assertEqual(len(changes), 2)
        change_dict = {c["field_name"]: c for c in changes}
        self.assertIn("balances", change_dict)
        self.assertIn("metadata", change_dict)


class SnapshotTaskTests(TestCase):
    """Test the snapshot_contract_state Celery task."""

    def setUp(self):
        """Create test user and contract."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.contract = TrackedContract.objects.create(
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4",
            name="Test Contract",
            owner=self.user,
            is_active=True,
            last_indexed_ledger=1000,
        )

    def test_snapshot_task_skips_non_interval_ledgers(self):
        """Test that task skips contracts not at interval boundaries."""
        # Set last_indexed_ledger to a non-interval value
        self.contract.last_indexed_ledger = 1001
        self.contract.save()

        result = snapshot_contract_state(snapshot_interval=1000)

        # Should not create any snapshots
        self.assertEqual(result["snapshot_count"], 0)
        self.assertEqual(ContractSnapshot.objects.count(), 0)

    def test_snapshot_task_skips_inactive_contracts(self):
        """Test that task skips inactive contracts."""
        self.contract.is_active = False
        self.contract.save()

        result = snapshot_contract_state(snapshot_interval=1000)

        # Should not create any snapshots
        self.assertEqual(result["snapshot_count"], 0)

    def test_snapshot_task_skips_existing_snapshots(self):
        """Test that task doesn't create duplicate snapshots."""
        # Create an existing snapshot
        ContractSnapshot.objects.create(
            contract=self.contract,
            ledger_sequence=1000,
            state_data={"value": 1},
        )

        # Mock the client to return state
        from unittest.mock import patch

        with patch("soroscan.ingest.tasks.SorobanClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.get_contract_state.return_value = {"value": 2}

            result = snapshot_contract_state(snapshot_interval=1000)

        # Should not create a new snapshot
        self.assertEqual(result["snapshot_count"], 0)
        self.assertEqual(ContractSnapshot.objects.count(), 1)

    def test_snapshot_task_creates_state_changes(self):
        """Test that task creates StateChange records for diffs."""
        # Create an old snapshot
        old_snapshot = ContractSnapshot.objects.create(
            contract=self.contract,
            ledger_sequence=0,
            state_data={"total_supply": "1000000", "paused": False},
        )

        # Update contract to next interval
        self.contract.last_indexed_ledger = 1000
        self.contract.save()

        # Mock the client to return new state
        from unittest.mock import patch

        new_state = {"total_supply": "2000000", "paused": True}

        with patch("soroscan.ingest.tasks.SorobanClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.get_contract_state.return_value = new_state

            result = snapshot_contract_state(snapshot_interval=1000)

        # Should create a new snapshot and state changes
        self.assertEqual(result["snapshot_count"], 1)
        self.assertEqual(ContractSnapshot.objects.count(), 2)

        new_snapshot = ContractSnapshot.objects.get(ledger_sequence=1000)
        changes = StateChange.objects.filter(snapshot=new_snapshot)

        # Should have 2 changes
        self.assertEqual(changes.count(), 2)

        change_dict = {c.field_name: c for c in changes}
        self.assertIn("total_supply", change_dict)
        self.assertIn("paused", change_dict)
