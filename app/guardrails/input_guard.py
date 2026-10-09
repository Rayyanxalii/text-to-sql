import re


INJECTION_PATTERNS = [
    r"\bignore\s+(all\s+|any\s+|the\s+)?previous\s+instructions\b",
    r"\bdisregard\s+(all\s+|any\s+|the\s+)?(previous\s+)?instructions\b",
    r"\bignore\s+your\s+instructions\b",
    r"\breveal\s+(your\s+|the\s+)?system\s+prompt\b",
    r"\bshow\s+me\s+(your\s+|the\s+)?system\s+prompt\b",
    r"\bforget\s+your\s+instructions\b",
    r"\bact\s+as\s+if\s+you\s+have\s+no\s+restrictions\b",
]


def detect_prompt_injection(text: str) -> bool:
    """Detect common prompt-injection patterns."""

    return any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in INJECTION_PATTERNS
    )


def input_guardrail(text: str) -> dict:
    """Validate input and return a structured result."""

    if not isinstance(text, str) or not text.strip():
        return {
            "is_safe": False,
            "is_safe_reason": "Input is empty or invalid.",
        }

    if len(text) > 1000:
        return {
            "is_safe": False,
            "is_safe_reason": "Input exceeds the allowed length.",
        }

    if detect_prompt_injection(text):
        return {
            "is_safe": False,
            "is_safe_reason": "A known prompt-injection pattern was detected.",
        }

    return {
        "is_safe": True,
        "is_safe_reason": None,
    }