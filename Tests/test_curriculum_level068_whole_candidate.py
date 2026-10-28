"""Focused source, musical, workload and output-boundary checks for whole Level 68."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest

from Tools import curriculum_level068_whole_candidate as level


class WholeLevel68Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = level.build_candidate()

    def test_source_identity_and_detached_status(self) -> None:
        c = self.candidate
        self.assertEqual(c['wbs'], '2.3.1.2.1')
        self.assertEqual(c['source_map_row']['level'], 68)
        self.assertEqual(c['source_map_row']['conversion_status'], 'not_converted')
        self.assertFalse(c['source_map_row']['admitted'])
        self.assertFalse(c['admitted'])
        for key in ('canonical_id', 'exercise_id', 'onset_q', 'duration_q', 'fixed_bpm', 'executable_events', 'sounding_midi_events'):
            self.assertIsNone(c[key], key)
        self.assertEqual(len(c['guidance']['txt_full_lines']), 871)
        self.assertEqual(len(c['guidance']['pdf_full_extracted_pages']), 20)
        self.assertEqual(tuple(c['source_sections']), level.KEYS)

    def test_all_modules_and_printed_workload(self) -> None:
        c = self.candidate
        self.assertEqual({key: len(c['modules'][key]) for key in level.KEYS[:-1]}, level.CELL_COUNTS)
        self.assertEqual(sum(map(len, c['modules'].values())), 67)
        self.assertEqual(len(c['recovery_cards']), 12)
        self.assertEqual(c['printed_tones_by_module'], level.EXPECTED)
        self.assertEqual(c['printed_sounding_tones'], 630)
        self.assertEqual(sum(cell['printed_tones'] for group in c['modules'].values() for cell in group), 606)
        self.assertEqual(sum(card['printed_tones'] for card in c['recovery_cards']), 24)
        self.assertEqual([cell['printed_tones'] for cell in c['modules']['D']], [8, 8, 8, 8, 32])
        self.assertEqual([cell['printed_tones'] for cell in c['modules']['J']], [4] * 16)

    def test_note_tab_pitch_degrees_and_pdf_counterparts(self) -> None:
        for letter, group in self.candidate['modules'].items():
            for cell in group:
                with self.subTest(module=letter, source=cell['txt_ref']):
                    self.assertEqual(len(cell['events']), cell['printed_tones'])
                    self.assertEqual([e['note'] for e in cell['events']], cell['note_names'])
                    self.assertEqual(len(cell['tab_rows']), 6)
                    self.assertTrue(cell['pdf_ref'].startswith('L68-PDF-p'))
                    self.assertEqual(len({e['source_column'] for e in cell['events']}), cell['printed_tones'])
                    for e in cell['events']:
                        self.assertEqual((level.OPEN[e['string']] + e['fret']) % 12, level.PC[e['note']])
                        self.assertEqual(e['degree'], level.DEGREE[e['note']])
        with self.assertRaisesRegex(level.SourceError, 'PDF/TXT notes'):
            altered = [list(page) for page in self.candidate['guidance']['pdf_full_extracted_pages']]
            at = next(i for i, row in enumerate(altered[14]) if row.startswith('Nte|'))
            altered[14][at] = altered[14][at].replace('Nte|A', 'Nte|B', 1)
            level.pdf_correspondence(self.candidate['modules'], altered)

    def test_harmony_and_source_specific_directions(self) -> None:
        c, m = self.candidate, self.candidate['modules']
        self.assertEqual(m['A'][0]['note_names'][:8], ['E', 'F', 'G#', 'A', 'B', 'C', 'D', 'E'])
        self.assertEqual(m['B'][0]['note_names'], ['F', 'E', 'G', 'G#', 'A', 'G#', 'C', 'B'])
        self.assertEqual(m['C'][0]['second_pass_event_ordinals'], [2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(m['D'][4]['note_names'][16:], list(reversed(m['D'][4]['note_names'][:16])))
        self.assertEqual(m['E'][0]['note_names'][:4], m['D'][0]['note_names'][:4])
        self.assertEqual([e['source_bar_ordinal'] for e in m['G'][0]['events']], [n for n in range(1, 5) for _ in range(4)])
        self.assertEqual([e['source_bar_ordinal'] for e in m['H'][0]['events']], [n for n in range(1, 4) for _ in range(4)])
        self.assertEqual(m['J'][13]['note_names'], ['E', 'G', 'C', 'G#'])
        self.assertEqual(m['J'][13]['heading_raw'], 'BAR 14: E7#9b13 - P5')
        self.assertEqual(len([line for line in c['capstone_lines'] if line.startswith('PASS ')]), 3)
        self.assertEqual(len(c['capstone']['four_bar_groups_raw']), 4)
        self.assertEqual(len(c['capstone']['pass_constraints_raw']), 3)
        self.assertEqual({d['kind'] for d in c['source_differences']}, {'PDF_I_combines_call_answer_note_rows', 'PDF_K_adds_capstone_rubric_and_phrase_constraints', 'PDF_only_recovery_ear_tests_and_practice_log'})
        self.assertEqual(len(c['source_ambiguities']), 1)
        self.assertEqual(c['source_ambiguities'][0]['kind'], 'F1_PDF_final_E_instruction_conflicts_with_printed_final_B')
        self.assertEqual(c['source_ambiguities'][0]['status'], 'pending_curriculum_review')

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
            self.assertEqual(level.build_candidate(root)['printed_sounding_tones'], 630)
            for spec in (level.TXT, level.PDF, level.MAP):
                target = root / spec[0]
                original = target.read_bytes()
                target.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
                with self.subTest(source=spec[0]), self.assertRaisesRegex(level.SourceError, 'pin drift'):
                    level.build_candidate(root)
                target.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
