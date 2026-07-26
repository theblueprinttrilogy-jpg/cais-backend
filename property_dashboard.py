#!/usr/bin/env python3
"""
Property Acquisition Dashboard
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from property_acquisition.search_engine import SearchEngine
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box

console = Console()


class PropertyDashboard:
    def __init__(self):
        self.engine = SearchEngine()

    def run(self):
        while True:
            console.clear()
            console.print(Panel.fit("[bold cyan]🏗️ PROPERTY ACQUISITION DASHBOARD[/]", border_style="cyan"))

            table = Table(box=box.HEAVY)
            table.add_column("Option", style="cyan")
            table.add_column("Action", style="green")

            table.add_row("1", "Search Properties")
            table.add_row("2", "View History")
            table.add_row("0", "Exit")

            console.print(table)

            choice = Prompt.ask("\n[bold yellow]➜[/bold yellow]", choices=["1", "2", "0"])

            if choice == "0":
                console.print("[green]Goodbye![/green]")
                break
            elif choice == "1":
                self._search()
            elif choice == "2":
                self._history()

    def _search(self):
        query = Prompt.ask("[bold]Enter your search[/bold]")
        if not query:
            return

        with console.status("[bold]Searching...[/bold]"):
            result = self.engine.search(query)

        console.print(f"\n[green]✅ Found {result['total_properties']} properties[/green]\n")

        for i, item in enumerate(result["results"][:5], 1):
            prop = item["property"]
            feasible = item["feasibility"]
            console.print(f"[{i}] {prop.address.street}, {prop.address.city}, {prop.address.state}")
            console.print(f"    Price: ${prop.price:,.0f} | Size: {prop.size_sqft:.0f} sqft")
            console.print(f"    Score: {feasible.score:.0f}/100 | ROI: {feasible.roi:.1f}%")
            console.print()

        if result["results"] and Confirm.ask("Add top result to favorites?"):
            console.print("[green]✅ Added![/green]")

        input("\nPress Enter to continue...")

    def _history(self):
        history = self.engine.search_history
        if not history:
            console.print("[yellow]No search history[/yellow]")
            input("\nPress Enter to continue...")
            return

        table = Table(title="Search History")
        table.add_column("Query", style="cyan")
        table.add_column("Results", style="green")
        table.add_column("Timestamp", style="dim")

        for h in history[-10:]:
            table.add_row(h["query"], str(h["results"]), h["timestamp"][:16])

        console.print(table)
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    dashboard = PropertyDashboard()
    dashboard.run()
