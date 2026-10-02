import re
from app.services.llm_service import llm
from app.state import state
from app.prompts.correct_sql import correct_sql_prompt


def clean_sql(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


def correct_sql_syntax(graph_state: state) -> dict:
    question = graph_state.question
    schema = graph_state.db_schema
    user_clarification = graph_state.user_clarification or ""
    sql = graph_state.sql
    sql_valid_error = graph_state.sql_valid_error
    
    correct_sql_chain = correct_sql_prompt | llm 
    
    corrected_sql_result = correct_sql_chain.invoke({
        "schema": schema,
        "question": question,
        "user_clarification": user_clarification,
        "sql": sql,
        "sql_valid_error": sql_valid_error
    })
    
    raw_content = corrected_sql_result.content if hasattr(corrected_sql_result, "content") else str(corrected_sql_result)
    
    return {
        'sql': clean_sql(raw_content),
        'correct_sql_count': graph_state.correct_sql_count + 1
    }