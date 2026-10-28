"""Focused Level36 source, geometry, authority and replay checks."""

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("p07_level036", ROOT / "Tools/parallel_07_level036_schema1_unallocated.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class Level36ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = tool.read_inputs(ROOT)
        cls.data["root"] = ROOT

    def changed(self):
        return copy.deepcopy(self.data)

    def test_whole_source_replay_and_count_boundary(self):
        proposal, handoff = tool.project(self.data)
        self.assertEqual(len(proposal["records"]), 37)
        self.assertEqual(sum(len(x["schema1_fields"]["events"]) for x in proposal["records"]), 165)
        self.assertEqual(proposal["counts"], tool.COUNTS)
        self.assertEqual(handoff["cadence_pdf_omissions"], 4)

    def test_module_a_note_and_finger_geometry(self):
        d = self.changed()
        d["candidate"]["modules"]["A_legato_positions"][0]["groups"][0]["frets"][0] += 1
        with self.assertRaisesRegex(ValueError, "geometry"):
            tool.project(d, replay=False)
        d = self.changed()
        d["candidate"]["modules"]["A_legato_positions"][0]["groups"][0]["fingers"][0] = 5
        with self.assertRaisesRegex(ValueError, "geometry"):
            tool.project(d, replay=False)

    def test_seam_route_and_bend_target_geometry(self):
        d = self.changed()
        d["candidate"]["modules"]["B_seam_chains"][0]["phrases"][0]["frets"][3] += 1
        with self.assertRaisesRegex(ValueError, "geometry"):
            tool.project(d, replay=False)
        d = self.changed()
        d["candidate"]["modules"]["C_whole_step_bends"][0]["target_fret"] += 1
        with self.assertRaisesRegex(ValueError, "geometry"):
            tool.project(d, replay=False)

    def test_cadence_txt_tab_and_pdf_difference(self):
        d = self.changed()
        d["candidate"]["modules"]["E_cadences"][0]["tab_rows"][0] += "x"
        with self.assertRaisesRegex(ValueError, "cadence TAB"):
            tool.project(d, replay=False)
        d = self.changed()
        d["candidate"]["source_discrepancies"].pop()
        with self.assertRaisesRegex(ValueError, "PDF omission"):
            tool.project(d, replay=False)
        d = self.changed()
        d["candidate"]["modules"]["E_cadences"][0]["pdf_notes_raw"] = "invented"
        with self.assertRaisesRegex(ValueError, "cadence TAB"):
            tool.project(d, replay=False)

    def test_no_invented_timing_or_performance_order(self):
        d = self.changed()
        d["candidate"]["fixed_bpm"] = 90
        with self.assertRaisesRegex(ValueError, "authority"):
            tool.project(d, replay=False)
        proposal, _ = tool.project(self.data, replay=False)
        self.assertIsNone(proposal["source_route_claims"]["cadence_performance_order"])
        self.assertFalse(proposal["admitted"])
        for record in proposal["records"]:
            self.assertIsNone(record["schema1_fields"]["id"])
            for event in record["schema1_fields"]["events"]:
                self.assertIsNone(event["id"])
                self.assertIsNone(event["performed_order"])
                self.assertIsNone(event["onset_q"])
                self.assertIsNone(event["duration_q"])
                self.assertIsNone(event["fixed_bpm"])

    def test_catalog_and_frozen_source_map_boundary(self):
        d = self.changed()
        e = next(x for x in d["package"]["workbook_catalog"]["entries"] if x["workbook_id"] == "fg:workbook:000036")
        e["admitted"] = True
        with self.assertRaisesRegex(ValueError, "catalog boundary"):
            tool.project(d, replay=False)
        d = self.changed()
        row = next(x for x in d["map"]["rows"] if x["level"] == 36)
        row["stable_ids_assigned"] = True
        with self.assertRaisesRegex(ValueError, "source-map boundary"):
            tool.project(d, replay=False)

    def test_input_pin_and_candidate_replay_drift(self):
        d = self.changed()
        d["candidate"]["source_guidance"]["txt_lines_1_40"][0] = "drift"
        with self.assertRaisesRegex(ValueError, "replay drift"):
            tool.project(d)
        self.assertEqual(tool.digest((ROOT / tool.UPSTREAM).read_bytes()), tool.INPUTS[tool.UPSTREAM])
        self.assertEqual(tool.digest((ROOT / tool.TXT).read_bytes()), tool.INPUTS[tool.TXT])
        self.assertEqual(tool.digest((ROOT / tool.PDF).read_bytes()), tool.INPUTS[tool.PDF])

    def test_deterministic_output_and_disk_verify(self):
        first = tool.products(ROOT)
        second = tool.products(ROOT)
        self.assertEqual({k: tool.encoded(v) for k, v in first.items()},
                         {k: tool.encoded(v) for k, v in second.items()})
        tool.run("verify", ROOT)


if __name__ == "__main__":
    unittest.main()
