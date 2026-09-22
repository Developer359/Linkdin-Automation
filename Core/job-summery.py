import os
import json
import re
import time
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

# Initialize Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Correct path resolution to project root
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)

INPUT_FILE = os.path.join(PROJECT_ROOT, "Data", "Job-Info.json")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "Data", "Job-summery.json")

MODEL_NAME = "gemini-3.5-flash-lite"


# Pydantic schema enforcing concise notes for LinkedIn
class JobLinkedInSummary(BaseModel):
    job_title: str = Field(description="Clean, concise job title")
    company: str = Field(description="Company name")
    job_url: str = Field(description="Direct URL to apply")
    company_email: str = Field(description="Extracted recruiter/company email from description or 'Not specified'")
    source: str = Field(description="Platform source (e.g., LinkedIn, WeWorkRemotely)")
    pay_info: str = Field(description="Salary or compensation details if found, otherwise 'Not specified'")
    job_summary: str = Field(description="1-2 short sentences summarizing the role for LinkedIn")
    requirements: list[str] = Field(description="Short bullet points of key requirements (max 4-5 items)")
    required_skills: list[str] = Field(description="Key technologies and skills list (e.g., React, Node.js, AWS)")
    what_we_offer: list[str] = Field(description="Perks, benefits, or offerings (max 3-4 items)")
    about_company: str = Field(description="1 concise sentence about what the company does")
    workplace_type: str = Field(description="100% accurate determination of whether the job is Remote, On-site, or Hybrid based on the job description")
    tags: list[str] = Field(description="Exactly two relevant tags related to the job (e.g., ['Full Stack Developer', 'Frontend Developer'])")
    color_code: str = Field(description="Matching hex color code based on the job query category")


def extract_email_fallback(text: str) -> str:
    """Regex helper to spot emails inside description text if missed by LLM."""
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    return emails[0] if emails else "Not specified"


def summarize_job_with_gemini(job_data: dict, max_retries: int = 3) -> dict:
    raw_desc = job_data.get("job_description", "")
    existing_email = job_data.get("company_email", "")
    existing_pay = job_data.get("pay_info", "Not specified")

    prompt = f"""
    You are an expert LinkedIn technical recruiter. Process this job posting into short, punchy notes for a LinkedIn automated post.
    
    CRITICAL INSTRUCTIONS:
    1. Keep all text fields short, clean, and direct. Avoid long paragraphs.
    2. Extract any company or recruiter contact email ONLY if explicitly mentioned in the job description. If not present, set company_email to 'Not specified'. Do NOT invent or estimate emails.
    3. Extract payment/salary info if mentioned in the description text and not already provided.
    4. Focus on essential skills, brief requirements, and perks.
    5. Read the description carefully and determine with 100% accuracy whether the job is 'Remote', 'On-site', or 'Hybrid' for the `workplace_type` field.
    6. Generate exactly TWO relevant job tags for the `tags` field according to the job role (e.g., ['Full Stack Developer', 'Frontend Developer']).
    7. Assign the correct `color_code` based on the job query category using these exact rules:
       - Full Stack: #171B26 (Deep Charcoal)
       - AI Engineering: #1C2B4D (Modern Classic Navy)
       - Design: #4A5568 (Professional Slate Grey)
       - Software Engineering: #2C1E1A (Warm Dark Brown / Espresso)
       - Other / Default query: #A0AEC0 (Crisp Light Grey)

    INPUT DATA:
    - Title: {job_data.get('title')}
    - Company: {job_data.get('company')}
    - Source: {job_data.get('source', 'LinkedIn')}
    - Direct Job URL: {job_data.get('job_url')}
    - Provided Email: {existing_email}
    - Provided Pay: {existing_pay}
    - Job Description:
    {raw_desc}
    """

    summarized = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=JobLinkedInSummary,
                    temperature=0.2,
                ),
            )
            summarized = response.parsed.model_dump()
            break
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                if attempt < max_retries:
                    print(f"  ⚠️ Rate limit hit (429). Waiting 15s before retry {attempt}/{max_retries}...")
                    time.sleep(15)
                    continue
            
            print(f"  -> Gemini Error for '{job_data.get('title')}': {e}")
            summarized = {
                "job_title": job_data.get("title", ""),
                "company": job_data.get("company", ""),
                "job_url": job_data.get("job_url", ""),
                "company_email": existing_email or extract_email_fallback(raw_desc),
                "source": job_data.get("source", "LinkedIn"),
                "pay_info": existing_pay,
                "job_summary": "Summary unavailable.",
                "requirements": [],
                "required_skills": [],
                "what_we_offer": [],
                "about_company": "Information unavailable.",
                "workplace_type": "Not specified",
                "tags": [],
                "color_code": "#A0AEC0"
            }
            break

    # Maintain direct URL
    summarized["job_url"] = job_data.get("job_url", "")

    # Resolve email STRICTLY from input data or description regex
    current_email = summarized.get("company_email", "Not specified")
    if current_email in ["Not specified", "", None]:
        if existing_email:
            summarized["company_email"] = existing_email
        else:
            summarized["company_email"] = extract_email_fallback(raw_desc)

    return summarized


def save_progress_to_json(data_list: list):
    """Saves accumulated job output directly to disk after each processed item."""
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data_list, f, indent=4, ensure_ascii=False)


def run_job_summarizer():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Could not find input file at '{INPUT_FILE}'")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        job_list = json.load(f)

    if not job_list:
        print("No jobs found in Job-Info.json to process.")
        return

    print(f"--- Starting Sequential LinkedIn Job Summarizer | Model: {MODEL_NAME} ---")
    print(f"Total jobs to process: {len(job_list)}\n")

    summarized_jobs = []

    for idx, job in enumerate(job_list, start=1):
        print(f"[{idx}/{len(job_list)}] Processing: {job.get('title')} @ {job.get('company')}...")
        
        clean_job = summarize_job_with_gemini(job)
        summarized_jobs.append(clean_job)

        save_progress_to_json(summarized_jobs)
        print(f"  ✓ Saved to 'Job-summery.json'")
        
        time.sleep(2)

    print(f"\nDone! Successfully saved {len(summarized_jobs)} jobs to '{OUTPUT_FILE}'")


if __name__ == "__main__":
    run_job_summarizer()