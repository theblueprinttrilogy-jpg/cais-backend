#!/usr/bin/env python3
"""
Dashboard Provisional - Interacción y Feedback para el desarrollo de CAIS
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import box
from rich.layout import Layout
from rich.live import Live
from rich.columns import Columns
from rich.syntax import Syntax
from rich.markdown import Markdown

# Importar módulos del sistema
from src.worm.worm_ledger import WormLedger
from src.core.logging_config import ForensicLogger
from src.dashboard.sovereign_vault import run_sovereign_vault

console = Console()

class InteractiveDashboard:
    """
    Dashboard provisional para interacción y feedback.
    """
    
    def __init__(self):
        self.worm = WormLedger()
        self.logger = ForensicLogger()
        self.ideas_file = Path("~/PROMETHEUS/data/ideas.json").expanduser()
        self.feedback_file = Path("~/PROMETHEUS/data/feedback.json").expanduser()
        self.ideas = self._load_ideas()
        self.feedback = self._load_feedback()
    
    def _load_ideas(self) -> List[Dict]:
        """Cargar ideas guardadas."""
        if self.ideas_file.exists():
            with open(self.ideas_file, 'r') as f:
                return json.load(f)
        return []
    
    def _save_ideas(self):
        """Guardar ideas."""
        with open(self.ideas_file, 'w') as f:
            json.dump(self.ideas, f, indent=2, default=str)
    
    def _load_feedback(self) -> List[Dict]:
        """Cargar feedback guardado."""
        if self.feedback_file.exists():
            with open(self.feedback_file, 'r') as f:
                return json.load(f)
        return []
    
    def _save_feedback(self):
        """Guardar feedback."""
        with open(self.feedback_file, 'w') as f:
            json.dump(self.feedback, f, indent=2, default=str)
    
    def run(self):
        """Ejecutar el dashboard interactivo."""
        console.clear()
        self._show_header()
        
        while True:
            self._show_main_menu()
            choice = Prompt.ask(
                "\n[bold cyan]➜[/bold cyan]",
                choices=['1', '2', '3', '4', '5', '6', '7', '8', '0']
            )
            
            if choice == '0':
                break
            elif choice == '1':
                self._system_status()
            elif choice == '2':
                self._add_idea()
            elif choice == '3':
                self._view_ideas()
            elif choice == '4':
                self._add_feedback()
            elif choice == '5':
                self._view_feedback()
            elif choice == '6':
                self._suggest_improvement()
            elif choice == '7':
                self._view_worm_entries()
            elif choice == '8':
                self._access_vault()
    
    def _show_header(self):
        """Mostrar cabecera del dashboard."""
        console.print(Panel.fit(
            "[bold magenta]╔══════════════════════════════════════════════════════════════╗[/]\n"
            "[bold magenta]║          🧠 CAIS - DASHBOARD PROVISIONAL                   ║[/]\n"
            "[bold magenta]║          INTERACCIÓN Y FEEDBACK PARA EL SOBERANO           ║[/]\n"
            "[bold magenta]╚══════════════════════════════════════════════════════════════╝[/]",
            border_style="magenta"
        ))
        console.print("[dim]Bienvenido, Soberano. Este es tu espacio para dar forma al sistema.[/dim]\n")
    
    def _show_main_menu(self):
        """Mostrar menú principal."""
        table = Table(title="[bold]Menú Principal[/bold]", box=box.HEAVY)
        table.add_column("Opción", style="cyan", width=4)
        table.add_column("Acción", style="green")
        table.add_column("Descripción", style="dim")
        
        table.add_row("1", "📊 Estado del Sistema", "Ver estado actual de CAIS")
        table.add_row("2", "💡 Nueva Idea", "Registrar una idea para el sistema")
        table.add_row("3", "📋 Ver Ideas", "Ver todas las ideas registradas")
        table.add_row("4", "📝 Feedback", "Dar feedback sobre el sistema")
        table.add_row("5", "📖 Ver Feedback", "Ver todo el feedback registrado")
        table.add_row("6", "🚀 Sugerir Mejora", "Sugerir una mejora específica")
        table.add_row("7", "🔗 Ver WORM", "Ver entradas del WORM Ledger")
        table.add_row("8", "🔐 Área Segura", "Acceder al Sovereign Vault")
        table.add_row("0", "🚪 Salir", "Cerrar el dashboard")
        
        console.print(table)
    
    def _system_status(self):
        """Mostrar estado del sistema."""
        console.clear()
        self._show_header()
        
        console.print("\n[bold cyan]📊 ESTADO DEL SISTEMA[/bold cyan]\n")
        
        # Verificar componentes
        components = {
            "Constitución": self._check_constitution(),
            "Leyes": self._check_laws(),
            "Códigos Generados": self._check_generated(),
            "Agentes": self._check_agents(),
            "WORM": self._check_worm(),
            "Ideas": len(self.ideas),
            "Feedback": len(self.feedback)
        }
        
        table = Table(title="Componentes del Sistema", box=box.ROUNDED)
        table.add_column("Componente", style="cyan")
        table.add_column("Estado", style="green")
        table.add_column("Detalles", style="dim")
        
        for name, status in components.items():
            if isinstance(status, dict):
                icon = "✅" if status.get('ok', False) else "⚠️"
                details = status.get('details', '')
            else:
                icon = "✅" if status > 0 else "⚠️"
                details = str(status)
            
            table.add_row(name, icon, details)
        
        console.print(table)
        
        # Mostrar resumen
        console.print("\n[bold]Resumen del Sistema:[/bold]")
        console.print(f"  • PDFs de Constitución: {components['Constitución'].get('count', 0)}")
        console.print(f"  • PDFs de Leyes: {components['Leyes'].get('count', 0)}")
        console.print(f"  • Agentes Generados: {components['Agentes']}")
        console.print(f"  • Ideas Registradas: {components['Ideas']}")
        console.print(f"  • Feedback Registrado: {components['Feedback']}")
        
        input("\n[dim]Presiona Enter para continuar...[/dim]")
    
    def _check_constitution(self) -> Dict:
        """Verificar archivos de constitución."""
        path = Path("~/PROMETHEUS/input/constitution").expanduser()
        if path.exists():
            files = list(path.glob("*.pdf"))
            return {'ok': True, 'count': len(files), 'details': f"{len(files)} PDF files"}
        return {'ok': False, 'count': 0, 'details': "No files found"}
    
    def _check_laws(self) -> Dict:
        """Verificar archivos de leyes."""
        path = Path("~/PROMETHEUS/input/laws").expanduser()
        if path.exists():
            files = list(path.glob("*.pdf"))
            return {'ok': True, 'count': len(files), 'details': f"{len(files)} PDF files"}
        return {'ok': False, 'count': 0, 'details': "No files found"}
    
    def _check_generated(self) -> Dict:
        """Verificar código generado."""
        path = Path("~/PROMETHEUS/output/generated_code").expanduser()
        if path.exists():
            files = list(path.glob("*.py"))
            return {'ok': True, 'count': len(files), 'details': f"{len(files)} Python files"}
        return {'ok': False, 'count': 0, 'details': "No files found"}
    
    def _check_agents(self) -> int:
        """Contar agentes generados."""
        path = Path("~/PROMETHEUS/output/generated_code/agents").expanduser()
        if path.exists():
            return len(list(path.glob("*.py")))
        return 0
    
    def _check_worm(self) -> Dict:
        """Verificar WORM Ledger."""
        try:
            status = self.worm.get_status()
            return {'ok': True, 'details': f"{status['total_entries']} entries, Integrity: {'✅' if status['integrity'] else '❌'}"}
        except:
            return {'ok': False, 'details': "WORM not accessible"}
    
    def _add_idea(self):
        """Registrar una nueva idea."""
        console.clear()
        self._show_header()
        
        console.print("\n[bold cyan]💡 NUEVA IDEA[/bold cyan]\n")
        console.print("[dim]Describe tu idea para mejorar CAIS.[/dim]\n")
        
        title = Prompt.ask("[bold]Título de la idea[/bold]")
        description = Prompt.ask("[bold]Descripción[/bold]")
        category = Prompt.ask(
            "[bold]Categoría[/bold]",
            choices=["arquitectura", "funcionalidad", "seguridad", "UX", "rendimiento", "otro"],
            default="funcionalidad"
        )
        priority = Prompt.ask(
            "[bold]Prioridad[/bold]",
            choices=["alta", "media", "baja"],
            default="media"
        )
        
        idea = {
            'id': f"IDEA-{len(self.ideas)+1:04d}",
            'title': title,
            'description': description,
            'category': category,
            'priority': priority,
            'status': 'registrada',
            'created_at': datetime.now().isoformat(),
            'source': 'soberano'
        }
        
        self.ideas.append(idea)
        self._save_ideas()
        
        # Registrar en WORM
        self.worm.append_entry(
            event_type="IDEA_REGISTRADA",
            data=idea,
            actor="soberano"
        )
        
        console.print(f"\n[green]✅ Idea registrada exitosamente![/green]")
        console.print(f"[dim]ID: {idea['id']}[/dim]")
        
        input("\n[dim]Presiona Enter para continuar...[/dim]")
    
    def _view_ideas(self):
        """Ver todas las ideas registradas."""
        console.clear()
        self._show_header()
        
        console.print("\n[bold cyan]📋 IDEAS REGISTRADAS[/bold cyan]\n")
        
        if not self.ideas:
            console.print("[yellow]No hay ideas registradas aún.[/yellow]")
            input("\n[dim]Presiona Enter para continuar...[/dim]")
            return
        
        table = Table(title="Ideas", box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("Título", style="green")
        table.add_column("Categoría", style="yellow")
        table.add_column("Prioridad", style="red")
        table.add_column("Estado", style="dim")
        table.add_column("Fecha", style="dim")
        
        for idea in self.ideas[-20:]:
            table.add_row(
                idea['id'],
                idea['title'][:30],
                idea['category'],
                idea['priority'],
                idea['status'],
                idea['created_at'][:16]
            )
        
        console.print(table)
        
        # Opción para ver detalles
        if Confirm.ask("\n¿Ver detalles de una idea?"):
            idea_id = Prompt.ask("[bold]ID de la idea[/bold]")
            
            idea = next((i for i in self.ideas if i['id'] == idea_id), None)
            if idea:
                console.print(Panel(
                    f"[bold]Título:[/bold] {idea['title']}\n"
                    f"[bold]Descripción:[/bold] {idea['description']}\n"
                    f"[bold]Categoría:[/bold] {idea['category']}\n"
                    f"[bold]Prioridad:[/bold] {idea['priority']}\n"
                    f"[bold]Estado:[/bold] {idea['status']}\n"
                    f"[bold]Creada:[/bold] {idea['created_at']}",
                    title=f"📌 {idea['id']}",
                    border_style="cyan"
                ))
                
                # Opciones de gestión
                console.print("\n[bold]Opciones:[/bold]")
                console.print("1. Cambiar estado")
                console.print("2. Eliminar idea")
                console.print("3. Volver")
                
                choice = Prompt.ask("[bold]➜[/bold]", choices=['1', '2', '3'])
                
                if choice == '1':
                    new_status = Prompt.ask(
                        "Nuevo estado",
                        choices=["registrada", "en_revision", "aprobada", "implementada", "rechazada"],
                        default="registrada"
                    )
                    idea['status'] = new_status
                    self._save_ideas()
                    console.print(f"[green]✅ Estado actualizado a: {new_status}[/green]")
                    
                    self.worm.append_entry(
                        event_type="IDEA_ESTADO_CAMBIADO",
                        data={'idea_id': idea['id'], 'new_status': new_status},
                        actor="soberano"
                    )
                
                elif choice == '2':
                    if Confirm.ask(f"[red]¿Eliminar idea {idea['id']}?[/red]"):
                        self.ideas.remove(idea)
                        self._save_ideas()
                        console.print("[green]✅ Idea eliminada[/green]")
            else:
                console.print("[red]❌ Idea no encontrada[/red]")
        
        input("\n[dim]Presiona Enter para continuar...[/dim]")
    
    def _add_feedback(self):
        """Registrar feedback sobre el sistema."""
        console.clear()
        self._show_header()
        
        console.print("\n[bold cyan]📝 FEEDBACK[/bold cyan]\n")
        console.print("[dim]Comparte tu experiencia y sugerencias sobre el sistema.[/dim]\n")
        
        topic = Prompt.ask("[bold]Tópico[/bold]")
        rating = Prompt.ask(
            "[bold]Calificación (1-10)[/bold]",
            choices=[str(i) for i in range(1, 11)],
            default="5"
        )
        comment = Prompt.ask("[bold]Comentario[/bold]")
        
        feedback = {
            'id': f"FB-{len(self.feedback)+1:04d}",
            'topic': topic,
            'rating': int(rating),
            'comment': comment,
            'created_at': datetime.now().isoformat(),
            'source': 'soberano'
        }
        
        self.feedback.append(feedback)
        self._save_feedback()
        
        # Registrar en WORM
        self.worm.append_entry(
            event_type="FEEDBACK_REGISTRADO",
            data=feedback,
            actor="soberano"
        )
        
        console.print(f"\n[green]✅ Feedback registrado exitosamente![/green]")
        
        input("\n[dim]Presiona Enter para continuar...[/dim]")
    
    def _view_feedback(self):
        """Ver todo el feedback registrado."""
        console.clear()
        self._show_header()
        
        console.print("\n[bold cyan]📖 FEEDBACK REGISTRADO[/bold cyan]\n")
        
        if not self.feedback:
            console.print("[yellow]No hay feedback registrado aún.[/yellow]")
            input("\n[dim]Presiona Enter para continuar...[/dim]")
            return
        
        table = Table(title="Feedback", box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("Tópico", style="green")
        table.add_column("Rating", style="yellow")
        table.add_column("Comentario", style="dim")
        table.add_column("Fecha", style="dim")
        
        for fb in self.feedback[-20:]:
            table.add_row(
                fb['id'],
                fb['topic'][:20],
                f"⭐ {fb['rating']}/10",
                fb['comment'][:30],
                fb['created_at'][:16]
            )
        
        console.print(table)
        
        # Estadísticas
        if self.feedback:
            avg_rating = sum(f['rating'] for f in self.feedback) / len(self.feedback)
            console.print(f"\n[bold]Rating promedio:[/bold] {avg_rating:.1f}/10")
        
        input("\n[dim]Presiona Enter para continuar...[/dim]")
    
    def _suggest_improvement(self):
        """Sugerir una mejora específica."""
        console.clear()
        self._show_header()
        
        console.print("\n[bold cyan]🚀 SUGERIR MEJORA[/bold cyan]\n")
        console.print("[dim]Describe una mejora específica que te gustaría ver en el sistema.[/dim]\n")
        
        improvement = {
            'id': f"IMP-{len(self.ideas)+1:04d}",
            'type': Prompt.ask(
                "[bold]Tipo de mejora[/bold]",
                choices=["nueva_funcionalidad", "optimizacion", "correccion", "documentacion", "seguridad"],
                default="nueva_funcionalidad"
            ),
            'title': Prompt.ask("[bold]Título[/bold]"),
            'description': Prompt.ask("[bold]Descripción detallada[/bold]"),
            'benefit': Prompt.ask("[bold]Beneficio esperado[/bold]"),
            'complexity': Prompt.ask(
                "[bold]Complejidad[/bold]",
                choices=["baja", "media", "alta"],
                default="media"
            ),
            'status': 'sugerida',
            'created_at': datetime.now().isoformat(),
            'source': 'soberano'
        }
        
        self.ideas.append(improvement)
        self._save_ideas()
        
        # Registrar en WORM
        self.worm.append_entry(
            event_type="MEJORA_SUGERIDA",
            data=improvement,
            actor="soberano"
        )
        
        console.print(f"\n[green]✅ Mejora sugerida exitosamente![/green]")
        console.print(f"[dim]ID: {improvement['id']}[/dim]")
        
        input("\n[dim]Presiona Enter para continuar...[/dim]")
    
    def _view_worm_entries(self):
        """Ver entradas del WORM Ledger."""
        console.clear()
        self._show_header()
        
        console.print("\n[bold cyan]🔗 WORM LEDGER ENTRIES[/bold cyan]\n")
        
        entries = self.worm.get_entries(limit=20)
        
        if not entries:
            console.print("[yellow]No hay entradas en el WORM.[/yellow]")
            input("\n[dim]Presiona Enter para continuar...[/dim]")
            return
        
        table = Table(title="Últimas entradas WORM", box=box.ROUNDED)
        table.add_column("Secuencia", style="cyan")
        table.add_column("Evento", style="green")
        table.add_column("Actor", style="yellow")
        table.add_column("Hash", style="dim")
        table.add_column("Timestamp", style="dim")
        
        for entry in entries[:20]:
            table.add_row(
                str(entry.get('sequence', '?')),
                entry.get('event_type', '?')[:20],
                entry.get('actor', '?'),
                entry.get('hash', '?')[:16] + '...',
                entry.get('timestamp', '?')[:16]
            )
        
        console.print(table)
        
        # Verificar integridad
        is_valid, errors = self.worm.verify_integrity()
        console.print(f"\n[bold]Integridad WORM:[/bold] {'✅ OK' if is_valid else '❌ CORRUPTA'}")
        if errors:
            for error in errors[:5]:
                console.print(f"[red]  • {error}[/red]")
        
        input("\n[dim]Presiona Enter para continuar...[/dim]")
    
    def _access_vault(self):
        """Acceder al Área Segura."""
        console.print("\n[bold red]🔐 Accediendo al Área Segura...[/bold red]")
        run_sovereign_vault()


def main():
    """Punto de entrada principal."""
    dashboard = InteractiveDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()
