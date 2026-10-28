"""Focused whole-Level62 source-tone and unallocated-authority checks."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tools"))

from parallel10_level062_schema1_unallocated import (  # noqa: E402
    ROOT, digest, encoded, ordered_units, pinned, project, read_inputs,
)
from parallel_07_level062_whole_candidate import EXPECTED, CELL_COUNTS  # noqa: E402


class Level62UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate, cls.foundation, cls.registry = read_inputs(ROOT)
        cls.proposal, cls.handoff = project(cls.candidate, cls.foundation, cls.registry)

    def test_all_printed_tones_in_source_order(self) -> None:
        self.assertEqual(self.proposal["counts"], {
            "provisional_components": 10, "attack_units": 83, "tab_grids": 71,
            "recovery_cards": 12, "printed_sounding_tones": 788,
            "J_recovery_tones": 24, "J_bridge_tones": 40})
        self.assertEqual([r["source_component"] for r in self.proposal["records"]], list("ABCDEFGHIJ"))
        for letter in "ABCDEFGHIJ":
            module = self.candidate["modules"][letter]
            record = self.proposal["records"][ord(letter) - ord("A")]["schema1_fields"]
            source_units = ordered_units(module, letter)
            expected = [tone for _, unit in source_units for tone in unit["events"]]
            events = record["events"]
            self.assertEqual(len(source_units), CELL_COUNTS[letter] + (12 if letter == "J" else 0))
            self.assertEqual(len(events), EXPECTED[letter])
            self.assertEqual([e["source_tone"] for e in events], expected)
            self.assertEqual([e["source_local_ordinal"] for e in events], list(range(1, len(events) + 1)))
            self.assertEqual([v["source_unit"]["source_ref"] for v in record["variants"]],
                             [unit["source_ref"] for _, unit in source_units])
            self.assertTrue(all(e["schema1_fields"]["event_id"] is None and
                                e["schema1_fields"]["onset_q"] is None and
                                e["schema1_fields"]["duration_q"] is None and
                                e["schema1_fields"]["pick"] is None and
                                e["schema1_fields"]["pitch_binding"] is None for e in events))
            self.assertIsNone(record["id"])
            self.assertIsNone(record["lineage"])
            self.assertIsNone(record["timing"]["fixed_bpm"])
        self.assertFalse(self.proposal["schema1_importable"])
        self.assertFalse(self.proposal["admitted"])

    def test_J_recovery_bridge_and_pdf_status(self) -> None:
        j = self.proposal["records"][9]["schema1_fields"]
        self.assertEqual([v["source_unit_type"] for v in j["variants"]],
                         ["recovery_card"] * 12 + ["tab_grid"] * 5)
        self.assertEqual([v["source_unit"]["tone_count"] for v in j["variants"]],
                         [2] * 12 + [8] * 5)
        self.assertEqual([e["source_pdf_grid_status"] for e in j["events"]], ["summary_only"] * 64)
        self.assertEqual([e["source_pdf_page"] for e in j["events"]], [19] * 64)
        for record in self.proposal["records"][:9]:
            self.assertTrue(all(e["source_pdf_grid_status"] == "exact_row_parity"
                                for e in record["schema1_fields"]["events"]))
        self.assertEqual(len(self.proposal["source_transcription"]["txt_lines"]), 874)
        self.assertEqual(len(self.proposal["source_transcription"]["pdf_pages"]), 20)

    def test_pdf_instructions_remain_non_timed(self) -> None:
        directions = self.proposal["pdf_only_directions"]
        self.assertEqual([z["zone"] for z in directions["connection_zones"]],
                         ["Z1", "Z2", "Z3", "Z4", "Z5"])
        self.assertIn("starting stroke reverses", " ".join(directions["picking_choices"]))
        self.assertIn("rest - notes 1-2 - rest - notes 3-4", directions["motif_grid"])
        self.assertIn("beat 4", directions["major_capstone_key_announcement"])
        self.assertIn("strict alternate picking", directions["minor_capstone_pick_option"])
        self.assertIn("No numeric BPM", self.proposal["timing_boundary"])
        self.assertFalse(self.proposal["runtime_eligible"])

    def test_source_count_pitch_timing_refusals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.txt").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "input drift"):
                pinned(root, "source.txt", "0" * 64)
        candidate = copy.deepcopy(self.candidate)
        candidate["workload"]["total_sounding_tones"] = 789
        with self.assertRaisesRegex(ValueError, "788 source"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["modules"]["A"]["cells"][0]["events"][0]["note"] = "F#"
        with self.assertRaisesRegex(ValueError, "pitch drift"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["modules"]["J"]["recovery_cards"][0]["events"][0]["onset_q"] = 0
        with self.assertRaisesRegex(ValueError, "timing/sounding"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["pdf_only_directions"]["motif_grid"] = "quarter rest"
        with self.assertRaisesRegex(ValueError, "PDF-only"):
            project(candidate, self.foundation, self.registry)

    def test_identity_boundary_and_determinism(self) -> None:
        candidate = copy.deepcopy(self.candidate)
        candidate["stable_ids"] = ["fg:item:invented"]
        with self.assertRaisesRegex(ValueError, "identity/admission"):
            project(candidate, self.foundation, self.registry)
        foundation = copy.deepcopy(self.foundation)
        foundation["records"].append({"legacy_level": 62, "workbook_id": "fg:workbook:000062"})
        with self.assertRaisesRegex(ValueError, "unexpected canonical Level62"):
            project(self.candidate, foundation, self.registry)
        registry = copy.deepcopy(self.registry)
        registry["entities"].append({"id": "fg:workbook:000062"})
        with self.assertRaisesRegex(ValueError, "unexpected Level62 registry"):
            project(self.candidate, self.foundation, registry)
        again, handoff = project(self.candidate, self.foundation, self.registry)
        self.assertEqual(encoded(again), encoded(self.proposal))
        self.assertEqual(encoded(handoff), encoded(self.handoff))
        self.assertEqual(digest(encoded(again)), digest(encoded(self.proposal)))


if __name__ == "__main__":
    unittest.main()
