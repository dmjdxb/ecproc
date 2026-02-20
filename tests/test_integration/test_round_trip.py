"""Integration tests: round-trip serialization and hash consistency."""

from __future__ import annotations

import json

from ecproc.ir.generator import generate_ir
from ecproc.ir.hash import compute_ir_hash
from ecproc.ir.schema import FaradayIR
from ecproc.ir.serializer import from_json, to_json
from ecproc.parser.yaml_parser import YAMLParser
from ecproc.sdk.procedure import Procedure

# ---------------------------------------------------------------------------
# YAML source for testing
# ---------------------------------------------------------------------------

ROUNDTRIP_YAML = """\
metadata:
  protocol: "Round Trip Test"
  version: "1.0"
  author: "Test Suite"

system:
  electrodes: 3
  reference: RHE
  electrolyte:
    solute: HClO4
    concentration_M: 0.1
  working:
    material: GC
    area_cm2: 0.196
    loading_ug_cm2: 20

procedure:
  - name: Conditioning
    setup:
      gas: N2
    steps:
      - cv:
          vertex1: 0.05
          vertex2: 1.2
          rate: 50
          cycles: 50
  - name: Measurement
    steps:
      - eis:
          f_start: 100000
          f_end: 0.1
          amplitude: 10
          at: OCP
          ppd: 10
          tag: eis_measurement
"""


# ---------------------------------------------------------------------------
# YAML -> IR -> JSON -> IR -> compare
# ---------------------------------------------------------------------------


class TestYAMLRoundTrip:
    """Test YAML parse -> IR -> JSON serialize -> JSON deserialize -> compare."""

    def test_yaml_parse_to_ir_to_json_to_ir(self):
        parser = YAMLParser()
        ast = parser.parse_string(ROUNDTRIP_YAML, source_name="test")
        ir_original = generate_ir(ast)

        # Serialize to JSON
        json_str = to_json(ir_original)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

        # Deserialize back
        ir_restored = from_json(json_str)
        assert isinstance(ir_restored, FaradayIR)

        # Compare key fields
        assert ir_restored.metadata.protocol == ir_original.metadata.protocol
        assert ir_restored.metadata.version == ir_original.metadata.version
        assert ir_restored.system.electrodes == ir_original.system.electrodes
        assert ir_restored.system.reference == ir_original.system.reference
        assert len(ir_restored.procedure) == len(ir_original.procedure)

    def test_yaml_round_trip_preserves_phase_names(self):
        parser = YAMLParser()
        ast = parser.parse_string(ROUNDTRIP_YAML, source_name="test")
        ir_original = generate_ir(ast)
        json_str = to_json(ir_original)
        ir_restored = from_json(json_str)

        original_names = [p.name for p in ir_original.procedure]
        restored_names = [p.name for p in ir_restored.procedure]
        assert original_names == restored_names

    def test_yaml_round_trip_preserves_step_techniques(self):
        parser = YAMLParser()
        ast = parser.parse_string(ROUNDTRIP_YAML, source_name="test")
        ir_original = generate_ir(ast)
        json_str = to_json(ir_original)
        ir_restored = from_json(json_str)

        for orig_phase, rest_phase in zip(ir_original.procedure, ir_restored.procedure):
            assert len(orig_phase.steps) == len(rest_phase.steps)
            for orig_step, rest_step in zip(orig_phase.steps, rest_phase.steps):
                assert orig_step.technique == rest_step.technique


# ---------------------------------------------------------------------------
# SDK -> IR -> JSON -> IR -> compare
# ---------------------------------------------------------------------------


