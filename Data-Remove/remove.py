import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load .env file from the project root directory
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(root_dir, ".env")
load_dotenv(dotenv_path=env_path)

# Retrieve Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env file.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def clear_all_data():
    print("🚀 Starting cleanup process...")

    # 1. Remove all files from Supabase Storage bucket ('job-images')
    try:
        bucket_name = "job-images"
        print(f"📁 Checking storage bucket '{bucket_name}'...")
        
        file_list = supabase.storage.from_(bucket_name).list()
        file_names = [f["name"] for f in file_list if f.get("name") and f["name"] != ".emptyFolderPlaceholder"]
        
        if file_names:
            print(f"Found {len(file_names)} file(s). Deleting...")
            supabase.storage.from_(bucket_name).remove(file_names)
            print("✓ Storage cleared successfully.")
        else:
            print("✓ Storage bucket is already empty.")
            
    except Exception as e:
        print(f"❌ Error clearing storage bucket: {e}")

    # 2. Truncate table and reset ID auto-increment sequence
    try:
        table_name = "jobs"
        print(f"📊 Truncating table '{table_name}' and resetting ID counter to 1...")
        
        # Calls the Postgres RPC function created in Step 1
        supabase.rpc("reset_jobs_table").execute()
        print("✓ Database table cleared and ID counter reset to 1 successfully.")
        
    except Exception as e:
        print(f"❌ Error resetting database table: {e}")

    print("✨ Cleanup complete!")

if __name__ == "__main__":
    clear_all_data()