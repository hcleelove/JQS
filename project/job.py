"""Job management for the job scheduling system."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from .config import (
    QUEUE_DIR, RUNNING_DIR, FINISHED_DIR, META_FILE, SCRIPT_FILE,
    PENDING, RUNNING, COMPLETED, FAILED, CANCELLED, SYSTEMD_UNIT_TEMPLATE
)
from .utils import read_json, write_json, iso8601_now, expand_paths
from .state import get_next_jobid, update_usage


def parse_script_header(script_path: Path) -> Dict[str, Any]:
    """Parse #JS directives from the script header."""
    req = {
        "cores": 1,
        "mem_mb": 1024,
        "time_limit": None
    }
    
    io = {
        "stdout": "stdout.log",
        "stderr": "stderr.log"
    }
    
    name = script_path.stem
    workdir = str(script_path.parent.absolute())  # Use absolute path
    
    with open(script_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line.startswith("#JS"):
                if line.startswith("#") or line == "":
                    continue
                else:
                    break  # Stop after header comments
            
            # Parse JS directives
            directive = line[3:].strip()  # Remove "#JS"
            
            # Parse key-value pairs like: cores=4, mem_mb=8192, name="myjob"
            matches = re.findall(r'(\w+)=("[^"]*"|\'[^\']*\'|\S+)', directive)
            for key, value in matches:
                value = value.strip('"\'')  # Remove quotes if present
                
                if key == "cores":
                    req["cores"] = int(value)
                elif key == "mem_mb":
                    req["mem_mb"] = int(value)
                elif key == "time_limit":
                    req["time_limit"] = value
                elif key == "stdout":
                    io["stdout"] = value
                elif key == "stderr":
                    io["stderr"] = value
                elif key == "name":
                    name = value
                elif key == "workdir":
                    workdir = value
    
    return {
        "req": req,
        "io": io,
        "name": name,
        "workdir": workdir
    }


def create_job(script_path: Path) -> str:
    """Create a new job from a script file."""
    # Parse script header
    parsed = parse_script_header(script_path)
    
    # Generate job ID
    job_id = get_next_jobid()
    
    # Get current user
    user = os.getenv("USER", "unknown")
    
    # Create job directory in queue
    job_dir = QUEUE_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy script to job directory
    dest_script = job_dir / SCRIPT_FILE
    shutil.copy2(script_path, dest_script)
    
    # Create meta.json
    meta_data = {
        "job_id": job_id,
        "name": parsed["name"],
        "user": user,
        "submit_time": iso8601_now(),
        "req": parsed["req"],
        "io": parsed["io"],
        "workdir": parsed["workdir"],
        "state": PENDING,
        "unit_name": None,
        "start_time": None,
        "end_time": None,
        "exit_code": None
    }
    
    meta_file = job_dir / META_FILE
    write_json(meta_file, meta_data)
    
    return job_id


def update_state(job_id: str, new_state: str, extra_fields: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Update job state and return updated meta data."""
    # Find job in any of the directories
    for job_dir in [QUEUE_DIR, RUNNING_DIR, FINISHED_DIR]:
        meta_file = job_dir / job_id / META_FILE
        if meta_file.exists():
            meta_data = read_json(meta_file)
            
            old_state = meta_data.get("state")
            meta_data["state"] = new_state
            
            # Update timestamps based on state transition
            if new_state == RUNNING and old_state == PENDING:
                meta_data["start_time"] = iso8601_now()
            elif new_state in [COMPLETED, FAILED, CANCELLED] and old_state in [PENDING, RUNNING]:
                meta_data["end_time"] = iso8601_now()
            
            # Apply any extra fields
            if extra_fields:
                meta_data.update(extra_fields)
            
            # Update unit name if provided and not already set
            if new_state == RUNNING and not meta_data.get("unit_name"):
                meta_data["unit_name"] = SYSTEMD_UNIT_TEMPLATE.format(jobid=job_id)
            
            write_json(meta_file, meta_data)
            return meta_data
    
    raise FileNotFoundError(f"Job {job_id} not found")


def get_job_meta(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job metadata by job ID."""
    for job_dir in [QUEUE_DIR, RUNNING_DIR, FINISHED_DIR]:
        meta_file = job_dir / job_id / META_FILE
        if meta_file.exists():
            return read_json(meta_file)
    
    return None


def move_job(job_id: str, target_dir: Path) -> Path:
    """Move a job directory to the target directory."""
    # Find current job directory
    current_dir = None
    for job_dir in [QUEUE_DIR, RUNNING_DIR, FINISHED_DIR]:
        job_path = job_dir / job_id
        if job_path.exists():
            current_dir = job_path
            break
    
    if current_dir is None:
        raise FileNotFoundError(f"Job {job_id} not found")
    
    # Move the job directory
    target_job_dir = target_dir / job_id
    shutil.move(str(current_dir), str(target_job_dir))
    
    return target_job_dir


def launch_job(job_id: str) -> bool:
    """Launch a job using systemd-run."""
    # Get job metadata
    meta_data = get_job_meta(job_id)
    if not meta_data:
        return False
    
    if meta_data.get("state") != PENDING:
        return False
    
    job_dir = QUEUE_DIR / job_id
    script_file = job_dir / SCRIPT_FILE
    meta_file = job_dir / META_FILE
    
    # Get the original workdir where the script was submitted
    original_workdir = meta_data.get("workdir", str(job_dir))
    
    # Expand paths for stdout/stderr (make them relative to original workdir)
    io = meta_data.get("io", {})
    stdout_template = io.get("stdout", "stdout.log")
    stderr_template = io.get("stderr", "stderr.log")

    # Use original workdir for output files to match user's expectations
    stdout_path = Path(original_workdir) / expand_paths(stdout_template, meta_data["name"], job_id)
    stderr_path = Path(original_workdir) / expand_paths(stderr_template, meta_data["name"], job_id)

    # Prepare systemd-run command
    req = meta_data.get("req", {})
    cores = req.get("cores", 1)
    mem_mb = req.get("mem_mb", 1024)
    time_limit = req.get("time_limit")
    # Use the original workdir as the working directory for the job
    workdir = original_workdir

    # Calculate CPU quota (cores * 100%)
    cpu_quota = f"{cores * 100}%"
    # Format memory as MB with 'M' suffix
    mem_max = f"{mem_mb}M"

    unit_name = SYSTEMD_UNIT_TEMPLATE.format(jobid=job_id)

    cmd = [
        "systemd-run",
        "--user",  # Run in user context
        "--unit", unit_name,
        "--collect",
        "--property=CPUQuota=" + cpu_quota,
        "--property=MemoryMax=" + mem_max,
        "--property=WorkingDirectory=" + workdir,
        "--property=StandardOutput=append:" + str(stdout_path),
        "--property=StandardError=append:" + str(stderr_path),
        "--property=KillMode=mixed",
        "--property=TimeoutStopSec=15s"
    ]

    # Add time limit if specified
    if time_limit:
        cmd.append(f"--property=RuntimeMax={time_limit}")

    # For execution, we'll create a temporary script in the workdir with a unique name
    # to avoid conflicts if multiple jobs run in the same directory
    temp_script_name = f".jqs_job_{job_id}_script.sh"
    temp_script_path = Path(workdir) / temp_script_name
    
    # Copy the script content to the workdir
    shutil.copy2(script_file, temp_script_path)
    # Make it executable
    temp_script_path.chmod(0o755)

    # Add the script execution command
    cmd.extend(["/bin/bash", "-lc", f"./{temp_script_name}; rm -f ./{temp_script_name}"])
    
    try:
        # Execute the systemd-run command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Update job state to RUNNING
        update_state(job_id, RUNNING)
        
        # Move job from queue to running
        move_job(job_id, RUNNING_DIR)
        
        # Update usage to account for allocated resources
        update_usage(delta_cores=req["cores"], delta_mem_mb=req["mem_mb"])
        
        return True
    except subprocess.CalledProcessError as e:
        # Mark job as failed if systemd-run fails
        update_state(job_id, FAILED, {"exit_code": e.returncode})
        move_job(job_id, FINISHED_DIR)
        # Release resources
        req = meta_data.get("req", {})
        update_usage(delta_cores=-req["cores"], delta_mem_mb=-req["mem_mb"])
        return False
    except Exception as e:
        # Mark job as failed if there's any other error
        update_state(job_id, FAILED, {"exit_code": 1})
        move_job(job_id, FINISHED_DIR)
        # Release resources
        req = meta_data.get("req", {})
        update_usage(delta_cores=-req["cores"], delta_mem_mb=-req["mem_mb"])
        return False


def cancel_job(job_id: str) -> bool:
    """Cancel a job by stopping it if running or updating state if pending."""
    meta_data = get_job_meta(job_id)
    if not meta_data:
        return False
    
    current_state = meta_data.get("state")
    
    if current_state == PENDING:
        # For pending jobs, just update the state
        update_state(job_id, CANCELLED)
        move_job(job_id, FINISHED_DIR)
        return True
    elif current_state == RUNNING:
        # For running jobs, first update the state to CANCELLED
        update_state(job_id, CANCELLED)
        
        # Then, stop the systemd unit
        unit_name = meta_data.get("unit_name")
        if unit_name:
            try:
                # Stop the systemd unit
                subprocess.run(["systemctl", "stop", unit_name], 
                             check=True, capture_output=True)
            except subprocess.CalledProcessError:
                # If systemctl fails, the job is already marked as cancelled
                # so we just log the issue and move on
                pass
        
        # Move job to finished
        move_job(job_id, FINISHED_DIR)
        
        # Update usage to release resources
        req = meta_data.get("req", {})
        update_usage(delta_cores=-req["cores"], delta_mem_mb=-req["mem_mb"])
        
        return True
    elif current_state in [COMPLETED, FAILED, CANCELLED]:
        # Already finished, nothing to cancel
        return True
    
    return False