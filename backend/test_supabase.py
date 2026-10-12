
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(override=True)

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    raise ValueError("Supabase credentials not found in .env")

print("Project URL:", url)
print(
    "Key type:",
    "Secret" if key.startswith("sb_secret_")
    else "Publishable/Anon"
)

supabase = create_client(url, key)

try:
    response = (
        supabase.table("services")
        .select("service_id, service_name", count="exact")
        .execute()
    )

    print("\nSupabase connection successful!")
    print("Total rows visible to Python:", response.count)
    print("Services returned:", response.data)

except Exception as e:
    print("Supabase query failed:", e)
