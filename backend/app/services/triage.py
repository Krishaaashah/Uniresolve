"""
NLP Triage Service
- Uses FLAN-T5-Base for category, severity, sentiment, key issue extraction
- Falls back to rule-based classification when model is unavailable
- Returns TriageResult with a suggested response draft
"""

import re
import json
import logging
from typing import Optional

from app.models.complaint import (
    TriageResult, Category, Severity, Sentiment
)

logger = logging.getLogger(__name__)

# ── Keyword maps for rule-based fallback ───────────────────────────────────────
CATEGORY_KEYWORDS = {
    Category.UPI:        ["upi", "payment", "transfer", "gpay", "phonepe", "neft", "rtgs", "imps", "transaction"],
    Category.NETBANKING: ["net banking", "netbanking", "login", "password", "otp", "internet banking", "online banking"],
    Category.LOANS:      ["loan", "emi", "interest", "repayment", "mortgage", "credit"],
    Category.ATM:        ["atm", "card", "debit card", "credit card", "swipe", "cash withdrawal", "blocked card"],
    Category.KYC:        ["kyc", "account", "aadhaar", "pan", "verification", "documents", "nominee"],
    Category.FRAUD:      ["fraud", "scam", "unauthorized", "stolen", "phishing", "hack", "cheat"],
}

SEVERITY_KEYWORDS = {
    Severity.CRITICAL: ["fraud", "stolen", "unauthorized", "scam", "hacked", "money gone", "lost money"],
    Severity.HIGH:     ["urgent", "immediately", "cannot access", "not working", "failed", "blocked", "emergency"],
    Severity.MEDIUM:   ["issue", "problem", "error", "complaint", "not able"],
    Severity.LOW:      ["inquiry", "request", "information", "update", "query"],
}

SENTIMENT_KEYWORDS = {
    Sentiment.ANGRY:      ["furious", "outraged", "disgusting", "terrible", "pathetic", "useless", "worst"],
    Sentiment.FRUSTRATED: ["frustrated", "annoyed", "fed up", "unhappy", "disappointed", "again", "still not"],
    Sentiment.SATISFIED:  ["happy", "thank", "resolved", "great", "good", "appreciate"],
}

RESPONSE_TEMPLATES = {
    Category.UPI:        "Dear Customer, we acknowledge your concern regarding your UPI/payment transaction. Our team is investigating the issue on priority. You will receive an update within 24 hours. Reference ID: {ref_id}",
    Category.NETBANKING: "Dear Customer, we understand you are facing difficulty accessing net banking services. Our technical team has been notified. Please try after 30 minutes or contact our 24x7 helpline at 1800-XXX-XXXX.",
    Category.LOANS:      "Dear Customer, we have received your query regarding your loan/EMI. Our loans team will review your account and contact you within 2 business days.",
    Category.ATM:        "Dear Customer, we are sorry to hear about your card/ATM issue. If your card is compromised, we strongly recommend calling our helpline immediately to block it. A replacement card will be dispatched within 5-7 working days.",
    Category.KYC:        "Dear Customer, your KYC/account query has been registered. Please visit your nearest branch with original documents or upload them via our mobile app for faster processing.",
    Category.FRAUD:      "URGENT: Dear Customer, we take fraud reports extremely seriously. Your account has been flagged for immediate review. Please call our fraud helpline 1800-XXX-XXXX (24x7) immediately. Do NOT share any OTP or credentials.",
    Category.GENERAL:    "Dear Customer, thank you for reaching out to Union Bank. Your complaint has been registered and will be addressed by our support team within 48 hours.",
}


def _rule_based_triage(text: str) -> TriageResult:
    """Deterministic fallback when the ML model is not loaded."""
    lower = text.lower()

    # Category
    category = Category.GENERAL
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            category = cat
            break

    # Severity
    severity = Severity.MEDIUM
    for sev, keywords in SEVERITY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            severity = sev
            break

    # Sentiment
    sentiment = Sentiment.NEUTRAL
    for sent, keywords in SENTIMENT_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            sentiment = sent
            break

    # Key issue: first sentence, trimmed
    sentences = re.split(r"[.!?]", text.strip())
    key_issue = sentences[0].strip()[:120] if sentences else text[:120]

    import uuid
    suggested_response = RESPONSE_TEMPLATES[category].format(
        ref_id=str(uuid.uuid4())[:8].upper()
    )

    return TriageResult(
        category=category,
        severity=severity,
        sentiment=sentiment,
        key_issue=key_issue,
        suggested_response=suggested_response,
        confidence=0.75,
    )


class TriageService:
    """
    Wraps FLAN-T5 for inference.
    Falls back to rule-based on import error or model unavailability.
    """

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        try:
            from transformers import T5ForConditionalGeneration, T5Tokenizer
            logger.info("Loading FLAN-T5-Base — this may take a minute...")
            model_name = "google/flan-t5-base"
            self.tokenizer = T5Tokenizer.from_pretrained(model_name)
            self.model = T5ForConditionalGeneration.from_pretrained(model_name)
            logger.info("FLAN-T5-Base loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load FLAN-T5 model: {e}. Using rule-based fallback.")

    def _prompt_classify(self, text: str, field: str, options: list[str]) -> str:
        """Ask the model to classify a single field."""
        prompt = (
            f"Classify the following banking customer complaint.\n"
            f"Field: {field}\n"
            f"Options: {', '.join(options)}\n"
            f"Complaint: {text}\n"
            f"Answer with only one option from the list."
        )
        inputs = self.tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
        outputs = self.model.generate(**inputs, max_new_tokens=20)
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip().lower()

    def _extract_key_issue(self, text: str) -> str:
        prompt = (
            f"Summarize the core issue in this banking complaint in one short sentence:\n{text}"
        )
        inputs = self.tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
        outputs = self.model.generate(**inputs, max_new_tokens=50)
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

    def triage(self, masked_text: str) -> TriageResult:
        if self.model is None:
            return _rule_based_triage(masked_text)

        try:
            # Category
            cat_str = self._prompt_classify(
                masked_text, "category",
                [c.value for c in Category]
            )
            category = next(
                (c for c in Category if c.value.lower() in cat_str),
                Category.GENERAL
            )

            # Severity
            sev_str = self._prompt_classify(
                masked_text, "severity",
                [s.value for s in Severity]
            )
            severity = next(
                (s for s in Severity if s.value in sev_str),
                Severity.MEDIUM
            )

            # Sentiment
            sent_str = self._prompt_classify(
                masked_text, "sentiment",
                [s.value for s in Sentiment]
            )
            sentiment = next(
                (s for s in Sentiment if s.value in sent_str),
                Sentiment.NEUTRAL
            )

            key_issue = self._extract_key_issue(masked_text)

            import uuid
            suggested_response = RESPONSE_TEMPLATES.get(category, RESPONSE_TEMPLATES[Category.GENERAL]).format(
                ref_id=str(uuid.uuid4())[:8].upper()
            )

            return TriageResult(
                category=category,
                severity=severity,
                sentiment=sentiment,
                key_issue=key_issue,
                suggested_response=suggested_response,
                confidence=0.88,
            )

        except Exception as e:
            logger.error(f"Model inference failed: {e}. Falling back to rules.")
            return _rule_based_triage(masked_text)


# Singleton
_triage_service: Optional[TriageService] = None


def get_triage_service() -> TriageService:
    global _triage_service
    if _triage_service is None:
        _triage_service = TriageService()
    return _triage_service
