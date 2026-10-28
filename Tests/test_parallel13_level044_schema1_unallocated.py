#!/usr/bin/env python3
"""Focused source geometry and refusal checks for the detached Level44 projection."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel13_level044_schema1_unallocated as p  # noqa: E402

OPEN = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
PC = {"A": 9, "C": 0, "D": 2, "Eb": 3, "E": 4, "G": 7,
      "C#": 1, "F#": 6, "F": 5, "B": 11, "G#": 8}
DEG = {"A": "1", "C": "b3", "D": "4", "Eb": "b5", "E": "5", "G": "b7",
       "C#": "3*", "F#": "6*", "F": "b6*", "B": "2*/E7-5", "G#": "7*/E7-3"}


def tab_pitches(rows: list[str]) -> list[int]:
    return sorted((OPEN[row[0]] + int(fret)) % 12 for row in rows
                  for fret in re.findall(r"\d+", row.split("|", 1)[1].split("|", 1)[0]))


class Level44ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.c = json.loads((ROOT / p.CANDIDATE).read_text())
        cls.proposal = p.build()

    def test_replay_and_pinned_originals(self) -> None:
        p.check_pins()
        p.check_candidate(self.c, p.source_tool.build_candidate(ROOT))
        self.assertEqual(set(self.c["source"]),
                         {"txt", "pdf", "source_map", "predecessor_txt", "predecessor_pdf"})
        for item in self.c["source"].values():
            self.assertEqual(hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest(),
                             item["sha256"])
        self.assertEqual(self.proposal["current_catalog"]["level44_status"], "not_converted")

    def test_exact_coverage_and_source_payloads(self) -> None:
        a = self.proposal
        self.assertEqual(a["source_task_count_by_module"], p.COUNTS)
        self.assertEqual(len(a["rows"]), 79)
        self.assertEqual(a["pdf_printed_workload_by_module"], p.TONES)
        self.assertEqual(sum(p.TONES.values()), 646)
        self.assertEqual(sum(r["source_count_backed_tones"] or 0 for r in a["rows"]), 582)
        self.assertEqual(len(a["source_context"]["source_guidance"]["txt_full_lines"]), 660)
        self.assertEqual(len(a["source_context"]["source_guidance"]["pdf_full_extracted_pages"]), 19)
        for row in a["rows"]:
            self.assertEqual(row["source_task_sha256"], p.sha(p.encoded(row["source_task"])))
            self.assertTrue(any(ref.startswith("L44-TXT-L")
                                for ref in row["schema1_fields"]["source_refs"]))
            self.assertTrue(any(ref.startswith("L44-PDF-p")
                                for ref in row["schema1_fields"]["source_refs"]))
        self.assertEqual([r["source_task"] for r in a["rows"] if r["source_module"] == "A"],
                         self.c["modules"]["A"])
        self.assertEqual([r["source_task"] for r in a["rows"] if r["source_module"] == "I"],
                         self.c["modules"]["I"])

    def test_site_pitch_and_alternatives(self) -> None:
        for letter in "AC":
            for row in self.c["modules"][letter]:
                self.assertEqual((OPEN[row["string"]] + row["source_fret"]) % 12,
                                 PC[row["source_note"]])
                self.assertEqual((OPEN[row["string"]] + row["target_fret"]) % 12,
                                 PC[row["target_note"]])
                self.assertEqual(len(row["alternatives"]), 4)
                self.assertTrue(row["txt_ref"].startswith("L44-TXT-L"))
        for row in self.c["modules"]["B"]:
            self.assertEqual([(OPEN[row["string"]] + f) % 12 for f in row["frets"]],
                             [PC[n] for n in row["notes"]])
            self.assertEqual(len(row["passes"]), 4)

    def test_tab_geometry_and_chordal_shape(self) -> None:
        c = self.c
        self.assertEqual(len(c["modules"]["D"]["families"]), 5)
        self.assertIn("four rhythm templates", c["modules"]["D"]["rhythm_templates_raw"][0])
        for lick in c["modules"]["F"]:
            for pos in lick["positions"]:
                rows = pos["tab_rows"]
                self.assertEqual([r[0] for r in rows], list("eBGDAE"))
                self.assertEqual(tab_pitches(rows), sorted(PC[n] for n in pos["notes"]))
                self.assertEqual(pos["degrees"], [DEG[n] for n in pos["notes"]])
        for module, members in (("G", ("call", "answer")),
                                ("H", ("tonic_ending", "turnaround_ending"))):
            for pair in c["modules"][module]:
                for member in members:
                    row = pair[member]
                    self.assertEqual([r[0] for r in row["tab_rows"]], list("eBGDAE"))
                    self.assertEqual(len(tab_pitches(row["tab_rows"])), row["written_tones"])
        chord = c["modules"]["I"][2]
        self.assertEqual(chord["kind"], "simultaneous_voice_leading_shapes")
        self.assertEqual(chord["printed_workload_tones"], 16)
        self.assertEqual(len(chord["tab_rows"]), 6)
        self.assertEqual(self.proposal["rows"][38]["source_module"], "G")

    def test_j_claims_and_pdf_only_context(self) -> None:
        a = self.proposal
        j = a["source_context"]["module_J_full_source"]
        self.assertEqual((len(j["openings"]), len(j["endings"]),
                          len(j["all_combinations"]), len(j["model_combinations_raw"])),
                         (4, 4, 16, 4))
        self.assertEqual((a["module_J_printed_workload_tones"],
                          a["module_J_implied_full_combination_degree_occurrences"]),
                         (64, 128))
        self.assertEqual({d["kind"] for d in a["source_context"]["source_differences"]},
                         {"PDF_only_post_workbook_variations", "PDF_only_completion_audit_checklist",
                          "PDF_visual_completion_audit_border_overlap", "J_workload_count_ambiguous"})
        self.assertTrue(all(r["source_count_backed_tones"] is None
                            for r in a["rows"] if r["source_module"] == "J"))

    def test_no_executable_or_admitted_fields(self) -> None:
        a = self.proposal
        self.assertEqual(a["playable_event_count"], 0)
        self.assertIsNone(a["playable_pick_attack_count"])
        for key in ("canonical_ids_allocated", "schema1_imported", "whole_workbook_accepted",
                    "runtime_eligible"):
            self.assertIs(a[key], False)
        for row in a["rows"]:
            fields = row["schema1_fields"]
            self.assertIsNone(row["playable_pick_attacks"])
            for key in ("id", "workbook_id", "module_id", "lineage", "content_revision",
                        "pitch", "route", "performed_result"):
                self.assertIsNone(fields[key])
            self.assertEqual(fields["events"], [])
            self.assertEqual(fields["variants"], [])
            self.assertTrue(all(value is None for key, value in fields["timing"].items()
                                if key != "status"))

    def test_refuses_semantic_and_admission_mutations(self) -> None:
        mutations = [
            lambda c: c["pdf_printed_workload_by_module"].__setitem__("J", 128),
            lambda c: c["modules"]["J"].__setitem__("count_status", "resolved"),
            lambda c: c["modules"]["I"][2].__setitem__("kind", "single_note_line"),
            lambda c: c.__setitem__("admitted", True),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                altered = copy.deepcopy(self.c)
                mutate(altered)
                with self.assertRaises(p.ProposalError):
                    p.check_candidate(altered, altered)
        altered = copy.deepcopy(self.c)
        altered["modules"]["A"][0]["target_fret"] += 1
        with self.assertRaisesRegex(p.ProposalError, "SOURCE_REPLAY_DRIFT"):
            p.check_candidate(altered, self.c)


if __name__ == "__main__":
    unittest.main()
