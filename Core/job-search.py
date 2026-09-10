import os
import json
import re
import warnings
import logging
from datetime import datetime, date
import pandas as pd
from dotenv import load_dotenv
from jobspy import scrape_jobs

warnings.filterwarnings("ignore")
logging.getLogger().setLevel(logging.ERROR)

load_dotenv()

CACHE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../query.json"))
OUTPUT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../job_results_cache.json"))

MAX_AGE_DAYS = 1
HOURS_OLD = MAX_AGE_DAYS * 24  
SITES = ["indeed", "linkedin"]
TARGET_PER_QUERY = 15          # Target 15 jobs per query
RESULTS_WANTED_PER_SITE = 50   # Expanded pool since title filtering is strict

# --- NEGATIVE KEYWORDS (Checks entire text: Title + Location + Description) ---
NEGATIVE_KEYWORDS = [
    "senior", "sr", "lead", "principal", "architect", "staff", 
    "director", "manager", "chief", "vp", "head", "mid", "mid-level", "middle",
    "3+ years", "4+ years", "5+ years", "3 years", "4 years", "5 years",
    "hybrid", "on-site", "onsite", "in-office", "in office"
]
NEGATIVE_REGEX = re.compile(r'\b(' + '|'.join([re.escape(k) for k in NEGATIVE_KEYWORDS]) + r')\b', re.IGNORECASE)

# --- STRICT TITLE KEYWORDS (MUST appear in the Job Title) ---
TITLE_POSITIVE_KEYWORDS = [
    "junior", "jr", "entry", "entry-level", "intern", "internship", 
    "trainee", "fresher", "new grad", "graduate"
]
TITLE_POSITIVE_REGEX = re.compile(r'\b(' + '|'.join([re.escape(k) for k in TITLE_POSITIVE_KEYWORDS]) + r')\b', re.IGNORECASE)


def safe_str(value, default: str = "") -> str:
    if value is None or pd.isna(value):
        return default
    return str(value)


def evaluate_job_inline(row) -> bool:
    """Strict inline filter: Drops if senior/hybrid anywhere, and requires junior/intern explicitly in the TITLE."""
    title = safe_str(row.get("title"))
    location = safe_str(row.get("location"))
    desc = safe_str(row.get("description"))
    text_to_search = f"{title} {location} {desc}"

    # 1. Drop if any negative keyword (senior, hybrid, etc.) appears anywhere
    if bool(NEGATIVE_REGEX.search(text_to_search)):
        return False

    # 2. STICKY RULE: Title MUST contain Junior, Intern, Entry Level, etc.
    if not bool(TITLE_POSITIVE_REGEX.search(title)):
        return False

    return True


def load_and_prepare_queries() -> list[dict]:
    target_file = CACHE_FILE if os.path.exists(CACHE_FILE) else "query.json"

    if not os.path.exists(target_file):
        raise FileNotFoundError(f"Cache file '{target_file}' not found.")

    with open(target_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        queries_data = data.get("queries", [])

    formatted_queries = []
    for item in queries_data:
        if isinstance(item, dict):
            q = item.get("query", "").strip()
            category = item.get("category", "General").strip()
            job_type = item.get("job_type", "Junior / Entry Level").strip()
            if q:
                formatted_queries.append({
                    "query": q,
                    "category": category,
                    "job_type": job_type
                })

    return formatted_queries


def days_since(posted) -> int | None:
    if posted is None or pd.isna(posted):
        return None
    if isinstance(posted, datetime):
        posted_date = posted.date()
    elif isinstance(posted, date):
        posted_date = posted
    else:
        try:
            posted_date = pd.to_datetime(posted).date()
        except (ValueError, TypeError):
            return None
    return max((date.today() - posted_date).days, 0)


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


def execute_job_search():
    query_items = load_and_prepare_queries()
    all_jobs = []
    seen_urls = set()

    print(f"--- Running Job Scraper | STRICT TITLE FILTER | Target: {TARGET_PER_QUERY} Jobs/Query ---")

    for i, item in enumerate(query_items):
        query = item["query"]
        category = item["category"]
        job_type = item["job_type"]

        print(f"\n[Query {i+1}/{len(query_items)}] [{category}] [{job_type}]")
        query_jobs = []

        for site in SITES:
            if len(query_jobs) >= TARGET_PER_QUERY:
                break

            try:
                jobs_df = scrape_jobs(
                    site_name=[site],
                    search_term=query,
                    is_remote=True,
                    results_wanted=RESULTS_WANTED_PER_SITE,
                    hours_old=HOURS_OLD,
                    country_indeed="USA",
                    description_format="markdown",
                    linkedin_fetch_description=True,
                )
            except Exception as e:
                print(f"  -> Error scraping {site}: {e}")
                continue

            if jobs_df is None or jobs_df.empty:
                continue

            for _, row in jobs_df.iterrows():
                if len(query_jobs) >= TARGET_PER_QUERY:
                    break

                url = row.get("job_url")
                if not url or pd.isna(url) or url in seen_urls:
                    continue

                if not evaluate_job_inline(row):
                    continue

                age_days = days_since(row.get("date_posted"))
                if age_days is not None and age_days > MAX_AGE_DAYS:
                    continue

                seen_urls.add(url)
                company_url = safe_str(row.get("company_url") or row.get("company_url_direct"))
                company_logo = safe_str(
                    row.get("company_logo") or row.get("logo_photo_url") or row.get("company_logo_url")
                )

                job_entry = {
                    "url": url,
                    "title": safe_str(row.get("title")),
                    "description": safe_str(row.get("description")),  # Full description saved
                    "company_name": safe_str(row.get("company"), "Unknown"),
                    "company_url": company_url if company_url else None,
                    "company_logo": company_logo if company_logo else None,
                    "website_name": safe_str(row.get("site"), site),
                    "location": safe_str(row.get("location"), "Remote"),
                    "is_remote": True,
                    "pay_info": format_pay(row),
                    "category": category,
                    "job_type": job_type,
                    "posted_days_ago": age_days,
                    "query_used": query,
                }

                query_jobs.append(job_entry)
                print(f"  + [PASSED] [{job_entry['website_name']}] {job_entry['title']} ({job_entry['company_name']})")

        all_jobs.extend(query_jobs)
        print(f"  -> Collected {len(query_jobs)}/{TARGET_PER_QUERY} verified jobs for query {i+1}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"jobs": all_jobs}, f, indent=4, ensure_ascii=False)

    print(f"\nSaved total {len(all_jobs)} strictly filtered jobs to '{OUTPUT_FILE}'")


if __name__ == "__main__":
    execute_job_search()