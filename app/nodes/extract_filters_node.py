from langchain_core.prompts import ChatPromptTemplate
from app.services.llm_service import llm
from app.structured_ouput import QueryFilters
from app.state import state


_EXTRACT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are a precise information extractor. "
            "Given the user's original question and any clarification they provided, "
            "extract the following into the structured output:\n"
            "  • years          – four-digit years explicitly mentioned\n"
            "  • numbers        – other numeric values (counts, amounts, IDs) excluding years\n"
            "  • entities       – named entities: wards, doctors, departments, diagnoses, etc.\n"
            "  • date_ranges    – date range expressions like 'Q1 2025', 'last 6 months'\n"
            "  • resolved_prompt – a single self-contained sentence that fully captures "
            "the user's intent after incorporating all clarifications. "
            "This will be used as the semantic cache key, so be specific and complete."
        ),
    ),
    (
        "human",
        (
            "Original question: {question}\n"
            "User clarification (if any): {user_clarification}\n\n"
            "Extract the filters and write the resolved_prompt. "
            "Respond with a JSON object with these exact keys: "
            "\"years\" (list of ints), \"numbers\" (list of floats), "
            "\"entities\" (list of strings), \"date_ranges\" (list of strings), "
            "\"resolved_prompt\" (string)."
        ),
    ),
])

_extractor = _EXTRACT_PROMPT | llm.with_structured_output(QueryFilters, method="json_mode")


def extract_query_filters(graph_state: state) -> dict:
    """
    LangGraph node that runs after clarification is resolved.
    Extracts structured filters from the final question + clarification,
    and stores them in state so the cache layer can use them.
    """
    result: QueryFilters = _extractor.invoke({
        "question": graph_state.question,
        "user_clarification": graph_state.user_clarification or "",
    })

    print(f"[FilterExtractor] {result}")

    return {"query_filters": result}
