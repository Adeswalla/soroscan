# Contract State Snapshots - Integration Guide

## URL Routing

Add the ContractSnapshotViewSet to your Django REST Framework router in `django-backend/soroscan/ingest/urls.py`:

```python
from rest_framework.routers import DefaultRouter
from .views import (
    TrackedContractViewSet,
    ContractEventViewSet,
    ContractSnapshotViewSet,  # Add this
    # ... other viewsets
)

router = DefaultRouter()
router.register(r'contracts', TrackedContractViewSet, basename='contract')
router.register(r'events', ContractEventViewSet, basename='event')
router.register(r'snapshots', ContractSnapshotViewSet, basename='snapshot')  # Add this
# ... other registrations

urlpatterns = [
    path('api/', include(router.urls)),
    # ... other patterns
]
```

## Celery Configuration

Update `django-backend/soroscan/celery.py` to include the snapshot task in the beat schedule:

```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    # ... existing tasks ...
    
    'snapshot-contract-state': {
        'task': 'soroscan.ingest.tasks.snapshot_contract_state',
        'schedule': crontab(minute='*/5'),  # Run every 5 minutes
        'kwargs': {'snapshot_interval': 1000},  # Capture every 1000 ledgers
    },
}
```

## Environment Configuration

Add to `.env` or environment variables:

```bash
# Snapshot configuration
SNAPSHOT_INTERVAL=1000  # Capture snapshots every N ledgers

# Optional: Adjust Soroban RPC settings if needed
SOROBAN_RPC_URL=https://soroban-testnet.stellar.org
STELLAR_NETWORK_PASSPHRASE=Test SDF Network ; September 2015
```

## Database Migration

Run the migration to create the new tables:

```bash
cd django-backend
python manage.py migrate ingest 0017_contract_snapshots
```

Verify the migration:

```bash
python manage.py showmigrations ingest | grep contract_snapshots
```

## Testing the Implementation

### 1. Create a test contract

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
from soroscan.ingest.models import TrackedContract

user = User.objects.first()
contract = TrackedContract.objects.create(
    contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4",
    name="Test Contract",
    owner=user,
    is_active=True,
    last_indexed_ledger=1000,
)
print(f"Created contract: {contract}")
```

### 2. Manually trigger the snapshot task

```python
from soroscan.ingest.tasks import snapshot_contract_state

result = snapshot_contract_state.delay(snapshot_interval=1000)
print(f"Task result: {result.get()}")
```

### 3. Verify snapshots were created

```python
from soroscan.ingest.models import ContractSnapshot

snapshots = ContractSnapshot.objects.all()
print(f"Total snapshots: {snapshots.count()}")
for snapshot in snapshots:
    print(f"  - {snapshot.contract.name} at ledger {snapshot.ledger_sequence}")
```

### 4. Test the REST API

```bash
# List all snapshots
curl http://localhost:8000/api/snapshots/

# Get snapshots for a specific contract
curl "http://localhost:8000/api/snapshots/by_contract/?contract_id=CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4"

# Get snapshots in a ledger range
curl "http://localhost:8000/api/snapshots/by_contract/?contract_id=CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4&ledger_min=500&ledger_max=1500"

# Get state changes for a snapshot
curl http://localhost:8000/api/snapshots/1/state_changes/
```

### 5. Test the GraphQL API

```bash
curl -X POST http://localhost:8000/graphql/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ contractState(contractId: \"CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4\") { ledgerSequence stateData capturedAt } }"
  }'
```

### 6. Access the admin interface

Navigate to: http://localhost:8000/admin/ingest/contractsnapshot/

## Running Tests

```bash
# Run all snapshot tests
pytest django-backend/soroscan/ingest/tests/test_contract_snapshots.py -v

# Run specific test
pytest django-backend/soroscan/ingest/tests/test_contract_snapshots.py::TestContractSnapshots::test_snapshot_creation -v

# Run with coverage
pytest django-backend/soroscan/ingest/tests/test_contract_snapshots.py --cov=soroscan.ingest --cov-report=html
```

## Monitoring

### Check Celery task execution

```bash
# Monitor Celery worker
celery -A soroscan worker -l debug

