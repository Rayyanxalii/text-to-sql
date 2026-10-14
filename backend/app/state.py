from pydantic import BaseModel, Field
from typing import Annotated, Optional
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from app.services.schema_service import get_metadata
from app.structured_ouput import QueryFilters

metadata = get_metadata()

class state(BaseModel):
    messages : Annotated[list[AnyMessage], add_messages] = Field(default_factory = list)
    
    question: str

    clarification_question: str | None = None
    clarification_reason: str | None = None
    user_clarification: str | None = None

    is_clear: bool = False

    db_schema: str = metadata
    sql: str = ""

    # Distinct fields for parallel SQL validations
    ast_safe: bool = True
    ast_error: str | None = None

    syntax_valid: bool = True
    syntax_error: str | None = None

    # Combined SQL validation state
    sql_valid: bool = False
    sql_valid_error: str | None = None

    ask_user_count: int = 0
    correct_sql_count: int = 0
    correct_semantic_count: int = 0

    semantic_error: bool | None = None
    semantic_error_reason: str | None = None

    db_result: list[tuple] | None = None
    sql_execution_error: str | None = None

    answer: str = ""

    # Populated by extract_filters_node after clarification is resolved.
    # Used by check_cache_node for lookup and by main.py for storing.
    query_filters: Optional[QueryFilters] = None

    # Set by check_cache_node. True = answer already populated from cache,
    # graph should jump to END. False = proceed to generate_sql.
    cache_hit: bool = False
    
    
    # Individual guardrail outputs for parallel execution
    regex_safe: bool = True
    regex_reason: str | None = None
    is_greeting: bool = False

    model_safe: bool = True
    model_reason: str | None = None

    # Combined input safety state
    input_safe : bool = False
    input_safe_reason : str | None = None
    
    permission_denied : bool = False
    
    answer_harmful : bool = False
    answer_harmful_reason : str | None = None
    
    