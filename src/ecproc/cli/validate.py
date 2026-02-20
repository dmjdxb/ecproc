"""Validate command implementation."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()

def run_validate(
    file: str, *, level: int = 2, hardware: str | None = None, strict: bool = False
) -> None:
    path = Path(file)
    if not path.exists():
        console.print(f"[red]Error: File not found: {path}[/red]")
        raise typer.Exit(2)
    try:
        if path.suffix == ".json":
            from ecproc.ir.serializer import from_file
            ir = from_file(path)
        else:
            from ecproc.ir.generator import generate_ir
            from ecproc.parser.yaml_parser import YAMLParser
            parser = YAMLParser()
            ast = parser.parse_file(path)
            ir = generate_ir(ast)
        from ecproc.validator.engine import ValidationEngine
        engine = ValidationEngine()
        hw = None
        if hardware:
            from ecproc.hardware_profiles.loader import load_profile
            hw = load_profile(hardware)
        result = engine.validate(ir, level=level, hardware=hw)
        if strict:
            from ecproc.validator.errors import Severity
            for issue in result.issues:
                if issue.severity == Severity.WARNING:
                    issue.severity = Severity.ERROR
                    result.valid = False
        if result.valid:
            console.print("[green]Validation passed[/green]")
        else:
            console.print("[red]Validation failed[/red]")
            for issue in result.errors:
                console.print(f"  [red]{issue.code}: {issue.message}[/red]")
            raise typer.Exit(1)
        for issue in result.warnings:
            console.print(f"  [yellow]{issue.code}: {issue.message}[/yellow]")
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e
