
import os
import json
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Error: Missing env vars")
    exit(1)

supabase = create_client(url, key)

print("--- VOTERS ---")
voters = supabase.table("voters").select("*").execute()
print(json.dumps(voters.data, indent=2))

# print("\n--- ENROLLMENT REQUESTS ---")
# requests = supabase.table("enrollment_requests").select("*").execute()
# print(json.dumps(requests.data, indent=2))
