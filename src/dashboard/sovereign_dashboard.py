#!/usr/bin/env python3
"""
Sovereign Dashboard - Command-line interface for the system owner.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich import box

# Import system modules
from src.integrations.gdrive_explorer import GDriveExplorer
from src.integrations.category_manager import CategoryManager
from src.acquisitor.acquisitor import Acquisitor
from src.parsers.constitution_parser import ConstitutionParser
from src.parsers.laws_ingestor import LawsIngestor
from src.parsers.instruction_parser import InstructionParser
from src.generators.code_generator import CodeGenerator
from src.generators.rule_generator import RuleGenerator
from src.generators.agent_compiler import AgentCompiler
from src.validators.constitution_validator import ConstitutionValidator
from src.worm.worm_ledger import WormLedger

console = Console()

class SovereignDashboard:
    """
    Command-line dashboard for the system owner.
    """
    
    def __init__(self):
        """Initialize the dashboard."""
        self.category_manager = CategoryManager()
        self.worm = WormLedger()
        
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load system configuration."""
        config_path = Path("~/PROMETHEUS/config/system_config.yaml").expanduser()
        if config_path.exists():
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {
            'gdrive_credentials': 'config/security/gdrive-credentials.json',
            'download_dir': 'downloads',
            'compressed_dir': 'compressed',
            'output_dir': 'output',
            'logs_dir': 'logs'
        }
    
    def run(self):
        """Run the interactive dashboard."""
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]╔══════════════════════════════════════════════════════╗[/]\n"
            "[bold cyan]║           CAIS SOVEREIGN DASHBOARD                 ║[/]\n"
            "[bold cyan]╚══════════════════════════════════════════════════════╝[/]",
            border_style="cyan"
        ))
        
        console.print("[dim]Welcome, Sovereign. The system is at your command.[/dim]\n")
        
        while True:
            self._show_menu()
            
            choice = Prompt.ask(
                "\n[bold yellow]➜[/bold yellow]",
                choices=['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'q']
            )
            
            if choice == 'q' or choice == '0':
                self._exit()
                break
            elif choice == '1':
                self._explore_gdrive()
            elif choice == '2':
                self._manage_categories()
            elif choice == '3':
                self._download_category()
            elif choice == '4':
                self._ingest_constitution()
            elif choice == '5':
                self._ingest_laws()
            elif choice == '6':
                self._parse_instructions()
            elif choice == '7':
                self._generate_system()
            elif choice == '8':
                self._view_logs()
            elif choice == '9':
                self._system_status()
    
    def _show_menu(self):
        """Show the main menu."""
        table = Table(title="[bold]Available Operations[/bold]", box=box.HEAVY)
        table.add_column("Option", style="cyan", width=4)
        table.add_column("Operation", style="green")
        table.add_column("Description", style="dim")
        
        table.add_row("1", "Explore Google Drive", "Browse and categorize documents")
        table.add_row("2", "Manage Categories", "View, edit, or delete categories")
        table.add_row("3", "Download Category", "Download and compress documents")
        table.add_row("4", "Ingest Constitution", "Parse system constitution PDFs")
        table.add_row("5", "Ingest Laws", "Parse building codes and regulations")
        table.add_row("6", "Parse Instructions", "Extract instructions from documents")
        table.add_row("7", "Generate System", "Generate code and rules from instructions")
        table.add_row("8", "View Logs", "View system logs")
        table.add_row("9", "System Status", "View system status")
        table.add_row("0", "Exit", "Exit the dashboard")
        
        console.print(table)
    
    def _explore_gdrive(self):
        """Open the Google Drive explorer."""
        console.print("\n[cyan]🔍 Launching Google Drive Explorer...[/cyan]")
        explorer = GDriveExplorer()
        explorer.run_interactive()
    
    def _manage_categories(self):
        """Manage categories."""
        while True:
            console.clear()
            console.print("[bold cyan]📂 Category Management[/bold cyan]\n")
            
            table = Table(title="Categories")
            table.add_column("Category", style="cyan")
            table.add_column("Files", style="green")
            
            categories = self.category_manager.list_categories()
            total_files = 0
            
            for cat in categories:
                file_ids = self.category_manager.get_category(cat)
                count = len(file_ids) if file_ids else 0
                total_files += count
                table.add_row(cat, str(count))
            
            table.add_section()
            table.add_row("[bold]TOTAL[/bold]", str(total_files))
            console.print(table)
            
            console.print("\n[bold]Commands:[/bold]")
            console.print("  [green]add <category> <file_id>[/green] - Add file to category")
            console.print("  [green]remove <category> <file_id>[/green] - Remove file from category")
            console.print("  [green]delete <category>[/green] - Delete entire category")
            console.print("  [green]merge <source> <target>[/green] - Merge categories")
            console.print("  [red]back[/red] - Return to main menu")
            
            cmd = Prompt.ask("\n[bold yellow]➜[/bold yellow]")
            
            if cmd == 'back':
                break
            elif cmd.startswith('add '):
                parts = cmd.split(' ', 2)
                if len(parts) == 3:
                    category = parts[1]
                    file_id = parts[2]
                    self.category_manager.add_files(category, [file_id])
                    console.print(f"[green]✅ Added file to '{category}'[/green]")
            elif cmd.startswith('remove '):
                parts = cmd.split(' ', 2)
                if len(parts) == 3:
                    category = parts[1]
                    file_id = parts[2]
                    self.category_manager.remove_files(category, [file_id])
                    console.print(f"[green]✅ Removed file from '{category}'[/green]")
            elif cmd.startswith('delete '):
                category = cmd[7:].strip()
                if Confirm.ask(f"Delete category '{category}'?"):
                    self.category_manager.delete_category(category)
            elif cmd.startswith('merge '):
                parts = cmd.split(' ', 2)
                if len(parts) == 3:
                    source, target = parts[1], parts[2]
                    self.category_manager.merge_categories(source, target)
            else:
                console.print(f"[red]Unknown command: {cmd}[/red]")
    
    def _download_category(self):
        """Download and compress a category."""
        categories = self.category_manager.list_categories()
        
        if not categories:
            console.print("[yellow]No categories defined. Explore Google Drive first.[/yellow]")
            return
        
        console.print("\n[bold]Available Categories:[/bold]")
        for i, cat in enumerate(categories, 1):
            file_ids = self.category_manager.get_category(cat)
            count = len(file_ids) if file_ids else 0
            console.print(f"  {i}. {cat} ({count} files)")
        
        choice = Prompt.ask("\n[bold yellow]Select category (number)[/bold yellow]")
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(categories):
                category = categories[idx]
                
                console.print(f"\n[cyan]📦 Downloading: {category}[/cyan]")
                compress = Confirm.ask("Compress after download?")
                
                acquisitor = Acquisitor()
                result = acquisitor.download_category(category, compress=compress)
                
                if result['success']:
                    console.print(Panel(
                        f"[green]✅ Download complete![/green]\n"
                        f"  Files: {result['successful']}/{result['total_files']}\n"
                        f"  Size: {result['total_size_mb']:.1f} MB\n"
                        f"  Compressed: {result['compressed']}\n"
                        f"  ZIP: {result.get('zip_path', 'N/A')}",
                        border_style="green"
                    ))
                else:
                    console.print(f"[red]Download failed: {result.get('error', 'Unknown error')}[/red]")
            else:
                console.print("[red]Invalid selection.[/red]")
        except ValueError:
            console.print("[red]Invalid selection.[/red]")
    
    def _ingest_constitution(self):
        """Parse the constitution PDFs."""
        console.print("\n[cyan]⚖️ Ingesting Constitution...[/cyan]")
        
        try:
            parser = ConstitutionParser()
            data = parser.parse_all()
            
            # Save the parsed data
            output_dir = Path("~/PROMETHEUS/output/constitution").expanduser()
            output_dir.mkdir(parents=True, exist_ok=True)
            
            with open(output_dir / 'constitution_data.json', 'w') as f:
                json.dump(data, f, indent=2)
            
            console.print(Panel(
                f"[green]✅ Constitution ingested![/green]\n"
                f"  Rules: {len(data['rules'])}\n"
                f"  Agents: {len(data['architecture']['agents'])}\n"
                f"  Workflows: {len(data['architecture']['workflows'])}\n"
                f"  Modules: {len(data['architecture']['modules'])}\n"
                f"  Source files: {len(data['source_hashes'])}",
                border_style="green"
            ))
            
            # Register in WORM
            self.worm.append_entry(
                event_type="CONSTITUTION_INGESTED",
                data=data,
                actor="sovereign"
            )
            
        except Exception as e:
            console.print(f"[red]❌ Constitution ingestion failed: {e}[/red]")
    
    def _ingest_laws(self):
        """Ingest building codes and regulations."""
        console.print("\n[cyan]📜 Ingesting Laws...[/cyan]")
        
        # Check if laws directory exists
        laws_dir = Path("~/PROMETHEUS/input/laws").expanduser()
        
        if not laws_dir.exists() or not any(laws_dir.glob("*.pdf")):
            console.print("[yellow]No law PDFs found in input/laws/[/yellow]")
            console.print("[dim]Please place building code PDFs in ~/PROMETHEUS/input/laws/[/dim]")
            return
        
        try:
            ingestor = LawsIngestor()
            result = ingestor.ingest_all()
            
            if result['status'] == 'ingested':
                console.print(Panel(
                    f"[green]✅ Laws ingested![/green]\n"
                    f"  Total laws: {result['total_laws']}\n"
                    f"  Jurisdictions: {', '.join(result['jurisdictions'])}\n"
                    f"  Output: {result['output_dir']}",
                    border_style="green"
                ))
                
                # Register in WORM
                self.worm.append_entry(
                    event_type="LAWS_INGESTED",
                    data=result,
                    actor="sovereign"
                )
            else:
                console.print("[yellow]No laws were ingested.[/yellow]")
                
        except Exception as e:
            console.print(f"[red]❌ Laws ingestion failed: {e}[/red]")
    
    def _parse_instructions(self):
        """Parse instruction documents from downloads."""
        console.print("\n[cyan]📖 Parsing Instructions...[/cyan]")
        
        downloads_dir = Path("~/PROMETHEUS/downloads").expanduser()
        
        if not downloads_dir.exists() or not any(downloads_dir.glob("**/*.pdf")):
            console.print("[yellow]No instruction PDFs found in downloads/[/yellow]")
            console.print("[dim]Please download documents first.[/dim]")
            return
        
        try:
            parser = InstructionParser()
            data = parser.parse_all()
            
            # Save parsed data
            output_dir = Path("~/PROMETHEUS/output/parsed").expanduser()
            output_dir.mkdir(parents=True, exist_ok=True)
            
            with open(output_dir / 'parsed_instructions.json', 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            console.print(Panel(
                f"[green]✅ Instructions parsed![/green]\n"
                f"  Tasks: {len(data['tasks'])}\n"
                f"  Agents: {len(data['agents'])}\n"
                f"  Parsed files: {len(data['parsed_files'])}",
                border_style="green"
            ))
            
        except Exception as e:
            console.print(f"[red]❌ Instruction parsing failed: {e}[/red]")
    
    def _generate_system(self):
        """Generate system code and rules from parsed instructions."""
        console.print("\n[cyan]🔧 Generating System...[/cyan]")
        
        # Check if parsed data exists
        parsed_path = Path("~/PROMETHEUS/output/parsed/parsed_instructions.json").expanduser()
        
        if not parsed_path.exists():
            console.print("[yellow]No parsed instructions found.[/yellow]")
            console.print("[dim]Please parse instructions first.[/dim]")
            return
        
        try:
            with open(parsed_path, 'r') as f:
                parsed_data = json.load(f)
            
            # Generate code
            console.print("[cyan]  Generating code...[/cyan]")
            code_generator = CodeGenerator()
            code_result = code_generator.generate_from_parsed_data(parsed_data)
            
            # Generate rules
            console.print("[cyan]  Generating rules...[/cyan]")
            rule_generator = RuleGenerator()
            rule_result = rule_generator.generate_from_parsed_data(parsed_data)
            
            # Compile agents
            console.print("[cyan]  Compiling agents...[/cyan]")
            agent_compiler = AgentCompiler()
            agent_count = 0
            
            for agent_data in parsed_data.get('agents', []):
                try:
                    agent_compiler.compile_agent(agent_data)
                    agent_count += 1
                except Exception as e:
                    console.print(f"[yellow]  ⚠️ Failed to compile agent {agent_data['name']}: {e}[/yellow]")
            
            console.print(Panel(
                f"[green]✅ System generation complete![/green]\n"
                f"  Code files: {len(code_result['generated_files'])}\n"
                f"  Rules: {rule_result['rules_generated']}\n"
                f"  Keywords: {rule_result['keywords_generated']}\n"
                f"  Agents compiled: {agent_count}",
                border_style="green"
            ))
            
            # Register in WORM
            self.worm.append_entry(
                event_type="SYSTEM_GENERATED",
                data={
                    'code_result': code_result,
                    'rule_result': rule_result,
                    'agent_count': agent_count
                },
                actor="sovereign"
            )
            
        except Exception as e:
            console.print(f"[red]❌ System generation failed: {e}[/red]")
    
    def _view_logs(self):
        """View system logs."""
        console.print("\n[cyan]📋 System Logs[/cyan]")
        
        log_types = ['success', 'errors', 'review_needed']
        
        table = Table(title="Log Types")
        table.add_column("Type", style="cyan")
        table.add_column("Log File", style="dim")
        table.add_column("Recent Entries", style="green")
        
        for log_type in log_types:
            log_path = Path(f"~/PROMETHEUS/logs/{log_type}/{log_type}.log").expanduser()
            entries = 0
            if log_path.exists():
                with open(log_path, 'r') as f:
                    entries = sum(1 for _ in f)
            table.add_row(log_type, str(log_path), str(entries))
        
        console.print(table)
        
        choice = Prompt.ask(
            "\n[bold yellow]Select log type to view[/bold yellow]",
            choices=['success', 'errors', 'review_needed', 'back']
        )
        
        if choice == 'back':
            return
        
        log_path = Path(f"~/PROMETHEUS/logs/{choice}/{choice}.log").expanduser()
        
        if not log_path.exists():
            console.print("[yellow]Log file not found.[/yellow]")
            return
        
        # Show last 20 lines
        with open(log_path, 'r') as f:
            lines = f.readlines()[-20:]
        
        console.print(f"\n[bold]Last {len(lines)} entries from {choice}.log:[/bold]\n")
        for line in lines:
            console.print(line.strip())
        
        if Confirm.ask("\nView full log?"):
            subprocess.run(['less', '-R', str(log_path)])
    
    def _system_status(self):
        """Show system status."""
        console.print("\n[cyan]📊 System Status[/cyan]")
        
        # Check all components
        status = {}
        
        # Check Constitution
        constitution_dir = Path("~/PROMETHEUS/input/constitution").expanduser()
        status['constitution'] = {
            'exists': constitution_dir.exists(),
            'files': len(list(constitution_dir.glob("*.pdf"))) if constitution_dir.exists() else 0
        }
        
        # Check Laws
        laws_dir = Path("~/PROMETHEUS/input/laws").expanduser()
        status['laws'] = {
            'exists': laws_dir.exists(),
            'files': len(list(laws_dir.glob("*.pdf"))) if laws_dir.exists() else 0
        }
        
        # Check Downloads
        downloads_dir = Path("~/PROMETHEUS/downloads").expanduser()
        status['downloads'] = {
            'exists': downloads_dir.exists(),
            'categories': len(list(downloads_dir.iterdir())) if downloads_dir.exists() else 0
        }
        
        # Check Compressed
        compressed_dir = Path("~/PROMETHEUS/compressed").expanduser()
        status['compressed'] = {
            'exists': compressed_dir.exists(),
            'zips': len(list(compressed_dir.glob("*.zip"))) if compressed_dir.exists() else 0
        }
        
        # Check Categories
        categories = self.category_manager.list_categories()
        status['categories'] = {
            'count': len(categories),
            'names': categories[:5]
        }
        
        # Check Generated Code
        generated_dir = Path("~/PROMETHEUS/output/generated_code").expanduser()
        status['generated'] = {
            'exists': generated_dir.exists(),
            'files': len(list(generated_dir.glob("**/*.py"))) if generated_dir.exists() else 0
        }
        
        # Display status
        table = Table(title="System Status", box=box.HEAVY)
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="dim")
        
        for name, info in status.items():
            if name == 'constitution':
                detail = f"{info['files']} PDF files"
            elif name == 'laws':
                detail = f"{info['files']} PDF files"
            elif name == 'downloads':
                detail = f"{info['categories']} categories"
            elif name == 'compressed':
                detail = f"{info['zips']} ZIP files"
            elif name == 'categories':
                detail = f"{info['count']} categories"
            elif name == 'generated':
                detail = f"{info['files']} Python files"
            else:
                detail = str(info)
            
            table.add_row(
                name.replace('_', ' ').title(),
                "✅" if info.get('exists', True) else "❌",
                detail
            )
        
        console.print(table)
        
        # Show WORM status
        worm_status = self.worm.get_status()
        console.print(f"\n[bold]WORM Ledger Status:[/bold]")
        console.print(f"  Entries: {worm_status['total_entries']}")
        console.print(f"  Last block: {worm_status['last_block']}")
        console.print(f"  Integrity: {'✅ OK' if worm_status['integrity'] else '❌ FAILED'}")
    
    def _exit(self):
        """Exit the dashboard."""
        console.print("\n[dim]Shutting down the system...[/dim]")
        console.print("[green]Goodbye, Sovereign.[/green]")

def main():
    """Main entry point."""
    dashboard = SovereignDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()
