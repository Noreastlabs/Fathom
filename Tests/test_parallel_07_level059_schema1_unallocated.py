"""Source/authority regression checks for the detached Level59 field proposal."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("level59_projection", ROOT / "Tools/parallel_07_level059_schema1_unallocated.py")
assert SPEC and SPEC.loader
S = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(S)


class Level59Projection(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = S.inputs(ROOT)
        cls.proposal, cls.handoff = S.project(cls.data)

    def mutated(self) -> dict:
        return copy.deepcopy(self.data)

    def test_whole_workload_and_authority(self) -> None:
        p = self.proposal
        self.assertEqual(len(p["records"]), 11)
        self.assertEqual(sum(len(r["schema1_fields"]["events"]) for r in p["records"]), 1120)
        self.assertEqual([len(r["schema1_fields"]["events"]) for r in p["records"]], list(S.COUNTS.values()))
        self.assertEqual(len(p["records"][0]["silent_tasks"]["silent_commands"]), 48)
        self.assertTrue(all(f["source_refs"]["txt_start_line"] == f["source_refs"]["txt_end_line"]
                            for f in p["records"][0]["silent_tasks"]["relative_fret_formulas"]))
        self.assertEqual([sum(len(v["events"]) for v in p["records"][i]["alternative_authored_variants"]) for i in (3, 4)], [48, 40])
        self.assertEqual(len(p["records"][10]["task_instructions"]["call_response_pairs"]), 8)
        self.assertTrue(all(e["schema1_fields"]["event_id"] is None and e["schema1_fields"]["onset_q"] is None
                            and e["schema1_fields"]["duration_q"] is None and e["schema1_fields"]["pitch_binding"] is None
                            for r in p["records"] for e in r["schema1_fields"]["events"]))
        self.assertFalse(p["admitted"] or p["schema1_importable"] or p["runtime_eligible"])
        for module in ("F", "G", "J"):
            record = next(r for r in p["records"] if r["source_component"] == module)
            self.assertTrue(all("txt_start_line" in e["source_attack"]["source_refs"]
                                for e in record["schema1_fields"]["events"]))

    def test_k_pair_refs_and_sustain_not_duration(self) -> None:
        k = self.proposal["records"][10]
        instructions = k["task_instructions"]["call_response_pairs"]
        events = k["schema1_fields"]["events"]
        for no, instruction in enumerate(instructions, 1):
            self.assertEqual(instruction["question_event_ordinals"], list(range((no - 1) * 8 + 1, (no - 1) * 8 + 5)))
            self.assertEqual(instruction["answer_event_ordinals"], list(range((no - 1) * 8 + 5, no * 8 + 1)))
            self.assertIsNone(instruction["sustain_duration_q"])
            self.assertEqual([e["source_attack"]["phase"] for e in events[(no - 1) * 8:no * 8]], ["question"] * 4 + ["answer"] * 4)
            self.assertTrue(all(e["source_attack"]["source_refs"]["pdf_page"] == 19 for e in events[(no - 1) * 8:no * 8]))

    def test_negative_whole_note_drift(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["modules"]["B"][0]["single_notes"][0] = "D"
        with self.assertRaisesRegex(ValueError, "TAB/note divergence"):
            S.project(data)

    def test_negative_narrow_k_position_drift(self) -> None:
        data = self.mutated()
        data[S.NARROW]["call_response_pairs"][0]["positions"][0]["source_tab"]["fret_token"] = "6"
        with self.assertRaisesRegex(ValueError, "K whole/narrow position divergence"):
            S.project(data)

    def test_negative_variant_choice_or_row_drift(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["modules"]["D"]["curriculum_choice"] = "PDF"
        with self.assertRaisesRegex(ValueError, "D/E variant choice drift"):
            S.project(data)
        data = self.mutated()
        data[S.WHOLE]["modules"]["E"]["txt_alternate_variant"][3]["source_rows"][1] = "Nte|wrong"
        with self.assertRaisesRegex(ValueError, "source rows occurrence"):
            S.project(data)

    def test_negative_structured_txt_shape_drift(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["modules"]["F"][0]["shapes"][0]["triad"]["frets"][0] = 6
        with self.assertRaisesRegex(ValueError, "source rows occurrence"):
            S.project(data)

    def test_negative_catalog_admission_drift(self) -> None:
        data = self.mutated()
        entry = next(x for x in data[S.PACKAGE]["workbook_catalog"]["entries"] if x["workbook_id"] == "fg:workbook:000059")
        entry["admitted"] = True
        with self.assertRaisesRegex(ValueError, "catalog source-only boundary drift"):
            S.project(data)

    def test_sealed_outputs_match_replay(self) -> None:
        built = S.products(ROOT)
        for name, value in built.items():
            path = ROOT / S.OUT / name
            self.assertEqual(path.read_bytes(), S.encoded(value))
        summary = json.loads((ROOT / S.OUT / "summary.json").read_text())
        self.assertEqual(summary["proposal_sha256"], S.sha((ROOT / S.OUT / "field-proposal.json").read_bytes()))


if __name__ == "__main__":
    unittest.main()
