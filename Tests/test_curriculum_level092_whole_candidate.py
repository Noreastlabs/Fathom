"""Focused source, table, musical-relation and output checks for whole Level 92."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest

from Tools import curriculum_level092_whole_candidate as level


class WholeLevel92Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = level.build_candidate()

    def test_source_identity_and_nonadmission(self) -> None:
        c = self.candidate
        self.assertEqual((c['wbs'], c['level'], c['section']), ('2.3.1.3.1', 92, 'XIII'))
        self.assertEqual(c['source_map_row']['conversion_status'], 'not_converted')
        self.assertFalse(c['source_map_row']['runtime_eligible'])
        self.assertFalse(c['admitted'])
        for key in ('canonical_id', 'exercise_id', 'onset_q', 'duration_q', 'fixed_bpm',
                    'executable_events', 'sounding_midi_events', 'performed_event_count', 'rubric_outcome'):
            self.assertIsNone(c[key], key)
        self.assertEqual(len(c['txt_full_lines']), 44)
        self.assertEqual(len(c['pdf_full_extracted_pages']), 16)
        self.assertEqual(tuple(c['modules']), level.KEYS)

    def test_all_pdf_tables_and_txt_workload_crosswalk(self) -> None:
        c = self.candidate
        self.assertEqual(c['declared_workload_by_module'], dict(zip(level.KEYS, level.EVENTS)))
        self.assertEqual((sum(level.EVENTS), c['declared_workload_total']), (1328, 1328))
        self.assertEqual([len(m['tables']) for m in c['modules'].values()], [2, 2, 2, 1, 1, 1, 1, 2, 1, 1])
        self.assertEqual(sum(len(t['rows']) for m in c['modules'].values() for t in m['tables']), 104)
        self.assertEqual(len(c['symbol_legend']), 8)
        for key, module in c['modules'].items():
            self.assertIn(module['name'].casefold(), c['txt_full_lines'][int(module['txt_ref'].split('L')[-1]) - 1].casefold())
            self.assertEqual(module['pdf_pages'], list(level.MODULE_PAGES[key]))
            self.assertIsNone(module['per_task_event_allocation'])
            for table in module['tables']:
                self.assertTrue(table['page_intro'])
                self.assertTrue(table['page_closing'])
                for row in table['rows']:
                    self.assertEqual(set(row['fields']), set(table['columns']))
                    self.assertEqual(len(row['raw_fields']), len(table['columns']))
                    self.assertTrue(row['pdf_ref'].startswith(f'L92-PDF-p{table["page"]}-L'))
                    self.assertIsNone(row['declared_events_for_row'])
                    self.assertIsNone(row['performed_events'])

    def test_articulation_order_voice_and_choice_relations(self) -> None:
        m = self.candidate['modules']
        a = m['A']['tables'][0]['rows']
        self.assertEqual([r['semantic']['muted_contact_count'] for r in a[:3]], [3, 4, 2])
        self.assertEqual(a[3]['semantic']['ordered_actions'], ['rake ends', 'bend begins'])
        self.assertEqual(a[4]['semantic']['ordered_actions'], ['pitch centers', 'vibrato begins'])
        self.assertEqual([r['semantic']['target_arrival_raw'] for r in a[5:]], ['next 16th', 'beat', 'beat 4'])
        self.assertEqual(m['A']['tables'][1]['rows'][4]['semantic']['relation'], 'diagnostic_flat')
        self.assertTrue(m['B']['tables'][1]['rows'][4]['semantic']['target_before_ornament'])
        self.assertTrue(m['B']['tables'][1]['rows'][5]['semantic']['ornament_omitted'])
        c = m['C']['tables'][0]['rows']
        self.assertEqual([r['semantic']['moving_voice_raw'] for r in c[4:7]], [('lower',), ('upper',), ('both',)])
        self.assertEqual(m['C']['tables'][1]['rows'][1]['semantic']['top_voice_action'], 'hold')
        self.assertEqual(m['C']['tables'][1]['rows'][1]['semantic']['lower_voice_action'], 'release early')
        self.assertEqual(m['D']['tables'][0]['rows'][4]['semantic']['node_sequence'], ['12th', '7th', '5th'])
        self.assertEqual(m['F']['tables'][0]['rows'][2]['semantic']['volume_stages'], ['0', 'full', '0 in 2 beats'])
        self.assertEqual(m['G']['tables'][0]['rows'][0]['semantic']['sequence_tokens'], ['x', 'target', 'x', 'target'])
        self.assertEqual(m['H']['tables'][0]['rows'][0]['semantic']['articulation_stages'], ['rake', 'bend', 'delayed vibrato'])
        self.assertEqual(m['H']['tables'][1]['rows'][6]['semantic']['alternatives'], ['natural harmonic', 'rest'])

    def test_capstone_mastery_and_unresolved_choices(self) -> None:
        c = self.candidate
        blocks = c['capstone']['section_blocks']
        self.assertEqual(len(blocks), 8)
        self.assertEqual([(r['semantic']['start_bar'], r['semantic']['end_bar']) for r in blocks], [(n, n + 3) for n in range(1, 33, 4)])
        self.assertEqual(sum(len(r['semantic']['chords']) for r in blocks), 32)
        self.assertEqual(blocks[3]['semantic']['chords'], ['E5', 'G5', 'A5', 'E5'])
        self.assertEqual(blocks[5]['semantic']['chords'], ['G', 'D', 'Em', 'C'])
        self.assertEqual(blocks[-1]['semantic']['dynamic_raw'], 'f -> pp')
        self.assertEqual([p['ordinal'] for p in c['capstone']['passes']], [1, 2, 3, 4, 5])
        gate = c['mastery']
        self.assertEqual((gate['required_score'], gate['maximum_score'], gate['separate_days']), (14, 16, 2))
        self.assertEqual(gate['txt_refs'], ['L92-TXT-L40', 'L92-TXT-L41'])
        self.assertEqual(len(gate['categories']), 8)
        self.assertIsNone(gate['score_descriptors'])
        self.assertEqual([a['kind'] for a in c['source_ambiguities']], ['PDF_only_task_expansion', 'workload_without_printed_note_events', 'mastery_scale_undefined', 'mastery_no_zero_label_mismatch'])
        self.assertTrue(all(a['status'] == 'pending_curriculum_review' for a in c['source_ambiguities']))

    def test_table_damage_and_output_boundary(self) -> None:
        page = list(self.candidate['pdf_full_extracted_pages'][2])
        page[page.index('1')] = 'missing ordinal'
        with self.assertRaisesRegex(level.SourceError, 'ordinal'):
            level.table(page, 3)
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
            self.assertEqual(level.build_candidate(root)['declared_workload_total'], 1328)
            for spec in (level.TXT, level.PDF, level.MAP):
                target = root / spec[0]
                original = target.read_bytes()
                target.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
                with self.subTest(source=spec[0]), self.assertRaisesRegex(level.SourceError, 'pin drift'):
                    level.build_candidate(root)
                target.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
