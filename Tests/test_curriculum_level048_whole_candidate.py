from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from collections import Counter

from pypdf import PdfReader

from curriculum_level048_whole_candidate import (
    BUILD_REL,
    EXPECTED_PDF_COUNTS,
    EXPECTED_TXT_COUNTS,
    MAP_REL,
    PDF_REL,
    ROOT,
    TXT_REL,
    CandidateError,
    build_candidate,
    serialize_candidate,
    write_candidates,
)


class Level048WholeCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = build_candidate()
        cls.txt_data = (ROOT / TXT_REL).read_bytes()
        cls.pdf_data = (ROOT / PDF_REL).read_bytes()
        cls.txt_lines = cls.txt_data.decode("utf-8").splitlines()
        cls.pdf_reader = PdfReader(ROOT / PDF_REL)

    def test_source_map_and_prior_reference_remain_exact(self) -> None:
        candidate = self.candidate
        row = candidate["source_map"]["level48_row"]
        self.assertEqual(row["representative_item_id"], "fg:item:000007")
        self.assertEqual(row["review"], "Pending")
        self.assertEqual(row["conversion_status"], "converted_candidate_reference")
        self.assertEqual((row["runtime_eligible"], row["imported"], row["admitted"]), ("False", "False", "False"))
        prior = candidate["prior_bounded_proof"]
        self.assertEqual(prior["preserved_source_refs"], ["L48-TXT49-76"])
        self.assertEqual(prior["preserved_event_suffixes"], ["0003", "0008", "0011", "0016"])
        self.assertIn("not Level48 whole-source conversion", prior["scope_note"])

    def test_all_txt_lines_and_pdf_pages_are_losslessly_represented(self) -> None:
        txt = self.candidate["txt_source"]
        self.assertEqual(txt["raw_text"].encode("utf-8"), self.txt_data)
        self.assertEqual(len(txt["lines"]), 1246)
        self.assertEqual([entry["line"] for entry in txt["lines"]], list(range(1, 1247)))
        self.assertEqual([entry["text"] for entry in txt["lines"]], self.txt_lines)
        pages = self.candidate["pdf_source"]["pages"]
        self.assertEqual(len(pages), 22)
        self.assertEqual([page["page"] for page in pages], list(range(1, 23)))
        self.assertEqual([page["extracted_text"] for page in pages], [p.extract_text() or "" for p in self.pdf_reader.pages])
        self.assertEqual([page["ref"] for page in pages], [f"L48-PDF-p{n}" for n in range(1, 23)])

    def test_source_sections_cover_txt_and_pdf_in_order(self) -> None:
        sections = self.candidate["source_coverage"]["sections_in_source_order"]
        self.assertEqual(sections[0]["txt_line_range"], [1, 45])
        self.assertEqual([s["module"] for s in sections if "module" in s], list("ABCDEFGHIJK"))
        self.assertEqual(sections[-2]["txt_line_range"], [1214, 1225])
        self.assertEqual(sections[-1]["txt_line_range"], [1226, 1246])
        ranges = [section["txt_line_range"] for section in sections]
        self.assertEqual(ranges[0][0], 1)
        self.assertEqual(ranges[-1][1], 1246)
        for left, right in zip(ranges, ranges[1:]):
            self.assertEqual(left[1] + 1, right[0])
        module_pages = self.candidate["source_coverage"]["pdf_module_page_index"]
        self.assertEqual([row["module"] for row in module_pages], list("ABCDEFGHIJK"))
        self.assertEqual(module_pages[0]["pdf_pages"], [3, 4, 5])
        self.assertEqual(module_pages[-1]["pdf_pages"], [20])

    def test_every_txt_notation_cell_and_tablature_row_is_preserved(self) -> None:
        cells = self.candidate["txt_notation_cells"]
        self.assertEqual(len(cells), 76)
        self.assertEqual(Counter(cell["module"] for cell in cells), Counter({"A": 10, "B": 4, "C": 8, "D": 3, "E": 3, "F": 12, "G": 12, "H": 12, "I": 6, "J": 6}))
        counts = Counter()
        tabs = 0
        for cell in cells:
            labels = [row["kind"] for row in cell["rows"] if row["kind"] != "TAB"]
            self.assertIn(labels, [list(EXPECTED_TXT_COUNTS), ["Cnt", "Nte", "Deg", "Rol", "Atk"]])
            self.assertEqual([r["string"] for r in cell["rows"] if r["kind"] == "TAB"], ["e", "B", "G", "D", "A", "E"])
            for row in cell["rows"]:
                if row["kind"] == "TAB":
                    tabs += 1
                else:
                    counts[row["kind"]] += 1
                self.assertEqual(self.txt_lines[row["line"] - 1], row["raw"])
            self.assertIn("no onset or duration derived", cell["timing_interpretation"])
        self.assertEqual({label: counts[label] for label in EXPECTED_TXT_COUNTS}, EXPECTED_TXT_COUNTS)
        self.assertEqual(tabs, 456)
        self.assertEqual(self.candidate["source_coverage"]["txt_tab_row_count"], 456)

    def test_pdf_extraction_preserves_distinct_notation_counts(self) -> None:
        coverage = self.candidate["source_coverage"]
        self.assertEqual(coverage["txt_table_row_counts"], EXPECTED_TXT_COUNTS)
        self.assertEqual(coverage["pdf_extracted_table_row_counts"], EXPECTED_PDF_COUNTS)
        self.assertEqual(coverage["txt_tab_row_count"], 456)
        self.assertEqual(coverage["pdf_extracted_tab_row_count"], 438)
        self.assertEqual(EXPECTED_PDF_COUNTS, {"Cnt": 73, "Nte": 73, "Deg": 64, "Col": 36, "Rol": 65, "Atk": 73})

    def test_recovery_grid_omissions_are_cited_in_both_forms(self) -> None:
        ledger = {entry["id"]: entry for entry in self.candidate["source_difference_ledger"]}
        recovery = ledger["module-j-three-recovery-grids"]
        self.assertEqual(recovery["txt_ref"], "L48-TXT1148-1188")
        self.assertEqual(recovery["pdf_ref"], "L48-PDF-p19")
        self.assertEqual((recovery["txt_additional_grid_count"], recovery["pdf_additional_grid_count"]), (3, 0))
        page19 = self.candidate["pdf_source"]["pages"][18]["extracted_text"]
        self.assertIn("SIX WRITTEN RECOVERY CELLS", page19)
        self.assertIn("Additional repairs: late response", page19)
        self.assertNotIn("MISSED BEND - SOURCE RELEASE", page19)
        self.assertNotIn("LOST POSITION - TONIC RESET", page19)

    def test_all_known_source_exceptions_are_pending_not_silently_resolved(self) -> None:
        ledger = {entry["id"]: entry for entry in self.candidate["source_difference_ledger"]}
        self.assertEqual(set(ledger), {
            "notation-row-coverage", "module-j-three-recovery-grids", "txt-only-core-written-counts",
            "rubric-wording-and-authored-counts", "next-section-map-history",
        })
        rows = ledger["notation-row-coverage"]["row_omissions"]
        self.assertEqual([(r["module"], r["rows_absent_in_pdf"]) for r in rows], [
            ("A", ["Col"]), ("B", ["Col"]), ("C", ["Col", "Rol"]), ("D", ["Col", "Deg"]),
            ("E", ["Deg"]), ("I", ["Col"]), ("J", ["Col", "Deg"]),
        ])
        self.assertIn("L48-TXT32-43", ledger["txt-only-core-written-counts"]["txt_ref"])
        self.assertIn("L48-TXT1244-1246", ledger["next-section-map-history"]["txt_ref"])
        self.assertEqual(ledger["next-section-map-history"]["status"], "historical-map-ambiguity-not-located-in-current-pair")
        self.assertEqual(ledger["notation-row-coverage"]["status"], "pending-source-reconciliation")

    def test_candidate_has_no_new_identity_or_derived_timing_fields(self) -> None:
        candidate = self.candidate
        self.assertEqual(candidate["candidate_status"], "pending-source-reconciliation")
        self.assertEqual(candidate["identity_state"]["preexisting_source_map_representative_reference_only"], "fg:item:000007")
        self.assertFalse(candidate["identity_state"]["new_stable_identity_created_by_lane"])
        self.assertFalse(candidate["identity_state"]["identity_assignment_or_reassignment_performed_by_lane"])
        self.assertEqual(candidate["release_state"], {"runtime_eligible": False, "imported": False, "admitted": False, "curriculum_accepted": False})
        self.assertFalse(candidate["timing_state"]["derived_onsets_or_durations_created"])
        self.assertFalse(candidate["timing_state"]["ascii_columns_are_timing_claims"])
        forbidden_keys = {"onset_q", "duration_q", "stable_id", "runtime_item_id", "tempo_bpm"}
        def walk(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    self.assertNotIn(key, forbidden_keys)
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        walk(candidate)

    def test_mutated_pinned_inputs_and_prior_proof_are_refused(self) -> None:
        with self.assertRaisesRegex(CandidateError, "PINNED_INPUT_DRIFT L48-TXT"):
            build_candidate(txt_data=self.txt_data + b" ")
        with self.assertRaisesRegex(CandidateError, "PINNED_INPUT_DRIFT L48-PDF"):
            build_candidate(pdf_data=self.pdf_data + b" ")
        map_data = (ROOT / MAP_REL).read_bytes()
        with self.assertRaisesRegex(CandidateError, "PINNED_INPUT_DRIFT source-map"):
            build_candidate(map_data=map_data + b" ")
        with self.assertRaisesRegex(CandidateError, "P03_RESULT_IDENTITY_DRIFT"):
            build_candidate(prior_result_data=b"not the cited prior result")

    def test_serialization_is_deterministic_and_root_independent(self) -> None:
        first = serialize_candidate(self.candidate)
        second = serialize_candidate(build_candidate())
        self.assertEqual(first, second)
        self.assertNotIn(str(ROOT).encode(), first)
        decoded = json.loads(first)
        self.assertEqual(decoded["candidate_format"], "p04.detached-level48-source-preservation.v1")

    def test_output_pair_is_confined_identical_and_no_replace(self) -> None:
        build_area = ROOT / "Build/parallel-04"
        with tempfile.TemporaryDirectory(prefix="level048-pair-test-", dir=build_area) as temp:
            dest = Path(temp) / "candidate-pair"
            paths = write_candidates(self.candidate, dest)
            self.assertEqual([p.name for p in paths], ["candidate-01.json", "candidate-02.json"])
            self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())
            with self.assertRaisesRegex(CandidateError, "OUTPUT_EXISTS"):
                write_candidates(self.candidate, dest)
        with self.assertRaisesRegex(CandidateError, "OUTPUT_OUTSIDE_LANE"):
            write_candidates(self.candidate, ROOT / "Results/parallel-04/not-a-build-output")


if __name__ == "__main__":
    unittest.main()
