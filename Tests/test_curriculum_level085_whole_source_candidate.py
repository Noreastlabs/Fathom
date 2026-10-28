from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from Tools import curriculum_level085_whole_source_candidate as candidate


class Level85WholeSourceCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = candidate.read_inputs()
        cls.candidate = candidate.build_candidate()

    def test_current_source_pair_catalog_and_pending_status(self) -> None:
        self.assertEqual(self.source["root"], candidate.ROOT.resolve())
        self.assertEqual(len(self.source["raw"]), 9)
        self.assertEqual(candidate.pypdf.__version__, "6.10.0")
        self.assertEqual(len(self.source["pdf_pages"]), 15)
        self.assertEqual(self.source["catalog_entry"]["review"], "Pending")
        self.assertEqual(self.source["catalog_entry"]["conversion_status"], "not_converted")
        self.assertIs(self.source["catalog_entry"]["runtime_eligible"], False)
        self.assertIs(self.source["catalog_entry"]["imported"], False)
        self.assertIs(self.source["catalog_entry"]["admitted"], False)
        self.assertIs(self.source["catalog_entry"]["whole_workbook_complete"], False)

    def test_all_txt_lines_keep_literal_text_spans_and_workload_labels(self) -> None:
        txt = self.candidate["txt"]
        self.assertEqual(txt["line_count"], 40)
        self.assertEqual(len(txt["literal_lines"]), 40)
        self.assertEqual(txt["literal_lines"][3]["literal"], "LEVEL 85 OF 105 - HARD STOP AFTER LEVEL 105")
        self.assertEqual(txt["literal_lines"][8]["literal"], "COMPLETE WRITTEN WORKLOAD: 1440 events")
        self.assertEqual(txt["literal_lines"][39]["literal"], self.source["txt_records"][39]["literal"])
        self.assertEqual([row["module_label"] for row in txt["modules"]], list("ABCDEFGHIJ"))
        self.assertEqual([row["declared_workload_value"] for row in txt["modules"]], [128, 128, 144, 144, 128, 96, 160, 192, 256, 64])
        for row in txt["literal_lines"]:
            span = row["source_position"]
            literal = self.source["txt_text"][span["start_char"]:span["end_char_exclusive"]]
            self.assertEqual(literal, row["literal"])

    def test_pdf_index_titles_and_counts_match_the_txt_source_labels(self) -> None:
        index = self.candidate["pdf"]["module_index"]
        self.assertEqual(index["header_literal"], "Module\nExercise\nEvents")
        self.assertEqual(len(index["rows"]), 10)
        self.assertTrue(all(row["titles_exactly_equal"] and row["workloads_exactly_equal"] for row in index["rows"]))
        self.assertEqual([row["pdf_index_title_literal"] for row in index["rows"]], [row["title_literal"] for row in self.source["txt_modules"]])
        self.assertEqual(index["declared_total_literal"], "1440")
        self.assertEqual(index["module_workload_sum"], 1440)

    def test_all_fifteen_pdf_pages_match_live_text_cache_and_history_by_reference(self) -> None:
        pages = self.candidate["pdf"]["pages"]
        self.assertEqual(len(pages), 15)
        self.assertEqual([page["literal_extracted_text_sha256"] for page in pages], [candidate.EXPECTED_PAGE_HASHES[n] for n in range(1, 16)])
        for number, page in enumerate(pages, 1):
            self.assertEqual(page["literal_extracted_text_sha256"], page["current_catalog_text_sha256"])
            self.assertEqual(page["literal_extracted_text_sha256"], page["historical_appendix_text_sha256"])
            self.assertNotIn("literal_extracted_text", page)
        history = self.candidate["pdf"]["complete_literal_page_text_reference"]
        self.assertEqual(history["page_count"], 15)
        self.assertEqual(history["path"], candidate.APPENDIX)
        self.assertEqual(history["sha256"], candidate.PINNED[candidate.APPENDIX][1])

    def test_module_detail_heading_crosswalk_uses_explicit_letters_only(self) -> None:
        crosswalk = self.candidate["module_crosswalk"]
        self.assertEqual([row["module_label"] for row in crosswalk], list("ABCDEFGHIJ"))
        pages = {row["module_label"]: [detail["page_number"] for detail in row["pdf_detail_headings"]] for row in crosswalk}
        self.assertEqual(pages, {"A": [3], "B": [4], "C": [5], "D": [6], "E": [7], "F": [8], "G": [9], "H": [10, 11, 12, 13], "I": [14], "J": [15]})
        self.assertEqual([row["detail_heading_literal"] for row in crosswalk[7]["pdf_detail_headings"]], [
            "Module H - Study 1 - Rock pocket",
            "Module H - Study 2 - Funk pocket",
            "Module H - Study 3 - Offbeat pocket",
            "Module H - Study 4 - Soul pocket",
        ])
        self.assertIn("four separately headed PDF studies", crosswalk[7]["source_difference_note"])

    def test_page_two_remains_an_unassigned_reference_page(self) -> None:
        p2 = self.candidate["pdf"]["unassigned_reference_page"]
        self.assertEqual(p2["page_number"], 2)
        self.assertEqual(p2["heading_literal"], "Reference - One Grid, Several Grooves")
        self.assertIsNone(p2["module_label"])
        self.assertEqual(p2["lexical_coverage_classification"], "no_exact_five_token_window_found")

    def test_capstone_table_preserves_eight_bar_ranges_without_event_mapping(self) -> None:
        table = self.candidate["pdf"]["i_capstone_table"]
        self.assertEqual(table["table_headers"], list(candidate.I_HEADERS))
        self.assertEqual(table["printed_bar_range_count"], 8)
        self.assertEqual(table["printed_bar_ranges"], ["1-4", "5-8", "9-12", "13-16", "17-20", "21-24", "25-28", "29-32"])
        self.assertIsNone(table["event_mapping"])
        self.assertEqual(table["declared_event_workload_reference"]["literal"], "256 events")
        self.assertEqual(table["rows"][7]["literal_fields"]["Dynamic"], "mp -> f -> p")
        self.assertNotIn("event_id", table["rows"][0])

    def test_pdf_source_page_roles_account_for_all_pages(self) -> None:
        pages = self.candidate["pdf"]["pages"]
        self.assertEqual([page["page_number"] for page in pages], list(range(1, 16)))
        self.assertEqual(pages[0]["page_role"], "document-title-and-module-index")
        self.assertEqual(pages[1]["page_role"], "unassigned-reference-page")
        self.assertEqual(pages[14]["literal_heading"], "Module J - Pocket Audit and Recovery")
        self.assertEqual(len({page["literal_extracted_text_sha256"] for page in pages}), 15)
        self.assertEqual(sum(page["lexical_coverage"]["classification"] == "partial_literal_overlap" for page in pages), 4)
        self.assertEqual(sum(page["lexical_coverage"]["classification"] == "no_exact_five_token_window_found" for page in pages), 11)

    def test_candidate_is_pending_and_contains_no_runtime_event_model(self) -> None:
        item = self.candidate
        self.assertEqual(item["candidate_status"], "pending_source_reconciliation")
        self.assertEqual(item["curriculum_review"], "Pending")
        for key in ("canonical_ids_allocated", "canonical_record_emitted", "runtime_eligible", "imported", "admitted", "whole_workbook_complete"):
            self.assertIs(item[key], False)
        self.assertNotIn("events", item)
        self.assertNotIn("event_schedule", item)
        self.assertNotIn("tempo", item)
        self.assertIn("Level86 is a boundary only", " ".join(item["source_specific_observations"]))

    def test_candidate_generation_is_deterministic(self) -> None:
        first = json.dumps(self.candidate, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        second = json.dumps(candidate.build_candidate(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        self.assertEqual(first.encode("utf-8"), second.encode("utf-8"))

    def test_source_mutations_and_non_root_or_unsafe_outputs_refuse(self) -> None:
        changed_records = copy.deepcopy(self.source["txt_records"])
        changed_records[11]["literal"] = "A. Unreviewed title - 128 events"
        with self.assertRaisesRegex(candidate.CandidateError, "TXT_MODULE_LITERAL_DRIFT"):
            candidate.parse_module_rows(changed_records)

        changed_index = self.source["pdf_pages"][0].replace("Subdivision-to-groove conversion\n128", "Subdivision-to-groove conversion\n129", 1)
        with self.assertRaisesRegex(candidate.CandidateError, "PDF_INDEX_ROW_DRIFT"):
            candidate.parse_pdf_index(changed_index, self.source["txt_modules"])

        changed_i = self.source["pdf_pages"][13].replace("straight rock", "straight swing", 1)
        with self.assertRaisesRegex(candidate.CandidateError, "PDF_I_TABLE_ROW_DRIFT"):
            candidate.parse_i_table(changed_i)

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
            exists = temp / "already-exists.json"
            exists.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(candidate.CandidateError, "OUTPUT_OVERWRITE_REFUSED"):
                candidate.validate_output_path(candidate.ROOT, exists)
            target = temp / "real"
            target.mkdir()
            alias = temp / "alias"
            alias.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(candidate.CandidateError, "OUTPUT_PATH_SYMLINK"):
                candidate.validate_output_path(candidate.ROOT, alias / "new.json")


if __name__ == "__main__":
    unittest.main()
