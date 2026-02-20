"""Run command implementation."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()

def run_procedure(
    file: str, *, target: str = "python", dry_run: bool = False, output: str = "."
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
        from ecproc.targets.python.compiler import compile_to_python
        from ecproc.targets.python.hardware.mock import MockHardware
        from ecproc.targets.python.runtime import PythonRuntime
        compiled = compile_to_python(ir)
        runtime = PythonRuntime(MockHardware())
        result = runtime.execute(compiled.output, dry_run=dry_run)
        if result.success:
            n = len(result.observations)
            console.print(f"[green]Execution complete ({n} observations)[/green]")
        else:
            console.print(f"[red]Execution failed: {result.errors}[/red]")
            raise typer.Exit(4)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Runtime error: {e}[/red]")
        raise typer.Exit(4) from e
