from app.services.llm_service import llm
from app.structured_ouput import ClarificationResult
from app.state import state
from app.prompts.clarification import clarification_prompt
from langchain_core.messages import AIMessage

def clarification_node(graph_state: state) -> str:
      
    clarification_question = graph_state.clarification_question
    schema = graph_state.db_schema
    user_clarification = graph_state.user_clarification or ""
    messages = graph_state.messages
    question = graph_state.question
        
    structured_llm = llm.with_structured_output(ClarificationResult)
    
    clarification_chain = clarification_prompt | structured_llm 
    
    result = clarification_chain.invoke({
    "schema": schema,
    'question':question,
    "clarification_question": clarification_question if clarification_question else "",
    "user_clarification": user_clarification if user_clarification else "",
    'messages' : messages
})
    
    print(result)

    return {
        "is_clear": result.is_clear,
        "clarification_question": result.clarification_question,
        'messages': [AIMessage(content=result.clarification_question)] if result.clarification_question else [],
        "clarification_reason": result.reason
    }