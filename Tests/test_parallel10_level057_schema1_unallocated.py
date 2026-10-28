"""Focused Level57 source attack, silent formation, and authority checks."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tools"))

from parallel10_level057_schema1_unallocated import (  # noqa: E402
    COUNTS, ROOT, _units, digest, encoded, pinned, project, read_inputs,
)


class Level57UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate, cls.foundation, cls.registry = read_inputs(ROOT)
        cls.proposal, cls.handoff = project(cls.candidate, cls.foundation, cls.registry)

    def test_every_printed_attack_and_silent_formation(self) -> None:
        self.assertEqual(self.proposal["counts"], {"provisional_components": 9,
            "attack_units": 90, "silent_formations": 56, "printed_attacks": 796})
        a = self.proposal["records"][0]
        self.assertEqual(a["schema1_fields"]["events"], [])
        self.assertEqual(len(a["silent_tasks"]), 56)
        self.assertTrue(all(t["performed"] is None for t in a["silent_tasks"]))
        for name, count in COUNTS.items():
            module = self.candidate["modules"][name]
            expected = [attack for unit in _units(name, module) for attack in unit["attacks"]]
            record = self.proposal["records"][ord(name[0]) - ord("A")]
            events = record["schema1_fields"]["events"]
            self.assertEqual(len(events), count)
            self.assertEqual([e["source_attack"] for e in events], expected)
            self.assertEqual([e["source_local_ordinal"] for e in events], list(range(1, count + 1)))
            self.assertTrue(all(e["schema1_fields"]["event_id"] is None and
                                e["schema1_fields"]["onset_q"] is None and
                                e["schema1_fields"]["duration_q"] is None and
                                e["schema1_fields"]["pick"] is None and
                                e["schema1_fields"]["pitch_binding"] is None for e in events))
        self.assertFalse(self.proposal["schema1_importable"])
        self.assertFalse(self.proposal["admitted"])

    def test_specific_source_limits_and_pdf_alternatives(self) -> None:
        b = self.proposal["records"][1]["schema1_fields"]["variants"]
        c = self.proposal["records"][2]["schema1_fields"]["variants"]
        self.assertEqual([len(v["source_event_ordinals"]) for v in b + c], [4] * 56)
        self.assertEqual(len(self.proposal["records"][3]["schema1_fields"]["variants"]), 2)
        f = self.proposal["records"][5]["source_module"]
        self.assertTrue(all(cell["preparatory_full_iiø"]["counted_in_printed_18"] is False
                            for cell in f["cells"]))
        self.assertFalse(f["supplemental_pdf_alternative"]["counted_in_printed_108"])
        self.assertFalse(self.proposal["records"][4]["source_module"]["supplemental_pdf_alternative"]["counted_in_printed_108"])
        g = self.proposal["records"][6]["schema1_fields"]["events"]
        self.assertEqual([len(p["attacks"]) for p in self.candidate["modules"]["G_A_blues"]["passes"]],
                         [12, 24, 24, 48])
        unknown = [e for e in g if e["source_attack"]["kind"] == "three_note_arpeggio_unspecified_contact"]
        self.assertEqual(len(unknown), 36)
        self.assertTrue(all(e["source_attack"]["contacts"] == [] and
                            e["source_attack"]["contact_selection"] is None for e in unknown))
        i = self.proposal["records"][8]["source_module"]
        self.assertTrue(all(block["preparatory_full_iiø"]["counted_in_printed_64"] is False
                            for block in i["minor"]["blocks"]))
        self.assertEqual(len(self.candidate["source_transcription"]["txt_lines"]), 741)
        self.assertEqual(len(self.candidate["source_transcription"]["pdf_pages"]), 20)
        self.assertTrue(self.proposal["musical_limits"]["flat_fifth_restoration_required"])

    def test_source_and_count_refusals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.txt").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "input drift"):
                pinned(root, "source.txt", "0" * 64)
        candidate = copy.deepcopy(self.candidate)
        candidate["workload"]["sounded_attacks"] = 797
        with self.assertRaisesRegex(ValueError, "796/56"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["musical_limits"]["blues_pass4_arpeggio_contacts"] = "E-A-D"
        with self.assertRaisesRegex(ValueError, "musical/count"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["modules"]["B_E_root_families"]["families"][0]["shapes"][0]["attacks"][0]["onset_q"] = 0
        with self.assertRaisesRegex(ValueError, "performance boundary"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        unknown = candidate["modules"]["G_A_blues"]["passes"][3]["attacks"][1]
        unknown["contacts"] = [{"string": "A", "fret": 0}]
        with self.assertRaisesRegex(ValueError, "invented blues"):
            project(candidate, self.foundation, self.registry)

    def test_identity_boundary_and_determinism(self) -> None:
        foundation = copy.deepcopy(self.foundation)
        foundation["records"].append({"legacy_level": 57, "workbook_id": "fg:workbook:000057"})
        with self.assertRaisesRegex(ValueError, "unexpected canonical Level57"):
            project(self.candidate, foundation, self.registry)
        registry = copy.deepcopy(self.registry)
        registry["entities"].append({"id": "fg:workbook:000057"})
        with self.assertRaisesRegex(ValueError, "unexpected Level57 registry"):
            project(self.candidate, self.foundation, registry)
        again, handoff = project(self.candidate, self.foundation, self.registry)
        self.assertEqual(encoded(again), encoded(self.proposal))
        self.assertEqual(encoded(handoff), encoded(self.handoff))
        self.assertEqual(digest(encoded(again)), digest(encoded(self.proposal)))


if __name__ == "__main__":
    unittest.main()
