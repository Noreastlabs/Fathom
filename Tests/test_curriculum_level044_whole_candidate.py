"""Focused source-fidelity checks for detached whole-Level44 candidate."""
from __future__ import annotations

import copy
from io import BytesIO
from pathlib import Path
import tempfile
import unittest

from pypdf import PdfReader
from Tools import curriculum_level044_whole_candidate as c


class Level44WholeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x=c.build_candidate()
        cls.lines=c.pin(c.ROOT,c.TXT).decode('utf-8').splitlines()
        cls.pages=[(p.extract_text() or '').splitlines() for p in PdfReader(BytesIO(c.pin(c.ROOT,c.PDF)),strict=True).pages]

    def test_pins_inventory_predecessor_and_nonadmission(self):
        x=self.x
        self.assertEqual({k:v['sha256'] for k,v in x['source'].items()},dict(txt=c.TXT[1],pdf=c.PDF[1],source_map=c.MAP[1],predecessor_txt=c.P43_TXT[1],predecessor_pdf=c.P43_PDF[1]))
        self.assertEqual(x['source_map_rows']['level44']['pair_status'],'exact_stem_pair')
        self.assertFalse(x['source_map_rows']['level44']['admitted'])
        self.assertEqual(x['status'],'non_admitted');self.assertIs(x['admitted'],False)
        for field in ('canonical_id','exercise_id','onset_q','duration_q','fixed_bpm','pick_attack_count','executable_events'):
            self.assertIsNone(x[field])

    def test_complete_module_coverage_and_pdf_workload(self):
        x=self.x;m=x['modules']
        self.assertEqual(list(m),list('ABCDEFGHIJ'))
        self.assertEqual(len(x['module_sections']),10)
        self.assertEqual(x['pdf_printed_workload_by_module'],c.COUNTS)
        self.assertEqual(x['pdf_printed_total_tones'],646)
        self.assertEqual(len(m['A']),6);self.assertEqual(len(m['B']),6);self.assertEqual(len(m['C']),6)
        self.assertEqual(len(m['D']['families']),5);self.assertEqual(len(m['D']['rhythm_templates_raw']),13)
        self.assertEqual(len(m['E']),5);self.assertEqual(len(m['F']),2)
        self.assertEqual([len(q['positions']) for q in m['F']],[5,5])
        self.assertEqual(len(m['G']),4);self.assertEqual(len(m['H']),5);self.assertEqual(len(m['I']),4)
        self.assertEqual(len(m['J']['all_combinations']),16)
        self.assertEqual(len(x['source_guidance']['txt_full_lines']),660)
        self.assertEqual(len(x['source_guidance']['pdf_full_extracted_pages']),19)

    def test_resolution_alternatives_and_support_note_roles(self):
        m=self.x['modules']
        self.assertEqual(self.x['core_notes'],['A','C','D','Eb','E','G'])
        self.assertEqual(self.x['marked_support_notes'],{'C#':'3*','F#':'6*','F':'b6*','B':'2*/E7-5','G#':'7*/E7-3'})
        for site in m['A']:
            self.assertEqual(site['target_fret']-site['source_fret'],1)
            self.assertEqual(set(site['alternatives']),{'fretted_target','bend_release','slide','hammer_pull'})
            self.assertEqual((c.OPEN[site['string']]+site['source_fret'])%12,c.PC['C'])
            self.assertEqual((c.OPEN[site['string']]+site['target_fret'])%12,c.PC['C#'])
        for site in m['B']:
            self.assertEqual(site['notes'],['D','Eb','E','E','Eb','D'])
            self.assertEqual(len(site['passes']),4)
        for site in m['C']:
            self.assertEqual(site['target_fret']-site['source_fret'],2)
            self.assertTrue({'picked','slide','legato'}.issubset(site['alternatives']))
        self.assertEqual(sum(x['printed_workload_tones'] for x in m['D']['families']),160)
        self.assertEqual(m['D']['families'][4]['notes'],['A','C','C#','E','G','F#','F','E'])

    def test_phrase_families_translations_and_endings(self):
        m=self.x['modules']
        self.assertEqual([p['written_tones'] for p in m['E']],[13,11,9,12,12])
        for pair in m['E']:
            self.assertEqual(pair['answer']['degrees'][-1],'1')
        self.assertEqual([x['written_tones'] for x in m['F']],[30,35])
        for lick in m['F']:
            self.assertEqual([p['position'] for p in lick['positions']],[1,2,3,4,5])
            self.assertEqual(len({tuple(p['notes']) for p in lick['positions']}),1)
        self.assertEqual([x['written_tones'] for x in m['G']],[12,12,14,13])
        self.assertEqual(sum(x['written_tones'] for x in m['H']),70)
        for pair in m['H']:
            self.assertEqual(pair['tonic_ending']['degrees'][:-1],pair['turnaround_ending']['degrees'][:-1])
            self.assertEqual(pair['tonic_ending']['degrees'][-1],'1')
            self.assertEqual(pair['turnaround_ending']['degrees'][-1],'5')

    def test_turnaround_chord_and_recombination_ambiguity(self):
        m=self.x['modules']
        self.assertEqual([i['printed_workload_tones'] for i in m['I']],[9,8,16,8])
        self.assertEqual(m['I'][2]['kind'],'simultaneous_voice_leading_shapes')
        self.assertIn('four descending three-note shapes',m['I'][2]['degrees_raw'])
        self.assertEqual(m['J']['printed_workload_tones'],64)
        self.assertEqual(m['J']['implied_full_combination_degree_occurrences'],128)
        self.assertEqual([x['label'] for x in m['J']['openings']],list('ABCD'))
        self.assertEqual([x['label'] for x in m['J']['endings']],['1','2','3','4'])
        self.assertEqual({(x['opening'],x['ending']) for x in m['J']['all_combinations']},{(a,b) for a in 'ABCD' for b in '1234'})
        self.assertTrue(any(x['kind']=='J_workload_count_ambiguous' for x in self.x['source_differences']))
        self.assertTrue(any(x['kind']=='PDF_visual_completion_audit_border_overlap' for x in self.x['source_differences']))

    def test_refuses_pin_and_semantic_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for spec in (c.TXT,c.PDF,c.MAP,c.P43_TXT,c.P43_PDF):
                target=root/spec[0];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((c.ROOT/spec[0]).read_bytes())
            self.assertEqual(c.build_candidate(root)['pdf_printed_total_tones'],646)
            target=root/c.TXT[0];target.write_bytes(target.read_bytes().replace(b'CORE PITCH POOL',b'CORE PITCH FOOL',1))
            with self.assertRaisesRegex(c.SourceError,'pin drift'):c.build_candidate(root)
        bad=copy.deepcopy(self.lines);bad[32]=bad[32].replace('8b(9)','8b(10)')
        with self.assertRaises(c.SourceError):c.parse_a(bad,self.pages)
        bad=copy.deepcopy(self.lines);bad[154]=bad[154].replace('b3-3*','b3-b3')
        with self.assertRaises(c.SourceError):c.parse_d(bad,self.pages)
        bad=copy.deepcopy(self.lines);bad[485]=bad[485].replace('b3-5','b3-1')
        with self.assertRaises(c.SourceError):c.parse_h(bad,self.pages)
        bad=copy.deepcopy(self.lines);bad[614]=bad[614].replace('G-F#-F-E','G-F#-F-A')
        with self.assertRaises(c.SourceError):c.parse_j(bad,self.pages)

    def test_output_bounds_and_determinism(self):
        self.assertEqual(c.encode(c.build_candidate()),c.encode(c.build_candidate()))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);good=str(c.BUILD/'test.json')
            self.assertEqual(c.output_path(root,good),root.resolve()/good)
            for bad in ('Results/test.json','Build/parallel-11/other/test.json','Build/parallel-11/2.3.1.1.1-level044-whole-r01/../test.json','/tmp/test.json'):
                with self.assertRaises(c.SourceError):c.output_path(root,bad)
            path=root/c.BUILD/'test.json';path.parent.mkdir(parents=True);path.write_text('{}')
            with self.assertRaises(c.SourceError):c.output_path(root,good)


if __name__=='__main__':unittest.main()
