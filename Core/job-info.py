import os
import json
from pathlib import Path
import pandas as pd
from jobspy import scrape_jobs

BASE_DIR = Path(__file__).resolve().parents[1]
RANK_FILE = BASE_DIR / "Data" / "Job_Rank.json"
OUTPUT_FILE = BASE_DIR / "Data" / "Job-Info.json"


def format_pay(row) -> str:
    min_amt = row.get("min_amount")
    max_amt = row.get("max_amount")
    interval = row.get("interval") or ""
    if pd.isna(min_amt) and pd.isna(max_amt):
        return "Not specified"
    parts = []
    if not pd.isna(min_amt):
        parts.append(f"${int(min_amt):,}")
    if not pd.isna(max_amt) and max_amt != min_amt:
        parts.append(f"${int(max_amt):,}")
    pay_str = " - ".join(parts) if len(parts) > 1 else parts[0]
    return f"{pay_str} / {interval}".strip(" /") if interval else pay_str


def fetch_job_details():
    if not RANK_FILE.exists():
        print("[!] Job_Rank.json not found. Please run job-rank.py first.")
        return

    with open(RANK_FILE, "r", encoding="utf-8") as f:
        ranked_jobs = json.load(f)

    if not ranked_jobs:
        print("[!] No ranked jobs found in Job_Rank.json.")
        return

    enriched_jobs = []

    print("[*] Starting Job Info Enrichment (Fetching description, logo, pay info, etc.)...\n")

    for job in ranked_jobs:
        title = job.get("title")
        company = job.get("company")
        location = job.get("location", "Pakistan")
        target_url = job.get("job_url")

        print(f" -> Fetching full details for: {title} at {company}")

        search_query = f"{title} {company}"
        job_details = {
            "job_description": "",
            "company_url": "",
            "company_logo": "",
            "company_email": "",
            "pay_info": ""
        }

        try:
            # Re-scrape with description fetching enabled
            df = scrape_jobs(
                site_name=["linkedin"],
                search_term=search_query,
                location=location,
                results_wanted=5,
                hours_old=72,
                linkedin_fetch_description=True,
                verbose=0
            )

            matched_row = None
            if df is not None and not df.empty:
                # Match by exact job URL if possible
                for _, row in df.iterrows():
                    if str(row.get("job_url", "")).strip() == target_url:
                        matched_row = row
                        break
                # Fallback to the first result if exact URL match isn't found
                if matched_row is None:
                    matched_row = df.iloc[0]

                if matched_row is not None:
                    company_url = str(matched_row.get("company_url") or matched_row.get("company_url_direct") or "")
                    company_logo = str(matched_row.get("company_logo") or matched_row.get("logo_photo_url") or "")
                    description = str(matched_row.get("description") or "")

                    job_details = {
                        "job_description": description,
                        "company_url": company_url if company_url != "nan" else "",
                        "company_logo": company_logo if company_logo != "nan" else "",
                        "company_email": "",  # LinkedIn public listings rarely expose raw emails directly
                        "pay_info": format_pay(matched_row)
                    }
        except Exception as e:
            print(f"    [!] Error fetching details for {title}: {e}")

        # Combine original ranked info with newly fetched deep info
        enriched_job = {
            **job,
            "job_description": job_details["job_description"],
            "company_url": job_details["company_url"],
            "company_logo": job_details["company_logo"],
            "company_email": job_details["company_email"],
            "pay_info": job_details["pay_info"]
        }
        enriched_jobs.append(enriched_job)
        print(f"    [✓] Successfully enriched.\n")

    # Save to Job-Info.json cache
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(enriched_jobs, f, indent=4, ensure_ascii=False)

    print(f"[✓] All job details successfully fetched and stored in Data/Job-Info.json")


if __name__ == "__main__":
    fetch_job_details()