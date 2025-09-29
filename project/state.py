"""State management for the job scheduling system."""

import json
from pathlib import Path
from typing import Dict, Any

from .config import LIMITS_FILE, USAGE_FILE, JOBID_COUNTER_FILE, BASE_DIR
from .utils import read_json, write_json, with_file_lock


def get_limits() -> Dict[str, Any]:
    """Read system limits from limits.json."""
    limits = read_json(LIMITS_FILE)
    
    # Initialize with defaults if file doesn't exist
    if not limits:
        limits = {
            "cores_total": 16,
            "mem_mb_total": 65536
        }
        # Ensure directory exists and write defaults
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        write_json(LIMITS_FILE, limits)
    
    return limits


def get_usage() -> Dict[str, Any]:
    """Read current resource usage from usage.json."""
    usage = read_json(USAGE_FILE)
    
    # Initialize with defaults if file doesn't exist
    if not usage:
        usage = {
            "cores_used": 0,
            "mem_mb_used": 0
        }
        # Write defaults
        write_json(USAGE_FILE, usage)
    
    return usage


def update_usage(delta_cores: int = 0, delta_mem_mb: int = 0) -> Dict[str, Any]:
    """Update resource usage by adding delta values."""
    def _update():
        usage = get_usage()
        limits = get_limits()
        
        new_cores = usage["cores_used"] + delta_cores
        new_mem = usage["mem_mb_used"] + delta_mem_mb
        
        # Check if update would exceed limits
        if new_cores > limits["cores_total"] or new_mem > limits["mem_mb_total"]:
            raise ValueError(f"Resource limit exceeded: cores={new_cores}/{limits['cores_total']}, "
                           f"mem={new_mem}/{limits['mem_mb_total']}MB")
        
        if new_cores < 0 or new_mem < 0:
            raise ValueError("Resource usage cannot be negative")
        
        usage["cores_used"] = new_cores
        usage["mem_mb_used"] = new_mem
        
        write_json(USAGE_FILE, usage)
        return usage
    
    # Use file locking for atomic update
    return with_file_lock(BASE_DIR / "usage.lock", _update)


def get_next_jobid() -> str:
    """Get the next job ID by incrementing the counter."""
    from .utils import generate_jobid
    return generate_jobid()


def init_system() -> None:
    """Initialize the system with default configuration files."""
    # Ensure base directory exists
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize limits.json if it doesn't exist
    if not LIMITS_FILE.exists():
        write_json(LIMITS_FILE, {
            "cores_total": 16,
            "mem_mb_total": 65536
        })
    
    # Initialize usage.json if it doesn't exist
    if not USAGE_FILE.exists():
        write_json(USAGE_FILE, {
            "cores_used": 0,
            "mem_mb_used": 0
        })
    
    # Initialize jobid_counter if it doesn't exist
    if not JOBID_COUNTER_FILE.exists():
        with open(JOBID_COUNTER_FILE, 'w') as f:
            f.write("1")