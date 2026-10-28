"""Fidelity and refusal tests for detached whole Level 56 natural-minor source."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest

from Tools import curriculum_level056_whole_candidate as level


class WholeLevel56Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = level.build_candidate()

    def test_pinned_scope_and_non_admission(self) -> None:
        c = self.value
        self.assertEqual(c['wbs'], '2.3.1.2.1')
        self.assertEqual(c['source_map_row']['level'], 56)
        self.assertEqual(c['source_map_row']['conversion_status'], 'not_converted')
        self.assertFalse(c['source_map_row']['stable_ids_assigned'])
        self.assertFalse(c['admitted'])
        self.assertEqual(c['status'], 'non_admitted')
        for key in ('canonical_id', 'exercise_id', 'onset_q', 'duration_q', 'fixed_bpm', 'executable_events', 'unique_full_chord_voicings', 'optional_pass_attack_count'):
            self.assertIsNone(c[key], key)
        self.assertEqual(len(c['guidance']['txt_full_lines']), 590)
        self.assertEqual(len(c['guidance']['pdf_full_extracted_pages']), 20)
        self.assertEqual(list(c['module_sections']), list('ABCDEFGHIJK'))

    def test_theory_ladders_and_raised_dominants(self) -> None:
        c = self.value
        b = c['modules']['B']
        self.assertEqual([f['key'] for f in b], ['A', 'E', 'B', 'F#', 'C#', 'D'])
        self.assertEqual([f['raised_seventh'] for f in b], ['G#', 'D#', 'A#', 'E#', 'B#', 'C#'])
        self.assertEqual([len(f['triads']) for f in b], [7] * 6)
        self.assertEqual([f['triad_string_set'] for f in b], ['D-G-B', 'E-A-D', 'G-B-e', 'G-B-e', 'D-G-B', 'G-B-e'])
        self.assertEqual(b[4]['natural_scale'], ['C#', 'D#', 'E', 'F#', 'G#', 'A', 'B'])
        self.assertEqual(b[4]['triads'][4]['spelling'], ['G#', 'B', 'D#'])
        self.assertEqual(b[4]['strong_V_raw'], 'Strong V: G# = G#-B#-D#')
        self.assertEqual(b[4]['leading_vii_diminished_raw'], 'Leading-tone vii°: B#dim = B#-D#-F#')
        self.assertTrue(all(f['printed_attacks'] == 28 for f in b))

    def test_progressions_voice_leading_and_separate_workloads(self) -> None:
        c = self.value
        m = c['modules']
        self.assertEqual(m['A']['practice_keys_circle_order'], ['D', 'A', 'E', 'B', 'F#', 'C#'])
        self.assertEqual(len(m['A']['silent_spelling_items']), 42)
        self.assertEqual([x['practice_key'] for x in m['A']['silent_spelling_items'][::7]], ['D', 'A', 'E', 'B', 'F#', 'C#'])
        self.assertEqual(m['A']['silent_spelling_items'][-1]['natural_triad_spelling'], ['B', 'D#', 'F#'])
        self.assertEqual(c['silent_spelling_prompts'], 42)
        self.assertEqual(c['written_prompts'], 24)
        self.assertEqual(c['sounded_attacks_by_module'], {'B': 168, 'C': 96, 'D': 96, 'E': 96, 'F': 96, 'G': 96, 'H': 96, 'I': 96, 'K': 96})
        self.assertEqual(c['sounded_attack_total'], 936)
        for key in 'CDEFGH':
            self.assertEqual(len(m[key]), 6)
            self.assertEqual([x['key'] for x in m[key]], ['D', 'A', 'E', 'B', 'F#', 'C#'])
            self.assertTrue(all(x['printed_attacks'] == 16 and len(x['voicing_alternatives_raw']) == 4 for x in m[key]))
        self.assertEqual(m['C'][0]['chord_symbols'], ['Dm', 'Gm', 'Am', 'Dm'])
        self.assertEqual(m['D'][0]['chord_symbols'], ['Dm', 'Gm', 'A', 'Dm'])
        self.assertEqual(m['H'][1]['roman_symbols'], ['ii°', 'V', 'i', 'i'])
        self.assertEqual(len(m['I']), 6)
        self.assertEqual(m['I'][4]['chord_symbols'], ['C#m', 'F#m', 'G#', 'C#m'])
        self.assertEqual(m['I'][4]['raised_seventh'], 'B#')
        self.assertEqual(m['K']['circle_order'], ['D', 'A', 'E', 'B', 'F#', 'C#'])
        self.assertEqual([cell['bars'] for cell in m['K']['cells']], [list(range(k, k + 4)) for k in (1, 5, 9, 13, 17, 21)])
        self.assertEqual(m['K']['printed_attacks'], 96)
        self.assertEqual(len(m['K']['passes_raw']), 3)

    def test_analysis_conflict_and_pdf_only_guidance(self) -> None:
        c = self.value
        j = c['modules']['J']
        self.assertEqual(len(j['analysis']), 12)
        self.assertEqual(len(j['transpose']), 12)
        self.assertEqual([v['analysis_number'] for v in c['source_conflicts']], [4, 5, 9, 10])
        self.assertTrue(all(v['progression_label'] == 'P/T' and v['analysis_label'] == 'P' and v['status'] == 'pending_curriculum_review' for v in c['source_conflicts']))
        self.assertEqual(j['analysis'][4]['answer_functions_raw'], ['T', 'P', 'P', 'D'])
        self.assertEqual(c['modules']['G'][3]['function_symbols'], ['T', 'P', 'P/T', 'D'])
        self.assertEqual(j['transpose'][11]['answer_chords'], ['Dm', 'Gm', 'A', 'Dm'])
        differences = {v['kind']: v for v in c['source_differences']}
        self.assertIn('Natural-v versus strong-V ear loop', differences['PDF_only_v_V_V7_ear_loop_and_advancement_rule']['pdf_text'])
        self.assertIn('Completion audit', differences['PDF_only_completion_audit_and_practice_log']['pdf_text'])
        self.assertIn('Practice log', differences['PDF_only_completion_audit_and_practice_log']['pdf_text'])

    def test_determinism_and_output_confinement(self) -> None:
        a, b = level.encode(level.build_candidate()), level.encode(level.build_candidate())
        self.assertEqual(a, b)
        self.assertEqual(hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid = str(level.BUILD / 'candidate.json')
            self.assertEqual(level.output_path(root, valid), root.resolve() / valid)
            for bad in ('Content/candidate.json', '../candidate.json', str(root / valid)):
                with self.subTest(path=bad), self.assertRaises(level.SourceError):
                    level.output_path(root, bad)
            target = root / valid
            target.parent.mkdir(parents=True)
            target.write_text('{}')
            with self.assertRaisesRegex(level.SourceError, 'overwrite'):
                level.output_path(root, valid)

    def test_source_pin_mutations_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for spec in (level.TXT, level.PDF, level.MAP):
                target = root / spec[0]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(level.ROOT / spec[0], target)
            self.assertEqual(level.build_candidate(root)['sounded_attack_total'], 936)
            for spec in (level.TXT, level.PDF, level.MAP):
                target = root / spec[0]
                original = target.read_bytes()
                target.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
                with self.subTest(source=spec[0]), self.assertRaisesRegex(level.SourceError, 'pin drift'):
                    level.build_candidate(root)
                target.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
