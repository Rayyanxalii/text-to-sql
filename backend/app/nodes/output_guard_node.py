from langchain_core.messages import AIMessage

from app.state import state
from app.guardrails.ouput_guardrail import validate_llm_output

REDACTED_RESPONSE = (
    "I couldn't provide this response because it may contain sensitive information."
)


def output_guard_node(s: state) -> dict:
    """
    Runs the generated answer through the output guardrail (PII, secrets,
    toxicity checks via Presidio + Detoxify).

    - If the answer is safe: passes through unchanged.
    - If harmful content is detected: replaces the answer with a fixed
      redaction message and sets answer_harmful=True.

    Sets:
        answer_harmful (bool)            – True when the answer was redacted.
        answer_harmful_reason (str|None) – Reason for redaction, or None.
        answer (str)                     – Possibly replaced with REDACTED_RESPONSE.
        messages (list)                  – Last AIMessage updated to match.
    """
    print("\n========== ENTERED OUTPUT GUARD ==========")

    is_safe, reason = validate_llm_output(s.answer)
    
    print(f"[OutputGuard] is_safe={is_safe}, reason={reason}")

    if is_safe:
        return {
            "answer_harmful": False,
            "answer_harmful_reason": None,
        }

    print(f"[OutputGuard] Harmful output detected: {reason}")
    return {
        "answer_harmful": True,
        "answer_harmful_reason": reason,
        "answer": REDACTED_RESPONSE,
        "messages": [AIMessage(content=REDACTED_RESPONSE)],
    }
