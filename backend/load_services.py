import json
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    raise ValueError("Supabase credentials not found in .env")

# Connect to Supabase
supabase = create_client(url, key)

# Locate services.json
json_path = Path(__file__).parent.parent / "data" / "services.json"

with open(json_path, "r", encoding="utf-8") as file:
    data = json.load(file)

services = data

# Insert services
response = supabase.table("services").insert(services).execute()

print(f"Successfully inserted {len(services)} services.")

for service in services:
    print(f"- {service['service_name']}")