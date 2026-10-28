"""Closed 105-workbook source-library bundle and corruption refusals."""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "parallel06_source_library_bundle", ROOT / "Tools/parallel06_source_library_bundle.py")
assert SPEC and SPEC.loader
source_library = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(source_library)
BUILD = ROOT / "Build/parallel-06/source-library-bundle-r01"
BUNDLE = BUILD / "bundle"


class SourceLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = source_library.load_catalog(ROOT)
        cls.handoff = json.loads((BUILD / "handoff.json").read_text())
        cls.index = source_library.verify_bundle(BUNDLE, cls.handoff["index"]["sha256"])

    def bundle_copy(self, parent: Path) -> Path:
        target = parent / "copy"
        shutil.copytree(BUNDLE, target)
        return target

    def test_exact_consumer_schema_and_original_assets(self):
        self.assertEqual(self.handoff, {
            "schema": "fathom-source-library-handoff.1", "bundle_root": "bundle",
            "index": {"path": "index.json", "sha256": self.handoff["index"]["sha256"],
                      "bytes": (BUNDLE / "index.json").stat().st_size}})
        self.assertEqual(self.index["schema"], "fathom-source-library.1")
        self.assertEqual(len(self.index["entries"]), 105)
        self.assertEqual(len(self.index["files"]), 210)
        self.assertFalse(self.index["admitted"])
        self.assertFalse(self.index["runtime_admission"])
        self.assertFalse(self.index["whole_workbook_complete"])
        self.assertEqual([x["legacy_level"] for x in self.index["entries"]], list(range(1, 106)))
        for level, entry in enumerate(self.index["entries"], 1):
            self.assertEqual(set(entry), {"workbook_id", "legacy_level", "label", "txt", "pdf"})
            self.assertEqual(entry["workbook_id"], f"fg:workbook:{level:06d}")
            for kind in ("txt", "pdf"):
                item = entry[kind]
                self.assertTrue(item["path"].startswith("assets/Notes/music/guitar project/"))
                self.assertEqual(self.index["files"][item["path"]],
                                 {"bytes": item["bytes"], "sha256": item["sha256"]})
                self.assertEqual((BUNDLE / item["path"]).read_bytes(),
                                 (ROOT / item["path"].removeprefix("assets/")).read_bytes())

    def test_catalog_order_duplicate_and_admission_refused(self):
        first = self.catalog["entries"][0]
        wrong = dict(first, workbook_id="fg:workbook:000002")
        with self.assertRaisesRegex(source_library.Refusal, "identity/order"):
            source_library.validate_catalog_entry(wrong, 1)
        wrong = dict(first, admitted=True)
        with self.assertRaisesRegex(source_library.Refusal, "source-only flags"):
            source_library.validate_catalog_entry(wrong, 1)
        entries = list(self.catalog["entries"])
        entries[1] = copy.deepcopy(entries[1])
        entries[1]["txt"]["path"] = entries[0]["txt"]["path"]
        with self.assertRaisesRegex(source_library.Refusal, "duplicate source path"):
            source_library.prepare(ROOT, {"catalog_version": self.catalog["catalog_version"], "entries": entries})

    def test_missing_asset_refused(self):
        with tempfile.TemporaryDirectory(dir=BUILD) as temporary:
            bundle = self.bundle_copy(Path(temporary))
            item = self.index["entries"][0]["txt"]["path"]
            (bundle / item).unlink()
            with self.assertRaisesRegex(source_library.Refusal, "bundle file set differs"):
                source_library.verify_bundle(bundle, self.handoff["index"]["sha256"])

    def test_changed_asset_refused(self):
        with tempfile.TemporaryDirectory(dir=BUILD) as temporary:
            bundle = self.bundle_copy(Path(temporary))
            item = self.index["entries"][0]["pdf"]["path"]
            with (bundle / item).open("ab") as stream:
                stream.write(b"changed")
            with self.assertRaisesRegex(source_library.Refusal, "changed bundle asset"):
                source_library.verify_bundle(bundle, self.handoff["index"]["sha256"])

    def test_symlink_asset_refused(self):
        with tempfile.TemporaryDirectory(dir=BUILD) as temporary:
            bundle = self.bundle_copy(Path(temporary))
            item = self.index["entries"][0]["txt"]["path"]
            (bundle / item).unlink()
            (bundle / item).symlink_to(BUNDLE / item)
            with self.assertRaisesRegex(source_library.Refusal, "bundle symlink"):
                source_library.verify_bundle(bundle, self.handoff["index"]["sha256"])

    def test_extra_file_refused(self):
        with tempfile.TemporaryDirectory(dir=BUILD) as temporary:
            bundle = self.bundle_copy(Path(temporary))
            (bundle / "surprise.txt").write_text("extra")
            with self.assertRaisesRegex(source_library.Refusal, "bundle file set differs"):
                source_library.verify_bundle(bundle, self.handoff["index"]["sha256"])

    def test_changed_original_and_source_symlink_refused(self):
        source = self.catalog["entries"][0]["txt"]
        with tempfile.TemporaryDirectory(dir=BUILD) as temporary:
            temp = Path(temporary)
            changed = temp / "changed.txt"
            changed.write_bytes((ROOT / source["path"]).read_bytes() + b"changed")
            with patch.object(source_library, "local_source", return_value=changed):
                with self.assertRaisesRegex(source_library.Refusal, "changed source"):
                    source_library.checked_source(ROOT, source, "txt")
            fake_root = temp / "root"
            link = fake_root / source["path"]
            link.parent.mkdir(parents=True)
            link.symlink_to(ROOT / source["path"])
            with self.assertRaisesRegex(source_library.Refusal, "source symlink"):
                source_library.local_source(fake_root, source["path"])

    def test_index_hash_and_closed_inventory_refused(self):
        with tempfile.TemporaryDirectory(dir=BUILD) as temporary:
            bundle = self.bundle_copy(Path(temporary))
            index = bundle / "index.json"
            index.write_bytes(index.read_bytes() + b"changed")
            with self.assertRaisesRegex(source_library.Refusal, "bundle index hash differs"):
                source_library.verify_bundle(bundle, self.handoff["index"]["sha256"])


if __name__ == "__main__":
    unittest.main()
