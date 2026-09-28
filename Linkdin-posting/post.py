import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Directories and Paths
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

# Load .env file from root directory
env_path = ROOT_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env file.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_top_pending_job():
    # 1. Fetch Top Pending Job
    response = (
        supabase.table("jobs")
        .select("*")
        .eq("status", "pending")
        .order("created_at", desc=False)
        .limit(1)
        .execute()
    )

    jobs = response.data

    # 2. Guard Check & Termination
    if not jobs:
        print("No pending jobs found in queue. Exiting.")
        sys.exit(0)

    # Store job details in local memory variables
    top_job = jobs[0]
    job_id = top_job.get("id")
    post_content = top_job.get("post_content")
    image_url = top_job.get("image_url")

    print(f"Successfully fetched job ID: {job_id}")

    # 3. Download Image if URL exists
    local_image_path = None
    if image_url:
        try:
            print(f"Downloading image from: {image_url}")
            img_response = requests.get(image_url, timeout=15)
            if img_response.status_code == 200:
                # Get file extension from URL or default to .png
                ext = Path(image_url.split("?")[0]).suffix or ".png"
                image_file_path = SCRIPT_DIR / "Post-Data" / f"post_image{ext}"
                
                with open(image_file_path, "wb") as img_file:
                    img_file.write(img_response.content)
                
                local_image_path = str(image_file_path)
                print(f"Image saved locally to: {local_image_path}")
            else:
                print(f"Failed to download image. Status code: {img_response.status_code}")
        except Exception as e:
            print(f"Error downloading image: {e}")

    # 4. Save Details to post.json
    job_data = {
        "job_id": job_id,
        "post_content": post_content,
        "image_url": image_url,
        "local_image_path": local_image_path,
        "full_job_record": top_job
    }

    json_file_path = SCRIPT_DIR / "Post-Data" / "post.json"
    with open(json_file_path, "w", encoding="utf-8") as json_file:
        json.dump(job_data, json_file, indent=4)

    print(f"Job data successfully written to: {json_file_path}")
    return job_data

if __name__ == "__main__":
    fetch_top_pending_job()