from pydantic import BaseModel, Field


class ClarificationResult(BaseModel):
    is_clear: bool = Field(
        description="Whether the user's question contains enough information to generate SQL."
    )
    clarification_question: str | None = Field(
        default=None,
        description="A question to ask the user if the request is unclear. Must be None if is_clear is True."
    )
    reason: str = Field(
        description="Brief explanation of why the question is clear or unclear."
    )
    
    
    
class sql(BaseModel):
    sql : str = Field(
        description="The SQL query generated from the user's question.")
    
    
    
    

class semantic_result(BaseModel):
    semantic_error : bool = Field(
        description="Whether there was a semantic error in the SQL query.")
    
    semantic_error_reason : str | None = Field(
        default=None,
        description="A brief explanation of the semantic error in the SQL query. Must be None if semantic_error is False."
    )




class QueryFilters(BaseModel):
    """
    Structured filters extracted from a user's (possibly clarified) question.
    Used as metadata tags when storing/checking the semantic cache so that
    queries that are semantically similar but differ in concrete values
    (e.g. year 2025 vs 2026) are never treated as cache hits.
    """
    years: list[int] = Field(
        default_factory=list,
        description="All four-digit year values explicitly mentioned in the question, e.g. [2025, 2026]."
    )
    numbers: list[float] = Field(
        default_factory=list,
        description="Any other numeric values (counts, amounts, IDs) mentioned, excluding years."
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Named entities such as ward names, doctor names, department names, or diagnosis types."
    )
    date_ranges: list[str] = Field(
        default_factory=list,
        description="Any date range expressions such as 'Q1 2025', 'January 2026', 'last 6 months'."
    )
    resolved_prompt: str = Field(
        description=(
            "A single, complete, self-contained restatement of what the user is asking, "
            "fully incorporating any clarifications provided. "
            "This is the canonical string stored as the cache key."
        )
    )
    





