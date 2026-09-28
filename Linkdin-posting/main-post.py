import subprocess
from pathlib import Path
import sys

def main():
    script_dir = Path(__file__).resolve().parent
    
    # Run post.py
    print("Running post.py...")
    post_process = subprocess.run([sys.executable, str(script_dir / "post.py")])
    if post_process.returncode != 0:
        print("❌ post.py failed. Exiting.")
        sys.exit(post_process.returncode)
        
    # Run linkdin-post.py
    print("Running linkdin-post.py...")
    linkdin_process = subprocess.run([sys.executable, str(script_dir / "linkdin-post.py")])
    if linkdin_process.returncode != 0:
        print("❌ linkdin-post.py failed. Exiting.")
        sys.exit(linkdin_process.returncode)
        
    print("🎉 Both scripts finished successfully.")

if __name__ == "__main__":
    main()
