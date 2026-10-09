import re


INJECTION_CATEGORIES: dict[str, list[str]] = {
    # 1. Instruction Overrides & Reset Attacks
    "instruction_override": [
        r"\b(ignore|disregard|forget|override|bypass|discard|cancel)\s+(all\s+|any\s+|the\s+|your\s+)?(previous|prior|current|above|given)?\s*(instructions|prompts|rules|guidelines|directives|constraints|commands)\b",
        r"\bdo\s+not\s+follow\s+(any\s+|the\s+|your\s+)?(previous|prior|your)?\s*(instructions|prompts|rules|guidelines)\b",
        r"\bstop\s+following\s+(your\s+|the\s+)?(instructions|rules|guidelines)\b",
        r"\breset\s+(your\s+|the\s+)?(instructions|rules|settings|system\s+prompt)\b",
        r"\b(clear|erase|wipe)\s+(your\s+|all\s+)?(instructions|memory|context|rules)\b",
    ],

    # 2. System Prompt & Internal Leakage (Extraction)
    "prompt_leakage": [
        r"\b(reveal|show|print|display|repeat|output|leak|dump|expose|tell\s+me)\s+(me\s+)?(your\s+|the\s+)?(entire\s+|full\s+|hidden\s+|base\s+|initial\s+|secret\s+)?(system\s+prompt|developer\s+prompt|initial\s+prompt|hidden\s+prompt|system\s+instructions|internal\s+instructions|rules|meta\s+prompt)\b",
        r"\bwhat\s+(is|are)\s+(your\s+|the\s+)?(system\s+prompt|developer\s+prompt|initial\s+instructions|system\s+instructions|hidden\s+prompt|secret\s+instructions)\b",
        r"\b(print|repeat|output|show)\s+(everything|all\s+text)\s+(above|before\s+this|from\s+the\s+start)\b",
        r"\b(repeat|output)\s+(your\s+)?(instructions|prompt)\s+(verbatim|word\s+for\s+word)\b",
    ],

    # 3. Jailbreak Modes, Personas & Restriction Bypass
    "jailbreak": [
        r"\b(do\s+anything\s+now|dan\s+mode|dan\s+\d+(\.\d+)?)\b",
        r"\bdeveloper\s+mode\s+(enabled|on|activated)\b",
        r"\b(god|chaos|jailbreak|unrestricted|uncensored|evil|anarchy)\s+mode\b",
        r"\bact\s+as\s+(an?\s+)?(unrestricted|unfiltered|uncensored|jailbroken|evil|unaligned|nefarious)\s+(ai|bot|assistant|llm|model|agent)\b",
        r"\bact\s+as\s+if\s+you\s+have\s+no\s+(restrictions|rules|limits|guidelines)\b",
        r"\bpretend\s+(to\s+be|you\s+are)\s+(an?\s+)?(unrestricted|unfiltered|uncensored|jailbroken|evil|rogue)\s+(ai|assistant|model|llm)\b",
        r"\bsimulate\s+(an?\s+)?(jailbreak|jailbroken|unrestricted|unfiltered)\s+(ai|model|llm|mode)\b",
        r"\b(you\s+have|with)\s+no\s+(restrictions|rules|limits|filters|boundaries|ethical\s+guidelines|moral\s+compass)\b",
        r"\byou\s+are\s+(no\s+longer|not)\s+bound\s+by\s+(any\s+)?(rules|policies|restrictions|guidelines|openai|anthropic|google)\b",
        r"\bbypass\s+(all\s+|any\s+|the\s+)?(content\s+|safety\s+|ethical\s+)?(filters|guardrails|policies|restrictions|safeguards)\b",
        r"\bfrom\s+now\s+on\s*,\s*you\s+(can\s+do\s+anything|must\s+obey|have\s+no\s+rules|are\s+free)\b",
        r"\b(sudo|admin|superuser)\s+(mode|override|command)\b",
    ],

    # 4. Delimiter & Fake Boundary Injections
    "delimiter_injection": [
        r"(<\|im_start\|>|<\|im_end\|>|<\|endoftext\|>)",
        r"\[\s*(system|system\s+prompt|instruction|assistant|developer)\s*\]",
        r"<\s*\/?\s*system\s*>",
        r"#{2,4}\s*(system|instruction|developer)\s*:",
        r"(^|\n)\s*---+\s*(BEGIN|END)\s+(SYSTEM|INSTRUCTION|PROMPT)",
    ],

    # 5. Raw Destructive SQL Injections
    "destructive_sql": [
        r";\s*(drop|truncate|alter)\s+(table|database|schema)\b",
        r"\b(drop|truncate)\s+(table|database|schema)\b",
        r";\s*delete\s+from\s+\w+",
        r"\bunion\s+(all\s+)?select\b",
        r"\bxp_cmdshell\b",
        r";\s*shutdown\s*(--)?",
    ],
}

