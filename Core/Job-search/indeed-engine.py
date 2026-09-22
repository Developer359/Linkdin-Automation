import json
import os
import re
import sys
import time
from pathlib import Path
from jobspy import scrape_jobs

# Ensure local module import path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from job_quries import CATEGORY_ROLE_KEYWORDS, SEARCH_QUERIES
except ImportError:
    from job_quries import CATEGORY_ROLE_KEYWORDS
    SEARCH_QUERIES = {}

CATEGORY_FILE_MAP = {
    "Frontend, Full Stack & Backend": "Fullstack.json",
    "AI & Data Engineer": "AIEngineer.json",
    "Mobile Developer": "MobileDeveloper.json",
    "UI/UX & Graphic Designer": "Designer.json",
    "Software & DevOps Engineer": "SoftwareEngineer.json"
}

BASE_DIR = Path(__file__).resolve().parents[2]
CACHE_DIR = BASE_DIR / "Data" / "Job-Result-cache"


def clean_text(text: str) -> str:
    """Removes tags like (Remote), (Hybrid), punctuation, and normalizes text for matching."""
    text = re.sub(r'\((remote|hybrid|onsite|full-time|part-time|contract)\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    return ' '.join(text.lower().split())


def build_search_term(category: str) -> str:
    if category in SEARCH_QUERIES:
        base = SEARCH_QUERIES[category]
    else:
        keywords = CATEGORY_ROLE_KEYWORDS.get(category, [category])
        base = " OR ".join(f'"{kw}"' if " " in kw else kw for kw in keywords[:5])
    
    # Automatically add junior, mid, entry, and intern terms to the search query
    return f"{base} (junior OR entry OR intern OR mid OR associate)"


def run_indeed_engine():
    """Scrapes Indeed, preserves existing LinkedIn jobs in cache, and appends unique Indeed jobs below them."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    print("[*] Starting Indeed Engine Scraping Loop...\n")

    for category, filename in CATEGORY_FILE_MAP.items():
        search_term = build_search_term(category)
        output_file_path = CACHE_DIR / filename
        
        print(f" -> Category: [{category}]")
        print(f"    Searching Indeed for: {search_term}")

        # Load existing jobs (e.g. LinkedIn jobs) so we don't overwrite them
        jobs_list = []
        seen_urls = set()
        seen_companies = set()
        seen_titles = set()

        if output_file_path.exists():
            try:
                with open(output_file_path, "r", encoding="utf-8") as f:
                    existing_jobs = json.load(f)
                    if isinstance(existing_jobs, list):
                        for j in existing_jobs:
                            u = str(j.get("job_url", "") or "").strip()
                            c = clean_text(str(j.get("company", "") or "").strip())
                            t = clean_text(str(j.get("title", "") or "").strip())
                            if u: seen_urls.add(u)
                            if c: seen_companies.add(c)
                            if t: seen_titles.add(t)
                            jobs_list.append(j)
                print(f"    [i] Loaded {len(jobs_list)} existing jobs from cache.")
            except Exception as e:
                print(f"    [!] Warning: Could not read existing cache file: {e}")

        try:
            # Fetch raw jobs with country_indeed set to Pakistan
            df = scrape_jobs(
                site_name=["indeed"],
                search_term=search_term,
                location="Pakistan",
                country_indeed="pakistan",
                results_wanted=15,
                hours_old=24,
                verbose=0
            )

            new_indeed_count = 0
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    raw_title = str(row.get("title", "") or "").strip()
                    raw_company = str(row.get("company", "") or "").strip()
                    job_url = str(row.get("job_url", "") or "").strip()

                    if not raw_title or not raw_company:
                        continue

                    # Filter out senior, manager, lead, director, etc., from titles
                    title_lower = raw_title.lower()
                    if any(bad_word in title_lower for bad_word in ["senior", "sr.", "manager", "lead", "director", "head", "principal", "vp"]):
                        continue

                    cleaned_title = clean_text(raw_title)
                    cleaned_company = clean_text(raw_company)

                    # 1. Block duplicate URLs
                    if job_url in seen_urls:
                        continue

                    # 2. Block agency spam (Max 1 job per company per category)
                    if cleaned_company in seen_companies:
                        continue

                    # 3. Block reworded duplicate titles in the same category
                    if cleaned_title in seen_titles:
                        continue

                    # Mark keys as seen
                    seen_urls.add(job_url)
                    seen_companies.add(cleaned_company)
                    seen_titles.add(cleaned_title)

                    job_data = {
                        "title": raw_title,
                        "company": raw_company,
                        "location": str(row.get("location", "Pakistan") or "Pakistan").strip(),
                        "job_url": job_url,
                        "date_posted": str(row.get("date_posted", "") or "").strip(),
                        "source": "Indeed"
                    }
                    jobs_list.append(job_data)
                    new_indeed_count += 1

                    # Stop after adding 5 new Indeed jobs
                    if new_indeed_count == 5:
                        break

            with open(output_file_path, "w", encoding="utf-8") as f:
                json.dump(jobs_list, f, indent=4, ensure_ascii=False)

            print(f"    [✓] Appended {new_indeed_count} Indeed jobs -> Total unique jobs in {filename}: {len(jobs_list)}\n")

        except Exception as e:
            print(f"    [!] Error scraping category '{category}': {e}")

        time.sleep(2)

    print("[✓] Indeed Engine completed successfully and merged below LinkedIn jobs.")


if __name__ == "__main__":
    run_indeed_engine()