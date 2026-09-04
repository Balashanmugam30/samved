import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.realtime.session_manager import telephony_session_manager


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_list_calls_empty_or_existing(client):
    response = client.get("/v1/calls")
    assert response.status_code == 200
    data = response.json()
    assert "active_calls" in data
    assert "recent_calls" in data
    assert "total_active" in data
    assert "total_recent" in data
    assert isinstance(data["active_calls"], list)
    assert isinstance(data["recent_calls"], list)


@pytest.mark.asyncio
async def test_call_lifecycle_and_transcript_events_rest(client):
    # 1. Create a session
    call_id = f"test-rest-call-{uuid.uuid4().hex[:6]}"
    session_id = f"test-rest-sess-{uuid.uuid4().hex[:6]}"
    raw_phone = "+919876543210"

    sess = await telephony_session_manager.create_session(
        session_id=session_id,
        call_id=call_id,
        provider_call_id=f"exo-{uuid.uuid4().hex[:6]}",
        caller_number=raw_phone,
        provider="mock",
    )

    try:
        # 2. Check GET /v1/calls shows the active session with masked number
        res = client.get("/v1/calls")
        assert res.status_code == 200
        active_calls = res.json()["active_calls"]
        found = [c for c in active_calls if c["call_id"] == call_id]
        assert len(found) == 1
        assert found[0]["caller_masked_number"] == "+91******3210"
        assert found[0]["state"] in ("NEW", "INITIATED")

        # 3. Check GET /v1/calls/{call_id}
        res_single = client.get(f"/v1/calls/{call_id}")
        assert res_single.status_code == 200
        data_single = res_single.json()
        assert data_single["call_id"] == call_id
        assert data_single["caller_masked_number"] == "+91******3210"

        # 4. Check GET /v1/calls/{call_id}/transcript
        res_transcript = client.get(f"/v1/calls/{call_id}/transcript")
        assert res_transcript.status_code == 200
        transcript_data = res_transcript.json()
        assert transcript_data["call_id"] == call_id
        assert isinstance(transcript_data["utterances"], list)

        # 5. Check GET /v1/calls/{call_id}/events
        res_events = client.get(f"/v1/calls/{call_id}/events")
        assert res_events.status_code == 200
        events_data = res_events.json()
        assert events_data["call_id"] == call_id
        assert isinstance(events_data["events"], list)

        # 6. Check unknown call 404
        res_404 = client.get(f"/v1/calls/non-existent-{uuid.uuid4().hex[:6]}")
        assert res_404.status_code == 404

        res_404_tr = client.get(f"/v1/calls/non-existent-{uuid.uuid4().hex[:6]}/transcript")
        assert res_404_tr.status_code == 404

    finally:
        # 7. End session and verify it is archived in recent_calls
        ended_sess = await telephony_session_manager.end_session(session_id, reason="test_done")
        assert ended_sess is not None

        res_after = client.get("/v1/calls")
        assert res_after.status_code == 200
        data_after = res_after.json()
        recent_found = [c for c in data_after["recent_calls"] if c["call_id"] == call_id]
        assert len(recent_found) == 1
        assert recent_found[0]["call_id"] == call_id
        assert recent_found[0]["caller_masked_number"] == "+91******3210"

        # Transcript endpoint still works for completed call
        res_recent_tr = client.get(f"/v1/calls/{call_id}/transcript")
        assert res_recent_tr.status_code == 200
        assert res_recent_tr.json()["call_id"] == call_id
