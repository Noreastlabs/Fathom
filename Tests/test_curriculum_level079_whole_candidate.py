"""Focused source, form, music and output checks for whole Level 79."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import shutil
import tempfile
import unittest

from Tools import curriculum_level079_whole_candidate as level


class WholeLevel79Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = level.build_candidate()

    def test_source_identity_and_nonadmission(self) -> None:
        c = self.candidate
        self.assertEqual((c['wbs'], c['status']), ('2.3.1.3.1', 'non_admitted'))
        self.assertEqual(c['source_map_row']['level'], 79)
        self.assertEqual(c['source_map_row']['conversion_status'], 'not_converted')
        self.assertFalse(c['source_map_row']['runtime_eligible'])
        self.assertFalse(c['admitted'])
        for key in ('canonical_id', 'exercise_id', 'onset_q', 'duration_q', 'fixed_bpm',
                    'executable_events', 'sounding_midi_events', 'performed_event_count', 'rubric_outcome'):
            self.assertIsNone(c[key], key)
        self.assertEqual(len(c['guidance']['txt_full_lines']), 220)
        self.assertEqual(len(c['guidance']['pdf_full_extracted_pages']), 20)
        self.assertEqual(tuple(c['source_sections']), level.KEYS)

    def test_master_form_and_section_study_parity(self) -> None:
        c = self.candidate
        form = c['master_form']
        self.assertEqual([s['section'] for s in form], ['INTRO', 'VERSE A', 'PRE', 'CHORUS', 'VERSE B', 'BRIDGE', 'FINALE'])
        self.assertEqual([(s['start_bar'], s['end_bar']) for s in form], [(1, 4), (5, 12), (13, 16), (17, 24), (25, 32), (33, 40), (41, 48)])
        self.assertEqual(sum(len(s['chords']) for s in form), 48)
        self.assertEqual(c['master_chords'], [chord for section in form for chord in section['chords']])
        studies = c['modules']['G']['section_studies']
        self.assertEqual(len(studies), 6)
        self.assertEqual([chord for study in studies for chord in study['chords']], c['master_chords'])
        self.assertEqual(sum(s['end_bar'] - s['start_bar'] + 1 for s in studies), 48)
        self.assertEqual(c['modules']['H']['declared_bars'], 48)

    def test_modules_and_musical_constraints(self) -> None:
        m = self.candidate['modules']
        self.assertEqual((len(m['A']['dynamic_arc']), len(m['A']['pdf_register_texture_cells'])), (8, 8))
        self.assertEqual((len(m['B']['targets']), len(m['B']['pivot_dominant_chains'])), (24, 6))
        self.assertEqual((len(m['C']['offset_cells']), len(m['C']['section_devices']), len(m['C']['pdf_section_studies'])), (8, 6, 6))
        self.assertEqual((len(m['D']['cue_response_matrix']), len(m['D']['cue_to_role_cells'])), (12, 8))
        self.assertEqual((len(m['E']['role_switch_circuits']), len(m['E']['density_register_studies'])), (8, 8))
        self.assertEqual((len(m['F']['recovery_cards']), len(m['F']['randomized_scenarios'])), (12, 8))
        self.assertEqual((len(m['G']['section_studies']), len(m['H']['passes']), len(m['H']['required_event_clauses'])), (6, 5, 9))
        self.assertEqual(m['C']['motif_notes'], ['C', 'E', 'G', 'B', 'A', 'G', 'E', 'D'])
        self.assertTrue(all((level.PC[re.match(r'[A-G](?:#|b)?', t['chord']).group()] + level.ROLE[t['role']]) % 12 == level.PC[t['target']] for t in m['B']['targets']))
        for chain in m['B']['pivot_dominant_chains']:
            self.assertEqual(len(chain['chords']), 3)
            for voice in chain['voices']:
                self.assertEqual(len(voice), 3)
                self.assertTrue(all(level.PC[note] in level.chord_pcs(chord) for note, chord in zip(voice, chain['chords'])))
        self.assertTrue(all(len(c['chords']) == len(c['roles']) == 4 for c in m['E']['role_switch_circuits']))
        self.assertEqual(m['F']['randomized_scenarios'][0]['setting'], 'Verse bar 7: wrong chord')

    def test_workload_ambiguity_and_scoring(self) -> None:
        c = self.candidate
        self.assertEqual(c['declared_workload_by_module'], {'A': 128, 'B': 144, 'C': 128, 'D': 96, 'E': 160, 'F': 96, 'G': 256, 'H': 192})
        self.assertEqual((sum(c['declared_workload_by_module'].values()), c['declared_workload_total']), (1200, 1200))
        self.assertEqual(c['modules']['G']['pdf_page_event_declarations'], [64, 64, 64])
        self.assertEqual(c['modules']['G']['pdf_page_event_sum'], 192)
        self.assertEqual(len(c['source_ambiguities']), 1)
        self.assertEqual((c['source_ambiguities'][0]['status'], c['source_ambiguities'][0]['difference']), ('pending_curriculum_review', 64))
        s = c['scoring']
        self.assertEqual((len(s['rubric']), s['maximum_score'], s['required_score'], s['separate_days']), (9, 18, 16, 2))
        self.assertTrue(all(set(r['scores']) == {'0', '1', '2'} for r in s['rubric']))
        self.assertEqual(s['hard_zero_categories'], ['pulse', 'form', 'cue response', 'recovery'])

    def test_determinism_and_output_confinement(self) -> None:
        first, second = level.encode(level.build_candidate()), level.encode(level.build_candidate())
        self.assertEqual(first, second)
        self.assertEqual(hashlib.sha256(first).hexdigest(), hashlib.sha256(second).hexdigest())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = str(level.BUILD / 'candidate.json')
            self.assertEqual(level.output_path(root, good), root.resolve() / good)
            for bad in ('Content/candidate.json', '../candidate.json', str(root / good)):
                with self.subTest(output=bad), self.assertRaises(level.SourceError):
                    level.output_path(root, bad)
            target = root / good
            target.parent.mkdir(parents=True)
            target.write_text('{}')
            with self.assertRaisesRegex(level.SourceError, 'overwrite'):
                level.output_path(root, good)

    def test_pinned_txt_pdf_and_map_mutations_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for spec in (level.TXT, level.PDF, level.MAP):
                target = root / spec[0]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(level.ROOT / spec[0], target)
            self.assertEqual(level.build_candidate(root)['declared_workload_total'], 1200)
            for spec in (level.TXT, level.PDF, level.MAP):
                target = root / spec[0]
                original = target.read_bytes()
                target.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
                with self.subTest(source=spec[0]), self.assertRaisesRegex(level.SourceError, 'pin drift'):
                    level.build_candidate(root)
                target.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
