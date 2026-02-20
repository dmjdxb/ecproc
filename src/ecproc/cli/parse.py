"""Parse command implementation."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()

def run_parse(file: str, *, format: str = "json", output: str | None = None) -> None:
    path = Path(file)
    if not path.exists():
        console.print(f"[red]Error: File not found: {path}[/red]")
        raise typer.Exit(2)
    try:
        from ecproc.ir.generator import generate_ir
        from ecproc.ir.serializer import to_json
        from ecproc.parser.yaml_parser import YAMLParser
        parser = YAMLParser()
        ast = parser.parse_file(path)
        ir = generate_ir(ast)
        result = to_json(ir)
        if output:
            Path(output).write_text(result, encoding="utf-8")
            console.print(f"[green]IR written to {output}[/green]")
        else:
            console.print(result)
    except Exception as e:
        console.print(f"[red]Parse error: {e}[/red]")
        raise typer.Exit(2) from e
