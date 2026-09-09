from pydantic import BaseModel, Field


class ClarificationResult(BaseModel):
    is_clear: bool = Field(
        description="Whether the user's question contains enough information to generate SQL."
    )
    clarification_question: str | None = Field(
        description="A question to ask the user if the request is unclear."
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
    
    semantic_error_reason : str | None = Field( description="A brief explanation of the semantic error in the SQL query.")
    
