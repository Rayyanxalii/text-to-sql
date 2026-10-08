from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.graph import graph_view as graph, pool
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from app.services.redis_service import store_semantic_cache
from app.structured_ouput import QueryFilters


app = FastAPI(
    title="Text-to-SQL API",
    description="Natural language to SQL system",
    version="1.0.0",
)


@app.on_event("startup")
def startup_event():
    print("Starting up the Text-to-SQL")


@app.on_event("shutdown")
def shutdown_event():
    pool.close()


class QueryRequest(BaseModel):
    question: str | None = None
    clarification_answer: str | None = None
    conversation_id: str


@app.get("/")
def root():
    return {"message": "Text-to-SQL API is running"}


def format_graph_output(result, conversation_id: str):
    if not isinstance(result, dict):
        if hasattr(result, "model_dump"):
            result_dict = result.model_dump()
        elif hasattr(result, "__dict__"):
            result_dict = result.__dict__
        else:
            result_dict = {"output": result}
    else:
        result_dict = result

    interrupts = result_dict.get("__interrupt__")
    if interrupts:
        interrupt_item = interrupts[0]
        clarification_q = (
            interrupt_item.value
            if hasattr(interrupt_item, "value")
            else str(interrupt_item)
        )
        return {
            "conversation_id": conversation_id,
            "requires_clarification": True,
            "clarification_question": clarification_q,
        }

    output = dict(result_dict)
    output["conversation_id"] = conversation_id
    output["requires_clarification"] = False
    return output["answer"] if "answer" in output else "No answer generated"


@app.post("/query")
def query_database(request: QueryRequest):
    config = {
        "configurable": {
            "thread_id": request.conversation_id
        }
    }

    snapshot = graph.get_state(config)
    tasks = getattr(snapshot, "tasks", [])
    has_interrupt = any(bool(task.interrupts) for task in tasks) or bool(
        getattr(snapshot, "interrupts", False)
    )

    if has_interrupt:
        # ------------------------------------------------------------------ #
        # Resuming after a clarification interrupt                            #
        # ------------------------------------------------------------------ #
        if request.clarification_answer:
            command = Command(resume=request.clarification_answer)
            result = graph.invoke(command, config=config)
        else:
            raise HTTPException(
                status_code=422,
                detail="Clarification answer required to resume the query.",
            )
    else:
        # ------------------------------------------------------------------ #
        # Fresh question                                                      #
        # ------------------------------------------------------------------ #
        if request.clarification_answer:
            raise HTTPException(
                status_code=409,
                detail="No pending clarification to resume.",
            )
        if not request.question:
            raise HTTPException(
                status_code=400,
                detail="Question is required for a new query.",
            )

        initial_state = {
            "question": request.question,
            "messages": [HumanMessage(content=request.question)],
            "user_clarification": None,
            "clarification_question": None,
            "clarification_reason": None,
            "is_clear": False,
            "sql": "",
            "sql_valid": False,
            "sql_valid_error": None,
            "ask_user_count": 0,
            "correct_sql_count": 0,
            "semantic_error": None,
            "semantic_error_reason": None,
            "db_result": None,
            "sql_execution_error": None,
            "answer": "",
            "query_filters": None,
            "cache_hit": False,
        }
        result = graph.invoke(initial_state, config=config)

    # ---------------------------------------------------------------------- #
    # Store in semantic cache — only when the graph ran SQL generation        #
    # (cache_hit=False means a fresh answer was produced, not served from     #
    # cache). Also skip if graph was interrupted waiting for clarification.   #
    # ---------------------------------------------------------------------- #
    if isinstance(result, dict):
        answer = result.get("answer", "")
        qf: QueryFilters | None = result.get("query_filters")
        cache_hit: bool = result.get("cache_hit", False)

        if answer and qf and not cache_hit:
            store_semantic_cache(
                resolved_prompt=qf.resolved_prompt,
                answer=answer,
                qf=qf,
            )

    return format_graph_output(result, request.conversation_id)



