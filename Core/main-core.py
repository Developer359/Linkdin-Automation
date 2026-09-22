import subprocess
import sys
from pathlib import Path

# Get the Core directory path
CORE_DIR = Path(__file__).resolve().parent

def run_script(script_path: Path, description: str):
    print(f"\n{'='*60}")
    print(f"[*] Starting: {description}")
    print(f"{'='*60}")
    
    if not script_path.exists():
        print(f"[!] Error: Script not found at '{script_path}'")
        sys.exit(1)
        
    try:
        # Run the script using the current Python interpreter
        subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            text=True
        )
        print(f"[✓] Successfully finished: {description}")
    except subprocess.CalledProcessError as e:
        print(f"[!] Error running {description} (Exit code: {e.returncode})")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Unexpected error while running {description}: {e}")
        sys.exit(1)

def main():
    print("[*] Beginning Master Automation Pipeline...")
    
    # Define script paths in the exact order requested
    linkedin_script = CORE_DIR / "Job-search" / "linkdin-engine.py"
    indeed_script = CORE_DIR / "Job-search" / "indeed-engine.py"
    job_rank_script = CORE_DIR / "job-rank.py"
    job_info_script = CORE_DIR / "job-info.py"
    job_summery_script = CORE_DIR / "job-summery.py"

    # Step 1: Run LinkedIn Engine
    run_script(linkedin_script, "LinkedIn Engine Scraper")

    # Step 2: Run Indeed Engine
    run_script(indeed_script, "Indeed Engine Scraper")

    # Step 3: Run Job Ranking
    run_script(job_rank_script, "Job Ranking Script")

    # Step 4: Run Job Info Processing
    run_script(job_info_script, "Job Info Processing Script")

    # Step 5: Run Job Summary Generation
    run_script(job_summery_script, "Job Summary Generation Script")

    print(f"\n{'='*60}")
    print("[✓] All pipeline steps completed successfully!")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()