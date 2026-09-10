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
HOURS_OLD = MAX_AGE_DAYS * 24  # Strictly under 24 hours
MAX_SALARY_YEARLY = 60000      # STRICT CAP: Maximum $60,000 USD/year

SITES = ["indeed", "linkedin"]

RESULTS_WANTED_PER_SITE = 40   # Fetches larger pool to isolate low-salary junior/intern roles
TARGET_PER_QUERY = 10

# Forbidden words: Senior, Manager, Tech Lead, Level II, Level III, etc.
EXPERT_KEYWORDS = [
    "senior", "sr", "sr.", "lead", "principal", "architect", "staff", 
    "director", "head", "vp", "manager", "expert", "chief", "team lead",
    "executive", "founder", "tech lead", "lead engineer", "ii", "iii", "iv",
    "level 2", "level 3", "level ii", "level iii"
]
EXPERT_REGEX = re.compile(r'\b(' + '|'.join([re.escape(k) for k in EXPERT_KEYWORDS]) + r')\b', re.IGNORECASE)


def load_and_prepare_queries() -> list[dict]:
    target_file = CACHE_FILE
    if not os.path.exists(target_file):
        target_file = "query.json"

    if not os.path.exists(target_file):
        raise FileNotFoundError("Cache file 'query.json' not found in root directory.")

    with open(target_file, "r") as f:
        data = json.load(f)
        queries_data = data.get("queries", [])

    formatted_queries = []
    for item in queries_data:
        if isinstance(item, dict):
            q = item.get("query", "").strip()
            j_type = item.get("category") or item.get("job_type", "Junior / Internship")
            j_type = str(j_type).strip()
            if q:
                formatted_queries.append({"query": q, "job_type": j_type})
        elif isinstance(item, str):
            q = item.strip()
            if q:
                formatted_queries.append({"query": q, "job_type": "Junior / Internship"})

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


def is_salary_within_limit(row) -> bool:
    """Removes any job exceeding $60,000/year or $30/hour."""
    min_amt = row.get("min_amount")
    max_amt = row.get("max_amount")
    interval = str(row.get("interval", "")).lower()

    check_amt = max_amt if not pd.isna(max_amt) and max_amt else min_amt
    if pd.isna(check_amt) or not check_amt:
        return True  # Keep unstated pay unless title fails level checks

    try:
        val = float(check_amt)
        if "hour" in interval:
            yearly_equiv = val * 2080  # 40 hrs/wk * 52 wks
        elif "month" in interval:
            yearly_equiv = val * 12
        elif "week" in interval:
            yearly_equiv = val * 52
        else:
            yearly_equiv = val

        return yearly_equiv <= MAX_SALARY_YEARLY
    except (ValueError, TypeError):
        return True


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


def is_valid_title(title: str) -> bool:
    """Blocks any title with Senior, Manager, or Level II/III modifiers."""
    return not bool(EXPERT_REGEX.search(title))


def detect_seniority_level(title: str, description: str) -> str:
    """Classifies job strictly into Internship or Junior."""
    text = f"{title} {description}".lower()
    if re.search(r'\b(intern|internship|trainee)\b', text):
        return "Internship"
    return "Junior"


def calculate_quality_score(job: dict) -> int:
    """Prioritizes explicit Junior and Internship postings."""
    score = 0
    level = job.get("seniority_level")
    desc_lower = job.get("description", "").lower()

    if level == "Junior":
        score += 10
    elif level == "Internship":
        score += 10

    if job.get("pay_info") and job["pay_info"] != "Not specified":
        score += 3

    perks = ["health", "bonus", "stipend", "pto", "vacation"]
    if any(perk in desc_lower for perk in perks):
        score += 2

    return score


def scrape_site_candidates(site: str, query: str, job_type: str, query_index: int, seen_urls: set) -> list[dict]:
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
        print(f"  -> Error scraping {site} for query {query_index}: {e}")
        return []

    if jobs_df is None or jobs_df.empty:
        return []

    candidates = []
    for _, row in jobs_df.iterrows():
        url = row.get("job_url")
        if not url or pd.isna(url) or url in seen_urls:
            continue

        title = safe_str(row.get("title"))

        # FILTER 1: Strict title check (No Senior/Manager/Engineer II)
        if not is_valid_title(title):
            continue

        # FILTER 2: Strict salary check (Max $60,000/year)
        if not is_salary_within_limit(row):
            continue

        age_days = days_since(row.get("date_posted"))
        if age_days is not None and age_days > MAX_AGE_DAYS:
            continue

        company_name = safe_str(row.get("company"), "Unknown")
        website_name = safe_str(row.get("site"), site)
        description = safe_str(row.get("description"))[:2000]
        tags = [w for w in title.split() if len(w) > 3]
        pay_info = format_pay(row)

        company_url = safe_str(row.get("company_url") or row.get("company_url_direct"))
        company_logo = safe_str(
            row.get("company_logo") or row.get("logo_photo_url") or row.get("company_logo_url")
        )

        seniority_level = detect_seniority_level(title, description)

        job_entry = {
            "url": url,
            "title": title,
            "description": description,
            "tags": tags,
            "pay_info": pay_info,
            "company_name": company_name,
            "company_url": company_url if company_url else None,
            "company_logo": company_logo if company_logo else None,
            "website_name": website_name,
            "posted_days_ago": age_days,
            "location": safe_str(row.get("location")),
            "job_type": job_type,
            "seniority_level": seniority_level,
            "query_index": query_index,
            "query_used": query,
        }

        job_entry["quality_score"] = calculate_quality_score(job_entry)
        candidates.append(job_entry)

    return candidates


def execute_job_search(query_items: list[dict]):
    all_jobs = []
    seen_urls = set()

    print(
        f"--- Running Job Engine | Strictly <= $60,000/yr | Junior & Internship Only "
        f"| Target: {TARGET_PER_QUERY} Jobs/Query | Max Age: 24h ---"
    )

    for i, item in enumerate(query_items):
        query = item["query"]
        job_type = item["job_type"]
        print(f"\n[Query {i+1}/{len(query_items)}] [{job_type}] {query}")

        raw_query_candidates = []
        for site in SITES:
            site_candidates = scrape_site_candidates(
                site=site,
                query=query,
                job_type=job_type,
                query_index=i + 1,
                seen_urls=seen_urls,
            )
            raw_query_candidates.extend(site_candidates)

        sorted_candidates = sorted(raw_query_candidates, key=lambda x: x["quality_score"], reverse=True)
        top_10_jobs = sorted_candidates[:TARGET_PER_QUERY]

        for job in top_10_jobs:
            seen_urls.add(job["url"])
            del job["quality_score"]
            all_jobs.append(job)

            print(f"  [{job['website_name']}] [{job['seniority_level']}] {job['title']}")
            print(f"      Link: {job['url']}")
            print(f"      Pay: {job['pay_info']} | Company: {job['company_name']}")

        print(f"  -> Kept Top {len(top_10_jobs)} Junior/Intern Job(s) (<= $60k/yr) for this query.")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"jobs": all_jobs}, f, indent=4, ensure_ascii=False)

    site_counts = {}
    for job in all_jobs:
        site_counts[job["website_name"]] = site_counts.get(job["website_name"], 0) + 1
    split_str = ", ".join(f"{site}: {count}" for site, count in site_counts.items())

    print(f"\nSaved total {len(all_jobs)} junior job(s) (<= $60k/yr, <= 24h old) to job_results_cache.json")
    print(f"Site distribution -> {split_str}")
    return all_jobs


if __name__ == "__main__":
    search_queries = load_and_prepare_queries()
    execute_job_search(search_queries)