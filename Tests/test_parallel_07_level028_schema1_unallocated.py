"""Focused source and TAB-geometry checks for detached Level28 projection."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("level28_projection", ROOT / "Tools/parallel_07_level028_schema1_unallocated.py")
assert SPEC and SPEC.loader
S = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(S)


class Level28Projection(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = S.read_inputs(ROOT)
        cls.proposal, cls.handoff = S.project(cls.data)

    def mutated(self) -> dict:
        return copy.deepcopy(self.data)

    def test_unique_triad_contact_geometry(self) -> None:
        p = self.proposal
        self.assertEqual(len(p["records"]), 13)
        self.assertEqual([len(r["schema1_fields"]["variants"]) for r in p["records"]], [22] * 13)
        self.assertEqual([len(r["schema1_fields"]["events"]) for r in p["records"]], [66] * 13)
        self.assertEqual(sum(len(r["schema1_fields"]["variants"]) for r in p["records"]), 286)
        self.assertEqual(sum(len(r["schema1_fields"]["events"]) for r in p["records"]), 858)
        self.assertEqual([r["source_rung"]["root_fret"] for r in p["records"]], list(range(5, 18)))
        for r in p["records"]:
            self.assertTrue(r["source_rung"]["diatonic_triad_names"][4].endswith("m"))
            self.assertFalse(r["source_rung"]["diatonic_triad_names"][6].endswith(("m", "dim")))
            for event in r["schema1_fields"]["events"]:
                fields = event["schema1_fields"]
                self.assertTrue(all(fields[k] is None for k in ("event_id", "pick", "pitch_binding", "onset_q", "duration_q")))
                self.assertIsNone(event["source_tone"]["sounding_midi"])
        self.assertFalse(p["admitted"] or p["runtime_eligible"] or p["schema1_importable"])

    def test_turnaround_and_route_reuse(self) -> None:
        p = self.proposal
        first = p["records"][0]["schema1_fields"]["events"]
        self.assertEqual(first[32]["source_contact"]["ordinal"], 33)
        self.assertEqual(first[33]["source_contact"]["ordinal"], 34)
        self.assertEqual((first[32]["source_contact"]["string"], first[32]["source_contact"]["fret"],
                          first[32]["source_contact"]["pitch_spelling"]),
                         (first[33]["source_contact"]["string"], first[33]["source_contact"]["fret"],
                          first[33]["source_contact"]["pitch_spelling"]))
        route = p["round_trip_route_reference"]
        self.assertEqual(route["source_rung_order"], list(range(1, 14)) + list(range(12, 0, -1)))
        self.assertEqual(route["route_contact_occurrences"], 1650)
        self.assertEqual(route["new_unique_contacts"], 0)
        self.assertEqual([x["root_fret"] for x in route["cells"]], list(range(5, 18)) + list(range(16, 4, -1)))

    def test_negative_contact_tab_or_spelling_drift(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["rungs"][0]["triads"][0]["contacts"][0]["fret"] = 6
        with self.assertRaisesRegex(ValueError, "contact order/TAB/finger drift"):
            S.project(data)
        data = self.mutated()
        data[S.WHOLE]["rungs"][0]["triads"][0]["contacts"][0]["pitch_spelling"] = "Bb"
        with self.assertRaisesRegex(ValueError, "pitch spelling/TAB geometry drift"):
            S.project(data)

    def test_negative_degree_or_source_row_drift(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["rungs"][0]["triads"][0]["contacts"][0]["degree"] = "2"
        with self.assertRaisesRegex(ValueError, "degree/finger source-cell drift"):
            S.project(data)
        data = self.mutated()
        data[S.WHOLE]["rungs"][0]["source_rows"]["ascending"][0] = "Hrm|wrong"
        with self.assertRaisesRegex(ValueError, "source rows not pinned to TXT"):
            S.project(data)

    def test_negative_rung_or_route_conflation(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["rungs"][0]["triads"].pop()
        with self.assertRaisesRegex(ValueError, "rung key/root/frame/triad count drift"):
            S.project(data)
        data = self.mutated()
        data[S.WHOLE]["full_round_trip_route"][13]["rung"] = 13
        with self.assertRaisesRegex(ValueError, "round-trip route geometry/count drift"):
            S.project(data)

    def test_negative_timing_or_catalog_admission(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["rungs"][0]["triads"][0]["contacts"][0]["onset_q"] = 0
        with self.assertRaisesRegex(ValueError, "invented contact timing"):
            S.project(data)
        data = self.mutated()
        entry = next(x for x in data[S.PACKAGE]["workbook_catalog"]["entries"] if x["workbook_id"] == "fg:workbook:000028")
        entry["admitted"] = True
        with self.assertRaisesRegex(ValueError, "source-only catalog boundary drift"):
            S.project(data)

    def test_negative_source_conflict_or_input_drift(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["source_discrepancies"].append({"invented": True})
        with self.assertRaisesRegex(ValueError, "candidate scope/conflict drift"):
            S.project(data)
        data = self.mutated()
        data[S.WHOLE]["source"]["txt_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "original source identity drift"):
            S.project(data)

    def test_sealed_output_replay(self) -> None:
        products = S.products(ROOT)
        for name, value in products.items():
            self.assertEqual((ROOT / S.OUT / name).read_bytes(), S.encoded(value))
        summary = json.loads((ROOT / S.OUT / "summary.json").read_text())
        self.assertEqual(summary["proposal_sha256"], S.sha((ROOT / S.OUT / "field-proposal.json").read_bytes()))


if __name__ == "__main__":
    unittest.main()
