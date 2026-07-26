#!/usr/bin/env python3
"""
Constitution Parser - Extracts system architecture and rules from the constitution PDFs.
"""

import os
import re
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
import fitz  # PyMuPDF
import pdfplumber
from dataclasses import dataclass, field


@dataclass
class ConstitutionRule:
    """A rule extracted from the constitution."""
    name: str
    description: str
    enforcement: str  # 'hard' or 'soft'
    source_file: str
    page_number: int
    hash: str = ""


@dataclass
class ConstitutionArchitecture:
    """The system architecture extracted from the constitution."""
    agents: List[Dict[str, Any]] = field(default_factory=list)
    workflows: List[Dict[str, Any]] = field(default_factory=list)
    modules: List[Dict[str, Any]] = field(default_factory=list)
    integrations: List[Dict[str, Any]] = field(default_factory=list)


class ConstitutionParser:
    """
    Parses the constitution PDFs to extract system architecture and immutable rules.
    """

    def __init__(self, constitution_dir: str = "~/PROMETHEUS/input/constitution"):
        """
        Initialize the constitution parser.

        Args:
            constitution_dir: Directory containing the constitution PDFs.
        """
        self.constitution_dir = Path(constitution_dir).expanduser()
        self.rules: List[ConstitutionRule] = []
        self.architecture = ConstitutionArchitecture()
        self.source_hashes = {}

    def parse_all(self) -> Dict[str, Any]:
        """
        Parse all constitution PDFs and extract architecture and rules.

        Returns:
            Dict containing the parsed constitution.
        """
        if not self.constitution_dir.exists():
            raise FileNotFoundError(f"Constitution directory not found: {self.constitution_dir}")

        for pdf_path in self.constitution_dir.glob("*.pdf"):
            self._parse_pdf(pdf_path)

        return {
            'rules': [vars(rule) for rule in self.rules],
            'architecture': {
                'agents': self.architecture.agents,
                'workflows': self.architecture.workflows,
                'modules': self.architecture.modules,
                'integrations': self.architecture.integrations
            },
            'source_hashes': self.source_hashes
        }

    def _parse_pdf(self, pdf_path: Path):
        """
        Parse a single PDF file.

        Args:
            pdf_path: Path to the PDF file.
        """
        print(f"Parsing constitution: {pdf_path.name}")

        # Calculate file hash for traceability
        with open(pdf_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        self.source_hashes[pdf_path.name] = file_hash

        # Extract text using both PyMuPDF and pdfplumber for robustness
        try:
            text = self._extract_text_pymupdf(pdf_path)
            text_plumber = self._extract_text_pdfplumber(pdf_path)
            # Use the longer text for better coverage
            full_text = text if len(text) >= len(text_plumber) else text_plumber
        except Exception as e:
            print(f"Error extracting text from {pdf_path.name}: {e}")
            return

        # Parse rules
        self._parse_rules(full_text, pdf_path.name)

        # Parse architecture
        self._parse_architecture(full_text, pdf_path.name)

    def _extract_text_pymupdf(self, pdf_path: Path) -> str:
        """Extract text from PDF using PyMuPDF."""
        text = ""
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text()
        doc.close()
        return text

    def _extract_text_pdfplumber(self, pdf_path: Path) -> str:
        """Extract text from PDF using pdfplumber."""
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    def _parse_rules(self, text: str, source_file: str):
        """
        Parse immutable rules from the constitution text.

        Patterns include:
        - "Principios Rectores (No Negociables)"
        - "Never modify source code automatically"
        - "Confidence Score threshold"
        - "Always mount Google Drive in --read-only mode"
        """
        # Look for rule sections
        rule_patterns = [
            r'Principios Rectores\s*\(No\s*Negociables\)\s*([\s\S]*?)(?=\n\n|\n[A-Z]|$)',
            r'Guiding Principles\s*\(Non-Negotiable\)\s*([\s\S]*?)(?=\n\n|\n[A-Z]|$)',
            r'Regla:\s*(.+?)(?:\n|$)',
            r'Rule:\s*(.+?)(?:\n|$)',
        ]

        for pattern in rule_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                self._extract_rules_from_section(str(match), source_file)

    def _extract_rules_from_section(self, section: str, source_file: str):
        """Extract individual rules from a section of text."""
        # Look for numbered or bulleted rules
        lines = section.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for numbered rules (1., 2., etc.)
            match = re.match(r'^(\d+)\.\s+(.+)$', line)
            if match:
                description = match.group(2)
                if 'modificar código fuente' in description.lower() or 'modify source code' in description.lower():
                    self.rules.append(ConstitutionRule(
                        name="CODE_IMMUTABILITY",
                        description="Never modify source code automatically",
                        enforcement="hard",
                        source_file=source_file,
                        page_number=1
                    ))
                elif 'confidence' in description.lower() or 'confianza' in description.lower():
                    self.rules.append(ConstitutionRule(
                        name="CONFIDENCE_SCORE",
                        description="Every non-deterministic process must have a confidence score",
                        enforcement="hard",
                        source_file=source_file,
                        page_number=1
                    ))
                elif 'google drive' in description.lower() or 'drive' in description.lower():
                    self.rules.append(ConstitutionRule(
                        name="GDRIVE_READONLY",
                        description="Access to Google Drive must always be in --read-only mode",
                        enforcement="hard",
                        source_file=source_file,
                        page_number=1
                    ))

    def _parse_architecture(self, text: str, source_file: str):
        """
        Parse system architecture from the constitution text.

        Looks for:
        - Agent definitions
        - Workflow definitions
        - Module definitions
        - Integration definitions
        """
        # Parse agents
        agent_sections = re.findall(
            r'Agent\s+([A-Za-z_]+)\s*[-—]\s*([^\n]+)([\s\S]*?)(?=\n\n|\n[A-Z]|$)',
            text,
            re.IGNORECASE
        )
        for agent_name, description, details in agent_sections:
            agent_info = {
                'name': agent_name.strip(),
                'description': description.strip(),
                'source': source_file,
                'details': details.strip()[:500]
            }
            self.architecture.agents.append(agent_info)

        # Parse workflows
        workflow_sections = re.findall(
            r'Flujo\s+([A-Za-z_]+)\s*[-—]\s*([^\n]+)([\s\S]*?)(?=\n\n|\n[A-Z]|$)',
            text,
            re.IGNORECASE
        )
        for workflow_name, description, details in workflow_sections:
            workflow_info = {
                'name': workflow_name.strip(),
                'description': description.strip(),
                'source': source_file,
                'details': details.strip()[:500]
            }
            self.architecture.workflows.append(workflow_info)

        # Parse modules
        module_sections = re.findall(
            r'Modulo\s+([A-Za-z_]+)\s*[-—]\s*([^\n]+)([\s\S]*?)(?=\n\n|\n[A-Z]|$)',
            text,
            re.IGNORECASE
        )
        for module_name, description, details in module_sections:
            module_info = {
                'name': module_name.strip(),
                'description': description.strip(),
                'source': source_file,
                'details': details.strip()[:500]
            }
            self.architecture.modules.append(module_info)

    def get_rules(self) -> List[Dict]:
        """Get all extracted rules."""
        return [vars(rule) for rule in self.rules]

    def get_architecture(self) -> Dict:
        """Get the extracted architecture."""
        return {
            'agents': self.architecture.agents,
            'workflows': self.architecture.workflows,
            'modules': self.architecture.modules,
            'integrations': self.architecture.integrations
        }

    def save_parsed_data(self, output_dir: str = "~/PROMETHEUS/output/constitution"):
        """Save parsed data to JSON files."""
        output_path = Path(output_dir).expanduser()
        output_path.mkdir(parents=True, exist_ok=True)

        data = self.parse_all()

        with open(output_path / 'constitution_data.json', 'w') as f:
            json.dump(data, f, indent=2, default=str)

        print(f"\n✅ Constitution data saved to: {output_path / 'constitution_data.json'}")
        return data
