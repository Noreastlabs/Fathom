#!/usr/bin/env python3
"""Focused source and musical-data checks for one Level 50 E/Em cell."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))

import convert_curriculum_v1_level050 as converter  # noqa: E402


class Level050ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.txt = (ROOT / converter.TXT_REL).read_bytes()
        cls.pdf = (ROOT / converter.PDF_REL).read_bytes()
        cls.projection = converter.build_projection(cls.txt, cls.pdf)

    def test_pinned_source_pair_and_exact_passage(self) -> None:
        txt = self.projection["source_authority"]["txt"]
        pdf = self.projection["source_authority"]["pdf"]
        self.assertEqual((txt["bytes"], txt["sha256"]), (converter.TXT_BYTES, converter.TXT_SHA256))
        self.assertEqual((pdf["bytes"], pdf["sha256"]), (converter.PDF_BYTES, converter.PDF_SHA256))
        self.assertEqual((txt["line_start"], txt["line_end"]), (45, 49))
        self.assertEqual(pdf["page"], 4)
        self.assertEqual(
            self.projection["record_projection"]["source_refs"],
            ["L50-TXT1-45-49", "L50-PDF1-p4"],
        )

    def test_pdf_page_four_independently_confirms_cell(self) -> None:
        from pypdf import PdfReader

        reader = PdfReader(str(ROOT / converter.PDF_REL))
        self.assertEqual(len(reader.pages), 20)
        page = reader.pages[3].extract_text() or ""
        for phrase in (
            "E <-> Em",
            "Use slow quarter notes.",
            "Each pair alternates for eight attacks.",
            "E: 0 2 2 1 0 0",
            "Em: 0 2 2 0 0 0",
            "Standard tuning.",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, page)

    def test_chord_voicings_finger_anchors_pitch_and_spelling(self) -> None:
        voicings = self.projection["record_projection"]["voicings"]
        self.assertEqual(voicings["E"]["frets_low_to_high"], [0, 2, 2, 1, 0, 0])
        self.assertEqual(voicings["E"]["fingers_low_to_high"], ["O", 2, 3, 1, "O", "O"])
        self.assertEqual(voicings["E"]["source_spelling"], ["E", "G#", "B"])
        self.assertEqual([m["midi"] for m in voicings["E"]["members_low_to_high"]], [40, 47, 52, 56, 59, 64])
        self.assertEqual(
            [m["spelling"] for m in voicings["E"]["members_low_to_high"]],
            ["E", "B", "E", "G#", "B", "E"],
        )
        self.assertEqual(voicings["Em"]["frets_low_to_high"], [0, 2, 2, 0, 0, 0])
        self.assertEqual(voicings["Em"]["fingers_low_to_high"], ["O", 2, 3, "O", "O", "O"])
        self.assertEqual(voicings["Em"]["source_spelling"], ["E", "G", "B"])
        self.assertEqual([m["midi"] for m in voicings["Em"]["members_low_to_high"]], [40, 47, 52, 55, 59, 64])
        self.assertEqual(
            [m["spelling"] for m in voicings["Em"]["members_low_to_high"]],
            ["E", "B", "E", "G", "B", "E"],
        )
        for name in ("E", "Em"):
            members = voicings[name]["members_low_to_high"]
            self.assertEqual((members[1]["string"], members[1]["fret"], members[1]["finger"]), (2, 2, 2))
            self.assertEqual((members[2]["string"], members[2]["fret"], members[2]["finger"]), (3, 2, 3))
        self.assertEqual(voicings["E"]["members_low_to_high"][3]["finger"], 1)
        self.assertEqual(voicings["Em"]["members_low_to_high"][3]["finger"], "O")
        self.assertTrue(all(shape["attack_scope"] == "all_6_strings" for shape in voicings.values()))

    def test_exact_eight_attack_order_quarter_onsets_and_unresolved_durations(self) -> None:
        record = self.projection["record_projection"]
        events = record["events"]
        self.assertEqual(len(events), 8)
        self.assertEqual([event["count_label"] for event in events], list(converter.EXPECTED_COUNTS))
        self.assertEqual(
            [event["canonical_event_shape_projection"]["symbol"] for event in events],
            list(converter.EXPECTED_CHORDS),
        )
        self.assertEqual([event["source_hand_direction"] for event in events], ["D"] * 8)
        self.assertEqual([event["source_hand_action"] for event in events], ["down_strum"] * 8)
        for index, event in enumerate(events):
            self.assertEqual(
                event["source_local_occurrence_key"],
                f"L50-TXT1-47-49:attack-{index + 1:04d}",
            )
            projected = event["canonical_event_shape_projection"]
            self.assertEqual(projected["onset_q"], [index, 1])
            self.assertIsNone(projected["duration_q"])
            self.assertEqual(projected["attack"], "simultaneous_example")
            self.assertTrue(all(member["onset_q"] is None for member in projected["members"]))
            self.assertTrue(all(member["duration_q"] is None for member in projected["members"]))
        self.assertIsNone(record["timing"]["tempo_bpm"])
        self.assertIsNone(record["timing"]["attack_duration_q"])
        self.assertIsNone(record["timing"]["member_duration_q"])
        self.assertEqual(record["technique_legend"]["D"], "down-strum, preserved from the authored Str row")

    def test_projection_is_unassigned_and_never_claims_canonical_or_runtime_status(self) -> None:
        import json

        self.assertEqual(self.projection["projection_schema"], "lane-local-source-cell-projection.1")
        identity = self.projection["identity_assignment"]
        self.assertEqual(identity["status"], "pending_trusted_identity_handoff")
        self.assertIsNone(identity["module_id"])
        self.assertIsNone(identity["item_id"])
        self.assertEqual(identity["variant_ids"], [])
        self.assertEqual(identity["event_ids"], [])
        state = self.projection["release_state"]
        self.assertTrue(all(value is False for value in state.values()))
        encoded = json.dumps(self.projection, ensure_ascii=False)
        self.assertNotIn("fg:item:", encoded)
        self.assertNotIn("fg:module:", encoded)
        self.assertNotIn("fg:variant:", encoded)
        self.assertNotIn('"event_id"', encoded)

    def test_generation_is_byte_deterministic(self) -> None:
        first = converter.deterministic_json_bytes(converter.build_projection(self.txt, self.pdf))
        second = converter.deterministic_json_bytes(converter.build_projection(self.txt, self.pdf))
        self.assertEqual(first, second)

    def test_changed_source_pair_is_refused(self) -> None:
        with self.assertRaises(converter.CandidateError):
            converter.build_projection(self.txt + b"\n", self.pdf)
        with self.assertRaises(converter.CandidateError):
            converter.build_projection(self.txt, self.pdf + b"\n")

    def test_malformed_selected_rows_fail_closed(self) -> None:
        cases = (
            (b"Cnt|1----2----3----4----1----2----3----4----|", b"Cnt|1----2----3----4----1----2----3----|"),
            (b"Chd|E----Em---E----Em---E----Em---E----Em---|", b"Chd|E----F----E----Em---E----Em---E----Em---|"),
            (b"Str|D----D----D----D----D----D----D----D----|", b"Str|D----U----D----D----D----D----D----D----|"),
        )
        for original, changed in cases:
            with self.subTest(original=original):
                with self.assertRaises(converter.CandidateError):
                    converter._parse_selected_cell(self.txt.replace(original, changed))

    def test_output_path_outside_lane_build_is_refused(self) -> None:
        output = Path(tempfile.gettempdir()) / f"fathom-level50-refusal-{uuid.uuid4().hex}.json"
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "Tools/convert_curriculum_v1_level050.py"),
                "--output",
                str(output),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
        self.assertIn("output must remain under", completed.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
