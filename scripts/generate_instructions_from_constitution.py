#!/usr/bin/env python3
"""
Generate instructions from constitution data.
"""

import json
from pathlib import Path

# Load constitution data
constitution_path = Path("~/PROMETHEUS/output/constitution/constitution_data.json").expanduser()
if not constitution_path.exists():
    print("❌ Constitution data not found. Please ingest constitution first.")
    exit(1)

with open(constitution_path, 'r') as f:
    constitution = json.load(f)

# Create instructions from constitution
instructions = {
    'tasks': [],
    'agents': []
}

# Convert agents to instructions
for agent in constitution.get('architecture', {}).get('agents', []):
    instructions['agents'].append({
        'name': agent.get('name', 'Unknown'),
        'description': agent.get('description', ''),
        'inputs': [],
        'outputs': [],
        'code': '',
        'source_file': agent.get('source', 'constitution')
    })

# Save instructions
output_dir = Path("~/PROMETHEUS/output/parsed").expanduser()
output_dir.mkdir(parents=True, exist_ok=True)

output_path = output_dir / 'parsed_instructions.json'
with open(output_path, 'w') as f:
    json.dump(instructions, f, indent=2, default=str)

print(f"✅ Instructions generated from constitution: {len(instructions['agents'])} agents")
print(f"   Agents: {', '.join([a['name'] for a in instructions['agents']])}")
print(f"   Output: {output_path}")
