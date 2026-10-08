from redisvl.extensions.cache.llm import SemanticCache
from redisvl.utils.vectorize import OllamaTextVectorizer


vectorizer = OllamaTextVectorizer(
    model="nomic-embed-text"
)

cache = SemanticCache(
    name="text_to_sql_cache",
    redis_url="redis://localhost:6379",
    vectorizer=vectorizer,
    distance_threshold=0.1,
)


cache.store(
    prompt="How many patients were admitted in 2025?",
    response="There were 150 patients."
)


result = cache.check(
    prompt="How many patients were admitted in 2026?",
)

if result:
    print("Cached answer:", result[0]["response"])
    print("Vector distance:", result[0]["vector_distance"])
else:
    print("No cached response found.")