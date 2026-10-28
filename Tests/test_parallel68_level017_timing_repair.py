"""P68 source-event-time projection regression and causal native refusals."""
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
import parallel68_level017_timing_repair as repair

ROOT=repair.ROOT
OUT=ROOT/repair.OUT
NATIVE=ROOT/'Build/parallel-13/four-shard-source-bundle-r01/bundle/bin/fathom_content_validate'
NATIVE_SHA='a85c1b25d8cded12cbe273e4620bd5f33a711d06311d29583a0fdbed7748f714'

def read(path):return json.loads(path.read_bytes())
def sha(raw):return hashlib.sha256(raw).hexdigest()

class Level17TimingRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package=read(OUT/'package.json')
        cls.profile=read(OUT/'expected-profile.json')
        cls.native=read(OUT/'native-report-r01.json')
        cls.provenance=read(OUT/'source-provenance.json')

    def test_exact_immutable_repair_boundary(self):
        output=repair.make()
        for name,data in output.items():self.assertEqual((OUT/name).read_bytes(),data,name)
        old=read(ROOT/repair.OLD/'package.json')
        self.assertEqual(self.package,read(ROOT/repair.DIAG))
        self.assertEqual(self.package['records'][0],old['records'][0])
        self.assertEqual(self.profile['reference_package'],self.package)
        self.assertEqual((OUT/'source-provenance.json').read_bytes(),(ROOT/repair.OLD/'source-provenance.json').read_bytes())
        changed=read(OUT/'repair-comparison.json')['changed_fields']
        self.assertEqual([x['variant_id'] for x in changed],list(repair.PAIR_IDS))
        for i,(new,prior) in enumerate(zip(self.package['records'],old['records'])):
            self.assertEqual(new['events'],prior['events'])
            self.assertEqual(new['runtime_eligible'],False)
            self.assertIsNone(new['rubric'])
            for current,previous in zip(new['variants'],prior['variants']):
                exact=copy.deepcopy(current);exact['grouping']=previous['grouping']
                self.assertEqual(exact,previous)
                if i==1:
                    self.assertEqual(current['grouping']['kind'],'source_event_time')
                    self.assertIsNone(current['grouping']['notes_per_beat'])
                    self.assertIsNone(current['grouping']['beat_unit_q'])
        self.assertEqual(sha(NATIVE.read_bytes()),NATIVE_SHA)

    def test_all_projected_variant_times_match_source_events(self):
        models={v['variant_id']:v for v in self.native['variants']}
        records=self.package['records']
        self.assertEqual(set(models),{v['id'] for r in records for v in r['variants']})
        self.assertEqual(sum(len(r['events']) for r in records),288)
        self.assertEqual(len(self.provenance['events']),288)
        for record in records:
            event_by_id={e['event_id']:e for e in record['events']}
            for variant in record['variants']:
                projected=models[variant['id']]['model']['events']
                self.assertEqual(len(projected),len(variant['event_ids']))
                self.assertEqual([e['event_id'] for e in projected],variant['event_ids'])
                for event in projected:
                    original=event_by_id[event['event_id']]
                    self.assertEqual(event['onset_q'],original['onset_q'],event['event_id'])
                    self.assertEqual(event['duration_q'],original['duration_q'],event['event_id'])
                    self.assertEqual(event['source_ref'],self.profile['event_sources'][event['event_id']])
                strokes=self.provenance['variant_strokes'][variant['id']]
                self.assertEqual(len(strokes),len(projected))
                self.assertEqual(strokes[0],variant['pick_start'])
                self.assertTrue(all(a!=b for a,b in zip(strokes,strokes[1:])))
        for variant_id in repair.PAIR_IDS:
            events=models[variant_id]['model']['events']
            self.assertEqual(events[95]['onset_q'],[95,4])
            self.assertEqual(events[96]['onset_q'],[25,1])
            self.assertEqual(events[-1]['onset_q'],[195,4])
            self.assertEqual(Fraction(*events[-1]['onset_q'])+Fraction(*events[-1]['duration_q']),Fraction(49))
            self.assertEqual(Fraction(*events[96]['onset_q'])-(Fraction(*events[95]['onset_q'])+Fraction(*events[95]['duration_q'])),Fraction(1))
            self.assertEqual(self.provenance['variant_strokes'][variant_id][95], 'U' if variant_id==repair.PAIR_IDS[0] else 'D')
            self.assertEqual(self.provenance['variant_strokes'][variant_id][96], 'D' if variant_id==repair.PAIR_IDS[0] else 'U')
        for variant_id in ('fg:variant:007442','fg:variant:007443'):
            events=models[variant_id]['model']['events']
            self.assertEqual(Fraction(*events[-1]['onset_q'])+Fraction(*events[-1]['duration_q']),Fraction(24))

    def test_native_positive_nonadmission(self):
        report=self.native
        self.assertTrue(report['valid_reference'])
        self.assertFalse(report['curriculum_playback_authorized'])
        self.assertEqual((report['coverage']['observed_records'],report['coverage']['events'],
                          report['coverage']['variants'],report['coverage']['variant_event_memberships']),
                         (2,288,4,576))
        self.assertEqual([(x['code'],x['record']) for x in report['issues']],
                         [('MODEL_not_admitted','fg:item:001160'),('MODEL_not_admitted','fg:item:001161')])
        self.assertEqual(report['package_sha256'],sha((OUT/'package.json').read_bytes()))

    def test_focused_causal_refusals(self):
        expected={'lost_pause':'RECORD_FIDELITY','source_hash':'SOURCE_HASH',
                  'grouping_drift':'RECORD_FIDELITY','variant_event_time_drift':'RECORD_FIDELITY'}
        index={}
        for name,required in expected.items():
            package=copy.deepcopy(self.package)
            pair=package['records'][1]
            if name=='lost_pause':pair['events'][96]['onset_q']=[24,1]
            elif name=='source_hash':package['sources']['L17-TXT-RUNG02']['sha256']='0'*64
            elif name=='grouping_drift':pair['variants'][0]['grouping']['kind']='even_subdivision'
            elif name=='variant_event_time_drift':
                pair['variants'][1]['event_ids'][96],pair['variants'][1]['event_ids'][97]=pair['variants'][1]['event_ids'][97],pair['variants'][1]['event_ids'][96]
            data=repair.encode(package)
            pp=OUT/f'negative-{name}-package.json';rp=OUT/f'negative-{name}-report-r01.json'
            if pp.exists():self.assertEqual(pp.read_bytes(),data)
            else:pp.write_bytes(data)
            if not rp.exists():
                run=subprocess.run([str(NATIVE),'--package',str(pp),'--registry',str(OUT/'identity-registry.json'),
                    '--profile',str(OUT/'expected-profile.json'),'--profile-sha256',sha((OUT/'expected-profile.json').read_bytes()),
                    '--source-root',str(ROOT),'--report',str(rp)],capture_output=True,text=True)
                self.assertEqual(run.returncode,1,(name,run.stdout,run.stderr))
            report=read(rp)
            self.assertFalse(report['valid_reference'],name)
            codes=[x['code'] for x in report['issues']]
            self.assertIn(required,codes,(name,codes))
            index[name]={'exit_code':1,'required_code':required,'issue_codes':codes,
                         'package_sha256':sha(data),'report_sha256':sha(rp.read_bytes())}
        (OUT/'negative-checks.json').write_bytes(repair.encode(index))

if __name__=='__main__':unittest.main()
