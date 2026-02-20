"""L2: Electrochemistry validation - parameter and domain rules on Faraday IR.

Implements merged PV (parameter-value) and DR (domain-rule) checks.
All values in the IR use SI units (V, A, s, Hz, m^2, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ecproc.ir.schema import FaradayIR, IRLoop, IRPhase, IRStep
from ecproc.validator.errors import Severity, ValidationResult

if TYPE_CHECKING:
    from collections.abc import Callable

# ---------------------------------------------------------------------------
# Rule registry
# ---------------------------------------------------------------------------

@dataclass
class Rule:
    """A single validation rule."""
    code: str
    description: str
    severity: Severity
    check: Callable[..., None]  # (step, path, result, **ctx) -> None
    enabled: bool = True


class RuleRegistry:
    """Registry of validation rules with enable/disable capability."""

    def __init__(self) -> None:
        self._rules: dict[str, Rule] = {}

    def register(
        self,
        code: str,
        description: str,
        severity: Severity,
        check: Callable[..., None],
    ) -> None:
        self._rules[code] = Rule(
            code=code, description=description, severity=severity, check=check
        )

    def enable(self, code: str) -> None:
        if code in self._rules:
            self._rules[code].enabled = True

    def disable(self, code: str) -> None:
        if code in self._rules:
            self._rules[code].enabled = False

    def enable_all(self) -> None:
        for rule in self._rules.values():
            rule.enabled = True

    def disable_all(self) -> None:
        for rule in self._rules.values():
            rule.enabled = False

    @property
    def rules(self) -> dict[str, Rule]:
        return dict(self._rules)

    def enabled_rules(self) -> list[Rule]:
        return [r for r in self._rules.values() if r.enabled]


# Global registry
_registry = RuleRegistry()


def get_registry() -> RuleRegistry:
    """Return the global rule registry."""
    return _registry


# ---------------------------------------------------------------------------
# Helper: extract extra fields from IRStep (technique-specific params)
# ---------------------------------------------------------------------------

def _extra(step: IRStep) -> dict[str, Any]:
    """Return extra (technique-specific) fields on an IRStep."""
    known = set(IRStep.model_fields.keys())
    return {k: v for k, v in step.model_dump().items() if k not in known}


# ---------------------------------------------------------------------------
# PV rules (parameter-value errors)
# ---------------------------------------------------------------------------

def _pv001(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """CV scan_rate <= 10 V/s."""
    if step.technique != "cv":
        return
    extras = _extra(step)
    sr = extras.get("scan_rate")
    if sr is not None and sr > 10.0:
        result.add_error(
            "L2", "PV001",
            f"CV scan_rate {sr} V/s exceeds maximum 10 V/s",
            path=f"{path}.scan_rate", expected="<= 10", actual=sr,
        )


def _pv002(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """CV scan_rate >= 0.0001 V/s."""
    if step.technique != "cv":
        return
    extras = _extra(step)
    sr = extras.get("scan_rate")
    if sr is not None and sr < 0.0001:
        result.add_error(
            "L2", "PV002",
            f"CV scan_rate {sr} V/s below minimum 0.0001 V/s",
            path=f"{path}.scan_rate", expected=">= 0.0001", actual=sr,
        )


def _pv003(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """CV cycles > 0."""
    if step.technique != "cv":
        return
    extras = _extra(step)
    cycles = extras.get("cycles")
    if cycles is not None and cycles <= 0:
        result.add_error(
            "L2", "PV003",
            f"CV cycles must be > 0, got {cycles}",
            path=f"{path}.cycles", expected="> 0", actual=cycles,
        )


def _pv004(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """CV vertex1 != vertex2."""
    if step.technique != "cv":
        return
    extras = _extra(step)
    v1 = extras.get("vertex1")
    v2 = extras.get("vertex2")
    if v1 is not None and v2 is not None and v1 == v2:
        result.add_error(
            "L2", "PV004",
            f"CV vertex1 and vertex2 must differ (both are {v1} V)",
            path=f"{path}.vertex1", expected="vertex1 != vertex2", actual=f"{v1} == {v2}",
        )


def _pv005(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """EIS f_start > f_end (sweep high to low)."""
    if step.technique != "eis":
        return
    extras = _extra(step)
    fs = extras.get("f_start")
    fe = extras.get("f_end")
    if fs is not None and fe is not None and fs <= fe:
        result.add_error(
            "L2", "PV005",
            f"EIS f_start ({fs} Hz) must be > f_end ({fe} Hz)",
            path=f"{path}.f_start", expected="f_start > f_end", actual=f"{fs} <= {fe}",
        )


def _pv006(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """EIS f_start <= 10 MHz (10e6 Hz)."""
    if step.technique != "eis":
        return
    extras = _extra(step)
    fs = extras.get("f_start")
    if fs is not None and fs > 10e6:
        result.add_error(
            "L2", "PV006",
            f"EIS f_start {fs} Hz exceeds maximum 10 MHz",
            path=f"{path}.f_start", expected="<= 10e6", actual=fs,
        )


def _pv007(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """EIS f_end >= 1e-6 Hz."""
    if step.technique != "eis":
        return
    extras = _extra(step)
    fe = extras.get("f_end")
    if fe is not None and fe < 1e-6:
        result.add_error(
            "L2", "PV007",
            f"EIS f_end {fe} Hz below minimum 1e-6 Hz",
            path=f"{path}.f_end", expected=">= 1e-6", actual=fe,
        )


def _pv008(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """EIS amplitude > 0."""
    if step.technique != "eis":
        return
    extras = _extra(step)
    amp = extras.get("amplitude")
    if amp is not None and amp <= 0:
        result.add_error(
            "L2", "PV008",
            f"EIS amplitude must be > 0, got {amp} V",
            path=f"{path}.amplitude", expected="> 0", actual=amp,
        )


def _pv009(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """EIS amplitude <= 0.1 V."""
    if step.technique != "eis":
        return
    extras = _extra(step)
    amp = extras.get("amplitude")
    if amp is not None and amp > 0.1:
        result.add_error(
            "L2", "PV009",
            f"EIS amplitude {amp} V exceeds maximum 0.1 V",
            path=f"{path}.amplitude", expected="<= 0.1", actual=amp,
        )


def _pv010(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """All potentials must be in range -10 V <= E <= 10 V."""
    extras = _extra(step)
    potential_fields = [
        "potential", "vertex1", "vertex2", "e_start", "e_end",
        "e_step", "e_dc", "e_initial", "e_final",
    ]
    for fname in potential_fields:
        val = extras.get(fname)
        if val is not None and isinstance(val, (int, float)) and (val < -10.0 or val > 10.0):
            result.add_error(
                "L2", "PV010",
                f"Potential {fname}={val} V outside safe range [-10, 10] V",
                path=f"{path}.{fname}", expected="-10 <= E <= 10", actual=val,
            )


def _pv011(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """Hold duration > 0."""
    if step.technique != "hold":
        return
    extras = _extra(step)
    dur = extras.get("duration")
    if dur is not None and dur <= 0:
        result.add_error(
            "L2", "PV011",
            f"Hold duration must be > 0, got {dur} s",
            path=f"{path}.duration", expected="> 0", actual=dur,
        )


def _pv012_013(loop: IRLoop, path: str, result: ValidationResult) -> None:
    """Loop count > 0 (PV012) and <= 1000000 (PV013)."""
    count = loop.count
    if isinstance(count, str):
        # Variable reference, skip numeric check
        return
    if count <= 0:
        result.add_error(
            "L2", "PV012",
            f"Loop count must be > 0, got {count}",
            path=f"{path}.count", expected="> 0", actual=count,
        )
    if count > 1_000_000:
        result.add_error(
            "L2", "PV013",
            f"Loop count {count} exceeds maximum 1000000",
            path=f"{path}.count", expected="<= 1000000", actual=count,
        )


# ---------------------------------------------------------------------------
# DR rules (domain-rule warnings)
# ---------------------------------------------------------------------------

def _dr001(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """DR001: Potential within solvent electrochemical window (stub)."""
    # Requires electrolyte-specific solvent window data; stub for future.
    pass


def _dr002(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """DR002: Reference electrode compatible with electrolyte (stub)."""
    pass


def _dr003(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """DR003: Temperature within stable range for system (stub)."""
    pass


def _dr004(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """DR004: OCP duration >= 30 s for equilibration."""
    if step.technique != "ocp":
        return
    extras = _extra(step)
    dur = extras.get("duration")
    if dur is not None and dur < 30.0:
        result.add_warning(
            "L2", "DR004",
            f"OCP duration {dur} s is short; >= 30 s recommended for equilibration",
            path=f"{path}.duration", expected=">= 30", actual=dur,
        )


def _dr005(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """DR005: EIS amplitude <= 0.01 V recommended for linearity."""
    if step.technique != "eis":
        return
    extras = _extra(step)
    amp = extras.get("amplitude")
    if amp is not None and amp > 0.01:
        result.add_warning(
            "L2", "DR005",
            f"EIS amplitude {amp} V exceeds 0.01 V; linearity may be compromised",
            path=f"{path}.amplitude", expected="<= 0.01", actual=amp,
        )


def _dr006(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """DR006: Conditioning step before measurement (stub)."""
    pass


def _dr007(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """DR007: Gas purge before ORR/HER measurements (stub)."""
    pass


def _dr008(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """DR008: iR compensation with reference electrode distance (stub)."""
    pass


def _dr009(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """DR009: Current density within electrode area limits (stub)."""
    pass


def _dr010(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """DR010: CV step size vs scan rate ratio (stub)."""
    pass


def _dr011(step: IRStep, path: str, result: ValidationResult, **_: Any) -> None:
    """DR011: CV cycles >= 3 recommended for steady-state."""
    if step.technique != "cv":
        return
    extras = _extra(step)
    cycles = extras.get("cycles")
    if cycles is not None and cycles < 3:
        result.add_warning(
            "L2", "DR011",
            f"CV cycles={cycles}; >= 3 recommended for steady-state assessment",
            path=f"{path}.cycles", expected=">= 3", actual=cycles,
        )


# ---------------------------------------------------------------------------
# Register all rules
# ---------------------------------------------------------------------------

_STEP_RULES: list[tuple[str, str, Severity, Callable[..., None]]] = [
    ("PV001", "CV scan_rate <= 10 V/s", Severity.ERROR, _pv001),
    ("PV002", "CV scan_rate >= 0.0001 V/s", Severity.ERROR, _pv002),
    ("PV003", "CV cycles > 0", Severity.ERROR, _pv003),
    ("PV004", "CV vertex1 != vertex2", Severity.ERROR, _pv004),
    ("PV005", "EIS f_start > f_end", Severity.ERROR, _pv005),
    ("PV006", "EIS f_start <= 10 MHz", Severity.ERROR, _pv006),
    ("PV007", "EIS f_end >= 1e-6 Hz", Severity.ERROR, _pv007),
    ("PV008", "EIS amplitude > 0", Severity.ERROR, _pv008),
    ("PV009", "EIS amplitude <= 0.1 V", Severity.ERROR, _pv009),
    ("PV010", "All potentials in [-10, 10] V", Severity.ERROR, _pv010),
    ("PV011", "Hold duration > 0", Severity.ERROR, _pv011),
    ("DR001", "Potential within solvent window (stub)", Severity.WARNING, _dr001),
    ("DR002", "RE compatible with electrolyte (stub)", Severity.WARNING, _dr002),
    ("DR003", "Temperature in stable range (stub)", Severity.WARNING, _dr003),
    ("DR004", "OCP duration >= 30 s", Severity.WARNING, _dr004),
    ("DR005", "EIS amplitude <= 0.01 V for linearity", Severity.WARNING, _dr005),
    ("DR006", "Conditioning before measurement (stub)", Severity.WARNING, _dr006),
    ("DR007", "Gas purge before ORR/HER (stub)", Severity.WARNING, _dr007),
    ("DR008", "iR comp with reference distance (stub)", Severity.WARNING, _dr008),
    ("DR009", "Current within area limits (stub)", Severity.WARNING, _dr009),
    ("DR010", "CV step size vs scan rate (stub)", Severity.WARNING, _dr010),
    ("DR011", "CV cycles >= 3 for steady-state", Severity.WARNING, _dr011),
]

for _code, _desc, _sev, _fn in _STEP_RULES:
    _registry.register(_code, _desc, _sev, _fn)


# ---------------------------------------------------------------------------
# Walk helpers
# ---------------------------------------------------------------------------

def _walk_steps(
    phase: IRPhase,
    phase_path: str,
    result: ValidationResult,
    rules: list[Rule],
) -> None:
    """Walk all steps in a phase, applying rules."""
    for j, step_or_loop in enumerate(phase.steps):
        _walk_step_or_loop(step_or_loop, f"{phase_path}.steps[{j}]", result, rules)


def _walk_step_or_loop(
    item: IRStep | IRLoop,
    path: str,
    result: ValidationResult,
    rules: list[Rule],
) -> None:
    if isinstance(item, IRStep):
        for rule in rules:
            rule.check(item, path, result)
    elif isinstance(item, IRLoop):
        # PV012/PV013: loop count checks
        _pv012_013(item, path, result)
        for k, sub in enumerate(item.steps):
            _walk_step_or_loop(sub, f"{path}.steps[{k}]", result, rules)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def validate_electrochemistry(ir: FaradayIR) -> ValidationResult:
    """Run L2 electrochemistry validation on a FaradayIR."""
    result = ValidationResult()
    rules = _registry.enabled_rules()

    for i, phase in enumerate(ir.procedure):
        _walk_steps(phase, f"procedure[{i}]", result, rules)

    return result
