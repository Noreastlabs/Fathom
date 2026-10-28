"""Focused Level 6 source-to-schema1 proposal checks (non-importable)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

import parallel03_level006_schema1_unallocated as lane


ROOT = Path(__file__).resolve().parents[1]


class Level006UnallocatedProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        txt = lane.pinned_bytes(ROOT, next(pin for pin in lane.PINS if pin["path"] == lane.TXT_REL.as_posix()))
        cls.records = lane.parse_source(txt)
        cls.proposal, cls.handoff = lane.build_proposal(ROOT, lane.verify_all_pins(ROOT))
        cls.by_key = {record["source_local_case_key"]: record for record in cls.proposal["records"]}

    def test_full_source_counts_order_and_four_locators(self) -> None:
        proposal = self.proposal
        self.assertEqual(proposal["coverage"], {
            "sets": 9,
            "distinct_codes": 108,
            "mode_records": 216,
            "source_events": 6912,
            "events_per_record": 32,
            "source_refs_per_record": 4,
        })
        self.assertEqual(len(self.records), 216)
        self.assertEqual([record["set_number"] for record in self.records[:24]], [1] * 24)
        self.assertEqual([record["mode"] for record in self.records[:24]], ["A"] * 12 + ["B"] * 12)
        self.assertEqual(proposal["source_code_order"], [record["pattern_code"] for record in self.records if record["mode"] == "A"])
        for record in self.records:
            self.assertEqual(record["source_event_count"], 32)
            fields = record["schema1_fields"]
            expected_page = 2 + (record["set_number"] - 1) * 2 + (1 if record["mode"] == "B" else 0)
            self.assertEqual(record["source_refs"][1], f"L6-PDF1-p{expected_page}")
            self.assertEqual(record["source_refs"][2:], ["L6-TXT1-1-23", "L6-PDF1-p1"])
            self.assertEqual(fields["source_refs"], record["source_refs"])
            self.assertEqual(len(fields["events"]), 32)
            self.assertTrue(record["source_refs"][0].startswith("L6-TXT1-"))
            self.assertTrue(all(event["source_local_provenance"]["source_txt_ref"] == record["source_refs"][0]
                                and event["source_local_provenance"]["source_pdf_page"] == expected_page
                                for event in fields["events"]))

    def test_non_admission_and_timing_are_explicitly_unassigned(self) -> None:
        proposal = self.proposal
        for field in ("schema1_importable", "canonical_schema_validated", "whole_workbook_complete", "runtime_eligible", "admitted", "canonical_ids_allocated"):
            self.assertIs(proposal[field], False)
        self.assertEqual(proposal["identity_assignment"], "unassigned")
        self.assertEqual(self.handoff["wbs_parent_status"], "Pending")
        self.assertIs(self.handoff["catalog_key_is_allocated_canonical_identity"], False)
        for record in proposal["records"]:
            fields = record["schema1_fields"]
            for key in ("id", "workbook_id", "module_id", "content_revision", "lineage"):
                self.assertIsNone(fields[key])
            for key in ("unit", "meter", "fixed_bpm", "note_per_click", "onset_q", "duration_q", "active_grouping"):
                self.assertIsNone(fields["timing"][key])
            self.assertEqual(fields["variants"], [])
            self.assertIsNone(fields["rubric"])
            self.assertEqual(fields["resource_requirements"], [])
            for event in fields["events"]:
                self.assertIsNone(event["event_id"])
                self.assertIsNone(event["onset_q"])
                self.assertIsNone(event["duration_q"])

    def test_every_event_matches_sealed_p04_source_projection(self) -> None:
        p04_records = []
        for pin in lane.P04_CANDIDATES:
            candidate = json.loads(lane.pinned_bytes(ROOT, pin))
            p04_records.extend(candidate["records"])
        self.assertEqual(len(p04_records), 216)
        self.assertEqual([record["source_local_case_key"] for record in p04_records],
                         [record["source_local_case_key"] for record in self.proposal["records"]])
        for reference, generated in zip(p04_records, self.proposal["records"], strict=True):
            self.assertEqual(reference["source_refs"], generated["source_refs"])
            self.assertEqual(len(reference["events"]), 32)
            for reference_event, generated_event in zip(reference["events"], generated["schema1_fields"]["events"], strict=True):
                provenance = generated_event["source_local_provenance"]
                self.assertEqual(reference_event["source_local_event_key"], provenance["source_local_event_key"])
                self.assertEqual(reference_event["source_direction"], provenance["direction"])
                for key in ("source_cell_order", "source_note_order_in_cell", "source_pair", "source_string", "source_fret", "source_digit", "source_finger_assignment", "silent_intervening_string"):
                    reference_value = reference_event[key]
                    proposal_value = provenance[key]
                    if key == "source_digit":
                        reference_value = str(reference_value)
                    self.assertEqual(reference_value, proposal_value)
                self.assertEqual(reference_event["derived_pitch"]["midi"], generated_event["midi"])

    def test_p06_index_and_p11_draft_confirm_same_whole_level_boundary(self) -> None:
        p06 = json.loads(lane.pinned_bytes(ROOT, lane.P06_INDEX))
        p11 = json.loads(lane.pinned_bytes(ROOT, lane.P11_DRAFT))
        proposal_keys = [record["source_local_case_key"] for record in self.proposal["records"]]
        self.assertEqual([record["source_local_case_key"] for record in p06["records"]], proposal_keys)
        self.assertEqual([record["event_count"] for record in p06["records"]], [32] * 216)
        self.assertEqual([record["source_local_case_key"] for record in p11["records"]], proposal_keys)
        for record in p11["records"]:
            self.assertIs(record["admitted"], False)
            self.assertIs(record["runtime_eligible"], False)
            self.assertIs(record["canonical_schema_validated"], False)
            for value in record["schema_slots"].values():
                self.assertIsNone(value)
            self.assertEqual(len(record["source_projection"]["events"]), 32)

    def test_deterministic_twin_outputs_are_identical(self) -> None:
        outputs = lane.rendered_outputs(ROOT)
        self.assertEqual(outputs["field-proposal-a.json"], outputs["field-proposal-b.json"])
        a = json.loads(outputs["field-proposal-a.json"])
        b = json.loads(outputs["field-proposal-b.json"])
        self.assertEqual(a, b)
        lane.validate_non_admission(a)

    def test_changed_printed_fret_and_route_refuse(self) -> None:
        original = lane.pinned_bytes(ROOT, next(pin for pin in lane.PINS if pin["path"] == lane.TXT_REL.as_posix()))
        changed_fret = original.replace(b"G|--------|------6-|--------|5-6-5---|", b"G|--------|------6-|--------|5-7-5---|", 1)
        self.assertNotEqual(changed_fret, original)
        with self.assertRaisesRegex(lane.ProposalError, "TAB_CELL_CODE_ORDER"):
            lane.parse_source(changed_fret)
        changed_route = original.replace(b"ASCEND - E-D, A-G, D-B, G-e", b"ASCEND - E-D, A-G, D-B, G-A", 1)
        with self.assertRaisesRegex(lane.ProposalError, "ASCENDING_ROUTE_LABEL"):
            lane.parse_source(changed_route)

    def test_invented_identity_timing_or_admission_refuses(self) -> None:
        mutations = (
            ("identity", lambda p: p["records"][0]["schema1_fields"].__setitem__("id", "fg:item:invented")),
            ("timing", lambda p: p["records"][0]["schema1_fields"]["events"][0].__setitem__("onset_q", 0)),
            ("admission", lambda p: p["records"][0].__setitem__("admitted", True)),
        )
        for name, mutate in mutations:
            with self.subTest(name=name):
                altered = copy.deepcopy(self.proposal)
                mutate(altered)
                with self.assertRaises(lane.ProposalError):
                    lane.validate_non_admission(altered)


if __name__ == "__main__":
    unittest.main()