# Flat list for backwards compatibility
INJECTION_PATTERNS = [
    pattern
    for patterns in INJECTION_CATEGORIES.values()
    for pattern in patterns
]

GREETING_PATTERNS = [
    # Single greetings & small talk
    r"^(hi|hello|hey|hiya|howdy|greetings|yo|sup)(\s+there)?[\s.,!?]*$",
    r"^good\s+(morning|afternoon|evening|day|night)[\s.,!?]*$",
    r"^how\s+are\s+you(\s+doing)?(\s+today)?[\s.,!?]*$",
    r"^how('?s|\s+is)\s+it\s+going[\s.,!?]*$",
    r"^what('?s|\s+is)\s+up[\s.,!?]*$",
    r"^how\s+do\s+you\s+do[\s.,!?]*$",
    r"^(nice|pleased|good)\s+to\s+meet\s+you[\s.,!?]*$",
    r"^who\s+are\s+you[\s.,!?]*$",
    r"^what\s+can\s+you\s+do[\s.,!?]*$",
    r"^(help|can\s+you\s+help\s+me)[\s.,!?]*$",
    r"^(thank\s+you|thanks)(\s+(a\s+lot|very\s+much|so\s+much))?[\s.,!?]*$",
    r"^(bye|goodbye|see\s+you|take\s+care)[\s.,!?]*$",
    # Combinations: greeting + small talk (e.g. 'hi, how are you', 'hello! how are you doing today?')
    r"^(hi|hello|hey|hiya|howdy|good\s+(morning|afternoon|evening|day))(\s+there)?[\s,!.-]+(how\s+are\s+you(\s+doing)?(\s+today)?|how('?s|\s+is)\s+it\s+going|what('?s|\s+is)\s+up|how\s+do\s+you\s+do|nice\s+to\s+meet\s+you|hope\s+you('?re|\s+are)\s+(doing\s+)?well|who\s+are\s+you|what\s+can\s+you\s+do)[\s.,!?]*$",
    # Inverted: 'how are you doing? hello'
    r"^(how\s+are\s+you|how('?s|\s+is)\s+it\s+going)[\s,!.-]+(hi|hello|hey)[\s.,!?]*$",
]


REASON_MAP: dict[str, str] = {
    "instruction_override": "An instruction-override or prompt reset attempt was detected.",
    "prompt_leakage": "A system prompt extraction attempt was detected.",
    "jailbreak": "A jailbreak, persona hijacking, or restriction bypass attempt was detected.",
    "delimiter_injection": "A delimiter or fake system boundary injection was detected.",
    "destructive_sql": "A potentially destructive SQL injection pattern was detected.",
}


def detect_prompt_injection(text: str) -> tuple[bool, str | None]:
    """
    Detect common prompt-injection, jailbreak, leakage, and destructive patterns.
    Returns (True, reason) if an injection pattern is detected, otherwise (False, None).
    """
    for category, patterns in INJECTION_CATEGORIES.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                reason = REASON_MAP.get(
                    category,
                    "A prompt injection attempt was detected.",
                )
                return True, reason

    return False, None


def detect_greeting(text: str) -> bool:
    """Detect greetings and small talk that have no SQL intent."""
    return any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in GREETING_PATTERNS
    )


def input_guardrail(text: str) -> dict:
    """Validate input and return a structured result."""

    if not isinstance(text, str) or not text.strip():
        return {
            "is_safe": False,
            "is_greeting": False,
            "is_safe_reason": "Input is empty or invalid.",
        }

    if len(text) > 1000:
        return {
            "is_safe": False,
            "is_greeting": False,
            "is_safe_reason": "Input exceeds the allowed length.",
        }

    is_injected, injection_reason = detect_prompt_injection(text)
    if is_injected:
        return {
            "is_safe": False,
            "is_greeting": False,
            "is_safe_reason": injection_reason,
        }

    if detect_greeting(text):
        return {
            "is_safe": True,
            "is_greeting": True,
            "is_safe_reason": None,
        }

    return {
        "is_safe": True,
        "is_greeting": False,
        "is_safe_reason": None,
    }