"""Focused source, pitch, count and boundary checks for whole Level 61."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest

from Tools import curriculum_level061_whole_candidate as level


class WholeLevel61Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = level.build_candidate()

    def test_source_identity_and_detached_status(self) -> None:
        c = self.candidate
        self.assertEqual(c['wbs'], '2.3.1.2.1')
        self.assertEqual(c['source_map_row']['level'], 61)
        self.assertEqual(c['source_map_row']['conversion_status'], 'not_converted')
        self.assertFalse(c['source_map_row']['admitted'])
        self.assertFalse(c['admitted'])
        for key in ('canonical_id', 'exercise_id', 'onset_q', 'duration_q', 'fixed_bpm', 'executable_events', 'sounding_midi_events'):
            self.assertIsNone(c[key], key)
        self.assertEqual(len(c['guidance']['txt_full_lines']), 1295)
        self.assertEqual(len(c['guidance']['pdf_full_extracted_pages']), 20)
        self.assertEqual(list(c['source_sections']), list(level.SECTION_KEYS))

    def test_all_modules_and_exact_written_workload(self) -> None:
        c = self.candidate
        m = c['modules']
        self.assertEqual({key: len(m[key]) for key in level.SECTION_KEYS}, level.CELL_COUNTS)
        self.assertEqual(len(m['H_recovery_cards']), 12)
        self.assertEqual(sum(len(m[key]) for key in level.SECTION_KEYS), 105)
        self.assertEqual(c['printed_tones_by_module'], {'A': 64, 'B': 120, 'C': 64, 'D': 48, 'E': 72, 'F': 72, 'G': 80, 'H': 72, 'I': 96, 'J': 128})
        self.assertEqual(c['printed_sounding_tones'], 816)
        self.assertEqual(sum(cell['printed_tones'] for key in level.SECTION_KEYS for cell in m[key]), 792)
        self.assertEqual(sum(card['printed_tones'] for card in m['H_recovery_cards']), 24)
        self.assertEqual([cell['printed_tones'] for cell in m['B_chromatic']], [5] * 12)
        self.assertEqual([cell['printed_tones'] for cell in m['J_minor']], [16] * 4)

    def test_note_tab_and_target_semantics(self) -> None:
        m = self.candidate['modules']
        for key in level.SECTION_KEYS:
            for cell in m[key]:
                with self.subTest(section=key, ref=cell['txt_ref']):
                    self.assertEqual(len(cell['events']), cell['printed_tones'])
                    self.assertEqual([event['note'] for event in cell['events']], cell['note_names'])
                    self.assertTrue(all((level.OPEN[event['string']] + event['fret']) % 12 == level.PC[event['note']] for event in cell['events']))
                    self.assertEqual(len({event['source_column'] for event in cell['events']}), cell['printed_tones'])
                    self.assertEqual(len(cell['tab_rows']), 6)
        self.assertEqual(m['A'][0]['chord'], 'Cmaj7')
        self.assertEqual(m['A'][0]['final_target_role'], 'R')
        self.assertEqual(m['B_chromatic'][0]['note_names'], ['E', 'Eb', 'E', 'F', 'E'])
        self.assertEqual(m['B_diatonic'][0]['note_names'], ['E', 'D', 'E', 'F', 'E'])
        self.assertEqual(m['C'][0]['enclosure_direction'], 'above-below')
        self.assertEqual(m['D'][0]['resolution_target_role'], '3')

    def test_recovery_and_pdf_representation_differences(self) -> None:
        c = self.candidate
        m = c['modules']
        self.assertEqual(m['H_recovery_cards'][0]['raw'], 'Dm7: E -> F | 9 -> b3')
        self.assertEqual(m['H_recovery_cards'][-1]['raw'], 'Am7: F# -> G | 13 -> b7')
        self.assertEqual([m['H'][0]['note_names'], m['H'][1]['note_names']], [m['H'][0]['note_names']] * 2)
        self.assertEqual(c['source_ambiguities'][0]['kind'], 'H2_rhythmic_displacement_without_printed_timing_difference')
        self.assertEqual(m['I_major'][0]['note_names'], m['J_major'][0]['note_names'])
        self.assertEqual(m['I_minor'][0]['note_names'], m['J_minor'][0]['note_names'])
        self.assertEqual(m['J_minor'][-1]['headers_raw'][0], 'D: Em7b5 | A7 | Dm7 | Dm7')
        diffs = {d['kind']: d for d in c['source_differences']}
        self.assertIn('The complete tablature appears in the text workbook.', ' '.join(diffs['J_PDF_table_omits_TAB_retained_in_TXT']['pdf_text']))
        self.assertIn('Target hierarchy', diffs['PDF_only_target_hierarchy_and_delayed_grid']['pdf_text'])
        self.assertIn('Practice log', diffs['PDF_only_practice_log']['pdf_text'])
        self.assertFalse(any(line.startswith('Nte|') for line in c['guidance']['pdf_full_extracted_pages'][18]))

    def test_determinism_and_build_output_confinement(self) -> None:
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
            self.assertEqual(level.build_candidate(root)['printed_sounding_tones'], 816)
            for spec in (level.TXT, level.PDF, level.MAP):
                target = root / spec[0]
                original = target.read_bytes()
                target.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
                with self.subTest(source=spec[0]), self.assertRaisesRegex(level.SourceError, 'pin drift'):
                    level.build_candidate(root)
                target.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
