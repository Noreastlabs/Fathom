import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel12_level032_schema1_unallocated as proposal


class Level32UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preserved, cls.fields, cls.handoff = proposal.build()
        cls.candidate = json.loads((ROOT / proposal.CANDIDATE).read_text())

    def test_complete_original_text_and_all_pdf_pages_preserved(self):
        txt_raw = (ROOT / proposal.p07.TXT_REL).read_bytes()
        pdf_raw = (ROOT / proposal.p07.PDF_REL).read_bytes()
        proposal.verify_preservation(self.preserved, txt_raw, pdf_raw)
        self.assertEqual(self.preserved["source"]["txt_text"].encode(), txt_raw)
        self.assertEqual(len(self.preserved["source"]["txt_text"].splitlines()), 741)
        reader = PdfReader(ROOT / proposal.p07.PDF_REL, strict=True)
        self.assertEqual([p["text"] for p in self.preserved["source"]["pdf_pages"]],
                         [page.extract_text() or "" for page in reader.pages])
        self.assertEqual([p["page"] for p in self.preserved["source"]["pdf_pages"]],
                         list(range(1, 17)))
        distinction = self.preserved["source_distinctions"][0]
        self.assertNotEqual(distinction["txt"], distinction["pdf"])
        self.assertIn("move one fret", distinction["txt"])
        self.assertIn("continue through rungs 12-01", distinction["pdf"])

    def test_all_rungs_notes_groups_printed_blocks_and_boundaries(self):
        self.assertEqual(proposal.verify_projection(self.preserved, self.fields,
                                                    self.handoff, self.candidate)["events"], 1612)
        for record, card in zip(self.fields["records"], self.candidate["records"], strict=True):
            events = record["schema1_fields"]["events"]
            self.assertEqual(record["source_modules"], card["modules"])
            self.assertEqual(record["source_linked_boundary"], card["linked_boundary"])
            self.assertEqual(len(events), 124)
            self.assertEqual(len(record["group_memberships"]), 32)
            self.assertEqual([event["midi"] for event in events],
                             [proposal.p07.OPEN_MIDI[note["string"]] + note["fret"]
                              for module in card["modules"] for direction in module["directions"]
                              for note in direction["notes"]])
            for a, b in ((26, 27), (53, 54), (88, 89)):
                self.assertEqual((events[a]["string"], events[a]["fret"], events[a]["midi"]),
                                 (events[b]["string"], events[b]["fret"], events[b]["midi"]))
            self.assertEqual([(block["module"], block["direction"], block["source_path_line"],
                               block["source_raw_rows"]) for block in record["source_printed_blocks"]],
                             [(module["module"], direction["direction"], direction["path_line"],
                               direction["raw_rows"]) for module in card["modules"]
                              for direction in module["directions"]])

    def test_group_orientation_variants_and_unresolved_timing(self):
        for record in self.fields["records"]:
            groups = record["group_memberships"]
            self.assertEqual([group["source_D_start_first_stroke"] for group in groups],
                             ["D" if i % 2 == 0 else "U" for i in range(32)])
            self.assertEqual([group["group_size"] for group in groups], [3] * 18 + [5] * 14)
            self.assertEqual([group["event_local_ordinals"] for group in groups],
                             [list(range(i * 3 + 1, i * 3 + 4)) for i in range(18)] +
                             [list(range(55 + i * 5, 60 + i * 5)) for i in range(14)])
            memberships = record["variant_memberships"]
            self.assertEqual([(v["mode"], v["pick_start"]) for v in memberships],
                             [(mode, pick) for mode in ("A", "B", "linked_A_B") for pick in ("D", "U")])
            self.assertEqual([len(v["event_local_ordinals"]) for v in memberships],
                             [54, 54, 70, 70, 124, 124])
            self.assertEqual(memberships[-1]["linked_low_root_ordinals"], [54, 55])
            self.assertTrue(all(event["onset_q"] is event["duration_q"] is None
                                for event in record["schema1_fields"]["events"]))

    def test_route_and_current659_gap(self):
        route = self.handoff["routes"]
        self.assertEqual(len(route["continuous_round_trip"]), 25)
        self.assertEqual(route["continuous_round_trip"].count("L32-rung13"), 1)
        self.assertEqual(route["down_standalone"][0], "L32-rung13")
        self.assertEqual(route["down_return"][0], "L32-rung12")
        self.assertEqual(self.fields["counts"]["round_trip_linked_contact_traversals"], 3100)
        self.assertEqual(self.fields["counts"]["source_grouped_beats_instruction_only"], 800)
        self.assertEqual(self.fields["current659_level32_records"], 0)
        self.assertFalse(self.fields["current659_level32_workbook_identity"])
        self.assertIsNone(self.fields["representative_collision"])

    def test_deterministic_bytes_and_saved_outputs(self):
        again = proposal.build()
        for name, value, rebuilt in zip(
                ("source-preservation.json", "field-proposal.json", "allocation-handoff.json"),
                (self.preserved, self.fields, self.handoff), again, strict=True):
            self.assertEqual(proposal.encode(rebuilt), proposal.encode(value))
            self.assertEqual((ROOT / proposal.OUT / name).read_bytes(), proposal.encode(value))

    def test_candidate_and_preservation_drift_refused(self):
        for mutation in (lambda x: x["records"].pop(),
                         lambda x: x["records"][0]["modules"][0]["directions"][0]["notes"][0].update(fret=6),
                         lambda x: x["records"][0]["modules"][1]["directions"][0]["raw_rows"].__setitem__(0, "tampered"),
                         lambda x: x["routes"]["continuous_round_trip"]["rungs"].pop()):
            changed = copy.deepcopy(self.candidate)
            mutation(changed)
            with self.assertRaisesRegex(proposal.ProposalError, "P07_SOURCE_CANDIDATE_DRIFT"):
                proposal.build(candidate_override=changed)
        txt_raw = (ROOT / proposal.p07.TXT_REL).read_bytes()
        pdf_raw = (ROOT / proposal.p07.PDF_REL).read_bytes()
        changed = copy.deepcopy(self.preserved)
        changed["source"]["txt_text"] = changed["source"]["txt_text"][:-1]
        with self.assertRaisesRegex(proposal.ProposalError, "SOURCE_PRESERVATION_DRIFT"):
            proposal.verify_preservation(changed, txt_raw, pdf_raw)
        changed = copy.deepcopy(self.preserved)
        changed["source"]["pdf_pages"][15]["text"] = ""
        with self.assertRaisesRegex(proposal.ProposalError, "PDF_PAGE_TEXT_DRIFT"):
            proposal.verify_preservation(changed, txt_raw, pdf_raw)

    def test_identity_timing_group_variant_route_and_pin_refused(self):
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["id"] = "fg:item:999999"
        with self.assertRaisesRegex(proposal.ProposalError, "INVALID_AUTHORITY"):
            proposal.verify_projection(self.preserved, changed, self.handoff, self.candidate)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["events"][0]["onset_q"] = [0, 1]
        with self.assertRaisesRegex(proposal.ProposalError, "UNSUPPORTED_TIMING_OR_NOTE"):
            proposal.verify_projection(self.preserved, changed, self.handoff, self.candidate)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["group_memberships"][0]["event_local_ordinals"][0] = 2
        with self.assertRaisesRegex(proposal.ProposalError, "GROUP_MEMBERSHIP"):
            proposal.verify_projection(self.preserved, changed, self.handoff, self.candidate)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["variant_memberships"][4]["linked_low_root_ordinals"] = []
        with self.assertRaisesRegex(proposal.ProposalError, "VARIANT_MEMBERSHIP"):
            proposal.verify_projection(self.preserved, changed, self.handoff, self.candidate)
        changed = copy.deepcopy(self.handoff)
        changed["routes"]["continuous_round_trip"][13] = "L32-rung13"
        with self.assertRaisesRegex(proposal.ProposalError, "ROUTE_OR_CASE_ORDER"):
            proposal.verify_projection(self.preserved, self.fields, changed, self.candidate)
        with patch.dict(proposal.PINS, {proposal.CANDIDATE: (978505, "0" * 64)}):
            with self.assertRaisesRegex(proposal.ProposalError, "INPUT_DRIFT"):
                proposal.pin()


if __name__ == "__main__":
    unittest.main()
