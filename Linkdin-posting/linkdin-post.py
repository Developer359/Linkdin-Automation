import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# File paths
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

# Load environment variables from root .env
load_dotenv(dotenv_path=ROOT_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
BUFFER_API_KEY = os.getenv("BUFFER_API_KEY")
BUFFER_CHANNEL_ID = os.getenv("BUFFER_CHANNEL_ID")

# Validate Credentials
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: Missing SUPABASE_URL or SUPABASE_KEY in .env file.")
    sys.exit(1)

if not BUFFER_API_KEY or not BUFFER_CHANNEL_ID:
    print("❌ Error: Missing BUFFER_API_KEY or BUFFER_CHANNEL_ID in .env file.")
    print("👉 Please make sure you saved your .env file in VS Code (Ctrl + S).")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_post_text(job_record):
    """Formats the post text dynamically using full_job_record data."""
    title = job_record.get("job_title", "Job Opportunity")
    company = job_record.get("company", "Our Company")
    location = job_record.get("location", "")
    workplace = job_record.get("workplace_type", "")
    summary = job_record.get("job_summary", "")
    pay_info = job_record.get("pay_info", "")
    job_url = job_record.get("job_url", "")
    about_company = job_record.get("about_company", "")

    # Bullet lists
    requirements = "\n".join([f"• {req}" for req in job_record.get("requirements", []) if req])
    skills_list = "\n".join([f"• {skill}" for skill in job_record.get("required_skills", []) if skill])
    what_we_offer = "\n".join([f"• {offer}" for offer in job_record.get("what_we_offer", []) if offer])
    
    # Hashtags
    raw_skills = job_record.get("required_skills", [])
    clean_title_tags = " ".join([f"#{word.capitalize()}" for word in title.split() if word.isalnum()])
    clean_skills = " ".join([f"#{skill.replace(' ', '').replace('-', '')}" for skill in raw_skills])
    hashtags = f"#Hiring #Jobs {clean_title_tags} {clean_skills}".strip()

    workplace_str = f" ({workplace})" if workplace else ""

    text = f"🚀 WE ARE HIRING: {title} 🚀\n\n"
    text += f"{company} is looking for a talented {title} to join our team"
    if location:
        text += f" in {location}"
    text += f"{workplace_str}!\n\n"

    if summary:
        text += f"📝 Job Summary:\n{summary}\n\n"

    if pay_info:
        text += f"💰 Pay & Compensation:\n{pay_info}\n\n"

    if requirements:
        text += f"Key Responsibilities & Requirements:\n{requirements}\n\n"

    if skills_list:
        text += f"🛠 Required Skills:\n{skills_list}\n\n"

    if what_we_offer:
        text += f"🎁 What We Offer:\n{what_we_offer}\n\n"

    if about_company:
        text += f"🏢 About Company:\n{about_company}\n\n"

    if job_url:
        text += f"📌 Apply Now:\n{job_url}\n\n"

    text += hashtags
    return text.strip()

def publish_buffer_post(text, image_url=None):
    """Sends post to Buffer via GraphQL API."""
    print("📤 Publishing post via Buffer GraphQL API...")
    url = "https://api.buffer.com/graphql"
    
    headers = {
        "Authorization": f"Bearer {BUFFER_API_KEY.strip()}",
        "Content-Type": "application/json"
    }

    # Corrected schema using BasicError for error handling
    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        __typename
        ... on PostActionSuccess {
          post {
            id
          }
        }
        ... on MutationError {
          message
        }
      }
    }
    """

    input_payload = {
        "channelId": BUFFER_CHANNEL_ID.strip(),
        "text": text,
        "mode": "shareNow",
        "schedulingType": "automatic"
    }

    if image_url:
        input_payload["assets"] = [{"image": {"url": image_url}}]

    try:
        res = requests.post(url, headers=headers, json={"query": mutation, "variables": {"input": input_payload}})
        res.raise_for_status()
        res_data = res.json()

        # Fallback to text-only if media payload fails schema checks
        if "errors" in res_data and image_url:
            print("⚠️ Media payload rejected by schema. Retrying text-only post...")
            input_payload.pop("assets", None)
            res = requests.post(url, headers=headers, json={"query": mutation, "variables": {"input": input_payload}})
            res.raise_for_status()
            res_data = res.json()

        if "errors" in res_data:
            print(f"❌ GraphQL Error: {res_data['errors']}")
            raise Exception(res_data['errors'])

        create_post_data = res_data.get("data", {}).get("createPost", {})
        
        if create_post_data.get("__typename") == "MutationError":
            error_msg = create_post_data.get("message", "Unknown Buffer error")
            print(f"❌ Buffer API Error: {error_msg}")
            raise Exception(error_msg)

        post_id = create_post_data.get("post", {}).get("id") if create_post_data.get("post") else "published"
        print(f"🎉 Post published successfully via Buffer! Buffer Post ID: {post_id}")
        return post_id
    except Exception as e:
        print(f"❌ Error publishing via Buffer GraphQL: {e}")
        raise e

def main():
    json_path = SCRIPT_DIR / "Post-Data" / "post.json"
    if not json_path.exists():
        print("❌ Error: post.json file not found. Run your post generation script first.")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    job_id = data.get("job_id")
    full_record = data.get("full_job_record", {})
    
    post_text = data.get("post_content") or generate_post_text(full_record)
    image_url = data.get("image_url") or data.get("public_image_url")

    buffer_post_id = publish_buffer_post(post_text, image_url=image_url)

    print(f"🔄 Updating Supabase status for Job ID {job_id}...")
    supabase.table("jobs").update({
        "status": "posted"
    }).eq("id", job_id).execute()

    print(f"✨ Job ID {job_id} successfully processed and marked as 'posted'!")

if __name__ == "__main__":
    main()