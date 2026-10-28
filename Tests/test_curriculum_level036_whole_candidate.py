"""Focused checks for the detached Level 36 source candidate."""
from __future__ import annotations

import copy
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest

from pypdf import PdfReader
from Tools import curriculum_level036_whole_candidate as c


class Level36WholeCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate = c.build_candidate()
        cls.lines = c.read_pinned(c.ROOT, c.TXT).decode('utf-8').splitlines()
        cls.pages = [(p.extract_text() or '').splitlines() for p in PdfReader(BytesIO(c.read_pinned(c.ROOT,c.PDF)),strict=True).pages]

    def test_source_and_nonadmission(self):
        x=self.candidate
        self.assertEqual(x['source']['txt']['sha256'],c.TXT[1])
        self.assertEqual(x['source']['pdf']['sha256'],c.PDF[1])
        self.assertEqual(x['status'],'non_admitted')
        self.assertIs(x['admitted'],False)
        for key in ('canonical_id','exercise_id','onset_q','duration_q','fixed_bpm'):
            self.assertIsNone(x[key])
        self.assertEqual(x['key'],'A major pentatonic')
        self.assertEqual(x['notes'],['A','B','C#','E','F#'])

    def test_module_a_groups_pitches_fingers_and_turn(self):
        positions=self.candidate['modules']['A_legato_positions']
        self.assertEqual(len(positions),5)
        self.assertEqual(sum(p['sounding_tones'] for p in positions),120)
        self.assertEqual(sum(p['pick_attacks'] for p in positions),60)
        for position in positions:
            groups=position['groups']
            self.assertEqual(len(groups),12)
            self.assertEqual([g['articulation'] for g in groups],['h']*6+['p']*6)
            self.assertEqual([g['string'] for g in groups],list(c.STRINGS)+list(reversed(c.STRINGS)))
            self.assertEqual(groups[5]['string'],groups[6]['string'])
            self.assertEqual(groups[5]['notes'][-1],groups[6]['notes'][0])
            self.assertEqual(sum(g['pick_attacks'] for g in groups),12)
            for group in groups:
                for fret,note,degree in zip(group['frets'],group['notes'],group['degrees']):
                    self.assertEqual(c.pitch(group['string'],fret),c.PC[note])
                    self.assertEqual(degree,c.DEG[note])
            self.assertEqual(position['raw_txt'][8:18],position['raw_pdf_cell'])

    def test_module_b_seam_contour_and_single_attack(self):
        seams=self.candidate['modules']['B_seam_chains']
        self.assertEqual([s['seam'] for s in seams],[1,2,3,4])
        self.assertEqual(sum(s['sounding_tones'] for s in seams),120)
        self.assertEqual(sum(s['pick_attacks'] for s in seams),24)
        for seam in seams:
            self.assertEqual([p['string'] for p in seam['phrases']],list(c.STRINGS))
            for phrase in seam['phrases']:
                self.assertEqual(phrase['articulations'],['pick','hammer_on','slide_up','slide_down','pull_off'])
                self.assertEqual(phrase['frets'][0],phrase['frets'][4])
                self.assertEqual(phrase['frets'][1],phrase['frets'][3])
                self.assertEqual(phrase['pick_attacks'],1)

    def test_whole_step_bends_prebends_and_root_holds(self):
        m=self.candidate['modules']
        self.assertEqual(len(m['C_whole_step_bends']),9)
        self.assertEqual(len(m['D_prebend_cells']),6)
        self.assertEqual(len(m['D_A_root_vibrato_holds']),8)
        for site in m['C_whole_step_bends']+m['D_prebend_cells']:
            self.assertEqual(site['target_fret']-site['source_fret'],2)
            self.assertEqual(c.pitch(site['string'],site['source_fret']),c.PC[site['source_note']])
            self.assertEqual(c.pitch(site['string'],site['target_fret']),c.PC[site['target_note']])
            self.assertEqual(site['pick_attacks'],4 if site in m['C_whole_step_bends'] else 3)
        for hold in m['D_A_root_vibrato_holds']:
            self.assertEqual(c.pitch(hold['string'],hold['fret']),c.PC['A'])
            self.assertEqual(hold['pick_attacks'],1)

    def test_cadences_counts_and_pdf_omission(self):
        x=self.candidate
        cadences=x['modules']['E_cadences']
        self.assertEqual([p['pick_attacks'] for p in cadences],[4,4,4,3,4])
        self.assertEqual([len(p['attack_tokens']) for p in cadences],[4,4,4,3,4])
        self.assertTrue(all(p['txt_notes_raw'].startswith('Notes:') for p in cadences))
        self.assertEqual([p['pdf_notes_raw'] is None for p in cadences],[True]*4+[False])
        self.assertEqual([d['position'] for d in x['source_discrepancies']],[1,2,3,4])
        self.assertTrue(all(d['status']=='pending_curriculum_review' for d in x['source_discrepancies']))
        self.assertEqual(x['counts']['total_pick_attacks'],165)
        self.assertEqual(x['counts']['explicit_legato_slide_tones'],240)
        self.assertEqual(x['counts']['bend_prebend_cells'],15)

    def test_refuses_source_and_structure_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for spec in (c.TXT,c.PDF):
                path=root/spec[0]; path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes((c.ROOT/spec[0]).read_bytes())
            self.assertEqual(c.build_candidate(root)['counts']['total_pick_attacks'],165)
            path=root/c.TXT[0]
            path.write_bytes(path.read_bytes().replace(b'4b(6)',b'4b(7)',1))
            with self.assertRaisesRegex(c.SourceError,'pinned input drift'):
                c.build_candidate(root)
        bad=copy.deepcopy(self.lines)
        bad[48]=bad[48].replace('AhB','AhC#',1)
        with self.assertRaises(c.SourceError):
            c.parse_position(bad,self.pages,1)
        bad=copy.deepcopy(self.lines)
        bad[148]=bad[148].replace('/9\\7p5','/10\\7p5',1)
        with self.assertRaises(c.SourceError):
            c.parse_seams(bad,self.pages)
        with self.assertRaises(c.SourceError):
            c.bend_row(self.lines[190].replace('4b(6)','4b(7)',1),'bend')
        badpdf=copy.deepcopy(self.pages)
        badpdf[12][13]='Notes: fabricated'
        with self.assertRaises(c.SourceError):
            c.parse_cadences(self.lines,badpdf)

    def test_determinism_and_output_boundary(self):
        self.assertEqual(c.encode(c.build_candidate()),c.encode(c.build_candidate()))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.assertEqual(c.output_path(root,str(c.BUILD/'x.json')),root.resolve()/c.BUILD/'x.json')
            for bad in ('Results/not-build.json','Build/parallel-11/other/x.json','Build/parallel-11/2.3.1.1.1-level036-whole-r01/../x.json','/tmp/x.json'):
                with self.assertRaises(c.SourceError):
                    c.output_path(root,bad)
            good=root/c.BUILD/'x.json';good.parent.mkdir(parents=True);good.write_text('{}')
            with self.assertRaises(c.SourceError):
                c.output_path(root,str(c.BUILD/'x.json'))


if __name__=='__main__':
    unittest.main()
