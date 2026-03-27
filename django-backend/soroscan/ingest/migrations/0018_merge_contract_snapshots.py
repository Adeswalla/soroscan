# Merge migration to resolve conflicting migration branches

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ingest', '0017_contract_snapshots'),
        ('ingest', '0018_merge_deprecation_and_eventdedup'),
        ('ingest', '0018_merge_webhook_timeout_and_eventdedup'),
    ]

    operations = [
    ]
