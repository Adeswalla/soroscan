#!/usr/bin/env python
"""Quick manual test for check_integrity command logic."""
import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "soroscan.settings_test")
sys.path.insert(0, "/home/adeswalla/Desktop/Work/Drips/Contribuitor/Wave 4/soroscan/django-backend")

django.setup()

from io import StringIO
from django.core.management import call_command
from soroscan.ingest.models import ContractEvent
from soroscan.ingest.tests.factories import ContractEventFactory, TrackedContractFactory


def test_basic_functionality():
    """Test basic command functionality."""
    print("=" * 60)
    print("Testing check_integrity command basic functionality")
    print("=" * 60)

    # Clean up existing test data
    ContractEvent.objects.all().delete()

    contract = TrackedContractFactory()

    # Test 1: No events
    print("\n1. Testing with no events...")
    out = StringIO()
    call_command("check_integrity", stdout=out)
    output = out.getvalue()
    assert "No events found" in output
    print("✓ Passed: No events case handled correctly")

    # Test 2: Continuous ledger sequence
    print("\n2. Testing with continuous ledger sequence...")
    ContractEvent.objects.all().delete()
    for i in range(6):
        ContractEventFactory(contract=contract, ledger=1000 + i)

    out = StringIO()
    call_command("check_integrity", stdout=out)
    output = out.getvalue()
    assert "✓ No gaps found" in output
    assert "Unique Ledgers with Events: 6" in output
    print("✓ Passed: Continuous sequence detected correctly")
    print(output)

    # Test 3: Single gap detection
    print("\n3. Testing with single gap...")
    ContractEvent.objects.all().delete()
    for ledger in [1000, 1001, 1005, 1006]:
        ContractEventFactory(contract=contract, ledger=ledger)

    out = StringIO()
    call_command("check_integrity", stdout=out)
    output = out.getvalue()
    assert "✗ Found 1 gap(s)" in output
    assert "Gap: Ledger 1,002 - 1,004" in output
    print("✓ Passed: Single gap detected correctly")
    print(output)

    # Test 4: Multiple gaps detection
    print("\n4. Testing with multiple gaps...")
    ContractEvent.objects.all().delete()
    for ledger in [1000, 1001, 1005, 1010, 1011]:
        ContractEventFactory(contract=contract, ledger=ledger)

    out = StringIO()
    call_command("check_integrity", stdout=out)
    output = out.getvalue()
    assert "✗ Found 2 gap(s)" in output
    assert "Gap: Ledger 1,002 - 1,004" in output
    assert "Gap: Ledger 1,006 - 1,009" in output
    print("✓ Passed: Multiple gaps detected correctly")
    print(output)

    # Test 5: Filter by contract
    print("\n5. Testing with contract filter...")
    contract2 = TrackedContractFactory()
    for i in range(3):
        ContractEventFactory(contract=contract2, ledger=2000 + i)

    out = StringIO()
    call_command("check_integrity", f"--contract={contract.id}", stdout=out)
    output = out.getvalue()
    assert "Contract ID:" in output
    print("✓ Passed: Contract filter works correctly")

    # Test 6: Filter by event type
    print("\n6. Testing with event-type filter...")
    ContractEvent.objects.all().delete()
    for i in range(3):
        ContractEventFactory(contract=contract, ledger=1000 + i, event_type="swap")
    for i in range(3):
        ContractEventFactory(
            contract=contract, ledger=1010 + i, event_type="transfer"
        )

    out = StringIO()
    call_command("check_integrity", "--event-type=swap", stdout=out)
    output = out.getvalue()
    assert "Event Type Filter: swap" in output
    assert "✓ No gaps found" in output
    print("✓ Passed: Event type filter works correctly")

    # Test 7: Large gap detection
    print("\n7. Testing with large gap...")
    ContractEvent.objects.all().delete()
    ContractEventFactory(contract=contract, ledger=1000)
    ContractEventFactory(contract=contract, ledger=100000)

    out = StringIO()
    call_command("check_integrity", stdout=out)
    output = out.getvalue()
    assert "✗ Found 1 gap(s)" in output
    assert "Total Missing Ledgers: 98,999" in output
    print("✓ Passed: Large gap detected correctly")
    print(output)

    print("\n" + "=" * 60)
    print("All manual tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_basic_functionality()
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
