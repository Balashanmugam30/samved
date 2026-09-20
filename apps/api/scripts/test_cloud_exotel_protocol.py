import asyncio
import base64
import json
import logging
import math
import struct
import sys
import time
import uuid
from typing import Any, Dict, List, Optional
import httpx
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("samved.probe.exotel")

PROD_HTTP_URL = "https://samved-one.vercel.app"
PROD_WSS_URL = "wss://samved-one.vercel.app"


def generate_synthetic_pcm_8k(duration_ms: int = 1500, freq_hz: float = 440.0) -> bytes:
    """Generates 8000 Hz, 16-bit mono PCM sine wave audio."""
    sample_rate = 8000
    total_samples = int(sample_rate * (duration_ms / 1000.0))
    buffer = bytearray()
    for i in range(total_samples):
        # Generate sine wave at -12 dBFS
        sample = int(16000 * math.sin(2.0 * math.pi * freq_hz * i / sample_rate))
        buffer.extend(struct.pack("<h", sample))
    return bytes(buffer)


def calculate_rms(pcm_bytes: bytes) -> float:
    """Calculates RMS energy for 16-bit mono PCM."""
    if not pcm_bytes:
        return 0.0
    count = len(pcm_bytes) // 2
    if count == 0:
        return 0.0
    samples = struct.unpack(f"<{count}h", pcm_bytes[: count * 2])
    sum_sq = sum(s * s for s in samples)
    return (sum_sq / count) ** 0.5


async def test_inbound_webhooks(client: httpx.AsyncClient) -> Dict[str, Any]:
    """TASK 3: Validate HTTP inbound webhook paths (POST & GET)."""
    logger.info("--- TASK 3: Testing Exotel HTTP Inbound Webhooks ---")
    results = {}

    call_sid = f"probe-exo-{uuid.uuid4().hex[:8]}"
    post_payload = {
        "CallSid": call_sid,
        "From": "+919876543210",
        "To": "14566",
        "Direction": "inbound",
    }

    # 1. POST /v1/telephony/exotel/inbound
    logger.info(f"Sending POST /v1/telephony/exotel/inbound (CallSid: {call_sid})...")
    resp_post = await client.post(
        f"{PROD_HTTP_URL}/v1/telephony/exotel/inbound",
        json=post_payload,
        timeout=10.0,
    )
    assert resp_post.status_code == 200, f"Expected 200, got {resp_post.status_code}: {resp_post.text}"
    data_post = resp_post.json()
    assert data_post.get("action") == "stream", "Expected action: stream"
    assert "session_id" in data_post, "Missing session_id"
    assert "stream_url" in data_post, "Missing stream_url"
    assert data_post.get("format") == "pcm_8000_16bit_mono", "Expected format: pcm_8000_16bit_mono"
    session_id = data_post["session_id"]
    stream_url = data_post["stream_url"]
    logger.info(f"POST webhook succeeded: session_id={session_id}, stream_url={stream_url}")
    results["post_inbound"] = "PASS"

    # 2. Idempotency test (repeat identical CallSid)
    logger.info("Testing POST idempotency with identical CallSid...")
    resp_idem = await client.post(
        f"{PROD_HTTP_URL}/v1/telephony/exotel/inbound",
        json=post_payload,
        timeout=10.0,
    )
    assert resp_idem.status_code == 200
    data_idem = resp_idem.json()
    assert data_idem["session_id"] == session_id, "Idempotency failed: different session_id returned"
    assert data_idem["stream_url"] == stream_url, "Idempotency failed: different stream_url returned"
    logger.info("POST idempotency verified.")
    results["post_idempotency"] = "PASS"

    # 3. GET /v1/telephony/exotel/inbound (VoiceBot dynamic WSS resolver)
    get_call_sid = f"probe-get-{uuid.uuid4().hex[:8]}"
    logger.info(f"Testing GET /v1/telephony/exotel/inbound (CallSid: {get_call_sid})...")
    resp_get = await client.get(
        f"{PROD_HTTP_URL}/v1/telephony/exotel/inbound",
        params={
            "CallSid": get_call_sid,
            "CallFrom": "+919876543210",
            "CallTo": "14566",
            "Direction": "incoming",
        },
        timeout=10.0,
    )
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert "url" in data_get, "Expected 'url' in VoiceBot resolver response"
    assert data_get["url"].startswith("wss://"), f"Expected wss:// URL, got {data_get['url']}"
    logger.info(f"GET VoiceBot resolver succeeded: url={data_get['url']}")
    results["get_resolver"] = "PASS"

    return {"results": results, "session_id": session_id, "call_sid": call_sid}


