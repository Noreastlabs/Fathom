"""Focused checks for detached Level31 unallocated schema1 field sketch."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel11_level031_schema1_unallocated as lane  # noqa: E402


class Level31UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.c, cls.row, cls.foundation, cls.registry = lane.read_inputs(ROOT)
        cls.proposal, cls.handoff = lane.project(cls.c, cls.row, cls.foundation, cls.registry)

    def test_sealed_twins_original_replay_pins_and_source_only_catalog(self) -> None:
        txt = next(k for k in lane.INPUTS if k.endswith(".txt"))
        pdf = next(k for k in lane.INPUTS if k.endswith(".pdf"))
        self.assertEqual(self.c["source_authority"]["txt"]["sha256"], lane.INPUTS[txt])
        self.assertEqual(self.c["source_authority"]["pdf"]["sha256"], lane.INPUTS[pdf])
        self.assertEqual(self.row["conversion_status"], "not_converted")
        self.assertEqual(self.handoff["existing_level031_records"], 0)
        self.assertEqual(self.handoff["existing_level031_workbook_entities"], 0)
        bad = copy.deepcopy(self.foundation)
        entry = next(e for e in bad["workbook_catalog"]["entries"] if e["workbook_id"] == "fg:workbook:000031")
        entry["admitted"] = True
        with self.assertRaisesRegex(ValueError, "source-only catalog drift"):
            lane.identity_boundary(bad, self.registry)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "source.txt").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "input drift"):
                lane.pinned(Path(d), "source.txt", "0" * 64)

    def test_13_cards_22_notes_286_total_25_cell_550_route(self) -> None:
        p = self.proposal
        self.assertEqual(p["counts"], {"rungs": 13, "notes_per_rung": 22,
                                       "notes_in_source_cards": 286, "round_trip_cells": 25,
                                       "round_trip_note_occurrences": 550})
        self.assertEqual([r["source_rung"] for r in p["records"]], list(range(1, 14)))
        self.assertEqual(sum(len(r["schema1_fields"]["events"]) for r in p["records"]), 286)
        self.assertEqual(p["route_source_only"]["round_trip_rung_order"],
                         list(range(1, 14)) + list(range(12, 0, -1)))
        self.assertEqual(p["route_source_only"]["additional_canonical_events"], 0)
        self.assertIsNone(p["route_source_only"]["performed"])
        self.assertEqual([r["source_record"]["root_fret"] for r in p["records"]], list(range(5, 18)))
        self.assertEqual([r["source_record"]["key"] for r in p["records"]], list(lane.KEYS))

    def test_every_printed_note_tab_finger_pitch_and_turn(self) -> None:
        for r in self.proposal["records"]:
            source = r["source_record"]
            self.assertEqual(len(source["raw_txt_card"]), 12)
            self.assertEqual(len(source["raw_pdf_card"]), 14)
            self.assertEqual(len(source["raw_pdf_route_map_row"]), 5)
            self.assertFalse(source["within_cell_shift"])
            self.assertTrue(source["shift_after_complete_cell_only"])
            self.assertEqual([n["degree"] for n in source["notes"][:11]], [1, 2, 3, 5, 6, 1, 2, 3, 5, 6, 1])
            high = source["notes"][10:12]
            self.assertEqual([(n["tone"], n["string"], n["fret"]) for n in high],
                             [(source["key"], "e", source["root_fret"])] * 2)
            self.assertEqual(r["schema1_fields"]["events"][0]["schema1_fields"]["string"], 1)
            self.assertEqual(r["schema1_fields"]["events"][10]["schema1_fields"]["string"], 6)
            for e in r["schema1_fields"]["events"]:
                n, fields = e["source_note"], e["schema1_fields"]
                self.assertEqual(fields["spelling"], n["tone"])
                self.assertEqual(fields["string"], lane.STRING_NUMBER[n["string"]])
                self.assertEqual(fields["fret"], n["fret"])
                self.assertEqual(fields["finger"], n["finger_digit"])
                self.assertEqual(fields["midi"], lane.OPEN_MIDI[n["string"]] + n["fret"])
                self.assertEqual(fields["midi"] % 12, lane.tone_pc(fields["spelling"]))
            starts = r["schema1_fields"]["variants"]
            self.assertEqual([v["source_pick_start_option"] for v in starts], ["D", "U"])
            self.assertEqual([v["source_alternate_strokes"][0] for v in starts], ["D", "U"])

    def test_separator_discrepancy_and_guidance_remain_unresolved(self) -> None:
        d = self.proposal["source_discrepancies"][0]
        self.assertEqual(d["kind"], "octave_separator_position")
        self.assertEqual([d[k]["tokens_before_separator"] for k in ("txt_card", "pdf_card", "pdf_worked_example")], [6, 6, 5])
        self.assertTrue(d["sounding_tone_order_same"])
        self.assertIsNone(d["resolution"])
        self.assertEqual(d["status"], "pending_curriculum_review")
        guidance = " ".join(" ".join(v) for v in self.proposal["source_guidance"].values())
        self.assertIn("10-15 BPM", guidance)
        self.assertIn("pause one beat", guidance)
        self.assertIn("550 picked notes", guidance)

    def test_refuses_mutated_note_route_separator_and_invented_fields(self) -> None:
        edits = [
            (lambda c: c["counts"].update(notes_in_source_cards=287), "13/22/286/25/550 source count drift"),
            (lambda c: c["round_trip_rung_order"].append(13), "round-trip route/shift drift"),
            (lambda c: c["records"][0]["notes"][7].update(fret=7), "printed note/TAB/finger/pitch drift"),
            (lambda c: c["records"][0]["notes"][10].update(finger_digit=4), "printed note/TAB/finger/pitch drift"),
            (lambda c: c["records"][0].update(fixed_bpm=80), "rung geometry/identity/timing drift"),
            (lambda c: c["source_discrepancies"][0].update(resolution="accepted"), "octave separator discrepancy drift"),
            (lambda c: c.update(admitted=True), "source identity/admission drift"),
        ]
        for edit, message in edits:
            with self.subTest(message=message):
                bad = copy.deepcopy(self.c)
                edit(bad)
                with self.assertRaisesRegex(ValueError, message):
                    lane.validate_candidate(bad)
        self.assertFalse(self.proposal["schema1_importable"])
        self.assertFalse(self.proposal["admitted"])
        self.assertIsNone(self.proposal["mastery_observed"])
        for r in self.proposal["records"]:
            f = r["schema1_fields"]
            for key in ("id", "workbook_id", "module_id", "content_revision", "lineage"):
                self.assertIsNone(f[key])
            self.assertFalse(f["runtime_eligible"])
            self.assertIsNone(f["timing"]["note_per_click"])
            self.assertIsNone(f["timing"]["fixed_bpm"])
            for e in f["events"]:
                for key in ("event_id", "onset_q", "duration_q", "pick", "performed"):
                    self.assertIsNone(e["schema1_fields"][key])
            for v in f["variants"]:
                self.assertIsNone(v["id"])
                self.assertIsNone(v["actual_pick_start"])
                self.assertIsNone(v["performed"])

    def test_deterministic_products_and_verify(self) -> None:
        a = lane.products(ROOT)
        b = lane.products(ROOT)
        self.assertEqual({k: lane.encoded(v) for k, v in a.items()},
                         {k: lane.encoded(v) for k, v in b.items()})
        lane.run("verify", ROOT)
        self.assertEqual(a["summary.json"]["proposal_sha256"], lane.digest(lane.encoded(a["field-proposal.json"])))


if __name__ == "__main__":
    unittest.main()
