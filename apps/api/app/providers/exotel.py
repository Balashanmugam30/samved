import base64
import hashlib
import hmac
import logging
from typing import Any, Dict, Optional
import httpx

from app.core.config import get_settings
from app.schemas.telephony import (
    AudioDirection,
    AudioFormat,
    AudioFrame,
    ExotelMediaEvent,
    ExotelOutboundMediaMessage,
    ExotelWebSocketMessage,
)

logger = logging.getLogger("samved.providers.exotel")


class ExotelTelephonyProvider:
    """Production provider adapter for Exotel Voice & Streaming APIs."""

    def __init__(self):
        self.settings = get_settings()
        self.account_sid = self.settings.EXOTEL_ACCOUNT_SID or ""
        self.api_key = self.settings.EXOTEL_API_KEY or ""
        self.api_token = self.settings.EXOTEL_API_TOKEN or ""
        self.subdomain = self.settings.EXOTEL_SUB_DOMAIN or "api.exotel.com"
        self.base_url = f"https://{self.subdomain}/v1/Accounts/{self.account_sid}"

    @property
    def is_configured(self) -> bool:
        return bool(self.account_sid and self.api_key and self.api_token)

    def _get_auth(self) -> Optional[httpx.BasicAuth]:
        if self.api_key and self.api_token:
            return httpx.BasicAuth(self.api_key, self.api_token)
        return None

    async def initiate_call(self, to_number: str, from_number: str, metadata: Dict[str, Any]) -> str:
        """Initiates an outbound call via Exotel REST API."""
        if not self.is_configured:
            raise RuntimeError("Exotel provider credentials not configured.")

        url = f"{self.base_url}/Calls/connect.json"
        data = {
            "From": from_number,
            "To": to_number,
            "CallerId": self.settings.EXOTEL_CALLER_ID or from_number,
            "CustomField": metadata.get("session_id", ""),
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, data=data, auth=self._get_auth())
            resp.raise_for_status()
            res_json = resp.json()
            call_sid = res_json.get("Call", {}).get("Sid")
            logger.info(f"Initiated Exotel call Sid: {call_sid}")
            return call_sid or "unknown-exotel-sid"

    async def terminate_call(self, call_id: str, reason: str = "normal_hangup") -> bool:
        """Terminates an active Exotel call via REST API."""
        if not self.is_configured:
            logger.warning(f"Mocking call termination for {call_id} (Exotel not configured)")
            return True

        url = f"{self.base_url}/Calls/{call_id}.json"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(url, data={"Status": "completed"}, auth=self._get_auth())
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Failed to terminate Exotel call {call_id}: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Checks Exotel configuration and connectivity."""
        if not self.is_configured:
            return {
                "provider": "Exotel",
                "configured": False,
                "status": "unconfigured",
                "streaming_enabled": False,
            }

        # Validate credentials with a lightweight GET against the Account endpoint
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}.json", auth=self._get_auth())
                is_healthy = resp.status_code == 200
                return {
                    "provider": "Exotel",
                    "configured": True,
                    "status": "healthy" if is_healthy else "unauthorized",
                    "status_code": resp.status_code,
                    "streaming_enabled": self.settings.EXOTEL_ENABLED,
                }
        except Exception as e:
            return {
                "provider": "Exotel",
                "configured": True,
                "status": "unreachable",
                "error": str(e),
                "streaming_enabled": self.settings.EXOTEL_ENABLED,
            }

    def validate_webhook(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        """Validates Exotel webhook authenticity using HMAC signature if enabled."""
        if not self.settings.EXOTEL_VERIFY_SIGNATURE:
            return True

        secret = self.settings.EXOTEL_WEBHOOK_SECRET
        if not secret:
            logger.warning("Webhook signature verification enabled but EXOTEL_WEBHOOK_SECRET is empty.")
            return False

        signature = headers.get("x-exotel-signature") or headers.get("X-Exotel-Signature")
        if not signature:
            return False

        expected_sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_sig, signature)

    def create_streaming_instruction(self, session_id: str, ws_stream_url: str) -> Dict[str, Any]:
        """Returns the streaming applet instruction for Exotel to connect to our WebSocket."""
        return {
            "action": "stream",
            "stream_url": ws_stream_url,
            "session_id": session_id,
            "format": "pcm_8000_16bit_mono",
            "tracks": ["inbound", "outbound"],
        }

    def normalize_media_event(
        self,
        raw_msg: Dict[str, Any],
        session_id: str,
        call_id: str,
        sequence_number: int,
    ) -> Optional[AudioFrame]:
        """Converts incoming Exotel WebSocket media JSON into a canonical AudioFrame."""
        event_type = raw_msg.get("event")
        if event_type != ExotelMediaEvent.MEDIA.value:
            return None

        media_data = raw_msg.get("media", {})
        payload_b64 = media_data.get("payload") or media_data.get("chunk") or ""
        if not payload_b64:
            return None

        try:
            raw_bytes = base64.b64decode(payload_b64)
            size_bytes = len(raw_bytes)
        except Exception:
            return None

        return AudioFrame(
            session_id=session_id,
            call_id=call_id,
            sequence_number=raw_msg.get("sequenceNumber", sequence_number),
            direction=AudioDirection.INBOUND,
            codec="pcm_s16le",
            sample_rate_hz=8000,
            channels=1,
            payload_base64=payload_b64,
            payload_size_bytes=size_bytes,
        )

    def format_outbound_media(self, stream_sid: str, pcm_bytes: bytes) -> Dict[str, Any]:
        """Encodes raw PCM bytes into Exotel outbound media envelope."""
        b64_payload = base64.b64encode(pcm_bytes).decode("utf-8")
        outbound = ExotelOutboundMediaMessage(
            event="media",
            streamSid=stream_sid,
            media={"payload": b64_payload},
        )
        return outbound.model_dump()
