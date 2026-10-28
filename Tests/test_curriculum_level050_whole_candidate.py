"""Focused fidelity and refusal checks for the detached whole Level 50 candidate."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest

from Tools import curriculum_level050_whole_candidate as level


class WholeLevel50Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = level.build_candidate()

    def test_pinned_identity_and_non_admission(self) -> None:
        c = self.candidate
        self.assertEqual(c['wbs'], '2.3.1.2.1')
        self.assertEqual(c['source_map_row']['level'], 50)
        self.assertEqual(c['source_map_row']['review'], 'Pending')
        self.assertEqual(c['source_map_row']['conversion_status'], 'not_converted')
        self.assertFalse(c['source_map_row']['stable_ids_assigned'])
        self.assertFalse(c['admitted'])
        self.assertEqual(c['status'], 'non_admitted')
        for key in ('canonical_id', 'exercise_id', 'onset_q', 'duration_q', 'fixed_bpm', 'audible_voicing_events', 'bass_note_midi_for_H4', 'optional_repeat_attack_count'):
            self.assertIsNone(c[key], key)
        self.assertEqual(len(c['guidance']['txt_full_lines']), 439)
        self.assertEqual(len(c['guidance']['pdf_full_extracted_pages']), 20)
        self.assertEqual([c['module_sections'][k]['pdf_pages'] for k in 'ABCDEFGHIJ'], [[3], [4, 5], [6], [7], [8, 9], [10, 11], [12, 13], [14], [15, 16], [17, 18]])

    def test_eight_voicings_and_two_transition_fingerings(self) -> None:
        chords = self.candidate['chord_reference']
        self.assertEqual(list(chords['standard']), ['Em', 'E', 'Am', 'A', 'Dm', 'D', 'C', 'G'])
        self.assertEqual(chords['standard']['G']['frets_low_to_high'], ['3', '2', '0', '0', '0', '3'])
        self.assertEqual(chords['standard']['Dm']['attack_zone'], 'D string through high e')
        self.assertEqual(chords['standard']['E']['spelling'], ['E', 'G#', 'B'])
        self.assertEqual(chords['alternate']['Em-alt']['fingers_low_to_high'], ['O', '1', '2', 'O', 'O', 'O'])
        self.assertEqual(chords['alternate']['E-alt']['fingers_low_to_high'], ['O', '3', '2', '1', 'O', 'O'])

    def test_all_modules_and_workload(self) -> None:
        c = self.candidate
        self.assertEqual({k: len(v) for k, v in c['modules'].items()}, level.ITEM_COUNTS)
        self.assertEqual(c['silent_landings'], 80)
        self.assertEqual(c['notated_attacks_by_module'], {k: level.COUNTS[k] for k in 'BCDEFGHIJ'})
        self.assertEqual(c['notated_attack_total'], 768)
        self.assertEqual([x['transition'] for x in c['modules']['A']], ['E-Em', 'D-Dm', 'C-Am', 'A-Am', 'G-Em-alt', 'Em-alt-C', 'A-D', 'E-A', 'D-G', 'G-C'])
        self.assertEqual([x['title'] for x in c['modules']['B']], ['E <-> Em', 'D <-> Dm', 'C <-> Am', 'A <-> Am', 'G <-> Em-alt', 'Em-alt <-> C', 'A <-> D', 'G <-> C'])
        self.assertEqual([x['title'] for x in c['modules']['C']], ['E <-> A', 'D <-> G', 'G <-> C', 'Em-alt <-> C', 'E-alt <-> C', 'Am <-> D'])
        self.assertEqual([x['title'] for x in c['modules']['D']], [f'{k} release cell' for k in ('Em', 'E', 'Am', 'A', 'Dm', 'D', 'C', 'G')])
        self.assertTrue(all(x['attack_symbols'] == ['D', 'D', 'D', 'x'] * 2 and x['hand_states'] == ['P', 'P', 'P', 'R'] * 2 for x in c['modules']['D']))
        self.assertTrue(all(x['pitched_attacks'] == 6 and x['muted_attacks'] == 2 for x in c['modules']['D']))
        self.assertTrue(all(x['anticipated_positions_one_based'] == [5, 10] and len(x['chord_symbols']) == 10 for x in c['modules']['E']))
        self.assertTrue(all(x['attack_symbols'] == ['D', 'U'] * 8 for x in c['modules']['F']))
        self.assertTrue(all(x['chord_symbols'] == x['chord_symbols'][:4] * 4 for x in c['modules']['G']))
        self.assertEqual([x['attack_symbols_per_bar'] for x in c['modules']['H']], [['D'] * 4, ['D'] * 4, ['D', 'x', 'D', 'x'], ['B', 'D', 'B', 'D']])
        self.assertEqual([x['bar_chords'] for x in c['modules']['I']], [['G', 'D', 'Em', 'C', 'G', 'D', 'C', 'D'], ['A', 'D', 'E', 'A', 'D', 'A', 'E', 'E'], ['Em', 'C', 'G', 'D', 'Em', 'G', 'D', 'C'], ['Am', 'C', 'G', 'Em', 'Am', 'Dm', 'E', 'Am']])
        self.assertEqual([len(x['systems']) for x in c['modules']['J']], [4, 4])
        self.assertEqual([len(x['bar_chords']) for x in c['modules']['J']], [16, 16])

    def test_source_specific_details_and_renderable_pdf_text(self) -> None:
        c = self.candidate
        self.assertIn('Em', c['modules']['B'][4]['chord_symbols'])
        self.assertNotIn('Em-alt', c['modules']['B'][4]['chord_symbols'])
        self.assertEqual(c['modules']['C'][4]['title'], 'E-alt <-> C')
        self.assertIn('Pass 2: let the anticipated chord ring through beat 1', c['modules']['E'][0]['pass_2_raw'])
        self.assertIn('Pass 1 re-strums the new chord on beat 1.', c['modules']['E'][0]['pdf_pass_1_and_2_guidance'])
        self.assertIn('Pass 3 anticipate bars 5 and 8', c['modules']['I'][0]['passes_raw'])
        self.assertIn('bass/chord alternation', c['modules']['J'][0]['performance_alternatives_raw'])
        self.assertIn('G#', c['modules']['J'][1]['performance_alternatives_raw'])
        differences = {x['kind']: x for x in c['source_differences']}
        self.assertIn('Pass 1 re-strums', differences['PDF_only_E_pass_1_confirmation']['pdf_text'])
        self.assertIn('Quarter-note clean/min', differences['PDF_only_clean_transition_tests']['pdf_text'])
        self.assertIn('Weak finger / bass / bar', differences['PDF_only_completion_audit_and_log']['pdf_text'])
        self.assertIn('movable major and minor barre chords', ' '.join(differences['PDF_expanded_next_level_guidance']['pdf_text']))
        self.assertEqual(c['guidance']['pdf_full_extracted_pages'][18][-1], 'Page 19 of 20')

    def test_deterministic_encoding_and_output_boundary(self) -> None:
        first, second = level.encode(level.build_candidate()), level.encode(level.build_candidate())
        self.assertEqual(first, second)
        self.assertEqual(hashlib.sha256(first).hexdigest(), hashlib.sha256(second).hexdigest())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(level.output_path(root, str(level.BUILD / 'candidate.json')), root.resolve() / level.BUILD / 'candidate.json')
            for name in ('Content/candidate.json', '../candidate.json', str(root / level.BUILD / 'candidate.json')):
                with self.subTest(name=name), self.assertRaises(level.SourceError):
                    level.output_path(root, name)
            target = root / level.BUILD / 'existing.json'
            target.parent.mkdir(parents=True)
            target.write_text('{}')
            with self.assertRaises(level.SourceError):
                level.output_path(root, str(level.BUILD / 'existing.json'))

    def test_pinned_txt_pdf_and_map_mutations_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for spec in (level.TXT, level.PDF, level.MAP):
                target = root / spec[0]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(level.ROOT / spec[0], target)
            self.assertEqual(level.build_candidate(root)['notated_attack_total'], 768)
            for spec in (level.TXT, level.PDF, level.MAP):
                target = root / spec[0]
                original = target.read_bytes()
                target.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
                with self.subTest(path=spec[0]), self.assertRaisesRegex(level.SourceError, 'pin drift'):
                    level.build_candidate(root)
                target.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
