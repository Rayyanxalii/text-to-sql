from app.guardrails.input_guard import input_guardrail
from app.state import state


def input_guard_node(graph_state: state) -> dict:
    print("\n========== ENTERED INPUT GUARD ==========")
    # When returning from ask_user, validate the user's clarification.
    # Otherwise, validate the original user question.
    if graph_state.user_clarification:
        text_to_check = graph_state.user_clarification
        print(f"[InputGuard] Validating user clarification: {text_to_check!r}")
    else:
        text_to_check = graph_state.question
        print(f"[InputGuard] Validating user question: {text_to_check!r}")

    result = input_guardrail(text_to_check)
    print(f"[InputGuard] is_safe={result['is_safe']}, is_greeting={result['is_greeting']}, reason={result['is_safe_reason']}")

    return {
        "input_safe": result["is_safe"],
        "input_safe_reason": result["is_safe_reason"],
        "is_greeting": result["is_greeting"],
    }