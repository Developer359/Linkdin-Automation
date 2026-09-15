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
        return SEARCH_QUERIES[category]
    keywords = CATEGORY_ROLE_KEYWORDS.get(category, [category])
    return " OR ".join(f'"{kw}"' if " " in kw else kw for kw in keywords[:5])


def run_linkedin_engine():
    """Scrapes LinkedIn, enforces 1 job per company, filters duplicate titles/URLs, and saves max 5 unique jobs."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    print("[*] Starting LinkedIn Engine Scraping Loop...\n")

    for category, filename in CATEGORY_FILE_MAP.items():
        search_term = build_search_term(category)
        output_file_path = CACHE_DIR / filename
        
        print(f" -> Category: [{category}]")
        print(f"    Searching LinkedIn for: {search_term}")

        try:
            # Fetch 15 raw jobs to give enough room for strict deduplication
            df = scrape_jobs(
                site_name=["linkedin"],
                search_term=search_term,
                location="Pakistan",
                results_wanted=15,
                hours_old=24,
                verbose=0
            )

            jobs_list = []
            seen_urls = set()
            seen_companies = set()
            seen_titles = set()

            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    raw_title = str(row.get("title", "") or "").strip()
                    raw_company = str(row.get("company", "") or "").strip()
                    job_url = str(row.get("job_url", "") or "").strip()

                    if not raw_title or not raw_company:
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
                        "source": "LinkedIn"
                    }
                    jobs_list.append(job_data)

                    # Strictly enforce exactly 5 unique jobs max
                    if len(jobs_list) == 5:
                        break

            with open(output_file_path, "w", encoding="utf-8") as f:
                json.dump(jobs_list, f, indent=4, ensure_ascii=False)

            print(f"    [✓] Scraped {len(jobs_list)} 100% unique jobs -> Saved to Data/Job-Result-cache/{filename}\n")

        except Exception as e:
            print(f"    [!] Error scraping category '{category}': {e}")
            with open(output_file_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=4)

        time.sleep(2)

    print("[✓] LinkedIn Engine completed successfully with zero duplicates.")


if __name__ == "__main__":
    run_linkedin_engine()