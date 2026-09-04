import struct
from typing import Iterator, List
from app.schemas.telephony import AudioFrame


class AudioStreamAdapter:
    """Manages audio frame slicing, normalization, and energy detection for realtime telephony."""

    FRAME_SIZE_BYTES = 320  # 20ms of 8000 Hz, 16-bit mono PCM (160 samples * 2 bytes)

    @staticmethod
    def slice_pcm_to_frames(pcm_bytes: bytes) -> List[bytes]:
        """Slices raw PCM byte buffer into exact 320-byte (20ms) chunks."""
        frames = []
        for i in range(0, len(pcm_bytes), AudioStreamAdapter.FRAME_SIZE_BYTES):
            chunk = pcm_bytes[i : i + AudioStreamAdapter.FRAME_SIZE_BYTES]
            if len(chunk) == AudioStreamAdapter.FRAME_SIZE_BYTES:
                frames.append(chunk)
            elif len(chunk) > 0:
                # Pad remaining bytes with silence
                padded = chunk + b"\x00" * (AudioStreamAdapter.FRAME_SIZE_BYTES - len(chunk))
                frames.append(padded)
        return frames

    @staticmethod
    def calculate_energy_rms(pcm_bytes: bytes) -> float:
        """Calculates RMS energy of 16-bit PCM chunk to detect voice presence."""
        if not pcm_bytes:
            return 0.0
        # 16-bit signed little-endian integers
        count = len(pcm_bytes) // 2
        if count == 0:
            return 0.0
        try:
            samples = struct.unpack(f"<{count}h", pcm_bytes[: count * 2])
            sum_squares = sum(s * s for s in samples)
            return (sum_squares / count) ** 0.5
        except Exception:
            return 0.0

    @staticmethod
    def is_speech_active(pcm_bytes: bytes, threshold_rms: float = 300.0) -> bool:
        """Heuristic check for voice activity in 20ms frame."""
        return AudioStreamAdapter.calculate_energy_rms(pcm_bytes) > threshold_rms