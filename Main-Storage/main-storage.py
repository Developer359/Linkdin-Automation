import os
import json

# Correct path resolution to project root
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)

INPUT_FILE = os.path.join(PROJECT_ROOT, "Data", "Job-summery.json")
OUTPUT_JSON_FILE = os.path.join(CORE_DIR, "main-storage.json")


def sanitize_filename(name: str) -> str:
    """Helper to sanitize job titles into safe filenames matching the image generator."""
    return "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in name).strip().replace(" ", "-")


def process_main_storage():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Could not find input file at '{INPUT_FILE}'")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    if not jobs:
        print("No jobs found in Job-summery.json to process.")
        return

    stored_jobs = []
    for idx, job in enumerate(jobs, start=1):
        job_record = job.copy()
        
        # Remove tags and color_code as requested
        job_record.pop("tags", None)
        job_record.pop("color_code", None)
        
        # Link the generated image path
        title = job.get("job_title", "Job Title")
        safe_title = sanitize_filename(title)
        image_filename = f"{idx}_{safe_title}.png"
        job_record["image_path"] = os.path.join("Job-Post-Design", "Generated-Images", image_filename)
        
        # Add status mode set to "pending"
        job_record["status"] = "pending"
        
        stored_jobs.append(job_record)

    # Save to main-storage.json
    os.makedirs(os.path.dirname(OUTPUT_JSON_FILE), exist_ok=True)
    with open(OUTPUT_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(stored_jobs, f, indent=4, ensure_ascii=False)

    print(f"Successfully processed {len(stored_jobs)} jobs with image references and stored them in '{OUTPUT_JSON_FILE}'.")


if __name__ == "__main__":
    process_main_storage()