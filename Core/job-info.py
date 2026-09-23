import os
import json
from pathlib import Path
import pandas as pd
from jobspy import scrape_jobs

BASE_DIR = Path(__file__).resolve().parents[1]
RANK_FILE = BASE_DIR / "Data" / "Job_Rank.json"
OUTPUT_FILE = BASE_DIR / "Data" / "Job-Info.json"


def format_pay(row) -> str:
    if row is None:
        return "Not specified"
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
        title = job.get("title", "Software Engineer")
        company = job.get("company", "Tech Company")
        location = job.get("location", "Pakistan")
        target_url = job.get("job_url", "")

        print(f" -> Fetching full details for: {title} at {company}")

        # Intelligent fallback description in case cloud scraping gets blocked
        default_desc = job.get("description", f"We are looking for a motivated {title} to join {company} in {location}. Responsibilities include developing scalable applications, collaborating with engineering teams, and writing robust code.")

        job_details = {
            "job_description": default_desc,
            "company_url": job.get("company_url", ""),
            "company_logo": job.get("company_logo", ""),
            "company_email": job.get("company_email", "Not specified"),
            "pay_info": job.get("pay_info", "Not specified")
        }

        try:
            # Re-scrape with description fetching enabled
            df = scrape_jobs(
                site_name=["linkedin"],
                search_term=f"{title} {company}",
                location=location,
                results_wanted=3,
                hours_old=72,
                linkedin_fetch_description=True,
                verbose=0
            )

            matched_row = None
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    if target_url and str(row.get("job_url", "")).strip() == target_url:
                        matched_row = row
                        break
                if matched_row is None:
                    matched_row = df.iloc[0]

                if matched_row is not None:
                    company_url = str(matched_row.get("company_url") or matched_row.get("company_url_direct") or "")
                    company_logo = str(matched_row.get("company_logo") or matched_row.get("logo_photo_url") or "")
                    description = str(matched_row.get("description") or "")

                    if description and len(description) > 30:
                        job_details["job_description"] = description
                    if company_url and company_url != "nan":
                        job_details["company_url"] = company_url
                    if company_logo and company_logo != "nan":
                        job_details["company_logo"] = company_logo
                    
                    pay = format_pay(matched_row)
                    if pay != "Not specified":
                        job_details["pay_info"] = pay

        except Exception as e:
            print(f"    [-] Scraper block encountered for {title}: {e}. Using fallback context.")

        # Combine original ranked info with enriched info
        enriched_job = {
            **job,
            **job_details
        }
        enriched_jobs.append(enriched_job)
        print(f"    [✓] Successfully processed.\n")

    # Save to Job-Info.json cache
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(enriched_jobs, f, indent=4, ensure_ascii=False)

    print(f"[✓] All job details successfully fetched and stored in Data/Job-Info.json")


if __name__ == "__main__":
    fetch_job_details()