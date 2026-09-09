from app.services.llm_service import llm_eval
from app.structured_ouput import semantic_result
from app.state import state
from app.prompts.validate_sql import validate_sql_prompt
from langchain_core.output_parsers import JsonOutputParser


def validate_sql_semantic(graph_state: state):
    print("\n========== ENTERED SEMANTIC VALIDATION ==========")
    
    question = graph_state.question
    schema = graph_state.db_schema
    user_clarification = graph_state.user_clarification or ""
    sql = graph_state.sql
    
    parser = JsonOutputParser(pydantic_object=semantic_result) 
    
    eval_chain = validate_sql_prompt | llm_eval | parser
    
    result = eval_chain.invoke({
    "question": question,
    "user_clarification": user_clarification,
    "schema": schema,
    "sql": sql,
    'format_instructions': parser.get_format_instructions()
    })
    
    print(result)
    
    return {
        'semantic_error': result['semantic_error'],
        'semantic_error_reason': result['semantic_error_reason']
    }