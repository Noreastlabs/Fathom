"""Focused Level45 source, mask, route, authority and replay checks."""

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("p07_level045", ROOT / "Tools/parallel_07_level045_schema1_unallocated.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class Level45ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = tool.read_inputs(ROOT)

    def changed(self):
        return copy.deepcopy(self.data)

    def test_whole_source_replay_and_written_core(self):
        proposal, handoff = tool.project(self.data)
        self.assertEqual(len(proposal["records"]), 55)
        self.assertEqual(sum(len(x["schema1_fields"]["events"]) for x in proposal["records"]), 540)
        self.assertEqual(proposal["module_attack_counts"], tool.COUNTS)
        self.assertEqual(handoff["source_discrepancies"], 3)

    def test_triplet_mask_and_two_bar_rest_geometry(self):
        d = self.changed()
        d["candidate"]["modules"]["B"][0]["bars"][0]["beats"][0] = "XX."
        with self.assertRaisesRegex(ValueError, "mask"):
            tool.project(d, replay=False)
        d = self.changed()
        d["candidate"]["modules"]["E"][0]["bars"][0]["attack_slots"].append([1, 1])
        with self.assertRaisesRegex(ValueError, "mask"):
            tool.project(d, replay=False)

    def test_tab_pitch_and_support_marker_replay(self):
        d = self.changed()
        d["candidate"]["modules"]["I"][0]["placements"][2]["fret"] += 1
        with self.assertRaisesRegex(ValueError, "TAB/pitch"):
            tool.project(d, replay=False)
        d = self.changed()
        d["candidate"]["modules"]["I"][0]["notes"][2] = "C#"
        with self.assertRaisesRegex(ValueError, "replay drift"):
            tool.project(d)

    def test_twelve_bar_and_pickup_route(self):
        d = self.changed()
        d["candidate"]["modules"]["C"]["form"][8]["root_fret"] = 5
        with self.assertRaisesRegex(ValueError, "C form route"):
            tool.project(d, replay=False)
        d = self.changed()
        d["candidate"]["modules"]["D"][0]["timing_masks"][0]["next_bar"]["attack_slots"] = [[1, 2]]
        with self.assertRaisesRegex(ValueError, "mask"):
            tool.project(d, replay=False)
        d = self.changed()
        d["candidate"]["modules"]["H"]["landmark"]["played_bars"].pop()
        with self.assertRaisesRegex(ValueError, "H landmark"):
            tool.project(d, replay=False)

    def test_capstone_reuse_and_source_differences(self):
        proposal, _ = tool.project(self.data, replay=False)
        self.assertEqual(proposal["capstone_reuse_reference"]["new_core_attacks"], 0)
        self.assertEqual(proposal["capstone_reuse_reference"]["existing_material_reused_attacks"], 108)
        self.assertEqual(len(proposal["source_discrepancies"]), 3)
        d = self.changed()
        d["candidate"]["capstone"]["included_in_written_core_540"] = True
        with self.assertRaisesRegex(ValueError, "capstone reuse"):
            tool.project(d, replay=False)
        d = self.changed()
        d["candidate"]["source_discrepancies"][1]["pdf_prose"] = "X.X|...|X.X|..."
        with self.assertRaisesRegex(ValueError, "source discrepancy"):
            tool.project(d, replay=False)

    def test_no_invented_timing_or_identity(self):
        d = self.changed()
        d["candidate"]["timing"]["fixed_bpm"] = 100
        with self.assertRaisesRegex(ValueError, "timing"):
            tool.project(d, replay=False)
        proposal, _ = tool.project(self.data, replay=False)
        self.assertFalse(proposal["admitted"])
        for record in proposal["records"]:
            self.assertIsNone(record["schema1_fields"]["id"])
            for e in record["schema1_fields"]["events"]:
                self.assertIsNone(e["id"])
                self.assertIsNone(e["performed_order"])
                self.assertIsNone(e["onset_q"])
                self.assertIsNone(e["duration_q"])
                self.assertIsNone(e["fixed_bpm"])
                self.assertIsNone(e["source_tone"]["sounding_midi"])

    def test_catalog_boundary_and_source_pins(self):
        d = self.changed()
        e = next(x for x in d["package"]["workbook_catalog"]["entries"] if x["workbook_id"] == "fg:workbook:000045")
        e["admitted"] = True
        with self.assertRaisesRegex(ValueError, "catalog boundary"):
            tool.project(d, replay=False)
        d = self.changed()
        row = next(x for x in d["source_map"]["rows"] if x["level"] == 45)
        row["stable_ids_assigned"] = True
        with self.assertRaisesRegex(ValueError, "source-map boundary"):
            tool.project(d, replay=False)
        for path in (tool.UPSTREAM, tool.TXT, tool.PDF, tool.TSV):
            self.assertEqual(tool.sha((ROOT / path).read_bytes()), tool.INPUTS[path])

    def test_deterministic_output_replay(self):
        first = tool.products(ROOT)
        second = tool.products(ROOT)
        self.assertEqual({k: tool.encoded(v) for k, v in first.items()},
                         {k: tool.encoded(v) for k, v in second.items()})
        tool.run("verify", ROOT)


if __name__ == "__main__":
    unittest.main()
