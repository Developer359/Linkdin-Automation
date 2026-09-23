import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from your .env file
load_dotenv()

# Load your Supabase credentials securely
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_image_and_save_job(job_data):
    local_img_path = job_data.get("image_path")
    public_image_url = None
    
    # 1. Upload local image to Supabase Storage bucket 'job-images'
    if local_img_path and os.path.exists(local_img_path):
        file_name = os.path.basename(local_img_path)
        bucket_name = "job-images"
        
        with open(local_img_path, "rb") as f:
            file_bytes = f.read()
            
        # Upload binary to Supabase Storage (upsert replaces if it already exists)
        supabase.storage.from_(bucket_name).upload(
            path=file_name,
            file=file_bytes,
            file_options={"contentType": "image/png", "upsert": "true"}
        )
        
        # Get the public URL for LinkedIn / database
        public_image_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
        print(f"Image uploaded successfully! Public URL: {public_image_url}")
    else:
        print(f"Warning: Image path not found or invalid: {local_img_path}")

    # 2. Map all your dictionary fields into the database payload
    db_payload = {
        "job_title": job_data.get("job_title"),
        "company": job_data.get("company"),
        "location": job_data.get("location"),
        "job_url": job_data.get("job_url"),
        "company_email": job_data.get("company_email"),
        "source": job_data.get("source"),
        "pay_info": job_data.get("pay_info"),
        "job_summary": job_data.get("job_summary"),
        "requirements": job_data.get("requirements"),       # Stored safely as JSON list
        "required_skills": job_data.get("required_skills"), # Stored safely as JSON list
        "what_we_offer": job_data.get("what_we_offer"),     # Stored safely as JSON list
        "about_company": job_data.get("about_company"),
        "workplace_type": job_data.get("workplace_type"),
        "image_url": public_image_url,                      # The cloud public URL
        "status": job_data.get("status", "pending")
    }

    # 3. Insert into Supabase 'jobs' table
    response = supabase.table("jobs").insert(db_payload).execute()
    print(f"Successfully saved job to Supabase: {job_data.get('job_title')}")
    return response

if __name__ == "__main__":
    storage_json_path = "Main-Storage/main-storage.json"
    
    if os.path.exists(storage_json_path):
        with open(storage_json_path, "r", encoding="utf-8") as f:
            jobs_list = json.load(f)
            
        print(f"Found {len(jobs_list)} jobs in main-storage.json. Processing sync to Supabase...")
        
        for idx, job in enumerate(jobs_list, 1):
            print(f"\n--- Processing Job {idx}/{len(jobs_list)}: {job.get('job_title')} ---")
            try:
                upload_image_and_save_job(job)
            except Exception as e:
                print(f"Error processing job '{job.get('job_title')}': {e}")
    else:
        print(f"Error: {storage_json_path} not found.")