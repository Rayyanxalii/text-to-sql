from app.services.llm_service import llm
from app.structured_ouput import sql
from app.state import state
from app.prompts.correct_sql import correct_sql_prompt



def correct_sql_syntax(graph_state: state) -> str:
    
    question = graph_state.question

    schema = graph_state.db_schema

    user_clarification = graph_state.user_clarification or ""

    sql = graph_state.sql

    sql_valid_error = graph_state.sql_valid_error

     
    structured_llm = llm.with_structured_output(sql)
    
    correct_sql_chain = correct_sql_prompt | structured_llm
    
    corrected_sql_result = correct_sql_chain.invoke({
    "schema": schema,
    "question": question,
    "user_clarification": user_clarification,
    "sql": sql,
    "sql_valid_error": sql_valid_error
    })
    
    return {
        'sql': corrected_sql_result.sql,
        'correct_sql_count': graph_state.correct_sql_count + 1
    }