"""Focused source/authority checks for detached Level77 field proposal."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("level77_projection", ROOT / "Tools/parallel_07_level077_schema1_unallocated.py")
assert SPEC and SPEC.loader
S = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(S)


class Level77Projection(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = S.read_inputs(ROOT)
        cls.proposal, cls.handoff = S.project(cls.data)

    def mutated(self) -> dict:
        return copy.deepcopy(self.data)

    def test_explicit_versus_declared_workload(self) -> None:
        p = self.proposal
        self.assertEqual(len(p["records"]), 8)
        self.assertEqual([len(r["source_tasks"]) for r in p["records"]], list(S.TASKS.values()))
        self.assertEqual([len(r["schema1_fields"]["events"]) for r in p["records"]], list(S.EXPLICIT.values()))
        self.assertEqual(sum(len(r["source_tasks"]) for r in p["records"]), 206)
        self.assertEqual(sum(len(r["schema1_fields"]["events"]) for r in p["records"]), 277)
        self.assertEqual(sum(r["source_declared_workload"] for r in p["records"]), 952)
        self.assertEqual(len(p["pdf_tables"]), 16)
        self.assertEqual(len(p["source_archive"]["txt_lines"]), 80)
        self.assertEqual(len(p["source_archive"]["pdf_pages"]), 20)
        self.assertFalse(p["admitted"] or p["runtime_eligible"] or p["schema1_importable"])

    def test_source_order_inference_and_nulls(self) -> None:
        p = self.proposal
        tasks = [task for r in p["records"] for task in r["source_tasks"]]
        self.assertEqual(sorted(x["source_global_ordinal"] for x in tasks), list(range(1, 207)))
        self.assertEqual([p["source_task_order"][x["source_global_ordinal"] - 1] for x in tasks],
                         [x["source_task"]["local_key"] for x in tasks])
        prompts = [x["source_task"] for x in tasks if x["source_task"]["kind"] == "random_function_prompt"]
        self.assertEqual(len(prompts), 18)
        self.assertTrue(all(x["fields"]["printed_answer"] is None and
                            x["fields"]["answer_provenance"] == "music_theory_inference_not_printed" for x in prompts))
        for record in p["records"]:
            for event in record["schema1_fields"]["events"]:
                fields = event["schema1_fields"]
                self.assertTrue(all(fields[key] is None for key in ("event_id", "contact", "pick", "pitch_binding", "onset_q", "duration_q")))
                self.assertIsNone(event["source_tone"]["sounding_midi"])
        self.assertEqual(p["source_tensions"][0]["printed_answer"], "m6")
        self.assertEqual(p["source_tensions"][0]["computed_semitones"], 9)
        self.assertEqual(p["source_tensions"][2]["missing_prompt_numbers"], list(range(19, 25)))

    def test_negative_declared_count_or_task_loss(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["declared_workload_total"] = 277
        with self.assertRaisesRegex(ValueError, "declared workload drift"):
            S.project(data)
        data = self.mutated()
        data[S.WHOLE]["tasks"].pop()
        with self.assertRaisesRegex(ValueError, "explicit task/event count drift"):
            S.project(data)

    def test_negative_event_authority_or_ref_drift(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["explicit_pitch_events"][0]["fret"] = 3
        with self.assertRaisesRegex(ValueError, "invented performance/identity"):
            S.project(data)
        data = self.mutated()
        data[S.WHOLE]["explicit_pitch_events"][0]["source"]["row"] = 999
        with self.assertRaisesRegex(ValueError, "PDF table/row ref drift"):
            S.project(data)

    def test_negative_inference_provenance(self) -> None:
        data = self.mutated()
        task = next(x for x in data[S.WHOLE]["tasks"] if x["kind"] == "random_function_prompt")
        task["fields"]["printed_answer"] = task["fields"]["derived_answer"]
        with self.assertRaisesRegex(ValueError, "inference boundary drift"):
            S.project(data)

    def test_negative_source_tension_or_inventory_status(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["source_tensions"][0]["computed_semitones"] = 8
        with self.assertRaisesRegex(ValueError, "card-20 interval conflict lost"):
            S.project(data)
        data = self.mutated()
        entry = next(x for x in data[S.PACKAGE]["workbook_catalog"]["entries"] if x["workbook_id"] == "fg:workbook:000077")
        entry["admitted"] = True
        with self.assertRaisesRegex(ValueError, "source-only catalog boundary drift"):
            S.project(data)

    def test_negative_original_archive_drift(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["source_archive"]["txt_lines"][0]["text"] = "changed"
        with self.assertRaisesRegex(ValueError, "original TXT/archive drift"):
            S.project(data)

    def test_sealed_output_replay(self) -> None:
        products = S.products(ROOT)
        for name, value in products.items():
            self.assertEqual((ROOT / S.OUT / name).read_bytes(), S.encoded(value))
        summary = json.loads((ROOT / S.OUT / "summary.json").read_text())
        self.assertEqual(summary["proposal_sha256"], S.sha((ROOT / S.OUT / "field-proposal.json").read_bytes()))


if __name__ == "__main__":
    unittest.main()
