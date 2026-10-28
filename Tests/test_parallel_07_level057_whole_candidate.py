"""Focused fidelity and determinism checks for the detached Level 57 candidate."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "level57_candidate", ROOT / "Tools/parallel_07_level057_whole_candidate.py")
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class Level57CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = module.build_candidate(ROOT)

    def test_printed_counts_and_silent_boundary(self) -> None:
        candidate = self.candidate
        self.assertEqual(candidate["workload"]["sounded_attacks"], 796)
        self.assertEqual(sum(candidate["workload"]["module_attacks"].values()), 796)
        self.assertEqual(candidate["modules"]["A_silent_formations"]["count"], 56)
        self.assertFalse(candidate["modules"]["A_silent_formations"]["sounded"])
        self.assertEqual(len(candidate["modules"]["B_E_root_families"]["families"]), 4)
        self.assertEqual(len(candidate["modules"]["C_A_root_families"]["families"]), 4)
        self.assertEqual([p["attack_count"] for p in candidate["modules"]["G_A_blues"]["passes"]],
                         [12, 24, 24, 48])

    def test_musical_constraints_and_source_gaps(self) -> None:
        c = self.candidate
        families = (c["modules"]["B_E_root_families"]["families"] +
                    c["modules"]["C_A_root_families"]["families"])
        for family in families:
            self.assertEqual(len(family["shapes"]), 7)
            for shape in family["shapes"]:
                self.assertEqual(len(shape["attacks"]), 4)
                self.assertEqual(len(shape["contacts"]), 4)
                self.assertTrue(shape["silent_formation_before_first_attack"])
        for cell in c["modules"]["F_minor_cadences"]["cells"]:
            self.assertEqual(len(cell["attacks"]), 18)
            self.assertFalse(cell["preparatory_full_iiø"]["counted_in_printed_18"])
        for block in c["modules"]["I_capstones"]["minor"]["blocks"]:
            self.assertFalse(block["preparatory_full_iiø"]["counted_in_printed_64"])
        fourth = c["modules"]["G_A_blues"]["passes"][3]
        self.assertEqual([fourth["attacks"][i * 4]["register"] for i in range(12)],
                         ["low"] * 4 + ["middle"] * 4 + ["high"] * 4)
        self.assertEqual(len([a for a in fourth["attacks"] if a.get("contact_selection") is None and
                              a["kind"] == "three_note_arpeggio_unspecified_contact"]), 36)
        self.assertTrue(all(a["contacts"] == [] for a in fourth["attacks"]
                            if a["kind"] == "three_note_arpeggio_unspecified_contact"))
        for scan in c["modules"]["H_arpeggio_scans"]["scans"]:
            self.assertEqual(len(scan["attacks"]), 8)
            self.assertEqual(scan["attacks"][3]["contacts"], scan["attacks"][4]["contacts"])

    def test_deterministic_and_pinned_drift_rejected(self) -> None:
        first = json.dumps(self.candidate, ensure_ascii=False, sort_keys=True)
        second = json.dumps(module.build_candidate(ROOT), ensure_ascii=False, sort_keys=True)
        self.assertEqual(first, second)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for rel in (module.TXT_REL, module.PDF_REL):
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / rel, target)
            txt = root / module.TXT_REL
            content = txt.read_bytes()
            txt.write_bytes(content[:-1] + bytes([content[-1] ^ 1]))
            with self.assertRaisesRegex(module.CandidateError, "PINNED_INPUT_DRIFT TXT"):
                module.build_candidate(root)


if __name__ == "__main__":
    unittest.main()
