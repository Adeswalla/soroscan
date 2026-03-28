from django.db import migrations
from django.utils import timezone
from datetime import timedelta
import secrets


def populate_signing_keys(apps, schema_editor):
    """Create initial signing keys for all existing webhooks."""
    WebhookSubscription = apps.get_model("ingest", "WebhookSubscription")
    WebhookSigningKey = apps.get_model("ingest", "WebhookSigningKey")
    
    for webhook in WebhookSubscription.objects.all():
        # Check if this webhook already has a signing key
        if not WebhookSigningKey.objects.filter(subscription=webhook).exists():
            # Create a new signing key
            new_key = secrets.token_hex(32)
            expires_at = timezone.now() + timedelta(days=7)
            
            WebhookSigningKey.objects.create(
                subscription=webhook,
                key=new_key,
                is_active=True,
                expires_at=expires_at,
            )


def reverse_populate(apps, schema_editor):
    """Reverse migration - delete all signing keys."""
    WebhookSigningKey = apps.get_model("ingest", "WebhookSigningKey")
    WebhookSigningKey.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ingest", "0018_webhooksigningkey"),
    ]

    operations = [
        migrations.RunPython(populate_signing_keys, reverse_populate),
    ]
