"""Focused source/authority refusals for the Level49 field proposal."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tools"))

from parallel10_level049_schema1_unallocated import (  # noqa: E402
    ROOT, MODULE_COUNTS, digest, encoded, pinned, project, read_inputs,
)


class Level49UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate, cls.foundation, _ = read_inputs(ROOT)
        cls.proposal, cls.handoff = project(cls.candidate, cls.foundation)

    def test_exact_whole_source_projection_and_representative_boundary(self) -> None:
        proposal = self.proposal
        self.assertEqual(proposal["counts"], {"components": 11, "units": 75, "printed_attacks": 780, "chord_shapes": 11})
        self.assertEqual([r["source_component"] for r in proposal["records"]], list(MODULE_COUNTS))
        self.assertEqual([len(r["schema1_fields"]["events"]) for r in proposal["records"]], list(MODULE_COUNTS.values()))
        self.assertEqual([len(r["schema1_fields"]["variants"]) for r in proposal["records"]], [6, 8, 8, 3, 8, 8, 8, 8, 8, 6, 4])
        for source_module, record in zip(self.candidate["modules"], proposal["records"]):
            projected = record["schema1_fields"]["events"]
            original = [a for unit in source_module["units"] for a in unit["attacks"]]
            self.assertEqual(len(projected), len(original))
            for item, attack in zip(projected, original):
                self.assertEqual(item["source_attack"]["printed_symbol"], attack["printed_symbol"])
                self.assertEqual(item["source_attack"]["txt_line"], attack["txt_line"])
                self.assertEqual(item["source_attack"]["pdf_page"], attack["pdf_page"])
                self.assertIsNone(item["schema1_fields"]["event_id"])
                self.assertIsNone(item["schema1_fields"]["onset_q"])
                self.assertIsNone(item["schema1_fields"]["duration_q"])
        self.assertEqual(self.handoff["existing_selected_representative"]["id"], "fg:item:000008")
        self.assertEqual(self.handoff["existing_selected_representative"]["event_count"], 2)
        self.assertFalse(self.handoff["existing_selected_representative"]["whole_workbook_complete"])
        self.assertFalse(proposal["schema1_importable"])
        self.assertFalse(proposal["admitted"])

    def test_strum_is_one_unpitched_attack_and_shapes_are_source_only(self) -> None:
        shapes = {shape["chord"]: shape for shape in self.proposal["chord_shapes"]}
        self.assertEqual(len(shapes), 11)
        self.assertEqual(shapes["A"]["frets"][0].lower(), "x")
        self.assertEqual(shapes["A"]["notes"][0].lower(), "x")
        for record in self.proposal["records"]:
            for event in record["schema1_fields"]["events"]:
                source = event["source_attack"]
                field = event["schema1_fields"]
                self.assertIsNone(field["pitch_binding"])
                if "strum" in source["kind"] or source["kind"] == "muted backbeat":
                    self.assertIsNone(event["source_tone"])
                    self.assertEqual(field["kind"], "contact")
                if source["kind"] == "downstrum":
                    self.assertEqual(field["pick"], "D")
                elif source["kind"] != "downstrum":
                    self.assertIsNone(field["pick"])
                if event["source_tone"]:
                    self.assertIsNone(event["source_tone"]["sounding_midi"])

    def test_source_hash_drift_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.txt").write_bytes(b"changed original")
            with self.assertRaisesRegex(ValueError, "input drift"):
                pinned(root, "source.txt", "0" * 64)

    def test_count_authority_timing_and_exception_refusals(self) -> None:
        candidate = copy.deepcopy(self.candidate)
        candidate["modules"][0]["units"][0]["attacks"].pop()
        with self.assertRaisesRegex(ValueError, "projected attack count drift"):
            project(candidate, self.foundation)
        candidate = copy.deepcopy(self.candidate)
        candidate["admitted"] = True
        with self.assertRaisesRegex(ValueError, "false authority"):
            project(candidate, self.foundation)
        candidate = copy.deepcopy(self.candidate)
        candidate["modules"][0]["units"][0]["attacks"][0]["performed_onset"] = [0, 1]
        with self.assertRaisesRegex(ValueError, "invented performance data"):
            project(candidate, self.foundation)
        candidate = copy.deepcopy(self.candidate)
        candidate["source_exceptions"].pop()
        with self.assertRaisesRegex(ValueError, "source exceptions"):
            project(candidate, self.foundation)

    def test_selected_identity_and_determinism(self) -> None:
        changed = copy.deepcopy(self.foundation)
        next(r for r in changed["records"] if r["id"] == "fg:item:000008")["content_revision"] = 4
        with self.assertRaisesRegex(ValueError, "representative identity"):
            project(self.candidate, changed)
        rebuilt, handoff = project(self.candidate, self.foundation)
        self.assertEqual(encoded(rebuilt), encoded(self.proposal))
        self.assertEqual(encoded(handoff), encoded(self.handoff))
        self.assertEqual(digest(encoded(rebuilt)), digest(encoded(self.proposal)))


if __name__ == "__main__":
    unittest.main()
