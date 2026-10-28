"""Complete-corpus/refusal tests for detached Level17 rolling ladder."""

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from Tools import parallel10_level017_rolling_candidate as rolling


class WholeLevel17Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (rolling.ROOT / rolling.BUILD_REL).mkdir(parents=True, exist_ok=True)

    def copied_root(self, base: Path) -> Path:
        root = base / "repo"
        for rel in (rolling.TXT_REL, rolling.PDF_REL):
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(rolling.ROOT / rel, target)
        return root

    def mutated_txt(self, old: str, new: str, error: str):
        with tempfile.TemporaryDirectory(dir=rolling.ROOT / rolling.BUILD_REL) as temp:
            root = self.copied_root(Path(temp))
            path = root / rolling.TXT_REL
            body = path.read_text()
            self.assertIn(old, body)
            path.write_text(body.replace(old, new, 1))
            with mock.patch.object(rolling, "TXT_SHA", hashlib.sha256(path.read_bytes()).hexdigest()):
                with self.assertRaisesRegex(ValueError, error):
                    rolling.build_candidate(root)

    def test_whole_corpus_pdf_txt_identity_and_route(self):
        result = rolling.build_candidate()
        self.assertEqual(result["source"]["txt_sha256"], rolling.TXT_SHA)
        self.assertEqual(result["source"]["pdf_sha256"], rolling.PDF_SHA)
        self.assertEqual(result["exceptions"], [])
        self.assertEqual([r["rung"] for r in result["rungs"]], list(range(1, 14)))
        self.assertEqual([r["txt_header_line"] for r in result["rungs"]], list(range(69, 358, 24)))
        self.assertEqual([r["pdf_page"] for r in result["rungs"]], [3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9])
        self.assertEqual([r["key"] for r in result["rungs"]], list(rolling.KEYS))
        self.assertEqual([r["low_e_root_fret"] for r in result["rungs"]], list(range(5, 18)))
        self.assertEqual(result["ladder"]["up_rungs"], list(range(1, 14)))
        self.assertEqual(result["ladder"]["down_rungs"], list(range(12, 0, -1)))
        self.assertEqual((result["ladder"]["round_trip_cells"], result["ladder"]["round_trip_note_contacts"]), (25, 2400))
        self.assertFalse(result["canonical_identity_assigned"])
        self.assertFalse(result["runtime_import_authorized"])
        self.assertFalse(result["timing_interpreted"])

    def test_13_by_24_group_overlap_pitch_and_high_root(self):
        result = rolling.build_candidate()
        self.assertEqual(sum(len(r["groups"]) for r in result["rungs"]), 312)
        self.assertEqual(sum(len(g["notes"]) for r in result["rungs"] for g in r["groups"]), 1248)
        for rung in result["rungs"]:
            root = rung["low_e_root_fret"]
            self.assertEqual(rung["cell_note_count"], 96)
            self.assertEqual(len(rung["groups"]), 24)
            self.assertEqual(rung["groups"][11]["notes"][-1]["scale_position"], 15)
            self.assertEqual(rung["groups"][12]["notes"][0]["scale_position"], 15)
            self.assertEqual(rung["groups"][11]["notes"][-1]["midi"], rung["groups"][12]["notes"][0]["midi"])
            for half in (rung["groups"][:12], rung["groups"][12:]):
                for first, second in zip(half, half[1:]):
                    self.assertEqual(first["scale_positions"][1:], second["scale_positions"][:3])
            for group in rung["groups"]:
                self.assertEqual(len(group["notes"]), 4)
                self.assertEqual([n["cell_note_index"] for n in group["notes"]], [4 * (group["group"] - 1) + k for k in range(1, 5)])
                for note in group["notes"]:
                    self.assertEqual(note["midi"], rolling.TUNING[note["string"]] + note["fret"])
                    self.assertEqual(note["midi"], 40 + root + rolling.MAJOR_OFFSETS[note["scale_position"] - 1])
                    if note["string"] == "B":
                        self.assertIn(note["fret"], (root, root + 2))
            self.assertTrue(all(rung[k] is None for k in ("canonical_item_id", "fixed_bpm", "note_per_click", "onset", "duration")))
            self.assertFalse(rung["runtime_eligible"])
            self.assertFalse(rung["admitted"])

    def test_determinism_and_overwrite_refusal(self):
        with tempfile.TemporaryDirectory(dir=rolling.ROOT / rolling.BUILD_REL) as temp:
            root = self.copied_root(Path(temp))
            a, b = root / rolling.BUILD_REL / "a.json", root / rolling.BUILD_REL / "b.json"
            self.assertEqual(rolling.write_candidate(a, root), rolling.write_candidate(b, root))
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with self.assertRaisesRegex(ValueError, "output exists"):
                rolling.write_candidate(a, root)

    def test_pinned_source_drift_refuses_without_output(self):
        for rel in (rolling.TXT_REL, rolling.PDF_REL):
            with self.subTest(rel=rel), tempfile.TemporaryDirectory(dir=rolling.ROOT / rolling.BUILD_REL) as temp:
                root = self.copied_root(Path(temp))
                path = root / rel
                path.write_bytes(path.read_bytes() + b"\n")
                output = root / rolling.BUILD_REL / "never.json"
                with self.assertRaisesRegex(ValueError, "source drift"):
                    rolling.write_candidate(output, root)
                self.assertFalse(output.exists())

    def test_wrong_tab_degree_finger_key_and_route_refuse(self):
        self.mutated_txt("B  |------------|------------|------------|------------|------------|------------|------------|------------|---------5--", "B  |------------|------------|------------|------------|------------|------------|------------|------------|---------6--", "PDF/TXT rolling")
        self.mutated_txt("Deg|1--2--3--4--|", "Deg|1--2--3--3--|", "PDF/TXT rolling")
        self.mutated_txt("Fng|2--4--1--2--|", "Fng|2--4--1--1--|", "PDF/TXT rolling")
        self.mutated_txt("RUNG 02 OF 13 - BB MAJOR", "RUNG 02 OF 13 - B MAJOR", "TXT rung header")
        self.mutated_txt("Bb(6) > B(7) > C(8)", "Bb(6) > C(8) > B(7)", "TXT UP ladder route")

    def test_group_semantic_refusal_and_output_confinement(self):
        lines, _ = rolling.sources()
        block = lines[68:91]
        base = rolling.scale_contacts(5, 0)
        bad = list(block)
        bad[4] = bad[4].replace("1--2--3--4--|", "1--2--3--3--|", 1)
        with self.assertRaisesRegex(ValueError, "ascending group 1 degree sequence"):
            rolling.parse_half(bad, 3, "ascending", base, 69)
        with tempfile.TemporaryDirectory(dir=rolling.ROOT / rolling.BUILD_REL) as temp:
            root = self.copied_root(Path(temp))
            outside = root / "Build/parallel-08/no.json"
            with self.assertRaisesRegex(ValueError, "outside P10 Level17 Build"):
                rolling.write_candidate(outside, root)
            self.assertFalse(outside.exists())
            allowed = root / rolling.BUILD_REL
            allowed.mkdir(parents=True)
            link = allowed / "link.json"
            link.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "symlink"):
                rolling.write_candidate(link, root)


if __name__ == "__main__":
    unittest.main()