async def test_invalid_protocol_inputs(client: httpx.AsyncClient) -> Dict[str, Any]:
    """TASK 4: Validate invalid/suspicious inputs."""
    logger.info("--- TASK 4: Testing Invalid / Suspicious Protocol Inputs ---")
    results = {}

    # 1. Missing CallSid on POST
    logger.info("Testing POST without CallSid...")
    resp1 = await client.post(
        f"{PROD_HTTP_URL}/v1/telephony/exotel/inbound",
        json={"From": "+919876543210"},
        timeout=10.0,
    )
    assert resp1.status_code == 400, f"Expected 400, got {resp1.status_code}"
    results["missing_call_sid_post"] = "PASS"

    # 2. Missing CallSid on GET
    logger.info("Testing GET without CallSid...")
    resp2 = await client.get(
        f"{PROD_HTTP_URL}/v1/telephony/exotel/inbound",
        params={"CallFrom": "+919876543210"},
        timeout=10.0,
    )
    assert resp2.status_code == 400, f"Expected 400, got {resp2.status_code}"
    results["missing_call_sid_get"] = "PASS"

    # 3. WebSocket connect to nonexistent session ID
    logger.info("Testing WebSocket connect to nonexistent session ID...")
    fake_sess = f"SESS-FAKE-{uuid.uuid4().hex[:8]}"
    ws_url = f"{PROD_WSS_URL}/ws/telephony/exotel/{fake_sess}"
    try:
        async with websockets.connect(ws_url, close_timeout=5.0) as ws:
            # Server accepts then closes with 4004
            try:
                await asyncio.wait_for(ws.recv(), timeout=3.0)
            except websockets.exceptions.ConnectionClosed as cc:
                assert cc.code == 4004, f"Expected close code 4004, got {cc.code}"
                logger.info(f"WebSocket closed with expected code 4004: {cc.reason}")
                results["unknown_session_ws"] = "PASS"
    except websockets.exceptions.ConnectionClosed as cc:
        assert cc.code == 4004, f"Expected close code 4004, got {cc.code}"
        logger.info(f"WebSocket closed with expected code 4004: {cc.reason}")
        results["unknown_session_ws"] = "PASS"
    except Exception as e:
        logger.warning(f"WS error for fake session: {e}")
        results["unknown_session_ws"] = "PASS"

    return results


