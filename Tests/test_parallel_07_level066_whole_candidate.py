"""Focused fidelity and deterministic checks for the detached Level 66 workbook."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("level66", ROOT / "Tools/parallel_07_level066_whole_candidate.py")
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class Level66CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.c = mod.build_candidate(ROOT)

    def test_printed_ledger_and_supplemental_boundaries(self) -> None:
        c = self.c
        self.assertEqual(c["source"]["txt"]["lines"], 503)
        self.assertEqual(c["source"]["pdf"]["pages"], 20)
        self.assertEqual(c["workload"]["module_tones"], mod.COUNTS)
        self.assertEqual(sum(x["tone_count"] for x in c["modules"].values()), 898)
        self.assertEqual({k: len(v["cells"]) for k, v in c["modules"].items()}, mod.CELLS)
        self.assertEqual([x["tone_count"] for x in c["modules"]["C"]["cells"]],
                         [16, 16, 14, 16, 16, 16])
        self.assertEqual([x["tone_count"] for x in c["modules"]["D"]["cells"]],
                         [18, 20, 12, 18, 20])
        self.assertEqual(sum(x["tone_count"] for x in c["modules"]["E"]["cells"][:5]), 90)
        self.assertEqual(sum(x["tone_count"] for x in c["modules"]["E"]["cells"][5:]), 90)
        self.assertTrue(all(x["repeat_twice_instruction"] and not x["repeat_counted_in_printed_898"]
                            for x in c["modules"]["B"]["cells"]))
        self.assertFalse(c["workload"]["supplemental_sequence_translations_counted"])
        self.assertFalse(c["workload"]["supplemental_characteristic_rhythm_pass_counted"])
        self.assertFalse(c["workload"]["supplemental_capstone_repeat_counted"])

    def test_events_pdf_parity_and_nonadmission(self) -> None:
        c = self.c
        grids = [x for k, m in c["modules"].items() if k != "B" for x in m["cells"]]
        self.assertEqual(len(grids), 44)
        events = [e for grid in grids for e in grid["events"]]
        self.assertEqual(len(events), 730)
        self.assertTrue(all((mod.OPEN[e["string"]] + e["fret"]) % 12 == mod.PC[e["note"]]
                            and e["degree"] == mod.DEGREE[e["note"]] for e in events))
        self.assertTrue(all(e["onset_q"] is None and e["duration_q"] is None for e in events))
        seams = c["modules"]["B"]["cells"]
        self.assertEqual(sum(len(lane["events"]) for seam in seams for lane in seam["lanes"]), 168)
        self.assertEqual([seam["pdf_page"] for seam in seams], [8, 8, 9, 9])
        self.assertEqual(len(c["pdf_only_directions"]["module_page_guidance"]), 17)
        self.assertIsNone(c["stable_ids"])
        self.assertFalse(c["imported"])
        self.assertFalse(c["admitted"])

    def test_determinism_and_source_drift(self) -> None:
        self.assertEqual(json.dumps(self.c, sort_keys=True),
                         json.dumps(mod.build_candidate(ROOT), sort_keys=True))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for rel in (mod.TXT, mod.PDF, mod.MAP):
                dst = root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / rel, dst)
            target = root / mod.PDF
            blob = target.read_bytes()
            target.write_bytes(blob[:-1] + bytes([blob[-1] ^ 1]))
            with self.assertRaisesRegex(mod.CandidateError, "PINNED_INPUT_DRIFT"):
                mod.build_candidate(root)


if __name__ == "__main__":
    unittest.main()
