from app.guardrails.input_guard import input_guardrail
from app.state import state


def input_guard_node(graph_state: state) -> dict:
    print("\n========== ENTERED INPUT GUARD ==========")
    result = input_guardrail(graph_state.question)

    return {
        "input_safe": result["is_safe"],
        "input_safe_reason": result["is_safe_reason"],
        "is_greeting": result["is_greeting"],
    }