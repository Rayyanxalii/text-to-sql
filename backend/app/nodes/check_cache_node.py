from app.state import state
from app.services.redis_service import check_semantic_cache


def check_cache_node(graph_state: state) -> dict:
    """
    LangGraph node that runs after extract_filters.

    Uses the fully-resolved prompt and structured filters (already in state)
    to query the semantic cache.

    State updates returned:
      • cache_hit = True  + answer = <cached string>  → conditional edge routes to END
      • cache_hit = False                             → conditional edge routes to generate_sql
    """
    print("\n========== ENTERED CHECK CACHE ==========")
    qf = graph_state.query_filters

    # Safety: if filters weren't extracted for some reason, treat as a miss.
    if qf is None:
        print("[CheckCache] No query_filters in state — treating as cache miss.")
        return {"cache_hit": False}

    cached_answer = check_semantic_cache(
        resolved_prompt=qf.resolved_prompt,
        qf=qf,
    )

    if cached_answer:
        print(f"[CheckCache] HIT — returning cached answer.")
        return {
            "cache_hit": True,
            "answer": cached_answer,
        }

    print("[CheckCache] MISS — proceeding to SQL generation.")
    return {"cache_hit": False}
