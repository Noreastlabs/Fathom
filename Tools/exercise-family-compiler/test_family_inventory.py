#!/usr/bin/env python3
"""Focused negative controls for inventory custody/prestate guards (no model QA)."""
import copy
import importlib.util
import io
import json
import pathlib
import tempfile
import time
import unittest

SPEC = importlib.util.spec_from_file_location("inventory", pathlib.Path(__file__).with_name("build_family_inventory.py"))
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
OUT = pathlib.Path("Build/manager-resume-r03/family-inventory-r01")


class InventoryGuards(unittest.TestCase):
    def setUp(self):
        self.official = {"k": {"source_identity": "s", "level": 53, "existing_parent_id": "p"}}
        self.old = M.metadata({"package_key": "k", "source_identity": "s", "level": 53,
                               "existing_parent_id": "p", "implementation": {"kind": "manual", "fret": 3}}, b"old")
        self.old["ref"] = {"path": "Build/old.jsonl", "sha256": "a" * 64, "jsonl_line": 1}
        self.new = M.metadata({"package_key": "k", "source_identity": "s", "level": 53,
                               "existing_parent_id": "p", "implementation": {"kind": "manual", "fret": 5}}, b"new")
        self.new["ref"] = {"path": "Build/new.jsonl", "sha256": "b" * 64, "jsonl_line": 1}
        self.state = {"k": {"row": self.old, "category": "pending"}}
        self.change = {"package_key": "k", "source_identity": "s", "base_record_sha256": self.old["compact_order_sha256"],
                       "overlay_record_sha256": self.new["compact_order_sha256"], "old_category": "pending", "new_category": "manual"}
        self.c_item = {"package_key": "k", "source_identity": "s", "previous_category": "pending", "effective_category": "manual"}

    def test_b_legal_transition(self):
        M.b_transition(self.official, self.state, self.change, self.new, set(), False)
        self.assertEqual(self.state["k"]["row"], self.new)

    def test_b_unknown_key(self):
        self.change["package_key"] = "unknown"
        with self.assertRaisesRegex(M.Refusal, "unknown B"):
            M.b_transition(self.official, self.state, self.change, self.new, set(), False)

    def test_b_wrong_preimage(self):
        self.change["base_record_sha256"] = "bad"
        with self.assertRaisesRegex(M.Refusal, "previous-effective"):
            M.b_transition(self.official, self.state, self.change, self.new, set(), False)

    def test_b_wrong_overlay_hash(self):
        self.change["overlay_record_sha256"] = "bad"
        with self.assertRaisesRegex(M.Refusal, "overlay record hash"):
            M.b_transition(self.official, self.state, self.change, self.new, set(), False)

    def test_b_wrong_category(self):
        self.change["old_category"] = "manual"
        with self.assertRaisesRegex(M.Refusal, "category prestate"):
            M.b_transition(self.official, self.state, self.change, self.new, set(), False)

    def test_b_undeclared_repeat(self):
        with self.assertRaisesRegex(M.Refusal, "revision/preimage"):
            M.b_transition(self.official, self.state, self.change, self.new, {"k"}, False)

    def test_b_repeat_without_preimage_basis(self):
        with self.assertRaisesRegex(M.Refusal, "revision/preimage"):
            M.b_transition(self.official, self.state, self.change, self.new, {"k"}, True)

    def test_b_new_key_marked_revision(self):
        with self.assertRaisesRegex(M.Refusal, "falsely marked revision"):
            M.b_transition(self.official, self.state, self.change, self.new, set(), True)

    def test_b_legal_declared_revision(self):
        self.change["replacement_basis"] = "previous_effective_record"
        M.b_transition(self.official, self.state, self.change, self.new, {"k"}, True)
        self.assertEqual(self.state["k"]["category"], "manual")

    def test_source_identity_crosswire(self):
        self.new["source_identity"] = "other"
        with self.assertRaisesRegex(M.Refusal, "source-identity"):
            M.join(self.official, self.new, "k")

    def test_key_crosswire(self):
        self.new["package_key"] = "other"
        with self.assertRaisesRegex(M.Refusal, "record-key"):
            M.join(self.official, self.new, "k")

    def test_level_crosswire(self):
        self.new["level"] = 54
        with self.assertRaisesRegex(M.Refusal, "level mismatch"):
            M.join(self.official, self.new, "k")

    def test_parent_crosswire(self):
        self.new["existing_parent_id"] = "q"
        with self.assertRaisesRegex(M.Refusal, "parent mismatch"):
            M.join(self.official, self.new, "k")

    def test_c_category_prestate(self):
        self.c_item["previous_category"] = "manual"
        with self.assertRaisesRegex(M.Refusal, "category prestate"):
            M.c_transition(self.official, self.state, self.c_item, self.new)

    def test_c_explicit_previous_payload(self):
        self.c_item["previous_effective_payload"] = self.old["ref"]
        M.c_transition(self.official, self.state, self.c_item, self.new)
        self.assertEqual(self.state["k"]["category"], "manual")

    def test_c_wrong_explicit_previous_payload(self):
        self.c_item["previous_effective_payload"] = self.new["ref"]
        with self.assertRaisesRegex(M.Refusal, "explicit previous payload"):
            M.c_transition(self.official, self.state, self.c_item, self.new)

    def test_duplicate_json_members(self):
        with self.assertRaisesRegex(M.Refusal, "duplicate JSON"):
            M.strict_json('{"key":1,"key":2}')

    def test_nonfinite_json(self):
        with self.assertRaisesRegex(M.Refusal, "nonfinite JSON"):
            M.strict_json('{"key":NaN}')

    def test_category_counts_refuse(self):
        with self.assertRaisesRegex(M.Refusal, "category/count"):
            M.same_counts({"manual": 2}, {"manual": 1}, "fixture")

    def test_predecessor_cycle(self):
        class FakeCache:
            def json(self, ref):
                return {"prior": {"path": "cycle", "sha256": "a"}}
        with self.assertRaisesRegex(M.Refusal, "predecessor cycle"):
            M.chain(FakeCache(), {"path": "cycle", "sha256": "a"}, "prior")

    def test_structural_hint_is_not_music_equivalence(self):
        self.assertEqual(self.old["structural_hint_sha256"], self.new["structural_hint_sha256"])
        self.assertNotEqual(self.old["canonical_sha256"], self.new["canonical_sha256"])

    def test_canonical_order_encodings_remain_distinct(self):
        a = {"b": 1, "a": 2}
        b = {"a": 2, "b": 1}
        self.assertEqual(M.compact(a, True), M.compact(b, True))
        self.assertNotEqual(M.compact(a), M.compact(b))

    def test_cache_file_hash_bytes_path_and_duplicate_packet(self):
        with tempfile.TemporaryDirectory(dir=OUT, prefix="guard-fixture-") as directory:
            root = pathlib.Path(directory)
            raw = M.compact({"package_key": "k", "source_identity": "s"}) + b"\n"
            (root / "packet.jsonl").write_bytes(raw)
            cache = M.Cache(root)
            ref = {"path": "packet.jsonl", "bytes": len(raw), "sha256": M.digest(raw)}
            cache.packet(ref)
            cache.packet(ref)
            self.assertEqual(len(cache.files), 1)
            with self.assertRaisesRegex(M.Refusal, "file hash"):
                cache.read({**ref, "sha256": "bad"})
            with self.assertRaisesRegex(M.Refusal, "byte-count"):
                cache.read({**ref, "bytes": 1})
            with self.assertRaisesRegex(M.Refusal, "non-relative"):
                cache.read({"path": "../packet.jsonl", "sha256": "bad"})
            (root / "duplicates.jsonl").write_bytes(raw * 2)
            with self.assertRaisesRegex(M.Refusal, "duplicate packet key"):
                cache.packet({"path": "duplicates.jsonl", "sha256": M.digest(raw * 2)})

    def projection_fixture(self):
        contacts = [{"ordinal": i + 1, "midi": 45 + i, "string_low_to_high": 1,
                     "fret": 5 + i, "finger": i + 1, "source_line": 20,
                     "source_column_1based": i + 3, "same_column_contact_count": 1,
                     "technique_symbols": "", "onset_q": [i, 4], "duration_q": [1, 4]} for i in range(2)]
        variants = [{"start_stroke": start, "contact_ordinals": [1, 2],
                     "strokes": [start, "U" if start == "D" else "D"], "end_q": [1, 2]} for start in ("D", "U")]
        return {"implementation": {"kind": "ordered_contact_transcription", "ordered_contacts": contacts,
                "relative_variants": variants, "ordered_rest_locations": []},
                "timing_authority": {"end_q": [1, 2], "selected_projection": "straight_sixteenth",
                "fixed_bpm": None, "unselected_options": ["triplet", "quintuplet"]}}

    def test_selected_projection_keeps_full_scope_boundary(self):
        profile = M.contact_projection_profile(self.projection_fixture())
        self.assertTrue(profile["stored_data_projection_eligible"])
        self.assertTrue(profile["other_source_obligations_present"])
        self.assertFalse(profile["full_source_exercise_completion_claimed"])
        self.assertFalse(profile["native_music_validate_run"])

    def test_unknown_midi_stays_deferred(self):
        obj = self.projection_fixture()
        obj["implementation"]["ordered_contacts"][0]["midi"] = None
        self.assertFalse(M.contact_projection_profile(obj)["stored_data_projection_eligible"])

    def test_wrong_variant_parity_stays_deferred(self):
        obj = self.projection_fixture()
        obj["implementation"]["relative_variants"][0]["strokes"] = ["D", "D"]
        self.assertFalse(M.contact_projection_profile(obj)["stored_data_projection_eligible"])

    def test_variant_end_disagreement_stays_deferred(self):
        obj = self.projection_fixture()
        obj["implementation"]["relative_variants"][0]["end_q"] = 1
        self.assertFalse(M.contact_projection_profile(obj)["stored_data_projection_eligible"])

    def test_metric_gap_stays_deferred(self):
        obj = self.projection_fixture()
        obj["implementation"]["ordered_contacts"][1]["onset_q"] = [2, 4]
        self.assertFalse(M.contact_projection_profile(obj)["stored_data_projection_eligible"])

    def test_rest_semantics_stay_separate(self):
        obj = self.projection_fixture()
        obj["implementation"]["ordered_rest_locations"] = [{"unknown_duration": True}]
        self.assertFalse(M.contact_projection_profile(obj)["stored_data_projection_eligible"])


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(InventoryGuards)
    capture = io.StringIO()
    result = unittest.TextTestRunner(stream=capture, verbosity=1).run(suite)
    report = {"result": "PASS" if result.wasSuccessful() else "FAIL", "tests": result.testsRun,
              "failures": len(result.failures) + len(result.errors), "seconds": round(time.perf_counter() - started, 6),
              "scope": "Inventory file/identity/prestate negative controls; no model/source/native QA",
              "details": capture.getvalue()}
    ref = M.write_json(OUT / "guard-tests.json", report)
    print(json.dumps({**report, "report_ref": ref}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
