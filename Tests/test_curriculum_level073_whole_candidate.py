"""Focused source, musical, worksheet and output checks for whole Level 73."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest

from Tools import curriculum_level073_whole_candidate as level


class WholeLevel73Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = level.build_candidate()

    def test_source_identity_and_nonadmission(self) -> None:
        c = self.candidate
        self.assertEqual(c['wbs'], '2.3.1.3.1')
        self.assertEqual(c['source_map_row']['level'], 73)
        self.assertEqual(c['source_map_row']['conversion_status'], 'not_converted')
        self.assertFalse(c['source_map_row']['admitted'])
        self.assertFalse(c['admitted'])
        for key in ('canonical_id', 'exercise_id', 'onset_q', 'duration_q', 'fixed_bpm', 'executable_events', 'sounding_midi_events'):
            self.assertIsNone(c[key], key)
        self.assertEqual(len(c['guidance']['txt_full_lines']), 668)
        self.assertEqual(len(c['guidance']['pdf_full_extracted_pages']), 20)
        self.assertEqual(tuple(c['source_sections']), level.KEYS)

    def test_all_modules_and_printed_workload(self) -> None:
        c = self.candidate
        self.assertEqual({key: len(c['modules'][key]) for key in level.CELL_COUNTS}, level.CELL_COUNTS)
        self.assertEqual(sum(map(len, c['modules'].values())), 55)
        self.assertEqual(len(c['guide_tone_worksheets']), 6)
        self.assertEqual(c['printed_tones_by_module'], level.EXPECTED)
        self.assertEqual(c['printed_sounding_tones'], 652)
        self.assertEqual(sum(cell['printed_tones'] for group in c['modules'].values() for cell in group), 604)
        self.assertEqual(sum(sheet['printed_tones'] for sheet in c['guide_tone_worksheets']), 48)
        self.assertEqual([len(c['modules'][key]) for key in 'GHI'], [8, 4, 12])

    def test_note_tab_pdf_and_chord_relationships(self) -> None:
        for letter, group in self.candidate['modules'].items():
            for cell in group:
                with self.subTest(module=letter, source=cell['txt_ref']):
                    self.assertEqual(len(cell['events']), cell['printed_tones'])
                    self.assertEqual([e['note'] for e in cell['events']], cell['note_names'])
                    self.assertTrue(cell['pdf_ref'].startswith('L73-PDF-p'))
                    self.assertEqual(len({e['source_column'] for e in cell['events']}), cell['printed_tones'])
                    for e in cell['events']:
                        self.assertEqual((level.OPEN[e['string']] + e['fret']) % 12, level.PC[e['note']])
        for letter in ('B', 'F', 'G', 'H'):
            self.assertTrue(all(len(cell['chords']) == cell['printed_tones'] // 4 for cell in self.candidate['modules'][letter]))
        self.assertEqual(self.candidate['modules']['G'][1]['absolute_bars'], [5, 6, 7, 8])
        self.assertEqual(self.candidate['modules']['H'][-1]['absolute_bars'], [13, 14, 15, 16])
        self.assertEqual(self.candidate['modules']['D'][0]['bridge_note'], 'E')
        self.assertEqual(self.candidate['modules']['E'][0]['degree_formula'], ['1', '3', '5', '7', '5', '3', '2', '1'])
        self.assertEqual(self.candidate['modules']['E'][3]['degree_formula'], ['1', 'b3', '5', 'b7', '5', 'b3', '2', '1'])
        altered = [list(page) for page in self.candidate['guidance']['pdf_full_extracted_pages']]
        at = next(i for i, row in enumerate(altered[2]) if row.startswith('  D|'))
        altered[2][at] = altered[2][at].replace('2', '3', 1)
        with self.assertRaisesRegex(level.SourceError, 'PDF/TXT notation rows'):
            level.pdf_note_correspondence(self.candidate['modules'], altered)

    def test_two_voice_worksheets_and_source_conflicts(self) -> None:
        c = self.candidate
        self.assertEqual([sheet['route'] for sheet in c['guide_tone_worksheets']], ['C -> G', 'C -> D', 'C -> F', 'Am -> C', 'Am -> Em', 'G -> Em'])
        self.assertEqual([sheet['printed_tones'] for sheet in c['guide_tone_worksheets']], [8] * 6)
        for sheet in c['guide_tone_worksheets']:
            self.assertEqual(len(sheet['chords']), 4)
            for voice in sheet['voices']:
                self.assertEqual(len(voice['events']), 4)
                for e in voice['events']:
                    self.assertEqual((level.OPEN[e['string']] + e['fret']) % 12, level.PC[e['note']])
                    self.assertIn(e['pitch_class'], level.chord_pcs(e['chord']))
        self.assertEqual(len(c['source_ambiguities']), 3)
        self.assertEqual([a['route'] for a in c['source_ambiguities']], ['Am7 -> C#m7', 'Am7 -> Fm7', 'Em7 -> G#m7'])
        self.assertTrue(all(a['status'] == 'pending_curriculum_review' for a in c['source_ambiguities']))
        self.assertEqual([cell['barline_repeats_note'] for cell in c['modules']['A']], [True] * 5 + [False] * 3)
        self.assertEqual(len(c['modules']['I']), 12)
        self.assertEqual(c['modules']['I'][2]['target_note'], 'D')
        self.assertIn('Three-pass improvisation ladder', c['guidance']['pdf_full_extracted_pages'][18])

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
            self.assertEqual(level.build_candidate(root)['printed_sounding_tones'], 652)
            for spec in (level.TXT, level.PDF, level.MAP):
                target = root / spec[0]
                original = target.read_bytes()
                target.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
                with self.subTest(source=spec[0]), self.assertRaisesRegex(level.SourceError, 'pin drift'):
                    level.build_candidate(root)
                target.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