# Monitor Celery beat
celery -A soroscan beat -l debug
```

### Check logs

```bash
# Django logs
tail -f logs/django.log | grep snapshot

# Celery logs
tail -f logs/celery.log | grep snapshot_contract_state
```

### Database queries

```python
from django.db import connection
from django.test.utils import CaptureQueriesContext

from soroscan.ingest.models import ContractSnapshot

with CaptureQueriesContext(connection) as context:
    snapshots = ContractSnapshot.objects.filter(
        ledger_sequence__gte=1000,
        ledger_sequence__lte=2000
    ).select_related('contract').prefetch_related('state_changes')
    list(snapshots)

print(f"Queries executed: {len(context)}")
for query in context:
    print(f"  - {query['sql'][:100]}...")
```

## Performance Tuning

### Optimize snapshot queries

```python
# Good: Use select_related and prefetch_related
snapshots = ContractSnapshot.objects.select_related(
    'contract'
).prefetch_related(
    'state_changes'
).filter(
    contract__is_active=True
).order_by('-ledger_sequence')[:100]

# Bad: N+1 queries
snapshots = ContractSnapshot.objects.all()[:100]
for snapshot in snapshots:
    print(snapshot.contract.name)  # Extra query per snapshot
    for change in snapshot.state_changes.all():  # Extra query per snapshot
        print(change.field_name)
```

### Index usage

The migration creates indexes on:
- `(contract, -ledger_sequence)` - For recent snapshots
- `(contract, ledger_sequence)` - For range queries
- `(snapshot, field_name)` - For state change lookups
- `(field_name, -created_at)` - For field history

Verify indexes are being used:

```python
from django.db import connection
from django.db.backends.utils import CursorDebugWrapper

# Enable query logging
connection.queries_log.clear()

snapshots = ContractSnapshot.objects.filter(
    contract_id=1,
    ledger_sequence__gte=1000
).order_by('-ledger_sequence')[:10]

for query in connection.queries:
    print(query['sql'])
```

## Troubleshooting

### Snapshots not being created

1. **Check contract is active**
   ```python
   from soroscan.ingest.models import TrackedContract
   contract = TrackedContract.objects.get(contract_id="CXXX...")
   print(f"Is active: {contract.is_active}")
   print(f"Last indexed ledger: {contract.last_indexed_ledger}")
   ```

2. **Check ledger is multiple of interval**
   ```python
   interval = 1000
   ledger = contract.last_indexed_ledger
   print(f"Ledger {ledger} % {interval} = {ledger % interval}")
   ```

3. **Check Soroban RPC connectivity**
   ```python
   from soroscan.ingest.stellar_client import SorobanClient
   client = SorobanClient()
   state = client.get_contract_state("CXXX...")
   print(f"State: {state}")
   ```

4. **Check Celery task logs**
   ```bash
   celery -A soroscan worker -l debug
   ```

### State size warnings

If snapshots are being skipped due to size:

1. **Check state size**
   ```python
   import json
   from soroscan.ingest.models import ContractSnapshot
   
   snapshot = ContractSnapshot.objects.latest('captured_at')
   size = len(json.dumps(snapshot.state_data).encode('utf-8'))
   print(f"State size: {size / 1024 / 1024:.2f} MB")
   ```

2. **Increase snapshot interval**
   ```python
   # Capture less frequently
   snapshot_contract_state.delay(snapshot_interval=5000)
   ```

3. **Implement state compression** (Phase 2)

## Rollback

If you need to rollback the migration:

```bash
python manage.py migrate ingest 0016_eventaggregation
```

This will:
- Drop the ContractSnapshot table
- Drop the StateChange table
- Remove the migration record

## Next Steps

1. Deploy to staging environment
2. Run integration tests
3. Monitor Celery task execution
4. Verify snapshots are being created
5. Test REST and GraphQL APIs
6. Deploy to production
7. Monitor performance and logs
