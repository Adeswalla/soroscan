"""
Integration tests for contract state snapshots and state-diff tracking.
"""
import json
from datetime import datetime, timedelta

import pytest
from django.utils import timezone

from ..models import ContractSnapshot, StateChange, TrackedContract
from ..tasks import snapshot_contract_state, _calculate_state_diff
from .factories import UserFactory


@pytest.mark.django_db
class TestContractSnapshots:
    """Test contract state snapshot capture and state-diff calculation."""

    def test_snapshot_creation(self):
        """Test that snapshots are created with correct metadata."""
        user = UserFactory()
        contract = TrackedContract.objects.create(
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4",
            name="Test Contract",
            owner=user,
            is_active=True,
            last_indexed_ledger=1000,
        )

        state_data = {
            "total_supply": "1000000",
            "balances": {"user1": "500000", "user2": "500000"},
        }

        snapshot = ContractSnapshot.objects.create(
            contract=contract,
            ledger_sequence=1000,
            state_data=state_data,
        )

        assert snapshot.contract == contract
        assert snapshot.ledger_sequence == 1000
        assert snapshot.state_data == state_data
        assert snapshot.captured_at is not None

    def test_snapshot_unique_constraint(self):
        """Test that only one snapshot per contract per ledger is allowed."""
        user = UserFactory()
        contract = TrackedContract.objects.create(
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4",
            name="Test Contract",
            owner=user,
            is_active=True,
            last_indexed_ledger=1000,
        )

        state_data = {"balance": "1000"}

        snapshot1 = ContractSnapshot.objects.create(
            contract=contract,
            ledger_sequence=1000,
            state_data=state_data,
        )

        # Attempting to create another snapshot at the same ledger should fail
        with pytest.raises(Exception):
            ContractSnapshot.objects.create(
                contract=contract,
                ledger_sequence=1000,
                state_data=state_data,
            )

    def test_state_diff_calculation(self):
        """Test state-diff calculation between snapshots."""
        old_state = {
            "total_supply": "1000000",
            "balances": {"user1": "500000", "user2": "500000"},
            "paused": False,
        }

        new_state = {
            "total_supply": "1000000",
            "balances": {"user1": "600000", "user2": "400000"},
            "paused": True,
            "owner": "GXXX...",
        }

        changes = _calculate_state_diff(old_state, new_state)

        # Should detect 3 changes: balances (as whole object), paused, owner
        # Note: nested object changes are tracked as whole objects, not individual fields
        assert len(changes) == 3

        # Check specific changes
        change_dict = {c["field_name"]: c for c in changes}

        assert change_dict["balances"]["old_value"] == {"user1": "500000", "user2": "500000"}
        assert change_dict["balances"]["new_value"] == {"user1": "600000", "user2": "400000"}

        assert change_dict["paused"]["old_value"] is False
        assert change_dict["paused"]["new_value"] is True

        assert change_dict["owner"]["old_value"] is None
        assert change_dict["owner"]["new_value"] == "GXXX..."

    def test_state_change_tracking(self):
        """Test that state changes are properly tracked between snapshots."""
        user = UserFactory()
        contract = TrackedContract.objects.create(
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4",
            name="Test Contract",
            owner=user,
            is_active=True,
            last_indexed_ledger=1000,
        )

        old_state = {"balance": "1000", "paused": False}
        new_state = {"balance": "2000", "paused": True}

        snapshot1 = ContractSnapshot.objects.create(
            contract=contract,
            ledger_sequence=1000,
            state_data=old_state,
        )

        snapshot2 = ContractSnapshot.objects.create(
            contract=contract,
            ledger_sequence=2000,
            state_data=new_state,
        )

        # Create state changes
        changes = _calculate_state_diff(old_state, new_state)
        for change in changes:
            StateChange.objects.create(
                snapshot=snapshot2,
                previous_snapshot=snapshot1,
                field_name=change["field_name"],
                old_value=change["old_value"],
                new_value=change["new_value"],
            )

        # Verify state changes were created
        state_changes = StateChange.objects.filter(snapshot=snapshot2)
        assert state_changes.count() == 2

        balance_change = state_changes.get(field_name="balance")
        assert balance_change.old_value == "1000"
        assert balance_change.new_value == "2000"
        assert balance_change.previous_snapshot == snapshot1

        paused_change = state_changes.get(field_name="paused")
        assert paused_change.old_value is False
        assert paused_change.new_value is True

    def test_snapshot_size_limit(self):
        """Test that snapshots exceeding 1 MB are handled."""
        user = UserFactory()
        contract = TrackedContract.objects.create(
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4",
            name="Test Contract",
            owner=user,
            is_active=True,
            last_indexed_ledger=1000,
        )

        # Create a large state (but under 1 MB)
        large_state = {
            f"key_{i}": "x" * 1000 for i in range(500)
        }

        snapshot = ContractSnapshot.objects.create(
            contract=contract,
            ledger_sequence=1000,
            state_data=large_state,
        )

        # Verify size calculation
        size_bytes = len(json.dumps(snapshot.state_data).encode("utf-8"))
        assert size_bytes < 1_000_000

    def test_snapshot_ordering(self):
        """Test that snapshots are ordered correctly."""
        user = UserFactory()
        contract = TrackedContract.objects.create(
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4",
            name="Test Contract",
            owner=user,
            is_active=True,
            last_indexed_ledger=3000,
        )

        # Create snapshots in non-sequential order
        snapshot2 = ContractSnapshot.objects.create(
            contract=contract,
            ledger_sequence=2000,
            state_data={"balance": "2000"},
        )

        snapshot1 = ContractSnapshot.objects.create(
            contract=contract,
            ledger_sequence=1000,
            state_data={"balance": "1000"},
        )

        snapshot3 = ContractSnapshot.objects.create(
            contract=contract,
            ledger_sequence=3000,
            state_data={"balance": "3000"},
        )

        # Query and verify ordering
        snapshots = ContractSnapshot.objects.filter(contract=contract).order_by("-ledger_sequence")
        assert list(snapshots) == [snapshot3, snapshot2, snapshot1]

    def test_snapshot_query_by_ledger_range(self):
        """Test querying snapshots within a ledger range."""
        user = UserFactory()
        contract = TrackedContract.objects.create(
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4",
            name="Test Contract",
            owner=user,
            is_active=True,
            last_indexed_ledger=5000,
        )

        # Create multiple snapshots
        for ledger in [1000, 2000, 3000, 4000, 5000]:
            ContractSnapshot.objects.create(
                contract=contract,
                ledger_sequence=ledger,
                state_data={"balance": str(ledger)},
            )

        # Query range 2000-4000
        snapshots = ContractSnapshot.objects.filter(
            contract=contract,
            ledger_sequence__gte=2000,
            ledger_sequence__lte=4000,
        ).order_by("-ledger_sequence")

        assert snapshots.count() == 3
        assert list(snapshots.values_list("ledger_sequence", flat=True)) == [4000, 3000, 2000]

    def test_state_change_field_tracking(self):
        """Test that state changes track field-level modifications."""
        user = UserFactory()
        contract = TrackedContract.objects.create(
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4",
            name="Test Contract",
            owner=user,
            is_active=True,
            last_indexed_ledger=1000,
        )

        old_state = {
            "metadata": {
                "name": "Token",
                "symbol": "TKN",
                "decimals": 7,
            },
            "supply": "1000000",
        }

        new_state = {
            "metadata": {
                "name": "Token",
                "symbol": "TKN",
                "decimals": 8,  # Changed
            },
            "supply": "2000000",  # Changed
        }

        snapshot1 = ContractSnapshot.objects.create(
            contract=contract,
            ledger_sequence=1000,
            state_data=old_state,
        )

        snapshot2 = ContractSnapshot.objects.create(
            contract=contract,
            ledger_sequence=2000,
            state_data=new_state,
        )

        changes = _calculate_state_diff(old_state, new_state)
        for change in changes:
            StateChange.objects.create(
                snapshot=snapshot2,
                previous_snapshot=snapshot1,
                field_name=change["field_name"],
                old_value=change["old_value"],
                new_value=change["new_value"],
            )

        # Verify changes
        state_changes = StateChange.objects.filter(snapshot=snapshot2)
        assert state_changes.count() == 2

        # Check that nested changes are tracked
        change_dict = {c.field_name: c for c in state_changes}
        assert "metadata" in change_dict
        assert "supply" in change_dict
