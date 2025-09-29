#!/bin/bash
# jqs-scheduler-daemon.sh
# Script to start the JQS scheduler as a background daemon

# Directory where the jqs script is located
JQS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JQS_SCRIPT="$JQS_DIR/jqs"

# Check if scheduler is already running
if pgrep -f "python3.*jqs scheduler" > /dev/null; then
    echo "JQS scheduler is already running"
    exit 1
fi

# Start the scheduler in the background
cd "$JQS_DIR"
nohup python3 "$JQS_SCRIPT" scheduler > scheduler.log 2>&1 &
SCHEDULER_PID=$!

if [ $? -eq 0 ]; then
    echo $SCHEDULER_PID > scheduler.pid
    echo "JQS scheduler started successfully with PID: $SCHEDULER_PID"
    echo "Log file: $JQS_DIR/scheduler.log"
    echo "PID file: $JQS_DIR/scheduler.pid"
else
    echo "Failed to start JQS scheduler"
    exit 1
fi