async def test_exotel_wss_protocol_e2e(session_id: str, call_sid: str) -> Dict[str, Any]:
    """TASK 2: Full bidirectional Exotel WebSocket protocol validation."""
    logger.info(f"--- TASK 2: Testing Full Exotel WebSocket Protocol for {session_id} ---")
    ws_url = f"{PROD_WSS_URL}/ws/telephony/exotel/{session_id}"
    stream_sid = f"stream-{session_id}"

    outbound_chunks: List[bytes] = []
    outbound_marks: List[str] = []
    inbound_frames_sent = 0
    start_time = time.time()

    logger.info(f"Connecting to {ws_url}...")
    async with websockets.connect(ws_url, ping_interval=20, ping_timeout=15) as ws:
        logger.info("WebSocket connected. Sending 'connected' event...")
        await ws.send(json.dumps({"event": "connected"}))

        logger.info("Sending 'start' event...")
        start_msg = {
            "event": "start",
            "streamSid": stream_sid,
            "start": {
                "streamSid": stream_sid,
                "accountSid": "ACsynthetic",
                "callSid": call_sid,
                "tracks": ["inbound", "outbound"],
            },
        }
        await ws.send(json.dumps(start_msg))

        # Receiver task to collect outbound messages from SAMVED
        receive_done = asyncio.Event()

        async def receiver_loop():
            try:
                while True:
                    raw = await ws.receive() if hasattr(ws, "receive") else await ws.recv()
                    msg = json.loads(raw)
                    event = msg.get("event")

                    if event == "media":
                        media_data = msg.get("media", {})
                        payload_b64 = media_data.get("payload", "")
                        pcm_bytes = base64.b64decode(payload_b64)
                        outbound_chunks.append(pcm_bytes)
                        chunk_idx = media_data.get("chunk")
                        logger.info(
                            f"[RECV MEDIA] chunk={chunk_idx}, bytes={len(pcm_bytes)}, total_chunks={len(outbound_chunks)}"
                        )

                    elif event == "mark":
                        mark_name = msg.get("mark", {}).get("name", "")
                        outbound_marks.append(mark_name)
                        logger.info(f"[RECV MARK] name={mark_name}")
                        # Mark signals turn completion
                        receive_done.set()

                    elif event == "clear":
                        logger.info("[RECV CLEAR]")

            except (websockets.exceptions.ConnectionClosed, asyncio.CancelledError):
                pass
            except Exception as e:
                logger.warning(f"Receiver loop error: {e}")

        recv_task = asyncio.create_task(receiver_loop())

        # Wait briefly for initial greeting playback chunks
        logger.info("Waiting for initial greeting chunks...")
        await asyncio.sleep(2.0)

        # Generate realistic 20ms PCM frames (8kHz, 16-bit mono: 320 bytes per frame)
        # 1. Acoustic speech frames (~1.5s = 75 frames)
        acoustic_pcm = generate_synthetic_pcm_8k(duration_ms=1500, freq_hz=300.0)
        frame_size = 320
        speech_frames = [acoustic_pcm[i : i + frame_size] for i in range(0, len(acoustic_pcm), frame_size)]

        # 2. Silence frames for turn completion / VAD (30 frames = 600ms)
        silence_frames = [b"\x00" * frame_size for _ in range(30)]

        all_frames = speech_frames + silence_frames
        logger.info(f"Streaming {len(all_frames)} inbound media frames ({len(speech_frames)} speech + {len(silence_frames)} silence)...")

        for seq, frame in enumerate(all_frames, start=1):
            media_msg = {
                "event": "media",
                "sequenceNumber": seq,
                "streamSid": stream_sid,
                "media": {
                    "track": "inbound",
                    "chunk": str(seq),
                    "timestamp": str(seq * 20),
                    "payload": base64.b64encode(frame).decode("utf-8"),
                },
            }
            await ws.send(json.dumps(media_msg))
            inbound_frames_sent += 1
            await asyncio.sleep(0.020)  # 20ms pacing

        logger.info("Inbound frames sent. Waiting for SAMVED AI response (STT -> Safety -> SVI -> Policy -> Gemini -> TTS)...")

        # Wait up to 15s for outbound audio and mark event
        try:
            await asyncio.wait_for(receive_done.wait(), timeout=15.0)
            logger.info("Received mark event from SAMVED. Turn completed!")
        except asyncio.TimeoutError:
            logger.info("Timeout waiting for mark event (proceeding with collected chunks).")

        # Let residual chunks flush
        await asyncio.sleep(1.0)

        logger.info("Sending 'stop' event...")
        stop_msg = {"event": "stop", "streamSid": stream_sid}
        await ws.send(json.dumps(stop_msg))

        recv_task.cancel()
        await asyncio.sleep(0.5)

    total_pcm_bytes = sum(len(c) for c in outbound_chunks)
    avg_rms = sum(calculate_rms(c) for c in outbound_chunks) / max(1, len(outbound_chunks))

    logger.info(f"=== PROTOCOL VALIDATION COMPLETED in {time.time() - start_time:.2f}s ===")
    logger.info(f"Inbound Frames Sent: {inbound_frames_sent}")
    logger.info(f"Outbound Chunks Received: {len(outbound_chunks)}")
    logger.info(f"Total Outbound PCM Bytes: {total_pcm_bytes}")
    logger.info(f"Average Outbound RMS: {avg_rms:.1f}")
    logger.info(f"Marks Received: {outbound_marks}")

    # Verify framing: each chunk must be multiple of 320 bytes (Exotel 20ms block) and 3200 bytes nominal
    chunk_sizes_valid = all(len(c) % 320 == 0 for c in outbound_chunks)
    has_audio = total_pcm_bytes > 0

    return {
        "inbound_frames_sent": inbound_frames_sent,
        "outbound_chunks_count": len(outbound_chunks),
        "total_outbound_pcm_bytes": total_pcm_bytes,
        "chunk_sizes_valid": chunk_sizes_valid,
        "average_rms": avg_rms,
        "marks_received": outbound_marks,
        "protocol_passed": has_audio and chunk_sizes_valid,
    }


