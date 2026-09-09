from app.state import state
from langgraph.types import interrupt



def ask_user(graph_state: state) -> str:
    
    clarification_question = graph_state.clarification_question
    
    user_clarification = interrupt(
        clarification_question
    )
    
    return {
        'user_clarification': user_clarification,
        'ask_user_count': graph_state.ask_user_count + 1
            }