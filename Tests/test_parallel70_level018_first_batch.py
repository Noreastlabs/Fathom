"""P70 focused original-source, learning-pulse, projected-membership and refusal checks."""
from __future__ import annotations
import copy
import hashlib
import json
import subprocess
import sys
import unittest
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'Tools'))
import parallel70_level018_first_batch as c

OUT = c.ROOT/c.OUT
NATIVE = c.ROOT/'Build/parallel-13/four-shard-source-bundle-r01/bundle/bin/fathom_content_validate'
NATIVE_SHA = 'a85c1b25d8cded12cbe273e4620bd5f33a711d06311d29583a0fdbed7748f714'
PYTHON = sys.executable

class Level18FirstBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = c.derive()

    def test_original_cards_source_parity_and_semantics(self):
        lines, pages, rows = c.source_facts()
        self.assertEqual([r['source_local_key'] for r in rows], ['L18-rung01','L18-rung02'])
        self.assertEqual([r['root_fret'] for r in rows], [5,6])
        self.assertEqual(lines[76:84], pages[2][8:16])
        self.assertEqual(lines[86:94], pages[2][17:25])
        self.assertIn('one pair per beat as eighth notes', '\n'.join(lines[:70]))
        self.assertIn('one-beat pause only after each complete cell', '\n'.join(lines[:70]))
        for row in rows:
            notes = [n for d in row['directions'] for n in d['notes']]
            self.assertEqual(len(notes),52)
            self.assertEqual((notes[25]['degree'],notes[26]['degree']), (15,15))
            self.assertEqual((notes[25]['string'],notes[25]['fret']),
                             (notes[26]['string'],notes[26]['fret']))
            self.assertEqual((notes[0]['string'],notes[0]['fret']),
                             (notes[-1]['string'],notes[-1]['fret']))
            self.assertEqual([(p['quality'],p['semitones']) for d in row['directions'] for p in d['pairs']],
                             [(p['quality'],4 if p['quality']=='M3' else 3)
                              for d in row['directions'] for p in d['pairs']])

    def test_source_timing_provenance_pick_and_nonadmission(self):
        records = self.output['package.json']['records']
        side = self.output['source-provenance.json']
        self.assertEqual([len(r['events']) for r in records],[52,104])
        self.assertEqual(len(side['events']),156)
        self.assertEqual(set(side['events']),set(self.output['expected-profile.json']['event_sources']))
        a,pair = (r['events'] for r in records)
        self.assertEqual([(e['string'],e['fret'],e['finger'],e['midi'],e['spelling']) for e in a],
                         [(e['string'],e['fret'],e['finger'],e['midi'],e['spelling']) for e in pair[:52]])
        self.assertEqual([e['onset_q'] for e in a],
                         [list(Fraction(i,2).as_integer_ratio()) for i in range(52)])
        self.assertEqual([e['duration_q'] for e in pair],[[1,2]]*104)
        self.assertEqual((pair[51]['onset_q'],pair[52]['onset_q'],pair[-1]['onset_q']),
                         ([51,2],[27,1],[105,2]))
        self.assertEqual([(pair[i]['string'],pair[i]['fret'],pair[i]['midi']) for i in (0,51,52,103)],
                         [(1,5,45),(1,5,45),(1,6,46),(1,6,46)])
        self.assertEqual([(pair[i]['string'],pair[i]['fret'],pair[i]['midi']) for i in (25,26,77,78)],
                         [(6,5,69),(6,5,69),(6,6,70),(6,6,70)])
        self.assertEqual(sum(x['one_beat_release_after_first_cell'] for x in side['events'].values()),1)
        self.assertEqual(sum(x['frame_move_frets'] for x in side['events'].values()),1)
        for ids,count in zip(c.VARIANTS,(52,104)):
            for vid,start in zip(ids,('D','U')):
                expected=[start if i%2==0 else ('U' if start=='D' else 'D') for i in range(count)]
                self.assertEqual(side['variant_strokes'][vid],expected)
                self.assertEqual(expected[52] if count==104 else expected[0],start)
        self.assertTrue(all(r['runtime_eligible'] is False and r['rubric'] is None and
                            not r['control_scope']['whole_workbook_complete'] for r in records))
        self.assertTrue(all('fixed_bpm' not in r['timing'] for r in records))

    def test_native_all_projected_memberships_and_causal_generic_loss(self):
        self.assertEqual(hashlib.sha256(NATIVE.read_bytes()).hexdigest(),NATIVE_SHA)
        report=json.loads((OUT/'native-report-r02.json').read_text())
        self.assertTrue(report['valid_reference'])
        self.assertFalse(report['curriculum_playback_authorized'])
        self.assertEqual(json.loads((OUT/'native-exit-r02.json').read_text())['exit_code'],2)
        self.assertEqual((report['coverage']['observed_records'],report['coverage']['events'],
                          report['coverage']['variants'],report['coverage']['variant_event_memberships']),
                         (2,156,4,312))
        self.assertEqual([(x['code'],x['record']) for x in report['issues']],
                         [('MODEL_not_admitted',c.ITEMS[0]),('MODEL_not_admitted',c.ITEMS[1])])
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
                self.assertEqual(actual['pick'],'')  # Later typed runtime binding required.
                compared+=1
        self.assertEqual(compared,312)
        generic=json.loads((OUT/'diagnostic-even-subdivision-report.json').read_text())
        self.assertEqual(json.loads((OUT/'diagnostic-even-subdivision-exit.json').read_text())['exit_code'],2)
        self.assertTrue(generic['valid_reference']);self.assertFalse(generic['curriculum_playback_authorized'])
        self.assertEqual([v['model']['events'][52]['onset_q'] for v in generic['variants'] if
                          len(v['model']['events'])>52],[[26,1],[26,1]])

    def test_generator_refusals_and_output_scope(self):
        rows=c.source_facts()[2]; cells=[[n for d in r['directions'] for n in d['notes']] for r in rows]
        contacts=[cells[0],cells[0]+cells[1]]
        altered=copy.deepcopy(contacts);altered[1][52]['fret']=7
        cases=[({'changed_contacts':altered},'CANDIDATE_CONTACT_DRIFT'),
               ({'changed_onsets':[[[0,1]]*52,[[0,1]]*104]},'CANDIDATE_TIMING_DRIFT'),
               ({'changed_durations':[[[1,3]]*52,[[1,3]]*104]},'CANDIDATE_DURATION_DRIFT'),
               ({'changed_route':[['A'],['A','B']]},'CANDIDATE_ROUTE_DRIFT'),
               ({'changed_strokes':{c.VARIANTS[0][0]:['D']*52}},'CANDIDATE_STROKE_DRIFT'),
               ({'forced_bpm':60},'FIXED_BPM_UNAUTHORIZED'),
               ({'force_eligible':True},'FORCED_ELIGIBILITY'),
               ({'reserved_item':'fg:item:999999'},'FOREIGN_ID')]
        for kwargs,code in cases:
            with self.subTest(code=code),self.assertRaisesRegex(c.CandidateError,code):c.derive(**kwargs)
        cmd=[PYTHON,'-B',str(c.ROOT/'Tools/parallel70_level018_first_batch.py')]
        self.assertEqual(subprocess.run(cmd+['verify'],capture_output=True).returncode,0)
        run=subprocess.run(cmd+['build'],capture_output=True,text=True)
        self.assertNotEqual(run.returncode,0);self.assertIn('OUTPUT_EXISTS',run.stderr)
        run=subprocess.run(cmd+['build','--out','Build/parallel-70/escape'],capture_output=True,text=True)
        self.assertNotEqual(run.returncode,0);self.assertIn('OUTPUT_SCOPE',run.stderr)

    def test_native_causal_refusals(self):
        expected={'pitch':'MODEL_pitch_position','finger':'RECORD_FIDELITY',
                  'degree':'RECORD_FIDELITY','tempo':'UNKNOWN_FIELD',
                  'onset':'RECORD_FIDELITY','duration':'RECORD_FIDELITY',
                  'pause':'RECORD_FIDELITY','source':'SOURCE_HASH',
                  'identity':'RECORD_IDENTITY','forced_eligibility':'RUNTIME_NOT_ADMITTED',
                  'variant_pick':'RECORD_FIDELITY'}
        fixtures={}
        for name,required in expected.items():
            package=copy.deepcopy(self.output['package.json']);record=package['records'][1]
            event=record['events'][52]
            if name=='pitch':event['midi']+=1
            elif name=='finger':event['finger']=4
            elif name=='degree':event['degree_contexts']['Bb-major']['ordinal']=2
            elif name=='tempo':record['timing']['fixed_bpm']=120
            elif name=='onset':event['onset_q']=[28,1]
            elif name=='duration':event['duration_q']=[1,3]
            elif name=='pause':event['onset_q']=[26,1]
            elif name=='source':package['sources']['L18-TXT-RUNG02']['sha256']='0'*64
            elif name=='identity':record['id']='fg:item:999999'
            elif name=='forced_eligibility':record['runtime_eligible']=True
            elif name=='variant_pick':record['variants'][0]['pick_start']='U'
            data=c.encode(package);pp=OUT/f'negative-{name}-package.json'
            if pp.exists():self.assertEqual(pp.read_bytes(),data)
            else:pp.write_bytes(data)
            suffix=1
            while (OUT/f'negative-{name}-report-r{suffix:02d}.json').exists():suffix+=1
            rp=OUT/f'negative-{name}-report-r{suffix:02d}.json'; profile=OUT/'expected-profile.json'
            cmd=[str(NATIVE),'--package',str(pp),'--registry',str(OUT/'identity-registry.json'),
                 '--profile',str(profile),'--profile-sha256',hashlib.sha256(profile.read_bytes()).hexdigest(),
                 '--source-root',str(c.ROOT),'--report',str(rp)]
            run=subprocess.run(cmd,capture_output=True,text=True);report=json.loads(rp.read_text())
            self.assertEqual(run.returncode,1,(name,run.stdout,run.stderr))
            self.assertFalse(report['valid_reference'],name)
            codes=[issue['code'] for issue in report['issues']]
            self.assertIn(required,codes,(name,codes))
            fixtures[name]={'exit_code':run.returncode,'required_code':required,'issue_codes':codes,
                            'package_sha256':hashlib.sha256(data).hexdigest(),
                            'report_sha256':hashlib.sha256(rp.read_bytes()).hexdigest()}
        (OUT/'negative-checks.json').write_bytes(c.encode(fixtures))

if __name__=='__main__':unittest.main()
