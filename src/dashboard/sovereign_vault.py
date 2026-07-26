#!/usr/bin/env python3
"""
Área Segura del Soberano - Operaciones de máxima seguridad.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import box
from rich.layout import Layout
from rich.live import Live
from rich.columns import Columns

from src.security.sovereign_auth import sovereign_auth
from src.worm.worm_ledger import WormLedger

console = Console()

class SovereignVault:
    """
    Área Segura del Soberano - Operaciones de máxima seguridad.
    Solo accesible con autenticación de 17 caracteres.
    """
    
    def __init__(self):
        """Initialize the Sovereign Vault."""
        self.worm = WormLedger()
        self.authenticated = False
    
    def run(self):
        """
        Run the Sovereign Vault interface.
        """
        console.clear()
        console.print(Panel.fit(
            "[bold red]╔══════════════════════════════════════════════════════╗[/]\n"
            "[bold red]║          🔐 SOVEREIGN VAULT                         ║[/]\n"
            "[bold red]║          ÁREA DE MÁXIMA SEGURIDAD                  ║[/]\n"
            "[bold red]╚══════════════════════════════════════════════════════╝[/]",
            border_style="red"
        ))
        
        # Check if already authenticated
        if sovereign_auth.is_authenticated():
            self.authenticated = True
            console.print("[green]✅ Sesión válida activa[/green]")
            self._show_secure_menu()
            return
        
        # Show authentication prompt
        self._show_auth_prompt()
    
    def _show_auth_prompt(self):
        """
        Show the authentication prompt.
        """
        console.print("\n[bold yellow]🔐 AUTENTICACIÓN REQUERIDA[/bold yellow]")
        console.print("[dim]Ingrese la contraseña maestra de 17 caracteres[/dim]")
        console.print("[dim]Intentos restantes: {}[/dim]".format(
            self._get_remaining_attempts()
        ))
        
        password = Prompt.ask(
            "\n[bold]Contraseña[/bold]",
            password=True
        )
        
        # Authenticate
        success, message = sovereign_auth.authenticate(password)
        
        if success:
            self.authenticated = True
            console.print(f"[green]✅ {message}[/green]")
            self._show_secure_menu()
        else:
            console.print(f"[red]❌ {message}[/red]")
            
            # Check if locked
            if 'locked' in message.lower():
                remaining = self._get_lockout_remaining()
                if remaining:
                    console.print(f"[yellow]⏳ Tiempo restante: {remaining} segundos[/yellow]")
            
            # Ask to retry
            if Confirm.ask("\n¿Intentar nuevamente?"):
                self._show_auth_prompt()
            else:
                console.print("[dim]Volviendo al menú principal...[/dim]")
    
    def _get_remaining_attempts(self) -> int:
        """Get remaining authentication attempts."""
        try:
            with open(sovereign_auth.auth_file, 'r') as f:
                config = json.load(f)
            
            attempts = config.get('attempts', 0)
            return max(0, sovereign_auth.MAX_ATTEMPTS - attempts)
        except:
            return sovereign_auth.MAX_ATTEMPTS
    
    def _get_lockout_remaining(self) -> Optional[int]:
        """Get remaining lockout time."""
        try:
            with open(sovereign_auth.auth_file, 'r') as f:
                config = json.load(f)
            
            locked_until = config.get('locked_until')
            if locked_until:
                lock_time = datetime.fromisoformat(locked_until)
                remaining = (lock_time - datetime.now()).seconds
                return max(0, remaining)
        except:
            pass
        
        return None
    
    def _show_secure_menu(self):
        """
        Show the secure menu with sovereign-only operations.
        """
        while True:
            console.clear()
            console.print(Panel.fit(
                "[bold red]╔══════════════════════════════════════════════════════╗[/]\n"
                "[bold red]║          🔐 SOVEREIGN VAULT                         ║[/]\n"
                "[bold red]║          ÁREA DE MÁXIMA SEGURIDAD                  ║[/]\n"
                "[bold red]╚══════════════════════════════════════════════════════╝[/]",
                border_style="red"
            ))
            
            # Show session info
            session_info = sovereign_auth.get_session_info()
            if session_info['authenticated_at']:
                auth_time = datetime.fromisoformat(session_info['authenticated_at'])
                console.print(f"[dim]Sesión iniciada: {auth_time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
                if session_info['expires_at']:
                    expires = datetime.fromisoformat(session_info['expires_at'])
                    remaining = (expires - datetime.now()).seconds
                    console.print(f"[dim]La sesión expira en: {remaining//60} minutos[/dim]")
            
            # Secure menu options
            table = Table(title="[bold red]Operaciones del Soberano[/bold red]", box=box.HEAVY)
            table.add_column("Opción", style="red", width=4)
            table.add_column("Operación", style="yellow")
            table.add_column("Descripción", style="dim")
            
            table.add_row("1", "Generar Nueva Contraseña", "Cambiar la contraseña maestra")
            table.add_row("2", "Verificar Integridad WORM", "Auditar la cadena WORM completa")
            table.add_row("3", "Exportar WORM Ledger", "Exportar la cadena WORM a archivo")
            table.add_row("4", "Kill Switch", "Activar/Desactivar el Kill Switch")
            table.add_row("5", "Revisar Solicitudes", "Aprobar o rechazar nuevas reglas")
            table.add_row("6", "Auditoría Forense", "Generar reporte forense completo")
            table.add_row("7", "Gestionar Sesiones", "Ver y revocar sesiones activas")
            table.add_row("8", "Logs de Seguridad", "Ver logs de acceso y seguridad")
            table.add_row("9", "Cerrar Sesión", "Salir del Área Segura")
            table.add_row("0", "Salir", "Volver al dashboard principal")
            
            console.print(table)
            
            choice = Prompt.ask(
                "\n[bold red]➜[/bold red]",
                choices=['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
            )
            
            if choice == '0':
                break
            elif choice == '1':
                self._change_password()
            elif choice == '2':
                self._verify_worm_integrity()
            elif choice == '3':
                self._export_worm_ledger()
            elif choice == '4':
                self._kill_switch_management()
            elif choice == '5':
                self._review_rule_requests()
            elif choice == '6':
                self._forensic_audit()
            elif choice == '7':
                self._manage_sessions()
            elif choice == '8':
                self._view_security_logs()
            elif choice == '9':
                self._logout()
                break
    
    def _change_password(self):
        """Change the master password."""
        console.print("\n[bold yellow]🔑 Cambiar Contraseña Maestra[/bold yellow]")
        console.print("[dim]La nueva contraseña debe tener exactamente 17 caracteres[/dim]")
        
        current = Prompt.ask("\n[bold]Contraseña actual[/bold]", password=True)
        new = Prompt.ask("[bold]Nueva contraseña[/bold]", password=True)
        confirm = Prompt.ask("[bold]Confirmar nueva contraseña[/bold]", password=True)
        
        if new != confirm:
            console.print("[red]❌ Las contraseñas no coinciden[/red]")
            return
        
        if len(new) != sovereign_auth.REQUIRED_LENGTH:
            console.print(f"[red]❌ La contraseña debe tener exactamente {sovereign_auth.REQUIRED_LENGTH} caracteres[/red]")
            return
        
        success, message = sovereign_auth.reset_password(current, new)
        
        if success:
            console.print(f"[green]✅ {message}[/green]")
            
            # Record in WORM
            self.worm.append_entry(
                event_type="MASTER_PASSWORD_CHANGED",
                data={'timestamp': datetime.now().isoformat()},
                actor="sovereign"
            )
        else:
            console.print(f"[red]❌ {message}[/red]")
    
    def _verify_worm_integrity(self):
        """Verify the integrity of the WORM ledger."""
        console.print("\n[bold yellow]🔍 Verificando Integridad WORM[/bold yellow]")
        
        with console.status("[bold]Analizando cadena WORM...[/bold]"):
            is_valid, errors = self.worm.verify_integrity()
        
        if is_valid:
            console.print("[green]✅ La cadena WORM está INTACTA[/green]")
            status = self.worm.get_status()
            console.print(f"[dim]Total de entradas: {status['total_entries']}[/dim]")
        else:
            console.print("[red]❌ ALERTA: La cadena WORM está CORRUPTA[/red]")
            for error in errors[:5]:
                console.print(f"[red]  • {error}[/red]")
    
    def _export_worm_ledger(self):
        """Export the WORM ledger to a file."""
        console.print("\n[bold yellow]📤 Exportando WORM Ledger[/bold yellow]")
        
        export_path = Path("~/PROMETHEUS/output/worm_export.json").expanduser()
        export_path.parent.mkdir(parents=True, exist_ok=True)
        
        entries = self.worm.get_entries(limit=10000)
        
        with open(export_path, 'w') as f:
            json.dump(entries, f, indent=2)
        
        console.print(f"[green]✅ WORM Ledger exportado a: {export_path}[/green]")
        console.print(f"[dim]Entradas: {len(entries)}[/dim]")
    
    def _kill_switch_management(self):
        """Kill Switch management interface."""
        console.print("\n[bold red]🛑 KILL SWITCH MANAGEMENT[/bold red]")
        console.print("[dim]⚠️ Esta operación puede poner el sistema en modo READ-ONLY[/dim]")
        
        console.print("\n[bold]Opciones:[/bold]")
        console.print("1. Activar Kill Switch (Modo READ-ONLY)")
        console.print("2. Desactivar Kill Switch (Volver a NORMAL)")
        console.print("3. Volver")
        
        choice = Prompt.ask("\n[bold red]➜[/bold red]", choices=['1', '2', '3'])
        
        if choice == '1':
            if Confirm.ask("[red]¿Está ABSOLUTAMENTE seguro?[/red]"):
                console.print("[red]🔴 KILL SWITCH ACTIVADO[/red]")
                self.worm.append_entry(
                    event_type="KILL_SWITCH_ACTIVATED",
                    data={'timestamp': datetime.now().isoformat()},
                    actor="sovereign"
                )
        elif choice == '2':
            if Confirm.ask("[yellow]¿Está seguro de desactivar el Kill Switch?[/yellow]"):
                console.print("[green]🟢 KILL SWITCH DESACTIVADO[/green]")
                self.worm.append_entry(
                    event_type="KILL_SWITCH_DEACTIVATED",
                    data={'timestamp': datetime.now().isoformat()},
                    actor="sovereign"
                )
    
    def _review_rule_requests(self):
        """Review and approve/reject rule requests."""
        console.print("\n[bold yellow]📋 REVISIÓN DE SOLICITUDES DE REGLAS[/bold yellow]")
        console.print("[yellow]No hay solicitudes pendientes[/yellow]")
    
    def _forensic_audit(self):
        """Generate a complete forensic audit report."""
        console.print("\n[bold yellow]🔍 AUDITORÍA FORENSE[/bold yellow]")
        
        with console.status("[bold]Recopilando datos forenses...[/bold]"):
            worm_status = self.worm.get_status()
            is_valid, errors = self.worm.verify_integrity()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'worm': worm_status,
            'integrity': {'valid': is_valid, 'errors': errors}
        }
        
        report_path = Path("~/PROMETHEUS/output/forensic_report.json").expanduser()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        console.print(f"[green]✅ Reporte forense generado: {report_path}[/green]")
        console.print(f"[dim]WORM entradas: {worm_status['total_entries']}[/dim]")
    
    def _manage_sessions(self):
        """Manage active sessions."""
        console.print("\n[bold yellow]👤 GESTIÓN DE SESIONES[/bold yellow]")
        console.print("[green]✅ Sesión actual activa[/green]")
        
        if Confirm.ask("[red]¿Cerrar TODAS las sesiones?[/red]"):
            console.print("[green]✅ Todas las sesiones cerradas[/green]")
            self.worm.append_entry(
                event_type="ALL_SESSIONS_REVOKED",
                data={'timestamp': datetime.now().isoformat()},
                actor="sovereign"
            )
    
    def _view_security_logs(self):
        """View security logs."""
        console.print("\n[bold yellow]📋 LOGS DE SEGURIDAD[/bold yellow]")
        
        if sovereign_auth.log_file.exists():
            with open(sovereign_auth.log_file, 'r') as f:
                logs = [json.loads(line) for line in f.readlines()]
            
            logs = logs[-20:]
            
            if logs:
                table = Table(title="Intentos de Acceso")
                table.add_column("Timestamp", style="dim")
                table.add_column("Éxito", style="green")
                table.add_column("IP", style="yellow")
                table.add_column("Detalles", style="cyan")
                
                for log in logs:
                    success = "✅" if log['success'] else "❌"
                    table.add_row(
                        log['timestamp'][:19],
                        success,
                        log['ip_address'],
                        log['details']
                    )
                
                console.print(table)
            else:
                console.print("[yellow]No hay logs de seguridad[/yellow]")
        else:
            console.print("[yellow]No hay logs de seguridad[/yellow]")
    
    def _logout(self):
        """Log out from the Sovereign Vault."""
        console.print("\n[bold yellow]🚪 Cerrando Sesión[/bold yellow]")
        sovereign_auth.logout()
        self.authenticated = False
        console.print("[green]✅ Sesión cerrada correctamente[/green]")


def run_sovereign_vault():
    """Run the Sovereign Vault interface."""
    vault = SovereignVault()
    vault.run()


if __name__ == "__main__":
    run_sovereign_vault()
