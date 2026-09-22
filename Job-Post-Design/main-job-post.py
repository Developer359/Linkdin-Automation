import os
import subprocess
import sys

# Correct path resolution to project root and Job-Post-Design folder
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)
JOB_POST_DIR = os.path.join(PROJECT_ROOT, "Job-Post-Design")


def run_script(script_name):
    script_path = os.path.join(JOB_POST_DIR, script_name)
    print(f"\n" + "=" * 50)
    print(f"▶ Starting execution: {script_name}")
    print("=" * 50)
    
    # Run the script using the same Python interpreter
    result = subprocess.run([sys.executable, script_path])
    
    if result.returncode != 0:
        print(f"❌ Error: '{script_name}' failed with exit code {result.returncode}.")
        sys.exit(result.returncode)
    else:
        print(f"✅ Successfully finished: {script_name}")


def main():
    print("🚀 Starting Job Post Automation Pipeline...")
    
    # Step 1: Run post-data.py first
    run_script("post-data.py")
    
    # Step 2: Run path-finder.py only after step 1 completes successfully
    run_script("path-finder.py")
    
    print("\n🎉 All pipeline steps completed successfully!")


if __name__ == "__main__":
    main()