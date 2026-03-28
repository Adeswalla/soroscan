# Generated migration for contract state snapshots

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ingest', '0019_populate_webhook_signing_keys'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContractSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ledger_sequence', models.PositiveBigIntegerField(db_index=True, help_text='Ledger sequence number when snapshot was captured')),
                ('state_data', models.JSONField(help_text='Contract state data (JSON, max 1 MB)')),
                ('captured_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Timestamp when snapshot was captured')),
                ('contract', models.ForeignKey(help_text='Contract this snapshot belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='snapshots', to='ingest.trackedcontract')),
            ],
            options={
                'ordering': ['-ledger_sequence'],
            },
        ),
        migrations.CreateModel(
            name='StateChange',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_name', models.CharField(db_index=True, help_text="Dotted path to the field (e.g., 'balances.user1')", max_length=256)),
                ('old_value', models.JSONField(blank=True, help_text='Previous value (null if field was created)', null=True)),
                ('new_value', models.JSONField(help_text='New value after change')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='When this change was recorded')),
                ('previous_snapshot', models.ForeignKey(blank=True, help_text='Previous snapshot for comparison (null if first snapshot)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='next_state_changes', to='ingest.contractsnapshot')),
                ('snapshot', models.ForeignKey(help_text='The snapshot where this change was detected', on_delete=django.db.models.deletion.CASCADE, related_name='state_changes', to='ingest.contractsnapshot')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='contractsnapshot',
            index=models.Index(fields=['contract', '-ledger_sequence'], name='ingest_cont_contract_ledger_idx'),
        ),
        migrations.AddIndex(
            model_name='contractsnapshot',
            index=models.Index(fields=['contract', 'captured_at'], name='ingest_cont_contract_captured_idx'),
        ),
        migrations.AddConstraint(
            model_name='contractsnapshot',
            constraint=models.UniqueConstraint(fields=('contract', 'ledger_sequence'), name='unique_contract_ledger_snapshot'),
        ),
        migrations.AddIndex(
            model_name='statechange',
            index=models.Index(fields=['snapshot', 'field_name'], name='ingest_stat_snapshot_field_idx'),
        ),
        migrations.AddIndex(
            model_name='statechange',
            index=models.Index(fields=['snapshot', 'created_at'], name='ingest_stat_snapshot_created_idx'),
        ),
        migrations.AddIndex(
            model_name='statechange',
            index=models.Index(fields=['field_name', 'created_at'], name='ingest_stat_field_created_idx'),
        ),
    ]
