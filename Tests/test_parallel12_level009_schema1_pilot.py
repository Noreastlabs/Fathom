import copy
import importlib.util
import json
import unittest
from pathlib import Path


TOOL = Path(__file__).resolve().parents[1] / "Tools/parallel12_level009_schema1_pilot.py"
spec = importlib.util.spec_from_file_location("parallel12_level009_schema1_pilot", TOOL)
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


class Level9PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proposal, cls.transaction = pilot.build()

    def test_whole_workbook_source_and_music(self):
        summary = pilot.verify(self.proposal, self.transaction)
        self.assertEqual(summary, {"records": 108, "events": 5184, "variants": 432, "new_entities": 649, "timing_status": "unresolved", "authority": "provisional"})
        self.assertEqual(len({x["source_local_key"] for x in self.transaction["source_map"]}), 108)
        self.assertEqual([x["exercise_number"] for x in self.transaction["source_map"]], list(range(1, 109)))
        for record in self.proposal["records"]:
            events = record["events"]
            self.assertEqual([x["string"] for x in events[:4]], [1] * 4)
            self.assertEqual([x["string"] for x in events[24:28]], [6] * 4)
            self.assertEqual([x["midi"] - x["fret"] for x in events], [n for n in [40, 45, 50, 55, 59, 64, 64, 59, 55, 50, 45, 40] for _ in range(4)])
            self.assertTrue(all(x["onset_q"] is None and x["duration_q"] is None for x in events))
            self.assertEqual([v["label"] for v in record["variants"]], ["shift_up-D", "shift_up-U", "shift_down-D", "shift_down-U"])

    def test_reproducible(self):
        self.assertEqual((pilot.serialized(self.proposal), pilot.serialized(self.transaction)), tuple(map(pilot.serialized, pilot.build())))

    def test_invalid_authority_refused(self):
        proposal = copy.deepcopy(self.proposal)
        proposal["baseline"][str(pilot.BASE / "package.json")] = "0" * 64
        with self.assertRaisesRegex(pilot.ProposalError, "INVALID_AUTHORITY"):
            pilot.verify(proposal, self.transaction)

    def test_invented_timing_refused(self):
        proposal = copy.deepcopy(self.proposal)
        proposal["records"][0]["events"][0]["duration_q"] = [1, 2]
        with self.assertRaisesRegex(pilot.ProposalError, "UNSUPPORTED_TIMING"):
            pilot.verify(proposal, self.transaction)
        proposal = copy.deepcopy(self.proposal)
        proposal["records"][0]["variants"][0]["grouping"]["notes_per_beat"] = 2
        with self.assertRaisesRegex(pilot.ProposalError, "UNSUPPORTED_TIMING"):
            pilot.verify(proposal, self.transaction)

    def test_pin_mismatch_refused(self):
        original = pilot.PINS[pilot.AGG]
        try:
            pilot.PINS[pilot.AGG] = "0" * 64
            with self.assertRaisesRegex(pilot.ProposalError, "BASELINE_MISMATCH"):
                pilot.pin_inputs()
        finally:
            pilot.PINS[pilot.AGG] = original

    def test_corrected_allocation_skips_all_pending_reservations(self):
        registry = json.loads((pilot.ROOT / pilot.CURRENT / "identity-registry.json").read_text())
        proposal, transaction = pilot.rebase_reserved_ids(self.proposal, self.transaction, registry)
        for kind, first, last in (("module", 588, 695), ("item", 588, 695), ("variant", 5002, 5433)):
            ids = sorted(pilot.suffix(e["id"]) for e in transaction["new_entities"] if e["kind"] == kind)
            self.assertEqual(ids, list(range(first, last + 1)))
        self.assertEqual(proposal["records"][0]["id"], "fg:item:000588")
        self.assertEqual(proposal["records"][-1]["id"], "fg:item:000695")
        self.assertTrue(all(e["onset_q"] is None and e["duration_q"] is None for r in proposal["records"] for e in r["events"]))

    def test_each_reserved_identity_family_is_refused(self):
        registry = json.loads((pilot.ROOT / pilot.CURRENT / "identity-registry.json").read_text())
        _, transaction = pilot.rebase_reserved_ids(self.proposal, self.transaction, registry)
        for kind, reserved in (("module", "fg:module:000552"), ("item", "fg:item:000587"), ("variant", "fg:variant:005001")):
            entities = copy.deepcopy(transaction["new_entities"])
            next(e for e in entities if e["kind"] == kind)["id"] = reserved
            with self.subTest(kind=kind), self.assertRaisesRegex(pilot.ProposalError, "RESERVED_ID_COLLISION"):
                pilot.assert_not_reserved(entities, registry)

    def test_overlay_preserves_baseline_and_refuses_mutated_timing(self):
        artifacts = pilot.overlay_build()
        baseline_package = json.loads((pilot.ROOT / pilot.CURRENT / "package.json").read_text())
        baseline_registry = json.loads((pilot.ROOT / pilot.CURRENT / "identity-registry.json").read_text())
        proposal, transaction = pilot.rebase_reserved_ids(self.proposal, self.transaction, baseline_registry)
        pilot.overlay_verify(artifacts, baseline_package, baseline_registry, proposal, transaction)
        self.assertEqual([r["id"] for r in artifacts[pilot.OVERLAY / "package.json"]["records"][551:]], [r["id"] for r in proposal["records"]])
        mutated = copy.deepcopy(artifacts)
        mutated[pilot.OVERLAY / "package.json"]["records"][551]["events"][0]["onset_q"] = [0, 1]
        with self.assertRaisesRegex(pilot.ProposalError, "UNSUPPORTED_TIMING"):
            pilot.overlay_verify(mutated, baseline_package, baseline_registry, proposal, transaction)


if __name__ == "__main__":
    unittest.main()
