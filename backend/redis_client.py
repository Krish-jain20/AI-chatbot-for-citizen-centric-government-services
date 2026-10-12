
import os
from pathlib import Path
from dotenv import load_dotenv
from upstash_redis import Redis

# Locate .env in the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")

if not redis_url or not redis_token:
    raise ValueError(
        "Upstash Redis credentials are missing from project-root .env"
    )

redis_client = Redis(
    url=redis_url,
    token=redis_token
)
