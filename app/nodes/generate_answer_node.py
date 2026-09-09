from app.services.llm_service import llm
from app.structured_ouput import sql
from app.state import state
from app.prompts.generate_answer import generate_answer_prompt



def generate_answer(graph_state: state) -> str:
    
    db_result =  graph_state.db_result
    question = graph_state.question
    user_clarification = graph_state.user_clarification or ""
    
    
    llm_chain =  generate_answer_prompt | llm
    
    answer = llm_chain.invoke({
        'question': question,
        'db_result' : db_result,
        'user_clarification': user_clarification
    })
    
    return {'answer' : answer}
    
    






    