class TestSDKRoundTrip:
    """Test SDK build -> AST -> IR -> JSON -> IR -> compare."""

    def _build_procedure(self) -> Procedure:
        proc = Procedure("SDK Round Trip", version="2.0", author="Test")
        proc.system(
            electrodes=3,
            reference="RHE",
            electrolyte=("H2SO4", 0.5),
            working={"material": "Pt", "area_cm2": 0.07},
        )
        proc.safety(max_current="200 mA", voltage_window=["-0.2 V", "1.8 V"])

        with proc.phase("OCP Stabilization") as p:
            p.ocp(stable="1 mV/s", timeout="5 min")
        with proc.phase("Electrochemistry") as p:
            p.cv(vertex1=0.05, vertex2=1.2, rate=50, cycles=3, tag="baseline_cv")
            p.eis(f_start=100000, f_end=0.1, amplitude=10, tag="baseline_eis")

        return proc

    def test_sdk_to_ir_to_json_to_ir(self):
        proc = self._build_procedure()
        ast = proc.to_ast()
        ir_original = generate_ir(ast)
        json_str = to_json(ir_original)
        ir_restored = from_json(json_str)

        assert ir_restored.metadata.protocol == "SDK Round Trip"
        assert ir_restored.metadata.version == "2.0"
        assert len(ir_restored.procedure) == 2

    def test_sdk_round_trip_preserves_system(self):
        proc = self._build_procedure()
        ast = proc.to_ast()
        ir_original = generate_ir(ast)
        json_str = to_json(ir_original)
        ir_restored = from_json(json_str)

        assert ir_restored.system.electrodes == 3
        assert ir_restored.system.reference == "RHE"

    def test_sdk_round_trip_preserves_safety(self):
        proc = self._build_procedure()
        ast = proc.to_ast()
        ir_original = generate_ir(ast)
        json_str = to_json(ir_original)
        ir_restored = from_json(json_str)

        assert ir_restored.safety is not None
        assert ir_restored.safety.max_current_A is not None


# ---------------------------------------------------------------------------
# Hash consistency
# ---------------------------------------------------------------------------


class TestHashConsistency:
    """Test that hash remains consistent across round trips."""

    def test_ir_hash_deterministic(self):
        parser = YAMLParser()
        ast = parser.parse_string(ROUNDTRIP_YAML, source_name="test")
        ir = generate_ir(ast)

        data = json.loads(to_json(ir))
        hash1 = compute_ir_hash(data)
        hash2 = compute_ir_hash(data)
        assert hash1 == hash2

    def test_ir_hash_starts_with_sha256(self):
        parser = YAMLParser()
        ast = parser.parse_string(ROUNDTRIP_YAML, source_name="test")
        ir = generate_ir(ast)
        data = json.loads(to_json(ir))
        h = compute_ir_hash(data)
        assert h.startswith("sha256:")

    def test_ir_hash_consistent_after_round_trip(self):
        parser = YAMLParser()
        ast = parser.parse_string(ROUNDTRIP_YAML, source_name="test")
        ir_original = generate_ir(ast)

        # Serialize and deserialize
        json_str = to_json(ir_original)
        ir_restored = from_json(json_str)

        # Compute hashes on both
        data_original = json.loads(to_json(ir_original))
        data_restored = json.loads(to_json(ir_restored))

        hash_original = compute_ir_hash(data_original)
        hash_restored = compute_ir_hash(data_restored)

        # The hashes should match because the IR content (excluding timestamps)
        # should be identical
        assert hash_original == hash_restored

    def test_different_procedures_produce_different_hashes(self):
        parser = YAMLParser()
        ast1 = parser.parse_string(ROUNDTRIP_YAML, source_name="test")
        ir1 = generate_ir(ast1)

        different_yaml = ROUNDTRIP_YAML.replace("Round Trip Test", "Different Protocol")
        ast2 = parser.parse_string(different_yaml, source_name="test2")
        ir2 = generate_ir(ast2)

        data1 = json.loads(to_json(ir1))
        data2 = json.loads(to_json(ir2))

        hash1 = compute_ir_hash(data1)
        hash2 = compute_ir_hash(data2)
        assert hash1 != hash2
