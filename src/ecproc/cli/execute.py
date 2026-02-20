"""Execute command - all-in-one parse, validate, compile, run."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()

def run_execute(file: str, *, hardware: str = "mock", output: str = ".") -> None:
    path = Path(file)
    if not path.exists():
        console.print(f"[red]Error: File not found: {path}[/red]")
        raise typer.Exit(2)
    try:
        from ecproc.ir.generator import generate_ir
        from ecproc.parser.yaml_parser import YAMLParser
        from ecproc.targets.python.compiler import compile_to_python
        from ecproc.targets.python.hardware.mock import MockHardware
        from ecproc.targets.python.runtime import PythonRuntime
        from ecproc.validator.engine import ValidationEngine
        parser = YAMLParser()
        ast = parser.parse_file(path)
        ir = generate_ir(ast)
        engine = ValidationEngine()
        vresult = engine.validate(ir, level=2)
        if not vresult.valid:
            console.print("[red]Validation failed[/red]")
            for issue in vresult.errors:
                console.print(f"  {issue.code}: {issue.message}")
            raise typer.Exit(1)
        compiled = compile_to_python(ir)
        runtime = PythonRuntime(MockHardware())
        result = runtime.execute(compiled.output)
        if result.success:
            from ecproc.ecdl.generator import generate_ecdl
            from ecproc.ecdl.serializer import to_file as ecdl_to_file
            ecdl = generate_ecdl(ir, result)
            out_path = Path(output) / f"{path.stem}.ecdl.json"
            ecdl_to_file(ecdl, out_path)
            console.print(f"[green]ECDL written to {out_path}[/green]")
        else:
            console.print("[red]Execution failed[/red]")
            raise typer.Exit(4)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e
