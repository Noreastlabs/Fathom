import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel12_level048_schema1_unallocated as proposal


class Level48UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preserved, cls.fields, cls.handoff = proposal.build()
        cls.candidate = json.loads((ROOT / proposal.CANDIDATE_A).read_text())

    def test_all_original_text_and_pdf_pages_preserved(self):
        txt_raw = (ROOT / proposal.p04.TXT_REL).read_bytes()
        pdf_raw = (ROOT / proposal.p04.PDF_REL).read_bytes()
        proposal.verify_preservation(self.preserved, txt_raw, pdf_raw)
        source = self.preserved["source_candidate"]
        self.assertEqual(source["txt_source"]["raw_text"].encode(), txt_raw)
        self.assertEqual(len(source["txt_source"]["lines"]), 1246)
        reader = PdfReader(ROOT / proposal.p04.PDF_REL, strict=True)
        self.assertEqual([page["extracted_text"] for page in source["pdf_source"]["pages"]],
                         [page.extract_text() or "" for page in reader.pages])
        self.assertEqual([page["page"] for page in source["pdf_source"]["pages"]],
                         list(range(1, 23)))

    def test_sections_cells_rows_and_authored_counts(self):
        counts = proposal.verify_projection(self.preserved, self.fields, self.handoff, self.candidate)
        self.assertEqual((counts["section_cases"], counts["notation_cell_cases"],
                          counts["projected_events"], counts["projected_variants"]), (14, 76, 0, 0))
        self.assertEqual(self.fields["authored_counts"]["total"]["sounding_tones"], 614)
        self.assertEqual(self.fields["authored_counts"]["total"]["pick_attacks"], 517)
        sections = self.fields["records"][:14]
        cells = self.fields["records"][14:]
        self.assertEqual([record["source_section"] for record in sections],
                         self.candidate["source_coverage"]["sections_in_source_order"])
        self.assertEqual([record["source_cell"] for record in cells], self.candidate["txt_notation_cells"])
        self.assertEqual([record["cell_ordinal"] for record in cells], list(range(1, 77)))
        for record in cells:
            context = record["schema1_fields"]["context"]
            self.assertEqual(context["source_rows"], record["source_cell"]["rows"])
            self.assertEqual(len(context["source_tab_rows"]), 6)
            self.assertTrue(context["source_note_row"].startswith("Nte|"))
            self.assertTrue(context["source_degree_row"].startswith("Deg|"))

    def test_independent_forms_and_five_differences_retained(self):
        coverage = self.candidate["source_coverage"]
        self.assertEqual(coverage["txt_table_row_counts"], proposal.p04.EXPECTED_TXT_COUNTS)
        self.assertEqual(coverage["pdf_extracted_table_row_counts"], proposal.p04.EXPECTED_PDF_COUNTS)
        self.assertEqual((coverage["txt_tab_row_count"], coverage["pdf_extracted_tab_row_count"]),
                         (456, 438))
        self.assertEqual([entry["id"] for entry in self.fields["source_difference_ledger"]],
                         ["notation-row-coverage", "module-j-three-recovery-grids",
                          "txt-only-core-written-counts", "rubric-wording-and-authored-counts",
                          "next-section-map-history"])
        self.assertIsNone(self.fields["source_precedence_selected"])
        self.assertTrue(all(record["schema1_fields"]["rubric"] is None
                            for record in self.fields["records"]))

    def test_selected_representative_is_read_only_and_degree_shape(self):
        representative = self.fields["selected_representative_read_only"]
        self.assertEqual(representative["id"], "fg:item:000007")
        self.assertEqual(representative["control_scope"]["extent"], "selected_illustration")
        self.assertEqual(representative["overlapping_new_source_cells"],
                         ["L48-cell-001", "L48-cell-002"])
        self.assertEqual(self.fields["current659_level48_records"], 1)
        self.assertEqual(self.fields["representative_collision"], "fg:item:000007")
        package = json.loads((ROOT / proposal.PACKAGE).read_text())
        selected = [record for record in package["records"] if record.get("legacy_level") == 48][0]
        self.assertEqual(proposal.sha(proposal.encode(selected)), representative["record_sha256"])
        proposal.verify_degree_contexts_shape(selected["events"])
        self.assertEqual(sum(event["kind"] == "rest" and event.get("degree_contexts") is None
                             for event in selected["events"]), 4)
        with self.assertRaisesRegex(proposal.ProposalError, "DEGREE_CONTEXTS_SHAPE"):
            proposal.verify_degree_contexts_shape([{"kind": "note", "degree_contexts": []}])

    def test_deterministic_bytes_and_saved_outputs(self):
        again = proposal.build()
        for name, value, rebuilt in zip(
                ("source-preservation.json", "field-proposal.json", "allocation-handoff.json"),
                (self.preserved, self.fields, self.handoff), again, strict=True):
            self.assertEqual(proposal.encode(rebuilt), proposal.encode(value))
            self.assertEqual((ROOT / proposal.OUT / name).read_bytes(), proposal.encode(value))

    def test_source_and_preservation_drift_refused(self):
        for mutation in (lambda x: x["txt_notation_cells"].pop(),
                         lambda x: x["txt_notation_cells"][0]["rows"][0].update(raw="Cnt|tampered"),
                         lambda x: x["source_difference_ledger"].pop(),
                         lambda x: x["identity_state"].update(preexisting_source_map_representative_reference_only="fg:item:999999")):
            changed = copy.deepcopy(self.candidate)
            mutation(changed)
            with self.assertRaisesRegex(proposal.ProposalError, "P04_SOURCE_CANDIDATE_DRIFT"):
                proposal.build(candidate_override=changed)
        txt_raw = (ROOT / proposal.p04.TXT_REL).read_bytes()
        pdf_raw = (ROOT / proposal.p04.PDF_REL).read_bytes()
        changed = copy.deepcopy(self.preserved)
        changed["source_candidate"]["txt_source"]["raw_text"] = ""
        with self.assertRaisesRegex(proposal.ProposalError, "SOURCE_PRESERVATION_DRIFT"):
            proposal.verify_preservation(changed, txt_raw, pdf_raw)
        changed = copy.deepcopy(self.preserved)
        changed["source_candidate"]["pdf_source"]["pages"][18]["extracted_text"] = ""
        with self.assertRaisesRegex(proposal.ProposalError, "PDF_PAGE_TEXT_DRIFT"):
            proposal.verify_preservation(changed, txt_raw, pdf_raw)

    def test_identity_timing_degree_and_input_pin_refused(self):
        changed = copy.deepcopy(self.fields)
        changed["records"][14]["schema1_fields"]["id"] = "fg:item:000007"
        with self.assertRaisesRegex(proposal.ProposalError, "INVALID_AUTHORITY"):
            proposal.verify_projection(self.preserved, changed, self.handoff, self.candidate)
        changed = copy.deepcopy(self.fields)
        changed["records"][14]["schema1_fields"]["context"]["unresolved_degree_contexts"] = []
        with self.assertRaisesRegex(proposal.ProposalError, "INVALID_AUTHORITY"):
            proposal.verify_projection(self.preserved, changed, self.handoff, self.candidate)
        changed = copy.deepcopy(self.fields)
        changed["records"][14]["schema1_fields"]["events"] = [
            {"kind": "note", "degree_contexts": {}, "onset_q": [0, 1]}]
        with self.assertRaisesRegex(proposal.ProposalError, "INVALID_AUTHORITY"):
            proposal.verify_projection(self.preserved, changed, self.handoff, self.candidate)
        changed = copy.deepcopy(self.handoff)
        changed["cell_source_map"][0]["source_local_key"] = "L48-cell-002"
        with self.assertRaisesRegex(proposal.ProposalError, "SOURCE_CASE_ORDER"):
            proposal.verify_projection(self.preserved, self.fields, changed, self.candidate)
        with patch.dict(proposal.PINS, {proposal.CANDIDATE_A: (498914, "0" * 64)}):
            with self.assertRaisesRegex(proposal.ProposalError, "INPUT_DRIFT"):
                proposal.pin()


if __name__ == "__main__":
    unittest.main()
