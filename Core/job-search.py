import os
import json
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
HOURS_OLD = MAX_AGE_DAYS * 24  # 24 hours limit
SITES = ["indeed", "linkedin"]
TARGET_PER_QUERY = 5
RESULTS_WANTED_PER_SITE = 20   # Increased pool to ensure 5 strict remote matches per query


def load_and_prepare_queries() -> list[dict]:
    """Reads queries, categories, and job types directly from query.json."""
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


def safe_str(value, default: str = "") -> str:
    if value is None or pd.isna(value):
        return default
    return str(value)


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


def is_strictly_remote(row) -> bool:
    """Enforces double verification that the job is 100% remote."""
    is_remote_flag = row.get("is_remote")
    if is_remote_flag is True:
        return True

    location = safe_str(row.get("location")).lower()
    title = safe_str(row.get("title")).lower()
    desc = safe_str(row.get("description")).lower()

    # Match common remote indicators
    remote_keywords = ["remote", "work from home", "wfh", "anywhere", "telecommute"]
    
    if any(kw in location for kw in remote_keywords):
        return True
    if any(kw in title for kw in remote_keywords):
        return True
    if "100% remote" in desc or "fully remote" in desc:
        return True

    return False


def execute_job_search():
    query_items = load_and_prepare_queries()
    all_jobs = []
    seen_urls = set()

    print(f"--- Running Job Scraper | STRICT REMOTE ONLY | Target: {TARGET_PER_QUERY} Jobs/Query ---")

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
                    is_remote=True,  # Primary API level remote filter
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

                # STRICT REMOTE FILTER
                if not is_strictly_remote(row):
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
                    "description": safe_str(row.get("description"))[:2000],
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
                print(f"  + [REMOTE] [{job_entry['website_name']}] {job_entry['title']} ({job_entry['company_name']})")

        all_jobs.extend(query_jobs)
        print(f"  -> Collected {len(query_jobs)}/10 remote jobs for query {i+1}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"jobs": all_jobs}, f, indent=4, ensure_ascii=False)

    print(f"\nSaved total {len(all_jobs)} strict remote jobs to '{OUTPUT_FILE}'")


if __name__ == "__main__":
    execute_job_search()