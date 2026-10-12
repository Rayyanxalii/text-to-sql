from app.state import state
from app.guardrails.sql_safety import validate_sql_safety


def sql_safety_node(s: state) -> dict:
    print("\n========== ENTERED SQL SAFETY NODE ==========")
    """
    Validates the generated SQL against structural / read-only safety rules
    using sqlglot (no database round-trip required).
    """
    is_safe, reason = validate_sql_safety(s.sql)

    return {
        "sql_valid": is_safe,
        "sql_valid_error": None if is_safe else reason,
    }
