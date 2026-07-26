#!/usr/bin/env python3
"""
Instruction Parser - Parses instruction documents and extracts code generation directives.
"""

import os
import re
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import fitz  # PyMuPDF

@dataclass
class CodeBlock:
    """Represents a code block extracted from an instruction document."""
    language: str
    content: str
    file_path: str
    line_number: int = 0
    description: str = ""

@dataclass
class TaskDefinition:
    """Represents a task definition extracted from an instruction document."""
    number: str
    name: str
    description: str
    subtasks: List[Dict[str, Any]] = field(default_factory=list)
    code_blocks: List[CodeBlock] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    source_file: str = ""

@dataclass
class AgentDefinition:
    """Represents an agent definition extracted from an instruction document."""
    name: str
    description: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    code: str = ""
    source_file: str = ""

class InstructionParser:
    """
    Parses instruction documents to extract code generation directives.
    """
    
    def __init__(self, instructions_dir: str = "~/PROMETHEUS/downloads"):
        """
        Initialize the instruction parser.
        
        Args:
            instructions_dir: Directory containing the instruction documents.
        """
        self.instructions_dir = Path(instructions_dir).expanduser()
        self.tasks: List[TaskDefinition] = []
        self.agents: List[AgentDefinition] = []
        self.parsed_files: List[Dict] = []
        
        # Patterns for parsing
        self.task_pattern = r'Tarea\s+(\d+)\s*[:.-]\s*([^\n]+)'
        self.subtask_pattern = r'Sub[Tt]area\s+(\d+\.\d+)\s*[:.-]\s*([^\n]+)'
        self.code_block_pattern = r'```(\w+)\s*\n(.*?)\n```'
        self.acceptance_pattern = r'Criterio\s+de\s+Aceptaci[oó]n.*?:?\s*([^\n]+)'
        
    def parse_all(self) -> Dict[str, Any]:
        """
        Parse all instruction documents.
        
        Returns:
            Dict containing all parsed information.
        """
        if not self.instructions_dir.exists():
            raise FileNotFoundError(f"Instructions directory not found: {self.instructions_dir}")
        
        for pdf_path in self.instructions_dir.glob("**/*.pdf"):
            print(f"📖 Parsing: {pdf_path.name}")
            self._parse_pdf(pdf_path)
        
        # Save parsed data
        output_dir = Path("~/PROMETHEUS/output/parsed").expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        with open(output_dir / 'tasks.json', 'w') as f:
            json.dump([t.__dict__ for t in self.tasks], f, indent=2, default=str)
        
        with open(output_dir / 'agents.json', 'w') as f:
            json.dump([a.__dict__ for a in self.agents], f, indent=2, default=str)
        
        return {
            'tasks': [t.__dict__ for t in self.tasks],
            'agents': [a.__dict__ for a in self.agents],
            'parsed_files': self.parsed_files
        }
    
    def _parse_pdf(self, pdf_path: Path):
        """
        Parse a single PDF file.
        
        Args:
            pdf_path: Path to the PDF file.
        """
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            pages_text = []
            
            for page_num, page in enumerate(doc):
                text = page.get_text()
                full_text += text + "\n"
                pages_text.append({
                    'page_num': page_num + 1,
                    'text': text
                })
            
            doc.close()
            
            # Parse tasks
            self._parse_tasks(full_text, pdf_path.name)
            
            # Parse agents
            self._parse_agents(full_text, pdf_path.name)
            
            # Parse code blocks
            self._parse_code_blocks(full_text, pdf_path.name)
            
            self.parsed_files.append({
                'filename': pdf_path.name,
                'pages': len(pages_text),
                'characters': len(full_text)
            })
            
        except Exception as e:
            print(f"  ❌ Error parsing {pdf_path.name}: {e}")
    
    def _parse_tasks(self, text: str, source_file: str):
        """
        Parse task definitions from text.
        """
        # Find task sections
        task_matches = re.findall(self.task_pattern, text, re.IGNORECASE)
        
        for match in task_matches:
            task_num = match[0]
            task_name = match[1].strip()
            
            # Find subtasks within this task's section
            subtask_pattern = rf'{task_num}\.\d+\s*[:.-]\s*([^\n]+)'
            subtask_matches = re.findall(subtask_pattern, text, re.IGNORECASE)
            
            subtasks = []
            for i, subtask_desc in enumerate(subtask_matches):
                subtasks.append({
                    'number': f"{task_num}.{i+1}",
                    'description': subtask_desc.strip()
                })
            
            task = TaskDefinition(
                number=task_num,
                name=task_name,
                description=f"Task {task_num}: {task_name}",
                subtasks=subtasks,
                source_file=source_file
            )
            
            # Find code blocks for this task
            # Look for code blocks after the task definition
            task_section = re.search(
                rf'Tarea\s+{task_num}.*?(?=Tarea\s+\d+|$)',
                text,
                re.DOTALL | re.IGNORECASE
            )
            
            if task_section:
                section_text = task_section.group(0)
                code_blocks = re.findall(self.code_block_pattern, section_text, re.DOTALL)
                
                for lang, code in code_blocks:
                    task.code_blocks.append(CodeBlock(
                        language=lang.strip(),
                        content=code.strip(),
                        file_path=f"src/{task_name.lower().replace(' ', '_')}.py",
                        description=f"Generated from task {task_num}"
                    ))
                
                # Find acceptance criteria
                acceptance = re.findall(self.acceptance_pattern, section_text, re.IGNORECASE)
                for criteria in acceptance:
                    task.acceptance_criteria.append(criteria.strip())
            
            self.tasks.append(task)
    
    def _parse_agents(self, text: str, source_file: str):
        """
        Parse agent definitions from text.
        """
        # Look for agent definitions
        agent_pattern = r'Agente\s+([A-Za-z_]+)\s*[-–]\s*([^\n]+)([\s\S]*?)(?=\n\n|\n[A-Z]|$)'
        agent_matches = re.findall(agent_pattern, text, re.IGNORECASE)
        
        for name, description, details in agent_matches:
            # Extract inputs
            inputs = []
            input_pattern = r'[Ii]nputs?\s*[:.]\s*([^\n]+)'
            input_match = re.search(input_pattern, details)
            if input_match:
                inputs = [i.strip() for i in input_match.group(1).split(',')]
            
            # Extract outputs
            outputs = []
            output_pattern = r'[Oo]utputs?\s*[:.]\s*([^\n]+)'
            output_match = re.search(output_pattern, details)
            if output_match:
                outputs = [o.strip() for o in output_match.group(1).split(',')]
            
            # Extract code
            code = ""
            code_match = re.search(self.code_block_pattern, details, re.DOTALL)
            if code_match:
                code = code_match.group(2).strip()
            
            agent = AgentDefinition(
                name=name.strip(),
                description=description.strip(),
                inputs=inputs,
                outputs=outputs,
                code=code,
                source_file=source_file
            )
            
            self.agents.append(agent)
    
    def _parse_code_blocks(self, text: str, source_file: str):
        """
        Parse code blocks from text.
        """
        code_blocks = re.findall(self.code_block_pattern, text, re.DOTALL)
        
        for lang, code in code_blocks:
            # Determine file path based on language
            if lang.lower() == 'python':
                file_path = "src/generated_code.py"
            elif lang.lower() == 'javascript':
                file_path = "src/generated_code.js"
            elif lang.lower() == 'bash':
                file_path = "scripts/generated_script.sh"
            else:
                file_path = f"src/generated_code.{lang}"
            
            # We don't store code blocks directly here; they will be stored with tasks or agents
            pass
