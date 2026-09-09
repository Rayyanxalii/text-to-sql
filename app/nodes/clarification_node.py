from app.services.llm_service import llm
from app.structured_ouput import ClarificationResult
from app.state import state
from app.prompts.clarification import clarification_prompt

def clarification_node(graph_state: state) -> str:
      
    question = graph_state.question
    schema = graph_state.db_schema
    user_clarification = graph_state.user_clarification or ""
    messages = graph_state.messages
    
        
    structured_llm =  llm.with_structured_output(ClarificationResult)
    
    clarification_chain = clarification_prompt | structured_llm 
    
    result = clarification_chain.invoke({
    "schema": schema,
    "question": question,
    "user_clarification": user_clarification,
    'messages' : messages
})
    
    print(result)
    
    return {
        "is_clear": result.is_clear,
        "clarification_question": result.clarification_question,
        "clarification_reason": result.reason
    }