"""Complete-corpus and fail-closed checks for Level 13 detached ladder."""

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from Tools import parallel10_level013_ladder_candidate as ladder


class WholeLevel13Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ladder.ROOT / ladder.BUILD_REL).mkdir(parents=True, exist_ok=True)

    def copied_root(self, base: Path) -> Path:
        root = base / "repo"
        for rel in (ladder.TXT_REL, ladder.PDF_REL):
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ladder.ROOT / rel, target)
        return root

    def mutated_txt(self, before: str, after: str, expected_error: str) -> None:
        with tempfile.TemporaryDirectory(dir=ladder.ROOT / ladder.BUILD_REL) as temp:
            root = self.copied_root(Path(temp))
            path = root / ladder.TXT_REL
            body = path.read_text()
            self.assertIn(before, body)
            path.write_text(body.replace(before, after, 1))
            with mock.patch.object(ladder, "TXT_SHA", hashlib.sha256(path.read_bytes()).hexdigest()):
                with self.assertRaisesRegex(ValueError, expected_error):
                    ladder.build_candidate(root)

    def test_all_rungs_pdf_txt_and_route(self):
        data = ladder.build_candidate()
        self.assertEqual(data["source"]["txt_sha256"], ladder.TXT_SHA)
        self.assertEqual(data["source"]["pdf_sha256"], ladder.PDF_SHA)
        self.assertEqual(data["exceptions"], [])
        self.assertEqual(len(data["rungs"]), 13)
        self.assertEqual([r["key"] for r in data["rungs"]], list(ladder.KEYS))
        self.assertEqual([r["low_e_root_fret"] for r in data["rungs"]], list(range(5, 18)))
        self.assertEqual([r["txt_header_line"] for r in data["rungs"]], list(range(52, 221, 14)))
        self.assertEqual([r["pdf_page"] for r in data["rungs"]], [3] * 3 + [4] * 3 + [5] * 3 + [6] * 3 + [7])
        self.assertEqual(data["ladder"]["up_rungs"], list(range(1, 14)))
        self.assertEqual(data["ladder"]["down_rungs"], list(range(12, 0, -1)))
        self.assertEqual(data["ladder"]["round_trip_note_contacts"], 750)
        self.assertFalse(data["canonical_identity_assigned"])
        self.assertFalse(data["runtime_import_authorized"])
        self.assertFalse(data["timing_interpreted"])

    def test_all_390_contacts_major_pitch_finger_and_b_offset(self):
        data = ladder.build_candidate()
        self.assertEqual(sum(len(r["notes"]) for r in data["rungs"]), 390)
        for rung in data["rungs"]:
            root = rung["low_e_root_fret"]
            notes = rung["notes"]
            self.assertEqual([n["degree"] for n in notes], list(ladder.ASC_DEGREES) + list(reversed(ladder.ASC_DEGREES)))
            self.assertEqual([n["finger"] for n in notes], list(ladder.FINGERS))
            self.assertEqual([n["midi"] for n in notes], [40 + root + x for x in ladder.MAJOR_OFFSETS] + [40 + root + x for x in reversed(ladder.MAJOR_OFFSETS)])
            self.assertEqual((notes[14]["string"], notes[14]["fret"]), ("e", root))
            self.assertEqual(notes[14]["midi"], notes[15]["midi"])
            self.assertEqual([n["repeated_high_root_at_turn"] for n in notes], [i in (15, 16) for i in range(1, 31)])
            b_frets = [n["fret"] for n in notes if n["string"] == "B"]
            self.assertEqual(b_frets, [root, root + 2, root + 2, root])
            for n in notes:
                self.assertEqual(n["midi"], ladder.TUNING_MIDI[n["string"]] + n["fret"])
            self.assertTrue(all(rung[k] is None for k in ("canonical_item_id", "fixed_bpm", "note_per_click", "onset", "duration")))
            self.assertFalse(rung["runtime_eligible"])
            self.assertFalse(rung["admitted"])

    def test_deterministic_twins_and_overwrite_refusal(self):
        with tempfile.TemporaryDirectory(dir=ladder.ROOT / ladder.BUILD_REL) as temp:
            root = self.copied_root(Path(temp))
            a = root / ladder.BUILD_REL / "a.json"
            b = root / ladder.BUILD_REL / "b.json"
            self.assertEqual(ladder.write_candidate(a, root), ladder.write_candidate(b, root))
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with self.assertRaisesRegex(ValueError, "output exists"):
                ladder.write_candidate(a, root)

    def test_source_hash_drift_refuses_before_output(self):
        for rel in (ladder.TXT_REL, ladder.PDF_REL):
            with self.subTest(rel=rel), tempfile.TemporaryDirectory(dir=ladder.ROOT / ladder.BUILD_REL) as temp:
                root = self.copied_root(Path(temp))
                (root / rel).write_bytes((root / rel).read_bytes() + b"\n")
                output = root / ladder.BUILD_REL / "should-not-exist.json"
                with self.assertRaisesRegex(ValueError, "source drift"):
                    ladder.write_candidate(output, root)
                self.assertFalse(output.exists())

    def test_wrong_tab_row_degree_finger_key_and_route_refuse(self):
        self.mutated_txt("B  |---------------------------------5--7", "B  |---------------------------------5--8", "PDF/TXT Deg/Fng/TAB mismatch")
        self.mutated_txt("Deg|1--2--3--4--5--6--7--1", "Deg|1--2--3--4--5--6--6--1", "degree sequence")
        self.mutated_txt("Fng|2--4--1--2--4--1--3--4", "Fng|2--4--1--2--4--1--2--4", "finger sequence")
        self.mutated_txt("RUNG 02 OF 13 - BB MAJOR", "RUNG 02 OF 13 - B MAJOR", "TXT rung header")
        self.mutated_txt("Bb(6) > B(7) > C(8)", "Bb(6) > C(8) > B(7)", "TXT UP ladder route")

    def test_output_confinement_and_symlink_refusal(self):
        with tempfile.TemporaryDirectory(dir=ladder.ROOT / ladder.BUILD_REL) as temp:
            root = self.copied_root(Path(temp))
            outside = root / "Build/parallel-09/other.json"
            with self.assertRaisesRegex(ValueError, "outside P10 Level13 Build"):
                ladder.write_candidate(outside, root)
            self.assertFalse(outside.exists())
            allowed = root / ladder.BUILD_REL
            allowed.mkdir(parents=True)
            link = allowed / "link.json"
            link.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "symlink"):
                ladder.write_candidate(link, root)
            self.assertFalse(outside.exists())


if __name__ == "__main__":
    unittest.main()
