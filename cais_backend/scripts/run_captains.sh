#!/bin/bash
# run_captains.sh - Launch local captain processes to consume jurisdictions from Redis
# Uses environment variables and relative paths for local execution.

NUM_CAPTAINS=${1:-3}
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6389}"

mkdir -p logs/captains

echo "Starting $NUM_CAPTAINS captains targeting Redis at ${REDIS_HOST}:${REDIS_PORT}..."

for i in $(seq 1 $NUM_CAPTAINS); do
    export CAPTAIN_ID=$i
    export REDIS_HOST=$REDIS_HOST
    export REDIS_PORT=$REDIS_PORT
    
    nohup python3 app/agents/captain.py > logs/captains/captain_${i}.out 2>&1 &
    echo "Captain $i started (PID: $!)"
    sleep 1
done

echo "All captains started successfully."
