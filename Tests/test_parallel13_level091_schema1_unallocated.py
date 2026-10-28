"""Focused Level91 detached schema1 projection and refusal checks."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel13_level091_schema1_unallocated as proposal  # noqa: E402


class Level91ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        proposal.check_pins()
        proposal.foundation_status()
        cls.original = proposal.source.build(ROOT)
        cls.candidate = json.loads((ROOT / proposal.CANDIDATE).read_text())
        cls.output = proposal.project(cls.candidate, cls.original)

    def test_whole_source_replay_and_source_hashes(self) -> None:
        self.assertEqual(self.candidate, self.original)
        self.assertEqual(hashlib.sha256((ROOT / proposal.CANDIDATE).read_bytes()).hexdigest(),
                         proposal.PINS[proposal.CANDIDATE])
        self.assertEqual(len(self.output["source_context"]["txt_lines"]), 37)
        pages = self.output["source_context"]["pdf_pages"]
        self.assertEqual(len(pages), 17)
        for page in pages:
            self.assertEqual(hashlib.sha256(page["extracted_text"].encode()).hexdigest(),
                             page["extracted_text_sha256"])
        for row in self.output["rows"] + self.output["supporting_rows"]:
            page = pages[row["source_provenance"]["pdf_page"] - 1]
            self.assertEqual(row["source_provenance"]["pdf_extracted_text_sha256"],
                             page["extracted_text_sha256"])

    def test_module_totals_and_no_fabricated_events(self) -> None:
        self.assertEqual(self.output["module_task_row_count"], 98)
        self.assertEqual(self.output["supporting_row_count"], 12)
        self.assertEqual({m["source_module"]: m["declared_events"]
                          for m in self.output["modules"]}, proposal.MODULE_EVENTS)
        self.assertEqual(self.output["declared_total_events"], 1424)
        self.assertEqual(self.output["playable_event_count"], 0)
        for row in self.output["rows"] + self.output["supporting_rows"]:
            self.assertIsNone(row["printed_event_allocation"])
            fields = row["schema1_fields"]
            self.assertEqual(fields["events"], [])
            self.assertEqual(fields["variants"], [])
            for key in ("id", "workbook_id", "module_id", "lineage", "content_revision",
                        "pitch", "route", "bend_curve"):
                self.assertIsNone(fields[key])
            self.assertFalse(fields["runtime_eligible"])
            self.assertEqual(fields["timing"],
                             {"status": "unresolved", "onset_q": None,
                              "duration_q": None, "fixed_bpm": None})

    def test_c_unison_is_literal_and_support_is_separate(self) -> None:
        c = [r for r in self.output["rows"] if r["source_module"] == "C"]
        self.assertEqual(len(c), 12)
        self.assertEqual([r["source_row"]["fields"] for r in c[:6]],
                         [t["fields"] for t in self.candidate["modules"][2]["tasks"][:6]])
        self.assertEqual({r["source_provenance"]["pdf_page"] for r in c[:6]}, {6})
        self.assertEqual({r["source_module"] for r in self.output["supporting_rows"]}, {None})
        timed = [r for r in self.output["supporting_rows"]
                 if r["source_provenance"]["pdf_page"] == 4]
        self.assertEqual(len(timed), 6)
        self.assertEqual({r["support_relation"] for r in timed},
                         {"adjacent_unallocated_timed_arrival_reference"})

    def test_h_i_j_and_mastery_source_criteria(self) -> None:
        rows = self.output["rows"]
        h = [r["source_row"] for r in rows if r["source_module"] == "H"]
        self.assertEqual(len(h), 24)
        self.assertEqual({r["study"] for r in h}, {1, 2, 3, 4})
        for study in range(1, 5):
            group = [r for r in h if r["study"] == study]
            self.assertEqual([r["pass"] for r in group], list(range(1, 7)))
            self.assertEqual(len({r["harmony"] for r in group}), 1)
            self.assertEqual(len({r["focus"] for r in group}), 1)
        i = [r["source_row"]["fields"]["Bars"] for r in rows if r["source_module"] == "I"]
        self.assertEqual(i, [f"{s}-{s+3}" for s in range(1, 33, 4)])
        self.assertIn("One master tempo", self.output["source_context"]["pdf_pages"][15]["extracted_text"])
        j = [r["source_row"]["fields"] for r in rows if r["source_module"] == "J"]
        self.assertEqual(len(j), 8)
        self.assertTrue(all(set(x) == {"Failure", "Repair"} for x in j))
        mastery = self.output["source_context"]["mastery"]
        self.assertEqual(mastery["minimum"], "14/16 or better on two separate days")
        self.assertEqual(mastery["protected_zero_domains"],
                         ["bend intonation", "vibrato control", "pulse", "recovery"])

    def test_refuse_modified_row_or_event_total(self) -> None:
        for mutate in (
            lambda c: c["modules"][2]["tasks"][0]["fields"].update(Goal="invented"),
            lambda c: c["modules"][0].update(declared_events=145),
            lambda c: c["modules"][0]["tasks"][0].update(declared_event_count_for_row=18),
        ):
            bad = copy.deepcopy(self.candidate)
            mutate(bad)
            with self.assertRaises(proposal.ProposalError):
                proposal.project(bad, self.original)

    def test_refuse_support_reassignment_mastery_or_admission(self) -> None:
        for mutate in (
            lambda c: c["supporting_tables"][1].update(relation="module_A_task"),
            lambda c: c["mastery"].update(minimum="12/16"),
            lambda c: c.update(runtime_eligible=True),
            lambda c: c["modules"][8]["tasks"][0]["fields"].update(Bars="2-5"),
        ):
            bad = copy.deepcopy(self.candidate)
            mutate(bad)
            with self.assertRaises(proposal.ProposalError):
                proposal.project(bad, self.original)

    def test_refuse_projection_byte_drift(self) -> None:
        self.assertEqual(proposal.encoded(self.output), proposal.encoded(
            proposal.project(self.candidate, self.original)))
        altered = copy.deepcopy(self.output)
        altered["rows"][0]["schema1_fields"]["events"] = [{"invented": True}]
        self.assertNotEqual(proposal.encoded(self.output), proposal.encoded(altered))


if __name__ == "__main__":
    unittest.main()
