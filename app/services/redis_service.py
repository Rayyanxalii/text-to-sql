from redisvl.extensions.cache.llm import SemanticCache
from redisvl.utils.vectorize import OllamaTextVectorizer
from app.structured_ouput import QueryFilters


# ---------------------------------------------------------------------------
# Vectorizer & semantic cache
# ---------------------------------------------------------------------------

_vectorizer = OllamaTextVectorizer(model="nomic-embed-text")

semantic_cache = SemanticCache(
    name="text_to_sql_cache",
    redis_url="redis://localhost:6379",
    vectorizer=_vectorizer,
    # Threshold: only surface hits that are very close semantically.
    # Exact-value differences (year, numbers) are caught by the filter guard
    # below, so we can afford a slightly generous threshold here.
    distance_threshold=0.12,
    ttl = 360
)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def build_cache_filters(qf: QueryFilters) -> dict:
    """
    Convert a QueryFilters object into a flat dict of strings suitable for
    redisvl Tag filters.  All values are stringified so redisvl can index them.
    """
    return {
        "years":       ",".join(str(y) for y in sorted(qf.years))       or "none",
        "numbers":     ",".join(str(n) for n in sorted(qf.numbers))     or "none",
        "entities":    ",".join(sorted(e.lower() for e in qf.entities)) or "none",
        "date_ranges": ",".join(sorted(d.lower() for d in qf.date_ranges)) or "none",
    }


def check_semantic_cache(resolved_prompt: str, qf: QueryFilters) -> str | None:
    """
    Look up the cache using the resolved (post-clarification) prompt plus
    exact filter matching on years / numbers / entities / date_ranges.

    Returns the cached answer string, or None on a miss.
    """
    results = semantic_cache.check(prompt=resolved_prompt, num_results=5)

    if not results:
        return None

    expected = build_cache_filters(qf)

    for hit in results:
        stored = hit.get("metadata", {})
        # Every filter dimension must match exactly.
        if all(stored.get(k) == v for k, v in expected.items()):
            print(f"[Cache HIT]  distance={hit.get('vector_distance'):.4f}  filters={expected}")
            return hit.get('response')

    print(f"[Cache MISS] semantic neighbours found but filters did not match. expected={expected}")
    return None



def store_semantic_cache(resolved_prompt: str, answer: str, qf: QueryFilters) -> None:
    """
    Store an answer in the semantic cache with filter metadata so future
    lookups can enforce exact value matching.
    """
    filters = build_cache_filters(qf)
    semantic_cache.store(
        prompt=resolved_prompt,
        response=answer,
        metadata=filters,
    )
    print(f"[Cache STORE] filters={filters}")


# ---------------------------------------------------------------------------
# Legacy simple-cache helpers (kept for backward compat, used nowhere new)
# ---------------------------------------------------------------------------

def normalize_question(question: str) -> str:
    return question.strip().lower()