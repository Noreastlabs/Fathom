#!/usr/bin/env python3
"""Focused exact-export, explicit-choice, and custody checks; no native job."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import sys
import time
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("level068_compiler", ROOT / "Tools/exercise-family-compiler/compile_level068.py")
compiler = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compiler)
OUT = ROOT / "Build/manager-resume-r03/level068-generation-r01"


class Level068Compiler(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.family = compiler.FrozenFamilies(ROOT)
        cls.rows = [compiler.strict_json(line) for line in (OUT / "definitions.jsonl").read_bytes().splitlines()]
        cls.closure = compiler.strict_json((OUT / "family-closure.json").read_bytes())

    def request(self, row, start="D"):
        request = {"package_key": row["source_key"], "contract_sha256": row["contract_sha256"], "start_stroke": start}
        if row["recipe"] == "recovery_pair":
            domain = self.family.allowed_choices(row["source_key"])
            origin = domain["source_contacts"][0]
            target = self.family.allowed_choices(row["source_key"], origin)["nearest_target_contacts"][0]
            request.update(source_contact=origin, target_contact=target,
                           rest_of_bar_plan="Explicit test-only manual plan: simplify remaining existing bar and release.")
        return request

    def test_exact_export_and_determinism(self):
        self.assertEqual(len(self.rows), 17)
        self.assertEqual({recipe: sum(r["recipe"] == recipe for r in self.rows) for recipe in compiler.RECIPES},
                         {"call_answer": 5, "recovery_pair": 12})
        self.assertEqual(compiler.encoded(self.rows), compiler.encoded(self.family.rows))
        self.assertEqual(compiler.encoded(self.closure, sort=True), compiler.encoded(self.family.closure(), sort=True))
        for row in self.rows:
            self.family.validate_row(row)
            self.assertEqual(row["contract_sha256"], compiler.digest(row["contract"]))
            self.assertIn(row["context_ref"], self.closure["contexts"])
        self.assertEqual(len(self.closure["contexts"]), 2)
        self.assertEqual(len(self.closure["source_pins"]), 3)

    def test_explicit_choices_for_every_row_both_pick_starts(self):
        for row in self.rows:
            domain = self.family.allowed_choices(row["source_key"])
            self.assertIsNone(domain["default_choice"])
            self.assertEqual(domain["start_strokes"], ["D", "U"])
            for start in ("D", "U"):
                request = self.request(row, start)
                selected = self.family.selection(row, request)
                self.assertFalse(selected["grants_credit"])
                self.assertFalse(selected["performance_observed"])
                if row["recipe"] == "call_answer":
                    self.assertEqual(len(selected["paired"]), 16)
                    self.assertEqual(len(selected["variation_call"]) + len(selected["variation_answer"]), 16)
                    self.assertEqual(selected["paired"][0]["selected_pick"], start)
                    self.assertEqual(selected["silent_gap"]["source_beats"], 2)
                    self.assertIsNone(selected["silent_gap"]["beat_to_quarter_note_mapping"])
                    self.assertFalse(selected["silent_gap"]["automatic_scheduling"])
                else:
                    self.assertEqual(len(selected["chosen_pair"]), 2)
                    self.assertEqual(selected["chosen_pair"][0]["selected_pick"], start)
                    self.assertFalse(selected["remainder_notes_or_attacks_generated"])
                    self.assertTrue(all(e["onset_q"] is None and e["duration_q"] is None for e in selected["chosen_pair"]))

    def test_complete_report_schemas_stay_manual_and_failed_release_is_retry(self):
        for row in self.rows:
            model = self.family.models[row["recipe"]]
            request = self.request(row)
            responses = model.done_responses() if row["recipe"] == "call_answer" else model.done_responses(row["contract"], request)
            state = model.workflow_state(row["contract"], request, responses)
            self.assertEqual(state["state"], "USER_REPORTED_STEPS_FINISHED")
            self.assertFalse(state["grants_credit"])
            self.assertFalse(state["performance_observed"])
            release = "final_A_released_reported" if row["recipe"] == "call_answer" else "final_target_released_reported"
            failed = copy.deepcopy(responses); failed[-1][release] = False
            self.assertEqual(model.workflow_state(row["contract"], request, failed)["state"], "NEEDS_RETRY")

    def test_changed_row_or_choice_identity_refuses(self):
        for row in (self.rows[0], self.rows[5]):
            bad = copy.deepcopy(row); bad["contract"]["grants_credit"] = True
            with self.assertRaises(compiler.Refusal): self.family.validate_row(bad)
            bad = copy.deepcopy(row); bad["contract"]["numeric_clock"] = 90
            with self.assertRaises(compiler.Refusal): self.family.validate_row(bad)
            bad = copy.deepcopy(row); bad["source_key"] = "foreign"
            with self.assertRaises(compiler.Refusal): self.family.validate_row(bad)
            bad = copy.deepcopy(row); bad["recipe"] = "triad"
            with self.assertRaises(compiler.Refusal): self.family.validate_row(bad)
            bad = copy.deepcopy(row); bad["context_ref"] = "foreign"
            with self.assertRaises(compiler.Refusal): self.family.validate_row(bad)
            request = self.request(row)
            for change in ({"package_key": "foreign"}, {"contract_sha256": "0" * 64}, {"start_stroke": ""}):
                wrong = {**request, **change}
                with self.assertRaises(ValueError): self.family.selection(row, wrong)
            with self.assertRaises(ValueError): self.family.selection(row, {**request, "fixed_bpm": 90})

    def test_recovery_domains_reject_unprinted_or_non_nearest_realizations(self):
        row = self.rows[5]; model = self.family.models["recovery_pair"]
        request = self.request(row)
        for change in ({"source_contact": {"string": True, "fret": 0}},
                       {"target_contact": {"string": 1, "fret": 99}},
                       {"rest_of_bar_plan": " "}, {"rest_of_bar_plan": "a" * 501}):
            with self.assertRaises(ValueError): self.family.selection(row, {**request, **change})
        destination = row["contract"]["source_pitch_events"][1]["printed_note"]
        nearest = model.nearest_targets(request["source_contact"], destination)
        far = next(c for c in model.pitch_menu(destination) if c not in nearest)
        with self.assertRaises(ValueError): self.family.selection(row, {**request, "target_contact": far})
        self.assertIsNone(row["contract"]["printed_contact_positions"])
        self.assertTrue(row["contract"]["selection_policy"]["nearest_policy_is_provisional_implementation_interpretation"])
        g = self.rows[7]["contract"]
        self.assertEqual(g["source_pitch_events"][0]["printed_note"], "G")
        self.assertIn("only in E7", g["borrowed_G_natural_scope"])
        with self.assertRaises(compiler.Refusal): self.family.allowed_choices("foreign")
        with self.assertRaises(compiler.Refusal): self.family.allowed_choices(self.rows[0]["source_key"], {"string": 1, "fret": 0})

    def test_custody_and_malformed_json_refusals_no_writes(self):
        with self.assertRaises(compiler.Refusal):
            compiler.read_pinned(ROOT, compiler.RECIPES["call_answer"]["packet"], "0" * 64)
        for text in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'):
            with self.assertRaises(compiler.Refusal): compiler.strict_json(text)
        with self.assertRaises(compiler.Refusal): compiler.compile_family(ROOT, OUT)
        with self.assertRaises(compiler.Refusal): compiler.compile_family(ROOT, ROOT / "Source/forbidden-generation")
        self.assertFalse((ROOT / "Source/forbidden-generation").exists())


if __name__ == "__main__":
    begin = time.perf_counter()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Level068Compiler)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    print(json.dumps({"result": "PASS" if result.wasSuccessful() else "FAIL", "tests": result.testsRun,
                      "failures": len(result.failures), "errors": len(result.errors),
                      "seconds": round(time.perf_counter() - begin, 6), "all_rows_compared": 17,
                      "explicit_choice_requests": 34, "manual_workflows": 17,
                      "native_jobs": 0, "new_source_research": False}))
    sys.exit(0 if result.wasSuccessful() else 1)
