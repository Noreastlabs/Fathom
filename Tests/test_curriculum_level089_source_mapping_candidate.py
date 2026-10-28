from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'Build/parallel-03/2.3.1.3.1-level089-source-music-r01'
TOOL = ROOT / 'Tools/curriculum_level089_source_mapping_candidate.py'
TXT = ROOT / 'Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XII_Level_89_Country_Americana_and_Hybrid_Picking_Groove_Alternating_Bass_Boom_Chuck_Train_Rhythm_Double_Stops_and_Controlled_Fills.txt'
PDF = ROOT / 'Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XII_Level_89_Country_Americana_and_Hybrid_Picking_Groove_Alternating_Bass_Boom_Chuck_Train_Rhythm_Double_Stops_and_Controlled_Fills.pdf'

spec = importlib.util.spec_from_file_location('level089_candidate', TOOL)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def sha(data: bytes | str) -> str:
    if isinstance(data, str): data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


class Level089CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = module.build(ROOT)
        cls.txt = TXT.read_text(encoding='utf-8')
        from pypdf import PdfReader
        cls.pages = [p.extract_text() or '' for p in PdfReader(str(PDF)).pages]

    def test_authority_identity_and_pending_nonruntime_status(self):
        d = self.doc
        self.assertEqual(d['workbook_id'], 'fg:workbook:000089')
        self.assertEqual(d['status'], 'pending_source_reconciliation')
        self.assertEqual(d['review'], 'Pending')
        for key in ('canonical_ids_allocated','canonical_record_emitted','runtime_eligible','imported','admitted','whole_workbook_complete','playable_projection_emitted'):
            self.assertIs(d[key], False)
        self.assertTrue(d['authority']['prior_staged_outputs_opened_or_used'] is False)
        self.assertTrue(d['authority']['lexical_coverage_is_metadata_only'])
        self.assertEqual(d['source_bindings']['catalog_status']['catalog_role'], 'read_only_source_preservation')

    def test_txt_lines_spans_and_pdf_module_parity(self):
        lines=self.doc['txt']['lines']
        self.assertEqual(len(lines),42)
        self.assertEqual(lines[2]['literal'],'')
        self.assertEqual(lines[8]['literal'],'COMPLETE WRITTEN WORKLOAD: 1488 events')
        self.assertEqual(lines[3]['literal'],'LEVEL 89 OF 105 - HARD STOP AFTER LEVEL 105')
        self.assertEqual(sum(x['declared_events'] for x in self.doc['txt']['modules']),1488)
        self.assertEqual(len(self.doc['structures']['p01_pdf_module_declarations']),10)
        self.assertEqual([x['exercise']['text'] for x in self.doc['structures']['p01_pdf_module_declarations']], [x[1] for x in module.MODULES])
        page1=self.pages[0].splitlines()
        self.assertTrue(any(page1[i:i+2]==['TOTAL','1488'] for i in range(len(page1)-1)))
        self.assertEqual(self.doc['txt']['next_boundary'],90)
        self.assertEqual(self.doc['txt']['hard_stop_after_level'],105)
        self.assertTrue(all(x['codepoint_span'][0] <= x['codepoint_span'][1] for x in lines))
        self.assertEqual(self.pages[0].splitlines()[2].count('\x7f'),5)

    def test_all_pdf_pages_cached_and_indexed(self):
        pages=self.doc['pdf']['pages']
        self.assertEqual(len(pages),20)
        self.assertEqual(self.doc['pdf']['pypdf_version'],'6.10.0')
        for i,p in enumerate(pages):
            self.assertEqual(p['page_number'],i+1)
            self.assertEqual(p['page_text_sha256'],module.PAGE_HASHES[i])
            self.assertEqual(sha(self.pages[i]),p['page_text_sha256'])
            self.assertEqual(self.pages[i].splitlines()[0],p['heading'])
            self.assertTrue(p['lexical_coverage_is_metadata_only'])
            self.assertTrue(p['line_index'])

    def test_supported_source_music_locators_have_exact_source_spans(self):
        d=self.doc
        self.assertEqual(d['mapping_counts'],{
            'a_p03_note_spelling_targets':32,'a_p04_action_cells':24,'b_p05_ordered_pattern_slots':28,
            'c_p06_grid_contacts':48,'f_p11_note_spelling_tokens':30,'g_p14_arrangement_bar_harmonies':16,
            'h_p15_18_bar_harmonies':32,'i_p19_bar_harmonies':32,'total_source_locators':242})
        self.assertEqual(len(d['source_music_locators']),242)
        for loc in d['source_music_locators']:
            self.assertTrue(loc['source_locator'].startswith('src-l089-'))
            self.assertIsNone(loc['canonical_id'])
            self.assertFalse(loc['canonical_identity'])
            self.assertFalse(loc['runtime_eligible'])
            start,end=loc['codepoint_span']
            literal=self.pages[loc['page_number']-1][start:end]
            self.assertEqual(literal,loc['literal'])
            self.assertEqual(sha(literal),loc['literal_sha256'])
            self.assertEqual(loc['temporal_semantics'],'source ordinal only; no onset or duration inferred')

    def test_exact_tables_and_unresolved_semantics(self):
        s=self.doc['structures']
        self.assertEqual(len(s['p03_a_bass_patterns']),8)
        for row in s['p03_a_bass_patterns']:
            self.assertEqual([x['count_label']['text'] for x in row['pitch_spelling_targets']],['1','2','3','4'])
            self.assertTrue(all(x['chord_label']['text']==row['chord']['text'] for x in row['pitch_spelling_targets']))
        self.assertEqual(len(s['p04_a_chord_answers']),6)
        self.assertEqual(len(s['p05_b_patterns']),6)
        self.assertEqual(sum(len(r['ordered_pattern_slots']) for r in s['p05_b_patterns']),28)
        self.assertEqual(len(s['p06_c_train_grids']),6)
        self.assertEqual(sum(len(r['contacts']) for r in s['p06_c_train_grids']),48)
        self.assertTrue(all(contact['role_reference']['symbol']['text']==contact['text'] for row in s['p06_c_train_grids'] for contact in row['contacts']))
        self.assertEqual(len(s['p11_f_bass_runs']),7)
        self.assertEqual(sum(len(r['note_spelling_tokens']) for r in s['p11_f_bass_runs']),30)
        self.assertEqual(len(s['p14_g_arrangements']),4)
        self.assertEqual(sum(len(r['bars']) for r in s['p14_g_arrangements']),16)
        self.assertEqual(sum(len(study['bars']) for study in s['p15_18_h_studies']),32)
        self.assertEqual(sum(len(row['expanded_bars']) for row in s['p19_i_capstone']),32)
        self.assertTrue(all(r['bar_count']=='not printed' for r in s['p13_g_pocket_variations']))
        self.assertEqual(s['p09_e_double_stop_routes'][0]['route_literal']['text'],'B3/e3 -> B5/e5 -> B7/e7')
        self.assertEqual(s['p09_e_double_stop_routes'][0]['interpretation'],'unresolved_literal_route')
        self.assertEqual(len(s['p20_j_recovery_mastery_roadmap']['recovery_rows']),8)
        self.assertIn('not_observed_learner_result',s['p20_j_recovery_mastery_roadmap']['status'])
        self.assertEqual(self.doc['unresolved_semantics']['workload'],'1488 is a declared workload total, not individually enumerated events')
        self.assertNotIn('events',self.doc)
        self.assertNotIn('playable_projection',self.doc)

    def test_candidate_is_deterministic_and_refuses_overwrite(self):
        a=BUILD/'candidate-a.json'; b=BUILD/'candidate-b.json'
        for p in (a,b):
            self.assertFalse(p.exists())
            cp=subprocess.run([sys.executable,str(TOOL),'--root',str(ROOT),'--output',str(p)],capture_output=True,text=True)
            self.assertEqual(cp.returncode,0,cp.stderr)
        self.assertEqual(a.read_bytes(),b.read_bytes())
        self.assertEqual(json.loads(a.read_text()),self.doc)
        cp=subprocess.run([sys.executable,str(TOOL),'--root',str(ROOT),'--output',str(a)],capture_output=True,text=True)
        self.assertEqual(cp.returncode,2)
        self.assertIn('overwrite refused',cp.stderr)

    def test_root_outside_output_and_symlink_refusals(self):
        out=BUILD/'refusal.json'
        cp=subprocess.run([sys.executable,str(TOOL),'--root',str(ROOT.parent),'--output',str(out)],capture_output=True,text=True)
        self.assertEqual(cp.returncode,2)
        self.assertIn('exact authoritative',cp.stderr)
        cp=subprocess.run([sys.executable,str(TOOL),'--root',str(ROOT),'--output','/tmp/level089-outside.json'],capture_output=True,text=True)
        self.assertEqual(cp.returncode,2)
        self.assertIn('under the exact P03 Build directory',cp.stderr)
        target=BUILD/'symlink-target.tmp'
        link=BUILD/'symlink-output.json'
        target.write_text('sentinel')
        try:
            link.symlink_to(target)
            cp=subprocess.run([sys.executable,str(TOOL),'--root',str(ROOT),'--output',str(link)],capture_output=True,text=True)
            self.assertEqual(cp.returncode,2)
            self.assertIn('symlink output refused',cp.stderr)
            self.assertEqual(target.read_text(),'sentinel')
        finally:
            link.unlink(missing_ok=True)
            target.unlink(missing_ok=True)


if __name__=='__main__':
    unittest.main(verbosity=2)
