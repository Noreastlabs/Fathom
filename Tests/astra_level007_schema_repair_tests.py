#!/usr/bin/env python3
"""Focused preservation/refusal tests; small native fixtures only, no full reruns."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("repair", ROOT / "Tools/astra_level007_schema_repair.py")
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)
SCRATCH = ROOT / "Build/astra-level007-schema/focused"
BINARY = ROOT / "Build/astral6-json-limit/native/fathom_content_validate"
BINARY_SHA = "e94c864507d8118aaf4a68310a8b7e0e47d0ff7ae46937c022f89fbc50055111"


class RepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        SCRATCH.mkdir(parents=True, exist_ok=False)
        cls.inputs = repair.load_inputs()
        cls.output = repair.derive(cls.inputs)

    def test_predecessor_and_complete_entity_preservation(self):
        before = self.inputs[repair.BASE / "package.json"]
        package = self.output["package.json"]
        self.assertEqual(repair.encoded(package["records"][:659]),
                         repair.encoded(self.inputs[repair.PRE / "package.json"]["records"]))
        self.assertEqual(self.output["identity-registry.json"], self.inputs[repair.BASE / "identity-registry.json"])
        self.assertEqual(self.output["identity-registry.json"]["entities"][:6336],
                         self.inputs[repair.PRE / "identity-registry.json"]["entities"])
        self.assertEqual([r["id"] for r in before["records"]], [r["id"] for r in package["records"]])
        self.assertEqual(package["sources"], before["sources"])
        self.assertEqual(package["workbook_catalog"], before["workbook_catalog"])

    def test_only_identity_representation_changes_in_new_records(self):
        for original, changed in zip(self.inputs[repair.BASE / "package.json"]["records"][659:],
                                     self.output["package.json"]["records"][659:]):
            restored = deepcopy(changed)
            note = restored["normalization"].pop()
            key = original["context"]["source_local_key"]
            self.assertEqual(note["kind"], "representation_metadata")
            self.assertEqual(note["text"], "Source-local identity: " + key)
            restored["context"]["source_local_key"] = key
            self.assertEqual(repair.encoded(restored), repair.encoded(original))
            self.assertNotIn("capo", changed["context"])
            self.assertEqual(changed["context"]["tuning_open_midi"], [40, 45, 50, 55, 59, 64])
            self.assertFalse(changed["runtime_eligible"])
            self.assertEqual(changed["timing"]["status"], "unresolved")
            self.assertTrue(all(e["onset_q"] is None and e["duration_q"] is None for e in changed["events"]))

    def test_complete_sidecar_and_identity_event_coverage(self):
        package = self.output["package.json"]
        records = package["records"][659:]
        rows = self.output["source-identity-map.json"]["records"]
        self.assertEqual(len(rows), 108)
        self.assertEqual({r["item_id"] for r in rows}, {f"fg:item:{n:06d}" for n in range(696, 804)})
        self.assertEqual({r["source_local_key"] for r in rows},
                         {f"L7-set{i // 12 + 1:02d}-ex{i + 1:03d}" for i in range(108)})
        variants = [v["id"] for r in records for v in r["variants"]]
        self.assertEqual(len(variants), 216)
        self.assertEqual(set(variants), {f"fg:variant:{n:06d}" for n in range(5434, 5650)})
        events = [e["event_id"] for r in records for e in r["events"]]
        self.assertEqual(len(events), 1728)
        self.assertEqual(len(set(events)), 1728)
        for row, old_row, record in zip(rows, self.inputs[repair.BASE / "transaction.json"]["source_map"], records):
            self.assertEqual({k: row[k] for k in old_row}, old_row)
            self.assertEqual(row["record_canonical_sha256"], repair.sha(repair.encoded(record)[:-1]))
            self.assertEqual(set(row["occurrences"].values()), {e["event_id"] for e in record["events"]})
            self.assertEqual(set(row["variants"].values()), {v["id"] for v in record["variants"]})
            self.assertIn(row["txt"], record["source_refs"])
            self.assertIn(row["pdf"], record["source_refs"])
        self.assertEqual(self.output["candidate-allocation.json"], self.inputs[repair.BASE / "candidate-allocation.json"])
        self.assertEqual(self.output["expected-profile.json"]["event_sources"],
                         self.inputs[repair.BASE / "expected-profile.json"]["event_sources"])

    def test_profile_allocation_and_generation_hash_binding(self):
        profile = self.output["expected-profile.json"]
        self.assertEqual(profile["reference_package"], {k: v for k, v in self.output["package.json"].items()
                                                       if k != "workbook_catalog"})
        self.assertEqual(profile["reference_registry"], self.inputs[repair.BASE / "expected-profile.json"]["reference_registry"])
        for name in ("candidate-allocation.json", "source-identity-map.json"):
            matches = [r for r in profile["authority_artifacts"] if r["path"] == str(repair.OUT / name)]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["sha256"], repair.sha(repair.encoded(self.output[name])))
        for name, digest in self.output["generation.json"]["identities"].items():
            self.assertEqual(digest, repair.sha(repair.encoded(self.output[name])))
        self.assertEqual(self.output["generation.json"]["bundle_status"],
                         self.inputs[repair.BASE / "generation.json"]["bundle_status"])

    def test_deterministic_bytes(self):
        again = repair.derive(self.inputs)
        identities = {}
        for name, first in self.output.items():
            raw = repair.encoded(first)
            self.assertEqual(raw, repair.encoded(again[name]))
            identities[name] = {"bytes": len(raw), "sha256": repair.sha(raw)}
        (SCRATCH / "deterministic-identities.json").write_text(json.dumps(identities, indent=2) + "\n")

    def test_pin_drift_refuses_before_derivation(self):
        mirror = SCRATCH / "drift-root"
        first = next(iter(repair.PINS))
        (mirror / first).parent.mkdir(parents=True)
        (mirror / first).write_bytes(b"{}\n")
        with self.assertRaisesRegex(repair.RepairError, "PIN_DRIFT"):
            repair.load_inputs(mirror)

    def test_duplicate_decoded_json_key_refused(self):
        with self.assertRaisesRegex(repair.RepairError, "DUPLICATE_KEY"):
            repair.strict_load(b'{"x":1,"\\u0078":2}')

    def test_duplicate_source_local_key_refused(self):
        rows = deepcopy(self.inputs[repair.BASE / "transaction.json"]["source_map"])
        rows[1]["source_local_key"] = rows[0]["source_local_key"]
        with self.assertRaisesRegex(repair.RepairError, "DUPLICATE_SOURCE_LOCAL_KEY"):
            repair.check_source_map(self.inputs[repair.BASE / "package.json"]["records"][659:], rows,
                                    self.inputs[repair.BASE / "transaction.json"]["records"],
                                    self.inputs[repair.SOURCE]["records"])

    def test_record_entity_variant_event_collisions_refused(self):
        package = self.inputs[repair.BASE / "package.json"]
        registry = self.inputs[repair.BASE / "identity-registry.json"]
        for obj, key, collision, code in [
            (package["records"][659], "id", package["records"][0]["id"], "DUPLICATE_RECORD"),
            (registry["entities"][6336], "id", registry["entities"][0]["id"], "DUPLICATE_ENTITY"),
            (package["records"][659]["events"][1], "event_id", package["records"][659]["events"][0]["event_id"], "DUPLICATE_EVENT"),
            (package["records"][659]["variants"][1], "id", package["records"][659]["variants"][0]["id"], "DUPLICATE_VARIANT"),
        ]:
            previous = obj[key]
            try:
                obj[key] = collision
                with self.subTest(code=code), self.assertRaisesRegex(repair.RepairError, code):
                    repair.check_baseline(self.inputs)
            finally:
                obj[key] = previous

    def test_native_metadata_authority_and_unknown_field_refusal(self):
        self.assertEqual(repair.sha(BINARY.read_bytes()), BINARY_SHA)
        fixture = ROOT / "Tests/fixtures/canonical_controls"
        for mode, expected_code in (("positive", None), ("unauthorized", "UNKNOWN_FIELD"), ("sidecar-drift", "SOURCE_HASH")):
            case = SCRATCH / ("native-" + mode)
            case.mkdir()
            package = repair.strict_load((fixture / "examples.json").read_bytes())
            profile = repair.strict_load((fixture / "expected-profile.json").read_bytes())
            sidecar = case / "source-identity-map.json"
            sidecar.write_bytes(b'{"synthetic_test_only":true}\n')
            package["records"][0]["normalization"].append({"kind": "representation_metadata",
                "basis": str(sidecar.relative_to(ROOT)), "text": "Synthetic source identity representation test"})
            if mode == "unauthorized":
                package["records"][0]["context"]["source_local_key"] = "synthetic-test-key"
            profile["reference_package"] = package
            profile["authority_artifacts"].append({"path": str(sidecar.relative_to(ROOT)),
                "role": "source_identity_allocation", "sha256": repair.sha(sidecar.read_bytes())})
            if mode == "sidecar-drift":
                sidecar.write_bytes(b'{"synthetic_test_only":false}\n')
            for name, raw in (("package", repair.encoded(package)), ("profile", repair.encoded(profile)),
                              ("registry", (fixture / "identity-registry.json").read_bytes())):
                (case / (name + ".json")).write_bytes(raw)
            command = [str(BINARY), "--package", str(case / "package.json"), "--registry", str(case / "registry.json"),
                "--profile", str(case / "profile.json"), "--profile-sha256", repair.sha((case / "profile.json").read_bytes()),
                "--source-root", str(ROOT), "--report", str(case / "report.json")]
            process = subprocess.run(command, capture_output=True, text=True)
            (case / "execution.json").write_text(json.dumps({"command": command, "exit_code": process.returncode,
                                                            "stdout": process.stdout, "stderr": process.stderr}, indent=2) + "\n")
            report = json.loads((case / "report.json").read_text())
            self.assertFalse(report["curriculum_playback_authorized"])
            self.assertEqual(process.returncode, 1 if expected_code else 2)
            if expected_code:
                self.assertFalse(report["valid_reference"])
                self.assertIn(expected_code, {i["code"] for i in report["issues"]})
            else:
                self.assertTrue(report["valid_reference"])
                self.assertEqual(len(report["records"]), 13)


if __name__ == "__main__":
    unittest.main(verbosity=2)
