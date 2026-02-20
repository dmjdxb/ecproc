"""CLI entry point using Typer."""

from __future__ import annotations

import typer

from ecproc._version import __version__

app = typer.Typer(
    name="ecproc",
    help="Electrochemical procedure toolchain",
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(False, "--version", help="Show version"),
) -> None:
    if version:
        typer.echo(f"ecproc {__version__}")
        raise typer.Exit()


@app.command()
def parse(
    file: str = typer.Argument(..., help="Path to .ecproc or .py file"),
    format: str = typer.Option("json", help="Output format: json or tree"),
    output: str = typer.Option(None, "-o", "--output", help="Output file path"),
) -> None:
    """Parse an .ecproc file to Faraday IR."""
    from ecproc.cli.parse import run_parse
    run_parse(file, format=format, output=output)


@app.command()
def validate(
    file: str = typer.Argument(..., help="Path to .ecproc or .ir.json file"),
    level: int = typer.Option(2, "--level", help="Validation level (1-4)"),
    hardware: str = typer.Option(None, "--hardware", help="Hardware profile name"),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as errors"),
) -> None:
    """Validate a procedure."""
    from ecproc.cli.validate import run_validate
    run_validate(file, level=level, hardware=hardware, strict=strict)


@app.command()
def compile(
    file: str = typer.Argument(..., help="Path to .ecproc or .ir.json file"),
    target: str = typer.Option("python", "--target", help="Target: python or manual"),
    output: str = typer.Option(None, "-o", "--output", help="Output directory"),
) -> None:
    """Compile a procedure to target format."""
    from ecproc.cli.compile import run_compile
    run_compile(file, target=target, output=output)


@app.command()
def run(
    file: str = typer.Argument(..., help="Path to .ecproc or .ir.json file"),
    target: str = typer.Option("python", "--target", help="Target runtime"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate execution"),
    output: str = typer.Option(".", "-o", "--output", help="Output directory"),
) -> None:
    """Run a procedure."""
    from ecproc.cli.run import run_procedure
    run_procedure(file, target=target, dry_run=dry_run, output=output)


@app.command()
def execute(
    file: str = typer.Argument(..., help="Path to .ecproc file"),
    hardware: str = typer.Option("mock", "--hardware", help="Hardware profile"),
    output: str = typer.Option(".", "-o", "--output", help="Output directory"),
) -> None:
    """Parse, validate, compile, and execute in one step."""
    from ecproc.cli.execute import run_execute
    run_execute(file, hardware=hardware, output=output)


@app.command()
def convert(
    file: str = typer.Argument(..., help="Source file"),
    to: str = typer.Option("ir", "--to", help="Target format: yaml, python, ir, ecdl"),
    output: str = typer.Option(None, "-o", "--output", help="Output file"),
) -> None:
    """Convert between formats."""
    from ecproc.cli.convert import run_convert
    run_convert(file, to=to, output=output)


@app.command()
def manual(
    file: str = typer.Argument(..., help="Path to .ecproc file"),
    format: str = typer.Option("md", "--format", help="Output format: md or pdf"),
    output: str = typer.Option(None, "-o", "--output", help="Output file"),
) -> None:
    """Generate human-readable procedure manual."""
    from ecproc.cli.manual import run_manual
    run_manual(file, format=format, output=output)
