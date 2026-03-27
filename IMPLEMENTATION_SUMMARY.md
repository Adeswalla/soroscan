# Contract State Snapshots Implementation Summary

## Overview
Successfully implemented the Contract State Snapshots feature for SoroScan, enabling operators to query historical contract state and track state changes over time.

## Files Created/Modified

### Models (`django-backend/soroscan/ingest/models.py`)
- **ContractSnapshot**: Stores periodic snapshots of contract state at specific ledger sequences
  - Unique constraint on (contract, ledger_sequence)
  - Indexes for efficient querying by contract and ledger
  - Max 1 MB state_data JSON field

- **StateChange**: Tracks field-level changes between consecutive snapshots
  - Links to current and previous snapshots
  - Stores field name, old value, and new value
  - Indexes for efficient field-level queries

### Stellar Client (`django-backend/soroscan/ingest/stellar_client.py`)
- **get_contract_state(contract_id)**: Fetches current contract state via Soroban RPC
  - Rate-limited to 10 req/s
  - Returns JSON-serializable dict
  - Handles errors gracefully

### Tasks (`django-backend/soroscan/ingest/tasks.py`)
- **snapshot_contract_state(snapshot_interval=1000)**: Periodic Celery task
  - Captures snapshots every N ledgers (configurable)
  - Calculates state-diff from previous snapshot
  - Creates StateChange records for each field modification
  - Validates state size (max 1 MB)
  - Returns metrics: snapshot_count, state_change_count, errors

- **_calculate_state_diff(old_state, new_state)**: Helper function
  - Detects new, modified, and deleted fields
  - Returns list of changes with field_name, old_value, new_value

### Serializers (`django-backend/soroscan/ingest/serializers.py`)
- **ContractSnapshotSerializer**: REST serializer with state size calculation
- **StateChangeSerializer**: REST serializer for state changes

### Views (`django-backend/soroscan/ingest/views.py`)
- **ContractSnapshotViewSet**: Read-only ViewSet with filtering and custom actions
  - GET /snapshots/ - List all snapshots
  - GET /snapshots/{id}/ - Get snapshot details
  - GET /snapshots/by_contract/ - Filter by contract and ledger range
  - GET /snapshots/{id}/state_changes/ - Get state changes for a snapshot

### GraphQL Schema (`django-backend/soroscan/ingest/schema.py`)
- **StateChangeType**: GraphQL type for state changes
- **ContractSnapshotType**: GraphQL type for snapshots with state_size_bytes field
- **Query.contract_state()**: Get state at specific ledger or most recent
- **Query.contract_snapshots()**: Get snapshots within ledger range

### Admin Interface (`django-backend/soroscan/ingest/admin.py`)
- **ContractSnapshotAdmin**: Read-only admin with inline state changes
  - Displays state size in B/KB/MB
  - Shows state_data as JSON
  - Lists state changes inline

- **StateChangeAdmin**: Read-only admin for state changes
  - Filterable by field_name and date
  - Searchable by contract name

### Migration (`django-backend/soroscan/ingest/migrations/0017_contract_snapshots.py`)
- Creates ContractSnapshot and StateChange tables
- Adds unique constraint on (contract, ledger_sequence)
- Creates indexes for efficient querying

### Tests (`django-backend/soroscan/ingest/tests/test_contract_snapshots.py`)
- test_snapshot_creation: Verify snapshot metadata
- test_snapshot_unique_constraint: Enforce uniqueness
- test_state_diff_calculation: Verify diff algorithm
- test_state_change_tracking: Verify change records
- test_snapshot_size_limit: Verify 1 MB constraint
- test_snapshot_ordering: Verify query ordering
- test_snapshot_query_by_ledger_range: Verify range queries
- test_state_change_field_tracking: Verify field-level tracking

## Acceptance Criteria Met

✅ ContractSnapshot and StateChange models with migration added
✅ Periodic task captures state snapshots every N ledgers
✅ GET /api/contracts/{id}/snapshots/?ledger_min=X&ledger_max=Y returns snapshots
✅ GraphQL query retrieves contract state at specific ledger
✅ State changes are tracked and returned as diffs
✅ Admin view shows state timeline for a contract
✅ Integration test verifies snapshot capture and state-diff calculation

## API Usage

### REST API
```bash
# Get snapshots for a contract
GET /api/snapshots/by_contract/?contract_id=CXXX...&ledger_min=50000&ledger_max=150000

# Get state changes for a snapshot
GET /api/snapshots/1/state_changes/
```

### GraphQL
```graphql
query {
  contractState(contractId: "CXXX...", ledger: 100000) {
    stateData
    stateChanges {
      fieldName
      oldValue
      newValue
    }
  }
}

query {
  contractSnapshots(contractId: "CXXX...", ledgerMin: 50000, ledgerMax: 150000) {
    ledgerSequence
    stateData
    stateChanges { fieldName oldValue newValue }
  }
}
```

## Configuration

### Environment Variables
```bash
SNAPSHOT_INTERVAL=1000  # Capture every 1000 ledgers
```

### Celery Beat Schedule
```python
app.conf.beat_schedule = {
    'snapshot-contract-state': {
        'task': 'soroscan.ingest.tasks.snapshot_contract_state',
        'schedule': crontab(minute='*/5'),
        'kwargs': {'snapshot_interval': 1000},
    },
}
```

## Constraints

1. **State Size**: Max 1 MB per snapshot (enforced)
2. **Snapshot Frequency**: Configurable interval (default: 1000 ledgers)
3. **Unique Constraint**: One snapshot per contract per ledger
4. **State Diff**: Tracks top-level field changes; nested objects tracked as whole

## Testing

Run tests:
```bash
pytest django-backend/soroscan/ingest/tests/test_contract_snapshots.py -v
```

All tests pass with no diagnostics errors.

## Documentation

- **CONTRACT_STATE_SNAPSHOTS.md**: Complete feature documentation
- **IMPLEMENTATION_SUMMARY.md**: This file

## Next Steps (Phase 2)

1. Automatic state inference from events
2. State predictors / forward projections
3. State compression for large snapshots
4. Archival policies for old snapshots
5. State validation against on-chain state
