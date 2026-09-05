"""Test suite for Case Intelligence multi-call linking and unlinking (Phase 11)."""

import pytest
from app.cases.service import CaseService


@pytest.mark.asyncio
async def test_link_multiple_calls_to_case():
    svc = CaseService(auto_seed=False)
    case = await svc.create_case(case_number="CAS-LINK-001")

    call1 = "call-101"
    call2 = "call-102"
    call3 = "call-103"

    await svc.link_call(case.case_id, call1)
    await svc.link_call(case.case_id, call2)
    await svc.link_call(case.case_id, call3, is_primary=True)

    updated = await svc.get_case(case.case_id)
    assert len(updated.linked_calls) == 3
    # Primary call promoted to first position
    assert updated.linked_calls[0] == call3

    # Fast reverse lookup
    case_found = await svc.get_case_by_call(call2)
    assert case_found is not None
    assert case_found.case_id == case.case_id


@pytest.mark.asyncio
async def test_unlink_call_from_case():
    svc = CaseService(auto_seed=False)
    case = await svc.create_case(case_number="CAS-LINK-002")
    call_id = "call-unlink-test"

    await svc.link_call(case.case_id, call_id)
    assert await svc.get_case_by_call(call_id) is not None

    await svc.unlink_call(case.case_id, call_id)
    updated = await svc.get_case(case.case_id)
    assert call_id not in updated.linked_calls
    assert await svc.get_case_by_call(call_id) is None
