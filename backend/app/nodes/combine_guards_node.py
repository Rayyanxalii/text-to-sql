from app.state import state


def combine_guards_node(graph_state: state) -> dict:
    """
    Fan-in node that merges the parallel outputs of input_guard (regex)
    and meta_guard (DeBERTa model).
    """
    print("\n========== ENTERED COMBINE GUARDS ==========")

    regex_safe = graph_state.regex_safe
    model_safe = graph_state.model_safe

    is_safe = regex_safe and model_safe
    reason = None

    if not regex_safe:
        reason = graph_state.regex_reason
    elif not model_safe:
        reason = reason + graph_state.model_reason

    print(
        f"[CombineGuards] regex_safe={regex_safe}, "
        f"model_safe={model_safe} -> input_safe={is_safe}, reason={reason}"
    )

    return {
        "input_safe": is_safe,
        "input_safe_reason": reason,
    }
