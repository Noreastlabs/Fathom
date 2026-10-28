"""Deterministic promoted shard tree, native binding and refusal checks."""

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel10_global_shard_verifier as globalv  # noqa: E402
import parallel10_portable_shard_promotion_r06 as promotion  # noqa: E402


class PortablePromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.origin = promotion.load_original()
        cls.manifest = json.loads((ROOT / promotion.OUT / "manifest.json").read_text())
        cls.summary = promotion.seal()

    def test_deterministic_tree_and_semantic_preservation(self):
        expected = promotion.derive_files()
        self.assertEqual(len(expected), 31)
        for rel, raw in expected.items():
            self.assertEqual((ROOT / rel).read_bytes(), raw)
        for old, new in zip(self.origin["shards"], self.manifest["shards"], strict=True):
            old_pkg = globalv.load_artifact(ROOT, old["artifacts"]["package"])
            new_pkg = globalv.load_artifact(ROOT, new["artifacts"]["package"])
            old_reg = globalv.load_artifact(ROOT, old["artifacts"]["registry"])
            new_reg = globalv.load_artifact(ROOT, new["artifacts"]["registry"])
            old_prof = globalv.load_artifact(ROOT, old["artifacts"]["profile"])
            new_prof = globalv.load_artifact(ROOT, new["artifacts"]["profile"])
            promotion.validate_semantics(old_pkg, new_pkg, old_reg, new_reg,
                                         old_prof, new_prof, old["legacy_level"])
            self.assertEqual(old_pkg["records"], new_pkg["records"])
            self.assertEqual(old_pkg["sources"], new_pkg["sources"])
            self.assertEqual(old_reg["entities"], new_reg["entities"])

    def test_all_seven_authority_refs_are_inside_candidate_tree(self):
        for descriptor in self.manifest["shards"]:
            profile = globalv.load_artifact(ROOT, descriptor["artifacts"]["profile"])
            refs = profile["authority_artifacts"]
            self.assertEqual(len(refs), 7)
            self.assertEqual({a["role"] for a in refs},
                             set(promotion.LOCAL_ROLES + promotion.HISTORICAL_ROLES))
            for a in refs:
                self.assertTrue(Path(a["path"]).is_relative_to(promotion.TREE))
                self.assertEqual(globalv.digest(ROOT, a["path"]), a["sha256"])
                self.assertNotIn("parallel-12", a["path"])
                self.assertNotIn("Results/primary", a["path"])

    def test_rebased_native_and_global_nonadmission(self):
        self.assertEqual(self.summary["validated_workbooks"], [7, 8, 10])
        self.assertEqual(self.summary["new_counts"],
                         {"records": 324, "entities": 2163, "events": 22464,
                          "sources": 473, "variants": 1512})
        self.assertFalse(self.summary["aggregate_complete"])
        self.assertFalse(self.summary["admitted"])
        self.assertFalse(self.summary["source_assets_embedded"])
        self.assertTrue(self.summary["local_authority_self_contained"])
        self.assertEqual((ROOT / promotion.OUT / "summary.json").read_bytes(),
                         globalv.encoded(self.summary))
        self.assertEqual((ROOT / promotion.OUT / "manifest.json").read_bytes(),
                         globalv.encoded(promotion.derive_manifest()))
        for old, new in zip(self.origin["shards"], self.manifest["shards"], strict=True):
            old_report = old["artifacts"]["native_report"]
            self.assertEqual(globalv.digest(ROOT, old_report["path"]), old_report["sha256"])
            report = globalv.load_artifact(ROOT, new["artifacts"]["native_report"])
            self.assertEqual((report["exit_code"], report["valid_reference"]), (2, True))
            self.assertEqual(report["coverage"]["observed_records"], 108)
            self.assertFalse(report["curriculum_playback_authorized"])
            self.assertFalse(any(x["severity"] == "error" for x in report["issues"]))

    def test_source_id_and_authority_path_mutations_refuse(self):
        old, new = self.origin["shards"][0], self.manifest["shards"][0]
        old_pkg = globalv.load_artifact(ROOT, old["artifacts"]["package"])
        new_pkg = globalv.load_artifact(ROOT, new["artifacts"]["package"])
        old_reg = globalv.load_artifact(ROOT, old["artifacts"]["registry"])
        new_reg = globalv.load_artifact(ROOT, new["artifacts"]["registry"])
        old_prof = globalv.load_artifact(ROOT, old["artifacts"]["profile"])
        new_prof = globalv.load_artifact(ROOT, new["artifacts"]["profile"])
        altered = copy.deepcopy(new_pkg)
        altered["sources"].pop(next(iter(altered["sources"])))
        with self.assertRaisesRegex(promotion.PromotionError, "SEMANTIC_VALUE_DRIFT"):
            promotion.validate_semantics(old_pkg, altered, old_reg, new_reg,
                                         old_prof, new_prof, 7)
        altered = copy.deepcopy(new_reg)
        altered["entities"][1]["id"] = "fg:workbook:000008"
        with self.assertRaisesRegex(promotion.PromotionError, "SEMANTIC_VALUE_DRIFT"):
            promotion.validate_semantics(old_pkg, new_pkg, old_reg, altered,
                                         old_prof, new_prof, 7)
        altered = copy.deepcopy(new_prof)
        altered["authority_artifacts"][0]["path"] = "Build/parallel-12/escaped.json"
        with self.assertRaisesRegex(promotion.PromotionError, "AUTHORITY_ESCAPE_OR_DRIFT"):
            promotion.validate_semantics(old_pkg, new_pkg, old_reg, new_reg,
                                         old_prof, altered, 7)

    def test_manifest_hash_and_order_refuse(self):
        changed = copy.deepcopy(self.manifest)
        changed["shards"][1]["artifacts"]["profile"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(globalv.GlobalError, "ARTIFACT_PIN"):
            globalv.verify(ROOT, changed)
        changed = copy.deepcopy(self.manifest)
        changed["shards"].reverse()
        with self.assertRaisesRegex(globalv.GlobalError, "GLOBAL_RESERVED_OR_ORDER"):
            globalv.verify(ROOT, changed)
        changed = copy.deepcopy(self.manifest)
        changed["admitted"] = True
        with self.assertRaisesRegex(globalv.GlobalError, "MANIFEST_AUTHORITY"):
            globalv.verify(ROOT, changed)


if __name__ == "__main__":
    unittest.main()
