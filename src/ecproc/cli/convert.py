"""Convert command implementation."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()

def run_convert(file: str, *, to: str = "ir", output: str | None = None) -> None:
    path = Path(file)
    if not path.exists():
        console.print(f"[red]Error: File not found: {path}[/red]")
        raise typer.Exit(2)
    console.print(f"[yellow]Convert to '{to}' not yet fully implemented[/yellow]")
