import re
from app.services.llm_service import llm
from app.structured_ouput import sql
from app.state import state
from app.prompts.generate_sql import generate_sql_prompt


def generate_sql(graph_state: state) -> dict:
    print("\n========== ENTERED GENERATE SQL ==========")
    # Use resolved_prompt if filters were extracted, else original question
    if graph_state.query_filters and graph_state.query_filters.resolved_prompt:
        question = graph_state.query_filters.resolved_prompt
    else:
        question = graph_state.question

    schema = graph_state.db_schema
    user_clarification = graph_state.user_clarification or ""

    format_instructions = 'Respond with a valid JSON object with a single "sql" key containing the PostgreSQL query.'

    # Attempt structured generation with json_mode (enforced by Groq)
    structured_llm = llm.with_structured_output(sql, method="json_mode")
    sql_chain = generate_sql_prompt | structured_llm

    sql_query = ""
    try:
        result = sql_chain.invoke({
            "schema": schema,
            "question": question,
            "clarification_answer": user_clarification,
            "format_instructions": format_instructions,
        })
        if hasattr(result, "sql"):
            sql_query = result.sql
        elif isinstance(result, dict):
            sql_query = result.get("sql", "")
        else:
            sql_query = str(result)
    except Exception as e:
        print(f"[generate_sql] Structured generation failed ({e}), falling back to raw LLM and extraction...")
        try:
            raw_chain = generate_sql_prompt | llm
            raw_res = raw_chain.invoke({
                "schema": schema,
                "question": question,
                "clarification_answer": user_clarification,
                "format_instructions": format_instructions,
            })
            text = raw_res.content if hasattr(raw_res, "content") else str(raw_res)
            # Try to extract SQL from markdown block or SELECT/WITH
            code_match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
            if code_match:
                sql_query = code_match.group(1).strip()
            else:
                select_match = re.search(r"((?:SELECT|WITH)\s+[\s\S]+?;?)", text, re.IGNORECASE)
                sql_query = select_match.group(1).strip() if select_match else ""
        except Exception as fallback_e:
            print(f"[generate_sql] Fallback extraction also failed: {fallback_e}")
            sql_query = ""

    print(f"[generate_sql] Final SQL: {sql_query}")
    return {"sql": sql_query.strip()}
