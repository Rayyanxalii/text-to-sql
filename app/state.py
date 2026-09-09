from pydantic import BaseModel


class state(BaseModel):
    question: str

    clarification_question: str | None = None
    clarification_reason: str | None = None
    user_clarification: str | None = None

    is_clear: bool = False

    db_schema: str = ""
    sql: str = ""

    sql_valid: bool = False
    sql_valid_error: str | None = None

    ask_user_count: int = 0
    correct_sql_count: int = 0

    semantic_error: bool | None = None
    semantic_error_reason: str | None = None

    db_result: list[tuple] = []
    sql_execution_error: str | None = None

    answer: str = ""