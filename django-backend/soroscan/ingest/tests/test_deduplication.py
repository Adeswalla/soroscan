"""
Integration tests for event deduplication system.
"""
import json
import os
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch

import pytest
from django.test import TestCase, override_settings
from django.utils import timezone

from ..models import ContractEvent, EventDeduplicationLog, TrackedContract
from ..tasks import _upsert_contract_event, _get_dedup_strategy, _handle_duplicate_event


@pytest.mark.django_db
class TestEventDeduplication(TestCase):
    """Test event deduplication logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.contract = TrackedContract.objects.create(
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            name="Test Contract",
            is_active=True,
        )

    def _create_event_dict(self, ledger=100, event_index=0, payload=None):
        """Helper to create an event dictionary."""
        if payload is None:
            payload = {"amount": 1000, "recipient": "user1"}
        return {
            "ledger": ledger,
            "ledger_sequence": ledger,
            "event_index": event_index,
            "type": "transfer",
            "event_type": "transfer",
            "tx_hash": "abc123",
            "transaction_hash": "abc123",
            "value": payload,
            "payload": payload,
            "timestamp": timezone.now(),
            "xdr": "xdr_data",
        }

    def test_first_event_creation(self):
        """Test that first event is created successfully."""
        event_dict = self._create_event_dict()
        obj, created = _upsert_contract_event(self.contract, event_dict)

        assert created is True
        assert obj.contract == self.contract
        assert obj.ledger == 100
        assert obj.event_index == 0
        assert obj.payload == {"amount": 1000, "recipient": "user1"}
        assert ContractEvent.objects.count() == 1

    def test_exact_duplicate_skipped(self):
        """Test that exact duplicate is skipped with log entry."""
        event_dict = self._create_event_dict()
        payload = event_dict["payload"].copy()

        # Create first event
        obj1, created1 = _upsert_contract_event(self.contract, event_dict)
        assert created1 is True

        # Ingest same event again
        obj2, created2 = _upsert_contract_event(self.contract, event_dict)
        assert created2 is False
        assert obj2.id == obj1.id

        # Check dedup log
        logs = EventDeduplicationLog.objects.all()
        assert logs.count() == 1
        assert logs[0].resolution == EventDeduplicationLog.Resolution.SKIPPED
        assert logs[0].duplicate_payload == payload

    @override_settings(DEDUP_STRATEGY="last-write-wins")
    def test_conflicting_payload_last_write_wins(self):
        """Test last-write-wins strategy for conflicting payloads."""
        with patch.dict(os.environ, {"DEDUP_STRATEGY": "last-write-wins"}):
            event_dict1 = self._create_event_dict(
                payload={"amount": 1000, "recipient": "user1"}
            )
            event_dict2 = self._create_event_dict(
                payload={"amount": 2000, "recipient": "user2"}
            )

            # Create first event
            obj1, created1 = _upsert_contract_event(self.contract, event_dict1)
            assert created1 is True
            assert obj1.payload == {"amount": 1000, "recipient": "user1"}

            # Ingest conflicting event
            obj2, created2 = _upsert_contract_event(self.contract, event_dict2)
            assert created2 is False
            assert obj2.id == obj1.id

            # Verify payload was replaced
            obj1.refresh_from_db()
            assert obj1.payload == {"amount": 2000, "recipient": "user2"}

            # Check dedup log
            logs = EventDeduplicationLog.objects.all()
            assert logs.count() == 1
            assert logs[0].resolution == EventDeduplicationLog.Resolution.REPLACED
            assert logs[0].duplicate_payload == {"amount": 2000, "recipient": "user2"}

    @override_settings(DEDUP_STRATEGY="first-write-wins")
    def test_conflicting_payload_first_write_wins(self):
        """Test first-write-wins strategy for conflicting payloads."""
        with patch.dict(os.environ, {"DEDUP_STRATEGY": "first-write-wins"}):
            event_dict1 = self._create_event_dict(
                payload={"amount": 1000, "recipient": "user1"}
            )
            event_dict2 = self._create_event_dict(
                payload={"amount": 2000, "recipient": "user2"}
            )

            # Create first event
            obj1, created1 = _upsert_contract_event(self.contract, event_dict1)
            assert created1 is True
            original_payload = obj1.payload.copy()

            # Ingest conflicting event
            obj2, created2 = _upsert_contract_event(self.contract, event_dict2)
            assert created2 is False

            # Verify payload was NOT replaced
            obj1.refresh_from_db()
            assert obj1.payload == original_payload

            # Check dedup log
            logs = EventDeduplicationLog.objects.all()
            assert logs.count() == 1
            assert logs[0].resolution == EventDeduplicationLog.Resolution.SKIPPED

    @override_settings(DEDUP_STRATEGY="merge")
    def test_conflicting_payload_merge(self):
        """Test merge strategy for conflicting payloads."""
        with patch.dict(os.environ, {"DEDUP_STRATEGY": "merge"}):
            event_dict1 = self._create_event_dict(
                payload={"amount": 1000, "recipient": "user1", "status": "pending"}
            )
            event_dict2 = self._create_event_dict(
                payload={"amount": 2000, "status": "completed"}
            )

            # Create first event
            obj1, created1 = _upsert_contract_event(self.contract, event_dict1)
            assert created1 is True

            # Ingest conflicting event
            obj2, created2 = _upsert_contract_event(self.contract, event_dict2)
            assert created2 is False

            # Verify payload was merged (new values override old)
            obj1.refresh_from_db()
            assert obj1.payload == {
                "amount": 2000,
                "recipient": "user1",
                "status": "completed",
            }

            # Check dedup log
            logs = EventDeduplicationLog.objects.all()
            assert logs.count() == 1
            assert logs[0].resolution == EventDeduplicationLog.Resolution.MERGED

    def test_multiple_dedup_rounds(self):
        """Test multiple deduplication rounds."""
        event_dict1 = self._create_event_dict(
            payload={"amount": 1000, "recipient": "user1"}
        )
        event_dict2 = self._create_event_dict(
            payload={"amount": 2000, "recipient": "user2"}
        )
        event_dict3 = self._create_event_dict(
            payload={"amount": 3000, "recipient": "user3"}
        )

        with patch.dict(os.environ, {"DEDUP_STRATEGY": "last-write-wins"}):
            # First event
            obj1, created1 = _upsert_contract_event(self.contract, event_dict1)
            assert created1 is True

            # Second duplicate with different payload
            obj2, created2 = _upsert_contract_event(self.contract, event_dict2)
            assert created2 is False
            obj1.refresh_from_db()
            assert obj1.payload["amount"] == 2000

            # Third duplicate with different payload
            obj3, created3 = _upsert_contract_event(self.contract, event_dict3)
            assert created3 is False
            obj1.refresh_from_db()
            assert obj1.payload["amount"] == 3000

            # Verify all dedup logs
            logs = EventDeduplicationLog.objects.all().order_by("created_at")
            assert logs.count() == 2
            assert logs[0].resolution == EventDeduplicationLog.Resolution.REPLACED
            assert logs[1].resolution == EventDeduplicationLog.Resolution.REPLACED

    def test_different_events_not_deduplicated(self):
        """Test that events with different indices are not deduplicated."""
        event_dict1 = self._create_event_dict(event_index=0)
        event_dict2 = self._create_event_dict(event_index=1)

        obj1, created1 = _upsert_contract_event(self.contract, event_dict1)
        obj2, created2 = _upsert_contract_event(self.contract, event_dict2)

        assert created1 is True
        assert created2 is True
        assert obj1.id != obj2.id
        assert ContractEvent.objects.count() == 2
        assert EventDeduplicationLog.objects.count() == 0

    def test_dedup_log_queryable(self):
        """Test that dedup logs are queryable for audit purposes."""
        event_dict1 = self._create_event_dict(
            payload={"amount": 1000, "recipient": "user1"}
        )
        event_dict2 = self._create_event_dict(
            payload={"amount": 2000, "recipient": "user2"}
        )

        with patch.dict(os.environ, {"DEDUP_STRATEGY": "last-write-wins"}):
            obj1, _ = _upsert_contract_event(self.contract, event_dict1)
            _upsert_contract_event(self.contract, event_dict2)

            # Query by resolution
            replaced_logs = EventDeduplicationLog.objects.filter(
                resolution=EventDeduplicationLog.Resolution.REPLACED
            )
            assert replaced_logs.count() == 1

            # Query by original event
            logs_for_event = EventDeduplicationLog.objects.filter(
                original_event=obj1
            )
            assert logs_for_event.count() == 1

            # Query by date range
            logs_recent = EventDeduplicationLog.objects.filter(
                created_at__gte=timezone.now() - timezone.timedelta(minutes=1)
            )
            assert logs_recent.count() == 1

    def test_get_dedup_strategy_default(self):
        """Test that default dedup strategy is last-write-wins."""
        with patch.dict(os.environ, {}, clear=True):
            strategy = _get_dedup_strategy()
            assert strategy == "last-write-wins"

    def test_get_dedup_strategy_invalid(self):
        """Test that invalid strategy defaults to last-write-wins."""
        with patch.dict(os.environ, {"DEDUP_STRATEGY": "invalid-strategy"}):
            strategy = _get_dedup_strategy()
            assert strategy == "last-write-wins"

    def test_unique_constraint_enforced(self):
        """Test that database-level unique constraint is enforced."""
        from django.db import IntegrityError

        event_dict = self._create_event_dict()
        obj1, _ = _upsert_contract_event(self.contract, event_dict)

        # Try to create duplicate directly (bypassing dedup logic)
        with pytest.raises(IntegrityError):
            ContractEvent.objects.create(
                contract=self.contract,
                ledger=100,
                event_index=0,
                tx_hash="abc123",
                event_type="transfer",
                payload={"amount": 5000},
                timestamp=timezone.now(),
            )
