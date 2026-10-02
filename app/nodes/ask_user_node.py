from app.state import state
from langgraph.types import interrupt
from langchain_core.messages import HumanMessage, AIMessage


def ask_user(graph_state: state) -> str:
    clarification_question = graph_state.clarification_question or "Could you clarify your request?"

    user_clarification = interrupt(clarification_question)

    updated_messages = [
        HumanMessage(content=user_clarification),
    ]

    return {
        'messages': updated_messages,
        'user_clarification': user_clarification,
        'ask_user_count': graph_state.ask_user_count + 1,
    }