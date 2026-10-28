"""Source, identity, timing, and native refusals for the isolated Rung04 cell."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel03_level012_rung04_candidate as candidate


class Rung04CandidateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = candidate.derive()
        cls.build = ROOT / candidate.OUT

    def test_deterministic_package_and_source_events(self):
        for name in candidate.NAMES:
            self.assertEqual((self.build / name).read_bytes(), candidate.encode(self.output[name]))
        record = self.output["package.json"]["records"][0]
        self.assertEqual((record["id"], record["module_id"], record["workbook_id"],
                          record["content_revision"], record["lineage"]),
                         ("fg:item:001143", "fg:module:001143", "fg:workbook:000012", 1, {"kind": "new"}))
        self.assertEqual([v["id"] for v in record["variants"]],
                         ["fg:variant:007408", "fg:variant:007409"])
        self.assertFalse(record["runtime_eligible"])
        self.assertEqual(len(record["events"]), 16)
        self.assertEqual([e["onset_q"] for e in record["events"]],
                         [[i, 2] if i % 2 else [i // 2, 1] for i in range(16)])
        self.assertTrue(all(e["duration_q"] == [1, 2] for e in record["events"]))
        self.assertEqual([v["pick_start"] for v in record["variants"]], ["D", "U"])
        self.assertTrue(all(v["pick_start_origin"] == "source_authored" and
                            v["tail_pause"] is None and len(v["event_ids"]) == 16
                            for v in record["variants"]))
        self.assertEqual(set(self.output["expected-profile.json"]["event_sources"].values()),
                         {"L12-TXT1-84-95"})
        candidate.check_source_cell(self.output["package.json"]["sources"], record,
                                    "L12-TXT1-84-95", "L12-PDF1-p3")

    def test_native_valid_reference_withheld_playback(self):
        report = json.loads((self.build / "native-report.json").read_text())
        self.assertEqual((report["exit_code"], report["valid_reference"],
                          report["curriculum_playback_authorized"]), (2, True, False))
        self.assertEqual(report["coverage"]["observed_records"], 1)
        self.assertEqual(report["coverage"]["events"], 16)
        self.assertEqual(report["coverage"]["variants"], 2)
        self.assertEqual(report["package_sha256"],
                         hashlib.sha256((self.build / "package.json").read_bytes()).hexdigest())
        self.assertIn("MODEL_not_admitted", {issue["code"] for issue in report["issues"]})

    def test_source_and_timing_mutations_refused(self):
        projected = copy.deepcopy(candidate.read(ROOT, candidate.PROPOSAL)["records"][3]["schema1_fields"])
        projected["events"][0]["fret"] += 1
        with self.assertRaisesRegex(candidate.PilotError, "CANDIDATE_SOURCE_DRIFT"):
            candidate.derive(override=projected)
        record = copy.deepcopy(self.output["package.json"]["records"][0])
        record["events"][1]["onset_q"] = [1, 1]
        with self.assertRaisesRegex(candidate.PilotError, "TIMING_SCOPE"):
            candidate.check_connected_eighths(record)
        record = copy.deepcopy(self.output["package.json"]["records"][0])
        record["events"][0]["fret"] += 1
        with self.assertRaisesRegex(candidate.PilotError, "SOURCE_EVENT_DRIFT"):
            candidate.check_source_cell(self.output["package.json"]["sources"], record,
                                        "L12-TXT1-84-95", "L12-PDF1-p3")

    def test_pinned_source_and_reservation(self):
        with mock.patch.dict(candidate.source.PINS, {candidate.source.TXT: (13087, "0" * 64)}):
            with self.assertRaisesRegex(candidate.source.ProposalError, "INPUT_HASH_DRIFT"):
                candidate.derive()
        self.assertEqual(self.output["summary.json"]["allocation_floors"],
                         {"item": 1143, "module": 1143, "variant": 7408})
        self.assertEqual(self.output["summary.json"]["live_identity_audit_sha256"],
                         candidate.IDENTITY_AUDIT_SHA)
        rung03 = candidate.read(ROOT, candidate.RUNG03 / "identity-registry.json")
        old = {e["id"] for e in rung03["entities"]}
        mine = {e["id"] for e in self.output["identity-registry.json"]["entities"]
                if e["kind"] in ("item", "module", "variant")}
        self.assertFalse(old & mine)

    def test_forced_runtime_admission_refused(self):
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
                (directory / name).write_bytes(candidate.encode(value))
            profile_sha = hashlib.sha256((directory / "expected-profile.json").read_bytes()).hexdigest()
            run = subprocess.run([str(exe), "--package", str(directory / "package.json"),
                                  "--registry", str(directory / "identity-registry.json"),
                                  "--profile", str(directory / "expected-profile.json"),
                                  "--profile-sha256", profile_sha, "--source-root", str(ROOT),
                                  "--report", str(directory / "report.json")],
                                 capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
            report = json.loads((directory / "report.json").read_text())
            self.assertIn("RUNTIME_NOT_ADMITTED", {issue["code"] for issue in report["issues"]})


if __name__ == "__main__":
    unittest.main()
