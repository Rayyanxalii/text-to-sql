from app.services.llm_service import llm
from app.structured_ouput import sql
from app.state import state
from app.prompts.generate_sql import generate_sql_prompt
from langchain_core.output_parsers import JsonOutputParser


def generate_sql(graph_state: state) -> dict:
    question = graph_state.question
    schema = graph_state.db_schema
    user_clarification = graph_state.user_clarification or ""
    messages = graph_state.messages
    
    parser = JsonOutputParser(pydantic_object=sql)
    sql_chain = generate_sql_prompt | llm | parser
    
    result = sql_chain.invoke({
        "schema": schema,
        "question": question,
        "clarification_answer": user_clarification,
        "messages": messages,
        "format_instructions": parser.get_format_instructions()
    })
    
    sql_query = result["sql"] if isinstance(result, dict) else result.sql
    print(sql_query)
    return {'sql': sql_query.strip()}

