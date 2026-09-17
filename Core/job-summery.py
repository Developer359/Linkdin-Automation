import os
import json
import re
import time
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError

# Load environment variables
load_dotenv()

# Initialize Gemini Client
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
    """Regex helper to spot emails inside description text if missed."""
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    return emails[0] if emails else "Not specified"


def research_company_email_with_gemini(company_name: str, company_url: str = "") -> str:
    """Uses Gemini 2.5 Flash with Google Search grounding to locate the company email with automatic retry on 429."""
    if not company_name or company_name.lower() in ["unknown", "n/a"]:
        return "Not specified"

    print(f"  └─ Email missing. Searching online for '{company_name}' contact email...")

    prompt = (
        f"Search online for the official careers, recruiting, HR, or contact email address for the company '{company_name}'. "
        f"Return ONLY the email address (e.g., jobs@company.com). If no specific email is found, reply 'Not specified'."
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.1,
                )
            )

            if response.text:
                found = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', response.text)
                if found:
                    print(f"     ✓ Gemini Search found email: {found[0]}")
                    return found[0]
            break

        except APIError as e:
            if e.code == 429:
                wait_time = 12 * (attempt + 1)
                print(f"     ⚠️ Rate limit hit during search. Waiting {wait_time}s before retry ({attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
            else:
                print(f"     ⚠️ Gemini Search failed: {e}")
                break
        except Exception as e:
            print(f"     ⚠️ Gemini Search failed: {e}")
            break

    # Domain fallback if company URL exists
    if company_url:
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', company_url)
        if domain_match:
            domain = domain_match.group(1).lower()
            if not any(p in domain for p in ["linkedin.com", "weworkremotely.com", "indeed.com"]):
                fallback_email = f"careers@{domain}"
                print(f"     ✓ Domain fallback generated: {fallback_email}")
                return fallback_email

    return "Not specified"


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

    summarized = None
    max_retries = 3

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=JobLinkedInSummary,
                    temperature=0.2,
                ),
            )
            summarized = response.parsed.model_dump()
            break

        except APIError as e:
            if e.code == 429:
                wait_time = 12 * (attempt + 1)
                print(f"  ⚠️ Rate limit hit (429). Retrying in {wait_time}s ({attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
            else:
                print(f"  -> Gemini Error for '{job_data.get('title')}': {e}")
                break
        except Exception as e:
            print(f"  -> Gemini Error for '{job_data.get('title')}': {e}")
            break

    # Fallback structure if summarization failed completely
    if not summarized:
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
            "about_company": "Information unavailable."
        }

    # Ensure direct URL is maintained
    summarized["job_url"] = job_data.get("job_url", "")

    # Check and resolve email if missing
    current_email = summarized.get("company_email", "Not specified")
    if current_email in ["Not specified", "", None]:
        if existing_email:
            summarized["company_email"] = existing_email
        else:
            regex_email = extract_email_fallback(raw_desc)
            if regex_email != "Not specified":
                summarized["company_email"] = regex_email
            else:
                company_name = job_data.get("company", "")
                company_url = job_data.get("company_url", "")
                summarized["company_email"] = research_company_email_with_gemini(company_name, company_url)

    return summarized


def save_progress_to_json(data_list: list):
    """Saves the accumulated list to JSON immediately after processing each job."""
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

    print(f"--- Starting Sequential LinkedIn Job Summarizer | Model: Gemini 2.5 Flash ---")
    print(f"Total jobs to process: {len(job_list)}\n")

    summarized_jobs = []

    for idx, job in enumerate(job_list, start=1):
        print(f"[{idx}/{len(job_list)}] Processing: {job.get('title')} @ {job.get('company')}...")
        
        # 1. Process individual job (Summarize + Search Email)
        clean_job = summarize_job_with_gemini(job)
        summarized_jobs.append(clean_job)

        # 2. Save progress immediately to disk
        save_progress_to_json(summarized_jobs)
        print(f"  ✓ Progress saved to 'Job-summery.json'")

        # 3. Pacing delay to avoid API rate limits
        if idx < len(job_list):
            time.sleep(4)

    print(f"\nDone! Successfully saved {len(summarized_jobs)} jobs to '{OUTPUT_FILE}'")


if __name__ == "__main__":
    run_job_summarizer()