"""Focused whole-Level6 non-admitted draft and refusal checks."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from Tools import curriculum_level006_draft_materializer_candidate as draft


ROOT = Path(__file__).resolve().parents[1]


class Level6DraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index, cls.candidates, cls.lines = draft.load_inputs(ROOT)

    def build(self, index=None, candidates=None):
        return draft.materialize(index if index is not None else self.index,
                                 candidates if candidates is not None else self.candidates,
                                 self.lines)

    def test_all_records_events_groups_and_unresolved_fields_survive_exactly(self) -> None:
        result = self.build()
        self.assertEqual(result["counts"], draft.COUNTS)
        self.assertEqual(len(result["records"]), 216)
        self.assertEqual(sum(len(row["source_projection"]["events"]) for row in result["records"]), 6912)
        self.assertEqual(sum(len(row["source_projection"]["directional_groups"]) for row in result["records"]), 432)
        self.assertEqual(sum(len(group["cells"]) for row in result["records"]
                             for group in row["source_projection"]["directional_groups"]), 1728)
        self.assertFalse(result["admitted"] or result["runtime_eligible"] or result["canonical_schema_validated"])
        self.assertEqual(result["identity_assignment"], "unassigned")
        self.assertEqual(result["p06_index"]["sha256"], draft.INDEX[1])
        for ref, row in zip(self.index["records"], result["records"], strict=True):
            offset = int(ref["candidate_json_pointer"].removeprefix("/records/"))
            source = self.candidates[ref["set"]]["records"][offset]
            self.assertEqual(row["source_projection"], source)
            self.assertEqual(row["source_record_sha256"], ref["record_sha256"])
            self.assertEqual(hashlib.sha256(draft.integrity.canonical(source)).hexdigest(), ref["record_sha256"])
            self.assertEqual(row["source_locator"]["source_refs"], source["source_refs"])
            self.assertEqual(set(row["schema_slots"]), set(draft.UNRESOLVED))
            self.assertTrue(all(value is None for value in row["schema_slots"].values()))
            self.assertFalse(row["admitted"] or row["runtime_eligible"] or row["canonical_schema_validated"])
            for field in ("cell_beat_count", "duration_q", "meter", "note_per_click", "onset_q", "tempo_bpm"):
                self.assertIsNone(source["timing"][field])
            for event in source["events"]:
                for field in ("beat_index", "duration_q", "note_per_click", "onset_q"):
                    self.assertIsNone(event[field])

    def test_twin_render_is_byte_identical_and_no_canonical_id_emitted(self) -> None:
        first = draft.render(ROOT)
        second = draft.render(ROOT)
        self.assertEqual(first, second)
        self.assertEqual(first, draft.canonical(json.loads(first)))
        result = json.loads(first)
        self.assertNotIn("canonical_records", result)
        self.assertNotIn("id", result["records"][0]["source_projection"])
        self.assertEqual(result["schema"], "fathom-level006-schema-oriented-draft.1")

    def test_index_hash_ref_and_order_conflicts_refuse(self) -> None:
        changed = copy.deepcopy(self.index)
        changed["records"][0]["record_sha256"] = "0" * 64
        with self.assertRaisesRegex(draft.DraftError, "hash/ref/code conflict"):
            self.build(index=changed)
        changed = copy.deepcopy(self.index)
        changed["records"][1]["candidate_json_pointer"] = "/records/0"
        with self.assertRaisesRegex(draft.DraftError, "pointer/order conflict"):
            self.build(index=changed)
        changed = copy.deepcopy(self.index)
        changed["records"][0]["source_refs"][0] = "wrong"
        with self.assertRaisesRegex(draft.DraftError, "hash/ref/code conflict"):
            self.build(index=changed)

    def test_false_admission_and_invented_timing_refuse(self) -> None:
        changed = copy.deepcopy(self.index)
        changed["runtime_eligible"] = True
        with self.assertRaisesRegex(draft.DraftError, "false index admission"):
            self.build(index=changed)
        changed_candidates = copy.deepcopy(self.candidates)
        changed_candidates[1]["release_state"]["admitted"] = True
        with self.assertRaisesRegex(draft.integrity.IntegrityError, "false admission"):
            self.build(candidates=changed_candidates)
        changed_candidates = copy.deepcopy(self.candidates)
        changed_candidates[1]["records"][0]["timing"]["note_per_click"] = 1
        with self.assertRaisesRegex(draft.integrity.IntegrityError, "invented timing"):
            self.build(candidates=changed_candidates)
        changed_candidates = copy.deepcopy(self.candidates)
        changed_candidates[1]["records"][0]["events"][0]["onset_q"] = [0, 1]
        with self.assertRaisesRegex(draft.integrity.IntegrityError, "invented event timing"):
            self.build(candidates=changed_candidates)
        changed_candidates = copy.deepcopy(self.candidates)
        changed_candidates[1]["records"][0]["events"][0]["source_local_event_key"] = "wrong"
        with self.assertRaisesRegex(draft.integrity.IntegrityError, "event order/source keys"):
            self.build(candidates=changed_candidates)

    def test_input_pins_refuse_drift(self) -> None:
        self.assertEqual(draft.digest(draft.pinned(ROOT, draft.INDEX)), draft.INDEX[1])
        bad = (draft.INDEX[0], "0" * 64, draft.INDEX[2])
        with self.assertRaisesRegex(draft.DraftError, "pinned input drift"):
            draft.pinned(ROOT, bad)
        self.assertEqual(draft.digest(draft.pinned(ROOT, draft.ADAPTER)), draft.ADAPTER[1])

    def test_cli_refuses_output_outside_lane_and_existing_draft(self) -> None:
        build = ROOT / draft.BUILD_REL
        build.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=build) as temporary:
            existing = Path(temporary) / "existing.json"
            existing.write_bytes(b"sentinel")
            command = [sys.executable, "-m", "Tools.curriculum_level006_draft_materializer_candidate",
                       "--root", str(ROOT), "--output"]
            refused = subprocess.run(command + [str(existing)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(refused.returncode, 2)
            self.assertIn("new file inside", refused.stderr)
            self.assertEqual(existing.read_bytes(), b"sentinel")
            refused = subprocess.run(command + [str(ROOT / "Results" / "forbidden.json")],
                                     cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(refused.returncode, 2)
            self.assertIn("P11 Level6 Build lane", refused.stderr)


if __name__ == "__main__":
    unittest.main()
