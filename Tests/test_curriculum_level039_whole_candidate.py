"""Focused source and boundary checks for detached Level 39 conversion."""
from __future__ import annotations

import copy
from io import BytesIO
from pathlib import Path
import tempfile
import unittest

from pypdf import PdfReader
from Tools import curriculum_level039_whole_candidate as c


class Level39WholeCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value=c.build_candidate()
        cls.lines=c.read_pinned(c.ROOT,c.TXT).decode('utf-8').splitlines()
        cls.pages=[(p.extract_text() or '').splitlines() for p in PdfReader(BytesIO(c.read_pinned(c.ROOT,c.PDF)),strict=True).pages]

    def test_source_roles_roots_and_nonadmission(self):
        v=self.value
        self.assertEqual(v['source']['txt']['sha256'],c.TXT[1])
        self.assertEqual(v['source']['pdf']['sha256'],c.PDF[1])
        self.assertEqual(v['pitch_roles']['F#'],{'A_major_degree':'6','F_sharp_minor_degree':'1'})
        self.assertEqual([(x['string'],x['fret']) for x in v['F_sharp_root_atlas']],c.F_ROOTS)
        self.assertEqual(v['status'],'non_admitted')
        self.assertIs(v['admitted'],False)
        for key in ('canonical_id','exercise_id','onset_q','duration_q','fixed_bpm','executable_audio_events'):
            self.assertIsNone(v[key])

    def test_every_written_note_has_one_matching_fret_and_two_degrees(self):
        m=self.value['modules']
        groups=(m['A_drone_comparison']+m['B_dual_degree_boxes']+m['C_root_to_root_cells']+
                [m['D_accent_relocation']]+[cad for pair in m['E_paired_cadences'] for cad in pair['cadences']]+[m['F_tonic_pivot']]+m['G_ear_cards'])
        for group in groups:
            for event in group['events']:
                note=event['note'];self.assertIn(note,c.ROLES)
                self.assertEqual((c.OPEN[event['string']]+event['fret'])%12,c.ROLES[note][2])
                self.assertEqual((event['A_major_degree'],event['F_sharp_minor_degree']),c.ROLES[note][:2])
                self.assertIn(event['finger'],range(1,5))
        self.assertEqual(len(groups),5+5+6+1+10+1+8)

    def test_module_counts_and_specific_semantics(self):
        m=self.value['modules'];counts=self.value['counts']
        self.assertEqual(counts,{'A':80,'B':120,'C':82,'D':48,'E':60,'F':32,'G':40,'total_written_sounding_tones':462})
        self.assertEqual([x['position'] for x in m['A_drone_comparison']],[1,2,3,4,5])
        self.assertTrue(all(x['drone_contexts']==['A','F#'] for x in m['A_drone_comparison']))
        for cell in m['B_dual_degree_boxes']+m['C_root_to_root_cells']:
            notes=[x['note'] for x in cell['events']]
            self.assertEqual(notes[cell['bars'][0]-1],notes[cell['bars'][0]])
        self.assertEqual([x['sounding_tones'] for x in m['C_root_to_root_cells']],[12]*5+[22])
        d=m['D_accent_relocation']
        self.assertEqual(d['A_accent_ordinals'],[2,7,12])
        self.assertEqual(d['F_sharp_accent_ordinals'],[1,6,11])
        for pair in m['E_paired_cadences']:
            a,f=pair['cadences']
            self.assertEqual([x['note'] for x in a['events'][:4]],[x['note'] for x in f['events'][:4]])
            self.assertEqual([x['note'] for x in a['events'][-2:]],['B','A'])
            self.assertEqual([x['note'] for x in f['events'][-2:]],['A','F#'])
        self.assertEqual(m['F_tonic_pivot']['center_by_bar'],['A','A','F#','F#','A','A','F#','F#'])
        self.assertEqual(m['F_tonic_pivot']['position_by_bar'],['P1','P1','P2','P2','P3','P3','P5','P5'])
        self.assertEqual([x['printed_answer'] for x in m['G_ear_cards']],['A-centered','F#-centered']*4)
        self.assertIn('score at least 7 of 8 on the ear test twice',self.value['mastery_gate_raw'][1])

    def test_pdf_presentation_differences_are_retained(self):
        diffs=self.value['source_presentation_differences']
        self.assertEqual(len(diffs),24)
        self.assertEqual({module:sum(x['module']==module for x in diffs) for module in 'AEFG'},{'A':5,'E':10,'F':1,'G':8})
        self.assertTrue(all(x['kind']=='TXT_Fng_row_not_printed_in_PDF' for x in diffs if x['module']=='A'))
        self.assertTrue(all('blank_tab_strings' in x for x in diffs if x['module']=='E'))
        self.assertTrue(all(x['kind']=='TXT_AMj_F_sharp_minor_Fng_rows_not_printed_in_PDF' for x in diffs if x['module']=='G'))
        variants=self.value['source_guidance_variants']
        self.assertEqual([x['module'] for x in variants],['D','E','F','G'])
        self.assertIn('hold it for two beats',variants[-1]['pdf_text'][0])
        self.assertIn('462 written sounding tones:',self.value['source_guidance']['pdf_full_extracted_pages'][0][51])
        self.assertEqual(len(self.value['source_guidance']['txt_full_lines']),520)
        self.assertEqual(len(self.value['source_guidance']['pdf_full_extracted_pages']),12)

    def test_rejects_pin_and_semantic_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for spec in (c.TXT,c.PDF):
                path=root/spec[0];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((c.ROOT/spec[0]).read_bytes())
            self.assertEqual(c.build_candidate(root)['counts']['total_written_sounding_tones'],462)
            path=root/c.TXT[0];path.write_bytes(path.read_bytes().replace(b'462 written sounding tones.',b'463 written sounding tones.',1))
            with self.assertRaisesRegex(c.SourceError,'pinned input drift'):c.build_candidate(root)
        bad=copy.deepcopy(self.lines);bad[30]=bad[30].replace('C#','C',1)
        with self.assertRaises(c.SourceError):c.parse_sources(bad,self.pages)
        bad=copy.deepcopy(self.lines);bad[240]=bad[240].replace('>','-',1)
        with self.assertRaises(c.SourceError):c.parse_sources(bad,self.pages)
        bad=copy.deepcopy(self.lines);bad[490]=bad[490].replace('B F#-centered','B A-centered')
        with self.assertRaises(c.SourceError):c.parse_sources(bad,self.pages)
        badpdf=copy.deepcopy(self.pages);badpdf[9][5]=badpdf[9][5].replace('F#','A',1)
        with self.assertRaises(c.SourceError):c.parse_sources(self.lines,badpdf)
        badpdf=copy.deepcopy(self.pages);badpdf[10][3]=badpdf[10][3].replace('two beats','three beats')
        with self.assertRaises(c.SourceError):c.parse_sources(self.lines,badpdf)

    def test_determinism_and_output_bounds(self):
        self.assertEqual(c.encode(c.build_candidate()),c.encode(c.build_candidate()))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);good=str(c.BUILD/'candidate.json')
            self.assertEqual(c.output_path(root,good),root.resolve()/good)
            for bad in ('Results/no.json','Build/parallel-11/other/no.json','Build/parallel-11/2.3.1.1.1-level039-whole-r01/../no.json','/tmp/no.json'):
                with self.assertRaises(c.SourceError):c.output_path(root,bad)
            path=root/c.BUILD/'candidate.json';path.parent.mkdir(parents=True);path.write_text('{}')
            with self.assertRaises(c.SourceError):c.output_path(root,good)


if __name__=='__main__':unittest.main()
