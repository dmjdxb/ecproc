"""Python SDK introspection parser."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ecproc.parser.ast import ProcedureAST
    from ecproc.sdk.procedure import Procedure


class PythonParser:
    """Introspects SDK Procedure objects into AST."""
    def parse_procedure(self, proc: Procedure) -> ProcedureAST:
        return proc.to_ast()
