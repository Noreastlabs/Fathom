import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel12_level042_schema1_unallocated as proposal


class Level42UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preserved, cls.fields, cls.handoff = proposal.build()
        cls.candidate = json.loads((ROOT / proposal.CANDIDATE_A).read_text())

    def test_all_original_text_and_pdf_pages_preserved(self):
        txt_raw = (ROOT / proposal.p08.TXT_REL).read_bytes()
        pdf_raw = (ROOT / proposal.p08.PDF_REL).read_bytes()
        proposal.verify_preservation(self.preserved, txt_raw, pdf_raw)
        self.assertEqual(self.preserved["source"]["txt_text"].encode(), txt_raw)
        self.assertEqual(len(self.preserved["source"]["txt_text"].splitlines()), 473)
        reader = PdfReader(ROOT / proposal.p08.PDF_REL, strict=True)
        self.assertEqual([page["text"] for page in self.preserved["source"]["pdf_pages"]],
                         [page.extract_text() or "" for page in reader.pages])
        self.assertEqual([page["page"] for page in self.preserved["source"]["pdf_pages"]],
                         list(range(1, 19)))

    def test_all_modules_source_order_geometry_and_attack_counts(self):
        counts = proposal.verify_projection(self.preserved, self.fields, self.handoff, self.candidate)
        self.assertEqual((counts["cases"], counts["counted_sounding_events"],
                          counts["pick_attacks"], counts["projected_event_units"]),
                         (91, 668, 428, 645))
        for record in self.fields["records"]:
            module, index = record["module"], record["module_item"]
            source = self.candidate["modules"][module][index - 1]
            self.assertEqual(record["source_item"], source)
            self.assertEqual(record["schema1_fields"]["context"]["source_item"], source)
            if module in "ABCDE":
                events = record["schema1_fields"]["events"]
                self.assertEqual([(event["string"], event["fret"], event["midi"],
                                   event["spelling"], event["articulation"], event["pick_attack"])
                                  for event in events],
                                 [(proposal.STRING_NUMBER[note["string"]], note["fret"],
                                   proposal.OPEN_MIDI[note["string"]] + note["fret"],
                                   note["note"], note["articulation"], note["pick_attack"])
                                  for note in source["events"]])
            self.assertEqual(sum(event["pick_attack"] for event in record["schema1_fields"]["events"]),
                             record["source_pick_attacks"])
        self.assertEqual(self.fields["counts"]["module_cases"], proposal.ITEM_COUNTS)
        self.assertEqual(self.fields["source_lanes"], self.candidate["lanes"])

    def test_slide_bend_blue_ceiling_and_aggregate_cadences(self):
        by_module = {module: [record for record in self.fields["records"] if record["module"] == module]
                     for module in "ABCDEFGH"}
        for module in "CE":
            for record in by_module[module]:
                for event in record["schema1_fields"]["events"]:
                    if event["articulation"].startswith("slide_"):
                        self.assertFalse(event["pick_attack"])
                        self.assertIsNone(event["onset_q"])
        for record in by_module["F"]:
            self.assertEqual(len(record["schema1_fields"]["events"]), 5)
            self.assertEqual(record["source_pick_attacks"], 4)
            self.assertTrue(all(event["midi"] is event["fret"] is None
                                for event in record["schema1_fields"]["events"]))
        shades = [record for record in by_module["F"] if record["source_item"]["kind"] == "blue_third"]
        self.assertEqual(len(shades), 4)
        self.assertTrue(all(not record["source_item"]["target_is_pentatonic_degree"] for record in shades))
        self.assertTrue(all(record["schema1_fields"]["events"][2]["source_pitch_label"] == "between C and C#"
                            for record in shades))
        self.assertEqual(self.fields["source_blue_third"]["C_sharp_is_pentatonic_degree"], False)
        self.assertEqual([record["source_counted_sounding_events"] for record in by_module["H"]],
                         [8, 8, 9, 9, 9])
        for record in by_module["H"]:
            events = record["schema1_fields"]["events"]
            self.assertEqual(len(events), 4)
            self.assertEqual(sum(event["source_counted_sounding_events"] for event in events),
                             record["source_counted_sounding_events"])
            self.assertTrue(all(event["kind"] == "unresolved_articulation_group" and
                                event["midi"] is event["onset_q"] is None for event in events))

    def test_source_map_variants_current659_and_unallocated_state(self):
        self.assertEqual(len(self.handoff["source_map"]), 91)
        self.assertEqual([record["source_local_key"] for record in self.fields["records"]],
                         [f"L42-{module}-{index:02d}" for module in "ABCDEFGH"
                          for index in range(1, proposal.ITEM_COUNTS[module] + 1)])
        self.assertEqual(self.fields["current659_level42_records"], 0)
        self.assertFalse(self.fields["current659_level42_workbook_identity"])
        self.assertIsNone(self.fields["representative_collision"])
        self.assertEqual(self.fields["counts"]["variants"], 182)
        for record in self.fields["records"]:
            self.assertEqual([v["pick_start"] for v in record["schema1_fields"]["variants"]], ["D", "U"])
            self.assertFalse(record["schema1_importable"])
            self.assertTrue(all(event["event_id"] is event["onset_q"] is event["duration_q"] is None
                                for event in record["schema1_fields"]["events"]))

    def test_deterministic_bytes_and_saved_outputs(self):
        again = proposal.build()
        for name, value, rebuilt in zip(
                ("source-preservation.json", "field-proposal.json", "allocation-handoff.json"),
                (self.preserved, self.fields, self.handoff), again, strict=True):
            self.assertEqual(proposal.encode(rebuilt), proposal.encode(value))
            self.assertEqual((ROOT / proposal.OUT / name).read_bytes(), proposal.encode(value))

    def test_candidate_and_preservation_drift_refused(self):
        for mutation in (lambda x: x["modules"]["A"].pop(),
                         lambda x: x["lanes"][0]["positions"][0].update(fret=6),
                         lambda x: x["modules"]["F"][9]["events"][2].update(pitch_label="C#"),
                         lambda x: x["modules"]["H"][0]["groups"][2].update(counted_sounding_events=3)):
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
        changed["source"]["pdf_pages"][16]["text"] = ""
        with self.assertRaisesRegex(proposal.ProposalError, "PDF_PAGE_TEXT_DRIFT"):
            proposal.verify_preservation(changed, txt_raw, pdf_raw)

    def test_identity_timing_attack_order_and_input_pin_refused(self):
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["id"] = "fg:item:999999"
        with self.assertRaisesRegex(proposal.ProposalError, "INVALID_AUTHORITY"):
            proposal.verify_projection(self.preserved, changed, self.handoff, self.candidate)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["events"][0]["onset_q"] = [0, 1]
        with self.assertRaisesRegex(proposal.ProposalError, "SOURCE_GEOMETRY_OR_ATTACK_DRIFT"):
            proposal.verify_projection(self.preserved, changed, self.handoff, self.candidate)
        changed = copy.deepcopy(self.fields)
        changed["records"][12]["schema1_fields"]["events"][2]["pick_attack"] = True
        with self.assertRaisesRegex(proposal.ProposalError, "SOURCE_GEOMETRY_OR_ATTACK_DRIFT"):
            proposal.verify_projection(self.preserved, changed, self.handoff, self.candidate)
        changed = copy.deepcopy(self.handoff)
        changed["source_map"][0]["module_item"] = 2
        with self.assertRaisesRegex(proposal.ProposalError, "SOURCE_CASE_ORDER"):
            proposal.verify_projection(self.preserved, self.fields, changed, self.candidate)
        with patch.dict(proposal.PINS, {proposal.CANDIDATE_A: (272845, "0" * 64)}):
            with self.assertRaisesRegex(proposal.ProposalError, "INPUT_DRIFT"):
                proposal.pin()


if __name__ == "__main__":
    unittest.main()
