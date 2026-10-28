"""Focused Level 41 printed-contact and nonadmission checks."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel06_level041_schema1_unallocated as lane  # noqa: E402


class Level41ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate, cls.package, cls.registry = lane.read_inputs(ROOT)

    def project(self, candidate=None):
        return lane.project(candidate if candidate is not None else self.candidate,
                            self.package, self.registry)

    def test_exact_units_contacts_and_pitch_geometry(self) -> None:
        proposal, handoff = self.project()
        self.assertEqual(len(proposal["records"]), 4)
        self.assertEqual(proposal["counts"]["source_items"], 21)
        self.assertEqual(proposal["counts"]["written_note_contacts"], 420)
        for record in proposal["records"]:
            module = record["source_component"]
            fields = record["schema1_fields"]
            units = lane.source_units(self.candidate, module)
            item_count, note_count = lane.COUNTS[module]
            self.assertEqual(len(fields["variants"]), item_count)
            self.assertEqual(len(fields["events"]), note_count)
            self.assertEqual([e["source_event"] for e in fields["events"]],
                             [e for unit in units for e in unit["events"]])
            for unit, variant in zip(units, fields["variants"]):
                self.assertEqual(variant["source_item"], unit["source_item"])
                self.assertIsNone(variant["id"])
            for event in fields["events"]:
                source, schema = event["source_event"], event["schema1_fields"]
                self.assertEqual(schema["spelling"], source["tone"])
                self.assertEqual(schema["midi"] % 12, lane.PITCH_CLASS[source["tone"]])
                self.assertEqual(schema["fret"], source["fret"])
                self.assertEqual(schema["finger"], source["finger"])
                self.assertIsNone(schema["event_id"])
                self.assertIsNone(schema["onset_q"])
                self.assertIsNone(schema["duration_q"])
                self.assertTrue(event["source_refs"])
        self.assertEqual(handoff["catalog_workbook_id"], "fg:workbook:000041")

    def test_route_turn_and_per_segment_source_refs(self) -> None:
        proposal, _ = self.project()
        zig = next(r for r in proposal["records"] if r["source_component"] == "linked_zigzag")
        events = zig["schema1_fields"]["events"]
        self.assertEqual(len(events), 120)
        self.assertEqual([v["source_item"]["direction"] for v in zig["schema1_fields"]["variants"]],
                         ["forward", "reverse"])
        self.assertEqual([e["source_refs"] for e in events],
                         [refs for unit in lane.source_units(self.candidate, "linked_zigzag")
                          for refs in unit["event_refs"]])
        self.assertEqual([(e["source_event"]["string"], e["source_event"]["fret"])
                          for e in events[59:61]], [("e", 17), ("e", 17)])
        self.assertEqual(proposal["source_pdf_layout_exceptions"],
                         self.candidate["pdf_layout_exceptions"])

    def test_major_minor_pairs_and_random_cards(self) -> None:
        proposal, handoff = self.project()
        comparison = next(r for r in proposal["records"]
                          if r["source_component"] == "parallel_color_comparisons")
        variants = comparison["schema1_fields"]["variants"]
        self.assertEqual([v["source_item"]["color"] for v in variants],
                         ["major", "minor"] * 5)
        self.assertTrue(all(v["source_item"]["silence_is_instruction_not_note_event"]
                            for v in variants))
        self.assertEqual(proposal["source_random_entry_cards"], self.candidate["random_entry_cards"])
        self.assertTrue(all(c["authored_phrase_events"] is None
                            for c in proposal["source_random_entry_cards"]))
        self.assertEqual(handoff["random_entry_cards_without_authored_phrases"], 10)

    def test_nonadmission_boundary(self) -> None:
        proposal, handoff = self.project()
        for key in ("canonical_ids_allocated", "schema1_importable", "whole_workbook_complete",
                    "runtime_eligible", "admitted"):
            self.assertIs(proposal[key], False)
        self.assertIs(handoff["admitted"], False)
        for record in proposal["records"]:
            fields = record["schema1_fields"]
            self.assertIsNone(fields["id"])
            self.assertIsNone(fields["timing"]["fixed_bpm"])
            self.assertTrue(all(e["schema1_fields"]["attack"] is None for e in fields["events"]))

    def test_note_tab_mismatch_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["vertical_positions"]["positions"][0]["events"][0]["fret"] += 1
        with self.assertRaisesRegex(ValueError, "pitch mismatch"):
            self.project(changed)

    def test_degree_mismatch_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["parallel_color_comparisons"]["pairs"][0]["phrases"][0]["events"][0]["degree"] = "b3"
        with self.assertRaisesRegex(ValueError, "degree/TAB"):
            self.project(changed)

    def test_added_or_missing_contacts_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["shared_anchor_seams"]["seams"][0]["events"].pop()
        with self.assertRaisesRegex(ValueError, "unit/contact count"):
            self.project(changed)
        changed = copy.deepcopy(self.candidate)
        changed["random_entry_cards"][0]["authored_phrase_events"] = []
        with self.assertRaisesRegex(ValueError, "authorship"):
            self.project(changed)

    def test_timing_and_admission_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["linked_zigzag"]["forward"]["route"][0]["events"][0]["onset_q"] = 0
        with self.assertRaisesRegex(ValueError, "timing"):
            self.project(changed)
        changed = copy.deepcopy(self.candidate)
        changed["admitted"] = True
        with self.assertRaisesRegex(ValueError, "source/boundary"):
            self.project(changed)

    def test_pinned_candidate_and_output_verify(self) -> None:
        rel = next(iter(lane.INPUTS))
        with patch.object(lane, "INPUTS", {**lane.INPUTS, rel: "0" * 64}):
            with self.assertRaisesRegex(ValueError, "input drift"):
                lane.read_inputs(ROOT)
        lane.run("verify", ROOT)


if __name__ == "__main__":
    unittest.main()
