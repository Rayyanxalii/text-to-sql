from langgraph.graph import StateGraph, START, END

from app.state import state
from app.querying_db import execute_sql, validate_sql_syntax 
from app.services.schema_service import get_metadata
from app.nodes.generate_answer_node import  generate_answer
from app.nodes.clarification_node  import clarification_node
from app.nodes.generate_sql_node import generate_sql
from app.nodes.ask_user_node import ask_user
from app.nodes.correct_sql_syntax_node import correct_sql_syntax
from app.nodes.validate_sql_semantic_node import validate_sql_semantic
from app.services.schema_service import get_metadata


db_schema = get_metadata()
    

graph = StateGraph(state)

graph.add_node("clarification", clarification_node)
graph.add_node("ask_user", ask_user)
graph.add_node('generate_answer',generate_answer )
graph.add_node('generate_sql', generate_sql)
graph.add_node('validate_sql_syntax', validate_sql_syntax)
graph.add_node('correct_sql_syntax', correct_sql_syntax)
graph.add_node('validate_sql_semantic', validate_sql_semantic)
graph.add_node('execute_sql', execute_sql)


graph.add_edge(START, 'clarification')
graph.add_conditional_edges(
    "clarification",
    lambda x : "generate_sql" if x.is_clear == True or x.ask_user_count >= 3 else "ask_user",
    {
        "ask_user": "ask_user",
        "generate_sql": "generate_sql",
    }
)
graph.add_edge("ask_user", "clarification")



graph.add_edge('generate_sql', 'validate_sql_syntax')
graph.add_conditional_edges(
    "validate_sql_syntax",
    lambda x: "correct_sql_syntax" if x.sql_valid == False and x.correct_sql_count < 3 else "validate_sql_semantic",
    {
        "correct_sql_syntax": "correct_sql_syntax",
        "validate_sql_semantic": "validate_sql_semantic"
    }
)
graph.add_edge('correct_sql_syntax', 'validate_sql_syntax')

# graph.add_conditional_edges(
#     "correct_sql_semantic",
#     lambda x: "correct_sql_semantic" if x["semantic_error"] == True or x['correct_sql_count'] >= 3 else "generate_answer",
#     {
#         "correct_sql_semantic": "correct_sql_semantic",
        
#     }
    
# )


graph.add_edge('validate_sql_semantic', 'execute_sql')
graph.add_edge('execute_sql', 'generate_answer')
graph.add_edge('generate_answer', END)


graph_view = graph.compile()


# png_data = graph_view.get_graph().draw_mermaid_png()


# with open("graph.png", "wb") as f:
#     f.write(png_data)
    
    
# result = graph_view.invoke({
#     "question": "Give record of all doctors",
#     'is_clear': False,
#     'schema': db_schema,
#     'ask_user_count': 0,
#     'correct_sql_count': 0
# })

# print(result['answer'].content)