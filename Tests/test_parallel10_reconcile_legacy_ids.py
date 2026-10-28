"""Focused exact-union and fail-closed checks for P10's Build-only candidate."""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from Tools import parallel10_reconcile_legacy_ids as reconcile


ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / "Build/parallel-10/2.3-legacy-id-reconciliation-r01/tests"


class ReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data, cls.manifest = reconcile.load_inputs(reconcile.source_root(ROOT))

    def test_exact_551_union_and_historical_identity(self) -> None:
        candidate = reconcile.compose(self.data)
        old = {row["id"]: row for row in self.data["current_package"]["records"]}
        new = {row["id"]: row for row in candidate["package.json"]["records"]}
        proof = {row["id"]: row["preserved_record"] for row in self.data["reviewed_report"]["records"]}
        self.assertEqual(len(new), 551)
        self.assertEqual({id_: new[id_] for id_ in old}, old)
        self.assertEqual(set(new) - set(old), set(reconcile.MISSING))
        self.assertEqual({id_: new[id_] for id_ in reconcile.MISSING},
                         {id_: proof[id_] for id_ in reconcile.MISSING})
        self.assertTrue(all(row["runtime_eligible"] is False for row in new.values()))
        self.assertEqual(candidate["generation.json"]["events"], 21661)
        self.assertEqual(candidate["generation.json"]["variants"], 4569)
        self.assertEqual(candidate["generation.json"]["current_entities"], 5687)
        self.assertEqual(candidate["generation.json"]["passages"], 657)
        self.assertEqual(candidate["identity-registry.json"]["entities"],
                         self.data["r14_registry"]["entities"])
        self.assertEqual(candidate["expected-profile.json"]["classification"],
                         "converted_candidate_reference")
        selected = candidate["authority-selection.json"]["selected"]
        for role in (*reconcile.BASELINE_PATHS, "candidate_identity_allocation"):
            self.assertEqual(sum(entry["role"] == role for entry in selected), 1)
        self.assertEqual(sum(entry["role"] == "predecessor_validation" for entry in selected), 13)
        self.assertEqual(len({entry["path"] for entry in selected}), len(selected))

    def test_candidate_bytes_are_deterministic(self) -> None:
        first = reconcile.compose(self.data)
        second = reconcile.compose(self.data)
        self.assertEqual({name: reconcile.digest(reconcile.encoded(value)) for name, value in first.items()},
                         {name: reconcile.digest(reconcile.encoded(value)) for name, value in second.items()})

    def assert_refusal_without_output(self, changed: dict, code: str) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
            output = Path(temporary) / "candidate"
            with self.assertRaisesRegex(reconcile.ReconciliationError, code):
                reconcile.write_candidate(output, reconcile.compose(changed), self.manifest)
            self.assertFalse(output.exists())

    def changed_current_record(self, mutate) -> dict:
        changed = dict(self.data)
        package = dict(self.data["current_package"])
        records = list(package["records"])
        row = copy.deepcopy(records[0])
        mutate(row)
        records[0] = row
        package["records"] = records
        changed["current_package"] = package
        profile = dict(self.data["current_profile"])
        profile["reference_package"] = {key: value for key, value in package.items() if key != "workbook_catalog"}
        changed["current_profile"] = profile
        return changed

    def test_existing_target_id_refused(self) -> None:
        self.assert_refusal_without_output(
            self.changed_current_record(lambda row: row.__setitem__("id", reconcile.MISSING[0])),
            "TARGET_PRESENT")

    def test_event_collision_refused(self) -> None:
        event = self.data["reviewed_report"]["records"][2]["preserved_record"]["events"][0]["event_id"]
        self.assert_refusal_without_output(
            self.changed_current_record(lambda row: row["events"][0].__setitem__("event_id", event)),
            "EVENT_COLLISION")

    def test_variant_collision_refused(self) -> None:
        historic = next(row for row in self.data["reviewed_report"]["records"]
                        if row["id"] == reconcile.MISSING[0])
        variant = historic["preserved_record"]["variants"][0]["id"]
        self.assert_refusal_without_output(
            self.changed_current_record(lambda row: row["variants"][0].__setitem__("id", variant)),
            "VARIANT_COLLISION")

    def test_source_reference_conflict_refused(self) -> None:
        changed = dict(self.data)
        package = dict(self.data["current_package"])
        sources = dict(package["sources"])
        ref = "L12-TXT14-28"
        sources[ref] = dict(self.data["control_package"]["sources"][ref], text="tampered passage")
        package["sources"] = sources
        changed["current_package"] = package
        profile = dict(self.data["current_profile"])
        profile["reference_package"] = {key: value for key, value in package.items() if key != "workbook_catalog"}
        changed["current_profile"] = profile
        self.assert_refusal_without_output(changed, "SOURCE_CONFLICT")

    def test_historical_entity_conflict_refused(self) -> None:
        changed = dict(self.data)
        registry = dict(self.data["control_registry"])
        entities = list(registry["entities"])
        index = next(i for i, entity in enumerate(entities) if entity["id"] == reconcile.MISSING[0])
        entities[index] = dict(entities[index], label="unreviewed label")
        registry["entities"] = entities
        changed["control_registry"] = registry
        self.assert_refusal_without_output(changed, "ENTITY_CONFLICT")


if __name__ == "__main__":
    unittest.main()
