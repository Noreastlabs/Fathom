"""P90 Level22 A->Bb original-card, exact-time and native-refusal checks."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import unittest
from fractions import Fraction
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
import parallel90_level022_first_neighbor as c

OUT=c.ROOT/c.OUT
NATIVE=c.ROOT/c.NATIVE

def native(package,report):
    profile=OUT/'expected-profile.json'
    run=subprocess.run([str(NATIVE),'--package',str(package),
                        '--registry',str(OUT/'identity-registry.json'),
                        '--profile',str(profile),
                        '--profile-sha256',hashlib.sha256(profile.read_bytes()).hexdigest(),
                        '--source-root',str(c.ROOT),'--report',str(report)],
                       capture_output=True,text=True)
    return run,json.loads(report.read_text())

class Level22NeighborTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=c.derive()

    def test_original_cards_and_all_60_contact_provenance(self):
        lines,pages,rungs=c.source_facts()
        self.assertEqual([(r['key'],r['root'],r['start'],r['pdfline']) for r in rungs],
                         [('A',5,55,6),('Bb',6,69,20)])
        self.assertIn('pause one beat','\n'.join(lines[45:50]))
        self.assertIn('pause one','\n'.join(pages[0]))
        side=self.output['source-provenance.json']['events']
        events=self.output['package.json']['records'][0]['events']
        self.assertEqual(len(events),len(side))
        self.assertEqual(len(events),60)
        self.assertEqual(set(side),{e['event_id'] for e in events})
        for index,(event,detail) in enumerate(zip(events,side.values())):
            rung=rungs[index//30]
            string,fret,finger=rung['layout'][index%30]
            degree=rung['degrees'][index%30]
            self.assertEqual((event['string'],event['fret'],event['finger'],
                              event['midi'],event['spelling']),
                             (c.OPEN[string][0],fret,finger,c.OPEN[string][1]+fret,
                              rung['tones'][index%30 if index%30<15 else 29-index%30]))
            self.assertEqual((detail['source_degree'],detail['source_fret'],
                              detail['source_finger'],detail['source_string_label']),
                             (degree,fret,finger,string))
            self.assertEqual(detail['source_txt_degree_line'],rung['start']+3)
            self.assertEqual(detail['source_txt_finger_line'],rung['start']+4)
            self.assertEqual(lines[detail['source_txt_tab_line']-1][:1],string)
            self.assertEqual(detail['source_pdf_page'],3)
            self.assertEqual(detail['pick_strokes'],
                             {c.VARIANTS[0]:'D' if index%2==0 else 'U',
                              c.VARIANTS[1]:'U' if index%2==0 else 'D'})
            self.assertEqual(detail['pick_txt_lines'],[38,39,40])
            self.assertEqual(event['degree_contexts'][f'{rung["key"]}-natural-minor']['source_label'],degree)
        for begin in (0,30):
            self.assertEqual((events[begin+14]['string'],events[begin+14]['fret'],events[begin+14]['midi']),
                             (events[begin+15]['string'],events[begin+15]['fret'],events[begin+15]['midi']))
            self.assertEqual([e['string'] for e in events[begin:begin+15]].count(4),3)
            self.assertEqual([e['string'] for e in events[begin:begin+15]].count(5),3)
            self.assertEqual(events[begin+8]['fret'],rungs[begin//30]['root']-1)

    def test_exact_q_pause_pair_end_and_two_continuous_pick_cycles(self):
        record=self.output['package.json']['records'][0]
        events=record['events']
        side=self.output['source-provenance.json']
        self.assertFalse(record['runtime_eligible'])
        self.assertFalse(record['control_scope']['whole_workbook_complete'])
        self.assertIsNone(record['rubric'])
        self.assertNotIn('fixed_bpm',record['timing'])
        for index,event in enumerate(events):
            q=Fraction((index//30)*16)+Fraction(index%30,2)
            self.assertEqual(event['onset_q'],list(q.as_integer_ratio()))
            self.assertEqual(event['duration_q'],[1,2])
            self.assertEqual(side['events'][event['event_id']]['nominal_slot_q'],event['onset_q'])
        self.assertEqual([events[i]['onset_q'] for i in (0,14,15,29,30,44,45,59)],
                         [[0,1],[7,1],[15,2],[29,2],[16,1],[23,1],[47,2],[61,2]])
        self.assertEqual(side['rest'],{'start_q':[15,1],'end_q':[16,1],
                                        'kind':'released_pressure; one-fret frame move'})
        self.assertEqual(sum(x['one_beat_release_after_cell'] for x in side['events'].values()),1)
        self.assertEqual(self.output['summary.json']['case_end_q'],[31,1])
        for variant,start in zip(record['variants'],('D','U')):
            self.assertEqual(variant['event_ids'],[e['event_id'] for e in events])
            self.assertEqual(side['variant_strokes'][variant['id']],
                             [start if i%2==0 else ('U' if start=='D' else 'D') for i in range(60)])
            self.assertEqual(side['variant_strokes'][variant['id']][29],
                             side['variant_strokes'][variant['id']][31])

    def test_frozen_native_valid_reference_with_playback_withheld(self):
        self.assertEqual(hashlib.sha256(NATIVE.read_bytes()).hexdigest(),c.NATIVE_SHA)
        report=json.loads((OUT/'native-report-r01.json').read_text())
        self.assertTrue(report['valid_reference'])
        self.assertFalse(report['curriculum_playback_authorized'])
        self.assertEqual(tuple(report['coverage'][k] for k in
                               ('observed_records','events','variants','variant_event_memberships')),
                         (1,60,2,120))
        self.assertEqual([(i['code'],i['record']) for i in report['issues']],
                         [('MODEL_not_admitted',c.ITEM)])
        for variant in report['variants']:
            self.assertFalse(variant['curriculum_playback_authorized'])
            self.assertEqual(len(variant['model']['events']),60)

    def test_generator_and_native_causal_refusals(self):
        for kwargs,code in (({'force_eligible':True},'FORCED_ELIGIBILITY'),
                            ({'forced_bpm':120},'FIXED_BPM_UNAUTHORIZED'),
                            ({'reserved_item':'fg:item:000001'},'FOREIGN_ID'),
                            ({'grouping':'even_subdivision'},'SOURCE_EVENT_TIME_REQUIRED'),
                            ({'changed_contacts':[]},'CONTACT_DRIFT')):
            with self.subTest(code=code),self.assertRaisesRegex(c.CandidateError,code):
                c.derive(**kwargs)
        checks=[]
        def check(name,edit):
            pkg=copy.deepcopy(self.output['package.json'])
            edit(pkg)
            package=OUT/f'negative-{name}-package.json'
            report=OUT/f'negative-{name}-report.json'
            package.write_bytes(c.encode(pkg))
            report.unlink(missing_ok=True)
            run,out=native(package,report)
            self.assertEqual(run.returncode,1,(name,run.stdout,run.stderr))
            self.assertFalse(out['valid_reference'])
            codes=sorted({issue['code'] for issue in out['issues']})
            self.assertTrue(codes,(name,'no causal issue'))
            checks.append({'name':name,'exit_code':run.returncode,'issue_codes':codes,
                           'package_sha256':c.sha(package.read_bytes()),
                           'report_sha256':c.sha(report.read_bytes())})
        check('minor-degree',lambda p:p['records'][0]['events'][2]['degree_contexts']['A-natural-minor'].update(source_label='3',alteration=0))
        check('minor-pitch',lambda p:p['records'][0]['events'][2].update(midi=49))
        check('g-backreach',lambda p:p['records'][0]['events'][8].update(fret=5))
        check('b-offset-finger',lambda p:p['records'][0]['events'][12].update(finger=3))
        check('wrong-onset',lambda p:p['records'][0]['events'][30].update(onset_q=[15,1]))
        check('wrong-duration',lambda p:p['records'][0]['events'][0].update(duration_q=[1,1]))
        check('wrong-identity',lambda p:p['records'][0].update(id='fg:item:009999'))
        check('forced-eligible',lambda p:p['records'][0].update(runtime_eligible=True))
        check('source-hash',lambda p:p['sources']['L22-TXT-RUNG01'].update(sha256='0'*64))
        check('wrong-pick',lambda p:p['records'][0]['variants'][0].update(pick_start='X'))
        (OUT/'negative-checks.json').write_bytes(c.encode({'checks':checks}))

    def test_frozen_packet_bytes(self):
        for name in c.NAMES:
            self.assertEqual((OUT/name).read_bytes(),c.encode(self.output[name]))

if __name__=='__main__':
    unittest.main()
