"""Command line interface for the job scheduling system."""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

from .config import (
    QUEUE_DIR, RUNNING_DIR, FINISHED_DIR, PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
)
from .utils import read_json
from .state import get_limits, get_usage, init_system
from .job import create_job, get_job_meta, cancel_job
from .scheduler import run_scheduler_cycle, run_scheduler


def cmd_submit(args: argparse.Namespace) -> None:
    """Submit a job."""
    script_path = Path(args.script)
    
    if not script_path.exists():
        print(f"Error: Script file '{script_path}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    try:
        job_id = create_job(script_path)
        print(f"Job submitted: {job_id}")
    except Exception as e:
        print(f"Error submitting job: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_q(args: argparse.Namespace) -> None:
    """List jobs with their status."""
    jobs = []
    
    # Collect all jobs from all directories
    for state, state_dir in [(PENDING, QUEUE_DIR), (RUNNING, RUNNING_DIR)]:
        for job_dir in state_dir.iterdir():
            if not job_dir.is_dir():
                continue
                
            meta_file = job_dir / "meta.json"
            if meta_file.exists():
                meta_data = read_json(meta_file)
                jobs.append({
                    "job_id": meta_data.get("job_id"),
                    "name": meta_data.get("name"),
                    "user": meta_data.get("user"),
                    "state": state,
                    "submit_time": meta_data.get("submit_time"),
                    "start_time": meta_data.get("start_time")
                })
    
    # Also include recent finished jobs (last 20)
    finished_jobs = []
    for job_dir in FINISHED_DIR.iterdir():
        if not job_dir.is_dir():
            continue
            
        meta_file = job_dir / "meta.json"
        if meta_file.exists():
            meta_data = read_json(meta_file)
            finished_jobs.append({
                "job_id": meta_data.get("job_id"),
                "name": meta_data.get("name"),
                "user": meta_data.get("user"),
                "state": meta_data.get("state"),
                "submit_time": meta_data.get("submit_time"),
                "start_time": meta_data.get("start_time"),
                "end_time": meta_data.get("end_time")
            })
    
    # Sort finished jobs by end time and take the last 20
    finished_jobs.sort(key=lambda x: x.get("end_time", ""), reverse=True)
    jobs.extend(finished_jobs[:20])
    
    # Sort all jobs by submission time
    jobs.sort(key=lambda x: x.get("submit_time", ""))
    
    # Print job list
    print(f"{'JOBID':<20} {'NAME':<20} {'USER':<15} {'STATE':<12} {'SUBMIT_TIME':<20}")
    print("-" * 85)
    
    for job in jobs:
        job_id = job.get("job_id", "N/A")
        name = job.get("name", "N/A")
        user = job.get("user", "N/A")
        state = job.get("state", "N/A")
        submit_time = job.get("submit_time", "N/A")[:19]  # Truncate to show only datetime
        
        print(f"{job_id:<20} {name:<20} {user:<15} {state:<12} {submit_time:<20}")


def cmd_info(args: argparse.Namespace) -> None:
    """Show detailed information about a job."""
    job_id = args.jobid
    meta_data = get_job_meta(job_id)
    
    if not meta_data:
        print(f"Error: Job '{job_id}' not found", file=sys.stderr)
        sys.exit(1)
    
    print(json.dumps(meta_data, indent=2))


def cmd_cancel(args: argparse.Namespace) -> None:
    """Cancel a job."""
    job_id = args.jobid
    
    if cancel_job(job_id):
        print(f"Job {job_id} cancelled")
    else:
        print(f"Failed to cancel job {job_id}", file=sys.stderr)
        sys.exit(1)


def cmd_nodes(args: argparse.Namespace) -> None:
    """Show system resources and usage."""
    limits = get_limits()
    usage = get_usage()
    
    print("Node Resources:")
    print(f"  Total Cores: {limits['cores_total']}")
    print(f"  Used Cores:  {usage['cores_used']}")
    print(f"  Available:   {limits['cores_total'] - usage['cores_used']}")
    print()
    print(f"  Total Memory: {limits['mem_mb_total']} MB")
    print(f"  Used Memory:  {usage['mem_mb_used']} MB")
    print(f"  Available:    {limits['mem_mb_total'] - usage['mem_mb_used']} MB")


def cmd_run_scheduler(args: argparse.Namespace) -> None:
    """Run the scheduler."""
    poll_interval = args.interval or 5  # Default to 5 seconds
    if args.once:
        # Run scheduler once
        result = run_scheduler_cycle()
        print(f"Scheduler cycle completed:")
        print(f"  Completed jobs: {len(result['completed_jobs'])}")
        print(f"  Scheduled jobs: {len(result['scheduled_jobs'])}")
        print(f"  Cleaned jobs: {result['cleaned_jobs']}")
    else:
        # Run scheduler continuously
        run_scheduler(poll_interval_sec=poll_interval)


def main():
    """Main command line interface."""
    # Initialize system on startup
    init_system()
    
    parser = argparse.ArgumentParser(description="Job Scheduling System CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Submit command
    submit_parser = subparsers.add_parser("submit", help="Submit a job script")
    submit_parser.add_argument("script", help="Path to the job script")
    submit_parser.set_defaults(func=cmd_submit)
    
    # q command (job queue)
    q_parser = subparsers.add_parser("q", help="List jobs")
    q_parser.set_defaults(func=cmd_q)
    
    # info command
    info_parser = subparsers.add_parser("info", help="Show job details")
    info_parser.add_argument("jobid", help="Job ID to show details for")
    info_parser.set_defaults(func=cmd_info)
    
    # cancel command
    cancel_parser = subparsers.add_parser("cancel", help="Cancel a job")
    cancel_parser.add_argument("jobid", help="Job ID to cancel")
    cancel_parser.set_defaults(func=cmd_cancel)
    
    # nodes command
    nodes_parser = subparsers.add_parser("nodes", help="Show system resources")
    nodes_parser.set_defaults(func=cmd_nodes)
    
    # scheduler command
    scheduler_parser = subparsers.add_parser("scheduler", help="Run the scheduler")
    scheduler_parser.add_argument("--interval", type=int, help="Poll interval in seconds")
    scheduler_parser.add_argument("--once", action="store_true", help="Run scheduler once instead of continuously")
    scheduler_parser.set_defaults(func=cmd_run_scheduler)
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    # Call the appropriate function
    args.func(args)


if __name__ == "__main__":
    main()