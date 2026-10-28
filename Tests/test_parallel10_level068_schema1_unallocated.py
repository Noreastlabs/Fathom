"""Focused Level68 source-tone, conflict and unallocated-authority checks."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tools"))

from parallel10_level068_schema1_unallocated import (  # noqa: E402
    ROOT, digest, encoded, pinned, project, read_inputs,
)
from curriculum_level068_whole_candidate import EXPECTED  # noqa: E402


class Level68UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate, cls.foundation, cls.registry = read_inputs(ROOT)
        cls.proposal, cls.handoff = project(cls.candidate, cls.foundation, cls.registry)

    def test_every_printed_tone_and_null_authority(self) -> None:
        self.assertEqual(self.proposal["counts"], {"provisional_components": 11,
            "attack_units": 79, "tab_cells": 67, "recovery_pairs": 12,
            "printed_sounding_tones": 630})
        self.assertEqual([r["source_component"] for r in self.proposal["records"]], list("ABCDEFGHIJK"))
        for letter in "ABCDEFGHIJ":
            record = self.proposal["records"][ord(letter) - ord("A")]["schema1_fields"]
            source = self.candidate["modules"][letter]
            expected = [tone for cell in source for tone in cell["events"]]
            events = record["events"]
            self.assertEqual(len(events), EXPECTED[letter])
            self.assertEqual([e["source_tone"] for e in events], expected)
            self.assertEqual([e["source_local_ordinal"] for e in events], list(range(1, len(events) + 1)))
            self.assertEqual([v["source_unit"]["txt_ref"] for v in record["variants"]],
                             [cell["txt_ref"] for cell in source])
            self.assertIsNone(record["id"])
            self.assertIsNone(record["lineage"])
            self.assertIsNone(record["timing"]["fixed_bpm"])
            self.assertFalse(record["runtime_eligible"])
            for event in events:
                self.assertIsNone(event["schema1_fields"]["event_id"])
                self.assertIsNone(event["schema1_fields"]["pick"])
                self.assertIsNone(event["schema1_fields"]["pitch_binding"])
                self.assertIsNone(event["schema1_fields"]["onset_q"])
                self.assertIsNone(event["schema1_fields"]["duration_q"])
                self.assertIsNone(event["performed_member_pitches"])
        self.assertFalse(self.proposal["schema1_importable"])
        self.assertFalse(self.proposal["admitted"])

    def test_K_recovery_pairs_without_invented_contacts(self) -> None:
        k = self.proposal["records"][10]["schema1_fields"]
        self.assertEqual(len(k["variants"]), 12)
        self.assertEqual(len(k["events"]), 24)
        for pair, variant in enumerate(k["variants"]):
            card = self.candidate["recovery_cards"][pair]
            self.assertEqual(variant["source_unit"], card)
            two = k["events"][2 * pair:2 * pair + 2]
            self.assertEqual([e["source_tone"]["note"] for e in two],
                             [card["weak_note"], card["target_note"]])
            self.assertEqual([e["source_tone"]["role_raw"] for e in two],
                             [card["weak_role"], card["target_role"]])
            self.assertTrue(all(e["source_tone"]["string"] is None and
                                e["source_tone"]["fret"] is None and
                                e["source_tone"]["pitch_class"] is None for e in two))
        self.assertEqual(len(self.proposal["capstone"]["four_bar_groups_raw"]), 4)
        self.assertEqual(len(self.proposal["capstone"]["pass_constraints_raw"]), 3)
        self.assertIn("tonic close in bar 16", self.proposal["capstone"]["rest_and_close_raw"])

    def test_F1_conflict_and_pdf_guidance_preserved(self) -> None:
        conflict = self.proposal["source_ambiguities"][0]
        self.assertEqual(conflict["status"], "pending_curriculum_review")
        self.assertEqual(conflict["printed_final_note"], "B")
        self.assertIn("resolve the final E clearly", conflict["pdf_instruction"])
        f = self.proposal["records"][5]["schema1_fields"]["events"]
        self.assertEqual(f[7]["source_tone"]["note"], "B")
        self.assertEqual([d["kind"] for d in self.proposal["source_differences"]], [
            "PDF_I_combines_call_answer_note_rows",
            "PDF_K_adds_capstone_rubric_and_phrase_constraints",
            "PDF_only_recovery_ear_tests_and_practice_log"])
        self.assertEqual(len(self.proposal["guidance"]["txt_full_lines"]), 871)
        self.assertEqual(len(self.proposal["guidance"]["pdf_full_extracted_pages"]), 20)
        self.assertEqual(self.candidate["modules"]["C"][0]["second_pass_event_ordinals"],
                         [2, 3, 4, 5, 6, 7, 8, 9])

    def test_source_count_pitch_conflict_refusals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.txt").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "input drift"):
                pinned(root, "source.txt", "0" * 64)
        candidate = copy.deepcopy(self.candidate)
        candidate["printed_sounding_tones"] = 631
        with self.assertRaisesRegex(ValueError, "630-tone"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["modules"]["A"][0]["events"][0]["note"] = "F"
        with self.assertRaisesRegex(ValueError, "pitch drift"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["source_ambiguities"][0]["printed_final_note"] = "E"
        with self.assertRaisesRegex(ValueError, "F1 source conflict"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["fixed_bpm"] = 80
        with self.assertRaisesRegex(ValueError, "identity/performance"):
            project(candidate, self.foundation, self.registry)

    def test_identity_boundary_and_determinism(self) -> None:
        foundation = copy.deepcopy(self.foundation)
        foundation["records"].append({"legacy_level": 68, "workbook_id": "fg:workbook:000068"})
        with self.assertRaisesRegex(ValueError, "unexpected canonical Level68"):
            project(self.candidate, foundation, self.registry)
        registry = copy.deepcopy(self.registry)
        registry["entities"].append({"id": "fg:workbook:000068"})
        with self.assertRaisesRegex(ValueError, "unexpected Level68 registry"):
            project(self.candidate, self.foundation, registry)
        again, handoff = project(self.candidate, self.foundation, self.registry)
        self.assertEqual(encoded(again), encoded(self.proposal))
        self.assertEqual(encoded(handoff), encoded(self.handoff))
        self.assertEqual(digest(encoded(again)), digest(encoded(self.proposal)))


if __name__ == "__main__":
    unittest.main()
