from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.graph import graph_view as graph, pool
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command
from app.services.redis_service import check_semantic_cache, store_semantic_cache
from app.structured_ouput import QueryFilters


# schema = get_metadata()

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
    return {
        "message": "Text-to-SQL API is running"
    }
    


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
    return output['answer'] if 'answer' in output else 'No answer generated'



@app.post("/query")
def query_database(request: QueryRequest):
    config = {
        'configurable': {
            'thread_id': request.conversation_id
        }
    }
    
    snapshot = graph.get_state(config)
    tasks = getattr(snapshot, 'tasks', [])
    has_interrupt = any(bool(task.interrupts) for task in tasks) or bool(getattr(snapshot, 'interrupts', False))
    
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
                detail="Clarification answer required to resume the query."
            )
    else:
        # ------------------------------------------------------------------ #
        # Fresh question                                                      #
        # ------------------------------------------------------------------ #
        if request.clarification_answer:
            raise HTTPException(
                status_code=409,
                detail="No pending clarification to resume."
            )
        if not request.question:
            raise HTTPException(
                status_code=400,
                detail="Question is required for a new query."
            )

        # --- Semantic cache check (pre-graph) ---
        # Use the raw question with empty filters for the initial lookup.
        # The extract_filters node will produce the precise filters later;
        # here we rely purely on vector similarity + empty-filter match so
        # only previously-cached identical-intent AND identical-value queries
        # are served from cache.
        raw_filters = QueryFilters(resolved_prompt=request.question)
        cached_answer = check_semantic_cache(request.question, raw_filters)

        if cached_answer:
            print("[Cache HIT] Returning cached answer without running graph.")
            return format_graph_output({"answer": cached_answer}, request.conversation_id)

        print("[Cache MISS] Running full graph pipeline.")
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
        }
        result = graph.invoke(initial_state, config=config)

    # ---------------------------------------------------------------------- #
    # Store in semantic cache (both fresh and resumed paths land here)        #
    # ---------------------------------------------------------------------- #
    if isinstance(result, dict):
        answer = result.get("answer", "")
        qf: QueryFilters | None = result.get("query_filters")

        # Only cache when we have a real answer and extracted filters.
        # If the graph was interrupted (clarification pending) qf will be None
        # and we skip caching until the final answer is produced.
        if answer and qf:
            store_semantic_cache(
                resolved_prompt=qf.resolved_prompt,
                answer=answer,
                qf=qf,
            )

    return format_graph_output(result, request.conversation_id)


