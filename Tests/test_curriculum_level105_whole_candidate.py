"""Focused source, examination, hard-stop and boundary checks for whole Level 105."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest

from Tools import curriculum_level105_whole_candidate as level


class WholeLevel105Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = level.build_candidate()

    def test_source_status_and_hard_stop(self) -> None:
        c = self.candidate
        self.assertEqual((c['wbs'], c['level']), ('2.3.1.3.1', 105))
        self.assertEqual(c['source_map_row']['conversion_status'], 'converted_candidate_reference')
        self.assertTrue(c['source_map_row']['stable_ids_assigned'])
        self.assertEqual(c['existing_representative_item_id_read_only'], 'fg:item:000013')
        self.assertFalse(c['source_map_row']['runtime_eligible'])
        self.assertFalse(c['source_map_row']['admitted'])
        self.assertFalse(c['admitted'])
        self.assertIsNone(c['core_complete'])
        self.assertIsNone(c['graduated'])
        for key in ('canonical_id', 'exercise_id', 'onset_q', 'duration_q', 'fixed_bpm',
                    'executable_events', 'sounding_midi_events', 'performed_event_count', 'rubric_outcome'):
            self.assertIsNone(c[key], key)
        self.assertEqual((len(c['txt_full_lines']), len(c['pdf_full_extracted_pages'])), (61, 34))
        self.assertEqual((c['hard_stop']['maximum_core_level'], c['hard_stop']['level_106_exists']), (105, False))
        self.assertIn('THE UNIVERSAL 105-LEVEL CURRICULUM ENDS HERE.', c['txt_full_lines'])
        self.assertEqual(c['pdf_full_extracted_pages'][33][0], 'FINAL HARD STOP')

    def test_all_modules_and_task_rows(self) -> None:
        c = self.candidate
        self.assertEqual(tuple(c['modules']), level.KEYS)
        self.assertEqual(c['declared_workload_by_module'], dict(zip(level.KEYS, level.EVENTS)))
        self.assertEqual((sum(level.EVENTS), c['declared_workload_total']), (1872, 1872))
        self.assertEqual([sum(len(t['rows']) for t in m['tables']) for m in c['modules'].values()], [16, 8, 16, 15, 13, 8, 8, 16, 16, 35])
        self.assertEqual(sum(len(t['rows']) for m in c['modules'].values() for t in m['tables']), 151)
        self.assertEqual(sum(count for _, count in level.SPECS.values()), 215)
        for key, module in c['modules'].items():
            self.assertIn(module['name'].casefold(), c['txt_full_lines'][int(module['txt_ref'].split('L')[-1]) - 1].casefold())
            self.assertEqual(module['pdf_pages'], list(level.MODULE_PAGES[key]))
            self.assertIsNone(module['per_task_event_allocation'])
            for table in module['tables']:
                for row in table['rows']:
                    self.assertEqual(set(row['fields']), set(table['columns']))
                    self.assertTrue(row['pdf_ref'].startswith(f'L105-PDF-p{table["page"]}-L'))
                    self.assertIsNone(row['declared_events_for_row'])
                    self.assertIsNone(row['performed_result'])

    def test_musical_task_structure_and_unanswered_prompts(self) -> None:
        m = self.candidate['modules']
        self.assertEqual(m['A']['tables'][1]['rows'][0]['semantic']['time_limit_seconds'], 5)
        self.assertEqual(m['A']['tables'][1]['rows'][-1]['semantic']['time_limit_seconds'], 8)
        fixed = m['B']['fixed_melody_reharmonization']
        self.assertEqual([r['top_note'] for r in fixed['top_notes']], ['E', 'G', 'C', 'F#', 'Bb', 'A'])
        self.assertEqual(fixed['required_supporting_harmonies_per_note'], 3)
        self.assertTrue(all(r['supporting_harmonies'] is None for r in fixed['top_notes']))
        self.assertEqual([(r['semantic']['start_bar'], r['semantic']['end_bar']) for r in m['C']['tables'][1]['rows']], [(n, n + 1) for n in range(1, 16, 2)])
        self.assertEqual([r['semantic']['pass'] for r in m['D']['tables'][0]['rows']], list(range(1, 8)))
        self.assertEqual([(r['semantic']['start_bar'], r['semantic']['end_bar']) for r in m['E']['tables'][1]['rows']], [(1, 2), (3, 4), (5, 6), (7, 7), (8, 8)])
        self.assertEqual(m['F']['tables'][0]['rows'][-1]['semantic']['repertoire_task'], 'Recover one injected failure')
        self.assertEqual(m['G']['tables'][0]['rows'][0]['semantic']['ensemble_scenario'], 'Solo guitar')
        self.assertEqual(m['H']['tables'][1]['rows'][-1]['semantic']['random_cue'], 'End')
        self.assertEqual(m['I']['tables'][0]['rows'][-1]['semantic']['required_response'], 'follow authoritative cutoff')
        self.assertEqual(m['I']['tables'][1]['rows'][-1]['semantic']['time_limit_seconds'], 5)

    def test_exam_blocks_minute_continuity_and_reflection(self) -> None:
        exam = self.candidate['final_exam']
        self.assertEqual([(r['semantic']['start_minute'], r['semantic']['end_minute']) for r in exam['schedule']], level.SCHEDULE)
        self.assertEqual(exam['scheduled_minutes'], 60)
        self.assertFalse(exam['minute_windows_are_musical_onsets'])
        self.assertIsNone(exam['actual_duration_minutes'])
        self.assertEqual([len(b['rows']) for b in exam['detailed_blocks_1_to_7']], [4, 4, 4, 4, 4, 4, 3])
        for block in exam['detailed_blocks_1_to_7']:
            windows = [(r['semantic']['start_minute'], r['semantic']['end_minute']) for r in block['rows']]
            self.assertEqual(windows[0][0], level.SCHEDULE[block['block'] - 1][0])
            self.assertEqual(windows[-1][1], level.SCHEDULE[block['block'] - 1][1])
            self.assertTrue(all(left[1] == right[0] for left, right in zip(windows, windows[1:])))
        reflection = exam['block_8_reflection']
        self.assertEqual(len(reflection['questions']), 6)
        self.assertTrue(all(q['answer'] is None for q in reflection['questions']))
        self.assertEqual(reflection['answer_format'], 'one sentence')

    def test_graduation_remediation_postcore_and_source_limits(self) -> None:
        c = self.candidate
        gate = c['graduation']
        self.assertEqual((gate['maximum_score'], gate['required_score']), (30, 24))
        self.assertEqual([r['semantic']['domain'] for r in gate['rubric']], level.RUBRIC_DOMAINS)
        self.assertTrue(all(set(r['semantic']['anchors']) == {'0', '1', '2', '3'} for r in gate['rubric']))
        self.assertEqual(gate['no_zero_domains'], level.NO_ZERO)
        self.assertEqual(len(gate['requirements']), 6)
        self.assertEqual(len(gate['repeatability_alternatives']), 2)
        self.assertIsNone(gate['recorded_scores'])
        self.assertEqual((len(c['remediation']), len(c['core_path_transformations']), len(c['post_core_tracks'])), (9, 12, 10))
        self.assertEqual(c['remediation'][-1]['semantic']['weak_domain'], 'Recovery/performance')
        self.assertEqual([a['kind'] for a in c['source_ambiguities']], ['PDF_only_exam_expansion', 'workload_without_printed_note_events', 'exam_minute_windows_not_event_timing', 'block7_condensed_core_vs_finished_original', 'unperformed_prompts_and_reflection', 'representative_scope_is_selected_case_only'])
        self.assertTrue(all(a['status'].startswith(('pending_', 'source_')) for a in c['source_ambiguities']))

    def test_damage_determinism_output_and_pinned_drift(self) -> None:
        page = list(self.candidate['pdf_full_extracted_pages'][4])
        page[page.index('5 sec')] = '9 sec'
        damaged, _, _ = level.table(page, 5)
        with self.assertRaisesRegex(level.SourceError, 'reaction limit'):
            level.annotate(5, damaged)
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
            for spec in (level.TXT, level.PDF, level.MAP):
                source = root / spec[0]
                source.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(level.ROOT / spec[0], source)
            self.assertEqual(level.build_candidate(root)['declared_workload_total'], 1872)
            for spec in (level.TXT, level.PDF, level.MAP):
                source = root / spec[0]
                original = source.read_bytes()
                source.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
                with self.subTest(source=spec[0]), self.assertRaisesRegex(level.SourceError, 'pin drift'):
                    level.build_candidate(root)
                source.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
