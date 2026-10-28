"""Focused checks for detached whole-Level43 unallocated schema1 fields."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel11_level043_schema1_unallocated as lane  # noqa: E402


class Level43UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.c, cls.row, cls.foundation, cls.registry = lane.read_inputs(ROOT)
        cls.proposal, cls.handoff = lane.project(cls.c, cls.row, cls.foundation, cls.registry)

    def test_sealed_replay_original_pins_source_map_and_catalog(self) -> None:
        self.assertEqual(self.c["source"]["txt_sha256"], lane.INPUTS[lane.TXT_REL])
        self.assertEqual(self.c["source"]["pdf_sha256"], lane.INPUTS[lane.PDF_REL])
        self.assertEqual(self.c["source"]["source_map_sha256"], lane.INPUTS[lane.MAP_REL])
        self.assertEqual(self.row["conversion_status"], "not_converted")
        self.assertEqual(self.handoff["existing_level043_records"], 0)
        self.assertEqual(self.handoff["existing_level043_workbook_entities"], 0)
        bad = copy.deepcopy(self.foundation)
        entry = next(e for e in bad["workbook_catalog"]["entries"] if e["workbook_id"] == "fg:workbook:000043")
        entry["admitted"] = True
        with self.assertRaisesRegex(ValueError, "source-only catalog drift"):
            lane.identity_boundary(bad, self.registry)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "source.txt").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "input drift"):
                lane.pinned(Path(d), "source.txt", "0" * 64)

    def test_nine_modules_422_tones_382_attacks_and_all_source_text(self) -> None:
        p = self.proposal
        self.assertEqual(p["counts"]["provisional_components"], 9)
        self.assertEqual(p["counts"]["source_units"], 50)
        self.assertEqual(p["counts"]["core_sounding_tones"], 422)
        self.assertEqual(p["counts"]["core_printed_pick_attacks"], 382)
        self.assertEqual(p["counts"]["unpicked_arrivals"], 40)
        self.assertEqual([r["source_component"] for r in p["records"]], list("ABCDEFGHI"))
        self.assertEqual([len(r["unit_field_proposals"]) for r in p["records"]], list(lane.UNIT_COUNTS.values()))
        self.assertEqual([tuple(p["counts"]["module_tones_and_attacks"][k]) for k in "ABCDEFGHI"], list(lane.MODULE_COUNTS.values()))
        self.assertEqual(sum(len(u["event_field_proposals"]) for r in p["records"] for u in r["unit_field_proposals"]), 422)
        self.assertEqual(sum(e["schema1_fields"]["printed_pick_attack"] for r in p["records"]
                             for u in r["unit_field_proposals"] for e in u["event_field_proposals"]), 382)
        self.assertEqual(len(p["printed_guidance"]["txt_full_text"].splitlines()), 554)
        self.assertEqual(len(p["printed_guidance"]["pdf_extracted_pages"]), 17)

    def test_note_geometry_reference_turn_slides_seams_and_rest_slots(self) -> None:
        a = self.proposal["records"][0]["unit_field_proposals"]
        self.assertEqual([u["source_sounding_tones"] for u in a], [7, 7, 13, 13])
        self.assertTrue(all(a[i]["source_unit"]["contacts"][-1]["note"] == "A" and
                            a[i + 1]["source_unit"]["contacts"][0]["note"] == "A" for i in (0, 2)))
        self.assertEqual(self.proposal["scale"]["blue_note"]["extension"], {"string": "A", "frets": [17, 18, 19]})
        for r in self.proposal["records"]:
            for u in r["unit_field_proposals"]:
                for e in u["event_field_proposals"]:
                    source, fields = e["source_contact"], e["schema1_fields"]
                    self.assertEqual(fields["spelling"], source["note"])
                    self.assertEqual(fields["source_degree"], lane.DEGREE[source["note"]])
                    self.assertEqual(fields["string"], lane.STRING_NUMBER[source["string"]])
                    self.assertEqual(fields["fret"], source["fret"])
                    self.assertEqual(fields["finger"], source["printed_finger"])
                    self.assertEqual(fields["midi"], lane.OPEN_MIDI[source["string"]] + source["fret"])
                    self.assertEqual(fields["midi"] % 12, lane.PITCH[source["note"]])
        f = self.proposal["records"][5]
        self.assertEqual([sum(e["schema1_fields"]["printed_pick_attack"] for e in u["event_field_proposals"])
                          for u in f["unit_field_proposals"]], [2] * 6)
        self.assertEqual([e["schema1_fields"]["printed_pick_attack"] for e in f["unit_field_proposals"][0]["event_field_proposals"]],
                         [True, False, False, True, False, False])
        g = self.proposal["records"][6]
        self.assertTrue(all(u["source_unit"]["reverse_variation"]["authored_reverse_contacts"] is None for u in g["unit_field_proposals"]))
        h = self.proposal["records"][7]
        self.assertEqual([sum(s["schema1_fields"]["kind"] == "rest" for s in u["printed_slot_field_proposals"])
                          for u in h["unit_field_proposals"]], [2, 2, 6])

    def test_pdf_only_panel_and_source_guidance_do_not_add_core_events(self) -> None:
        p = self.proposal
        self.assertEqual(p["source_exceptions"][0]["code"], "PDF_ONLY_POST_CLEAN_VARIATIONS")
        self.assertEqual(p["source_exceptions"][0]["status"], "Pending Curriculum review")
        self.assertEqual(p["counts"]["supplemental_pdf_p16_core_tones"], 0)
        self.assertIn("Hold Eb for one, two, and four beats", p["printed_guidance"]["pdf_only_post_clean_variations"])
        self.assertIn("one note per click", p["printed_guidance"]["txt_full_text"])
        self.assertIn("PRACTICE LOG", p["printed_guidance"]["txt_full_text"])
        self.assertEqual(len(p["printed_guidance"]["core_alternatives"]), 6)
        self.assertEqual(p["music_row_exceptions"], [])

    def test_refuses_mutated_counts_geometry_roles_and_invented_admission(self) -> None:
        edits = [
            (lambda c: c.update(sounding_tone_count=423), "9/422/382 source count drift"),
            (lambda c: c["modules"][5]["units"][0]["contacts"][1].update(printed_pick_attack=True), "contact/count/source drift"),
            (lambda c: c["modules"][5]["units"][0]["contacts"][1].update(fret=12), "note/degree/string/fret/finger/performance drift"),
            (lambda c: c["modules"][6]["units"][0]["reverse_variation"].update(authored_reverse_contacts=[]), "seam/reverse instruction drift"),
            (lambda c: c["modules"][7]["units"][0]["slots"][1].update(contact=c["modules"][7]["units"][0]["contacts"][0]), "rest/slot drift"),
            (lambda c: c["source_exceptions"][0].update(status="Resolved"), "PDF-only post-clean/source exception drift"),
            (lambda c: c.update(admitted=True), "source identity/admission/performance drift"),
        ]
        for edit, message in edits:
            with self.subTest(message=message):
                bad = copy.deepcopy(self.c)
                edit(bad)
                with self.assertRaisesRegex(ValueError, message):
                    lane.validate_candidate(bad)
        self.assertFalse(self.proposal["schema1_importable"])
        self.assertFalse(self.proposal["admitted"])
        self.assertIsNone(self.proposal["performed_mastery_observed"])
        for r in self.proposal["records"]:
            fields = r["schema1_fields"]
            for key in ("id", "workbook_id", "module_id", "content_revision", "lineage"):
                self.assertIsNone(fields[key])
            self.assertFalse(fields["runtime_eligible"])
            self.assertIsNone(fields["timing"]["fixed_bpm"])
            self.assertIsNone(fields["timing"]["note_per_click"])
            for u in r["unit_field_proposals"]:
                self.assertIsNone(u["canonical_variant_id"])
                self.assertIsNone(u["actual_option_selected"])
                for e in u["event_field_proposals"]:
                    for key in ("event_id", "attack", "pick", "onset_q", "duration_q", "performed"):
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
