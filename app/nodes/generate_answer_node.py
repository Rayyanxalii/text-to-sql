from app.services.llm_service import llm
from app.structured_ouput import sql
from app.state import state
from app.prompts.generate_answer import generate_answer_prompt
from langchain_core.messages import AIMessage


def generate_answer(graph_state: state):
    print("\n========== ENTERED GENERATE ANSWER ==========")

    question = graph_state.question
    db_result = graph_state.db_result
    user_clarification = graph_state.user_clarification or ""
    input_safe = graph_state.input_safe
    input_safe_reason = graph_state.input_safe_reason
    is_greeting = graph_state.is_greeting
    sql_execution_error = graph_state.sql_execution_error

    # 1. Greetings: return a friendly greeting immediately without an expensive/brittle LLM call
    if is_greeting:
        greeting_text = (
            "Hello! I'm your hospital data assistant. "
            "Feel free to ask me any questions about the hospital database."
        )
        return {
            "answer": greeting_text,
            "messages": [AIMessage(content=greeting_text)],
        }

    # 2. Blocked inputs: return a clear, polite rejection message immediately
    if not input_safe:
        rejection_text = (
            "I'm sorry, but I cannot process this request as it contains "
            "restricted instructions or violates safety guidelines."
        )
        return {
            "answer": rejection_text,
            "messages": [AIMessage(content=rejection_text)],
        }

    # 3. For database queries, use a sliding window of recent messages (last 10)
    # to avoid context bloating and safety-filter poisoning from old turns.
    recent_messages = graph_state.messages[-10:] if graph_state.messages else []

    try:
        llm_chain = generate_answer_prompt | llm
        answer = llm_chain.invoke({
            "question": question,
            "db_result": db_result,
            "user_clarification": user_clarification,
            "sql_execution_error": sql_execution_error,
            "messages": recent_messages,
        })
        content = answer.content if hasattr(answer, "content") else str(answer)
        if not content.strip():
            if db_result is not None:
                content = f"Query executed successfully. Result: {db_result}"
            else:
                content = "No matching records were found."
    except Exception as e:
        print(f"[generate_answer] LLM call failed ({e}). Using direct database result fallback.")
        if sql_execution_error:
            content = f"The query could not be executed: {sql_execution_error}"
        elif db_result is not None:
            if len(db_result) == 1 and len(db_result[0]) == 1:
                content = f"The query returned: {db_result[0][0]}"
            else:
                content = f"The query returned {len(db_result)} record(s): {db_result[:5]}"
        else:
            content = "I could not retrieve an answer for this request."

    return {
        "answer": content,
        "messages": [AIMessage(content=content)],
    }
