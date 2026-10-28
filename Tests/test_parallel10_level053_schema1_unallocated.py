"""Focused Level53 whole-source field and authority refusals."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tools"))

from parallel10_level053_schema1_unallocated import (  # noqa: E402
    COUNTS, ROOT, digest, encoded, pinned, project, read_inputs,
)


class Level53UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate, cls.foundation, cls.registry = read_inputs(ROOT)
        cls.proposal, cls.handoff = project(cls.candidate, cls.foundation, cls.registry)

    def test_exact_attack_projection_and_silent_separation(self) -> None:
        proposal = self.proposal
        self.assertEqual(proposal["counts"]["printed_attacks"], 1248)
        self.assertEqual(proposal["counts"]["silent_formations"], 168)
        self.assertEqual(proposal["counts"]["silent_formulas"], 24)
        self.assertEqual(proposal["counts"]["attack_units"], 248)
        self.assertEqual([r["source_component"] for r in proposal["records"]], list(COUNTS))
        for module, expected in COUNTS.items():
            record = next(r for r in proposal["records"] if r["source_component"] == module)
            events = record["schema1_fields"]["events"]
            original = [attack for unit in self.candidate["modules"][module]["units"] for attack in unit["attacks"]]
            self.assertEqual(len(events), expected)
            self.assertEqual([e["source_attack"] for e in events], original)
            for event in events:
                fields = event["schema1_fields"]
                self.assertIsNone(fields["event_id"])
                self.assertIsNone(fields["onset_q"])
                self.assertIsNone(fields["duration_q"])
                self.assertIsNone(fields["pick"])
                self.assertIsNone(fields["pitch_binding"])
                self.assertIsNone(event["performed_member_pitches"])
        a = proposal["records"][0]
        self.assertEqual(a["schema1_fields"]["events"], [])
        self.assertEqual(len(a["silent_tasks"]["formations"]), 168)
        self.assertEqual(len(a["silent_tasks"]["formulas"]), 24)
        self.assertTrue(all(f["performed"] is None for f in a["silent_tasks"]["formations"]))
        self.assertFalse(proposal["schema1_importable"])
        self.assertFalse(proposal["admitted"])

    def test_octave_pdf_detail_and_unbound_voice_picks(self) -> None:
        b = self.proposal["records"][1]["schema1_fields"]["variants"]
        d = self.proposal["records"][3]["schema1_fields"]["variants"]
        b_c2 = next(v["source_unit"] for v in b if v["source_unit"]["set"] == "123" and v["source_unit"]["chord"] == "C" and v["source_unit"]["inversion"] == "2nd")
        d_c2 = next(v["source_unit"] for v in d if v["source_unit"]["set"] == "123" and v["source_unit"]["inversion"] == "2nd")
        self.assertEqual(b_c2["frets"], [0, 1, 0])
        self.assertEqual(d_c2["major_frets"], [12, 13, 12])
        f = self.proposal["records"][5]["schema1_fields"]
        self.assertTrue(all(v["source_unit"]["pdf_only_detail"] for v in f["variants"][6:8]))
        voice_picks = [e for e in f["events"] if e["source_attack"]["kind"] == "individual voice pick"]
        self.assertEqual(len(voice_picks), 38)
        self.assertTrue(all(e["source_tone"]["fret"] is None and e["source_tone"]["sounding_midi"] is None for e in voice_picks))
        self.assertIn("Pass at least 30 of 42 random prompts", self.proposal["printed_guidance"]["txt_full_text"])
        self.assertEqual(len(self.proposal["source_exceptions"]), 4)

    def test_source_hash_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.txt").write_bytes(b"changed original")
            with self.assertRaisesRegex(ValueError, "input drift"):
                pinned(root, "source.txt", "0" * 64)

    def test_invented_attack_and_authority_refusals(self) -> None:
        candidate = copy.deepcopy(self.candidate)
        candidate["printed_attack_count"] = 1249
        with self.assertRaisesRegex(ValueError, "1248/168"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["modules"]["B"]["units"][0]["attacks"][0]["member_midi"] = [60, 64, 67]
        with self.assertRaisesRegex(ValueError, "source attack field"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["modules"]["F"]["units"][1]["attacks"][0]["fret"] = 10
        with self.assertRaisesRegex(ValueError, "unprinted fret"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["modules"]["A"]["formations"][0]["performed"] = True
        with self.assertRaisesRegex(ValueError, "silent formation"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["source_exceptions"].pop()
        with self.assertRaisesRegex(ValueError, "source-specific exceptions"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["performed_bpm"] = 90
        with self.assertRaisesRegex(ValueError, "invented authority/performance"):
            project(candidate, self.foundation, self.registry)

    def test_identity_boundary_and_determinism(self) -> None:
        changed = copy.deepcopy(self.foundation)
        changed["records"].append({"legacy_level": 53, "workbook_id": "fg:workbook:000053"})
        with self.assertRaisesRegex(ValueError, "unexpected canonical Level53"):
            project(self.candidate, changed, self.registry)
        changed = copy.deepcopy(self.registry)
        changed["entities"].append({"id": "fg:workbook:000053"})
        with self.assertRaisesRegex(ValueError, "unexpected Level53 registry"):
            project(self.candidate, self.foundation, changed)
        again, handoff = project(self.candidate, self.foundation, self.registry)
        self.assertEqual(encoded(again), encoded(self.proposal))
        self.assertEqual(encoded(handoff), encoded(self.handoff))
        self.assertEqual(digest(encoded(again)), digest(encoded(self.proposal)))


if __name__ == "__main__":
    unittest.main()
