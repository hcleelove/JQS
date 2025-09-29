"""Setup script for the job scheduling system."""

import sys
from pathlib import Path

# Add the project directory to the path so we can import modules
sys.path.append(str(Path(__file__).parent))

from project.state import init_system
from project.config import BASE_DIR, QUEUE_DIR, RUNNING_DIR, FINISHED_DIR, LOCKS_DIR, LIMITS_FILE, USAGE_FILE, JOBID_COUNTER_FILE


def main():
    print("Initializing job scheduling system...")
    
    # Call the initialization function
    init_system()
    
    # Check which components were newly created vs already existing
    dirs_status = {
        "queue": "EXISTS" if QUEUE_DIR.exists() else "CREATED",
        "running": "EXISTS" if RUNNING_DIR.exists() else "CREATED", 
        "finished": "EXISTS" if FINISHED_DIR.exists() else "CREATED",
        "locks": "EXISTS" if LOCKS_DIR.exists() else "CREATED"
    }
    
    files_status = {
        "limits.json": "EXISTS" if LIMITS_FILE.exists() else "CREATED",
        "usage.json": "EXISTS" if USAGE_FILE.exists() else "CREATED", 
        "jobid_counter": "EXISTS" if JOBID_COUNTER_FILE.exists() else "CREATED"
    }
    
    print("System initialization complete!")
    print(f"Base directory: {BASE_DIR} ({'EXISTS' if BASE_DIR.exists() else 'CREATED'})")
    print("Directory status:")
    for dir_name, status in dirs_status.items():
        dir_path = BASE_DIR / dir_name
        print(f"  {dir_path}: {status}")
    print("Configuration files status:")
    for file_name, status in files_status.items():
        file_path = BASE_DIR / file_name
        print(f"  {file_path}: {status}")
    print("\nNote: Running setup multiple times is safe - existing files/directories will not be overwritten.")


if __name__ == "__main__":
    main()