"""Focused native-shard and global-authority checks for P10 Level7 r02."""

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel10_level007_shard_reference as shard  # noqa: E402
import parallel10_level007_schema1_overlay as prior  # noqa: E402


class Level7ShardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local = shard.derive_local()
        cls.manifest = shard.read(ROOT, shard.OUT / "global-manifest.json")
        cls.report = shard.read(ROOT, shard.OUT / "native-report.json")

    def test_local_rebuild_and_source_coverage(self):
        for name in shard.FILES:
            self.assertEqual((ROOT / shard.OUT / name).read_bytes(), shard.encoded(self.local[name]))
        pkg = self.local["package.json"]
        self.assertEqual((len(pkg["records"]), len(pkg["sources"])), (108, 120))
        self.assertEqual(sum(len(r["events"]) for r in pkg["records"]), 1728)
        self.assertEqual(sum(len(r["variants"]) for r in pkg["records"]), 216)
        self.assertTrue(all(r["context"]["capo"] == 0 and
                            r["context"]["tuning_open_midi"] == [40, 45, 50, 55, 59, 64]
                            for r in pkg["records"]))
        self.assertTrue(all(e["onset_q"] is None and e["duration_q"] is None
                            for r in pkg["records"] for e in r["events"]))
        self.assertTrue(all("workbook_catalog" not in self.local[n]
                            for n in ("package.json", "identity-registry.json", "expected-profile.json")))

    def test_native_reference_is_local_only(self):
        self.assertEqual((self.report["exit_code"], self.report["valid_reference"]), (2, True))
        self.assertFalse(self.report["curriculum_playback_authorized"])
        self.assertEqual(self.report["coverage"]["observed_records"], 108)
        self.assertFalse(any(issue["severity"] == "error" for issue in self.report["issues"]))
        self.assertEqual(self.manifest["validated_workbooks"], [7])
        self.assertFalse(self.manifest["aggregate_complete"])
        self.assertFalse(self.manifest["admitted"])
        shard.ensure_global(ROOT, self.manifest, self.report)

    def test_global_manifest_hash_and_authority_refuse(self):
        altered = copy.deepcopy(self.manifest)
        altered["shards"][0]["sha256"]["package.json"] = "0" * 64
        with self.assertRaisesRegex(shard.ShardError, "SHARD_PIN"):
            shard.ensure_global(ROOT, altered, self.report)
        altered = copy.deepcopy(self.manifest)
        altered["admitted"] = True
        with self.assertRaisesRegex(shard.ShardError, "MANIFEST_AUTHORITY"):
            shard.ensure_global(ROOT, altered, self.report)
        altered = copy.deepcopy(self.manifest)
        altered["shards"].append(copy.deepcopy(altered["shards"][0]))
        with self.assertRaisesRegex(shard.ShardError, "SHARD_COVERAGE"):
            shard.ensure_global(ROOT, altered, self.report)

    def test_native_report_refusal(self):
        altered = copy.deepcopy(self.report)
        altered["valid_reference"] = False
        with self.assertRaisesRegex(shard.ShardError, "NATIVE_NOT_LOCAL_VALID"):
            shard.ensure_global(ROOT, self.manifest, altered)
        altered = copy.deepcopy(self.report)
        altered["curriculum_playback_authorized"] = True
        with self.assertRaisesRegex(shard.ShardError, "NATIVE_NOT_LOCAL_VALID"):
            shard.ensure_global(ROOT, self.manifest, altered)

    def test_reserved_and_duplicate_ids_refuse(self):
        registry = shard.read(ROOT, prior.CURRENT / "identity-registry.json")
        entities = copy.deepcopy(self.local["identity-registry.json"]["entities"][1:])
        prior.check_new_ids(registry, entities)
        entities[0]["id"] = registry["entities"][0]["id"]
        with self.assertRaisesRegex(prior.OverlayError, "DUPLICATE_ENTITY"):
            prior.check_new_ids(registry, entities)
        entities = copy.deepcopy(self.local["identity-registry.json"]["entities"][1:])
        entities[1]["id"] = "fg:module:000552"
        with self.assertRaisesRegex(prior.OverlayError, "RESERVED_ID_COLLISION"):
            prior.check_new_ids(registry, entities)

    def test_pinned_foundation_refusal(self):
        altered = copy.deepcopy(self.manifest)
        altered["foundation"]["package.json"] = "0" * 64
        with self.assertRaisesRegex(shard.ShardError, "FOUNDATION_PIN"):
            shard.ensure_global(ROOT, altered, self.report)
        altered = copy.deepcopy(self.manifest)
        altered["catalog_sha256"] = "0" * 64
        with self.assertRaisesRegex(shard.ShardError, "CATALOG_PIN"):
            shard.ensure_global(ROOT, altered, self.report)


if __name__ == "__main__":
    unittest.main()
