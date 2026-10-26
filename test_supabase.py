
from pathlib import Path
from dotenv import dotenv_values
from supabase import create_client

# Read the .env file directly
env_path = Path(__file__).resolve().parent / ".env"
config = dotenv_values(env_path)

url = config.get("SUPABASE_URL")
key = config.get("SUPABASE_KEY")

print("Step 1: Environment file found:", env_path.exists())
print("Step 2: Supabase URL found:", bool(url))
print("Step 3: Supabase key found:", bool(key))

if not url or not key:
    raise ValueError("Missing Supabase URL or API key in .env")

try:
    supabase = create_client(url, key)
    print("Step 4: Supabase client created successfully")

    response = (
        supabase.table("schemes")
        .select("id")
        .limit(5)
        .execute()
    )

    print("Step 5: Supabase query successful!")
    print("Schemes returned:", len(response.data))
    print("Data:", response.data)

except Exception as error:
    print("Supabase connection or query failed!")
    print("Error:", error)
