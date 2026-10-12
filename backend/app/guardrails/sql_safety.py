
import sqlglot
from sqlglot import exp


FORBIDDEN_NODE_TYPES = {
    "insert",
    "update",
    "delete",
    "merge",
    "create",
    "drop",
    "alter",
    "command",
    "copy",
    "truncate",
    "truncatetable",
    "grant",
    "revoke",
    "set",
    "use",
    "transaction",
    "commit",
    "rollback",
    "into",
    "lock",
    "call",
    "execute",
    "vacuum",
    "attach",
    "detach",
    "pragma",
    "analyze",
}


def validate_sql_safety(sql: str) -> tuple[bool, str]:
    """
    Check whether generated SQL follows the project's
    basic read-only SQL rules.

    Returns:
        (True, "") if the query passes these checks.
        (False, reason) if the query is rejected.
    """

    # 1. Reject empty SQL.
    if not sql or not sql.strip():
        return False, "SQL query is empty."

    # 2. Parse SQL using PostgreSQL syntax.
    try:
        statements = [
            statement
            for statement in sqlglot.parse(sql, read="postgres")
            if statement is not None
        ]

    except sqlglot.errors.ParseError as exc:
        return False, f"SQL parsing failed: {exc}"

    # 3. Allow exactly one SQL statement.
    if len(statements) != 1:
        return False, "Exactly one SQL statement is allowed."

    statement = statements[0]

    # 4. Allow only SELECT as the main statement.
    if not isinstance(statement, exp.Select):
        return False, "Only SELECT queries are allowed."

    # 5. Inspect the entire SQL syntax tree.
    # This includes nested queries and CTEs.
    for node in statement.walk():
        node_type = node.key.lower()
        class_name = node.__class__.__name__.lower()

        if (
            node_type in FORBIDDEN_NODE_TYPES
            or class_name in FORBIDDEN_NODE_TYPES
        ):
            return (
                False,
                f"Prohibited SQL construct detected: {class_name}",
            )

    # 6. The query passed these structural checks.
    return True, ""
