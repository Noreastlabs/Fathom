"""Offline projection contract and meaningful refusal cases."""

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "bridge_projection", ROOT / "Tools/parallel06_bridge_resource_projection.py")
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)


class ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = bridge.load_pinned(ROOT)
        cls.plan = cls.docs[bridge.PLAN]
        cls.content = cls.docs[bridge.CONTENT]

    def copy_content(self):
        return json.loads(json.dumps(self.content))

    def test_exact_plan_and_source_contract(self):
        cards = bridge.validate_cards(self.plan, self.content)
        passages = bridge.validate_passages(ROOT, self.content)
        self.assertEqual(len(cards), 21)
        self.assertEqual(len(passages), 43)
        self.assertEqual([x["id"] for x in cards[:5]], ["G01", "G02", "G03", "G04", "G05"])
        for card in cards[5:]:
            approved = next(x for x in self.plan["resources"] if x["id"] == card["id"])
            self.assertEqual(card["approved_requirement"]["required_outputs"], approved["required_outputs"])
            self.assertEqual(card["availability"], "required_unsupplied")
            self.assertIsNone(approved["supplied_asset"])

    def test_missing_card_refused_by_id(self):
        changed = self.copy_content()
        changed["cards"] = [x for x in changed["cards"] if x["id"] != "R97C"]
        with self.assertRaisesRegex(bridge.Refusal, r"source card omission.*R97C"):
            bridge.validate_cards(self.plan, changed)

    def test_missing_required_output_refused(self):
        changed = self.copy_content()
        next(x for x in changed["cards"] if x["id"] == "R97C")["approved_requirement"]["required_outputs"].pop()
        with self.assertRaisesRegex(bridge.Refusal, "R97C: changed or incomplete accepted requirement"):
            bridge.validate_cards(self.plan, changed)

    def test_fake_supplied_asset_refused(self):
        changed = self.copy_content()
        next(x for x in changed["cards"] if x["id"] == "R39")["availability"] = "supplied"
        with self.assertRaisesRegex(bridge.Refusal, "R39: resource availability"):
            bridge.validate_cards(self.plan, changed)

    def test_source_drift_refused_with_ref_and_path(self):
        first = next(iter(self.content["source_passages"].values()))["path"]

        def changed_reader(relative):
            data = bridge.local_file(ROOT, relative).read_bytes()
            return data + b"changed" if relative == first else data

        with self.assertRaisesRegex(bridge.Refusal, "source drift: .*Notes/"):
            bridge.validate_passages(ROOT, self.content, changed_reader)

    def test_missing_passage_refused(self):
        changed = self.copy_content()
        del changed["source_passages"]["L12-TXT9-39"]
        with self.assertRaisesRegex(bridge.Refusal, "missing source passages: .*L12-TXT9-39"):
            bridge.validate_passages(ROOT, changed)

    def test_pinned_binding_and_bundle_files(self):
        manifest = self.docs[bridge.PRESENTATION]
        self.assertEqual(manifest["files"]["content.json"], bridge.PINNED[bridge.CONTENT])
        self.assertEqual(manifest["plan_sha256"], bridge.PINNED[bridge.CORRECTION])
        bundle = ROOT / "Build/parallel-06/bridge-resource-projection-r01/final-run03"
        if bundle.exists():
            m = json.loads((bundle / "manifest.json").read_text())
            self.assertEqual(m["version"], "bridge-resource-bundle.1")
            self.assertEqual(len(m["bridge_ids"]), 5)
            self.assertEqual(len(m["resource_ids"]), 16)
            self.assertEqual(m["supplied_assets"], [])
            self.assertFalse(m["runtime_admitted"])
            for item in m["files"]:
                data = (bundle / item["path"]).read_bytes()
                self.assertEqual((len(data), bridge.digest(data)), (item["bytes"], item["sha256"]))
            projected = json.loads((bundle / "cards.json").read_text())["cards"]
            for card in projected:
                self.assertFalse(card["runtime_admitted"])
                self.assertIsNone(card["supplied_asset"])
                self.assertTrue(card["source_links"])
                if card["kind"] == "resource":
                    self.assertEqual(card["availability"], "required_unsupplied")
                    self.assertEqual(card["required_outputs"], card["approved_requirement"]["required_outputs"])


if __name__ == "__main__":
    unittest.main()
