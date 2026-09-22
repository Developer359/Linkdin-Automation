import subprocess
import sys
from pathlib import Path

# Root directory of the project
ROOT_DIR = Path(__file__).resolve().parent

def run_script(script_path: Path, description: str):
    print(f"\n{'='*70}")
    print(f"[*] Starting Pipeline Step: {description}")
    print(f"{'='*70}")
    
    if not script_path.exists():
        print(f"[!] Error: Script not found at '{script_path}'")
        sys.exit(1)
        
    try:
        # Run script using the current Python interpreter
        subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            text=True
        )
        print(f"[✓] Successfully finished: {description}")
    except subprocess.CalledProcessError as e:
        print(f"[!] Error in {description} (Exit code: {e.returncode})")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Unexpected error while running {description}: {e}")
        sys.exit(1)

def main():
    print("[*] Launching Master Automation Workflow...")

    # Define paths based on your project structure
    core_script = ROOT_DIR / "Core" / "main-core.py"
    job_post_script = ROOT_DIR / "Job-Post-Design" / "main-job-post.py"
    storage_script = ROOT_DIR / "Main-Storage" / "main-storage.py"

    # Step 1: Run main-core.py (Scrapes, Ranks, Infos, and Summarizes Jobs)
    run_script(core_script, "Core Automation & Summarization (main-core.py)")

    # Step 2: Run main-job-post.py (Generates designs/images for posts)
    run_script(job_post_script, "Job Post Design Generator (main-job-post.py)")

    # Step 3: Run main-storage.py (Stores and archives the final pipeline assets)
    run_script(storage_script, "Main Storage Handler (main-storage.py)")

    print(f"\n{'='*70}")
    print("[✓] Entire project workflow executed successfully from start to finish!")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()