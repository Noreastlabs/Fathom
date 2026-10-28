from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from Tools import curriculum_level088_semantic_expansion_candidate as candidate


class Level88SemanticPdfExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.item = candidate.build_candidate()

    def module(self, label: str) -> dict:
        return next(row for row in self.item["modules"] if row["module_label"] == label)

    def test_current_source_bindings_and_pending_status_are_preserved(self) -> None:
        self.assertEqual(self.item["workbook_id"], "fg:workbook:000088")
        self.assertEqual(self.item["source_status"]["source_map_review"], "Pending")
        self.assertEqual(self.item["source_status"]["source_map_conversion_status"], "not_converted")
        self.assertEqual(self.item["source_status"]["catalog_review"], "Pending")
        self.assertEqual(self.item["source_status"]["prior_staging_used"], False)
        self.assertEqual(self.item["input_identities"][candidate.TXT]["bytes"], 1489)
        self.assertEqual(self.item["input_identities"][candidate.PDF]["bytes"], 40992)
        self.assertEqual(self.item["input_identities"][candidate.PACKAGE]["sha256"], candidate.PINNED[candidate.PACKAGE][1])

    def test_all_ten_printed_module_letters_titles_and_workloads_crosswalk(self) -> None:
        self.assertEqual([row["module_label"] for row in self.item["modules"]], list("ABCDEFGHIJ"))
        self.assertEqual(
            [row["declared_workload"]["value"] for row in self.item["modules"]],
            [160, 144, 160, 144, 128, 128, 160, 192, 256, 64],
        )
        self.assertEqual(sum(row["declared_workload"]["value"] for row in self.item["modules"]), 1536)
        self.assertEqual(
            [row["source_ref"]["pdf_detail_pages"] for row in self.item["modules"]],
            [[3], [4], [5], [6], [7], [8], [9], [10, 11, 12, 13], [14], [15]],
        )
        self.assertFalse(self.module("A")["title_relationship"]["titles_exactly_equal"])
        self.assertEqual(self.module("H")["title_relationship"]["pdf_detail_heading_literals"][3], candidate.PDF_PAGE_HEADINGS[13])

    def test_task_unit_kinds_and_counts_are_distinct_from_declared_workload(self) -> None:
        self.assertEqual(
            [(m["task_unit_kind"], m["task_unit_count"]) for m in self.item["modules"]],
            [
                ("pass", 8),
                ("cell", 8),
                ("riff", 6),
                ("cell", 8),
                ("accent_cycle", 6),
                ("section_texture", 6),
                ("riff_example", 8),
                ("study", 4),
                ("capstone_segment", 8),
                ("failure_repair", 8),
            ],
        )
        self.assertNotEqual(
            [m["task_unit_count"] for m in self.item["modules"]],
            [m["declared_workload"]["value"] for m in self.item["modules"]],
        )
        for module in self.item["modules"]:
            self.assertEqual(module["task_unit_count"], len(module["task_rows"]))
            self.assertIsNone(module["source_task_to_event_mapping"])

    def test_a_mute_depth_passes_keep_the_authored_progression(self) -> None:
        rows = self.module("A")["task_rows"]
        self.assertEqual([row["fields"]["pass"] for row in rows], [str(n) for n in range(1, 9)])
        self.assertEqual(rows[0]["fields"]["mute_target_literal"], "heavy mute; short low-E pitch")
        self.assertEqual(rows[2]["fields"]["mute_target_literal"], "light mute; near-open")
        self.assertEqual(rows[4]["fields"]["mute_target_literal"], "verse-to-chorus lift")
        self.assertEqual(rows[6]["fields"]["grid_literal"], ">M M >M M >M M >M M")
        self.assertIn("not tempo", self.module("A")["explicit_guidance_literals"][0])

    def test_b_gallop_cells_preserve_count_pick_and_continuity_facts(self) -> None:
        rows = self.module("B")["task_rows"]
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[0]["fields"]["sixteenth_grid_literal"], "M - M M")
        self.assertEqual(rows[0]["fields"]["picking_goal_literal"], "D - D U")
        self.assertEqual(rows[5]["fields"]["picking_goal_literal"], "reverse-gallop continuity")
        self.assertIn("Count each beat as 1 e & a.", self.module("B")["explicit_guidance_literals"][0])
        self.assertIn("Begin on one string.", self.module("B")["explicit_guidance_literals"][1])

    def test_c_pedal_riffs_and_d_displacement_cells_retain_exact_fields(self) -> None:
        c_rows = self.module("C")["task_rows"]
        d_rows = self.module("D")["task_rows"]
        self.assertEqual(len(c_rows), 6)
        self.assertEqual(c_rows[4]["fields"]["chord_punctuation_literal"], "F5-G5-A5")
        self.assertEqual(c_rows[5]["fields"]["pattern_literal"], "gallop pedal + chord on beat 4")
        self.assertIn("structural event", self.module("C")["explicit_guidance_literals"][0])
        self.assertEqual(len(d_rows), 8)
        self.assertEqual(d_rows[4]["fields"]["chord_attacks_literal"], "1, a2, &3, 4")
        self.assertEqual(d_rows[7]["fields"]["purpose_literal"], "high-displacement test")

    def test_e_keeps_partial_accent_patterns_and_f_keeps_shared_harmony(self) -> None:
        e_rows = self.module("E")["task_rows"]
        f_rows = self.module("F")["task_rows"]
        self.assertEqual(len(e_rows), 6)
        self.assertTrue(all(row["fields"]["attack_pattern_literal"].endswith("...") for row in e_rows[:4]))
        self.assertEqual(e_rows[4]["fields"]["accent_cycle_literal"], "3+3+2")
        self.assertEqual(e_rows[5]["fields"]["attack_pattern_literal"], "1 0 1 0 1 0 0 0")
        self.assertIn("16 eighth-note attacks", self.module("E")["explicit_guidance_literals"][0])
        self.assertEqual([row["fields"]["section_literal"] for row in f_rows], [
            "Verse", "Pre-chorus", "Chorus", "Breakdown", "Bridge", "Outro"
        ])
        self.assertIn("same E5-G5-A5-D5 harmony", self.module("F")["explicit_guidance_literals"][0])

    def test_g_records_variation_instruction_without_fabricating_variations(self) -> None:
        g = self.module("G")
        self.assertEqual(len(g["task_rows"]), 8)
        self.assertEqual(g["task_rows"][7]["fields"]["cell_literal"], "E - G5 - | A5 E D5 E")
        self.assertEqual(
            g["explicit_guidance_literals"],
            ["For each riff create exactly three variations: change accent only; change final chord only; change note density only. Preserve the original rhythmic identity."],
        )
        self.assertNotIn("variations", g["task_rows"][0])

    def test_h_retains_four_distinct_studies_and_shared_six_pass_sequence(self) -> None:
        h = self.module("H")["task_rows"]
        self.assertEqual([row["fields"]["study_label"] for row in h], [
            "Study 1 - Rock eighth-note drive",
            "Study 2 - Hard-rock pedal riff",
            "Study 3 - Gallop study",
            "Study 4 - Breakdown/chorus contrast",
        ])
        self.assertEqual(len(h[0]["pass_requirements"]), 6)
        self.assertEqual(
            [row["requirement_literal"] for row in h[0]["pass_requirements"]],
            list(candidate.H_PASS_REQUIREMENTS),
        )
        self.assertEqual(h[3]["fields"]["descriptor_literal"], "bars 1-4 sparse breakdown; 5-8 open chorus")
        self.assertIn("192 events", " ".join(self.item["source_specific_ambiguities"]))
        self.assertIsNone(self.module("H")["source_task_to_event_mapping"])

    def test_i_capstone_order_matches_at_motif_level_but_event_mapping_stays_blocked(self) -> None:
        relation = self.item["capstone_order_relation"]
        self.assertEqual(relation["txt_motifs"], list(candidate.CAPSTONE_TXT_MOTIFS))
        self.assertEqual(relation["pdf_roles"], list(candidate.CAPSTONE_PDF_ROLES))
        self.assertEqual(relation["bar_ranges"], ["1-4", "5-8", "9-12", "13-16", "17-20", "21-24", "25-28", "29-32"])
        self.assertEqual(relation["total_printed_bars"], 32)
        self.assertTrue(relation["ordered_correspondence"])
        self.assertIsNone(relation["event_mapping"])
        self.assertEqual(relation["event_declaration"]["txt_literal"], "256 events")
        self.assertEqual(relation["event_declaration"]["reconciliation_status"], "blocked_unresolved")
        self.assertIn("time signature", relation["event_declaration"]["reason"])

    def test_j_preserves_repairs_and_mastery_without_scoring_allocation(self) -> None:
        j = self.module("J")
        self.assertEqual(len(j["task_rows"]), 8)
        self.assertEqual(j["task_rows"][0]["fields"]["failure_literal"], "Palm mute kills pitch")
        self.assertEqual(j["task_rows"][7]["fields"]["immediate_repair_literal"], "quarter-note E pedal until next 4-bar boundary")
        mastery = self.item["mastery_comparison"]
        self.assertEqual(mastery["txt_literals"], ["14/16 or better on two separate days.", "No zero in pulse, gallop control, pedal/chord balance, or recovery."])
        self.assertIn("14/16 or better on two separate days", mastery["pdf_literal"])
        self.assertIsNone(mastery["scoring_allocation"])
        self.assertIn("no authored scoring allocation", " ".join(self.item["source_specific_ambiguities"]))

    def test_shared_attack_reference_remains_unassigned(self) -> None:
        reference = self.item["shared_unassigned_reference"]
        self.assertIsNone(reference["module_label"])
        self.assertEqual(reference["page_number"], 2)
        self.assertEqual([row["symbol_literal"] for row in reference["symbols"]], ["O", "M", "x", "-", ">", "~"])
        self.assertIn("after the attack pattern is stable", reference["guidance_literal"])
        self.assertEqual(reference["assignment_status"], "shared reference; no printed A-J module label")

    def test_every_page_ref_matches_predecessor_and_live_page_hash(self) -> None:
        refs = self.item["pdf_page_references"]
        self.assertEqual(len(refs), 15)
        self.assertEqual([ref["page_number"] for ref in refs], list(range(1, 16)))
        for ref in refs:
            self.assertEqual(ref["extracted_text_sha256"], candidate.EXPECTED_PAGE_HASHES[ref["page_number"]])
            self.assertEqual(ref["source_path"], candidate.PDF)
        for module in self.item["modules"]:
            for row in module["task_rows"]:
                ref = row["source_ref"]
                self.assertEqual(ref["page_text_sha256"], candidate.EXPECTED_PAGE_HASHES[ref["page_number"]])

    def test_numeric_parity_is_separate_from_event_model_and_output_has_no_events(self) -> None:
        workload = self.item["workload_reconciliation"]
        self.assertEqual(workload["txt_total_declaration"]["value"], 1536)
        self.assertEqual(workload["txt_module_sum"], 1536)
        self.assertEqual(workload["pdf_p1_total"], 1536)
        self.assertEqual(workload["printed_total_arithmetic"], "matched")
        self.assertEqual(workload["task_to_event_reconciliation"], "blocked_unresolved")
        self.assertFalse(self.item["runtime_eligible"])
        self.assertFalse(self.item["imported"])
        self.assertFalse(self.item["admitted"])
        self.assertFalse(self.item["whole_workbook_complete"])

        forbidden_keys = {
            "events", "event_id", "event_schedule", "onset", "onset_q", "duration",
            "duration_q", "bpm", "pitch", "midi", "fret", "playable_projection",
        }
        def walk(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    self.assertNotIn(key.lower(), forbidden_keys)
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        walk(self.item)

    def test_task_source_drift_is_refused(self) -> None:
        raw = candidate.safe_input(candidate.ROOT, candidate.TXT).read_bytes()
        changed = raw.replace(b"A. Eighth-note drive and palm-mute depth - 160 events", b"A. Changed title - 160 events", 1)
        with self.assertRaisesRegex(candidate.CandidateError, "TXT_MODULE_DRIFT"):
            candidate.parse_txt(changed)

    def test_git_root_and_output_path_boundaries_refuse_escape_and_overwrite(self) -> None:
        with self.assertRaisesRegex(candidate.CandidateError, "GIT_ROOT_MISMATCH"):
            candidate.assert_git_root(candidate.ROOT / "Build")

        with tempfile.TemporaryDirectory(prefix="level88-semantic-output-", dir=candidate.ROOT / "Build") as name:
            temp_root = Path(name)
            lane_build = temp_root / candidate.BUILD_REL
            lane_build.mkdir(parents=True)
            inside = lane_build / "fresh.json"
            self.assertEqual(candidate.validate_output_path(temp_root, inside), inside)
            with self.assertRaisesRegex(candidate.CandidateError, "OUTPUT_OUTSIDE_LANE_BUILD_ROOT"):
                candidate.validate_output_path(temp_root, temp_root / "outside.json")
            with self.assertRaisesRegex(candidate.CandidateError, "OUTPUT_PARENT_TRAVERSAL"):
                candidate.validate_output_path(temp_root, lane_build / ".." / "escape.json")
            inside.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(candidate.CandidateError, "OUTPUT_OVERWRITE_REFUSED"):
                candidate.validate_output_path(temp_root, inside)
            real = lane_build / "real"
            real.mkdir()
            alias = lane_build / "alias"
            alias.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(candidate.CandidateError, "OUTPUT_PATH_SYMLINK"):
                candidate.validate_output_path(temp_root, alias / "child.json")

    def test_candidate_serialization_is_deterministic(self) -> None:
        first = (json.dumps(self.item, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
        second = (json.dumps(candidate.build_candidate(), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
