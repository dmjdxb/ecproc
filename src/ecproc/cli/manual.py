"""Manual command implementation."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()

def run_manual(file: str, *, format: str = "md", output: str | None = None) -> None:
    path = Path(file)
    if not path.exists():
        console.print(f"[red]Error: File not found: {path}[/red]")
        raise typer.Exit(2)
    try:
        from ecproc.ir.generator import generate_ir
        from ecproc.parser.yaml_parser import YAMLParser
        from ecproc.targets.manual.compiler import compile_to_manual
        from ecproc.targets.manual.markdown import render_markdown
        parser = YAMLParser()
        ast = parser.parse_file(path)
        ir = generate_ir(ast)
        compiled = compile_to_manual(ir)
        md = render_markdown(compiled.output, title=ir.metadata.protocol)
        if output:
            Path(output).write_text(md, encoding="utf-8")
            console.print(f"[green]Manual written to {output}[/green]")
        else:
            console.print(md)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e
