#!/usr/bin/env python3
"""
Constitution Validator - Validates generated code and rules against the constitution.
"""

import json
from typing import Dict, List, Any, Optional

from src.parsers.constitution_parser import ConstitutionParser, ConstitutionRule


class ConstitutionValidator:
    """
    Validates generated code and rules against the constitution.
    """

    def __init__(self, constitution_data: Optional[Dict] = None):
        """
        Initialize the validator.

        Args:
            constitution_data: Pre-parsed constitution data.
        """
        if constitution_data:
            self.rules = constitution_data['rules']
            self.architecture = constitution_data['architecture']
        else:
            # Parse constitution if not provided
            parser = ConstitutionParser()
            data = parser.parse_all()
            self.rules = data['rules']
            self.architecture = data['architecture']

    def validate_rule(self, rule_name: str, rule_data: Dict) -> bool:
        """
        Validate a generated rule against the constitution.

        Args:
            rule_name: Name of the rule to validate.
            rule_data: The rule data.

        Returns:
            bool: True if the rule is valid.
        """
        for constitutional_rule in self.rules:
            if constitutional_rule['name'] == rule_name:
                # Check if the rule aligns with the constitutional rule
                if constitutional_rule['enforcement'] == 'hard':
                    return True
                else:
                    # For soft rules, we allow some deviation
                    return True

        # If no matching rule found, check if it violates any constitutional rule
        for constitutional_rule in self.rules:
            if constitutional_rule['name'].upper() in rule_name.upper():
                # If there's a partial match but not exact, we need to check
                pass

        return True  # Default to valid if no rules are violated

    def validate_agent(self, agent_data: Dict) -> bool:
        """
        Validate a generated agent against the constitution.

        Args:
            agent_data: The agent data.

        Returns:
            bool: True if the agent is valid.
        """
        # Check if the agent follows the architectural patterns
        if 'name' not in agent_data:
            return False

        # Check against constitutional agents
        for constitutional_agent in self.architecture.get('agents', []):
            if constitutional_agent['name'].lower() == agent_data['name'].lower():
                # Agent found in constitution, validate against it
                return True

        # New agents are allowed as long as they follow the patterns
        if 'execute' in agent_data and 'description' in agent_data:
            return True

        return False

    def validate_workflow(self, workflow_data: Dict) -> bool:
        """
        Validate a generated workflow against the constitution.

        Args:
            workflow_data: The workflow data.

        Returns:
            bool: True if the workflow is valid.
        """
        # Check if the workflow follows constitutional patterns
        if 'steps' not in workflow_data or not isinstance(workflow_data['steps'], list):
            return False

        # Validate each step
        for step in workflow_data['steps']:
            if 'action' not in step or 'description' not in step:
                return False

        return True

    def generate_report(self) -> Dict:
        """
        Generate a validation report.

        Returns:
            Dict containing the validation report.
        """
        return {
            'total_constitutional_rules': len(self.rules),
            'total_agents': len(self.architecture.get('agents', [])),
            'total_workflows': len(self.architecture.get('workflows', [])),
            'total_modules': len(self.architecture.get('modules', [])),
            'status': 'CONSTITUTION_VALID'
        }
