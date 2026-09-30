from __future__ import annotations

import hashlib
import re

PII_PATTERNS: dict[str, str] = {
    "email": r"[\w\.-]+@[\w\.-]+\.\w+",
    "phone_vn": r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)",
    "cccd": r"\b\d{12}\b",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    # Passport identifiers commonly appear after an explicit label.
    "passport": r"(?i)\bpassport\s*[:#]?\s*[A-Z]\d{7,8}\b",
    # Scrub address values after common Vietnamese address labels.
    "vn_address": r"(?i)\b(?:địa chỉ|dia chi|address)\s*[:=]\s*[^,;\n]{5,100}",
}


def scrub_text(text: str) -> str:
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = re.sub(pattern, f"[REDACTED_{name.upper()}]", safe)
    return safe


def scrub_event(_: object, __: str, event_dict: dict) -> dict:
    """Scrub every string recursively before logs reach any output processor."""
    def clean(value):
        if isinstance(value, str):
            return scrub_text(value)
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items()}
        if isinstance(value, list):
            return [clean(item) for item in value]
        if isinstance(value, tuple):
            return tuple(clean(item) for item in value)
        return value

    return clean(event_dict)


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
