
import json
from backend.redis_client import redis_client

SESSION_TTL = 1800  # 30 minutes


def get_session(user_id: int) -> dict:
    key = f"civicbridge:session:{user_id}"
    data = redis_client.get(key)

    if data is None:
        return {
            "flow": None,
            "step": None,
            "answers": {}
        }

    return json.loads(data)


def save_session(user_id: int, session: dict) -> None:
    key = f"civicbridge:session:{user_id}"

    redis_client.set(
        key,
        json.dumps(session),
        ex=SESSION_TTL
    )


def clear_session(user_id: int) -> None:
    redis_client.delete(f"civicbridge:session:{user_id}")
