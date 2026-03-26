from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ingest", "0015_merge_notification_and_teams"),
    ]

    operations = [
        migrations.CreateModel(
            name="EventAggregation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "contract",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="aggregations",
                        to="ingest.trackedcontract",
                    ),
                ),
                ("event_type", models.CharField(max_length=128)),
                ("timestamp", models.DateTimeField(db_index=True, help_text="Rounded to the nearest hour (bucket start)")),
                ("event_count", models.IntegerField(default=0)),
            ],
            options={
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="eventaggregation",
            unique_together={("contract", "event_type", "timestamp")},
        ),
        migrations.AddIndex(
            model_name="eventaggregation",
            index=models.Index(fields=["contract", "timestamp"], name="ingest_even_contrac_ts_idx"),
        ),
        migrations.AddIndex(
            model_name="eventaggregation",
            index=models.Index(fields=["timestamp"], name="ingest_even_ts_idx"),
        ),
    ]
