import json
import uuid
from app.schemas.events import EventEnvelope, EventType, SVIBand, SVIUpdatedPayload


def test_contract_event_flow_producer_to_consumer(client):
    """Verifies that an event produced conforms strictly to EventEnvelope,

    is transported via WebSocket, and consumed with valid field extraction.
    """
    session_id = f"contract-sess-{uuid.uuid4().hex[:6]}"
    call_id = f"contract-call-{uuid.uuid4().hex[:6]}"

    # 1. Producer generates SVI payload
    svi_payload = SVIUpdatedPayload(
        score=65,
        band=SVIBand.HIGH,
        confidence=0.92,
        contributing_factors=[
            {"factor": "acute_withdrawal", "weight": 0.45, "evidence": "shivering reported"},
            {"factor": "housing_instability", "weight": 0.35, "evidence": "no safe shelter"},
        ],
        is_clinical_diagnosis=False,
    )

    # 2. Package into canonical EventEnvelope
    outgoing_envelope = EventEnvelope(
        event_type=EventType.SVI_UPDATED,
        session_id=session_id,
        call_id=call_id,
        payload=svi_payload.model_dump(),
    )

    # 3. Transmit through WebSocket gateway
    with client.websocket_connect(f"/ws?session_id={session_id}") as ws:
        # Welcome event
        _ = ws.receive_json()

        # Send envelope
        ws.send_text(outgoing_envelope.model_dump_json())

        # Receive broadcast/echo
        raw_received = ws.receive_text()
        received_dict = json.loads(raw_received)

        # 4. Consumer decodes and validates
        incoming_envelope = EventEnvelope.model_validate(received_dict)
        assert incoming_envelope.event_type == EventType.SVI_UPDATED
        assert incoming_envelope.schema_version == "1.0"
        assert incoming_envelope.session_id == session_id
        assert incoming_envelope.call_id == call_id

        # Verify decoded payload preserves all contract fields
        decoded_svi = SVIUpdatedPayload.model_validate(incoming_envelope.payload)
        assert decoded_svi.score == 65
        assert decoded_svi.band == SVIBand.HIGH
        assert decoded_svi.is_clinical_diagnosis is False
        assert len(decoded_svi.contributing_factors) == 2
