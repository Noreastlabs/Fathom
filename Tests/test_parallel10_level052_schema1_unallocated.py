"""Focused source-to-field and refusal tests for Level52."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tools"))

from parallel10_level052_schema1_unallocated import (  # noqa: E402
    EXPECTED_COUNTS, ROOT, UNIT_KEYS, digest, encoded, pinned, project, read_inputs,
)


class Level52UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate, cls.foundation, cls.registry, cls.source_map = read_inputs(ROOT)
        cls.proposal, cls.handoff = project(cls.candidate, cls.foundation, cls.registry, cls.source_map)

    def test_all_attacks_and_silent_formations_stay_distinct(self) -> None:
        proposal = self.proposal
        self.assertEqual(proposal["counts"]["printed_attacks"], 976)
        self.assertEqual(proposal["counts"]["silent_formations"], 42)
        self.assertEqual(proposal["counts"]["attack_units"], 123)
        self.assertEqual(proposal["counts"]["attack_kinds"], {"blocked": 690, "arpeggio": 282, "muted_backbeat": 4})
        for module, expected in EXPECTED_COUNTS.items():
            record = next(r for r in proposal["records"] if r["source_component"] == module)
            events = record["schema1_fields"]["events"]
            self.assertEqual(len(events), expected)
            original = [attack for unit in self.candidate["modules"][module][UNIT_KEYS[module]]
                        for attack in unit["attacks"]]
            self.assertEqual([event["source_attack"] for event in events], original)
            for event in events:
                fields = event["schema1_fields"]
                self.assertIsNone(fields["event_id"])
                self.assertIsNone(fields["onset_q"])
                self.assertIsNone(fields["duration_q"])
                self.assertIsNone(fields["pick"])
                self.assertIsNone(fields["pitch_binding"])
                self.assertIsNone(event["performed_member_pitches"])
        silent = proposal["records"][-1]
        self.assertEqual(silent["source_component"], "silent_and_ear_tasks")
        self.assertEqual(silent["schema1_fields"]["events"], [])
        self.assertEqual(len(silent["silent_tasks"]["formations"]), 42)
        self.assertTrue(all(f["sound_attack"] is False for f in silent["silent_tasks"]["formations"]))
        self.assertEqual(silent["silent_tasks"]["pdf_first_attempt_threshold"], {"minimum_correct_per_quality": 18, "total_per_quality": 21})
        self.assertEqual(silent["silent_tasks"]["txt_mastery_separate_days"], 2)
        self.assertFalse(proposal["schema1_importable"])
        self.assertFalse(proposal["admitted"])

    def test_c_octave_alternative_and_f6_mutes(self) -> None:
        self.assertEqual(self.proposal["authored_alternatives"][0]["module_a_and_d_frets_g_b_e"], [0, 1, 0])
        self.assertEqual(self.proposal["authored_alternatives"][0]["module_e_quality_switch_frets_g_b_e"], [12, 13, 12])
        cycle = next(e for e in self.proposal["records"][1]["schema1_fields"]["events"]
                     if e["source_attack"]["chord"] == "C" and e["source_attack"]["inversion"] == "second_inversion")
        self.assertEqual(cycle["source_attack"]["frets_g_b_e"], [0, 1, 0])
        switch = next(e for e in self.proposal["records"][2]["schema1_fields"]["events"]
                      if e["source_attack"]["chord"] == "C" and e["source_attack"]["frets_g_b_e"] == [12, 13, 12])
        self.assertEqual(switch["source_attack"]["quality"], "major")
        patterns = self.proposal["records"][3]["schema1_fields"]
        f6_ordinals = patterns["variants"][5]["source_event_ordinals"]
        kinds = [patterns["events"][n - 1]["source_attack"]["kind"] for n in f6_ordinals]
        self.assertEqual(kinds, ["blocked", "muted_backbeat"] * 4)
        self.assertEqual(sum(patterns["events"][n - 1]["schema1_fields"]["contact"] == "muted" for n in f6_ordinals), 4)

    def test_source_drift_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.txt").write_bytes(b"changed original")
            with self.assertRaisesRegex(ValueError, "input drift"):
                pinned(root, "source.txt", "0" * 64)

    def test_invented_event_and_authority_refusals(self) -> None:
        candidate = copy.deepcopy(self.candidate)
        candidate["sounded_workload_attack_count"] = 977
        with self.assertRaisesRegex(ValueError, "976/42"):
            project(candidate, self.foundation, self.registry, self.source_map)
        candidate = copy.deepcopy(self.candidate)
        candidate["modules"]["patterns"]["patterns"][5]["attacks"][1]["sounded"] = True
        with self.assertRaisesRegex(ValueError, "muted backbeat"):
            project(candidate, self.foundation, self.registry, self.source_map)
        candidate = copy.deepcopy(self.candidate)
        candidate["modules"]["shape_workouts"]["shapes"][0]["attacks"][0]["member_midi"] = [60, 64, 67]
        with self.assertRaisesRegex(ValueError, "source attack field drift"):
            project(candidate, self.foundation, self.registry, self.source_map)
        candidate = copy.deepcopy(self.candidate)
        candidate["fixed_bpm"] = 80
        with self.assertRaisesRegex(ValueError, "invented authority/timing"):
            project(candidate, self.foundation, self.registry, self.source_map)
        candidate = copy.deepcopy(self.candidate)
        candidate["authored_alternatives"][0]["module_e_quality_switch_frets_g_b_e"] = [0, 1, 0]
        with self.assertRaisesRegex(ValueError, "octave alternative"):
            project(candidate, self.foundation, self.registry, self.source_map)

    def test_identity_boundary_and_determinism(self) -> None:
        foundation = copy.deepcopy(self.foundation)
        foundation["records"].append({"legacy_level": 52, "workbook_id": "fg:workbook:000052"})
        with self.assertRaisesRegex(ValueError, "unexpected canonical Level52"):
            project(self.candidate, foundation, self.registry, self.source_map)
        registry = copy.deepcopy(self.registry)
        registry["entities"].append({"id": "fg:workbook:000052"})
        with self.assertRaisesRegex(ValueError, "unexpected Level52 registry"):
            project(self.candidate, self.foundation, registry, self.source_map)
        again, handoff = project(self.candidate, self.foundation, self.registry, self.source_map)
        self.assertEqual(encoded(again), encoded(self.proposal))
        self.assertEqual(encoded(handoff), encoded(self.handoff))
        self.assertEqual(digest(encoded(again)), digest(encoded(self.proposal)))


if __name__ == "__main__":
    unittest.main()
