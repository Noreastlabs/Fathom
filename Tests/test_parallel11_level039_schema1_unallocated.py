"""Focused checks for Level39 whole-source unallocated schema1 field sketches."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel11_level039_schema1_unallocated as lane  # noqa: E402


class Level39UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.c, cls.row, cls.foundation, cls.registry, _ = lane.read_inputs(ROOT)
        cls.selected, cls.snapshot = lane.representative_boundary(cls.foundation, cls.registry)
        cls.proposal, cls.handoff = lane.project(cls.c, cls.row, cls.foundation, cls.registry)

    def test_sealed_twins_original_replay_source_map_and_selected_identity(self) -> None:
        self.assertEqual(self.c["source"]["txt"]["sha256"], lane.INPUTS[lane.TXT[0]])
        self.assertEqual(self.c["source"]["pdf"]["sha256"], lane.INPUTS[lane.PDF[0]])
        self.assertEqual(self.row["representative_item_id"], "fg:item:000006")
        self.assertEqual(self.snapshot["item_id"], "fg:item:000006")
        self.assertEqual(self.snapshot["variant_ids"], ["fg:variant:000038", "fg:variant:000039"])
        self.assertEqual(self.snapshot["content_revision"], 3)
        self.assertEqual(self.snapshot["lineage"], self.selected["lineage"])
        self.assertTrue(self.snapshot["read_only"])
        self.assertEqual(self.proposal["existing_selected_representative_read_only"], self.snapshot)
        bad = copy.deepcopy(self.foundation)
        next(r for r in bad["records"] if r.get("legacy_level") == 39)["content_revision"] = 4
        with self.assertRaisesRegex(ValueError, "representative identity/lineage drift"):
            lane.representative_boundary(bad, self.registry)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "source.txt").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "input drift"):
                lane.pinned(Path(d), "source.txt", "0" * 64)

    def test_seven_modules_386_printed_columns_462_written_occurrences(self) -> None:
        p = self.proposal
        self.assertEqual(p["counts"], {"provisional_components": 7, "source_printed_note_columns": 386,
                                       "written_sounding_tone_occurrences": 462,
                                       "module_tones": lane.COUNTS, "extra_performed_passes_observed": None})
        self.assertEqual([r["source_component"] for r in p["records"]], list("ABCDEFG"))
        self.assertEqual([sum(u["source_written_sounding_tones"] for u in r["unit_field_proposals"])
                          for r in p["records"]], list(lane.COUNTS.values()))
        self.assertEqual(sum(u["source_printed_note_columns"] for r in p["records"]
                             for u in r["unit_field_proposals"]), 386)
        self.assertEqual(sum(len(u["event_field_proposals"]) for r in p["records"]
                             for u in r["unit_field_proposals"]), 462)
        self.assertEqual([len(u["event_field_proposals"]) for u in p["records"][0]["unit_field_proposals"]], [16] * 5)
        self.assertEqual(len(p["records"][3]["unit_field_proposals"][0]["event_field_proposals"]), 48)

    def test_every_note_tab_finger_pitch_and_frozen_degree_object_shape(self) -> None:
        self.assertEqual(set(self.selected["events"][0]["degree_contexts"]["A-major"]),
                         {"alteration", "ordinal", "source_label"})
        first = self.proposal["records"][0]["unit_field_proposals"][0]["event_field_proposals"][:8]
        self.assertEqual([e["schema1_fields"]["degree_contexts"] for e in first],
                         [e["degree_contexts"] for e in self.selected["events"]])
        for r in self.proposal["records"]:
            for u in r["unit_field_proposals"]:
                for e in u["event_field_proposals"]:
                    n, f = e["source_note"], e["schema1_fields"]
                    self.assertEqual(f["spelling"], n["note"])
                    self.assertEqual(f["string"], lane.STRING_NUMBER[n["string"]])
                    self.assertEqual(f["fret"], n["fret"])
                    self.assertEqual(f["finger"], n["finger"])
                    self.assertEqual(f["midi"], lane.OPEN[n["string"]] + n["fret"])
                    self.assertEqual(f["midi"] % 12, lane.ROLES[n["note"]][2])
                    self.assertEqual(f["degree_contexts"], lane.degree_contexts(n))
                    for context in ("A-major", "F#-minor"):
                        d = f["degree_contexts"][context]
                        self.assertEqual(set(d), {"alteration", "ordinal", "source_label"})
                        self.assertEqual(d["alteration"], -1 if d["source_label"].startswith("b") else 0)
        c = self.c["modules"]["C_root_to_root_cells"]
        self.assertTrue(all(u["events"][len(u["events"]) // 2 - 1] ==
                            {**u["events"][len(u["events"]) // 2], "ordinal": len(u["events"]) // 2}
                            for u in c))

    def test_source_differences_contexts_answers_and_guidance(self) -> None:
        p = self.proposal
        self.assertEqual(len(p["source_presentation_differences"]), 24)
        self.assertEqual([sum(d["module"] == k for d in p["source_presentation_differences"]) for k in "AEFG"], [5, 10, 1, 8])
        self.assertEqual([d["kind"] for d in p["source_guidance_variants"]],
                         ["PDF_attack_weight_clarification", "PDF_partner_call_task",
                          "PDF_quarter_and_swing_practice_guidance", "PDF_second_pass_final_note_two_beat_hold"])
        self.assertEqual(len(p["source_guidance"]["txt_full_lines"]), 520)
        self.assertEqual(len(p["source_guidance"]["pdf_full_extracted_pages"]), 12)
        self.assertEqual(p["F_sharp_root_atlas"], [{"string": s, "fret": f} for s, f in lane.F_ROOTS])
        d = self.c["modules"]["D_accent_relocation"]
        self.assertEqual(d["A_accent_ordinals"], [2, 7, 12])
        self.assertEqual(d["F_sharp_accent_ordinals"], [1, 6, 11])
        self.assertEqual(self.c["modules"]["F_tonic_pivot"]["center_by_bar"], ["A", "A", "F#", "F#", "A", "A", "F#", "F#"])
        self.assertEqual([u["printed_answer"] for u in self.c["modules"]["G_ear_cards"]], ["A-centered", "F#-centered"] * 4)
        self.assertIsNone(p["auditory_judgment_observed"])
        self.assertIsNone(p["performed_mastery_observed"])

    def test_refuses_source_mutations_and_invented_identity_timing(self) -> None:
        edits = [
            (lambda c: c["counts"].update(A=81), "7/462/module source count drift"),
            (lambda c: c["modules"]["B_dual_degree_boxes"][0]["events"][0].update(fret=6), "printed row/note/TAB/finger/dual-degree drift"),
            (lambda c: c["modules"]["A_drone_comparison"][0].update(drone_contexts=["A"]), "A/D/F/G source role/pass/answer drift"),
            (lambda c: c["modules"]["D_accent_relocation"].update(A_accent_ordinals=[1, 7, 12]), "A/D/F/G source role/pass/answer drift"),
            (lambda c: c["source_presentation_differences"].pop(), "presentation difference/guidance variant drift"),
            (lambda c: c.update(onset_q=0), "source identity/admission/timing drift"),
            (lambda c: c.update(admitted=True), "source identity/admission/timing drift"),
        ]
        for edit, message in edits:
            with self.subTest(message=message):
                bad = copy.deepcopy(self.c)
                edit(bad)
                with self.assertRaisesRegex(ValueError, message):
                    lane.validate_candidate(bad, self.selected)
        self.assertFalse(self.proposal["schema1_importable"])
        self.assertFalse(self.proposal["admitted"])
        for r in self.proposal["records"]:
            f = r["schema1_fields"]
            for key in ("id", "workbook_id", "module_id", "content_revision", "lineage"):
                self.assertIsNone(f[key])
            self.assertFalse(f["runtime_eligible"])
            self.assertIsNone(f["timing"]["fixed_bpm"])
            self.assertIsNone(f["timing"]["note_per_click"])
            for u in r["unit_field_proposals"]:
                self.assertIsNone(u["variant_id"])
                self.assertIsNone(u["performed_passes_observed"])
                for e in u["event_field_proposals"]:
                    for key in ("event_id", "attack", "onset_q", "duration_q", "pick", "accent", "performed"):
                        self.assertIsNone(e["schema1_fields"][key])

    def test_deterministic_products_and_verify(self) -> None:
        a = lane.products(ROOT)
        b = lane.products(ROOT)
        self.assertEqual({k: lane.encoded(v) for k, v in a.items()},
                         {k: lane.encoded(v) for k, v in b.items()})
        lane.run("verify", ROOT)
        self.assertEqual(a["summary.json"]["proposal_sha256"], lane.digest(lane.encoded(a["field-proposal.json"])))


if __name__ == "__main__":
    unittest.main()
