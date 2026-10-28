"""Focused Level74 explicit-contact, count-backed and identity-boundary checks."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tools"))

from parallel10_level074_schema1_unallocated import (  # noqa: E402
    ROOT, digest, encoded, pinned, positioned_events, project, read_inputs,
)
from curriculum_level074_whole_candidate import COUNTS  # noqa: E402


class Level74UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate, cls.foundation, cls.registry = read_inputs(ROOT)
        cls.proposal, cls.handoff = project(cls.candidate, cls.foundation, cls.registry)

    def test_exact_explicit_contact_projection(self) -> None:
        self.assertEqual(self.proposal["counts"], {"provisional_components": 8,
            "source_tasks": 51, "printed_contacts": 1168,
            "individual_event_fields": 932, "printed_pitch_events": 858,
            "unspecified_pitch_events": 74, "count_backed_contacts_without_grid": 236})
        self.assertEqual([r["source_component"] for r in self.proposal["records"]], list("ABCDEFGH"))
        for letter in "ABCDEFGH":
            tasks = self.candidate["modules"][letter]
            record = self.proposal["records"][ord(letter) - ord("A")]
            fields = record["schema1_fields"]
            expected = [event for task in tasks for event in (positioned_events(task) or [])]
            self.assertEqual([e["source_event"] for e in fields["events"]], expected)
            self.assertEqual([e["source_local_ordinal"] for e in fields["events"]],
                             list(range(1, len(expected) + 1)))
            self.assertEqual(sum(task["notated_contacts"] for task in tasks), COUNTS[letter])
            self.assertEqual(len(fields["variants"]), len(tasks))
            self.assertIsNone(fields["id"])
            self.assertIsNone(fields["lineage"])
            self.assertIsNone(fields["timing"]["fixed_bpm"])
            for event in fields["events"]:
                self.assertIsNone(event["schema1_fields"]["event_id"])
                self.assertIsNone(event["schema1_fields"]["pick"])
                self.assertIsNone(event["schema1_fields"]["pitch_binding"])
                self.assertIsNone(event["schema1_fields"]["onset_q"])
                self.assertIsNone(event["schema1_fields"]["duration_q"])
                self.assertIsNone(event["performed_member_pitches"])
        self.assertFalse(self.proposal["schema1_importable"])
        self.assertFalse(self.proposal["admitted"])

    def test_count_backed_and_unknown_pitch_stay_unfilled(self) -> None:
        d, h = self.proposal["records"][3], self.proposal["records"][7]
        self.assertEqual([t["printed_contact_count"] for t in d["count_backed_tasks"]], [18, 18])
        self.assertEqual([t["printed_contact_count"] for t in h["count_backed_tasks"]], [48, 80, 32, 40])
        self.assertEqual(len(h["schema1_fields"]["events"]), 0)
        self.assertTrue(all(t["individual_events"] is None for t in d["count_backed_tasks"] + h["count_backed_tasks"]))
        self.assertTrue(all(v["source_event_ordinals"] is None for v in h["schema1_fields"]["variants"]))
        c = self.proposal["records"][2]["schema1_fields"]["events"]
        unknown = [e for e in c if e["source_event"]["pitch"] is None]
        self.assertEqual(len(unknown), 74)
        self.assertTrue(all(e["source_event"]["fret_contact"] is None for e in unknown))
        self.assertEqual([bar["bar"] for task in h["count_backed_tasks"] for bar in task["source_task"]["bar_plan"]],
                         list(range(1, 17)))

    def test_representative_and_pdf_exceptions(self) -> None:
        self.assertEqual(self.proposal["existing_representative_item_id"], "fg:item:000010")
        self.assertEqual(self.handoff["existing_level074_records"], 1)
        self.assertEqual(self.handoff["existing_level074_workbook_entities"], 1)
        self.assertEqual([x["task"] for x in self.proposal["workload_exceptions"]],
                         ["E5-E8", "C7", "F3", "H close"])
        self.assertIn("outside printed 200-contact capstone", self.proposal["workload_exceptions"][3]["ledger_effect"])
        self.assertIn("+2 BPM", self.proposal["uncertainty_ledger"][-1]["status"])
        self.assertEqual(len(self.proposal["txt_source_lines"]), 429)
        self.assertEqual(len(self.proposal["pdf_source_pages"]), 20)
        d = self.proposal["records"][3]["schema1_fields"]["events"]
        self.assertEqual(sum(e["source_event"].get("voice") == "lower" for e in d), 28)
        self.assertEqual(sum(e["source_event"].get("voice") == "upper" for e in d), 40)

    def test_source_count_and_authority_refusals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.txt").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "input drift"):
                pinned(root, "source.txt", "0" * 64)
        candidate = copy.deepcopy(self.candidate)
        candidate["notated_contacts"] = 1169
        with self.assertRaisesRegex(ValueError, "1168/932/236"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["modules"]["C"][2]["events"][0]["pitch"] = "A"
        with self.assertRaisesRegex(ValueError, "whole-Level74 contact/task separation"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["modules"]["H"][0]["events"] = [{"pitch": "C"}]
        with self.assertRaisesRegex(ValueError, "positioned source-event count"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["new_canonical_ids_assigned"] = True
        with self.assertRaisesRegex(ValueError, "source/admission"):
            project(candidate, self.foundation, self.registry)

    def test_identity_boundary_and_determinism(self) -> None:
        foundation = copy.deepcopy(self.foundation)
        foundation["records"].append({"legacy_level": 74, "workbook_id": "fg:workbook:000074", "id": "fg:item:new"})
        with self.assertRaisesRegex(ValueError, "frozen representative"):
            project(self.candidate, foundation, self.registry)
        registry = copy.deepcopy(self.registry)
        registry["entities"] = [e for e in registry["entities"] if e.get("id") != "fg:item:000010"]
        with self.assertRaisesRegex(ValueError, "existing registry"):
            project(self.candidate, self.foundation, registry)
        again, handoff = project(self.candidate, self.foundation, self.registry)
        self.assertEqual(encoded(again), encoded(self.proposal))
        self.assertEqual(encoded(handoff), encoded(self.handoff))
        self.assertEqual(digest(encoded(again)), digest(encoded(self.proposal)))


if __name__ == "__main__":
    unittest.main()
