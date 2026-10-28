"""Focused complete Level101 composition-source and refusal checks."""

from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "level101_whole", ROOT / "Tools/curriculum_level101_whole_semantic_candidate.py")
assert SPEC and SPEC.loader
candidate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(candidate)


class Level101WholeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = candidate.read_source()
        cls.payload = candidate.build_from_source(cls.source)
        cls.modules = {m["module"]: m for m in cls.payload["modules"]}

    def changed(self):
        return copy.deepcopy(self.source)

    def test_complete_source_module_and_event_claims(self):
        self.assertEqual(len(self.payload["txt_lines"]), 51)
        self.assertEqual(len(self.payload["pdf_pages"]), 21)
        self.assertEqual(self.payload["module_order"], list("ABCDEFGHIJ"))
        self.assertEqual([m["declared_events"] for m in self.payload["modules"]],
                         [144, 144, 128, 128, 128, 144, 160, 224, 320, 64])
        self.assertEqual(self.payload["declared_total_events"], 1584)
        self.assertEqual(self.payload["extracted_task_rows"], 118)
        self.assertEqual([len(self.modules[x]["tasks"]) for x in "ABCDEFGHIJ"],
                         [13, 12, 14, 13, 14, 6, 10, 24, 4, 8])
        self.assertEqual(len(self.payload["supporting_reference"]["rows"]), 8)

    def test_every_task_has_exact_page_and_unknown_event_realization(self):
        for module in self.modules.values():
            self.assertIsNone(module["allocated_event_count"])
            self.assertFalse(module["per_task_event_counts_known"])
            for row in module["tasks"]:
                page = row["source"]["page"]
                self.assertEqual(row["source"]["extracted_text_sha256"],
                                 self.payload["pdf_pages"][page-1]["extracted_text_sha256"])
                for field in ("declared_event_count_for_row", "canonical_id", "composed_notes",
                              "motif_realization", "recorded_take", "duration", "performed_timing"):
                    self.assertIsNone(row[field])

    def test_composition_motif_and_form_constraints_retained(self):
        self.assertEqual(self.modules["A"]["tasks"][0]["fields"],
                         {"Variable": "Motif", "A section": "original contour", "B section": "inverted or sequenced"})
        self.assertEqual(self.modules["C"]["tasks"][6]["fields"],
                         {"Bridge strategy": "Motif absence", "Exercise": "remove main motif, then restore it on return"})
        self.assertEqual(self.modules["D"]["tasks"][-1]["fields"],
                         {"Version": "0%", "Allowed content": "direct cut to next section"})
        self.assertEqual(self.modules["E"]["tasks"][0]["fields"]["Return type"], "Exact return")
        self.assertEqual(self.modules["F"]["tasks"][-1]["fields"]["Bars"], "4+4+4+4")

    def test_sparse_g_map_and_h_i_j_structure(self):
        sparse = self.modules["G"]["tasks"][-4:]
        self.assertEqual([x["fields"]["Energy 1-5"] for x in sparse], ["2", "3", "4-5", "2-4"])
        for row in sparse:
            self.assertTrue(row["blank_cells_verified_from_render"])
            self.assertIsNone(row["fields"]["Density"])
            self.assertIsNone(row["fields"]["Register"])
            self.assertIsNone(row["fields"]["Cadence"])
        self.assertEqual([x["study"] for x in self.payload["h_studies"]], [1, 2, 3, 4])
        self.assertEqual([x["fields"]["Bars"] for x in self.modules["I"]["tasks"]],
                         ["1-8", "9-16", "17-24", "25-32"])
        self.assertEqual([x["fields"]["Section"] for x in self.modules["I"]["tasks"]],
                         ["A", "B", "Bridge", "A'"])
        self.assertEqual(self.modules["J"]["tasks"][-1]["fields"]["Revision task"],
                         "rewrite unclear section")

    def test_txt_pdf_capstone_wording_kept_separate(self):
        capstone = self.payload["capstone_deliverables"]
        self.assertIn("harmony/function chart", capstone["txt"])
        self.assertIn("chord/function chart", capstone["pdf"])
        self.assertIn("motif statement", capstone["pdf"])
        self.assertNotEqual(capstone["txt"], capstone["pdf"])
        self.assertEqual(capstone["wording_equivalence_review"], "Pending")
        self.assertEqual(self.payload["mastery"]["protected_zero_domains"],
                         ["identity", "form", "thematic return", "performance"])

    def test_missing_or_changed_source_rows_refused(self):
        for page, old, new in [(3, "Texture\n", ""),
                               (15, "Bridge/Peak\n4-5\n", "Bridge/Peak\n5\n"),
                               (18, "record and revise once\n", ""),
                               (20, "25-32\n", "25-33\n"),
                               (21, "rewrite unclear section\n", "")]:
            with self.subTest(page=page):
                changed = self.changed()
                changed["pdf"]["content"][page-1] = changed["pdf"]["content"][page-1].replace(old, new, 1)
                with self.assertRaises(candidate.SourceError):
                    candidate.build_from_source(changed)

    def test_total_and_mastery_drift_refused(self):
        changed = self.changed()
        changed["pdf"]["content"][0] = changed["pdf"]["content"][0].replace("TOTAL\n1584", "TOTAL\n1585", 1)
        with self.assertRaisesRegex(candidate.SourceError, "module total"):
            candidate.build_from_source(changed)
        changed = self.changed()
        changed["txt"]["content"][46] = "15/16 or better."
        with self.assertRaisesRegex(candidate.SourceError, "TXT line missing/repeated"):
            candidate.build_from_source(changed)

    def test_pinned_sources_and_pending_boundary(self):
        for kind in ("txt", "pdf"):
            relative, size, digest = candidate.SOURCE[kind]
            raw = (ROOT / relative).read_bytes()
            self.assertEqual((len(raw), candidate.sha(raw)), (size, digest))
            self.assertNotEqual(candidate.sha(raw+b"changed"), digest)
        self.assertEqual(self.payload["status"], "Pending")
        self.assertFalse(self.payload["whole_workbook_accepted"])
        self.assertFalse(self.payload["canonical_ids_allocated"])
        self.assertFalse(self.payload["schema1_imported"])
        self.assertFalse(self.payload["runtime_eligible"])
        self.assertIsNone(self.payload["unresolved"]["per_task_event_counts"])
        self.assertIsNone(self.payload["unresolved"]["recorded_take"])


if __name__ == "__main__":
    unittest.main()
