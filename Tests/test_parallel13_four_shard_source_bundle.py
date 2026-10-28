"""Focused refusal checks for the sealed four-shard source bundle."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel13_four_shard_source_bundle as bundle  # noqa: E402


class BundleRefusalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="p13-negative-", dir=ROOT / bundle.OUT)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "bundle"
        shutil.copytree(ROOT / bundle.BUNDLE, self.root, copy_function=os.link)

    def chosen_source(self) -> Path:
        inventory = json.loads((self.root / bundle.INVENTORY).read_text())
        rel = next(k for k, v in inventory["files"].items()
                   if any(x.endswith("source_asset") for x in v["roles"]))
        return self.root / rel

    def test_unchanged_bundle_checks(self) -> None:
        self.assertEqual(len(bundle.check_bundle(self.root)["files"]), 65)

    def test_missing_source_refused(self) -> None:
        self.chosen_source().unlink()
        with self.assertRaisesRegex(bundle.BundleError, "INVENTORY_CLOSED"):
            bundle.check_bundle(self.root)

    def test_altered_source_refused(self) -> None:
        path = self.chosen_source()
        path.unlink()  # Break the test copy's hard link before writing.
        path.write_bytes(b"altered")
        with self.assertRaisesRegex(bundle.BundleError, "ASSET_DRIFT"):
            bundle.check_bundle(self.root)

    def test_symlink_source_refused(self) -> None:
        path = self.chosen_source()
        path.unlink()
        path.symlink_to(self.root / bundle.INVENTORY)
        with self.assertRaisesRegex(bundle.BundleError, "SYMLINK"):
            bundle.check_bundle(self.root)

    def test_extra_asset_refused(self) -> None:
        (self.root / "extra.txt").write_text("not referenced")
        with self.assertRaisesRegex(bundle.BundleError, "INVENTORY_CLOSED"):
            bundle.check_bundle(self.root)

    def test_traversal_refused(self) -> None:
        for path in ("../escape", "/tmp/escape", "Notes/../escape", "Notes\\escape"):
            with self.subTest(path=path), self.assertRaisesRegex(bundle.BundleError, "PATH_UNSAFE"):
                bundle.relative(path)


if __name__ == "__main__":
    unittest.main()
