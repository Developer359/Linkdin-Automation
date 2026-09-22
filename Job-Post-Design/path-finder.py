import os
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# Correct path resolution to project root
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)

INPUT_FILE = os.path.join(PROJECT_ROOT, "Data", "Job-summery.json")
OUTPUT_JSON_FILE = os.path.join(PROJECT_ROOT, "Job-Post-Design", "Post-data.json")
HTML_TEMPLATE_PATH = Path(os.path.join(PROJECT_ROOT, "Job-Post-Design", "Design-Template", "index.html")).resolve()
OUTPUT_IMG_DIR = os.path.join(PROJECT_ROOT, "Job-Post-Design", "Generated-Images")


def sanitize_filename(name: str) -> str:
    """Helper to sanitize job titles into safe filenames."""
    return "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in name).strip().replace(" ", "-")


def process_and_capture_jobs():
    # --- STEP 1: Load and process data from Job-summery.json into Post-data.json ---
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Could not find input file at '{INPUT_FILE}'")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    if not jobs:
        print("No jobs found in Job-summery.json to process.")
        return

    extracted_posts = []
    for job in jobs:
        post_item = {
            "job_title": job.get("job_title", ""),
            "job_summary": job.get("job_summary", ""),
            "tags": job.get("tags", []),
            "work_location": job.get("workplace_type", "Not specified"),
            "color_code": job.get("color_code", "#A0AEC0")
        }
        extracted_posts.append(post_item)

    # Group into batches of 5 jobs per post file as requested
    chunk_size = 5
    batched_posts = [extracted_posts[i:i + chunk_size] for i in range(0, len(extracted_posts), chunk_size)]

    # Ensure output directory exists and save to Post-data.json
    os.makedirs(os.path.dirname(OUTPUT_JSON_FILE), exist_ok=True)
    with open(OUTPUT_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(batched_posts, f, indent=4, ensure_ascii=False)

    print(f"Successfully processed {len(extracted_posts)} jobs into batches of 5 and saved to '{OUTPUT_JSON_FILE}'")

    # --- STEP 2: Launch local Chrome browser and capture dynamic job cards ---
    if not HTML_TEMPLATE_PATH.exists():
        print(f"Error: Could not find HTML template at '{HTML_TEMPLATE_PATH}'")
        return

    os.makedirs(OUTPUT_IMG_DIR, exist_ok=True)

    print(f"\n--- Starting Dynamic Job Post Image Generator ({len(extracted_posts)} total jobs) ---")

    with sync_playwright() as p:
        # Launch local system Chrome to bypass download blocks
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page()

        # Set viewport size wide and tall enough for the canvas
        page.set_viewport_size({"width": 1280, "height": 1000})

        global_idx = 1
        for batch in batched_posts:
            for job in batch:
                title = job.get("job_title", "Job Title")
                summary = job.get("job_summary", "")
                tags = job.get("tags", [])
                work_location = job.get("work_location", "Remote")
                color_code = job.get("color_code", "#A0AEC0")

                print(f"[{global_idx}/{len(extracted_posts)}] Processing & Capturing: {title}...")

                # Securely format local Windows file path into a file:// URI
                page.goto(HTML_TEMPLATE_PATH.as_uri(), wait_until="domcontentloaded")

                # Inject dynamic job data and color code directly into the DOM
                page.evaluate(
                    """({ title, summary, tags, workLocation, colorCode }) => {
                        const titleEl = document.getElementById('job-title');
                        if (titleEl) titleEl.innerText = title;

                        const summaryEl = document.getElementById('job-summary');
                        if (summaryEl) summaryEl.innerText = summary;

                        const locEl = document.getElementById('work-location');
                        if (locEl) locEl.innerText = workLocation;

                        const tagsContainer = document.getElementById('job-tags');
                        if (tagsContainer && tags && tags.length > 0) {
                            const tagSpans = tagsContainer.querySelectorAll('span');
                            tags.forEach((tag, i) => {
                                if (tagSpans[i]) tagSpans[i].innerText = tag;
                            });
                        }

                        const card = document.getElementById('job-post-card');
                        if (card) {
                            card.style.borderColor = colorCode;
                            card.style.borderWidth = '4px';
                        }
                    }""",
                    {
                        "title": title,
                        "summary": summary,
                        "tags": tags,
                        "workLocation": work_location,
                        "colorCode": color_code,
                    },
                )

                # Target the main card container and ensure visibility
                job_card = page.locator("#job-post-card")
                job_card.wait_for(state="visible", timeout=15000)

                safe_title = sanitize_filename(title)
                output_image_path = os.path.join(OUTPUT_IMG_DIR, f"{global_idx}_{safe_title}.png")

                # Capture clean screenshot of the card
                job_card.screenshot(path=output_image_path)
                print(f"  ✓ Saved image to: {output_image_path}")

                # 2-second pause between queries
                time.sleep(2)
                global_idx += 1

        browser.close()

    print(f"\nDone! All data processed and card images generated successfully.")


if __name__ == "__main__":
    process_and_capture_jobs()