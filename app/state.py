from pydantic import BaseModel, Field
from typing import Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class state(BaseModel):
    messages : Annotated[list[AnyMessage], add_messages] = Field(default_factory = list)
    
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