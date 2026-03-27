# Contract State Snapshots Feature

## Overview

The Contract State Snapshots feature enables SoroScan to capture and track contract state at periodic intervals, allowing operators to answer historical questions about contract behavior such as:

- "What was the total supply at ledger 100,000?"
- "When did the pause flag flip to true?"
- "How did the balance distribution change over time?"

## Architecture

### Models

#### ContractSnapshot
Stores periodic snapshots of contract state at specific ledger sequences.

```python
class ContractSnapshot(models.Model):
    contract = ForeignKey(TrackedContract)
    ledger_sequence = PositiveBigIntegerField()  # Ledger at which snapshot was captured
    state_data = JSONField()  # Full contract state (max 1 MB)
    captured_at = DateTimeField()  # Timestamp of capture
    
    class Meta:
        unique_together = ('contract', 'ledger_sequence')
        indexes = [
            Index(fields=['contract', '-ledger_sequence']),
        ]
```

#### StateChange
Tracks field-level changes between consecutive snapshots.

```python
class StateChange(models.Model):
    snapshot = ForeignKey(ContractSnapshot)
    previous_snapshot = ForeignKey(ContractSnapshot, null=True)
    field_name = CharField()  # Dotted path (e.g., 'balances.user1')
    old_value = JSONField(null=True)
    new_value = JSONField()
    created_at = DateTimeField()
    
    class Meta:
        indexes = [
            Index(fields=['snapshot', 'field_name']),
            Index(fields=['field_name', '-created_at']),
        ]
```

### Periodic Task

The `snapshot_contract_state` Celery task runs periodically to capture snapshots:

```python
@shared_task
def snapshot_contract_state(snapshot_interval: int = 1000):
    """
    Capture snapshots every N ledgers (default: 1000).
    
    For each active contract:
    1. Check if last_indexed_ledger is a multiple of snapshot_interval
    2. Fetch current state via SorobanClient.get_contract_state()
    3. Create ContractSnapshot record
    4. Calculate state-diff from previous snapshot
    5. Create StateChange records for each field modification
    """
```

### API Endpoints

#### REST API

**List snapshots with filtering:**
```
GET /api/snapshots/?contract={id}&ledger_min={X}&ledger_max={Y}
```

**Get snapshots for a specific contract:**
```
GET /api/snapshots/by_contract/?contract_id={address}&ledger_min={X}&ledger_max={Y}
```

**Get state changes for a snapshot:**
```
GET /api/snapshots/{id}/state_changes/
```

#### GraphQL API

**Query contract state at a specific ledger:**
```graphql
query {
  contractState(contractId: "CXXX...", ledger: 100000) {
    id
    ledgerSequence
    stateData
    capturedAt
    stateChanges {
      fieldName
      oldValue
      newValue
      createdAt
    }
  }
}
```

**Query snapshots within a ledger range:**
```graphql
query {
  contractSnapshots(
    contractId: "CXXX..."
    ledgerMin: 50000
    ledgerMax: 150000
    limit: 50
  ) {
    id
    ledgerSequence
    stateData
    stateChanges {
      fieldName
      oldValue
      newValue
    }
    capturedAt
  }
}
```

### Admin Interface

The Django admin provides:

1. **ContractSnapshotAdmin**
   - List view with contract, ledger, state size, and capture time
   - Inline display of state changes
   - Read-only access (no manual creation/deletion)
   - State size display (B, KB, MB)

2. **StateChangeAdmin**
   - List view with snapshot, field name, and timestamp
   - Filtering by field name and date
   - Read-only access

## Configuration

### Snapshot Interval

Configure the snapshot capture interval (in ledgers) via environment variable:

```bash
SNAPSHOT_INTERVAL=1000  # Capture every 1000 ledgers (default)
```

Or pass as parameter to the task:

```python
snapshot_contract_state.delay(snapshot_interval=500)
```

### Celery Beat Schedule

Add to `celery.py`:

```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    'snapshot-contract-state': {
        'task': 'soroscan.ingest.tasks.snapshot_contract_state',
        'schedule': crontab(minute='*/5'),  # Run every 5 minutes
        'kwargs': {'snapshot_interval': 1000},
    },
}
```

## Constraints & Limitations

1. **State Size Limit**: Snapshots exceeding 1 MB are skipped with a warning
2. **Snapshot Frequency**: Only captured at configured intervals (default: every 1000 ledgers)
3. **State Diff Accuracy**: Detects top-level field changes; nested object changes are tracked as whole objects
4. **Storage**: Each snapshot stores the full state JSON; consider archival policies for long-term retention

## Usage Examples

### REST API

**Get the most recent state for a contract:**
```bash
curl "http://localhost:8000/api/snapshots/by_contract/?contract_id=CXXX..."
```

**Get state changes for a specific field:**
```bash
curl "http://localhost:8000/api/snapshots/?contract=1&ledger_min=50000&ledger_max=150000"
```

### GraphQL

**Query state at a specific ledger:**
```graphql
{
  contractState(contractId: "CXXX...", ledger: 100000) {
    stateData
    stateChanges {
      fieldName
      oldValue
      newValue
    }
  }
}
```

**Track a specific field over time:**
```graphql
{
  contractSnapshots(contractId: "CXXX...", limit: 100) {
    ledgerSequence
    stateData
    stateChanges(fieldName: "paused") {
      oldValue
      newValue
      createdAt
    }
  }
}
```

## Testing

Run the integration tests:

```bash
pytest django-backend/soroscan/ingest/tests/test_contract_snapshots.py -v
```

Tests cover:
- Snapshot creation and metadata
- Unique constraint enforcement
- State-diff calculation
- State change tracking
- Snapshot ordering and querying
- Field-level change detection

## Future Enhancements (Phase 2)

1. **State Inference**: Reconstruct state at any ledger from events
2. **State Predictors**: Forward-project state changes based on patterns
3. **Compression**: Compress large state snapshots
4. **Archival**: Move old snapshots to cold storage (S3, etc.)
5. **State Validation**: Verify snapshots against on-chain state

## Troubleshooting

### Snapshots not being created

1. Check that contracts have `is_active=True`
2. Verify `last_indexed_ledger` is set and is a multiple of `snapshot_interval`
3. Check Celery task logs: `celery -A soroscan worker -l debug`
4. Verify SorobanClient can connect to RPC: `python manage.py shell`

### State size warnings

If you see "State snapshot exceeds 1 MB":
1. Review the contract's state structure
2. Consider increasing `snapshot_interval` to reduce frequency
3. Implement state compression (Phase 2)

### Missing state changes

State changes are only tracked between consecutive snapshots. If snapshots are sparse:
1. Decrease `snapshot_interval` for more frequent captures
2. Use event-based reconstruction for intermediate states (Phase 2)
