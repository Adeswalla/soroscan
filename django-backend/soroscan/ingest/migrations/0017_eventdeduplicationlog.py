from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ingest", "0016_eventaggregation"),
    ]

    operations = [
        migrations.CreateModel(
            name="EventDeduplicationLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("duplicate_payload", models.JSONField(help_text="The payload of the duplicate event")),
                (
                    "resolution",
                    models.CharField(
                        choices=[
                            ("skipped", "Skipped (identical payload)"),
                            ("replaced", "Replaced (conflicting payload)"),
                            ("merged", "Merged (custom merge strategy)"),
                        ],
                        help_text="How the duplicate was resolved",
                        max_length=16,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="When the deduplication decision was made",
                    ),
                ),
                (
                    "original_event",
                    models.ForeignKey(
                        help_text="The original event that was kept",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dedup_logs",
                        to="ingest.contractevent",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="eventdeduplicationlog",
            index=models.Index(fields=["original_event", "created_at"], name="ingest_even_origina_created_idx"),
        ),
        migrations.AddIndex(
            model_name="eventdeduplicationlog",
            index=models.Index(fields=["resolution", "created_at"], name="ingest_even_resolut_created_idx"),
        ),
        migrations.AddIndex(
            model_name="eventdeduplicationlog",
            index=models.Index(fields=["created_at"], name="ingest_even_created_idx"),
        ),
    ]
