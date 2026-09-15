import json
import os
import sys
import time
from pathlib import Path
from jobspy import scrape_jobs

# Add current directory to Python path for seamless relative imports
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# Import queries directly from job_quries.py
try:
    from job_quries import CATEGORY_ROLE_KEYWORDS, SEARCH_QUERIES
except ImportError:
    from job_quries import CATEGORY_ROLE_KEYWORDS
    SEARCH_QUERIES = {}

# Map category names to their respective cache JSON files
CATEGORY_FILE_MAP = {
    "Frontend, Full Stack & Backend": "Fullstack.json",
    "AI & Data Engineer": "AIEngineer.json",
    "Mobile Developer": "MobileDeveloper.json",
    "UI/UX & Graphic Designer": "Designer.json",
    "Software & DevOps Engineer": "SoftwareEngineer.json"
}

# Resolve target cache directory (Data/Job-Result-cache)
BASE_DIR = Path(__file__).resolve().parents[2]
CACHE_DIR = BASE_DIR / "Data" / "Job-Result-cache"


def build_search_term(category: str) -> str:
    """Builds an OR search query if SEARCH_QUERIES isn't explicitly defined."""
    if category in SEARCH_QUERIES:
        return SEARCH_QUERIES[category]
    keywords = CATEGORY_ROLE_KEYWORDS.get(category, [category])
    return " OR ".join(f'"{kw}"' if " " in kw else kw for kw in keywords[:5])


def run_linkedin_engine():
    """Scrapes LinkedIn category by category and writes 5 latest jobs directly to JSON cache files."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    print("[*] Starting LinkedIn Engine Scraping Loop...\n")

    for category, filename in CATEGORY_FILE_MAP.items():
        search_term = build_search_term(category)
        output_file_path = CACHE_DIR / filename
        
        print(f" -> Category: [{category}]")
        print(f"    Searching LinkedIn for: {search_term}")

        try:
            df = scrape_jobs(
                site_name=["linkedin"],
                search_term=search_term,
                location="Pakistan",
                results_wanted=5,
                hours_old=24,
                verbose=0
            )

            jobs_list = []
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    job_data = {
                        "title": str(row.get("title", "") or "").strip(),
                        "company": str(row.get("company", "") or "").strip(),
                        "location": str(row.get("location", "Pakistan") or "Pakistan").strip(),
                        "job_url": str(row.get("job_url", "") or "").strip(),
                        "date_posted": str(row.get("date_posted", "") or "").strip(),
                        "source": "LinkedIn"
                    }
                    jobs_list.append(job_data)

            # Restrict output count to strict top 5
            jobs_list = jobs_list[:5]

            with open(output_file_path, "w", encoding="utf-8") as f:
                json.dump(jobs_list, f, indent=4, ensure_ascii=False)

            print(f"    [✓] Scraped {len(jobs_list)} jobs -> Saved to Data/Job-Result-cache/{filename}\n")

        except Exception as e:
            print(f"    [!] Error scraping category '{category}': {e}")
            with open(output_file_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=4)

        time.sleep(2)

    print("[✓] LinkedIn Engine completed processing all categories.")


if __name__ == "__main__":
    run_linkedin_engine()