# Merge migration to resolve conflicting migration branches

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ingest', '0017_contract_snapshots'),
    ]

    operations = [
    ]
