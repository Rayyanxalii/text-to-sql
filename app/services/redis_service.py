from redisvl.extensions.cache.llm import SemanticCache
from redisvl.utils.vectorize import OllamaTextVectorizer
from app.structured_ouput import QueryFilters


# ---------------------------------------------------------------------------
# Lazy Vectorizer & semantic cache (graceful if Redis is down)
# ---------------------------------------------------------------------------

_semantic_cache = None


def get_semantic_cache():
    global _semantic_cache
    if _semantic_cache is not None:
        return _semantic_cache
    try:
        vectorizer = OllamaTextVectorizer(model="nomic-embed-text")
        _semantic_cache = SemanticCache(
            name="text_to_sql_cache",
            redis_url="redis://localhost:6379",
            vectorizer=vectorizer,
            distance_threshold=0.12,
            ttl=360,
        )
        return _semantic_cache
    except Exception as e:
        print(f"[Cache WARNING] Could not connect to Redis ({e}). Semantic cache is bypassed.")
        return None


class _LazySemanticCacheProxy:
    def __getattr__(self, name):
        cache = get_semantic_cache()
        if cache is None:
            raise ConnectionError("Redis cache unavailable")
        return getattr(cache, name)


semantic_cache = _LazySemanticCacheProxy()


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def build_cache_filters(qf: QueryFilters) -> dict:
    """
    Convert a QueryFilters object into a flat dict of strings suitable for
    redisvl Tag filters. All values are stringified so redisvl can index them.
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

    Returns the cached answer string, or None on a miss or connection failure.
    """
    cache = get_semantic_cache()
    if cache is None:
        return None

    try:
        results = cache.check(prompt=resolved_prompt, num_results=5)
        if not results:
            return None

        expected = build_cache_filters(qf)

        for hit in results:
            stored = hit.get("metadata", {})
            if all(stored.get(k) == v for k, v in expected.items()):
                print(f"[Cache HIT]  distance={hit.get('vector_distance'):.4f}  filters={expected}")
                return hit.get("response")

        print(f"[Cache MISS] semantic neighbours found but filters did not match. expected={expected}")
        return None
    except Exception as e:
        print(f"[Cache WARNING] Error during cache lookup: {e}")
        return None


def store_semantic_cache(resolved_prompt: str, answer: str, qf: QueryFilters) -> None:
    """
    Store an answer in the semantic cache with filter metadata so future
    lookups can enforce exact value matching.
    """
    cache = get_semantic_cache()
    if cache is None:
        return

    try:
        filters = build_cache_filters(qf)
        cache.store(
            prompt=resolved_prompt,
            response=answer,
            metadata=filters,
        )
        print(f"[Cache STORE] filters={filters}")
    except Exception as e:
        print(f"[Cache WARNING] Error storing to cache: {e}")


def normalize_question(question: str) -> str:
    return question.strip().lower()