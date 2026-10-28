"""Whole-Level21 natural-minor source and refusal checks."""

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from Tools import parallel10_level021_minor_candidate as minor


class WholeLevel21Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (minor.ROOT / minor.BUILD_REL).mkdir(parents=True, exist_ok=True)

    def copied_root(self, base: Path) -> Path:
        root = base / "repo"
        for rel in (minor.TXT_REL, minor.PDF_REL):
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(minor.ROOT / rel, target)
        return root

    def mutated_txt(self, old: str, new: str, error: str):
        with tempfile.TemporaryDirectory(dir=minor.ROOT / minor.BUILD_REL) as temp:
            root = self.copied_root(Path(temp))
            path = root / minor.TXT_REL
            text = path.read_text()
            self.assertIn(old, text)
            path.write_text(text.replace(old, new, 1))
            with mock.patch.object(minor, "TXT_SHA", hashlib.sha256(path.read_bytes()).hexdigest()):
                with self.assertRaisesRegex(ValueError, error):
                    minor.build_candidate(root)

    def test_complete_source_pdf_and_neck_route(self):
        data = minor.build_candidate()
        self.assertEqual(data["source"]["txt_sha256"], minor.TXT_SHA)
        self.assertEqual(data["source"]["pdf_sha256"], minor.PDF_SHA)
        self.assertEqual(data["exceptions"], [])
        self.assertEqual(len(data["rungs"]), 13)
        self.assertEqual([r["txt_header_line"] for r in data["rungs"]], list(range(45, 214, 14)))
        self.assertEqual([r["pdf_page"] for r in data["rungs"]], [3] * 4 + [4] * 4 + [5] * 4 + [6])
        self.assertEqual([r["key"] for r in data["rungs"]], list(minor.KEYS))
        self.assertEqual([r["low_e_root_fret"] for r in data["rungs"]], list(range(5, 18)))
        self.assertEqual(data["ladder"]["up_rungs"], list(range(1, 14)))
        self.assertEqual(data["ladder"]["down_rungs"], list(range(12, 0, -1)))
        self.assertEqual((data["ladder"]["round_trip_cells"], data["ladder"]["round_trip_note_contacts"]), (25, 400))
        self.assertFalse(data["canonical_identity_assigned"])
        self.assertFalse(data["runtime_import_authorized"])
        self.assertFalse(data["timing_interpreted"])

    def test_all_208_minor_contacts_and_lowered_degrees(self):
        data = minor.build_candidate()
        self.assertEqual(sum(len(r["notes"]) for r in data["rungs"]), 208)
        expected_deg = list(minor.DEGREES) + list(reversed(minor.DEGREES))
        expected_fingers = list(minor.FINGERS) + list(reversed(minor.FINGERS))
        for rung in data["rungs"]:
            root, notes = rung["low_e_root_fret"], rung["notes"]
            self.assertEqual(rung["cell_note_count"], 16)
            self.assertEqual([n["degree"] for n in notes], expected_deg)
            self.assertEqual([n["finger"] for n in notes], expected_fingers)
            self.assertEqual([n["string"] for n in notes], ["E"] * 3 + ["A"] * 3 + ["D"] * 2 + ["D"] * 2 + ["A"] * 3 + ["E"] * 3)
            self.assertEqual([n["midi"] for n in notes], [40 + root + x for x in minor.MINOR_OFFSETS] + [40 + root + x for x in reversed(minor.MINOR_OFFSETS)])
            self.assertEqual(notes[7]["midi"], notes[8]["midi"])
            self.assertEqual([n["repeated_octave_root_at_turn"] for n in notes], [i in (8, 9) for i in range(1, 17)])
            for n in notes:
                self.assertEqual(n["midi"], minor.TUNING[n["string"]] + n["fret"])
            self.assertTrue(all(rung[k] is None for k in ("canonical_item_id", "fixed_bpm", "note_per_click", "onset", "duration")))
            self.assertFalse(rung["runtime_eligible"])
            self.assertFalse(rung["admitted"])
        self.assertEqual(data["rungs"][6]["scale_tones"], ["Eb", "F", "Gb", "Ab", "Bb", "Cb", "Db", "Eb"])

    def test_deterministic_writes_and_overwrite_refusal(self):
        with tempfile.TemporaryDirectory(dir=minor.ROOT / minor.BUILD_REL) as temp:
            root = self.copied_root(Path(temp))
            a, b = root / minor.BUILD_REL / "a.json", root / minor.BUILD_REL / "b.json"
            self.assertEqual(minor.write_candidate(a, root), minor.write_candidate(b, root))
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with self.assertRaisesRegex(ValueError, "output exists"):
                minor.write_candidate(a, root)

    def test_source_drift_refuses_without_output(self):
        for rel in (minor.TXT_REL, minor.PDF_REL):
            with self.subTest(rel=rel), tempfile.TemporaryDirectory(dir=minor.ROOT / minor.BUILD_REL) as temp:
                root = self.copied_root(Path(temp))
                path = root / rel
                path.write_bytes(path.read_bytes() + b"\n")
                output = root / minor.BUILD_REL / "never.json"
                with self.assertRaisesRegex(ValueError, "source drift"):
                    minor.write_candidate(output, root)
                self.assertFalse(output.exists())

    def test_wrong_row_degree_finger_key_and_route_refuse(self):
        self.mutated_txt("D  |------------------5--7--7--5", "D  |------------------5--8--7--5", "PDF/TXT Deg/Fng/TAB mismatch")
        self.mutated_txt("Deg|1--2--b3-4--5--b6-b7-8--", "Deg|1--2--3--4--5--b6-b7-8--", "PDF/TXT Deg/Fng/TAB mismatch")
        self.mutated_txt("Fng|1--3--4--1--3--4--1--3--", "Fng|1--3--3--1--3--4--1--3--", "PDF/TXT Deg/Fng/TAB mismatch")
        self.mutated_txt("RUNG 02 OF 13 - BB NATURAL MINOR", "RUNG 02 OF 13 - B NATURAL MINOR", "TXT rung header")
        self.mutated_txt("Bb(6) > B(7) > C(8)", "Bb(6) > C(8) > B(7)", "TXT UP minor ladder route")

    def test_semantic_refusal_and_output_confinement(self):
        lines, _ = minor.sources()
        block = lines[44:57]
        wrong = list(block)
        wrong[3] = wrong[3].replace("b3", "3", 1)
        with self.assertRaisesRegex(ValueError, "lowered b3/b6/b7 degree sequence"):
            minor.checked_degree_tokens(wrong[3])
        with tempfile.TemporaryDirectory(dir=minor.ROOT / minor.BUILD_REL) as temp:
            root = self.copied_root(Path(temp))
            outside = root / "Build/parallel-09/no.json"
            with self.assertRaisesRegex(ValueError, "outside P10 Level21 Build"):
                minor.write_candidate(outside, root)
            self.assertFalse(outside.exists())
            allowed = root / minor.BUILD_REL
            allowed.mkdir(parents=True)
            link = allowed / "link.json"
            link.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "symlink"):
                minor.write_candidate(link, root)


if __name__ == "__main__":
    unittest.main()
