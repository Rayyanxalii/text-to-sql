from app.guardrails.meta_guard import check_meta_guard
from app.state import state


def meta_guard_node(graph_state: state) -> dict:
    """
    Model-based prompt injection guard node (DeBERTa).
    Evaluates the question (or clarification) using meta_guard classifier.
    Sets input_safe and input_safe_reason on graph state.
    """
    print("\n========== ENTERED META GUARD ==========")

    # Check clarification if returning from ask_user, otherwise original question
    if graph_state.user_clarification:
        text_to_check = graph_state.user_clarification
        print(f"[MetaGuard] Evaluating user clarification: {text_to_check!r}")
    else:
        text_to_check = graph_state.question
        print(f"[MetaGuard] Evaluating user question: {text_to_check!r}")

    result = check_meta_guard(text_to_check)
    print(f"[MetaGuard] is_safe={result['is_safe']}, label={result['label']}, score={result['score']:.4f}")

    return {
        "input_safe": result["is_safe"],
        "input_safe_reason": result["reason"],
    }
