# SAMVED — Exotel Telephony & Realtime Streaming Integration Guide

## 1. Architectural Overview

```
📱 Caller Mobile Phone
         │ (dials 14566 / Exotel Virtual Number)
         ▼
📞 Exotel Telephony Cloud
         │
         ├──── [1] HTTP POST /v1/telephony/exotel/inbound (Passthru Applet)
         │         SAMVED creates Call & Session, returns Stream instruction
         │
         ▼
⚡ SAMVED Realtime Telephony Gateway
         │
         ├<─── [2] WebSocket wss://.../ws/telephony/exotel/{session_id} (Voicebot Applet)
         │         Bi-directional 16-bit 8000Hz PCM audio streaming
         │
         ▼
🎙️ Canonical Audio Pipeline (8kHz PCM Frames)
         │
         └──── [Future Phase 2] ➔ Sarvam Multilingual STT & TTS Loop
```

---

## 2. Exotel Account & Flow Configuration (Human Setup Steps)

To route live telephone calls from a mobile device to SAMVED:

### Step 1: Provision an Exotel Virtual Number (VN)
1. Log into your **Exotel Dashboard** (`my.exotel.com`).
2. Navigate to **ExoPhones / Numbers** and verify that your virtual number is active.
3. For the SIH 26093 implementation, this number maps to or forwards the **NHAA 14566** national helpline trunk.

### Step 2: Create Call Flow in App Bazaar
1. Go to **App Bazaar** → **Create App**.
2. Add a **Passthru Applet** as the entry point:
   - **URL**: `https://<YOUR_PUBLIC_DOMAIN>/v1/telephony/exotel/inbound`
   - **HTTP Method**: `POST`
   - **Data Format**: `JSON` or `Form-Encoded`
   - Connect the primary output leg to a **Stream / Voicebot Applet**.
3. Add a **Voicebot / Stream Applet**:
   - **WebSocket URL**: `wss://<YOUR_PUBLIC_DOMAIN>/ws/telephony/exotel/{CustomField}`
   - **Audio Format**: 16-bit Linear PCM (`s16le`), 8000 Hz, Mono.
   - **Direction**: Both (Inbound + Outbound).
4. Add a final **Passthru Applet** on hangup:
   - **URL**: `https://<YOUR_PUBLIC_DOMAIN>/v1/telephony/exotel/status`
   - **HTTP Method**: `POST`

---

## 3. Environment Variables

Configure the following parameters in your `.env` file (never commit real values to git):

```env
# Telephony Mode
APP_MODE=DEV                    # Set to LIVE only during authorized live testing
EXOTEL_ENABLED=false            # Toggle to true when Exotel credentials are active

# Exotel Credentials
EXOTEL_ACCOUNT_SID=your_exotel_account_sid
EXOTEL_API_KEY=your_exotel_api_key
EXOTEL_API_TOKEN=your_exotel_api_token
EXOTEL_SUB_DOMAIN=api.exotel.com
EXOTEL_CALLER_ID=+9180XXXXXXXX
EXOTEL_PHONE_NUMBER=+9180XXXXXXXX

# Public Ingress URLs (Required for Exotel Cloud to reach local server)
PUBLIC_BASE_URL=https://samved-dev.ngrok-free.app
PUBLIC_WS_BASE_URL=wss://samved-dev.ngrok-free.app

# Security & Verification
EXOTEL_VERIFY_SIGNATURE=false   # Set true in production with shared secret
EXOTEL_WEBHOOK_SECRET=your_webhook_hmac_secret
```

---

## 4. Local Development Public Tunnel

Exotel's telephony servers cannot connect to `localhost:8000`. To test live webhooks during development, expose port 8000 through a secure tunnel:

### Using Cloudflare Tunnel (`cloudflared`)
```bash
cloudflared tunnel --url http://localhost:8000
```

### Using ngrok
```bash
ngrok http 8000
```
Copy the generated HTTPS URL (e.g. `https://abc-123.ngrok.app`) and update your `.env`:
```env
PUBLIC_BASE_URL=https://abc-123.ngrok.app
PUBLIC_WS_BASE_URL=wss://abc-123.ngrok.app
```

---

## 5. Audio Format & Codec Specifications

| Parameter | Specification | Notes |
| :--- | :--- | :--- |
| **Codec** | 16-bit Linear PCM (`s16le`) | Uncompressed audio for low-latency DSP |
| **Sample Rate** | 8000 Hz (8 kHz) | Standard narrowband telephony |
| **Channels** | 1 (Mono) | Single audio channel |
| **Frame Duration** | 20 ms (standard) or 100 ms | Multiple of 320 bytes (160 samples × 2 bytes) |
| **Encoding** | Base64 | Encoded inside WebSocket JSON payload |

---

## 6. Pre-Call Diagnostics: Telephony Doctor

Before initiating or testing calls, run the diagnostic check:
```bash
curl http://localhost:8000/v1/telephony/doctor
```
Response:
```json
{
  "app_mode": "DEV",
  "telephony_provider": "Exotel",
  "exotel_credentials_present": false,
  "exotel_enabled": false,
  "live_mode_safe_to_start": false,
  "public_webhook_base_url": "http://localhost:8000",
  "public_ws_base_url": "ws://localhost:8000",
  "public_url_configured": false,
  "signature_verification_enabled": false,
  "active_calls_count": 0,
  "note": "Exotel webhooks require public HTTPS/WSS reachable endpoints during LIVE calls."
}
```
If `live_mode_safe_to_start` is `false`, the system safely degrades to `MockTelephonyProvider` and prevents unauthorized telephony charges.
