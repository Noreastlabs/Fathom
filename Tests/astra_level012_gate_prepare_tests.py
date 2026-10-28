#!/usr/bin/env python3
"""Focused immutable preparation/refusal checks; no production admission."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gate", ROOT / "Tools/astra_level012_gate_prepare.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
WORK = ROOT / "Build/astra-admission-gate"


class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = gate.derive()
        cls.package, cls.registry, cls.profile = [gate.parse((ROOT / gate.CASE / (s + ".json")).read_bytes())
                                                for s in ("package", "identity-registry", "expected-profile")]
        cls.old, cls.old_registry = [gate.parse((ROOT / gate.BASE / (s + ".json")).read_bytes())
                                     for s in ("package", "identity-registry")]

    def check_case(self, p=None, r=None, f=None):
        gate.verify_case(p or self.package, r or self.registry, f or self.profile, self.old, self.old_registry)

    def test_01_all_frozen_and_original13_bytes_preserved(self):
        for path, digest in gate.PINS.items():
            self.assertEqual(gate.sha(self.files["closure/" + path]), digest)
        base = gate.parse(self.files["original13/manifest.json"])
        for entry in base["files"]:
            self.assertEqual(gate.sha(self.files["original13/" + entry["path"]]), entry["sha256"])
        self.check_case()

    def test_02_deterministic_complete_bytes(self):
        self.assertEqual(self.files, gate.derive())
        inv = gate.parse(self.files["inventory.json"])
        self.assertEqual(len(inv["files"]), len(self.files) - 1)
        for entry in inv["files"]:
            self.assertEqual(gate.sha(self.files[entry["path"]]), entry["sha256"])

    def test_03_no_authority_created(self):
        decision = gate.parse(self.files["decision-needed.json"])
        with self.assertRaisesRegex(ValueError, "PENDING_OR_REJECTED"):
            gate.validate_decision(decision)
        self.assertFalse(gate.parse(self.files["integration-plan.json"])["installable"])
        self.assertFalse(self.package["records"][0]["runtime_eligible"])

    def test_04_hypothetical_decision_refusals_not_human_acceptance(self):
        # Memory-only structural fixture; never saved as an actual decision.
        hypothetical = gate.pending_decision()
        hypothetical.update(status="ACCEPTED", authority_name="SYNTHETIC TEST ONLY",
                            recorded_utc="2026-09-23T00:00:00Z", owner_response_evidence="TEST ONLY",
                            notes_fingerings_picking_timing_accepted=True,
                            stable_identities_accepted=True, single_cell_runtime_eligible=True)
        gate.validate_decision(hypothetical)
        mutations = [("status", "Rejected"), ("package_sha256", "0" * 64),
                     ("profile_sha256", "0" * 64), ("registry_sha256", "0" * 64),
                     ("authority_name", None), ("recorded_utc", ""), ("owner_response_evidence", None),
                     ("notes_fingerings_picking_timing_accepted", False),
                     ("stable_identities_accepted", False), ("single_cell_runtime_eligible", False)]
        for key, value in mutations:
            with self.subTest(key=key):
                bad = copy.deepcopy(hypothetical); bad[key] = value
                with self.assertRaises(ValueError): gate.validate_decision(bad)
        for key in ("whole_ladder", "mastery", "automatic_credit", "optional_inter_cell_pause"):
            bad = copy.deepcopy(hypothetical); bad["scope"][key] = True
            with self.assertRaisesRegex(ValueError, "DECISION_BINDING"): gate.validate_decision(bad)
        isolated = gate.pending_decision(); isolated["scope"]["whole_ladder"] = True
        self.assertFalse(gate.pending_decision()["scope"]["whole_ladder"])
        bad = copy.deepcopy(hypothetical); bad["scope"]["content_revision"] = True
        with self.assertRaisesRegex(ValueError, "DECISION_BINDING"): gate.validate_decision(bad)
        bad = copy.deepcopy(hypothetical); bad["extra_runtime_permission"] = True
        with self.assertRaisesRegex(ValueError, "DECISION_FIELDS"): gate.validate_decision(bad)

    def test_05_identity_duplicate_and_collision_refusal(self):
        for entity in (self.registry["entities"][-1], self.old_registry["entities"][-1]):
            registry = copy.deepcopy(self.registry); registry["entities"].append(entity)
            profile = copy.deepcopy(self.profile); profile["reference_registry"] = registry
            with self.assertRaisesRegex(ValueError, "DUPLICATE_ENTITY|IDENTITY_COLLISION"):
                self.check_case(r=registry, f=profile)

    def test_06_no_changed_music_or_eligibility(self):
        for name in ("timing", "eligibility", "event", "pause"):
            p, f = copy.deepcopy(self.package), copy.deepcopy(self.profile)
            r = p["records"][0]
            if name == "timing": r["events"][0]["duration_q"] = [1, 4]
            if name == "eligibility": r["runtime_eligible"] = True
            if name == "event": r["events"][1]["event_id"] = r["events"][0]["event_id"]
            if name == "pause": r["variants"][0]["tail_pause"] = [1, 1]
            f["reference_package"] = p
            with self.subTest(name=name), self.assertRaises(ValueError): self.check_case(p=p, f=f)

    def test_07_strict_duplicates_nonfinite_and_traversal_refused(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.assertRaises(ValueError): gate.parse(raw)
        for path in ("../outside", "/tmp/outside", "a/../outside", "a/./outside", "a\\outside"):
            with self.assertRaises(ValueError): gate.source_file(ROOT, path)

    def test_08_hash_and_immutable_output_refusal(self):
        with self.assertRaisesRegex(ValueError, "HASH_DRIFT"):
            gate.pinned(ROOT, gate.CASE + "/package.json", "0" * 64)
        with tempfile.TemporaryDirectory(dir=WORK, prefix="output-test-") as temp:
            out = Path(temp) / "new"
            gate.write_new(out, {"input": b"frozen"})
            with self.assertRaisesRegex(ValueError, "OUTPUT_EXISTS"): gate.write_new(out, {"input": b"changed"})
            self.assertEqual((out / "input").read_bytes(), b"frozen")


if __name__ == "__main__":
    WORK.mkdir(parents=True, exist_ok=True)
    unittest.main(verbosity=2)
