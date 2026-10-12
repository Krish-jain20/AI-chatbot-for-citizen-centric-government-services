
from backend.redis_client import redis_client

redis_client.set(
    "civicbridge:test",
    "CivicBridge Redis is working"
)

value = redis_client.get("civicbridge:test")

print(value)

assert value == "CivicBridge Redis is working"
print("Redis connection successful!")
