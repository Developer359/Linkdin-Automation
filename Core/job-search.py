import os
import json
import re
import warnings
import logging
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed

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
FALLBACK_HOURS_OLD = HOURS_OLD * 3      # used only if a query comes up short
FALLBACK_MAX_AGE_DAYS = MAX_AGE_DAYS * 3
SITES = ["indeed", "linkedin"]
TARGET_PER_QUERY = 10
RESULTS_WANTED_PER_SITE = 40     # was 80 — fewer pages to paginate through = fewer Indeed timeouts, faster overall
SITE_RETRY_ATTEMPTS = 3          # retry a site immediately if it errors (timeout, connection reset, etc.)

# --- SENIORITY KEYWORDS (Title MUST contain at least one of these) ---
TITLE_KEYWORDS = [
    "junior", "jr", "entry", "entry-level", "intern", "internship",
    "trainee", "fresher", "new grad", "graduate", "grad", "remote-internship"
]
TITLE_REGEX = re.compile(r'\b(' + '|'.join([re.escape(k) for k in TITLE_KEYWORDS]) + r')\b', re.IGNORECASE)

# --- ROLE KEYWORDS (Title must ALSO be relevant to what the query actually asked for) ---
# Keyed by category so "Mobile Developer" doesn't pull generic "Software Engineer" postings.
CATEGORY_ROLE_KEYWORDS = {
    "Frontend, Full Stack & Backend": [
        "frontend", "front-end", "front end", "backend", "back-end", "back end",
        "full stack", "fullstack", "full-stack", "web developer", "java",
        "Html", "react", "next.js", "nextjs", "node", "javascript", "typescript"
    ],
    "AI & Data Engineer": [
        "ai", "artificial intelligence", "machine learning", "ml engineer", "data scientist",
        "data analyst", "data engineer", "llm", "langchain", "automation engineer", "python developer"
    ],
    "Mobile Developer": [
        "mobile", "ios", "android", "swift", "kotlin", "react native", "flutter", "expo",
        "app developer", "mobile developer", "mobile engineer"
    ],
    "UI/UX & Graphic Designer": [
        "ui", "ux", "ui/ux", "product design", "product designer", "graphic design",
        "graphic designer", "figma", "wireframe", "visual designer", "designer"
    ],
    "Software & DevOps Engineer": [
        "devops", "dev ops", "cloud engineer", "site reliability", "sre", "platform engineer",
        "infrastructure", "software engineer", "software developer", "docker", "kubernetes", "aws"
    ],
}

# Generic words to ignore when deriving role keywords automatically for an unlisted category
STOPWORDS = {
    "junior", "jr", "entry", "entry-level", "intern", "internship", "trainee", "fresher",
    "new", "grad", "graduate", "remote-internship", "developer", "engineer", "and", "the",
    "for", "with", "of", "a", "an"
}


def safe_str(value, default: str = "") -> str:
    if value is None or pd.isna(value):
        return default
    return str(value)


