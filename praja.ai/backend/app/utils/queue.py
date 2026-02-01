import os
from redis import Redis
from rq import Queue

# Single source of truth for Redis URL
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

def _redis():
    # decode_responses avoids byte/string surprises in debug scripts
    return Redis.from_url(REDIS_URL, decode_responses=True)

def get_queue(name: str = "praja") -> Queue:
    return Queue(name, connection=_redis())
