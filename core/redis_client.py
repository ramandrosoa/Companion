"""
core/redis_client.py
Shared Redis connection — import this everywhere you need Redis.
"""
import os
from dotenv import load_dotenv
from upstash_redis import Redis

load_dotenv()

redis = Redis(
    url=os.environ["UPSTASH_REDIS_URL"],
    token=os.environ["UPSTASH_REDIS_TOKEN"]
)