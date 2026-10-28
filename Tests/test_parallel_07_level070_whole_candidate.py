"""Focused fidelity and determinism checks for detached whole Level 70."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("level70", ROOT / "Tools/parallel_07_level070_whole_candidate.py")
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class Level70CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.c = mod.build_candidate(ROOT)

    def test_printed_ledger_and_directional_choice(self) -> None:
        c = self.c
        self.assertEqual(c["source"]["txt"]["lines"], 533)
        self.assertEqual(c["source"]["pdf"]["pages"], 20)
        self.assertEqual(c["workload"]["module_tones"], mod.COUNTS)
        self.assertEqual(sum(x["tone_count"] for x in c["modules"].values()), 898)
        self.assertEqual({k: len(v["cells"]) for k, v in c["modules"].items()}, mod.CELLS)
        self.assertEqual([x["tone_count"] for x in c["modules"]["C"]["cells"]],
                         [16, 16, 14, 16, 16, 16])
        self.assertEqual([x["tone_count"] for x in c["modules"]["D"]["cells"]],
                         [18, 20, 12, 18, 20])
        self.assertEqual([x["tone_count"] for x in c["modules"]["F"]["cells"]], [12] * 5)
        for cell in c["modules"]["F"]["cells"]:
            self.assertEqual([e["note"] for e in cell["events"]],
                             ["E", "F#", "G#", "A", "A", "G#", "F#", "E", "A", "G", "F", "E"])
            self.assertEqual([e["form"] for e in cell["events"]],
                             ["ASC"] * 4 + ["SYM"] * 4 + ["CLS"] * 4)
        self.assertTrue(c["workload"]["module_f_both_descent_forms_written_and_counted"])
        self.assertFalse(c["workload"]["supplemental_seam_second_pass_counted"])
        self.assertFalse(c["workload"]["supplemental_sequence_translations_counted"])
        self.assertFalse(c["workload"]["supplemental_capstone_repeat_counted"])

    def test_grid_pdf_and_harmony(self) -> None:
        c = self.c
        grids = [x for k, m in c["modules"].items() if k != "B" for x in m["cells"]]
        self.assertEqual(len(grids), 39)
        self.assertEqual(sum(x["pdf_grid_status"] == "exact_row_parity" for x in grids), 29)
        self.assertEqual(sum(x["pdf_grid_status"] == "degree_finger_tab_without_note_row" for x in grids), 10)
        events = [e for grid in grids for e in grid["events"]]
        self.assertEqual(len(events), 730)
        self.assertTrue(all((mod.OPEN[e["string"]] + e["fret"]) % 12 == mod.PC[e["note"]]
                            and e["degree"] == mod.DEGREE[e["note"]] for e in events))
        self.assertTrue(all(e["onset_q"] is None and e["duration_q"] is None for e in events))
        self.assertEqual(sum(len(lane["events"]) for seam in c["modules"]["B"]["cells"]
                             for lane in seam["lanes"]), 168)
        self.assertEqual([s["pdf_page"] for s in c["modules"]["B"]["cells"]], [8, 8, 9, 9])
        self.assertTrue(all(s["pdf_grid_status"] == "degree_finger_tab_without_note_row"
                            for s in c["modules"]["B"]["cells"]))
        self.assertIsNone(c["stable_ids"])
        self.assertFalse(c["imported"])
        self.assertFalse(c["admitted"])

    def test_determinism_and_pinned_drift(self) -> None:
        self.assertEqual(json.dumps(self.c, sort_keys=True),
                         json.dumps(mod.build_candidate(ROOT), sort_keys=True))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for rel in (mod.TXT, mod.PDF, mod.MAP):
                dst = root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / rel, dst)
            target = root / mod.TXT
            blob = target.read_bytes()
            target.write_bytes(blob[:-1] + bytes([blob[-1] ^ 1]))
            with self.assertRaisesRegex(mod.CandidateError, "PINNED_INPUT_DRIFT"):
                mod.build_candidate(root)


if __name__ == "__main__":
    unittest.main()
