#!/usr/bin/env python3
"""
Rule Generator - Generates system rules from parsed instructions.
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

class RuleGenerator:
    """
    Generates system rules from parsed instructions.
    """
    
    def __init__(self, output_dir: str = "~/PROMETHEUS/output/generated_rules"):
        """
        Initialize the rule generator.
        
        Args:
            output_dir: Directory for generated rules.
        """
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.rules: List[Dict] = []
        self.keywords: Dict[str, List[str]] = {}
    
    def generate_from_parsed_data(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate system rules from parsed instruction data.
        
        Args:
            parsed_data: Parsed instruction data.
            
        Returns:
            Dict containing generation results.
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'rules_generated': 0,
            'errors': []
        }
        
        # Generate rules from tasks
        for task in parsed_data.get('tasks', []):
            rules = self._extract_rules_from_task(task)
            self.rules.extend(rules)
        
        # Generate rules from agents
        for agent in parsed_data.get('agents', []):
            rules = self._extract_rules_from_agent(agent)
            self.rules.extend(rules)
        
        # Generate keyword rules
        self._generate_keyword_rules(parsed_data)
        
        # Save rules
        self._save_rules()
        
        results['rules_generated'] = len(self.rules)
        results['keywords_generated'] = len(self.keywords)
        
        return results
    
    def _extract_rules_from_task(self, task: Dict) -> List[Dict]:
        """Extract rules from a task definition."""
        rules = []
        
        rules.append({
            'id': f"TASK_{task['number'].replace('.', '_')}_EXEC",
            'type': 'execution',
            'description': f"Execute task {task['number']}: {task['name']}",
            'condition': f"task_number == '{task['number']}'",
            'action': f"execute_task_{task['number'].replace('.', '_')}",
            'source': task.get('source_file', 'unknown')
        })
        
        for criteria in task.get('acceptance_criteria', []):
            rules.append({
                'id': f"TASK_{task['number'].replace('.', '_')}_ACCEPT",
                'type': 'acceptance',
                'description': f"Acceptance criteria: {criteria}",
                'condition': f"task_{task['number'].replace('.', '_')}_completed",
                'action': f"accept_task_{task['number'].replace('.', '_')}",
                'source': task.get('source_file', 'unknown')
            })
        
        return rules
    
    def _extract_rules_from_agent(self, agent: Dict) -> List[Dict]:
        """Extract rules from an agent definition."""
        rules = []
        
        rules.append({
            'id': f"AGENT_{agent['name'].upper()}_EXEC",
            'type': 'execution',
            'description': f"Execute agent: {agent['name']}",
            'condition': f"agent == '{agent['name']}'",
            'action': f"execute_agent_{agent['name'].lower()}",
            'source': agent.get('source_file', 'unknown')
        })
        
        for input_field in agent.get('inputs', []):
            rules.append({
                'id': f"AGENT_{agent['name'].upper()}_INPUT_{input_field.upper()}",
                'type': 'validation',
                'description': f"Validate input: {input_field}",
                'condition': f"input_exists('{input_field}')",
                'action': f"validate_input_{input_field}",
                'source': agent.get('source_file', 'unknown')
            })
        
        for output_field in agent.get('outputs', []):
            rules.append({
                'id': f"AGENT_{agent['name'].upper()}_OUTPUT_{output_field.upper()}",
                'type': 'output',
                'description': f"Generate output: {output_field}",
                'condition': f"agent_{agent['name'].lower()}_completed",
                'action': f"generate_output_{output_field}",
                'source': agent.get('source_file', 'unknown')
            })
        
        return rules
    
    def _generate_keyword_rules(self, parsed_data: Dict[str, Any]):
        """Generate keyword rules from parsed data."""
        for task in parsed_data.get('tasks', []):
            name_keywords = task['name'].lower().split()
            for keyword in name_keywords:
                if len(keyword) > 3:
                    self._add_keyword(keyword, f"task_{task['number'].replace('.', '_')}")
            
            for subtask in task.get('subtasks', []):
                desc_keywords = subtask['description'].lower().split()
                for keyword in desc_keywords:
                    if len(keyword) > 3:
                        self._add_keyword(keyword, f"task_{task['number'].replace('.', '_')}")
        
        for agent in parsed_data.get('agents', []):
            name_keywords = agent['name'].lower().split()
            for keyword in name_keywords:
                if len(keyword) > 3:
                    self._add_keyword(keyword, f"agent_{agent['name'].lower()}")
            
            desc_keywords = agent['description'].lower().split()
            for keyword in desc_keywords:
                if len(keyword) > 3:
                    self._add_keyword(keyword, f"agent_{agent['name'].lower()}")
    
    def _add_keyword(self, keyword: str, target: str):
        """Add a keyword to the keyword rules."""
        if keyword not in self.keywords:
            self.keywords[keyword] = []
        if target not in self.keywords[keyword]:
            self.keywords[keyword].append(target)
    
    def _save_rules(self):
        """Save generated rules to files."""
        with open(self.output_dir / 'execution_rules.json', 'w') as f:
            json.dump(
                [r for r in self.rules if r['type'] in ['execution', 'acceptance']],
                f, indent=2
            )
        
        with open(self.output_dir / 'validation_rules.json', 'w') as f:
            json.dump(
                [r for r in self.rules if r['type'] == 'validation'],
                f, indent=2
            )
        
        with open(self.output_dir / 'keyword_rules.json', 'w') as f:
            json.dump(self.keywords, f, indent=2)
        
        dynamic_rules = {
            'trade_keywords': self.keywords,
            'descriptor_rules': {},
            'custom_stopwords': [],
            'manual_overrides': {}
        }
        
        with open(self.output_dir / 'dynamic_rules.json', 'w') as f:
            json.dump(dynamic_rules, f, indent=2)
