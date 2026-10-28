"""Focused source, task-relation, form and boundary checks for whole Level 97."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest

from Tools import curriculum_level097_whole_candidate as level


class WholeLevel97Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = level.build_candidate()

    def test_source_status_and_detached_boundary(self) -> None:
        c = self.candidate
        self.assertEqual((c['wbs'], c['level'], c['section']), ('2.3.1.3.1', 97, 'XIV'))
        self.assertEqual(c['source_map_row']['conversion_status'], 'converted_candidate_reference')
        self.assertTrue(c['source_map_row']['stable_ids_assigned'])
        self.assertEqual(c['existing_representative_item_id_read_only'], 'fg:item:000012')
        self.assertFalse(c['source_map_row']['runtime_eligible'])
        self.assertFalse(c['source_map_row']['admitted'])
        self.assertFalse(c['admitted'])
        for key in ('canonical_id', 'exercise_id', 'onset_q', 'duration_q', 'fixed_bpm',
                    'executable_events', 'sounding_midi_events', 'performed_event_count', 'rubric_outcome'):
            self.assertIsNone(c[key], key)
        self.assertEqual(len(c['txt_full_lines']), 43)
        self.assertEqual(len(c['pdf_full_extracted_pages']), 19)

    def test_all_module_tables_and_workload(self) -> None:
        c = self.candidate
        self.assertEqual(tuple(c['modules']), level.KEYS)
        self.assertEqual(c['declared_workload_by_module'], dict(zip(level.KEYS, level.EVENTS)))
        self.assertEqual((sum(level.EVENTS), c['declared_workload_total']), (1424, 1424))
        self.assertEqual([len(m['tables']) for m in c['modules'].values()], [2, 2, 2, 2, 1, 2, 2, 2, 1, 1])
        self.assertEqual(sum(len(t['rows']) for m in c['modules'].values() for t in m['tables']), 117)
        self.assertEqual(len(c['reference_listening_passes']), 7)
        for key, module in c['modules'].items():
            self.assertIn(module['name'].casefold(), c['txt_full_lines'][int(module['txt_ref'].split('L')[-1]) - 1].casefold())
            self.assertEqual(module['pdf_pages'], list(level.MODULE_PAGES[key]))
            self.assertIsNone(module['per_task_event_allocation'])
            for table in module['tables']:
                for row in table['rows']:
                    self.assertEqual(set(row['fields']), set(table['columns']))
                    self.assertTrue(row['pdf_ref'].startswith(f'L97-PDF-p{table["page"]}-L'))
                    self.assertIsNone(row['declared_events_for_row'])
                    self.assertIsNone(row['observed_answer'])
                    self.assertIsNone(row['performed_events'])

    def test_listening_dependencies_and_decision_rows(self) -> None:
        c = self.candidate
        passes = c['reference_listening_passes']
        self.assertEqual([r['semantic']['pass'] for r in passes], list(range(1, 8)))
        self.assertEqual(passes[0]['semantic']['listen_for'], 'pulse/form')
        self.assertEqual(passes[0]['semantic']['defer'], 'exact chords')
        self.assertEqual(passes[-1]['semantic']['defer'], 'micro-details')
        m = c['modules']
        self.assertEqual(m['A']['tables'][0]['rows'][0]['semantic']['answer_options'], ['4/4', '3/4', '6/8', 'uncertain'])
        self.assertIn('No guitar during Pass 1', m['A']['tables'][0]['page_closing'][0])
        self.assertEqual(m['A']['tables'][1]['rows'][-1]['semantic']['deliverable'], 'memory recitation with audio stopped')
        self.assertEqual(m['B']['tables'][1]['rows'][-1]['semantic']['harmonic_question'], 'inversion/slash chord?')
        self.assertTrue(m['C']['tables'][0]['rows'][3]['semantic']['requires_primary_contact_map'])
        self.assertEqual(m['C']['tables'][1]['rows'][5]['semantic']['candidate_arrangement_inference'], 'intentional rest is part of arrangement')
        self.assertEqual(m['D']['tables'][1]['rows'][2]['semantic']['treatment'], 'approximate or omit')
        self.assertEqual(m['E']['tables'][0]['rows'][0]['semantic']['classification_options'], ['S', 'C', 'O'])
        self.assertEqual([r['semantic']['version'] for r in m['F']['tables'][0]['rows']], ['Skeleton', 'Functional', 'Identity', 'Performance', 'Reduced', 'Emergency'])
        self.assertEqual(m['F']['tables'][0]['rows'][4]['semantic']['required_contents_raw'], '50% fewer fills/ornaments')
        self.assertEqual(m['G']['tables'][0]['rows'][0]['semantic']['accept_if'], 'same function/register role')
        self.assertEqual([r['semantic']['score'] for r in m['G']['tables'][1]['rows']], [0, 1, 2, 3])

    def test_studies_capstone_and_mastery(self) -> None:
        c = self.candidate
        self.assertEqual(len(c['studies']), 2)
        self.assertEqual([len(s['passes']) for s in c['studies']], [6, 6])
        self.assertTrue(all(not s['audio_supplied'] and s['observed_harmony'] is None for s in c['studies']))
        self.assertIn('bar 9', c['studies'][0]['brief'])
        self.assertIn('secondary dominant', c['studies'][1]['brief'])
        blocks = c['capstone']['section_blocks']
        self.assertEqual([(r['semantic']['start_bar'], r['semantic']['end_bar']) for r in blocks], [(1, 4), (5, 12), (13, 16), (17, 24), (25, 32), (33, 40), (41, 44), (45, 48)])
        self.assertEqual([r['semantic']['section_label'] for r in blocks], ['Intro', 'A', 'B', "A'", 'C', 'Solo/support', 'Return', 'Outro'])
        self.assertEqual(sum(r['semantic']['end_bar'] - r['semantic']['start_bar'] + 1 for r in blocks), 48)
        self.assertEqual(len(c['capstone']['required_deliverables']), 7)
        self.assertFalse(c['capstone']['source_audio_supplied'])
        self.assertFalse(c['capstone']['chord_chart_allowed'])
        gate = c['mastery']
        self.assertEqual((gate['required_score'], gate['maximum_score'], gate['unfamiliar_excerpt_count']), (14, 16, 2))
        self.assertEqual([r['semantic']['category'] for r in gate['rubric']], level.RUBRIC_CATEGORIES)
        self.assertEqual(gate['rubric'][-1]['semantic']['anchors'], {'0': 'restart', '1': 'simplifies', '2': 'seamless'})
        self.assertEqual(gate['no_zero_categories'], ['Form', 'Bass/function', 'Groove', 'Recovery'])
        self.assertEqual([a['kind'] for a in c['source_ambiguities']], ['PDF_only_task_expansion', 'audio_not_supplied', 'workload_without_printed_note_events', 'representative_scope_is_selected_case_only'])

    def test_table_damage_determinism_and_output_boundary(self) -> None:
        page = list(self.candidate['pdf_full_extracted_pages'][17])
        page[page.index('1-4')] = 'bad range'
        rows, _, _ = level.table(page, 18)
        with self.assertRaisesRegex(level.SourceError, 'I bar range'):
            level.annotate(18, rows)
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
            self.assertEqual(level.build_candidate(root)['declared_workload_total'], 1424)
            for spec in (level.TXT, level.PDF, level.MAP):
                target = root / spec[0]
                original = target.read_bytes()
                target.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
                with self.subTest(source=spec[0]), self.assertRaisesRegex(level.SourceError, 'pin drift'):
                    level.build_candidate(root)
                target.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
