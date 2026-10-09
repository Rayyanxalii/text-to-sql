from app.services.llm_service import llm_eval
from app.structured_ouput import semantic_result
from app.state import state
from app.prompts.validate_sql import validate_sql_prompt
from langchain_core.output_parsers import JsonOutputParser


def validate_sql_semantic(graph_state: state):
    print("\n========== ENTERED SEMANTIC VALIDATION ==========")

    question = graph_state.question
    schema = graph_state.db_schema
    user_clarification = graph_state.user_clarification or ""
    sql = graph_state.sql

    parser = JsonOutputParser(pydantic_object=semantic_result)

    try:
        eval_chain = validate_sql_prompt | llm_eval | parser
        result = eval_chain.invoke({
            "question": question,
            "user_clarification": user_clarification,
            "schema": schema,
            "sql": sql,
            "format_instructions": parser.get_format_instructions(),
        })
        semantic_err = result.get("semantic_error", False) if isinstance(result, dict) else getattr(result, "semantic_error", False)
        semantic_err_reason = result.get("semantic_error_reason", None) if isinstance(result, dict) else getattr(result, "semantic_error_reason", None)
    except Exception as e:
        print(f"[validate_sql_semantic] Evaluation parsing failed ({e}). Defaulting to semantic_error=False.")
        semantic_err = False
        semantic_err_reason = None

    print(f"[validate_sql_semantic] semantic_error={semantic_err}, reason={semantic_err_reason}")

    return {
        "semantic_error": semantic_err,
        "semantic_error_reason": semantic_err_reason,
    }