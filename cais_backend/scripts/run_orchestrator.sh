#!/bin/bash
# run_orchestrator.sh - Populate Redis queue with US states jurisdictions
# Uses environment variables with sensible defaults for local execution.

REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6389}"

echo "Filling Redis queue at ${REDIS_HOST}:${REDIS_PORT}..."
python3 -c "
import os
import redis
import json

host = os.getenv('REDIS_HOST', 'localhost')
port = int(os.getenv('REDIS_PORT', 6389))

r = redis.Redis(host=host, port=port, db=0, decode_responses=True)
states = [
    'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado',
    'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho',
    'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana',
    'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota',
    'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada',
    'New Hampshire', 'New Jersey', 'New Mexico', 'New York',
    'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon',
    'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
    'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington',
    'West Virginia', 'Wisconsin', 'Wyoming'
]

# Clear existing queue if needed
r.delete('cais:jurisdictions:queue')

for s in states:
    r.rpush('cais:jurisdictions:queue', json.dumps({'state': s, 'country': 'USA', 'path': f'USA/{s}'}))

print(f'Loaded {len(states)} jurisdictions into Redis.')
"
echo "Orchestrator done."
