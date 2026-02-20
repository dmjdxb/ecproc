"""Compile command implementation."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()

def run_compile(file: str, *, target: str = "python", output: str | None = None) -> None:
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
        if target == "manual":
            from ecproc.targets.manual.compiler import compile_to_manual
            compile_to_manual(ir)
        else:
            from ecproc.targets.python.compiler import compile_to_python
            compile_to_python(ir)
        console.print(f"[green]Compiled to {target} target[/green]")
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Compilation error: {e}[/red]")
        raise typer.Exit(3) from e
