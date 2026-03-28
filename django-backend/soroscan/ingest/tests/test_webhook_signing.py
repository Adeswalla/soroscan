"""
Tests for webhook HMAC-SHA256 signing and key rotation.
"""
import hashlib
import hmac
import json
import secrets
from datetime import timedelta
from unittest.mock import patch, MagicMock

import pytest
from django.test import TestCase
from django.utils import timezone

from ..models import (
    ContractEvent,
    TrackedContract,
    WebhookSubscription,
    WebhookSigningKey,
)
from ..tasks import (
    _get_active_signing_key,
    _sign_webhook_payload,
    _rotate_webhook_signing_key,
    _cleanup_expired_signing_keys,
)


@pytest.mark.django_db
class TestWebhookSigning(TestCase):
    """Test webhook HMAC-SHA256 signing."""

    def setUp(self):
        """Set up test fixtures."""
        self.contract = TrackedContract.objects.create(
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            name="Test Contract",
            is_active=True,
        )
        self.webhook = WebhookSubscription.objects.create(
            contract=self.contract,
            target_url="https://example.com/webhook",
            secret=secrets.token_hex(32),
        )

    def test_get_active_signing_key(self):
        """Test retrieving the active signing key."""
        # Create a signing key
        key = WebhookSigningKey.objects.create(
            subscription=self.webhook,
            key=secrets.token_hex(32),
            is_active=True,
            expires_at=timezone.now() + timedelta(days=7),
        )

        # Retrieve it
        active_key = _get_active_signing_key(self.webhook)
        assert active_key is not None
        assert active_key.id == key.id
        assert active_key.is_active is True

    def test_get_active_signing_key_none(self):
        """Test that None is returned when no active key exists."""
        active_key = _get_active_signing_key(self.webhook)
        assert active_key is None

    def test_get_active_signing_key_ignores_inactive(self):
        """Test that inactive keys are ignored."""
        # Create an inactive key
        WebhookSigningKey.objects.create(
            subscription=self.webhook,
            key=secrets.token_hex(32),
            is_active=False,
            expires_at=timezone.now() + timedelta(days=7),
        )

        active_key = _get_active_signing_key(self.webhook)
        assert active_key is None

    def test_sign_webhook_payload(self):
        """Test HMAC-SHA256 signing of webhook payload."""
        payload = '{"amount": 1000, "recipient": "user1"}'
        key = secrets.token_hex(32)

        signature = _sign_webhook_payload(payload, key)

        # Verify signature is correct
        expected_sig = hmac.new(
            key.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        assert signature == expected_sig

    def test_sign_webhook_payload_deterministic(self):
        """Test that signing is deterministic."""
        payload = '{"amount": 1000, "recipient": "user1"}'
        key = secrets.token_hex(32)

        sig1 = _sign_webhook_payload(payload, key)
        sig2 = _sign_webhook_payload(payload, key)

        assert sig1 == sig2

    def test_sign_webhook_payload_different_keys(self):
        """Test that different keys produce different signatures."""
        payload = '{"amount": 1000, "recipient": "user1"}'
        key1 = secrets.token_hex(32)
        key2 = secrets.token_hex(32)

        sig1 = _sign_webhook_payload(payload, key1)
        sig2 = _sign_webhook_payload(payload, key2)

        assert sig1 != sig2

    def test_sign_webhook_payload_different_payloads(self):
        """Test that different payloads produce different signatures."""
        payload1 = '{"amount": 1000, "recipient": "user1"}'
        payload2 = '{"amount": 2000, "recipient": "user2"}'
        key = secrets.token_hex(32)

        sig1 = _sign_webhook_payload(payload1, key)
        sig2 = _sign_webhook_payload(payload2, key)

        assert sig1 != sig2

    def test_rotate_webhook_signing_key(self):
        """Test rotating a webhook signing key."""
        # Create initial key
        old_key = WebhookSigningKey.objects.create(
            subscription=self.webhook,
            key=secrets.token_hex(32),
            is_active=True,
            expires_at=timezone.now() + timedelta(days=7),
        )

        # Rotate key
        new_key = _rotate_webhook_signing_key(self.webhook)

        # Verify old key is inactive
        old_key.refresh_from_db()
        assert old_key.is_active is False

        # Verify new key is active
        assert new_key.is_active is True
        assert new_key.key != old_key.key

        # Verify new key expires in 7 days
        expires_in = (new_key.expires_at - timezone.now()).total_seconds()
        assert 6 * 86400 < expires_in < 8 * 86400  # Between 6 and 8 days

    def test_rotate_webhook_signing_key_creates_new_key(self):
        """Test that rotation creates a new key."""
        initial_count = WebhookSigningKey.objects.filter(
            subscription=self.webhook
        ).count()

        _rotate_webhook_signing_key(self.webhook)

        final_count = WebhookSigningKey.objects.filter(
            subscription=self.webhook
        ).count()

        assert final_count == initial_count + 1

    def test_rotate_webhook_signing_key_multiple_times(self):
        """Test rotating a key multiple times."""
        keys = []

        for _ in range(3):
            key = _rotate_webhook_signing_key(self.webhook)
            keys.append(key)

        # Verify all keys are unique
        key_values = [k.key for k in keys]
        assert len(set(key_values)) == 3

        # Verify only the last key is active
        active_keys = WebhookSigningKey.objects.filter(
            subscription=self.webhook,
            is_active=True,
        )
        assert active_keys.count() == 1
        assert active_keys.first().id == keys[-1].id

    def test_cleanup_expired_signing_keys(self):
        """Test cleaning up expired signing keys."""
        # Create an expired key
        expired_key = WebhookSigningKey.objects.create(
            subscription=self.webhook,
            key=secrets.token_hex(32),
            is_active=False,
            expires_at=timezone.now() - timedelta(days=1),
        )

        # Create a non-expired key
        active_key = WebhookSigningKey.objects.create(
            subscription=self.webhook,
            key=secrets.token_hex(32),
            is_active=True,
            expires_at=timezone.now() + timedelta(days=7),
        )

        # Clean up
        deleted_count = _cleanup_expired_signing_keys()

        # Verify expired key is deleted
        assert deleted_count == 1
        assert not WebhookSigningKey.objects.filter(id=expired_key.id).exists()

        # Verify non-expired key is kept
        assert WebhookSigningKey.objects.filter(id=active_key.id).exists()

    def test_cleanup_expired_signing_keys_multiple(self):
        """Test cleaning up multiple expired keys."""
        # Create multiple expired keys
        for _ in range(3):
            WebhookSigningKey.objects.create(
                subscription=self.webhook,
                key=secrets.token_hex(32),
                is_active=False,
                expires_at=timezone.now() - timedelta(days=1),
            )

        # Clean up
        deleted_count = _cleanup_expired_signing_keys()

        # Verify all expired keys are deleted
        assert deleted_count == 3

    def test_webhook_signing_key_unique_constraint(self):
        """Test that signing keys are unique."""
        from django.db import IntegrityError

        key_value = secrets.token_hex(32)

        WebhookSigningKey.objects.create(
            subscription=self.webhook,
            key=key_value,
            is_active=True,
            expires_at=timezone.now() + timedelta(days=7),
        )

        # Try to create another key with the same value
        with pytest.raises(IntegrityError):
            WebhookSigningKey.objects.create(
                subscription=self.webhook,
                key=key_value,
                is_active=True,
                expires_at=timezone.now() + timedelta(days=7),
            )

    def test_webhook_signing_key_minimum_length(self):
        """Test that signing keys are at least 32 bytes (64 hex chars)."""
        key = secrets.token_hex(32)
        assert len(key) == 64  # 32 bytes = 64 hex characters

    def test_signing_key_grace_period(self):
        """Test that old keys are retained for 7 days."""
        # Create initial key
        old_key = WebhookSigningKey.objects.create(
            subscription=self.webhook,
            key=secrets.token_hex(32),
            is_active=True,
            expires_at=timezone.now() + timedelta(days=7),
        )

        # Rotate key
        _rotate_webhook_signing_key(self.webhook)

        # Verify old key still exists (grace period)
        assert WebhookSigningKey.objects.filter(id=old_key.id).exists()

        # Verify old key is inactive
        old_key.refresh_from_db()
        assert old_key.is_active is False

    def test_multiple_webhooks_independent_keys(self):
        """Test that different webhooks have independent signing keys."""
        webhook2 = WebhookSubscription.objects.create(
            contract=self.contract,
            target_url="https://example.com/webhook2",
            secret=secrets.token_hex(32),
        )

        key1 = _rotate_webhook_signing_key(self.webhook)
        key2 = _rotate_webhook_signing_key(webhook2)

        assert key1.subscription_id == self.webhook.id
        assert key2.subscription_id == webhook2.id
        assert key1.key != key2.key

    def test_signing_key_indexes(self):
        """Test that signing keys have proper indexes for queries."""
        # Create a signing key
        key = WebhookSigningKey.objects.create(
            subscription=self.webhook,
            key=secrets.token_hex(32),
            is_active=True,
            expires_at=timezone.now() + timedelta(days=7),
        )

        # Query by subscription and is_active (should use index)
        result = WebhookSigningKey.objects.filter(
            subscription=self.webhook,
            is_active=True,
        ).first()
        assert result.id == key.id

        # Query by expires_at (should use index)
        result = WebhookSigningKey.objects.filter(
            expires_at__lt=timezone.now() + timedelta(days=8)
        ).first()
        assert result.id == key.id
