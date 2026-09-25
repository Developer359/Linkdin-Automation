import os
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# Correct cross-platform path resolution using pathlib
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "Data" / "Job-summery.json"
OUTPUT_JSON_FILE = BASE_DIR / "Job-Post-Design" / "Post-data.json"
HTML_TEMPLATE_PATH = BASE_DIR / "Job-Post-Design" / "Design-Template" / "index.html"
OUTPUT_IMG_DIR = BASE_DIR / "Job-Post-Design" / "Generated-Images"


def sanitize_filename(name: str) -> str:
    """Helper to sanitize job titles into safe filenames."""
    return "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in name).strip().replace(" ", "-")


def process_and_capture_jobs():
    # --- STEP 1: Load and process data from Job-summery.json into Post-data.json ---
    if not DATA_FILE.exists():
        print(f"Error: Could not find input file at '{DATA_FILE}'")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
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
            "color_code": job.get("color_code", "#15172e")
        }
        extracted_posts.append(post_item)

    # Group into batches of 5 jobs per post file as requested
    chunk_size = 5
    batched_posts = [extracted_posts[i:i + chunk_size] for i in range(0, len(extracted_posts), chunk_size)]

    OUTPUT_JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(batched_posts, f, indent=4, ensure_ascii=False)

    print(f"Successfully processed {len(extracted_posts)} jobs into batches of 5 and saved to '{OUTPUT_JSON_FILE}'")

    # --- STEP 2: Launch browser and capture dynamic colored job cards ---
    if not HTML_TEMPLATE_PATH.exists():
        print(f"Error: Could not find HTML template at '{HTML_TEMPLATE_PATH}'")
        return

    OUTPUT_IMG_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n--- Starting Dynamic Colored Job Post Image Generator ({len(extracted_posts)} total jobs) ---")

    with sync_playwright() as p:
        # --- PERMANENT FIX: Use System Browser to Bypass Download Errors ---
        # Tries to use the already installed Google Chrome or MS Edge on your machine.
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            try:
                browser = p.chromium.launch(channel="msedge", headless=True)
            except Exception:
                browser = p.chromium.launch(headless=True) # Fallback to default Playwright browser
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
                color_code = job.get("color_code", "#15172e")

                print(f"[{global_idx}/{len(extracted_posts)}] Processing & Capturing: {title} (Color: {color_code})...")

                page.goto(HTML_TEMPLATE_PATH.as_uri(), wait_until="domcontentloaded")

                # Inject dynamic job data and color codes via CSS Variables into the DOM
                page.evaluate(
                    """({ title, summary, tags, workLocation, colorCode }) => {
                        const summaryEl = document.getElementById('job-summary');
                        if (summaryEl) summaryEl.innerText = summary;

                        const locEl = document.getElementById('work-location');
                        if (locEl) locEl.innerText = workLocation;

                        const tagsContainer = document.getElementById('job-tags');
                        if (tagsContainer && tags && tags.length > 0) {
                            const items = tagsContainer.querySelectorAll('li');
                            tags.forEach((tag, i) => {
                                if (items[i]) {
                                    const span = items[i].querySelector('span');
                                    if (span) span.innerText = tag;
                                    items[i].style.display = 'flex';
                                }
                            });
                            for (let j = tags.length; j < items.length; j++) {
                                items[j].style.display = 'none';
                            }
                        }

                        // Helper to lighten/darken hex colors for secondary accents
                        function adjustColor(hex, percent) {
                            if (!hex || !hex.startsWith('#')) return '#6b7499';
                            let num = parseInt(hex.replace("#",""), 16);
                            let amt = Math.round(2.55 * percent);
                            let R = (num >> 16) + amt;
                            let G = (num >> 8 & 0x00FF) + amt;
                            let B = (num & 0x0000FF) + amt;
                            return "#" + (
                                0x1000000 +
                                (R<255?(R<0?0:R):255)*0x10000 +
                                (G<255?(G<0?0:G):255)*0x100 +
                                (B<255?(B<0?0:B):255)
                            ).toString(16).slice(1);
                        }

                        const primaryColor = colorCode || '#15172e';
                        const secondaryColor = adjustColor(primaryColor, 35); // Lighter accent tint
                        const primaryDark = adjustColor(primaryColor, -20); // Darker shade for gradients

                        // Set CSS variables on the main card container
                        const card = document.getElementById('job-post-card');
                        if (card) {
                            card.style.setProperty('--primary-color', primaryColor);
                            card.style.setProperty('--secondary-color', secondaryColor);
                            card.style.setProperty('--primary-dark', primaryDark);
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

                job_card = page.locator("#job-post-card")
                job_card.wait_for(state="visible", timeout=15000)

                safe_title = sanitize_filename(title)
                output_image_path = OUTPUT_IMG_DIR / f"{global_idx}_{safe_title}.png"

                job_card.screenshot(path=str(output_image_path))
                print(f"    ✓ Saved image to: {output_image_path}")

                time.sleep(2)
                global_idx += 1

        browser.close()

    print(f"\nDone! All dynamic colored job card images generated successfully.")


if __name__ == "__main__":
    process_and_capture_jobs()