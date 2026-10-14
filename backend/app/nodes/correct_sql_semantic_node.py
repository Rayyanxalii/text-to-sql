import re
from app.services.llm_service import llm
from app.structured_ouput import sql
from app.state import state
from app.prompts.correct_sql_semantic import correct_sql_semantic_prompt


def clean_sql(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    text = re.sub(r"^\s*EXPLAIN(\s+ANALYZE|\s+VERBOSE)?\s+", "", text, flags=re.IGNORECASE).strip()
    return text


def correct_sql_semantic(graph_state: state) -> dict:
    print("\n========== ENTERED CORRECT SQL SEMANTIC ==========")

    question = graph_state.question
    schema = graph_state.db_schema
    user_clarification = graph_state.user_clarification or ""
    current_sql = graph_state.sql
    semantic_error_reason = graph_state.semantic_error_reason or "The query does not match the user's intent."

    print(f"[correct_sql_semantic] Flawed SQL: {current_sql}")
    print(f"[correct_sql_semantic] Reason: {semantic_error_reason}")
    print(f"[correct_sql_semantic] Attempt: {graph_state.correct_semantic_count + 1} of 2")

    format_instructions = 'Respond with a valid JSON object with a single "sql" key containing the corrected PostgreSQL query.'

    structured_llm = llm.with_structured_output(sql, method="json_mode")
    chain = correct_sql_semantic_prompt | structured_llm

    corrected_query = ""
    try:
        result = chain.invoke({
            "schema": schema,
            "question": question,
            "user_clarification": user_clarification,
            "sql": current_sql,
            "semantic_error_reason": semantic_error_reason,
            "format_instructions": format_instructions,
        })
        if hasattr(result, "sql"):
            corrected_query = result.sql
        elif isinstance(result, dict):
            corrected_query = result.get("sql", "")
        else:
            corrected_query = str(result)
    except Exception as e:
        print(f"[correct_sql_semantic] Structured invocation failed ({e}), falling back to raw LLM...")
        try:
            raw_chain = correct_sql_semantic_prompt | llm
            raw_res = raw_chain.invoke({
                "schema": schema,
                "question": question,
                "user_clarification": user_clarification,
                "sql": current_sql,
                "semantic_error_reason": semantic_error_reason,
                "format_instructions": format_instructions,
            })
            text = raw_res.content if hasattr(raw_res, "content") else str(raw_res)
            corrected_query = clean_sql(text)
        except Exception as fallback_e:
            print(f"[correct_sql_semantic] Fallback failed: {fallback_e}")
            corrected_query = current_sql

    corrected_query = clean_sql(corrected_query)
    print(f"[correct_sql_semantic] Corrected SQL: {corrected_query}")

    return {
        "sql": corrected_query,
        "correct_semantic_count": graph_state.correct_semantic_count + 1,
    }
