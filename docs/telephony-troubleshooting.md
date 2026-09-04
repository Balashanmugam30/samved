# SAMVED — Telephony Troubleshooting & Diagnostic Manual

This manual documents diagnostic procedures for telephony ingress and realtime audio streaming issues during Phase 1 operations.

---

## Diagnostic Symptom Matrix

| # | Symptom | Likely Cause | How to Verify | Remediation |
| :- | :--- | :--- | :--- | :--- |
| **1** | **No Inbound Webhook Received** | Caller dials number but FastAPI receives no `POST /v1/telephony/exotel/inbound` request. | Check `cloudflared` / `ngrok` request logs to see if traffic reaches your local machine. Verify virtual number mapping in Exotel App Bazaar. | Ensure `PUBLIC_BASE_URL` in `.env` is identical to your public tunnel HTTPS URL. Re-verify the Passthru applet URL in your Exotel call flow. |
| **2** | **Webhook 403 Forbidden** | Signature verification failed or shared secret mismatch. | Check FastAPI logs for `Rejected Exotel webhook: invalid HMAC signature`. | Verify `EXOTEL_WEBHOOK_SECRET` in `.env`. In local testing, set `EXOTEL_VERIFY_SIGNATURE=false`. |
| **3** | **Webhook 400 Bad Request** | Request missing `CallSid` parameter. | Inspect request body logs: `Missing required CallSid parameter`. | Ensure Exotel Passthru applet passes standard parameters (`CallSid`, `From`, `To`). |
| **4** | **WebSocket Rejected with Code 4004** | Exotel connects to `/ws/telephony/exotel/{session_id}` with an unknown or expired `session_id`. | Check logs: `Rejecting telephony WebSocket connection: unknown session_id`. | Ensure the Passthru applet passes the `session_id` returned from the inbound webhook into the Voicebot applet stream URL. |
| **5** | **Media Stream Never Starts** | Exotel connects WebSocket but emits no `start` or `media` events. | Check active sessions via `GET /v1/telephony/sessions`. Session remains in `CONNECTING` state. | Verify Voicebot Applet settings in Exotel; ensure "Bidirectional Streaming" is toggled ON and audio format is set to PCM 8000Hz. |
| **6** | **Sequence Gaps Reported in UI** | Audio packets dropped in network transit between Exotel and SAMVED gateway. | Check `sequence_gaps_count` in `/v1/telephony/sessions` or the Calls console. | Sequence gaps indicate network jitter between Exotel cloud and local tunnel. For production, host SAMVED on a cloud instance with low latency to AWS Mumbai (`ap-south-1`). |
| **7** | **Malformed Audio Frame Warning** | Base64 decode failed or frame length not a multiple of 320 bytes. | Check logs for `Malformed JSON in telephony stream` or dropped frames. | Confirm Exotel sends uncompressed 16-bit PCM at 8000Hz (not MP3 or AMR). |
| **8** | **Call Terminated Unexpectedly** | Exotel emitted `stop` event or caller hung up early. | Inspect `disconnect_reason` in session history. | Check if Exotel call timeout limit was reached or if the caller disconnected the call. |
| **9** | **Crosstalk / Shared State Between Calls** | Concurrency leak across concurrent calls. | Run `uv run pytest apps/api/tests/test_telephony_concurrency.py -v`. | SAMVED enforces strict per-session isolation in `RealtimeSessionManager`. Ensure global mutable variables are never used to store per-call audio. |
| **10** | **High Latency in Audio Stream** | Local development machine overloaded or public tunnel buffering packets. | Check `last_activity_at` and frame interval timestamps. | Run Next.js and FastAPI without heavy debug tracing; ensure tunnel has a direct TCP connection. |