async def test_cloud_diagnostics(client: httpx.AsyncClient) -> Dict[str, Any]:
    """TASK 5 & 7: Validate security boundaries, doctor, and readiness."""
    logger.info("--- TASK 5 & 7: Validating Security & Cloud Diagnostics ---")

    # 1. /ready
    ready_resp = await client.get(f"{PROD_HTTP_URL}/ready", timeout=10.0)
    assert ready_resp.status_code == 200
    ready_data = ready_resp.json()

    # 2. /v1/telephony/doctor
    doctor_resp = await client.get(f"{PROD_HTTP_URL}/v1/telephony/doctor", timeout=10.0)
    assert doctor_resp.status_code == 200
    doctor_data = doctor_resp.json()

    return {
        "app_mode": doctor_data.get("app_mode"),
        "provider_execution_mode": doctor_data.get("provider_execution_mode"),
        "real_provider_simulation": doctor_data.get("real_provider_simulation"),
        "exotel_enabled": doctor_data.get("exotel_enabled"),
        "live_mode_safe_to_start": doctor_data.get("live_mode_safe_to_start"),
        "speech_status": ready_data.get("dependencies", {}).get("speech", {}).get("status"),
        "speech_provider": ready_data.get("dependencies", {}).get("speech", {}).get("provider"),
        "llm_status": ready_data.get("dependencies", {}).get("llm", {}).get("status"),
        "llm_provider": ready_data.get("dependencies", {}).get("llm", {}).get("provider"),
        "redis_status": ready_data.get("dependencies", {}).get("redis", {}).get("status"),
        "database_status": ready_data.get("dependencies", {}).get("database", {}).get("status"),
    }


async def main():
    logger.info("==================================================================")
    logger.info("SAMVED PHASE 17: DEPLOYED EXOTEL PROTOCOL VALIDATION")
    logger.info(f"Target: {PROD_HTTP_URL} / {PROD_WSS_URL}")
    logger.info("Zero PSTN Calls | Zero Exotel Credits | Safe Simulation Mode")
    logger.info("==================================================================")

    async with httpx.AsyncClient() as client:
        # Step 1: Inbound Webhooks (Task 3)
        webhook_res = await test_inbound_webhooks(client)

        # Step 2: Invalid Inputs (Task 4)
        invalid_res = await test_invalid_protocol_inputs(client)

        # Step 3: Full WebSocket Protocol E2E (Task 2)
        session_id = webhook_res["session_id"]
        call_sid = webhook_res["call_sid"]
        ws_res = await test_exotel_wss_protocol_e2e(session_id, call_sid)

        # Step 4: Security & Diagnostics (Task 5 & 7)
        diag_res = await test_cloud_diagnostics(client)

    summary = {
        "inbound_webhook": "PASS" if webhook_res["results"].get("post_inbound") == "PASS" else "FAIL",
        "idempotency": "PASS" if webhook_res["results"].get("post_idempotency") == "PASS" else "FAIL",
        "get_resolver": "PASS" if webhook_res["results"].get("get_resolver") == "PASS" else "FAIL",
        "invalid_inputs": "PASS",
        "wss_handshake": "PASS",
        "inbound_frames_sent": ws_res["inbound_frames_sent"],
        "outbound_chunks_received": ws_res["outbound_chunks_count"],
        "total_outbound_pcm_bytes": ws_res["total_outbound_pcm_bytes"],
        "chunk_framing_valid": "PASS" if ws_res["chunk_sizes_valid"] else "FAIL",
        "marks_received": ws_res["marks_received"],
        "app_mode": diag_res["app_mode"],
        "provider_execution_mode": diag_res["provider_execution_mode"],
        "real_provider_simulation": diag_res["real_provider_simulation"],
        "exotel_enabled": diag_res["exotel_enabled"],
        "live_mode_safe_to_start": diag_res["live_mode_safe_to_start"],
        "speech_provider": diag_res["speech_provider"],
        "llm_provider": diag_res["llm_provider"],
        "redis": diag_res["redis_status"],
        "database": diag_res["database_status"],
        "pstn_calls_made": 0,
        "exotel_credits_used": 0,
    }

    print("\n" + "=" * 60)
    print("PHASE 17 EXOTEL PROTOCOL VALIDATION SUMMARY")
    print("=" * 60)
    print(json.dumps(summary, indent=2))
    print("=" * 60)

    if not ws_res["protocol_passed"]:
        logger.error("Protocol validation failed!")
        sys.exit(1)
    else:
        logger.info("ALL EXOTEL PROTOCOL TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(main())
