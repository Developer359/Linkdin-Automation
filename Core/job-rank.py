import os
import sys
import json
import traceback
from pathlib import Path
from dotenv import load_dotenv
from google import genai

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
CACHE_DIR = BASE_DIR / "Data" / "Job-Result-cache"
OUTPUT_FILE = BASE_DIR / "Data" / "Job_Rank.json"

CATEGORY_FILES = [
    "Fullstack.json",
    "AIEngineer.json",
    "MobileDeveloper.json",
    "Designer.json",
    "SoftwareEngineer.json"
]

def rank_and_select_jobs():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[!] GEMINI_API_KEY not found in environment variables.")
        # Save empty output so downstream scripts don't crash on missing file
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        sys.exit(1)

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"[!] Failed to initialize GenAI Client: {e}")
        traceback.print_exc()
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        sys.exit(1)

    ranked_results = []

    for filename in CATEGORY_FILES:
        file_path = CACHE_DIR / filename
        if not file_path.exists():
            print(f"[-] Cache file not found: {filename}, skipping...")
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                jobs = json.load(f)
        except Exception as e:
            print(f"    [!] Error reading {filename}: {e}")
            traceback.print_exc()
            continue

        if not jobs:
            print(f"[-] No jobs found in {filename}, skipping...")
            continue

        print(f"[*] Processing and ranking query category: {filename.replace('.json', '')}...")

        prompt = f"""
        You are an expert AI Career Recruiter and Company Evaluator. 
        Below is a JSON list of scraped job openings for the category '{filename.replace('.json', '')}'.

        JOBS DATA:
        {json.dumps(jobs, indent=2)}

        EVALUATION & RANKING RULES:
        1. Evaluate each company's global/regional reputation, market performance, brand size, stability, and hiring prestige. Major, well-established, or high-performance companies must receive the highest priority.
        2. Consider junior/entry-level role appropriateness if available, but corporate reputation and company hiring score carry maximum weight.
        3. Rank the options and select the **SINGLE absolute best job** from this list.
        4. Return ONLY a valid JSON object (no markdown blocks like ```json, just the raw JSON text) with this exact structure:
        {{
            "category": "{filename.replace('.json', '')}",
            "title": "...",
            "company": "...",
            "location": "...",
            "job_url": "...",
            "date_posted": "...",
            "source": "...",
            "evaluation_score": "...",  
            "reason": "Write a short, punchy 2-3 sentence summary explaining why this job won based on company reputation, hiring score, and role fit."
        }}
        """

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            
            result_text = response.text.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            best_job = json.loads(result_text)
            ranked_results.append(best_job)
            print(f"    [✓] Top pick selected: {best_job.get('title')} at {best_job.get('company')}")

        except Exception as e:
            print(f"    [!] Error processing {filename}: {e}")
            traceback.print_exc()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(ranked_results, f, indent=4, ensure_ascii=False)

    print(f"\n[✓] Successfully ranked all categories and saved to Data/Job_Rank.json")

if __name__ == "__main__":
    rank_and_select_jobs()