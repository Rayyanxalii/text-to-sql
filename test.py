"""
Semantic cache test – demonstrates filter-based cache isolation.

Scenario:
  • Store an answer for "How many patients were admitted in 2025?"
  • Check the same question  → should HIT  (same filters)
  • Check a 2026 question   → should MISS (year filter differs)
  • Check a paraphrase      → should HIT  (same intent + same year)
"""

from redisvl.extensions.cache.llm import SemanticCache
from redisvl.utils.vectorize import OllamaTextVectorizer
from app.services.redis_service import (
    check_semantic_cache,
    store_semantic_cache,
    build_cache_filters,
)
from app.structured_ouput import QueryFilters


# ---------------------------------------------------------------------------
# Helper: build a QueryFilters manually for testing (no LLM call needed)
# ---------------------------------------------------------------------------

def make_filters(prompt: str, years: list[int] | None = None) -> QueryFilters:
    return QueryFilters(
        resolved_prompt=prompt,
        years=years or [],
        numbers=[],
        entities=[],
        date_ranges=[],
    )


# ---------------------------------------------------------------------------
# 1. Store
# ---------------------------------------------------------------------------

qf_2025 = make_filters(
    prompt="How many patients were admitted in 2025?",
    years=[2025],
)

store_semantic_cache(
    resolved_prompt=qf_2025.resolved_prompt,
    answer="There were 150 patients admitted in 2025.",
    qf=qf_2025,
)
print("\n[STORED] 2025 question\n")


# ---------------------------------------------------------------------------
# 2. Exact same question → expect HIT
# ---------------------------------------------------------------------------

hit = check_semantic_cache(
    resolved_prompt="How many patients were admitted in 2025?",
    qf=make_filters("How many patients were admitted in 2025?", years=[2025]),
)
print(f"Test 1 – exact same question   : {'HIT ✅  → ' + hit if hit else 'MISS ❌'}")


# ---------------------------------------------------------------------------
# 3. Same question but 2026 → expect MISS  (year filter differs)
# ---------------------------------------------------------------------------

miss = check_semantic_cache(
    resolved_prompt="How many patients were admitted in 2026?",
    qf=make_filters("How many patients were admitted in 2026?", years=[2026]),
)
print(f"Test 2 – different year (2026) : {'HIT ❌  → ' + miss if miss else 'MISS ✅  (correctly rejected)'}")


# ---------------------------------------------------------------------------
# 4. Paraphrased but same intent + same year → expect HIT
# ---------------------------------------------------------------------------

paraphrase_hit = check_semantic_cache(
    resolved_prompt="Total number of patient admissions during 2025?",
    qf=make_filters("Total number of patient admissions during 2025?", years=[2025]),
)
print(f"Test 3 – paraphrase, same year : {'HIT ✅  → ' + paraphrase_hit if paraphrase_hit else 'MISS (threshold may need tuning)'}")