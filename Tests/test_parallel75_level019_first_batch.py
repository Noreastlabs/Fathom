"""P75 original-source, triplet-time, projection and native refusal checks."""
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
import parallel75_level019_first_batch as c

OUT=c.ROOT/c.OUT
NATIVE=c.ROOT/c.NATIVE

def native(package,profile,report):
    if report.exists():
        original=report
        serial=2
        while report.exists():
            report=original.with_name(f'{original.stem}-r{serial:02d}{original.suffix}')
            serial+=1
    run=subprocess.run([str(NATIVE),'--package',str(package),
                        '--registry',str(OUT/'identity-registry.json'),
                        '--profile',str(profile),'--profile-sha256',hashlib.sha256(profile.read_bytes()).hexdigest(),
                        '--source-root',str(c.ROOT),'--report',str(report)],
                       capture_output=True,text=True)
    return run,json.loads(report.read_text()),report

class Level19ThreeCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=c.derive()

    def test_original_three_cards_and_harmonic_semantics(self):
        lines,pages,rows,proposal=c.source_facts()
        self.assertEqual([r['source_local_key'] for r in rows],
                         ['L19-rung01','L19-rung02','L19-rung03'])
        self.assertEqual([r['key'] for r in rows],['A','Bb','B'])
        self.assertEqual([r['root_fret'] for r in rows],[5,6,7])
        self.assertIn('one triad per beat as eighth-note triplets','\n'.join(lines[:70]))
        self.assertIn('one-beat pause only after each complete cell','\n'.join(lines[:70]))
        self.assertIn('One triad per beat while learning',pages[3][3])
        for row,prior in zip(rows,proposal):
            triads=row['triads']
            notes=[n for t in triads for n in t['notes']]
            self.assertEqual((len(triads),len(notes)),(22,66))
            self.assertEqual((notes[32]['degree'],notes[33]['degree']),(15,15))
            self.assertEqual((notes[32]['string'],notes[32]['fret']),
                             (notes[33]['string'],notes[33]['fret']))
            self.assertEqual((notes[0]['string'],notes[0]['fret']),
                             (notes[-1]['string'],notes[-1]['fret']))
            self.assertEqual([n['role'] for n in notes[:3]],['root','third','fifth'])
            self.assertEqual([n['role'] for n in notes[33:36]],['fifth','third','root'])
            self.assertEqual([(t['roman'],t['quality'],t['chord_name']) for t in triads],
                             [(t['roman'],t['quality'],t['chord_name']) for t in prior['triad_memberships']])
        self.assertEqual((pages[2][12],pages[2][13]),
                         (rows[0]['printed_txt']['ascending_deg'],rows[0]['printed_txt']['ascending_fng']))
        self.assertEqual((pages[3][12],pages[3][13]),
                         (rows[2]['printed_txt']['ascending_deg'],rows[2]['printed_txt']['ascending_fng']))

    def test_provenance_triplet_time_picks_and_nonadmission(self):
        records=self.output['package.json']['records']
        side=self.output['source-provenance.json']
        self.assertEqual([len(r['events']) for r in records],[66,132,198])
        self.assertEqual(len(side['events']),396)
        self.assertEqual(set(side['events']),set(self.output['expected-profile.json']['event_sources']))
        for idx,record in enumerate(records):
            events=record['events']
            for rung in range(idx+1):
                for j,event in enumerate(events[rung*66:(rung+1)*66]):
                    q=Fraction(rung*23)+Fraction(j,3)
                    self.assertEqual(event['onset_q'],list(q.as_integer_ratio()))
                    self.assertEqual(event['duration_q'],[1,3])
            self.assertFalse(record['runtime_eligible'])
            self.assertIsNone(record['rubric'])
            self.assertFalse(record['control_scope']['whole_workbook_complete'])
            self.assertNotIn('fixed_bpm',record['timing'])
        triple=records[2]['events']
        self.assertEqual([triple[i]['onset_q'] for i in (0,65,66,131,132,197)],
                         [[0,1],[65,3],[23,1],[134,3],[46,1],[203,3]])
        self.assertEqual([triple[i]['string'] for i in (0,32,33,65,66,98,99,131,132,164,165,197)],
                         [1,6,6,1,1,6,6,1,1,6,6,1])
        self.assertEqual(sum(s['one_beat_release_after_cell'] for s in side['events'].values()),3)
        self.assertEqual(sum(s['frame_move_frets'] for s in side['events'].values()),3)
        for vids,count in zip(c.VARIANTS,(66,132,198)):
            for vid,start in zip(vids,('D','U')):
                expected=[start if i%2==0 else ('U' if start=='D' else 'D') for i in range(count)]
                self.assertEqual(side['variant_strokes'][vid],expected)
                self.assertEqual(expected[66] if count>66 else expected[0],start)
                if count==198:self.assertEqual(expected[132],start)

    def test_native_all_792_projected_memberships(self):
        self.assertEqual(hashlib.sha256(NATIVE.read_bytes()).hexdigest(),c.NATIVE_SHA)
        report=json.loads((OUT/'native-report-r01.json').read_text())
        self.assertTrue(report['valid_reference'])
        self.assertFalse(report['curriculum_playback_authorized'])
        self.assertEqual((report['coverage']['observed_records'],report['coverage']['events'],
                          report['coverage']['variants'],report['coverage']['variant_event_memberships']),
                         (3,396,6,792))
        self.assertEqual([(i['code'],i['record']) for i in report['issues']],
                         [('MODEL_not_admitted',item) for item in c.ITEMS])
        by_item={r['id']:r for r in self.output['package.json']['records']}
        refs=self.output['expected-profile.json']['event_sources']
        compared=0
        for variant in report['variants']:
            authored=by_item[variant['item_id']]['events']
            projected=variant['model']['events']
            self.assertEqual(len(projected),len(authored))
            self.assertFalse(variant['curriculum_playback_authorized'])
            for expected,actual in zip(authored,projected):
                self.assertEqual((actual['event_id'],actual['onset_q'],actual['duration_q'],actual['source_ref']),
                                 (expected['event_id'],expected['onset_q'],expected['duration_q'],
                                  refs[expected['event_id']]))
                self.assertEqual(actual['pick'],'')  # P02 typed runtime binding still required.
                compared+=1
        self.assertEqual(compared,792)

    def test_native_generic_projection_causally_loses_both_gaps(self):
        output=c.derive(grouping='even_subdivision')
        package=OUT/'diagnostic-even-subdivision-package.json'
        profile=OUT/'diagnostic-even-subdivision-profile.json'
        package.write_bytes(c.encode(output['package.json']))
        profile.write_bytes(c.encode(output['expected-profile.json']))
        report=OUT/'diagnostic-even-subdivision-report.json'
        run,result,report=native(package,profile,report)
        self.assertEqual(run.returncode,2,(run.stdout,run.stderr))
        self.assertTrue(result['valid_reference'])
        self.assertFalse(result['curriculum_playback_authorized'])
        self.assertEqual([v['model']['events'][66]['onset_q'] for v in result['variants'] if
                          len(v['model']['events'])>66],[[22,1]]*4)
        self.assertEqual([v['model']['events'][132]['onset_q'] for v in result['variants'] if
                          len(v['model']['events'])>132],[[44,1]]*2)
        (OUT/'diagnostic-even-subdivision-exit.json').write_bytes(c.encode({'exit_code':run.returncode}))

    def test_generator_boundaries_and_native_refusals(self):
        with self.assertRaisesRegex(c.CandidateError,'FIXED_BPM_UNAUTHORIZED'):
            c.derive(forced_bpm=120)
        with self.assertRaisesRegex(c.CandidateError,'FORCED_ELIGIBILITY'):
            c.derive(force_eligible=True)
        with self.assertRaisesRegex(c.CandidateError,'GROUPING_INVALID'):
            c.derive(grouping='unbound')
        cmd=[sys.executable,'-B',str(c.ROOT/'Tools/parallel75_level019_first_batch.py')]
        self.assertEqual(subprocess.run(cmd+['verify'],capture_output=True).returncode,0)
        run=subprocess.run(cmd+['build'],capture_output=True,text=True)
        self.assertNotEqual(run.returncode,0);self.assertIn('OUTPUT_EXISTS',run.stderr)
        run=subprocess.run(cmd+['build','--out','Build/parallel-75/escape'],
                           capture_output=True,text=True)
        self.assertNotEqual(run.returncode,0);self.assertIn('OUTPUT_SCOPE',run.stderr)
        expected={'pitch':'MODEL_pitch_position','finger':'RECORD_FIDELITY',
                  'degree':'RECORD_FIDELITY','tempo':'UNKNOWN_FIELD',
                  'onset':'RECORD_FIDELITY','duration':'RECORD_FIDELITY',
                  'pause_a':'RECORD_FIDELITY','pause_bb':'RECORD_FIDELITY',
                  'source':'SOURCE_HASH','identity':'RECORD_IDENTITY',
                  'forced_eligibility':'RUNTIME_NOT_ADMITTED',
                  'variant_pick':'RECORD_FIDELITY'}
        fixtures={}
        for name,required in expected.items():
            package=copy.deepcopy(self.output['package.json'])
            record=package['records'][2]
            event=record['events'][66]
            if name=='pitch':event['midi']+=1
            elif name=='finger':event['finger']=4
            elif name=='degree':event['degree_contexts']['Bb-major']['ordinal']=2
            elif name=='tempo':record['timing']['fixed_bpm']=120
            elif name=='onset':event['onset_q']=[24,1]
            elif name=='duration':event['duration_q']=[1,2]
            elif name=='pause_a':event['onset_q']=[22,1]
            elif name=='pause_bb':record['events'][132]['onset_q']=[45,1]
            elif name=='source':package['sources']['L19-TXT-RUNG02']['sha256']='0'*64
            elif name=='identity':record['id']='fg:item:999999'
            elif name=='forced_eligibility':record['runtime_eligible']=True
            elif name=='variant_pick':record['variants'][0]['pick_start']='U'
            data=c.encode(package);pp=OUT/f'negative-{name}-package.json'
            pp.write_bytes(data)
            rp=OUT/f'negative-{name}-report.json'
            run,result,rp=native(pp,OUT/'expected-profile.json',rp)
            self.assertEqual(run.returncode,1,(name,run.stdout,run.stderr))
            self.assertFalse(result['valid_reference'],name)
            codes=[issue['code'] for issue in result['issues']]
            self.assertIn(required,codes,(name,codes))
            fixtures[name]={'exit_code':run.returncode,'required_code':required,
                            'issue_codes':codes,'package_sha256':hashlib.sha256(data).hexdigest(),
                            'report_path':str(rp.relative_to(c.ROOT)),
                            'report_sha256':hashlib.sha256(rp.read_bytes()).hexdigest()}
        (OUT/'negative-checks.json').write_bytes(c.encode(fixtures))

if __name__=='__main__':unittest.main()
