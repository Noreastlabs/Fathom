import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "reviewed_child_overlay", ROOT / "Tools/exercise-family-compiler/reviewed_child_overlay.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class StrictChildResolution(unittest.TestCase):
    def setUp(self):
        self.row = {"package_key": "existing", "existing_parent_id": "2.3.1.2.1",
                    "status": "Pending", "exercise": {"source_identity": "source",
                    "app_status": "missing"}, "proposal": {"status": "Pending",
                    "app_status": "missing"}}
        self.base = json.dumps(self.row).encode()
        self.op = {"selection": {"package_key": "existing", "source_identity": "source",
                   "existing_parent_id": "2.3.1.2.1",
                   "exercise_canonical_json_sha256": M.canonical_sha(self.row["exercise"]),
                   "candidate_canonical_json_sha256": M.canonical_sha(self.row),
                   "canonical_hash_encoding": "UTF-8 JSON sort_keys=true separators=(comma,colon) ensure_ascii=false"},
                   "assert_before": {"candidate_status": "Pending", "exercise_app_status": "missing",
                   "proposal_status": "Pending", "proposal_app_status": "missing"},
                   "current_overlay": {"status": "Accepted", "app_status": "installed",
                   "base_line": 1, "source_key": "existing", "acceptance_evidence": {"path": "bound-review"}}}

    def test_preserves_base_and_exact_transition(self):
        before = bytes(self.base)
        self.assertEqual(M.resolve(self.base, [])['status_counts'], {'Pending': 1})
        result = M.resolve(self.base, [self.op])
        self.assertEqual(result['status_counts'], {'Accepted': 1})
        self.assertEqual(result['parent_counts'], {'2.3.1.2.1': {'total': 1, 'Accepted': 1}})
        self.assertEqual(before, self.base)

    def test_refuses_conflicts_and_unbound_proposals(self):
        mutations = [
            lambda o: o['selection'].update(package_key='unknown'),
            lambda o: o['selection'].update(source_identity='wrong'),
            lambda o: o['selection'].update(existing_parent_id='wrong'),
            lambda o: o['selection'].update(exercise_canonical_json_sha256='wrong'),
            lambda o: o['selection'].update(candidate_canonical_json_sha256='wrong'),
            lambda o: o['selection'].update(canonical_hash_encoding='wrong'),
            lambda o: o['assert_before'].update(candidate_status='Accepted'),
            lambda o: o['current_overlay'].update(base_line=2),
            lambda o: o['current_overlay'].update(source_key='wrong'),
            lambda o: o['current_overlay'].update(acceptance_evidence={}),
            lambda o: o.update(proposed_overlay=o.pop('current_overlay')),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                operation = copy.deepcopy(self.op)
                mutate(operation)
                with self.assertRaises((ValueError, KeyError)):
                    M.resolve(self.base, [operation])
        with self.assertRaises(ValueError): M.resolve(self.base, [self.op, self.op])
        with self.assertRaises(ValueError): M.resolve(self.base + b'\n' + self.base, [])
        with self.assertRaises(ValueError): M.strict_json('{"a":1,"a":2}')
        with self.assertRaises(ValueError): M.strict_json('{"a":NaN}')


if __name__ == '__main__':
    unittest.main()
