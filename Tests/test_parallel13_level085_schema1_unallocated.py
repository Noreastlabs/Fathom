"""Focused Level85 unallocated schema1 projection and loss/refusal checks."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel13_level085_schema1_unallocated as proposal  # noqa: E402


class Level85ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        proposal.check_pins()
        cls.replayed = proposal.source.build()
        cls.candidate = json.loads((ROOT / proposal.CANDIDATE).read_text())
        cls.output = proposal.project(cls.candidate, cls.replayed)

    def test_original_replay_and_page_provenance(self) -> None:
        self.assertEqual(self.candidate, self.replayed)
        self.assertEqual(hashlib.sha256((ROOT / proposal.CANDIDATE).read_bytes()).hexdigest(),
                         proposal.PINS[proposal.CANDIDATE])
        self.assertEqual(len(self.output["source_context"]["txt_lines"]), 40)
        pages = self.output["source_context"]["pdf_pages"]
        self.assertEqual(len(pages), 15)
        for page in pages:
            self.assertEqual(page["extracted_text_sha256"],
                             hashlib.sha256(page["extracted_text"].encode()).hexdigest())
        for row in self.output["rows"] + self.output["reference_rows"]:
            source = row["source_provenance"]
            self.assertEqual(source["pdf_extracted_text_sha256"],
                             pages[source["pdf_page"] - 1]["extracted_text_sha256"])
            self.assertEqual(row["source_row_sha256"],
                             proposal.sha(proposal.encoded(row["source_row"])))

    def test_count_coverage_empty_events_and_null_ids_timing(self) -> None:
        self.assertEqual((self.output["module_task_row_count"],
                          self.output["reference_row_count"]), (82, 6))
        self.assertEqual({m["source_module"]: len(m["task_keys"])
                          for m in self.output["modules"]}, proposal.COUNTS)
        self.assertEqual({m["source_module"]: m["declared_events"]
                          for m in self.output["modules"]}, proposal.MODULE_EVENTS)
        self.assertEqual(self.output["declared_total_events"], 1440)
        self.assertEqual(self.output["playable_event_count"], 0)
        self.assertEqual(len({r["source_local_key"] for r in
                              self.output["rows"] + self.output["reference_rows"]}), 88)
        for row in self.output["rows"] + self.output["reference_rows"]:
            self.assertIsNone(row["printed_event_allocation"])
            fields = row["schema1_fields"]
            self.assertEqual(fields["events"], [])
            self.assertEqual(fields["variants"], [])
            self.assertFalse(fields["runtime_eligible"])
            for key in ("id", "workbook_id", "module_id", "lineage", "content_revision",
                        "pitch", "route", "performed_result"):
                self.assertIsNone(fields[key])
            self.assertEqual(fields["timing"],
                             {"status": "unresolved", "onset_q": None,
                              "duration_q": None, "fixed_bpm": None,
                              "exact_microtiming_ms": None})

    def test_reference_remains_separate_with_literal_symbol_legend(self) -> None:
        context = self.output["source_context"]
        self.assertEqual(context["symbol_legend"],
                         {"P": "pitched contact", "x": "muted contact",
                          "-": "air stroke", "~": "sustain"})
        self.assertEqual(context["continuous_hand_motion"], "D U D U sixteenths")
        self.assertEqual({r["source_module"] for r in self.output["reference_rows"]}, {None})
        self.assertEqual({r["support_relation"] for r in self.output["reference_rows"]},
                         {"adjacent_unassigned_groove_reference"})
        self.assertEqual({r["source_provenance"]["pdf_page"]
                          for r in self.output["reference_rows"]}, {2})
        self.assertEqual({r["support_relation"] for r in self.output["rows"]}, {None})

    def test_a_b_c_d_e_f_g_source_semantics_remain_literal(self) -> None:
        rows = self.output["rows"]
        by = {letter: [r["source_row"]["semantic"] for r in rows if r["source_module"] == letter]
              for letter in proposal.COUNTS}
        self.assertTrue(all(r["fixed_harmony"] == "Am7" for r in by["A"]))
        self.assertTrue(all(r["tempo_change"] is False and
                            r["quarter_attacks_per_measure"] == 4 for r in by["B"]))
        self.assertTrue(all(r["ghost_pitch_allowed"] is False and
                            r["pitched_attack_events"] is None for r in by["C"]))
        self.assertTrue(all(r["imagined_drum_part"] is True for r in by["D"]))
        self.assertTrue(all(r["recorded_bass_supplied"] is False for r in by["E"]))
        self.assertTrue(all(r["exact_millisecond_target"] is None for r in by["F"]))
        self.assertTrue(all(r["complete_genre_definition"] is False for r in by["G"]))

    def test_h_studies_i_capstone_and_j_mastery_not_performed(self) -> None:
        rows = self.output["rows"]
        h = [r["source_row"]["semantic"] for r in rows if r["source_module"] == "H"]
        self.assertEqual(len(h), 24)
        for study in range(1, 5):
            group = [r for r in h if r["study"] == study]
            self.assertEqual([r["pass"] for r in group], list(range(1, 7)))
            self.assertEqual(len(group[0]["harmony_bars_literal"]), 8)
            self.assertTrue(all(r["performed_study"] is None for r in group))
        i = [r for r in rows if r["source_module"] == "I"]
        self.assertEqual([(r["source_row"]["semantic"]["bar_start"],
                           r["source_row"]["semantic"]["bar_end"]) for r in i],
                         [(n, n + 3) for n in range(1, 33, 4)])
        self.assertTrue(all(r["printed_event_allocation"] is None and
                            r["source_row"]["semantic"]["declared_events_for_range"] is None
                            for r in i))
        self.assertEqual(self.output["modules"][8]["declared_events"], 256)
        capstone = self.output["source_context"]["capstone"]
        self.assertTrue(capstone["one_underlying_tempo"])
        self.assertTrue(capstone["beat_four_announcement_required"])
        self.assertIsNone(capstone["per_four_bar_row_event_counts"])
        j = [r for r in rows if r["source_module"] == "J"]
        self.assertEqual(len(j), 8)
        self.assertTrue(all(r["source_row"]["semantic"]["observed_failure"] is None
                            for r in j))
        mastery = self.output["source_context"]["mastery"]
        self.assertEqual(mastery["minimum"], "14/16 or better on two separate days")
        self.assertEqual(mastery["protected_zero_domains"],
                         ["pulse", "note length", "muting", "recovery"])
        self.assertIsNone(mastery["observed_score"])

    def test_refuse_source_loss_count_reference_or_admission_drift(self) -> None:
        for mutate in (
            lambda c: c["modules"][0]["tasks"].pop(),
            lambda c: c["modules"][8].update(declared_events=257),
            lambda c: c["reference_rows"][0].update(relation="Module A"),
            lambda c: c["modules"][8]["tasks"][0]["semantic"].update(declared_events_for_range=32),
            lambda c: c["modules"][7]["tasks"][0]["semantic"].update(performed_study=True),
            lambda c: c["mastery"].update(minimum="12/16"),
            lambda c: c.update(runtime_eligible=True),
        ):
            bad = copy.deepcopy(self.candidate)
            mutate(bad)
            with self.assertRaises(proposal.ProposalError):
                proposal.project(bad, self.replayed)

    def test_refuse_projection_byte_drift(self) -> None:
        self.assertEqual(proposal.encoded(self.output),
                         proposal.encoded(proposal.project(self.candidate, self.replayed)))
        bad = copy.deepcopy(self.output)
        bad["rows"][0]["schema1_fields"]["events"] = [{"fabricated": True}]
        self.assertNotEqual(proposal.encoded(self.output), proposal.encoded(bad))


if __name__ == "__main__":
    unittest.main()
