from app.services.llm_service import llm
from app.structured_ouput import sql
from app.state import state
from app.prompts.generate_sql import generate_sql_prompt


def generate_sql(graph_state: state) -> str:
    
    question = graph_state.question
    schema = graph_state.db_schema
    user_clarification = graph_state.user_clarification or ""
    
    
    structured_llm = llm.with_structured_output(sql)
    
    sql_chain = generate_sql_prompt | structured_llm
    
    result = sql_chain.invoke({
    "schema": schema,
    "question": question,
    "clarification_answer": user_clarification
    })
    
    return {'sql': result.sql}