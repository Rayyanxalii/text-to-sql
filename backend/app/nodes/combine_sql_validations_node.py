from app.state import state


def combine_sql_validations_node(graph_state: state) -> dict:
    """
    Fan-in node that merges the parallel outputs of:
    1. sql_safety (AST structural check via sqlglot)
    2. validate_sql_syntax (PostgreSQL EXPLAIN check)
    3. validate_sql_semantic (LLM semantic evaluation)
    """
    print("\n========== ENTERED COMBINE SQL VALIDATIONS ==========")

    ast_safe = graph_state.ast_safe
    ast_error = graph_state.ast_error
    syntax_valid = graph_state.syntax_valid
    syntax_error = graph_state.syntax_error
    permission_denied = graph_state.permission_denied
    semantic_error = graph_state.semantic_error
    semantic_error_reason = graph_state.semantic_error_reason

    print(
        f"[CombineSQLValidations] ast_safe={ast_safe}, "
        f"syntax_valid={syntax_valid}, permission_denied={permission_denied}, "
        f"semantic_error={semantic_error}",
        f"semantic_error_reason={semantic_error_reason}"
    )

    if not ast_safe:
        return {
            "sql_valid": False,
            "sql_valid_error": ast_error or "Prohibited SQL construct detected.",
            "permission_denied": False,
        }

    if permission_denied:
        return {
            "sql_valid": False,
            "sql_valid_error": 'Permission denied',
            "permission_denied": True,
        }

    if not syntax_valid:
        return {
            "sql_valid": False,
            "sql_valid_error": syntax_error,
            "permission_denied": False,
        }

    return {
        "sql_valid": True,
        "sql_valid_error": None,
        "permission_denied": False,
    }


def route_after_sql_validation(graph_state: state) -> str:
    """
    Evaluates merged validation flags and determines the next step.
    Priority:
    1. AST security violation -> generate_answer (rejection)
    2. Permission denied -> generate_answer (rejection)
    3. Syntax error -> correct_sql_syntax (up to 3 attempts)
    4. Semantic error -> correct_sql_semantic (up to 2 attempts)
    5. All valid -> execute_sql
    """
    # 1. AST security check failed (sqlglot)
    if not graph_state.ast_safe:
        print("[route_after_sql_validation] AST security violation -> routing to generate_answer.")
        return "generate_answer"

    # 2. Permission denied by database
    if graph_state.permission_denied:
        print("[route_after_sql_validation] Permission denied -> routing to generate_answer.")
        return "generate_answer"

    # 3. PostgreSQL syntax error (EXPLAIN failed)
    if not graph_state.syntax_valid:
        if graph_state.correct_sql_count < 3:
            print(f"[route_after_sql_validation] Syntax error -> routing to correct_sql_syntax (attempt {graph_state.correct_sql_count + 1} of 3).")
            return "correct_sql_syntax"
        print("[route_after_sql_validation] Syntax retries exhausted -> routing to generate_answer.")
        return "generate_answer"

    # 4. Semantic error (intent mismatch)
    if graph_state.semantic_error and graph_state.correct_semantic_count < 2:
        print(f"[route_after_sql_validation] Semantic error -> routing to correct_sql_semantic (attempt {graph_state.correct_semantic_count + 1} of 2).")
        return "correct_sql_semantic"

    # 5. All valid (or exhausted semantic retries) -> execute SQL
    print("[route_after_sql_validation] Validations passed -> routing to execute_sql.")
    return "execute_sql"