def derive_role_keywords(query: str) -> list[str]:
    """Fallback: pull meaningful terms out of the query itself if category isn't in the map."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9+\.#]*", query)
    keywords = [w.lower() for w in words if w.lower() not in STOPWORDS and len(w) > 2]
    return keywords or [query.lower()]


def evaluate_job_inline(row, role_keywords: list[str]) -> bool:
    """
    1. Title must contain a seniority keyword (junior/entry/intern/grad...).
    2. Title must ALSO be relevant to the role the query was actually about.
    3. Location must be remote (reject explicit on-site/hybrid).
    """
    title = safe_str(row.get("title"))
    title_lower = title.lower()
    location = safe_str(row.get("location")).lower()

    if not bool(TITLE_REGEX.search(title)):
        return False

    if not any(kw in title_lower for kw in role_keywords):
        return False

    if "on-site" in location or "onsite" in location or "hybrid" in location:
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


def scrape_site(site: str, query: str, hours_old: int):
    last_error = None
    for attempt in range(1, SITE_RETRY_ATTEMPTS + 1):
        try:
            return site, scrape_jobs(
                site_name=[site],
                search_term=query,
                is_remote=True,
                results_wanted=RESULTS_WANTED_PER_SITE,
                hours_old=hours_old,
                country_indeed="USA",
                linkedin_fetch_description=False,  # kept off for speed
            )
        except Exception as e:
            last_error = e
            if attempt < SITE_RETRY_ATTEMPTS:
                print(f"  -> {site} attempt {attempt} failed ({e}), retrying...")
            continue
    print(f"  -> Error scraping {site} after {SITE_RETRY_ATTEMPTS} attempts: {last_error}")
    return site, None


def build_job_entry(row, site, category, job_type, query, age_days):
    company_url = safe_str(row.get("company_url") or row.get("company_url_direct"))
    company_logo = safe_str(
        row.get("company_logo") or row.get("logo_photo_url") or row.get("company_logo_url")
    )
    return {
        "url": row.get("job_url"),
        "title": safe_str(row.get("title")),
        "description": "",  # Description skipped per request
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


def collect_from_df(jobs_df, site, category, job_type, query, role_keywords, seen_urls,
                     query_jobs, max_age_days):
    if jobs_df is None or jobs_df.empty:
        return

    for _, row in jobs_df.iterrows():
        if len(query_jobs) >= TARGET_PER_QUERY:
            break

        url = row.get("job_url")
        if not url or pd.isna(url) or url in seen_urls:
            continue

        if not evaluate_job_inline(row, role_keywords):
            continue

        age_days = days_since(row.get("date_posted"))
        if age_days is not None and age_days > max_age_days:
            continue

        seen_urls.add(url)
        job_entry = build_job_entry(row, site, category, job_type, query, age_days)
        query_jobs.append(job_entry)
        print(f"  + [PASSED] [{job_entry['website_name']}] {job_entry['title']} ({job_entry['company_name']})")


def execute_job_search():
    query_items = load_and_prepare_queries()
    all_jobs = []
    seen_urls = set()

    print(f"--- Running Job Scraper | Role-Matched + Parallel Sites Per Query | Target: {TARGET_PER_QUERY} Jobs/Query ---")

    for i, item in enumerate(query_items):
        query = item["query"]
        category = item["category"]
        job_type = item["job_type"]
        role_keywords = CATEGORY_ROLE_KEYWORDS.get(category, derive_role_keywords(query))

        print(f"\n[Query {i+1}/{len(query_items)}] [{category}] [{job_type}]")
        query_jobs = []

        # --- Pass 1: normal recency window, both sites fetched in parallel ---
        with ThreadPoolExecutor(max_workers=len(SITES)) as executor:
            futures = [executor.submit(scrape_site, site, query, HOURS_OLD) for site in SITES]
            for future in as_completed(futures):
                site, jobs_df = future.result()
                collect_from_df(jobs_df, site, category, job_type, query, role_keywords,
                                 seen_urls, query_jobs, MAX_AGE_DAYS)

        # --- Pass 2 (fallback): only runs if still short, widens the recency window ---
        if len(query_jobs) < TARGET_PER_QUERY:
            with ThreadPoolExecutor(max_workers=len(SITES)) as executor:
                futures = [executor.submit(scrape_site, site, query, FALLBACK_HOURS_OLD) for site in SITES]
                for future in as_completed(futures):
                    site, jobs_df = future.result()
                    collect_from_df(jobs_df, site, category, job_type, query, role_keywords,
                                     seen_urls, query_jobs, FALLBACK_MAX_AGE_DAYS)

        all_jobs.extend(query_jobs)
        print(f"  -> Collected {len(query_jobs)}/{TARGET_PER_QUERY} verified jobs for query {i+1}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"jobs": all_jobs}, f, indent=4, ensure_ascii=False)

    print(f"\nSaved total {len(all_jobs)} strictly filtered jobs to '{OUTPUT_FILE}'")


if __name__ == "__main__":
    execute_job_search()