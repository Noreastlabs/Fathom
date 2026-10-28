"""Focused Level56 printed-attack and authority checks."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tools"))

from parallel10_level056_schema1_unallocated import (  # noqa: E402
    ATTACK_COUNTS, ROOT, digest, encoded, pinned, project, read_inputs,
)


class Level56UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate, cls.foundation, cls.registry = read_inputs(ROOT)
        cls.proposal, cls.handoff = project(cls.candidate, cls.foundation, cls.registry)

    def test_whole_workload_and_null_authority(self) -> None:
        self.assertEqual(self.proposal["counts"], {
            "provisional_components": 11, "attack_units": 54, "silent_spellings": 42,
            "written_prompts": 24, "printed_attacks": 936, "vi_source_conflicts": 4})
        self.assertEqual([r["source_component"] for r in self.proposal["records"]], list("ABCDEFGHIJK"))
        for record in self.proposal["records"]:
            fields = record["schema1_fields"]
            self.assertIsNone(fields["id"])
            self.assertIsNone(fields["workbook_id"])
            self.assertIsNone(fields["lineage"])
            self.assertIsNone(fields["timing"]["fixed_bpm"])
            self.assertFalse(fields["runtime_eligible"])
            for event in fields["events"]:
                self.assertIsNone(event["performed_member_pitches"])
                self.assertIsNone(event["schema1_fields"]["event_id"])
                self.assertIsNone(event["schema1_fields"]["onset_q"])
                self.assertIsNone(event["schema1_fields"]["duration_q"])
                self.assertIsNone(event["schema1_fields"]["pitch_binding"])
                self.assertIsNone(event["schema1_fields"]["pick"])
        for module, count in ATTACK_COUNTS.items():
            record = self.proposal["records"][ord(module) - ord("A")]
            self.assertEqual(len(record["schema1_fields"]["events"]), count)
        self.assertEqual(self.proposal["records"][0]["schema1_fields"]["events"], [])
        self.assertEqual(self.proposal["records"][9]["schema1_fields"]["events"], [])
        self.assertEqual(len(self.proposal["records"][0]["silent_tasks"]["silent_spelling_items"]), 42)
        self.assertEqual(len(self.proposal["records"][9]["written_tasks"]["analysis"]), 12)
        self.assertEqual(len(self.proposal["records"][9]["written_tasks"]["transpose"]), 12)
        self.assertFalse(self.proposal["schema1_importable"])
        self.assertFalse(self.proposal["admitted"])

    def test_printed_attack_mapping_and_alternative_passes(self) -> None:
        b = self.proposal["records"][1]["schema1_fields"]
        self.assertEqual(len(b["variants"]), 6)
        for start in range(0, 168, 4):
            group = b["events"][start:start + 4]
            self.assertEqual([e["printed_attack_type"] for e in group],
                             ["blocked_triad", "individual_voice", "individual_voice", "individual_voice"])
            self.assertEqual(len({e["printed_chord_symbol"] for e in group}), 1)
            self.assertEqual(len({e["source_txt_ref"] for e in group}), 1)
        for module in "CDEFGH":
            record = self.proposal["records"][ord(module) - ord("A")]["schema1_fields"]
            self.assertEqual(len(record["variants"]), 6)
            self.assertEqual([len(v["source_event_ordinals"]) for v in record["variants"]], [16] * 6)
            self.assertEqual([e["source_bar_number"] for e in record["events"][:16]],
                             [1] * 4 + [2] * 4 + [3] * 4 + [4] * 4)
        i = self.proposal["records"][8]["schema1_fields"]
        self.assertEqual(sum(e["printed_attack_type"] == "individual_voice" for e in i["events"]), 72)
        self.assertTrue(all(e["source_tone"]["sounding_midi"] is None for e in i["events"]
                            if e["source_tone"] is not None))
        k = self.proposal["records"][10]["schema1_fields"]
        self.assertEqual(len(k["events"]), 96)
        self.assertTrue(all(e["printed_attack_type"] == "rhythm_chord" for e in k["events"]))
        self.assertEqual(self.candidate["optional_pass_attack_count"], None)

    def test_conflicts_and_pdf_only_guidance_preserved(self) -> None:
        self.assertEqual([c["analysis_number"] for c in self.proposal["source_conflicts"]], [4, 5, 9, 10])
        self.assertTrue(all(c["progression_label"] == "P/T" and c["analysis_label"] == "P"
                            for c in self.proposal["source_conflicts"]))
        for module in "FG":
            events = self.proposal["records"][ord(module) - ord("A")]["schema1_fields"]["events"]
            self.assertTrue(any(e["printed_roman"] == "VI" and e["printed_function"] == "P/T"
                                for e in events))
        self.assertEqual([d["kind"] for d in self.proposal["source_differences"]], [
            "PDF_only_v_V_V7_ear_loop_and_advancement_rule",
            "PDF_only_completion_audit_and_practice_log",
            "PDF_additional_progression_passes_and_voicing_substitutions"])
        self.assertIn("Natural-v versus strong-V ear loop",
                      self.proposal["source_differences"][0]["pdf_text"])
        self.assertIn("24-bar capstone", self.proposal["source_differences"][1]["pdf_text"])
        self.assertEqual(self.proposal["source_differences"][2]["pdf_pages"], [9, 10, 11, 12, 13, 14])

    def test_source_and_authority_refusals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.txt").write_bytes(b"changed source")
            with self.assertRaisesRegex(ValueError, "input drift"):
                pinned(root, "source.txt", "0" * 64)
        candidate = copy.deepcopy(self.candidate)
        candidate["sounded_attack_total"] = 937
        with self.assertRaisesRegex(ValueError, "936/42/24"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["source_conflicts"][0]["progression_label"] = "P"
        with self.assertRaisesRegex(ValueError, "VI source"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["fixed_bpm"] = 80
        with self.assertRaisesRegex(ValueError, "invented identity/performance"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["modules"]["C"][0]["printed_attacks"] = 32
        with self.assertRaisesRegex(ValueError, "printed bar/attack"):
            project(candidate, self.foundation, self.registry)

    def test_identity_boundary_and_determinism(self) -> None:
        changed = copy.deepcopy(self.foundation)
        changed["records"].append({"legacy_level": 56, "workbook_id": "fg:workbook:000056"})
        with self.assertRaisesRegex(ValueError, "unexpected canonical Level56"):
            project(self.candidate, changed, self.registry)
        changed = copy.deepcopy(self.registry)
        changed["entities"].append({"id": "fg:workbook:000056"})
        with self.assertRaisesRegex(ValueError, "unexpected Level56 registry"):
            project(self.candidate, self.foundation, changed)
        again, handoff = project(self.candidate, self.foundation, self.registry)
        self.assertEqual(encoded(again), encoded(self.proposal))
        self.assertEqual(encoded(handoff), encoded(self.handoff))
        self.assertEqual(digest(encoded(again)), digest(encoded(self.proposal)))


if __name__ == "__main__":
    unittest.main()
