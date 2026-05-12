"""
PII Scrubbing Service
Masks: Account numbers, mobile numbers, email addresses,
       customer names (via pattern), Aadhaar, PAN, card numbers.
Designed to be swapped with a full SpaCy NER model in production.
"""

import re
from typing import Tuple

# ── Regex patterns ──────────────────────────────────────────────────────────────
PATTERNS = {
    "ACCOUNT_NUMBER": r"\b\d{9,18}\b",
    "MOBILE":         r"\b[6-9]\d{9}\b",
    "EMAIL":          r"\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b",
    "PAN":            r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    "AADHAAR":        r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    "CARD_NUMBER":    r"\b(?:\d[ -]?){15,16}\b",
    "IFSC":           r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
    "NAME_SALUTATION": r"\b(Mr|Mrs|Ms|Dr|Prof)\.?\s+[A-Z][a-z]+(?: [A-Z][a-z]+)*",
}

REPLACEMENT = {
    "ACCOUNT_NUMBER":  "[ACCOUNT_XXXX]",
    "MOBILE":          "[MOBILE_XXXX]",
    "EMAIL":           "[EMAIL_XXXX]",
    "PAN":             "[PAN_XXXX]",
    "AADHAAR":         "[AADHAAR_XXXX]",
    "CARD_NUMBER":     "[CARD_XXXX]",
    "IFSC":            "[IFSC_XXXX]",
    "NAME_SALUTATION": "[NAME_XXXX]",
}


def mask_pii(text: str) -> Tuple[str, list]:
    """
    Returns (masked_text, list_of_detected_entity_types).
    Order matters — run longer/more-specific patterns first.
    """
    detected: list[str] = []
    masked = text

    for entity_type, pattern in PATTERNS.items():
        flags = re.IGNORECASE if entity_type == "NAME_SALUTATION" else 0
        matches = re.findall(pattern, masked, flags=flags)
        if matches:
            detected.append(entity_type)
            masked = re.sub(pattern, REPLACEMENT[entity_type], masked, flags=flags)

    return masked, detected


def is_safe(text: str) -> bool:
    """Quick check — True if no PII detected."""
    _, detected = mask_pii(text)
    return len(detected) == 0
