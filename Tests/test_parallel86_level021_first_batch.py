"""P86 Level21 source/native first-batch facts and causal refusals."""
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
import parallel86_level021_first_batch as c

OUT=c.ROOT/c.OUT
NATIVE=c.ROOT/c.NATIVE

def native(package,profile,report):
    run=subprocess.run([str(NATIVE),'--package',str(package),
                        '--registry',str(OUT/'identity-registry.json'),
                        '--profile',str(profile),
                        '--profile-sha256',hashlib.sha256(profile.read_bytes()).hexdigest(),
                        '--source-root',str(c.ROOT),'--report',str(report)],
                       capture_output=True,text=True)
    return run,json.loads(report.read_text())

class Level21FirstBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=c.derive()

    def test_original_cards_minor_pitch_and_comparison(self):
        lines,pages,rows,proposal=c.source_facts()
        self.assertEqual([r['key'] for r in rows],['A','Bb','B'])
        self.assertEqual([r['low_e_root_fret'] for r in rows],[5,6,7])
        self.assertIn('A natural minor: A B C  D E F  G  A','\n'.join(lines[:43]))
        self.assertIn('A B C D E F G A',self.output['package.json']['records'][0]['normalization'][1]['text'])
        self.assertEqual([r['notes'][2]['source_tone'] for r in rows],['C','Db','D'])
        self.assertEqual([r['notes'][5]['source_tone'] for r in rows],['F','Gb','G'])
        for rung,(row,prior) in enumerate(zip(rows,proposal)):
            events=self.output['package.json']['records'][rung]['events'][rung*16:(rung+1)*16]
            self.assertEqual(len(row['notes']),16)
            for e,n,f in zip(events,row['notes'],prior['schema1_fields']['events']):
                self.assertEqual((e['string'],e['fret'],e['finger'],e['midi'],e['spelling']),
                                 (f['string'],n['fret'],n['finger'],n['midi'],n['source_tone']))
                self.assertEqual(e['degree_contexts'],f['degree_contexts'])
            self.assertEqual((events[7]['string'],events[7]['fret'],events[7]['midi']),
                             (events[8]['string'],events[8]['fret'],events[8]['midi']))
            self.assertEqual(row['txt_rows']['Deg'],lines[row['txt_header_line']+2])
            self.assertEqual(row['txt_rows']['Fng'],lines[row['txt_header_line']+3])
        self.assertEqual(len(pages),6)

    def test_q_time_rest_pick_provenance_and_nonadmission(self):
        records=self.output['package.json']['records']
        side=self.output['source-provenance.json']
        self.assertEqual([len(r['events']) for r in records],[16,32,48])
        self.assertEqual(len(side['events']),96)
        self.assertEqual(set(side['events']),set(self.output['expected-profile.json']['event_sources']))
        for cidx,record in enumerate(records):
            self.assertFalse(record['runtime_eligible'])
            self.assertIsNone(record['rubric'])
            self.assertFalse(record['control_scope']['whole_workbook_complete'])
            self.assertNotIn('fixed_bpm',record['timing'])
            for rung in range(cidx+1):
                for j,event in enumerate(record['events'][rung*16:(rung+1)*16]):
                    q=Fraction(rung*9)+Fraction(j,2)
                    self.assertEqual(event['onset_q'],list(q.as_integer_ratio()))
                    self.assertEqual(event['duration_q'],[1,2])
            for variant in record['variants']:
                self.assertEqual(variant['event_ids'],[e['event_id'] for e in record['events']])
        self.assertEqual([records[2]['events'][i]['onset_q'] for i in (0,15,16,31,32,47)],
                         [[0,1],[15,2],[9,1],[33,2],[18,1],[51,2]])
        self.assertEqual(sum(s['one_beat_release_after_cell'] for s in side['events'].values()),3)
        for vids,count in zip(c.VARIANTS,(16,32,48)):
            for vid,start in zip(vids,('D','U')):
                expected=[start if i%2==0 else ('U' if start=='D' else 'D') for i in range(count)]
                self.assertEqual(side['variant_strokes'][vid],expected)

    def test_native_exact_reference(self):
        self.assertEqual(hashlib.sha256(NATIVE.read_bytes()).hexdigest(),c.NATIVE_SHA)
        report=json.loads((OUT/'native-report-r02.json').read_text())
        self.assertTrue(report['valid_reference'])
        self.assertFalse(report['curriculum_playback_authorized'])
        self.assertEqual(tuple(report['coverage'][k] for k in
                               ('observed_records','events','variants','variant_event_memberships')),
                         (3,96,6,192))
        self.assertEqual([(i['code'],i['record']) for i in report['issues']],
                         [('MODEL_not_admitted',item) for item in c.ITEMS])
        records={r['id']:r for r in self.output['package.json']['records']}
        for variant in report['variants']:
            authored=records[variant['item_id']]['events']
            self.assertEqual(len(variant['model']['events']),len(authored))
            self.assertFalse(variant['curriculum_playback_authorized'])
            for expected,actual in zip(authored,variant['model']['events']):
                self.assertEqual((actual['event_id'],actual['onset_q'],actual['duration_q'],actual['source_ref']),
                                 (expected['event_id'],expected['onset_q'],expected['duration_q'],
                                  self.output['expected-profile.json']['event_sources'][expected['event_id']]))

    def test_generator_and_native_refusals(self):
        for keyword,code in (({'force_eligible':True},'FORCED_ELIGIBILITY'),
                             ({'forced_bpm':120},'FIXED_BPM_UNAUTHORIZED'),
                             ({'reserved_item':'fg:item:000001'},'FOREIGN_ID'),
                             ({'grouping':'even_subdivision'},'SOURCE_EVENT_TIME_REQUIRED'),
                             ({'changed_contacts':[]},'CONTACT_DRIFT')):
            with self.subTest(code=code),self.assertRaisesRegex(c.CandidateError,code):
                c.derive(**keyword)
        first=c.ITEMS[0] + ':event:0003'
        for keyword,code in (({'changed_onsets':{first:[3,1]}},'timing'),
                             ({'changed_durations':{first:[1,1]}},'timing'),
                             ({'changed_strokes':{c.VARIANTS[0][0]:['U']*16}},'pick')):
            with self.subTest(code=code):
                changed=c.derive(**keyword)
                self.assertNotEqual(changed['package.json'] if code=='timing' else changed['source-provenance.json'],
                                    self.output['package.json'] if code=='timing' else self.output['source-provenance.json'])
        checks=[]
        def check(name,edit):
            pkg=copy.deepcopy(self.output['package.json'])
            edit(pkg)
            package=OUT/f'negative-{name}-package.json'
            report=OUT/f'negative-{name}-report.json'
            package.write_bytes(c.encode(pkg))
            run,out=native(package,OUT/'expected-profile.json',report)
            self.assertEqual(run.returncode,1,(name,run.stdout,run.stderr))
            self.assertFalse(out['valid_reference'])
            checks.append({'name':name,'exit_code':run.returncode,'issue_codes':sorted(set(i['code'] for i in out['issues'])),
                           'package_sha256':c.sha(package.read_bytes()),'report_sha256':c.sha(report.read_bytes())})
        check('minor-degree',lambda p:p['records'][0]['events'][2]['degree_contexts']['A-natural-minor'].update(source_label='3',alteration=0))
        check('minor-pitch',lambda p:p['records'][0]['events'][2].update(midi=49))
        check('wrong-finger',lambda p:p['records'][0]['events'][2].update(finger=3))
        check('wrong-onset',lambda p:p['records'][1]['events'][16].update(onset_q=[8,1]))
        check('wrong-duration',lambda p:p['records'][0]['events'][0].update(duration_q=[1,1]))
        check('wrong-identity',lambda p:p['records'][0].update(id='fg:item:009869'))
        check('forced-eligible',lambda p:p['records'][0].update(runtime_eligible=True))
        check('source-hash',lambda p:p['sources']['L21-TXT-RUNG01'].update(sha256='0'*64))
        check('wrong-pick',lambda p:p['records'][0]['variants'][0].update(pick_start='X'))
        (OUT/'negative-checks.json').write_bytes(c.encode({'checks':checks}))

    def test_frozen_bytes_and_prior_exit1_preserved(self):
        for name in c.NAMES:
            self.assertEqual((OUT/name).read_bytes(),c.encode(self.output[name]))
        first=json.loads((OUT/'attempt-r01/native-report-r01.json').read_text())
        self.assertEqual(first['exit_code'],1)
        self.assertIn('UNKNOWN_FIELD',[i['code'] for i in first['issues']])
        self.assertTrue((OUT/'attempt-r01/package.json').is_file())

if __name__=='__main__':unittest.main()
