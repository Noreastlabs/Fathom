import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel12_level023_source_preservation_schema1 as proposal


class Level23SourcePreservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preserved, cls.fields, cls.handoff = proposal.build()
        cls.candidate = json.loads((ROOT / proposal.CANDIDATE).read_text())

    def test_complete_original_text_and_all_pdf_pages_preserved(self):
        txt_raw = (ROOT / proposal.p08.TXT_REL).read_bytes()
        pdf_raw = (ROOT / proposal.p08.PDF_REL).read_bytes()
        proposal.verify_preservation(self.preserved, txt_raw, pdf_raw)
        self.assertEqual(self.preserved["source"]["txt_text"].encode(), txt_raw)
        self.assertEqual(len(self.preserved["source"]["txt_text"].splitlines()), 275)
        reader = PdfReader(ROOT / proposal.p08.PDF_REL, strict=True)
        self.assertEqual([p["text"] for p in self.preserved["source"]["pdf_pages"]],
                         [page.extract_text() or "" for page in reader.pages])
        self.assertEqual([p["page"] for p in self.preserved["source"]["pdf_pages"]],
                         list(range(1, 8)))

    def test_rungs_printed_rows_groups_notes_and_final_footer(self):
        self.assertEqual(proposal.verify_projection(self.preserved, self.fields, self.handoff)["events"], 468)
        for record, card in zip(self.fields["records"], self.candidate["records"], strict=True):
            events = record["schema1_fields"]["events"]
            self.assertEqual(record["source_printed_txt"], card["printed_txt"])
            self.assertEqual(record["source_printed_pdf"], card["printed_pdf"])
            self.assertEqual(record["source_group_details"], card["groups"])
            self.assertEqual(len(events), 36)
            self.assertEqual([e["midi"] for e in events],
                             [proposal.OPEN[n["string"]][1] + n["fret"]
                              for group in card["groups"] for n in group["notes"]])
            self.assertEqual(events[17]["midi"], events[18]["midi"])
            self.assertEqual([g["event_local_ordinals"] for g in record["group_memberships"]],
                             [list(range(i * 3 + 1, i * 3 + 4)) for i in range(12)])
        distinction = self.preserved["source_distinctions"][0]
        self.assertNotEqual(distinction["txt"], distinction["pdf"])
        self.assertEqual(distinction["txt"], self.candidate["records"][-1]["printed_txt"]["footer"])
        self.assertEqual(distinction["pdf"], self.candidate["records"][-1]["printed_pdf"]["footer"])

    def test_route_and_current659_gap(self):
        route = self.handoff["routes"]
        self.assertEqual(len(route["continuous_round_trip"]), 25)
        self.assertEqual(route["continuous_round_trip"].count("L23-rung13"), 1)
        self.assertEqual(route["down_landmarks"][0], "L23-rung13")
        self.assertEqual(route["down_return"][0], "L23-rung12")
        self.assertEqual(self.fields["counts"]["round_trip_contact_traversals"], 900)
        self.assertEqual(self.fields["current659_level23_records"], 0)
        self.assertFalse(self.fields["current659_level23_workbook_identity"])
        self.assertIsNone(self.fields["representative_collision"])

    def test_deterministic_bytes_and_saved_outputs(self):
        again = proposal.build()
        for name, value, rebuilt in zip(
                ("source-preservation.json", "field-proposal.json", "allocation-handoff.json"),
                (self.preserved, self.fields, self.handoff), again, strict=True):
            self.assertEqual(proposal.encode(rebuilt), proposal.encode(value))
            self.assertEqual((ROOT / proposal.OUT / name).read_bytes(), proposal.encode(value))

    def test_source_and_preservation_drift_refused(self):
        for mutation in (lambda x: x["records"].pop(),
                         lambda x: x["records"][0]["groups"][0]["notes"][0].update(fret=6),
                         lambda x: x["records"][-1]["printed_pdf"].update(footer="move one fret"),
                         lambda x: x["neck_route"]["single_turn_cell_sequence"].pop()):
            changed = copy.deepcopy(self.candidate)
            mutation(changed)
            with self.assertRaisesRegex(proposal.ProposalError, "P08_SOURCE_CANDIDATE_DRIFT"):
                proposal.build(candidate_override=changed)
        txt_raw = (ROOT / proposal.p08.TXT_REL).read_bytes()
        pdf_raw = (ROOT / proposal.p08.PDF_REL).read_bytes()
        changed = copy.deepcopy(self.preserved)
        changed["source"]["txt_text"] = changed["source"]["txt_text"][:-1]
        with self.assertRaisesRegex(proposal.ProposalError, "SOURCE_PRESERVATION_DRIFT"):
            proposal.verify_preservation(changed, txt_raw, pdf_raw)
        changed = copy.deepcopy(self.preserved)
        changed["source"]["pdf_pages"][6]["text"] = ""
        with self.assertRaisesRegex(proposal.ProposalError, "PDF_PAGE_TEXT_DRIFT"):
            proposal.verify_preservation(changed, txt_raw, pdf_raw)

    def test_allocation_timing_group_and_route_refused(self):
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["id"] = "fg:item:999999"
        with self.assertRaisesRegex(proposal.ProposalError, "INVALID_AUTHORITY"):
            proposal.verify_projection(self.preserved, changed, self.handoff)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["events"][0]["onset_q"] = [0, 1]
        with self.assertRaisesRegex(proposal.ProposalError, "UNSUPPORTED_TIMING_OR_NOTE"):
            proposal.verify_projection(self.preserved, changed, self.handoff)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["group_memberships"][0]["event_local_ordinals"][0] = 2
        with self.assertRaisesRegex(proposal.ProposalError, "GROUP_MEMBERSHIP"):
            proposal.verify_projection(self.preserved, changed, self.handoff)
        changed = copy.deepcopy(self.handoff)
        changed["routes"]["continuous_round_trip"][13] = "L23-rung13"
        with self.assertRaisesRegex(proposal.ProposalError, "ROUTE_OR_CASE_ORDER"):
            proposal.verify_projection(self.preserved, self.fields, changed)

    def test_input_pin_refusal(self):
        with patch.dict(proposal.PINS, {proposal.CANDIDATE: (279793, "0" * 64)}):
            with self.assertRaisesRegex(proposal.ProposalError, "INPUT_DRIFT"):
                proposal.pin()


if __name__ == "__main__":
    unittest.main()
