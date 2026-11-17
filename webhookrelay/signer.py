import base64
import hashlib
import hmac
import time
from typing import Dict


def sign_payload(provider: str, secret: str, payload: str | bytes) -> Dict[str, str]:
    if isinstance(payload, str):
        payload_bytes = payload.encode("utf-8")
    else:
        payload_bytes = payload

    normalized = provider.strip().lower()

    if normalized == "stripe":
        timestamp = int(time.time())
        to_sign = f"{timestamp}.".encode("utf-8") + payload_bytes
        signature = hmac.new(secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
        return {
            "stripe-signature": f"t={timestamp},v1={signature}",
            "x-signature-timestamp": str(timestamp),
        }

    if normalized == "github":
        signature = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        return {
            "x-hub-signature-256": f"sha256={signature}",
        }

    if normalized == "shopify":
        digest = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode("utf-8")
        return {
            "x-shopify-hmac-sha256": signature,
        }

    signature = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return {
        "x-signature-sha256": signature,
    }
