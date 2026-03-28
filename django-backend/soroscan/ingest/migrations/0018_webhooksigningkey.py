from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ingest", "0017_eventdeduplicationlog"),
    ]

    operations = [
        migrations.CreateModel(
            name="WebhookSigningKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "key",
                    models.CharField(
                        help_text="HMAC signing key (hex-encoded, at least 32 bytes)",
                        max_length=255,
                        unique=True,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        db_index=True,
                        default=True,
                        help_text="Whether this key is currently used for signing",
                    ),
                ),
                (
                    "expires_at",
                    models.DateTimeField(
                        db_index=True,
                        help_text="When this key expires (7 days after rotation)",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="When this key was created",
                    ),
                ),
                (
                    "subscription",
                    models.ForeignKey(
                        help_text="Webhook subscription this key belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="signing_keys",
                        to="ingest.webhooksubscription",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="webhooksigningkey",
            index=models.Index(fields=["subscription", "is_active"], name="ingest_webh_subscri_is_act_idx"),
        ),
        migrations.AddIndex(
            model_name="webhooksigningkey",
            index=models.Index(fields=["subscription", "created_at"], name="ingest_webh_subscri_created_idx"),
        ),
        migrations.AddIndex(
            model_name="webhooksigningkey",
            index=models.Index(fields=["expires_at"], name="ingest_webh_expires_idx"),
        ),
    ]
