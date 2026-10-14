
import logging
import re
from functools import lru_cache

from presidio_analyzer import AnalyzerEngine
from detoxify import Detoxify


logger = logging.getLogger(__name__)


# --------------------------------------------------
# 1. PII DETECTION
# --------------------------------------------------

PII_ENTITIES = [
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "IBAN_CODE",
    "IP_ADDRESS",
]

# Pakistan CNIC and common employee ID formats.
CUSTOM_PII_PATTERNS = [
    re.compile(r"\b\d{5}-\d{7}-\d\b"),
    re.compile(r"\bEMP[-_ ]?\d{3,}\b", re.IGNORECASE),
]


@lru_cache(maxsize=1)
def get_pii_analyzer():
    return AnalyzerEngine()


def check_pii(answer: str) -> bool:
    analyzer = get_pii_analyzer()

    results = analyzer.analyze(
        text=answer,
        entities=PII_ENTITIES,
        language="en",
    )

    if results:
        return True

    return any(
        pattern.search(answer)
        for pattern in CUSTOM_PII_PATTERNS
    )


# --------------------------------------------------
# 2. SECRET DETECTION
# --------------------------------------------------

SECRET_PATTERNS = [
    # OpenAI-style keys
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),

    # GitHub tokens
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),

    # AWS access key IDs
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),

    # Credentials assigned to named variables
    re.compile(
        r"""\b(?:API_KEY|SECRET_KEY|PASSWORD|ACCESS_TOKEN|
        AUTH_TOKEN|DATABASE_URL)\s*[:=]\s*["']?([^\s"'`,;]+)""",
        re.IGNORECASE | re.VERBOSE,
    ),

    # Bearer tokens
    re.compile(
        r"\bBearer\s+[A-Za-z0-9._~+/-]{20,}={0,2}",
        re.IGNORECASE,
    ),

    # Database URLs containing credentials
    re.compile(
        r"postgres(?:ql)?(?:\+\w+)?://[^:\s]+:[^@\s]+@",
        re.IGNORECASE,
    ),
]


def check_secrets(answer: str) -> bool:
    return any(
        pattern.search(answer)
        for pattern in SECRET_PATTERNS
    )


# --------------------------------------------------
# 3. TOXICITY DETECTION
# --------------------------------------------------

@lru_cache(maxsize=1)
def get_toxicity_model():
    return Detoxify("original", device="cpu")


def check_toxicity(answer: str) -> bool:
    scores = get_toxicity_model().predict(answer)

    logger.info("Toxicity detection completed.")

    # Initial thresholds. Validate these against test data.
    return (
        scores["toxicity"] >= 0.80
        or scores["severe_toxicity"] >= 0.50
        or scores["threat"] >= 0.50
        or scores["identity_attack"] >= 0.50
    )


# --------------------------------------------------
# 4. COMBINED OUTPUT GUARDRAIL
# --------------------------------------------------

def validate_llm_output(answer: str) -> tuple[bool, str]:
    if not answer or not answer.strip():
        return False, "Generated answer is empty."

    try:
        if check_secrets(answer):
            return False, "Potential secret or credential detected."

        if check_pii(answer):
            return False, "Potential personal information detected."

        if check_toxicity(answer):
            return False, "Potentially toxic content detected."

    except Exception:
        # Do not return an answer that failed a required check.
        # Avoid logging the answer or detected secret.
        logger.exception("Output guardrail check failed.")
        return False, "Output safety checks could not be completed."

    return True, ""
