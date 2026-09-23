import os
import subprocess
import sys

# Correct path resolution to project root and Job-Post-Design folder
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)
JOB_POST_DIR = os.path.join(PROJECT_ROOT, "Job-Post-Design")
GENERATED_IMAGES_DIR = os.path.join(JOB_POST_DIR, "Generated-Images")


def clear_previous_images():
    print(f"\n" + "=" * 50)
    print(f"🧹 Clearing previous images from Generated-Images...")
    print("=" * 50)
    
    if os.path.exists(GENERATED_IMAGES_DIR):
        count = 0
        for filename in os.listdir(GENERATED_IMAGES_DIR):
            file_path = os.path.join(GENERATED_IMAGES_DIR, filename)
            # Ensure we are deleting files and not subdirectories
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    print(f"🗑️ Deleted: {filename}")
                    count += 1
                except Exception as e:
                    print(f"❌ Failed to delete {filename}: {e}")
        print(f"✅ Successfully cleared {count} previous image(s).")
    else:
        print(f"⚠️ Directory not found: {GENERATED_IMAGES_DIR}. Skipping cleanup.")


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
    
    # Step 0: Remove all previous images before running pipeline scripts
    clear_previous_images()
    
    # Step 1: Run post-data.py first
    run_script("post-data.py")
    
    # Step 2: Run path-finder.py only after step 1 completes successfully
    run_script("path-finder.py")
    
    print("\n🎉 All pipeline steps completed successfully!")


if __name__ == "__main__":
    main()