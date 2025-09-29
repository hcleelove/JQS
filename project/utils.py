"""Utility functions for the job scheduling system."""

import json
import os
import fcntl
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .config import JOBID_COUNTER_FILE, LOCKS_DIR


def read_json(path: Path) -> Dict[str, Any]:
    """Read JSON from file."""
    if not path.exists():
        return {}
    
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write JSON to file."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def with_file_lock(lockfile: Path, func, *args, **kwargs):
    """Execute function with file lock."""
    # Create parent directory if it doesn't exist
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    
    with open(lockfile, 'w') as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            return func(*args, **kwargs)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def generate_jobid(counter_file: Path = JOBID_COUNTER_FILE) -> str:
    """Generate a new job ID by incrementing the counter."""
    def _increment_counter():
        if counter_file.exists():
            with open(counter_file, 'r') as f:
                counter = int(f.read().strip())
        else:
            counter = 0
        
        counter += 1
        
        with open(counter_file, 'w') as f:
            f.write(str(counter))
        
        return counter
    
    # Use file locking to ensure atomic increment
    counter = with_file_lock(LOCKS_DIR / "jobid_counter.lock", _increment_counter)
    
    # Format: YYYYMMDD-XXXX
    today = datetime.now().strftime("%Y%m%d")
    return f"{today}-{counter:04d}"


def iso8601_now() -> str:
    """Return current time in ISO8601 format."""
    return datetime.now().isoformat()


def expand_paths(template: str, job_name: str, job_id: str) -> str:
    """Expand path templates using job info (%x for name, %j for jobid)."""
    result = template.replace("%x", job_name)
    result = result.replace("%j", job_id)
    return result