import os
import json
import re
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

# Initialize Gemini Client with gemini-2.5-flash
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Correct path resolution to project root
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)

INPUT_FILE = os.path.join(PROJECT_ROOT, "Data", "Job-Info.json")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "Data", "Job-summery.json")

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


def extract_email_fallback(text: str) -> str:
    """Regex helper to spot emails if missed."""
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    return emails[0] if emails else "Not specified"


def summarize_job_with_gemini(job_data: dict) -> dict:
    raw_desc = job_data.get("job_description", "")
    existing_email = job_data.get("company_email", "")
    existing_pay = job_data.get("pay_info", "Not specified")

    prompt = f"""
    You are an expert LinkedIn technical recruiter. Process this job posting into short, punchy notes for a LinkedIn automated post.
    
    CRITICAL INSTRUCTIONS:
    1. Keep all text fields short, clean, and direct. Avoid long paragraphs.
    2. Extract any company or recruiter contact email mentioned in the job description.
    3. Extract payment/salary info if mentioned in the description text and not already provided.
    4. Focus on essential skills, brief requirements, and perks.

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

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config={
                "response_mime_type": "application/json",
                "response_schema": JobLinkedInSummary,
                "temperature": 0.2,
            },
        )
        # Parse Pydantic object back into a Python dictionary
        summarized = response.parsed.model_dump()
        
        # Preserve direct URL and ensure fallback email regex if LLM returned 'Not specified'
        summarized["job_url"] = job_data.get("job_url", "")
        if summarized["company_email"] == "Not specified" and existing_email:
            summarized["company_email"] = existing_email
        elif summarized["company_email"] == "Not specified":
            summarized["company_email"] = extract_email_fallback(raw_desc)

        return summarized

    except Exception as e:
        print(f"  -> Gemini Error for '{job_data.get('title')}': {e}")
        return {
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
            "about_company": "Information unavailable."
        }


def run_job_summarizer():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Could not find input file at '{INPUT_FILE}'")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        job_list = json.load(f)

    if not job_list:
        print("No jobs found in Job-Info.json to process.")
        return

    print(f"--- Starting LinkedIn Job Summarizer | Model: Gemini 2.5 Flash ---")
    print(f"Total jobs to process: {len(job_list)}\n")

    summarized_jobs = []
    for idx, job in enumerate(job_list, start=1):
        print(f"[{idx}/{len(job_list)}] Summarizing: {job.get('title')} @ {job.get('company')}...")
        clean_job = summarize_job_with_gemini(job)
        summarized_jobs.append(clean_job)

    # Save cleanly structured output
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(summarized_jobs, f, indent=4, ensure_ascii=False)

    print(f"\nDone! Saved {len(summarized_jobs)} LinkedIn-ready job summaries to '{OUTPUT_FILE}'")


if __name__ == "__main__":
    run_job_summarizer()