# Generated migration for ContractSnapshot and StateChange models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ingest', '0016_eventaggregation'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContractSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ledger_sequence', models.PositiveBigIntegerField(db_index=True, help_text='Ledger sequence at which this snapshot was captured')),
                ('state_data', models.JSONField(help_text='Full contract state as JSON (max 1 MB)')),
                ('captured_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Timestamp when snapshot was captured')),
                ('contract', models.ForeignKey(help_text='The contract being snapshotted', on_delete=django.db.models.deletion.CASCADE, related_name='snapshots', to='ingest.trackedcontract')),
            ],
            options={
                'ordering': ['-ledger_sequence'],
            },
        ),
        migrations.CreateModel(
            name='StateChange',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_name', models.CharField(db_index=True, help_text="Dotted path to the changed field (e.g., 'balances.user1')", max_length=256)),
                ('old_value', models.JSONField(blank=True, help_text='Previous value of the field', null=True)),
                ('new_value', models.JSONField(help_text='New value of the field')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('previous_snapshot', models.ForeignKey(blank=True, help_text='Previous snapshot for comparison (null if first snapshot)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='next_state_changes', to='ingest.contractsnapshot')),
                ('snapshot', models.ForeignKey(help_text='The snapshot where this change was detected', on_delete=django.db.models.deletion.CASCADE, related_name='state_changes', to='ingest.contractsnapshot')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='contractsnapshot',
            index=models.Index(fields=['contract', '-ledger_sequence'], name='ingest_cont_contract_idx_ledger_desc'),
        ),
        migrations.AddIndex(
            model_name='contractsnapshot',
            index=models.Index(fields=['contract', 'ledger_sequence'], name='ingest_cont_contract_idx_ledger_asc'),
        ),
        migrations.AlterUniqueTogether(
            name='contractsnapshot',
            unique_together={('contract', 'ledger_sequence')},
        ),
        migrations.AddIndex(
            model_name='statechange',
            index=models.Index(fields=['snapshot', 'field_name'], name='ingest_stat_snapshot_idx_field'),
        ),
        migrations.AddIndex(
            model_name='statechange',
            index=models.Index(fields=['field_name', '-created_at'], name='ingest_stat_field_idx_created'),
        ),
    ]
