"""Focused source and refusal checks for detached Level 10 Set 2."""

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from Tools import parallel10_level010_set02_candidate as candidate


class Level10Set2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        candidate.BUILD_ROOT.mkdir(parents=True, exist_ok=True)

    def copied_root(self, base: Path) -> Path:
        root = base / "repo"
        for rel in (candidate.TXT_REL, candidate.PDF_REL):
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(candidate.ROOT / rel, target)
        return root

    def test_exact_source_identity_and_all_cards(self):
        payload = candidate.build_candidate()
        self.assertEqual(payload["source"]["txt_sha256"], candidate.TXT_SHA)
        self.assertEqual(payload["source"]["pdf_sha256"], candidate.PDF_SHA)
        self.assertEqual([r["exercise_number"] for r in payload["records"]], list(range(13, 25)))
        self.assertEqual([r["finger_code"] for r in payload["records"]], list(candidate.CODES))
        self.assertEqual(sum(len(m["routes"]) for r in payload["records"] for m in r["modes"]), 288)
        self.assertEqual(sum(len(route["notes"]) for r in payload["records"] for m in r["modes"] for route in m["routes"]), 1152)
        self.assertFalse(payload["canonical_identity_assigned"])
        self.assertFalse(payload["runtime_import_authorized"])
        self.assertFalse(payload["timing_interpreted"])

    def test_mode_landing_frame_order_and_pdf_parity(self):
        payload = candidate.build_candidate()
        for record in payload["records"]:
            self.assertEqual([m["mode"] for m in record["modes"]], ["A", "B"])
            self.assertIsNone(record["canonical_item_id"])
            self.assertIsNone(record["fixed_bpm"])
            self.assertIsNone(record["onset"])
            self.assertIsNone(record["duration"])
            for mode in record["modes"]:
                split, landing = (3, 4) if mode["mode"] == "A" else (1, 2)
                self.assertEqual((mode["shift_after_note"], mode["landing_note_index"]), (split, landing))
                self.assertEqual([r["direction"] for r in mode["routes"]], ["UP"] * 6 + ["DOWN"] * 6)
                self.assertEqual([r["string"] for r in mode["routes"][:6]], list(candidate.STRINGS["UP"]))
                self.assertEqual([r["string"] for r in mode["routes"][6:]], list(candidate.STRINGS["DOWN"]))
                for route in mode["routes"]:
                    self.assertEqual("S" + route["txt_tab_row"][1:], route["pdf_tab_template"])
                    self.assertEqual(route["txt_finger_row"], route["pdf_finger_template"])
                    source, dest = ("P5", "P7") if route["direction"] == "UP" else ("P7", "P5")
                    self.assertEqual([n["frame"] for n in route["notes"]], [source] * split + [dest] * (4 - split))
                    self.assertEqual([n["landing_note"] for n in route["notes"]], [i == landing for i in range(1, 5)])
                    self.assertEqual([n["fret"] for n in route["notes"]], [(5 if n["frame"] == "P5" else 7) + n["finger"] - 1 for n in route["notes"]])

    def test_deterministic_twin_writes_and_overwrite_refusal(self):
        with tempfile.TemporaryDirectory(dir=candidate.BUILD_ROOT) as temp:
            root = self.copied_root(Path(temp))
            a = root / "Build/parallel-10/2.3.1.1.1-level010-set02-r01/a.json"
            b = root / "Build/parallel-10/2.3.1.1.1-level010-set02-r01/b.json"
            size_a, hash_a = candidate.write_candidate(a, root)
            size_b, hash_b = candidate.write_candidate(b, root)
            self.assertEqual((size_a, hash_a), (size_b, hash_b))
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with self.assertRaisesRegex(ValueError, "already exists"):
                candidate.write_candidate(a, root)

    def test_txt_and_pdf_hash_drift_refused_without_output(self):
        for rel in (candidate.TXT_REL, candidate.PDF_REL):
            with self.subTest(rel=rel), tempfile.TemporaryDirectory(dir=candidate.BUILD_ROOT) as temp:
                root = self.copied_root(Path(temp))
                (root / rel).write_bytes((root / rel).read_bytes() + b"\n")
                output = root / "Build/parallel-10/2.3.1.1.1-level010-set02-r01/should-not-exist.json"
                with self.assertRaisesRegex(ValueError, "source drift"):
                    candidate.write_candidate(output, root)
                self.assertFalse(output.exists())

    def test_wrong_tab_row_refused_after_explicit_new_hash(self):
        with tempfile.TemporaryDirectory(dir=candidate.BUILD_ROOT) as temp:
            root = self.copied_root(Path(temp))
            source = root / candidate.TXT_REL
            data = source.read_text()
            self.assertIn("e|5-7-6------|7----------|", data)
            data = data.replace("e|5-7-6------|7----------|", "e|5-7-6------|8----------|", 1)
            source.write_text(data)
            with mock.patch.object(candidate, "TXT_SHA", hashlib.sha256(source.read_bytes()).hexdigest()):
                with self.assertRaisesRegex(ValueError, "PDF/TXT TAB template mismatch|finger/frame/fret mismatch"):
                    candidate.build_candidate(root)

    def test_wrong_code_and_set_boundary_refused(self):
        for before, after, message in (("Exercise 013: 1321", "Exercise 013: 1322", "card identity"),
                                        ("SET 3 OF 9 - EXERCISES 025-036", "SET 3 OF 9 - EXERCISES 025-037", "next-set boundary")):
            with self.subTest(before=before), tempfile.TemporaryDirectory(dir=candidate.BUILD_ROOT) as temp:
                root = self.copied_root(Path(temp))
                source = root / candidate.TXT_REL
                data = source.read_text()
                self.assertIn(before, data)
                source.write_text(data.replace(before, after, 1))
                with mock.patch.object(candidate, "TXT_SHA", hashlib.sha256(source.read_bytes()).hexdigest()):
                    with self.assertRaisesRegex(ValueError, message):
                        candidate.build_candidate(root)

    def test_outside_and_symlink_output_refused(self):
        with tempfile.TemporaryDirectory(dir=candidate.BUILD_ROOT) as temp:
            root = self.copied_root(Path(temp))
            outside = root / "Build/other-lane/no.json"
            with self.assertRaisesRegex(ValueError, "outside P10 Build allowance"):
                candidate.write_candidate(outside, root)
            self.assertFalse(outside.exists())
            allowed = root / "Build/parallel-10/2.3.1.1.1-level010-set02-r01"
            allowed.mkdir(parents=True)
            link = allowed / "link.json"
            link.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "symlink"):
                candidate.write_candidate(link, root)
            self.assertFalse(outside.exists())


if __name__ == "__main__":
    unittest.main()
