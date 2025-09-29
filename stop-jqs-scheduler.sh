#!/bin/bash
# stop-jqs-scheduler.sh
# Script to stop the JQS scheduler daemon

SCHEDULER_PID_FILE="$(dirname "$0")/scheduler.pid"

if [ -f "$SCHEDULER_PID_FILE" ]; then
    SCHEDULER_PID=$(cat "$SCHEDULER_PID_FILE")
    
    if ps -p $SCHEDULER_PID > /dev/null; then
        kill $SCHEDULER_PID
        rm -f "$SCHEDULER_PID_FILE"
        echo "JQS scheduler stopped (PID: $SCHEDULER_PID)"
    else
        echo "No running scheduler found with PID $SCHEDULER_PID (PID file exists but process not running)"
        rm -f "$SCHEDULER_PID_FILE"
    fi
else
    # If no PID file, try to find and kill any running scheduler
    SCHEDULER_PIDS=$(pgrep -f "python3.*jqs scheduler")
    
    if [ ! -z "$SCHEDULER_PIDS" ]; then
        kill $SCHEDULER_PIDS
        echo "JQS scheduler stopped (PID: $SCHEDULER_PIDS)"
    else
        echo "No JQS scheduler is currently running"
    fi
fi