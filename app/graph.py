import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from langgraph.graph import StateGraph, START, END
from app.state import state
from app.querying_db import execute_sql, validate_sql_syntax 
from app.nodes.generate_answer_node import  generate_answer
from app.nodes.clarification_node  import clarification_node
from app.nodes.generate_sql_node import generate_sql
from app.nodes.ask_user_node import ask_user
from app.nodes.correct_sql_syntax_node import correct_sql_syntax
from app.nodes.validate_sql_semantic_node import validate_sql_semantic
from app.nodes.extract_filters_node import extract_query_filters
from app.nodes.check_cache_node import check_cache_node
from app.nodes.input_guard_node import input_guard_node
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
import os
from dotenv import load_dotenv
load_dotenv()



DB_URI = os.getenv("DB_URI")

    

graph = StateGraph(state)

graph.add_node("clarification", clarification_node)
graph.add_node("ask_user", ask_user)
graph.add_node("extract_filters", extract_query_filters)
graph.add_node("check_cache", check_cache_node)           
graph.add_node('generate_answer', generate_answer)
graph.add_node('generate_sql', generate_sql)
graph.add_node('validate_sql_syntax', validate_sql_syntax)
graph.add_node('correct_sql_syntax', correct_sql_syntax)
graph.add_node('validate_sql_semantic', validate_sql_semantic)
graph.add_node('execute_sql', execute_sql)
graph.add_node('input_guard', input_guard_node) 


graph.add_edge(START, 'input_guard')
graph.add_conditional_edges(
    "input_guard",
    lambda x: "clarification" if x.input_safe and not x.is_greeting else "generate_answer",
    {
        "clarification": "clarification",
        "generate_answer": "generate_answer",
    }
)

graph.add_conditional_edges(
    "clarification",
    lambda x: "extract_filters" if x.is_clear == True or x.ask_user_count >= 3 else "ask_user",
    {
        "ask_user": "ask_user",
        "extract_filters": "extract_filters",
    }
)
graph.add_edge("ask_user", "input_guard")

# extract_filters → check_cache
graph.add_edge("extract_filters", "check_cache")

# check_cache → END (hit) or generate_sql (miss)
graph.add_conditional_edges(
    "check_cache",
    lambda x: END if x.cache_hit else "generate_sql",
    {
        END: END,
        "generate_sql": "generate_sql",
    }
)

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

graph.add_edge('validate_sql_semantic', 'execute_sql')
graph.add_edge('execute_sql', 'generate_answer')
graph.add_edge('generate_answer', END)


pool = ConnectionPool(
    conninfo=DB_URI,
    max_size=20,
    kwargs={"autocommit": True, "prepare_threshold": 0},
)

checkpointer = PostgresSaver(pool)
checkpointer.setup()

graph_view = graph.compile(checkpointer=checkpointer)

png_data = graph_view.get_graph().draw_mermaid_png()


with open("graph.png", "wb") as f:
    f.write(png_data)
    
