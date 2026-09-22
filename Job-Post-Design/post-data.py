import os
import json

# Correct path resolution to project root
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)

INPUT_FILE = os.path.join(PROJECT_ROOT, "Data", "Job-summery.json")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "Job-Post-Design", "Post-data.json")

def generate_post_data():
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

    # Group into batches of 5 jobs per post file as requested ("every five query")
    chunk_size = 5
    batched_posts = [extracted_posts[i:i + chunk_size] for i in range(0, len(extracted_posts), chunk_size)]

    # Ensure output directory exists and save to Post-data.json
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(batched_posts, f, indent=4, ensure_ascii=False)

    print(f"Successfully processed {len(extracted_posts)} jobs into batches of 5 and saved to '{OUTPUT_FILE}'")

if __name__ == "__main__":
    generate_post_data()