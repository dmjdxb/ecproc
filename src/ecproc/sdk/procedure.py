"""Procedure class - main entry point for programmatic procedure definition."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from ecproc.parser.ast import (
    ElectrolyteAST,
    MetadataAST,
    OutputAST,
    PhaseAST,
    ProcedureAST,
    SafetyAST,
    StateRecoveryAST,
    SystemAST,
    WorkingElectrodeAST,
)
from ecproc.sdk.phase import Phase

if TYPE_CHECKING:
    from collections.abc import Generator


class Procedure:
    """Main entry point for programmatic procedure definition.

    Example:
        proc = Procedure("My Experiment", version="1.0")
        proc.system(electrodes=3, reference="RHE")
        with proc.phase("Conditioning") as p:
            p.cv(vertex1=0.05, vertex2=1.2, rate=50, cycles=50)
    """

    def __init__(
        self,
        name: str,
        *,
        version: str = "1.0",
        author: str | None = None,
        **metadata: Any,
    ) -> None:
        self._name = name
        self._version = version
        self._author = author
        self._extra_metadata = metadata
        self._system: SystemAST | None = None
        self._phases: list[PhaseAST] = []
        self._safety: SafetyAST | None = None
        self._state_recovery: StateRecoveryAST | None = None
        self._output: OutputAST | None = None
        self._current_phase: Phase | None = None
        self._variables: dict[str, dict[str, Any]] = {}

    def system(
        self,
        electrodes: int = 3,
        reference: str = "RHE",
        *,
        working: dict[str, Any] | None = None,
        electrolyte: tuple[str, float] | dict[str, Any] | str | None = None,
        counter: str | None = None,
    ) -> None:
        """Define system configuration."""
        we = None
        if working:
            we = WorkingElectrodeAST(
                material=working.get("material", ""),
                area_cm2=working.get("area_cm2"),
                loading_ug_cm2=working.get("loading_ug_cm2"),
                additional={k: v for k, v in working.items()
                           if k not in ("material", "area_cm2", "loading_ug_cm2")} or None,
            )

        elyte: str | ElectrolyteAST | None = None
        if electrolyte is not None:
            if isinstance(electrolyte, str):
                elyte = electrolyte
            elif isinstance(electrolyte, tuple):
                elyte = ElectrolyteAST(solute=electrolyte[0], concentration_M=electrolyte[1])
            elif isinstance(electrolyte, dict):
                elyte = ElectrolyteAST(
                    solute=electrolyte["solute"],
                    concentration_M=electrolyte["concentration_M"],
                    additional={k: v for k, v in electrolyte.items()
                               if k not in ("solute", "concentration_M")} or None,
                )

        self._system = SystemAST(
            electrodes=electrodes,
            reference=reference,
            working=we,
            electrolyte=elyte,
            counter=counter,
        )

    def safety(self, **kwargs: Any) -> None:
        """Define safety constraints."""
        self._safety = SafetyAST(
            max_current=kwargs.get("max_current"),
            voltage_window=kwargs.get("voltage_window"),
            temperature_limits=kwargs.get("temperature_limits"),
            stop_if=kwargs.get("stop_if"),
        )

    def state_recovery(self, **kwargs: Any) -> None:
        """Define state recovery behavior."""
        self._state_recovery = StateRecoveryAST(
            after_pause=kwargs.get("after_pause"),
            after_checkpoint=kwargs.get("after_checkpoint"),
            after_error=kwargs.get("after_error"),
        )

    def output(self, **kwargs: Any) -> None:
        """Define output configuration."""
        self._output = OutputAST(ecdl=kwargs.get("ecdl"))

    def variable(self, name: str, *, type: type = float, unit: str = "") -> None:
        """Declare an extracted variable."""
        self._variables[name] = {"type": type.__name__, "unit": unit}

    @contextmanager
    def phase(self, name: str) -> Generator[Phase, None, None]:
        """Context manager for defining a phase."""
        phase = Phase(name)
        self._current_phase = phase
        try:
            yield phase
        finally:
            self._phases.append(phase.to_ast())
            self._current_phase = None

    def to_ast(self) -> ProcedureAST:
        """Convert to internal AST."""
        if self._system is None:
            self._system = SystemAST(electrodes=3, reference="RHE")

        metadata = MetadataAST(
            protocol=self._name,
            version=self._version,
            author=self._author,
            additional=self._extra_metadata or None,
        )

        return ProcedureAST(
            metadata=metadata,
            system=self._system,
            procedure=list(self._phases),
            safety=self._safety,
            state_recovery=self._state_recovery,
            output=self._output,
        )

    def compile(self, target: str = "python") -> Any:
        """Compile procedure to target."""
        from ecproc.ir.generator import generate_ir
        ast = self.to_ast()
        ir = generate_ir(ast)
        # Target compilation would go here
        return ir

    def validate(self, level: int = 2) -> Any:
        """Validate the procedure."""
        from ecproc.ir.generator import generate_ir
        from ecproc.validator.engine import ValidationEngine
        ast = self.to_ast()
        ir = generate_ir(ast)
        engine = ValidationEngine()
        return engine.validate(ir, level=level)
