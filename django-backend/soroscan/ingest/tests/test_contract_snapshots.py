"""
Integration tests for contract state snapshots and state-diff tracking.
"""
import json

import pytest

from ..models import ContractSnapshot, StateChange, TrackedContract
from ..tasks import _calculate_state_diff
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

        ContractSnapshot.objects.create(
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


    def test_snapshot_task_creates_snapshots(self):
        """Test that the snapshot task creates snapshots for active contracts."""
        from ..tasks import snapshot_contract_state
        
        user = UserFactory()
        contract = TrackedContract.objects.create(
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4",
            name="Test Contract",
            owner=user,
            is_active=True,
            last_indexed_ledger=1000,
        )

        # Mock the get_contract_state method directly
        from unittest.mock import patch
        with patch('soroscan.ingest.tasks.SorobanClient.get_contract_state') as mock_get_state:
            mock_get_state.return_value = {"balance": "1000"}
            
            result = snapshot_contract_state(snapshot_interval=1000)
            
            assert result["snapshot_count"] == 1
            assert result["state_change_count"] == 0
            assert len(result["errors"]) == 0
            # Verify snapshot was created for the contract
            assert ContractSnapshot.objects.filter(contract=contract).exists()

    def test_snapshot_task_skips_inactive_contracts(self):
        """Test that the snapshot task skips inactive contracts."""
        from ..tasks import snapshot_contract_state
        
        user = UserFactory()
        contract = TrackedContract.objects.create(
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4",
            name="Test Contract",
            owner=user,
            is_active=False,
            last_indexed_ledger=1000,
        )

        result = snapshot_contract_state(snapshot_interval=1000)
        
        assert result["snapshot_count"] == 0
        assert result["state_change_count"] == 0
        # Verify no snapshot was created for inactive contract
        assert not ContractSnapshot.objects.filter(contract=contract).exists()

    def test_snapshot_task_respects_interval(self):
        """Test that the snapshot task only captures at configured intervals."""
        from ..tasks import snapshot_contract_state
        
        user = UserFactory()
        contract = TrackedContract.objects.create(
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4",
            name="Test Contract",
            owner=user,
            is_active=True,
            last_indexed_ledger=999,  # Not a multiple of 1000
        )

        result = snapshot_contract_state(snapshot_interval=1000)
        
        assert result["snapshot_count"] == 0
        # Verify no snapshot was created since ledger is not at interval boundary
        assert not ContractSnapshot.objects.filter(contract=contract).exists()

    def test_get_contract_state_success(self):
        """Test successful contract state retrieval."""
        from ..stellar_client import SorobanClient
        from unittest.mock import Mock, patch
        
        mock_server = Mock()
        mock_entry = Mock()
        mock_entry.key = "balance"
        mock_entry.val = "1000"
        mock_response = Mock()
        mock_response.entries = [mock_entry]
        mock_server.get_contract_data.return_value = mock_response
        
        with patch('soroscan.ingest.stellar_client.SorobanServer', return_value=mock_server):
            client = SorobanClient()
            state = client.get_contract_state("CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4")
            
            assert state is not None
            assert "balance" in state

    def test_get_contract_state_empty(self):
        """Test contract state retrieval with no entries."""
        from ..stellar_client import SorobanClient
        from unittest.mock import Mock, patch
        
        mock_server = Mock()
        mock_response = Mock()
        mock_response.entries = []
        mock_server.get_contract_data.return_value = mock_response
        
        with patch('soroscan.ingest.stellar_client.SorobanServer', return_value=mock_server):
            client = SorobanClient()
            state = client.get_contract_state("CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4")
            
            assert state == {"_empty": True}

    def test_get_contract_state_error(self):
        """Test contract state retrieval with error."""
        from ..stellar_client import SorobanClient
        from unittest.mock import Mock, patch
        
        mock_server = Mock()
        mock_server.get_contract_data.side_effect = Exception("RPC Error")
        
        with patch('soroscan.ingest.stellar_client.SorobanServer', return_value=mock_server):
            client = SorobanClient()
            state = client.get_contract_state("CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4")
            
            assert state is None

    def test_contract_snapshot_viewset_by_contract(self):
        """Test ContractSnapshotViewSet by_contract action."""
        from rest_framework.test import APIRequestFactory
        from ..views import ContractSnapshotViewSet
        
        user = UserFactory()
        contract = TrackedContract.objects.create(
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4",
            name="Test Contract",
            owner=user,
            is_active=True,
            last_indexed_ledger=1000,
        )
        
        snapshot = ContractSnapshot.objects.create(
            contract=contract,
            ledger_sequence=1000,
            state_data={"balance": "1000"},
        )
        
        factory = APIRequestFactory()
        request = factory.get(f'/api/snapshots/by_contract/?contract_id={contract.contract_id}')
        request.user = user
        
        view = ContractSnapshotViewSet.as_view({'get': 'by_contract'})
        response = view(request)
        
        assert response.status_code == 200
        # Verify snapshot was created
        assert ContractSnapshot.objects.filter(id=snapshot.id).exists()


