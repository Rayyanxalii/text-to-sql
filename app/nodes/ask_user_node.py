from app.state import state


def ask_user(graph_state: state) -> str:
    
    clarification_question = graph_state['clarification_question']
    
    user_clarification = input(f"Your Query is unclear. Please answer the following question to clarify your intent:\n{clarification_question}\nYour Answer: ")
    
    return {'user_clarification': user_clarification,
            'ask_user_count': graph_state['ask_user_count'] + 1
            }