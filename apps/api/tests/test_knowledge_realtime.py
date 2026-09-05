"""Tests for knowledge search event broadcasting over WebSocket."""

from typing import List
import pytest
from app.knowledge.models import KnowledgeJurisdiction, KnowledgeQuery
from app.knowledge.service import KnowledgeService
from app.schemas.events import EventEnvelope, EventType


@pytest.mark.asyncio
async def test_knowledge_search_events_broadcast():
    service = KnowledgeService(auto_seed=True)
    captured_events: List[EventEnvelope] = []

    async def mock_broadcaster(envelope: EventEnvelope):
        captured_events.append(envelope)

    service.set_event_broadcaster(mock_broadcaster)

    query = KnowledgeQuery(
        query="One Stop Centre shelter admission",
        jurisdiction=KnowledgeJurisdiction.INDIA.value,
        call_id="call-ws-test-1",
    )
    res = await service.search(query)

    assert res.status == "COMPLETED"
    assert len(captured_events) >= 2

    event_types = [e.event_type for e in captured_events]
    assert EventType.KNOWLEDGE_SEARCH_STARTED in event_types
    assert EventType.KNOWLEDGE_SEARCH_COMPLETED in event_types

    # Verify session and call IDs are populated
    for e in captured_events:
        assert e.call_id == "call-ws-test-1"
