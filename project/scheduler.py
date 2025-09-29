"""Scheduler for the job scheduling system."""

import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List

from .config import (
    QUEUE_DIR, RUNNING_DIR, FINISHED_DIR, META_FILE, PENDING, RUNNING, 
    COMPLETED, FAILED, CANCELLED
)
from .utils import read_json, write_json, iso8601_now
from .state import get_limits, get_usage, update_usage
from .job import update_state, move_job, launch_job


def scan_running_jobs() -> List[Dict[str, Any]]:
    """Scan running jobs and update their status."""
    completed_jobs = []
    
    for job_dir in RUNNING_DIR.iterdir():
        if not job_dir.is_dir():
            continue
            
        meta_file = job_dir / META_FILE
        if not meta_file.exists():
            continue
            
        meta_data = read_json(meta_file)
        job_id = meta_data.get("job_id")
        unit_name = meta_data.get("unit_name")
        
        if not unit_name:
            continue  # Skip if no systemd unit name
        
        # Check the status of the systemd unit
        try:
            result = subprocess.run(
                ["systemctl", "show", "--property=ActiveState,ExecMainStatus,SubState", unit_name],
                capture_output=True, text=True, check=True
            )
            
            # Parse systemctl output
            properties = {}
            for line in result.stdout.strip().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    properties[key] = value
            
            active_state = properties.get("ActiveState", "")
            exec_status = properties.get("ExecMainStatus", "0")  # Default to 0 (success)
            sub_state = properties.get("SubState", "")
            
            # Determine if job is still running or has completed
            # Job is completed if it's inactive and in dead/exited state
            if active_state == "inactive" and sub_state in ["exited", "dead"]:
                # Job has completed
                exit_code = int(exec_status) if exec_status.isdigit() else 0
                
                # Update state based on exit code
                if exit_code == 0:
                    new_state = COMPLETED
                else:
                    new_state = FAILED
                
                # Update job state and move to finished
                update_state(job_id, new_state, {"exit_code": exit_code})
                move_job(job_id, FINISHED_DIR)
                
                # Release resources
                req = meta_data.get("req", {})
                update_usage(delta_cores=-req["cores"], delta_mem_mb=-req["mem_mb"])
                
                completed_jobs.append({
                    "job_id": job_id,
                    "state": new_state,
                    "exit_code": exit_code
                })
        except subprocess.CalledProcessError:
            # If systemctl show fails, the job might have completed, failed or been cancelled.
            # We mark it as FAILED to be safe, as we can't determine the exact exit code.
            update_state(job_id, FAILED, {"exit_code": -1, "notes": "Systemd unit disappeared unexpectedly"})
            move_job(job_id, FINISHED_DIR)
            
            # Release resources
            req = meta_data.get("req", {})
            update_usage(delta_cores=-req["cores"], delta_mem_mb=-req["mem_mb"])
            
            completed_jobs.append({
                "job_id": job_id,
                "state": FAILED,
                "exit_code": -1
            })
    
    return completed_jobs


def scan_queue_and_schedule() -> List[str]:
    """Scan the queue and schedule jobs if resources are available."""
    scheduled_jobs = []
    
    # Get current limits and usage
    limits = get_limits()
    usage = get_usage()
    
    available_cores = limits["cores_total"] - usage["cores_used"]
    available_mem = limits["mem_mb_total"] - usage["mem_mb_used"]
    
    # Get all pending jobs, sorted by submission time
    pending_jobs = []
    for job_dir in QUEUE_DIR.iterdir():
        if not job_dir.is_dir():
            continue
            
        meta_file = job_dir / META_FILE
        if meta_file.exists():
            meta_data = read_json(meta_file)
            if meta_data.get("state") == PENDING:
                pending_jobs.append((meta_data.get("submit_time"), meta_data.get("job_id"), meta_data))
    
    # Sort by submission time (earliest first)
    pending_jobs.sort(key=lambda x: x[0])
    
    # Try to launch jobs that fit within available resources
    for _, job_id, meta_data in pending_jobs:
        req = meta_data.get("req", {})
        req_cores = req.get("cores", 1)
        req_mem = req.get("mem_mb", 1024)
        
        # Check if we have enough resources
        if available_cores >= req_cores and available_mem >= req_mem:
            # Try to launch the job
            if launch_job(job_id):
                scheduled_jobs.append(job_id)
                
                # Update available resources
                available_cores -= req_cores
                available_mem -= req_mem
    
    return scheduled_jobs


def cleanup_old_jobs(history_keep: int = 100) -> int:
    """Remove old finished jobs to keep only the most recent ones."""
    finished_jobs = []
    for job_dir in FINISHED_DIR.iterdir():
        if job_dir.is_dir():
            meta_file = job_dir / META_FILE
            if meta_file.exists():
                meta_data = read_json(meta_file)
                end_time = meta_data.get("end_time")
                if end_time:
                    finished_jobs.append((end_time, job_dir))
    
    # Sort by end time (oldest first)
    finished_jobs.sort(key=lambda x: x[0])
    
    # Remove oldest jobs beyond the history limit
    removed_count = 0
    for _, job_dir in finished_jobs[:-history_keep] if len(finished_jobs) > history_keep else []:
        try:
            import shutil
            shutil.rmtree(job_dir)
            removed_count += 1
        except OSError:
            # Skip if we can't remove the directory
            continue
    
    return removed_count


def run_scheduler_cycle() -> Dict[str, Any]:
    """Run one cycle of the scheduler."""
    # First, scan running jobs and update their status
    completed_jobs = scan_running_jobs()
    
    # Then, scan queue and schedule new jobs
    scheduled_jobs = scan_queue_and_schedule()
    
    # Cleanup old jobs
    cleaned_jobs = cleanup_old_jobs()
    
    return {
        "completed_jobs": completed_jobs,
        "scheduled_jobs": scheduled_jobs,
        "cleaned_jobs": cleaned_jobs
    }


def run_scheduler(poll_interval_sec: int = 5) -> None:
    """Run the scheduler loop."""
    print(f"Starting scheduler with poll interval {poll_interval_sec}s...")
    
    try:
        while True:
            result = run_scheduler_cycle()
            
            if result["completed_jobs"] or result["scheduled_jobs"]:
                print(f"[{iso8601_now()}] Scheduler cycle completed:")
                print(f"  Completed jobs: {len(result['completed_jobs'])}")
                print(f"  Scheduled jobs: {len(result['scheduled_jobs'])}")
                print(f"  Cleaned jobs: {result['cleaned_jobs']}")
            
            time.sleep(poll_interval_sec)
    except KeyboardInterrupt:
        print("\nScheduler stopped by user")