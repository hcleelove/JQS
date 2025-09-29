"""Configuration module for the job scheduling system."""

import os
from pathlib import Path

# Base directory for job storage
BASE_DIR = Path(os.path.expanduser("~/jqs"))

# Subdirectories
QUEUE_DIR = BASE_DIR / "queue"
RUNNING_DIR = BASE_DIR / "running"
FINISHED_DIR = BASE_DIR / "finished"
LOCKS_DIR = BASE_DIR / "locks"

# Configuration files
LIMITS_FILE = BASE_DIR / "limits.json"
USAGE_FILE = BASE_DIR / "usage.json"
JOBID_COUNTER_FILE = BASE_DIR / "jobid_counter"
CONFIG_FILE = BASE_DIR / "config.json"

# Default configuration values
DEFAULT_POLL_INTERVAL_SEC = 5
DEFAULT_STDOUT = "stdout.log"
DEFAULT_STDERR = "stderr.log"
DEFAULT_WORKDIR = "."
HISTORY_KEEP = 100

# Job metadata filename
META_FILE = "meta.json"
SCRIPT_FILE = "script.sh"

# Job states
PENDING = "PENDING"
RUNNING = "RUNNING"
COMPLETED = "COMPLETED"
FAILED = "FAILED"
CANCELLED = "CANCELLED"
JOB_STATES = [PENDING, RUNNING, COMPLETED, FAILED, CANCELLED]

# Systemd unit name template
SYSTEMD_UNIT_TEMPLATE = "jqs-job-{jobid}"