import redis

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

# print(redis_client.ping())  # Should print True if the connection is successful

def get_cache(key):
    return redis_client.get(key)


def set_cache(key, value, ttl=300):
    redis_client.setex(key, ttl, value)