"""Focused source, identity and frozen-native refusals for one new Level12 cell."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel02_level012_rung02_vertical as pilot


class Rung02PilotTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = pilot.derive()
        cls.build = ROOT / pilot.OUT

    def test_deterministic_source_identity_and_native_reference(self):
        for name in pilot.NAMES:
            self.assertEqual((self.build / name).read_bytes(), pilot.encode(self.output[name]))
        record = self.output["package.json"]["records"][0]
        self.assertEqual((record["id"], record["workbook_id"], record["lineage"]),
                         ("fg:item:001141", "fg:workbook:000012", {"kind": "new"}))
        self.assertEqual(len(record["events"]), 16)
        self.assertEqual([e["onset_q"] for e in record["events"]],
                         [[i, 2] if i % 2 else [i // 2, 1] for i in range(16)])
        self.assertTrue(all(e["duration_q"] == [1, 2] for e in record["events"]))
        self.assertEqual([v["pick_start"] for v in record["variants"]], ["D", "U"])
        self.assertTrue(all(v["pick_start_origin"] == "source_authored" for v in record["variants"]))
        self.assertTrue(all(v["tail_pause"] is None for v in record["variants"]))
        self.assertFalse(record["runtime_eligible"])
        report = json.loads((self.build / "native-report.json").read_text())
        self.assertEqual((report["exit_code"], report["valid_reference"],
                          report["curriculum_playback_authorized"]), (2, True, False))
        self.assertEqual(report["coverage"]["observed_records"], 1)
        self.assertEqual(report["package_sha256"], hashlib.sha256((self.build / "package.json").read_bytes()).hexdigest())

    def test_old_thirteen_and_source_projection_remain_exact(self):
        old = ROOT / "Content/controls/representative-v1/package.json"
        self.assertEqual(hashlib.sha256(old.read_bytes()).hexdigest(),
                         "0ecd2b1466a7b16e10ca6221299b3b1b21c197ff13cd5df9f038e307673aea8b")
        self.assertEqual(len(json.loads(old.read_text())["records"]), 13)
        self.assertEqual(self.output["summary.json"]["foundation_sha256"],
                         "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255")
        self.assertEqual(self.output["summary.json"]["source_local_key"], "L12-rung02")

    def test_source_field_and_reserved_identity_drift_refused(self):
        altered = copy.deepcopy(pilot.read(ROOT, pilot.PROPOSAL)["records"][1]["schema1_fields"])
        altered["events"][0]["fret"] += 1
        with self.assertRaisesRegex(pilot.PilotError, "CANDIDATE_SOURCE_DRIFT"):
            pilot.derive(override=altered)
        registry = pilot.read(ROOT, pilot.BASE / "identity-registry.json")
        expanded = copy.deepcopy(registry)
        expanded["entities"].append({"id": "fg:item:001141", "kind": "item", "parent": "fg:module:000003", "label": "collision"})
        self.assertEqual(pilot.allocation_floor([expanded], "item", expanded), 1142)

    def test_source_specific_timing_refuses_changed_onset(self):
        altered = copy.deepcopy(self.output["package.json"]["records"][0])
        altered["events"][1]["onset_q"] = [1, 1]
        with self.assertRaisesRegex(pilot.PilotError, "TIMING_SCOPE"):
            pilot.check_connected_eighths(altered)

    def test_level13_sealed_reservation_is_excluded(self):
        level13 = pilot.read(ROOT, pilot.LEVEL13 / "identity-registry.json")
        mine = self.output["identity-registry.json"]
        old = {e["id"] for e in level13["entities"]}
        new = {e["id"] for e in mine["entities"] if e["kind"] in ("item", "module", "variant")}
        self.assertFalse(old & new)
        self.assertEqual(self.output["summary.json"]["allocation_floors"],
                         {"item": 1141, "module": 1141, "variant": 7404})
        self.assertEqual(self.output["summary.json"]["level013_registry_sha256"],
                         pilot.LEVEL13_REGISTRY_SHA)

    def test_frozen_native_refuses_runtime_flag_without_authority(self):
        exe = ROOT / "Build/parallel-13/four-shard-source-bundle-r01/bundle/bin/fathom_content_validate"
        package = copy.deepcopy(self.output["package.json"])
        profile = copy.deepcopy(self.output["expected-profile.json"])
        package["records"][0]["runtime_eligible"] = True
        profile["reference_package"] = package
        with tempfile.TemporaryDirectory(dir=self.build) as temp:
            directory = Path(temp)
            for name, value in (("package.json", package),
                                ("identity-registry.json", self.output["identity-registry.json"]),
                                ("expected-profile.json", profile)):
                (directory / name).write_bytes(pilot.encode(value))
            profile_hash = hashlib.sha256((directory / "expected-profile.json").read_bytes()).hexdigest()
            command = [str(exe), "--package", str(directory / "package.json"),
                       "--registry", str(directory / "identity-registry.json"),
                       "--profile", str(directory / "expected-profile.json"),
                       "--profile-sha256", profile_hash, "--source-root", str(ROOT),
                       "--report", str(directory / "report.json")]
            run = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
            report = json.loads((directory / "report.json").read_text())
            self.assertIn("RUNTIME_NOT_ADMITTED", {issue["code"] for issue in report["issues"]})


if __name__ == "__main__":
    unittest.main()
