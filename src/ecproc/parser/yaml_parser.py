"""YAML parser for .ecproc procedure files.

Transforms .ecproc YAML into an internal :class:`ProcedureAST`.  The parser
preserves source-location information (line numbers) for every AST node so
that downstream validation errors can point back to the originating YAML.

Supported syntax features
-------------------------
* Value+unit strings  – ``rate: 50 mV/s``
* Range syntax        – ``between: 0.05 V and 1.2 V``
* Duration syntax     – ``for: 20 min``
* Phase structure     – ``setup / stabilize / steps / teardown``
* Step tags           – ``tag: "bol_cv"``
* Extract fields      – string or dict form
* Vendor flags        – per-vendor parameter dicts
* Loops               – ``loop: {count: N, steps: [...], checkpoint: {...}}``
* Checkpoints         – ``trigger: {any: [...]}`` wrapper transformation
* State recovery      – ``after_pause / after_checkpoint / after_error``
* Output section      – ``ecdl: {...}``
* Variable templates  – ``"{variable}"`` preserved as strings
* Source line tracking – via custom PyYAML loader
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from yaml import MappingNode, ScalarNode, SequenceNode

from ecproc.parser.ast import (
    CheckpointAST,
    ElectrolyteAST,
    LoopAST,
    MetadataAST,
    OutputAST,
    PhaseAST,
    ProcedureAST,
    ReferenceMonitorAST,
    SafetyAST,
    SourceLocation,
    StateRecoveryAST,
    StepAST,
    SystemAST,
    ThermalRunawayAST,
    TriggerAST,
    WorkingElectrodeAST,
)
from ecproc.parser.errors import (
    InvalidSyntaxError,
    MissingFieldError,
    UnknownTechniqueError,
    YAMLStructureError,
)

# ---------------------------------------------------------------------------
# Known electrochemical techniques
# ---------------------------------------------------------------------------

KNOWN_TECHNIQUES: frozenset[str] = frozenset(
    {
        "cv",
        "lsv",
        "eis",
        "ocp",
        "hold",
        "galvanostatic",
        "dpv",
        "swv",
        "gcd",
        "cc",
        "stripping",
        "purge",
    }
)

# Keys that are metadata on a step dict, not technique parameters.
_STEP_META_KEYS: frozenset[str] = frozenset(
    {"tag", "extract", "vendor_flags"}
)

# Keys that signal structural elements rather than technique steps.
_STRUCTURAL_KEYS: frozenset[str] = frozenset(
    {"loop", "checkpoint"}
)

# Variable-template pattern, e.g. ``{loop.count}``
_VARIABLE_RE = re.compile(r"^\{[\w.]+\}$")

# ---------------------------------------------------------------------------
# Line-tracking YAML loader
# ---------------------------------------------------------------------------


class _LineLoader(yaml.SafeLoader):  # type: ignore[misc]
    """SafeLoader subclass that annotates every mapping with ``__line__``."""


def _mapping_constructor(loader: _LineLoader, node: MappingNode) -> dict[str, Any]:
    """Construct a dict and inject ``__line__`` from the YAML token."""
    loader.flatten_mapping(node)
    pairs = loader.construct_pairs(node)
    result: dict[str, Any] = {}
    for key, value in pairs:
        result[key] = value
    result["__line__"] = node.start_mark.line + 1  # 1-indexed
    return result


def _sequence_constructor(loader: _LineLoader, node: SequenceNode) -> list[Any]:
    result: list[Any] = loader.construct_sequence(node)
    return result


def _scalar_constructor(loader: _LineLoader, node: ScalarNode) -> Any:
    return loader.construct_scalar(node)


_LineLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping_constructor
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class YAMLParser:
    """Parse ``.ecproc`` YAML files into :class:`ProcedureAST`."""

    def __init__(self) -> None:
        self._source_name: str = "<string>"

    # -- public entry points ------------------------------------------------

    def parse_file(self, path: str | Path) -> ProcedureAST:
        """Parse a ``.ecproc`` file from disk.

        Args:
            path: Filesystem path to the YAML file.

        Returns:
            A fully populated :class:`ProcedureAST`.

        Raises:
            FileNotFoundError: If *path* does not exist.
            ParseError: On malformed YAML or missing structure.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        text = path.read_text(encoding="utf-8")
        self._source_name = str(path)
        ast = self._parse_raw(text)
        ast.source_file = path
        return ast

    def parse_string(self, content: str, source_name: str = "<string>") -> ProcedureAST:
        """Parse YAML content supplied as a string.

        Args:
            content: Raw YAML text.
            source_name: Descriptive name used in error messages.

        Returns:
            A fully populated :class:`ProcedureAST`.
        """
        self._source_name = source_name
        return self._parse_raw(content)

    # -- internal -----------------------------------------------------------

    def _parse_raw(self, text: str) -> ProcedureAST:
        """Deserialize YAML text and build the AST."""
        try:
            doc = yaml.load(text, Loader=_LineLoader)  # noqa: S506
        except yaml.YAMLError as exc:
            raise YAMLStructureError(
                f"YAML parse error: {exc}",
                location=SourceLocation(line=1, file=self._source_name),
            ) from exc

        if not isinstance(doc, dict):
            raise YAMLStructureError(
                "Top-level YAML must be a mapping",
                location=self._loc(doc if isinstance(doc, dict) else {}),
            )

        metadata = self._parse_metadata(doc)
        system = self._parse_system(doc)
        procedure = self._parse_procedure(doc)
        safety = self._parse_safety(doc)
        state_recovery = self._parse_state_recovery(doc)
        output = self._parse_output(doc)

        return ProcedureAST(
            metadata=metadata,
            system=system,
            procedure=procedure,
            safety=safety,
            state_recovery=state_recovery,
            output=output,
        )

    # -- helpers ------------------------------------------------------------

    def _loc(self, d: dict[str, Any]) -> SourceLocation:
        """Build a :class:`SourceLocation` from the ``__line__`` injected by the loader."""
        return SourceLocation(
            line=d.get("__line__", 0),
            file=self._source_name,
        )

    @staticmethod
    def _strip_meta(d: dict[str, Any]) -> dict[str, Any]:
        """Return a shallow copy of *d* without internal bookkeeping keys."""
        return {k: v for k, v in d.items() if k != "__line__"}

    def _require(
        self,
        d: dict[str, Any],
        key: str,
        section: str,
    ) -> Any:
        """Fetch a required key from *d*, raising :class:`MissingFieldError` if absent."""
        if key not in d:
            raise MissingFieldError(key, section, location=self._loc(d))
        return d[key]

    # -----------------------------------------------------------------------
    # Section: metadata
    # -----------------------------------------------------------------------

    def _parse_metadata(self, doc: dict[str, Any]) -> MetadataAST:
        raw = self._require(doc, "metadata", "root")
        if not isinstance(raw, dict):
            raise YAMLStructureError(
                "'metadata' must be a mapping",
                location=self._loc(doc),
            )

        protocol = self._require(raw, "protocol", "metadata")
        version = str(self._require(raw, "version", "metadata"))

        # Collect recognised optional fields.
        known_optional = {
            "author", "electrolyte", "gas",
            "working_electrode", "reference", "notes",
        }
        kwargs: dict[str, Any] = {}
        for k in known_optional:
            if k in raw:
                kwargs[k] = raw[k]

        # Anything left over goes into ``additional``.
        extra_keys = set(raw) - {"protocol", "version", "__line__"} - known_optional
        additional: dict[str, Any] | None = None
        if extra_keys:
            additional = {k: raw[k] for k in extra_keys}

        return MetadataAST(
            protocol=str(protocol),
            version=version,
            additional=additional,
            **kwargs,
        )

    # -----------------------------------------------------------------------
    # Section: system
    # -----------------------------------------------------------------------

    def _parse_system(self, doc: dict[str, Any]) -> SystemAST:
        raw = self._require(doc, "system", "root")
        if not isinstance(raw, dict):
            raise YAMLStructureError(
                "'system' must be a mapping",
                location=self._loc(doc),
            )

        electrodes = int(self._require(raw, "electrodes", "system"))
        reference = str(self._require(raw, "reference", "system"))
        loc = self._loc(raw)

        working = self._parse_working_electrode(raw.get("working"))
        electrolyte = self._parse_electrolyte(raw.get("electrolyte"))
        counter = raw.get("counter")
        if counter is not None:
            counter = str(counter)

        return SystemAST(
            electrodes=electrodes,
            reference=reference,
            working=working,
            electrolyte=electrolyte,
            counter=counter,
            source_location=loc,
        )

    def _parse_working_electrode(
        self, raw: Any
    ) -> WorkingElectrodeAST | None:
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise YAMLStructureError(
                "'system.working' must be a mapping",
                location=SourceLocation(line=0, file=self._source_name),
            )

        material = self._require(raw, "material", "system.working")
        area = raw.get("area_cm2")
        loading = raw.get("loading_ug_cm2")

        known = {"material", "area_cm2", "loading_ug_cm2", "__line__"}
        extra = set(raw) - known
        additional = {k: raw[k] for k in extra} if extra else None

        return WorkingElectrodeAST(
            material=str(material),
            area_cm2=float(area) if area is not None else None,
            loading_ug_cm2=float(loading) if loading is not None else None,
            additional=additional,
        )

    def _parse_electrolyte(
        self, raw: Any
    ) -> str | ElectrolyteAST | None:
        if raw is None:
            return None
        if isinstance(raw, str):
            return raw
        if isinstance(raw, dict):
            solute = self._require(raw, "solute", "system.electrolyte")
            conc = self._require(raw, "concentration_M", "system.electrolyte")
            known = {"solute", "concentration_M", "__line__"}
            extra = set(raw) - known
            additional = {k: raw[k] for k in extra} if extra else None
            return ElectrolyteAST(
                solute=str(solute),
                concentration_M=float(conc),
                additional=additional,
            )
        # Treat anything else as a plain string.
        return str(raw)

    # -----------------------------------------------------------------------
    # Section: procedure (list of phases)
    # -----------------------------------------------------------------------

    def _parse_procedure(self, doc: dict[str, Any]) -> list[PhaseAST]:
        raw = self._require(doc, "procedure", "root")
        if not isinstance(raw, list):
            raise YAMLStructureError(
                "'procedure' must be a sequence of phases",
                location=self._loc(doc),
            )
        if len(raw) == 0:
            raise YAMLStructureError(
                "'procedure' must contain at least one phase",
                location=self._loc(doc),
            )

        phases: list[PhaseAST] = []
        for item in raw:
            phases.append(self._parse_phase(item))
        return phases

    def _parse_phase(self, raw: Any) -> PhaseAST:
        if not isinstance(raw, dict):
            raise YAMLStructureError(
                "Each phase must be a mapping",
                location=SourceLocation(line=0, file=self._source_name),
            )

        name = self._require(raw, "name", "phase")
        loc = self._loc(raw)

        setup = self._parse_phase_block(raw.get("setup"))
        stabilize = raw.get("stabilize")
        if stabilize is not None:
            if isinstance(stabilize, str):
                stabilize = [stabilize]
            elif not isinstance(stabilize, list):
                raise YAMLStructureError(
                    "'stabilize' must be a string or list of strings",
                    location=loc,
                )
        teardown = self._parse_phase_block(raw.get("teardown"))

        steps: list[StepAST | LoopAST] = []
        raw_steps = raw.get("steps", [])
        if not isinstance(raw_steps, list):
            raise YAMLStructureError(
                "'steps' must be a sequence",
                location=loc,
            )
        for item in raw_steps:
            steps.append(self._parse_step_or_loop(item))

        return PhaseAST(
            name=str(name),
            setup=setup,
            stabilize=stabilize,
            steps=steps,
            teardown=teardown,
            source_location=loc,
        )

    @staticmethod
    def _parse_phase_block(raw: Any) -> dict[str, Any] | None:
        """Parse a ``setup`` or ``teardown`` block (simple dict passthrough)."""
        if raw is None:
            return None
        if isinstance(raw, dict):
            return {k: v for k, v in raw.items() if k != "__line__"}
        return {"value": raw}

    # -----------------------------------------------------------------------
    # Steps & loops
    # -----------------------------------------------------------------------

    def _parse_step_or_loop(self, raw: Any) -> StepAST | LoopAST:
        """Decide whether *raw* is a technique step or a loop construct."""
        if not isinstance(raw, dict):
            raise YAMLStructureError(
                "Each step must be a mapping",
                location=SourceLocation(line=0, file=self._source_name),
            )

        if "loop" in raw:
            return self._parse_loop(raw)

        return self._parse_step(raw)

    # -- technique step -----------------------------------------------------

    def _parse_step(self, raw: dict[str, Any]) -> StepAST:
        loc = self._loc(raw)

        # Identify the technique: first key that is a known technique name.
        technique: str | None = None
        for key in raw:
            if key in KNOWN_TECHNIQUES:
                technique = key
                break

        if technique is None:
            # If the dict has a single non-meta key that is not structural,
            # treat it as an unknown technique and report a helpful error.
            candidates = set(raw) - _STEP_META_KEYS - _STRUCTURAL_KEYS - {"__line__"}
            if len(candidates) == 1:
                bad = candidates.pop()
                raise UnknownTechniqueError(bad, location=loc)
            raise YAMLStructureError(
                f"Cannot determine technique from step keys: {sorted(set(raw) - {'__line__'})}",
                location=loc,
            )

        # Build parameters dict from the technique's sub-mapping.
        tech_raw = raw[technique]
        parameters: dict[str, Any] = {}
        if isinstance(tech_raw, dict):
            parameters = self._strip_meta(tech_raw)
        elif tech_raw is not None:
            # Scalar shorthand, e.g. ``ocp: 30 s``
            parameters = {"value": tech_raw}

        # Also collect any top-level keys that are not the technique name,
        # tag, extract, vendor_flags, or internal bookkeeping.  These are
        # parameters that live beside the technique key (flat step form).
        for k, v in raw.items():
            if k in {technique, "__line__"} | _STEP_META_KEYS | _STRUCTURAL_KEYS:
                continue
            # Only add if not already provided in the nested form.
            if k not in parameters:
                parameters[k] = v

        # Extract tag, extract, vendor_flags from step level OR from nested
        # technique params (both forms are valid in .ecproc YAML).
        tag = raw.get("tag") or parameters.pop("tag", None)
        if tag is not None:
            tag = str(tag)

        extract = raw.get("extract") or parameters.pop("extract", None)

        vendor_flags = raw.get("vendor_flags") or parameters.pop("vendor_flags", None)
        if vendor_flags is not None and not isinstance(vendor_flags, dict):
            raise YAMLStructureError(
                "'vendor_flags' must be a mapping of vendor names to parameter dicts",
                location=loc,
            )
        if vendor_flags is not None:
            vendor_flags = {
                k: (self._strip_meta(v) if isinstance(v, dict) else v)
                for k, v in vendor_flags.items()
                if k != "__line__"
            }

        return StepAST(
            technique=technique,
            parameters=parameters,
            tag=tag,
            extract=extract,
            vendor_flags=vendor_flags if vendor_flags else None,
            source_location=loc,
        )

    # -- loop ---------------------------------------------------------------

    def _parse_loop(self, raw: dict[str, Any]) -> LoopAST:
        loc = self._loc(raw)
        loop_raw = raw["loop"]

        if not isinstance(loop_raw, dict):
            raise YAMLStructureError(
                "'loop' value must be a mapping with 'count' and 'steps'",
                location=loc,
            )

        count_raw = self._require(loop_raw, "count", "loop")
        count: int | str
        if isinstance(count_raw, int):
            count = count_raw
        elif isinstance(count_raw, str) and _VARIABLE_RE.match(count_raw):
            count = count_raw  # variable template
        else:
            try:
                count = int(count_raw)
            except (ValueError, TypeError):
                count = str(count_raw)

        raw_steps = self._require(loop_raw, "steps", "loop")
        if not isinstance(raw_steps, list):
            raise YAMLStructureError(
                "'loop.steps' must be a sequence",
                location=loc,
            )

        steps: list[StepAST | LoopAST] = []
        for item in raw_steps:
            steps.append(self._parse_step_or_loop(item))

        stop_if = loop_raw.get("stop_if")
        if stop_if is not None:
            stop_if = str(stop_if)

        # Checkpoint can appear inside the loop dict or as a sibling key.
        checkpoint_raw = loop_raw.get("checkpoint") or raw.get("checkpoint")
        checkpoint = self._parse_checkpoint(checkpoint_raw) if checkpoint_raw else None

        return LoopAST(
            count=count,
            steps=steps,
            checkpoint=checkpoint,
            stop_if=stop_if,
            source_location=loc,
        )

    # -- checkpoint ---------------------------------------------------------

    def _parse_checkpoint(self, raw: Any) -> CheckpointAST:
        if not isinstance(raw, dict):
            raise YAMLStructureError(
                "'checkpoint' must be a mapping",
                location=SourceLocation(line=0, file=self._source_name),
            )

        loc = self._loc(raw)

        # ---- triggers ----
        trigger_raw = raw.get("trigger") or raw.get("triggers")
        triggers: list[TriggerAST] = []
        logic: str = "any"

        if trigger_raw is not None:
            triggers, logic = self._parse_triggers(trigger_raw)
        else:
            # Fall back: look for top-level every_* / when keys.
            inline = self._extract_inline_triggers(raw)
            if inline:
                triggers = inline

        reset = str(raw.get("reset", "independent"))

        # ---- do list ----
        do_raw = raw.get("do", [])
        do_items: list[StepAST | PhaseAST] = []
        if isinstance(do_raw, list):
            for item in do_raw:
                do_items.append(self._parse_checkpoint_action(item))
        elif isinstance(do_raw, dict):
            do_items.append(self._parse_checkpoint_action(do_raw))

        return CheckpointAST(
            triggers=triggers,
            logic=logic,
            reset=reset,
            do=do_items,
            source_location=loc,
        )

    def _parse_triggers(
        self, raw: Any
    ) -> tuple[list[TriggerAST], str]:
        """Parse the ``trigger:`` field of a checkpoint.

        Handles both the wrapper form::

            trigger:
              any:
                - every: 5000 cycles
                - every: 24 h

        and the plain list form::

            trigger:
              - every: 5000 cycles
              - every: 24 h
        """
        logic = "any"
        items: list[Any] = []

        if isinstance(raw, dict):
            clean = self._strip_meta(raw)
            if "any" in clean:
                logic = "any"
                items = clean["any"] if isinstance(clean["any"], list) else [clean["any"]]
            elif "all" in clean:
                logic = "all"
                items = clean["all"] if isinstance(clean["all"], list) else [clean["all"]]
            else:
                # Single trigger as a dict, e.g. ``trigger: {every: 24 h}``
                items = [raw]
        elif isinstance(raw, list):
            items = raw
        else:
            items = [raw]

        triggers: list[TriggerAST] = []
        for item in items:
            triggers.append(self._parse_single_trigger(item))
        return triggers, logic

    def _parse_single_trigger(self, raw: Any) -> TriggerAST:
        """Parse one trigger entry into a :class:`TriggerAST`."""
        loc = SourceLocation(line=0, file=self._source_name)
        if isinstance(raw, dict):
            loc = self._loc(raw)
            clean = self._strip_meta(raw)

            if "every" in clean:
                return self._parse_every_trigger(clean["every"], loc)
            if "when" in clean:
                return TriggerAST(
                    type="when",
                    value=str(clean["when"]),
                    source_location=loc,
                )

            # If the dict has a single key, treat it as a shorthand.
            if len(clean) == 1:
                key, val = next(iter(clean.items()))
                if key.startswith("every"):
                    return self._parse_every_trigger(val, loc)
                return TriggerAST(type=key, value=val, source_location=loc)

        # Plain string trigger, e.g. ``"every 5000 cycles"``
        if isinstance(raw, str):
            return self._parse_trigger_string(raw)

        raise InvalidSyntaxError(
            f"Cannot parse trigger: {raw!r}",
            location=loc,
        )

    def _parse_every_trigger(self, value: Any, loc: SourceLocation) -> TriggerAST:
        """Parse the value side of ``every: <value>``."""
        if isinstance(value, int):
            return TriggerAST(
                type="every_cycles", value=value, unit="cycles", source_location=loc
            )
        if isinstance(value, (float, int)):
            return TriggerAST(
                type="every_cycles", value=int(value), unit="cycles", source_location=loc
            )

        text = str(value).strip()
        # Try "<number> <unit>" form.
        _time_units = r"cycles?|h|hr|hrs|hours?|min|minutes?|s|sec|secs|seconds?"
        m = re.match(
            rf"^(\d+(?:\.\d+)?)\s+({_time_units})$", text, re.IGNORECASE
        )
        if m:
            num_str, unit_str = m.group(1), m.group(2).lower()
            num = float(num_str) if "." in num_str else int(num_str)
            if unit_str.startswith("cycle"):
                return TriggerAST(
                    type="every_cycles", value=num, unit="cycles", source_location=loc
                )
            return TriggerAST(
                type="every_time", value=num, unit=unit_str, source_location=loc
            )

        # Fallback: treat as raw string.
        return TriggerAST(type="every_time", value=text, source_location=loc)

    def _parse_trigger_string(self, text: str) -> TriggerAST:
        """Parse a plain-string trigger like ``'every 5000 cycles'``."""
        text = text.strip()
        m = re.match(r"^every\s+(\d+(?:\.\d+)?)\s+(\S+)$", text, re.IGNORECASE)
        if m:
            num_str, unit_str = m.group(1), m.group(2).lower()
            num = float(num_str) if "." in num_str else int(num_str)
            if unit_str.startswith("cycle"):
                return TriggerAST(type="every_cycles", value=num, unit="cycles")
            return TriggerAST(type="every_time", value=num, unit=unit_str)

        if text.lower().startswith("when "):
            return TriggerAST(type="when", value=text[5:].strip())

        return TriggerAST(type="when", value=text)

    def _extract_inline_triggers(self, d: dict[str, Any]) -> list[TriggerAST]:
        """Extract trigger-like keys directly from a checkpoint dict."""
        triggers: list[TriggerAST] = []
        loc = self._loc(d)
        for key in ("every_cycles", "every_time", "every", "when"):
            if key in d:
                if key == "every":
                    triggers.append(self._parse_every_trigger(d[key], loc))
                elif key == "when":
                    triggers.append(
                        TriggerAST(type="when", value=str(d[key]), source_location=loc)
                    )
                elif key == "every_cycles":
                    triggers.append(
                        TriggerAST(
                            type="every_cycles", value=d[key], unit="cycles", source_location=loc
                        )
                    )
                elif key == "every_time":
                    triggers.append(
                        TriggerAST(type="every_time", value=d[key], source_location=loc)
                    )
        return triggers

    def _parse_checkpoint_action(
        self, raw: Any
    ) -> StepAST | PhaseAST:
        """Parse a single action inside a checkpoint ``do:`` list."""
        if not isinstance(raw, dict):
            raise YAMLStructureError(
                "Checkpoint 'do' items must be mappings",
                location=SourceLocation(line=0, file=self._source_name),
            )
        # If the item has a ``name`` key, treat as an inline phase.
        if "name" in raw:
            return self._parse_phase(raw)
        return self._parse_step(raw)

    # -----------------------------------------------------------------------
    # Section: safety
    # -----------------------------------------------------------------------

    def _parse_safety(self, doc: dict[str, Any]) -> SafetyAST | None:
        raw = doc.get("safety")
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise YAMLStructureError(
                "'safety' must be a mapping",
                location=self._loc(doc),
            )

        loc = self._loc(raw)
        max_current = raw.get("max_current")
        if max_current is not None:
            max_current = str(max_current)

        voltage_window = raw.get("voltage_window")
        if voltage_window is not None and not isinstance(voltage_window, list):
            voltage_window = [str(voltage_window)]
        elif isinstance(voltage_window, list):
            voltage_window = [str(v) for v in voltage_window]

        temperature_limits = raw.get("temperature_limits")
        if temperature_limits is not None and not isinstance(temperature_limits, list):
            temperature_limits = [str(temperature_limits)]
        elif isinstance(temperature_limits, list):
            temperature_limits = [str(t) for t in temperature_limits]

        stop_if = raw.get("stop_if")
        if stop_if is not None:
            if isinstance(stop_if, str):
                stop_if = [stop_if]
            elif isinstance(stop_if, list):
                stop_if = [str(s) for s in stop_if]

        thermal_runaway = self._parse_thermal_runaway(raw.get("thermal_runaway"))
        ref_monitor = self._parse_reference_monitor(raw.get("reference_electrode_monitor"))

        return SafetyAST(
            max_current=max_current,
            voltage_window=voltage_window,
            temperature_limits=temperature_limits,
            stop_if=stop_if,
            thermal_runaway=thermal_runaway,
            reference_electrode_monitor=ref_monitor,
            source_location=loc,
        )

    def _parse_thermal_runaway(self, raw: Any) -> ThermalRunawayAST | None:
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise YAMLStructureError(
                "'thermal_runaway' must be a mapping",
                location=SourceLocation(line=0, file=self._source_name),
            )
        max_dT_dt = self._require(raw, "max_dT_dt", "safety.thermal_runaway")
        action = self._require(raw, "action", "safety.thermal_runaway")
        return ThermalRunawayAST(max_dT_dt=float(max_dT_dt), action=str(action))

    def _parse_reference_monitor(self, raw: Any) -> ReferenceMonitorAST | None:
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise YAMLStructureError(
                "'reference_electrode_monitor' must be a mapping",
                location=SourceLocation(line=0, file=self._source_name),
            )
        max_Ru_change = raw.get("max_Ru_change")
        if max_Ru_change is not None:
            max_Ru_change = str(max_Ru_change)
        max_ocp_drift = raw.get("max_ocp_drift")
        if max_ocp_drift is not None:
            max_ocp_drift = str(max_ocp_drift)
        action = str(raw.get("action", "cell_off"))
        return ReferenceMonitorAST(
            max_Ru_change=max_Ru_change,
            max_ocp_drift=max_ocp_drift,
            action=action,
        )

    # -----------------------------------------------------------------------
    # Section: state_recovery
    # -----------------------------------------------------------------------

    def _parse_state_recovery(self, doc: dict[str, Any]) -> StateRecoveryAST | None:
        raw = doc.get("state_recovery")
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise YAMLStructureError(
                "'state_recovery' must be a mapping",
                location=self._loc(doc),
            )

        after_pause = self._parse_recovery_steps(raw.get("after_pause"))
        after_checkpoint = self._parse_recovery_steps(raw.get("after_checkpoint"))
        after_error = self._parse_recovery_steps_or_strings(raw.get("after_error"))

        return StateRecoveryAST(
            after_pause=after_pause,
            after_checkpoint=after_checkpoint,
            after_error=after_error,
        )

    def _parse_recovery_steps(self, raw: Any) -> list[StepAST] | None:
        if raw is None:
            return None
        if not isinstance(raw, list):
            raw = [raw]
        return [self._parse_step(item) for item in raw if isinstance(item, dict)]

    def _parse_recovery_steps_or_strings(
        self, raw: Any
    ) -> list[StepAST | str] | None:
        if raw is None:
            return None
        if not isinstance(raw, list):
            raw = [raw]
        result: list[StepAST | str] = []
        for item in raw:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                result.append(self._parse_step(item))
            else:
                result.append(str(item))
        return result

    # -----------------------------------------------------------------------
    # Section: output
    # -----------------------------------------------------------------------

    def _parse_output(self, doc: dict[str, Any]) -> OutputAST | None:
        raw = doc.get("output")
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise YAMLStructureError(
                "'output' must be a mapping",
                location=self._loc(doc),
            )

        ecdl_raw = raw.get("ecdl")
        ecdl: dict[str, Any] | None = None
        if ecdl_raw is not None:
            if isinstance(ecdl_raw, dict):
                ecdl = self._strip_meta(ecdl_raw)
            else:
                ecdl = {"value": ecdl_raw}

        return OutputAST(ecdl=ecdl)
