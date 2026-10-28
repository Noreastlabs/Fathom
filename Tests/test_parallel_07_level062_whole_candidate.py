"""Focused Level 62 whole-candidate source and event checks."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("level62", ROOT / "Tools/parallel_07_level062_whole_candidate.py")
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class Level62CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = mod.build_candidate(ROOT)

    def test_counts_and_source_scope(self) -> None:
        c = self.candidate
        self.assertEqual(c["source"]["txt"]["lines"], 874)
        self.assertEqual(c["source"]["pdf"]["pages"], 20)
        self.assertEqual(c["workload"]["module_tones"], mod.EXPECTED)
        self.assertEqual(sum(m["tone_count"] for m in c["modules"].values()), 788)
        self.assertEqual({letter: len(m["cells"]) for letter, m in c["modules"].items()}, mod.CELL_COUNTS)
        self.assertEqual([cell["tone_count"] for cell in c["modules"]["H"]["cells"]],
                         [8, 8, 8, 8, 8, 12, 12, 4])
        self.assertEqual(len(c["modules"]["J"]["recovery_cards"]), 12)
        self.assertEqual(sum(x["tone_count"] for x in c["modules"]["J"]["recovery_cards"]), 24)
        self.assertEqual(sum(x["tone_count"] for x in c["modules"]["J"]["cells"]), 40)

    def test_tab_pdf_and_unassigned_timing(self) -> None:
        c = self.candidate
        cells = [cell for m in c["modules"].values() for cell in m["cells"]]
        self.assertEqual(len(cells), 71)
        self.assertEqual(sum(x["pdf_grid_status"] == "exact_row_parity" for x in cells), 66)
        self.assertEqual(sum(x["pdf_grid_status"] == "summary_only" for x in cells), 5)
        self.assertTrue(all(event["onset_q"] is None and event["duration_q"] is None
                            for cell in cells for event in cell["events"]))
        self.assertTrue(all((mod.OPEN[event["string"]] + event["fret"]) % 12 == mod.PC[event["note"]]
                            for cell in cells for event in cell["events"]))
        self.assertEqual(c["modules"]["I"]["cells"][0]["chords_by_bar"],
                         ["Dm7", "G7", "Cmaj7", "Cmaj7"])
        self.assertEqual(c["modules"]["I"]["cells"][4]["chords_by_bar"],
                         ["Bm7b5", "E7", "Am7", "Am7"])
        self.assertIn("rest - notes 1-2", c["pdf_only_directions"]["motif_grid"])
        self.assertEqual(len(c["pdf_only_directions"]["module_page_guidance"]), 16)
        self.assertIsNone(c["stable_ids"])
        self.assertFalse(c["admitted"])

    def test_determinism_and_source_drift(self) -> None:
        self.assertEqual(json.dumps(self.candidate, sort_keys=True),
                         json.dumps(mod.build_candidate(ROOT), sort_keys=True))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for rel in (mod.TXT, mod.PDF, mod.MAP):
                dst = root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / rel, dst)
            txt = root / mod.TXT
            blob = txt.read_bytes()
            txt.write_bytes(blob[:-1] + bytes([blob[-1] ^ 1]))
            with self.assertRaisesRegex(mod.CandidateError, "PINNED_INPUT_DRIFT"):
                mod.build_candidate(root)


if __name__ == "__main__":
    unittest.main()
