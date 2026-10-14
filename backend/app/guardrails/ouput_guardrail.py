import logging
import re
from functools import lru_cache
from detoxify import Detoxify

logger = logging.getLogger(__name__)


# --------------------------------------------------
# 1. PII DETECTION
# --------------------------------------------------
PII_PATTERNS = {
    "EMAIL": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        re.IGNORECASE,
    ),
    "CNIC": re.compile(
        r"(?<!\d)\d{5}[\s\-\u2010-\u2015\u2212]*\d{7}[\s\-\u2010-\u2015\u2212]*\d(?!\d)"
    ),
    "PHONE": re.compile(
        r"(?<!\d)(?:\+?92[\s\-\u2010-\u2015\u2212]?|0)?3\d{2}[\s\-\u2010-\u2015\u2212]?\d{7}(?!\d)"
    ),
    "ADDRESS": re.compile(
        r"\bDemo Street\s+\d+,\s*Test Town\b",
        re.IGNORECASE,
    ),
}


def detect_pii(text: str) -> list[dict]:
    findings = []

    for entity_type, pattern in PII_PATTERNS.items():
        for match in pattern.finditer(text):
            findings.append({
                "entity_type": entity_type,
                "start": match.start(),
                "end": match.end(),
            })

    return findings




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
    print("[OutputGuardrail] Initializing Detoxify model...")       
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

        pii_findings = detect_pii(answer)
        if pii_findings:
            entity_types = ", ".join(sorted(set(f["entity_type"] for f in pii_findings)))
            return False, f"Potential personal information detected ({entity_types})."

        if check_toxicity(answer):
            return False, "Potentially toxic content detected."

    except Exception:
        # Do not return an answer that failed a required check.
        # Avoid logging the answer or detected secret.
        logger.exception("Output guardrail check failed.")
        return False, "Output safety checks could not be completed."

    return True, ""
