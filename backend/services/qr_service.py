"""
services/qr_service.py — Dynamic QR code generation and verification.

QR payload rotates every 60 seconds using HMAC-SHA256.
This prevents students from sharing screenshots to fake attendance.
"""
import time
import hmac
import hashlib
import base64
import qrcode
from io import BytesIO
from backend.config import SECRET_KEY


def _make_token(lecture_id: str, window: int) -> str:
    """HMAC token for a specific 60-second time window."""
    msg = f"{lecture_id}:{window}".encode()
    return hmac.new(SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()[:12].upper()


def generate_qr(lecture_id: str) -> dict:
    """
    Generate a QR code image (PNG, base64) plus a token valid for 60 seconds.
    Returns: { token, window, expires_at, image_b64 }
    """
    window = int(time.time()) // 60          # changes every 60 seconds
    token  = _make_token(lecture_id, window)
    expires_at = (window + 1) * 60          # unix timestamp when it expires

    payload = f"MITAOE|{lecture_id}|{token}|{expires_at}"

    img = qrcode.make(payload)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return {
        "token":      token,
        "window":     window,
        "expires_at": expires_at,
        "image_b64":  base64.b64encode(buf.getvalue()).decode(),
    }


def verify_qr(lecture_id: str, token: str) -> bool:
    """
    Check that the scanned token matches the current or previous window.
    Allows a 120-second grace period (current window + one past window).
    """
    now = int(time.time()) // 60
    valid_tokens = {
        _make_token(lecture_id, now),
        _make_token(lecture_id, now - 1),   # grace: 60-120 s old scans
    }
    return token in valid_tokens
