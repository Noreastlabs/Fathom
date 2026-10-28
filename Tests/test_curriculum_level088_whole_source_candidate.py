from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from Tools import curriculum_level088_whole_source_candidate as candidate


class Level88WholeSourceCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = candidate.read_inputs()
        cls.candidate = candidate.build_candidate()

    def test_live_pair_map_catalog_and_pending_status_are_bound(self) -> None:
        self.assertEqual(self.source["root"], candidate.ROOT.resolve())
        self.assertEqual(len(self.source["raw"]), len(candidate.PINNED))
        self.assertEqual(candidate.pypdf.__version__, "6.10.0")
        self.assertEqual(len(self.source["pdf_pages"]), 15)
        self.assertEqual(len(self.source["txt_records"]), 43)
        self.assertEqual(self.source["source_map_row"]["representative_status"], "outside_representative_package")
        self.assertIs(self.source["source_map_row"]["prior_staging_found"], True)
        entry = self.source["catalog_entry"]
        self.assertEqual(entry["review"], "Pending")
        self.assertEqual(entry["conversion_status"], "not_converted")
        for flag in ("runtime_eligible", "runtime_admitted", "imported", "admitted", "whole_workbook_complete"):
            self.assertIs(entry[flag], False)
        self.assertEqual(entry["playable_projection"]["status"], "explicitly_empty_unresolved")
        self.assertIs(self.candidate["current_source_status"]["prior_staging_used"], False)

    def test_all_43_original_txt_lines_retain_exact_unicode_spans(self) -> None:
        txt = self.candidate["txt"]
        self.assertEqual(txt["line_count"], 43)
        self.assertEqual(len(txt["literal_lines"]), 43)
        self.assertEqual(txt["literal_lines"][3]["literal"], "LEVEL 88 OF 105 - HARD STOP AFTER LEVEL 105")
        self.assertEqual(txt["literal_lines"][9]["literal"], "COMPLETE WRITTEN WORKLOAD: 1536 events")
        self.assertEqual(txt["literal_lines"][42]["literal"], "Level 89: country, Americana, and hybrid-picking groove principles.")
        for row in txt["literal_lines"]:
            span = row["source_position"]
            self.assertEqual(self.source["txt_text"][span["start_char"]:span["end_char_exclusive"]], row["literal"])
        self.assertEqual([row["module_label"] for row in txt["modules"]], list("ABCDEFGHIJ"))
        self.assertEqual([row["declared_workload_value"] for row in txt["modules"]], [160, 144, 160, 144, 128, 128, 160, 192, 256, 64])
        self.assertEqual(sum(row["declared_workload_value"] for row in txt["modules"]), 1536)

    def test_pdf_index_titles_and_workloads_match_txt_module_lines(self) -> None:
        index = self.candidate["pdf"]["module_index"]
        self.assertEqual(index["header_literal"], "Module\nExercise\nEvents")
        self.assertEqual(len(index["rows"]), 10)
        self.assertTrue(all(row["titles_exactly_equal"] for row in index["rows"]))
        self.assertTrue(all(row["workloads_exactly_equal"] for row in index["rows"]))
        self.assertEqual([row["module_label"] for row in index["rows"]], list("ABCDEFGHIJ"))
        self.assertEqual(index["declared_total_literal"], "1536")
        self.assertEqual(index["module_workload_sum"], 1536)

    def test_every_pdf_page_matches_live_cache_and_historical_literal_appendix(self) -> None:
        pages = self.candidate["pdf"]["pages"]
        self.assertEqual(len(pages), 15)
        self.assertEqual([page["literal_extracted_text_sha256"] for page in pages], [candidate.EXPECTED_PAGE_HASHES[n] for n in range(1, 16)])
        for number, page in enumerate(pages, 1):
            self.assertEqual(page["literal_extracted_text_sha256"], page["current_catalog_text_sha256"])
            self.assertEqual(page["literal_extracted_text_sha256"], page["historical_appendix_text_sha256"])
            self.assertEqual(page["historical_appendix_reference"]["page_number"], number)
            self.assertEqual(page["historical_appendix_reference"]["page_text_sha256"], page["literal_extracted_text_sha256"])
            self.assertFalse(page["full_pdf_text_embedded"])
            self.assertNotIn("literal_extracted_text", page)
        self.assertEqual(self.candidate["pdf"]["historical_full_literal_page_reference"]["page_count"], 15)

    def test_explicit_headings_map_modules_without_normalizing_source_spelling(self) -> None:
        rows = self.candidate["module_crosswalk"]
        self.assertEqual([row["module_label"] for row in rows], list("ABCDEFGHIJ"))
        self.assertEqual(
            {row["module_label"]: [heading["page_number"] for heading in row["pdf_detail_headings"]] for row in rows},
            {"A": [3], "B": [4], "C": [5], "D": [6], "E": [7], "F": [8], "G": [9], "H": [10, 11, 12, 13], "I": [14], "J": [15]},
        )
        self.assertEqual(rows[0]["pdf_detail_headings"][0]["detail_heading_literal"], "Module A - Eighth-Note Drive and Mute Depth")
        self.assertNotEqual(rows[0]["txt_summary_title_literal"], rows[0]["pdf_detail_headings"][0]["detail_heading_literal"])
        self.assertIn("four separately headed", rows[7]["source_difference_note"])
        self.assertIn("256 events", rows[8]["source_difference_note"])

    def test_pdf_page_roles_and_lexical_coverage_account_for_all_pages(self) -> None:
        pages = self.candidate["pdf"]["pages"]
        self.assertEqual([page["page_number"] for page in pages], list(range(1, 16)))
        self.assertEqual(pages[0]["page_role"], "document-title-and-module-index")
        self.assertEqual(pages[1]["page_role"], "unassigned-reference-page")
        self.assertEqual(pages[1]["module_label_from_printed_heading"], None)
        self.assertEqual(pages[14]["literal_heading"], "Module J - Recovery and Groove Audit")
        self.assertEqual(sum(page["lexical_coverage"]["classification"] == "partial_literal_overlap" for page in pages), 9)
        self.assertEqual(sum(page["lexical_coverage"]["classification"] == "no_exact_five_token_window_found" for page in pages), 6)
        refs = self.candidate["pdf_only_structure_references"]
        self.assertEqual([ref["page_number"] for ref in refs if "page_number" in ref], [2, 3, 4, 5, 6, 7, 8, 9, 14, 15])
        h = next(ref for ref in refs if ref.get("page_numbers"))
        self.assertEqual(h["page_numbers"], [10, 11, 12, 13])

    def test_reference_page_keeps_attack_symbols_outside_module_map(self) -> None:
        reference = self.candidate["pdf"]["unassigned_reference_page"]
        self.assertEqual(reference["page_number"], 2)
        self.assertEqual(reference["heading_literal"], "Reference - Attack and Mute Vocabulary")
        self.assertIsNone(reference["module_label"])
        self.assertEqual([row["symbol_literal"] for row in reference["attack_vocabulary"]], ["O", "M", "x", "-", ">", "~"])
        self.assertEqual(reference["lexical_coverage_classification"], "no_exact_five_token_window_found")

    def test_capstone_preserves_eight_ranges_without_event_mapping(self) -> None:
        table = self.candidate["pdf"]["i_capstone_table"]
        self.assertEqual(table["table_headers"], list(candidate.CAPSTONE_HEADERS))
        self.assertEqual(table["printed_bar_ranges"], ["1-4", "5-8", "9-12", "13-16", "17-20", "21-24", "25-28", "29-32"])
        self.assertEqual(table["printed_row_count"], 8)
        self.assertIsNone(table["event_mapping"])
        self.assertEqual(table["declared_event_workload_reference"], {"txt_line_number": 21, "literal": "256 events"})
        self.assertEqual(table["rows"][7]["literal_fields"]["Dynamic"], "f -> p")
        self.assertNotIn("event_id", table["rows"][0])

    def test_pypdf_extracted_control_separator_is_counted_not_normalized(self) -> None:
        record = self.candidate["pdf"]["pages"][0]
        self.assertEqual(record["pypdf_extracted_control_codepoints"], {"U+007F": 4})
        self.assertEqual(self.source["pdf_pages"][0].count("\x7f"), 4)

    def test_candidate_is_pending_and_has_no_playable_event_model(self) -> None:
        item = self.candidate
        self.assertEqual(item["candidate_status"], "pending_source_reconciliation")
        self.assertEqual(item["curriculum_review"], "Pending")
        for key in ("canonical_ids_allocated", "canonical_record_emitted", "runtime_eligible", "imported", "admitted", "whole_workbook_complete"):
            self.assertIs(item[key], False)
        self.assertNotIn("events", item)
        self.assertNotIn("event_schedule", item)
        self.assertNotIn("tempo", item)
        self.assertIn("Level89 is a boundary only", " ".join(item["limits"]) + " " + " ".join(item["source_specific_observations"]))
        self.assertEqual(item["source_identities"][candidate.CATALOG]["sha256"], candidate.PINNED[candidate.CATALOG][1])

    def test_candidate_generation_is_deterministic(self) -> None:
        first = json.dumps(self.candidate, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        second = json.dumps(candidate.build_candidate(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        self.assertEqual(first.encode("utf-8"), second.encode("utf-8"))

    def test_literal_drift_root_and_output_boundary_refusals(self) -> None:
        mutated_txt = copy.deepcopy(self.source["txt_records"])
        mutated_txt[12]["literal"] = "A. Modified source title - 160 events"
        with self.assertRaisesRegex(candidate.CandidateError, "TXT_MODULE_LITERAL_DRIFT"):
            candidate.parse_module_rows(mutated_txt)

        mutated_index = self.source["pdf_pages"][0].replace("Eighth-note drive and palm-mute depth", "Eighth-note drive and mute depth", 1)
        with self.assertRaisesRegex(candidate.CandidateError, "PDF_INDEX_ROW_DRIFT"):
            candidate.parse_pdf_index(mutated_index, self.source["txt_modules"])

        mutated_capstone = self.source["pdf_pages"][13].replace("rock drive", "rock metal", 1)
        with self.assertRaisesRegex(candidate.CandidateError, "PDF_CAPSTONE_ROW_DRIFT"):
            candidate.parse_capstone_table(mutated_capstone)

        with self.assertRaisesRegex(candidate.CandidateError, "GIT_ROOT_MISMATCH"):
            candidate.assert_git_root(candidate.ROOT / "Build")
        with self.assertRaisesRegex(candidate.CandidateError, "OUTPUT_OUTSIDE_LANE_BUILD_ROOT"):
            candidate.validate_output_path(candidate.ROOT, candidate.ROOT / "unrelated.json")
        with self.assertRaisesRegex(candidate.CandidateError, "OUTPUT_PARENT_TRAVERSAL"):
            candidate.validate_output_path(candidate.ROOT, candidate.ROOT / candidate.BUILD_REL / ".." / "escape.json")

        build = candidate.ROOT / candidate.BUILD_REL
        build.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="path-refusal-", dir=build) as temp_name:
            temp = Path(temp_name)
            existing = temp / "already-exists.json"
            existing.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(candidate.CandidateError, "OUTPUT_OVERWRITE_REFUSED"):
                candidate.validate_output_path(candidate.ROOT, existing)
            target = temp / "real"
            target.mkdir()
            alias = temp / "alias"
            alias.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(candidate.CandidateError, "OUTPUT_PATH_SYMLINK"):
                candidate.validate_output_path(candidate.ROOT, alias / "new.json")


if __name__ == "__main__":
    unittest.main()
