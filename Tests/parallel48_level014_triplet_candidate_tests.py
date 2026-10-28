"""Focused source, triplet timing, identity and native refusal checks for P48."""
from __future__ import annotations
import copy, hashlib, json, subprocess, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
import parallel48_level014_triplet_candidate as c
OUT=c.ROOT/c.OUT
NATIVE=c.ROOT/'Build/parallel-13/four-shard-source-bundle-r01/bundle/bin/fathom_content_validate'
NATIVE_SHA='a85c1b25d8cded12cbe273e4620bd5f33a711d06311d29583a0fdbed7748f714'
PYTHON=sys.executable
class TripletCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.output=c.derive()
    def test_original_contacts_provenance_triplet_grid_and_pick_cycle(self):
        records=self.output['package.json']['records']; side=self.output['source-provenance.json']
        self.assertEqual([len(r['events']) for r in records],[36,72])
        self.assertEqual(sum(len(r['variants']) for r in records),4)
        self.assertEqual(len(side['events']),108)
        self.assertEqual(set(side['events']),set(self.output['expected-profile.json']['event_sources']))
        a,pair=(r['events'] for r in records)
        self.assertEqual([(e['string'],e['fret'],e['finger'],e['midi'],e['spelling']) for e in a],
                         [(e['string'],e['fret'],e['finger'],e['midi'],e['spelling']) for e in pair[:36]])
        self.assertEqual([e['onset_q'] for e in a],[list(c.Fraction(i,3).as_integer_ratio()) for i in range(36)])
        self.assertEqual([e['duration_q'] for e in pair],[[1,3]]*72)
        self.assertEqual((pair[35]['onset_q'],pair[36]['onset_q'],pair[-1]['onset_q']),
                         ([35,3],[13,1],[74,3]))
        self.assertEqual([(pair[i]['string'],pair[i]['fret'],pair[i]['midi']) for i in (0,35,36,71)],
                         [(1,5,45),(1,5,45),(1,6,46),(1,6,46)])
        self.assertEqual([(pair[i]['string'],pair[i]['fret'],pair[i]['midi']) for i in (17,18,53,54)],
                         [(3,7,57),(3,7,57),(3,8,58),(3,8,58)])
        self.assertEqual(sum(x['one_beat_pause_after_first_cell'] for x in side['events'].values()),1)
        self.assertEqual(sum(x['whole_frame_move_fret'] for x in side['events'].values()),1)
        self.assertEqual([x['source_rung'] for x in list(side['events'].values())[36:]], [1]*36+[2]*36)
        for vids,n in zip(c.VARIANTS,(36,72)):
            for vid,start in zip(vids,('D','U')):
                expected=[start if i%2==0 else ('U' if start=='D' else 'D') for i in range(n)]
                self.assertEqual(side['variant_strokes'][vid],expected)
                if n==72: self.assertEqual(expected[36],start)
        self.assertTrue(all(r['runtime_eligible'] is False and r['rubric'] is None and
                            not r['control_scope']['whole_workbook_complete'] for r in records))
        self.assertTrue(all('fixed_bpm' not in r['context'] for r in records))
        self.assertEqual(self.output['expected-profile.json']['degree_roots']['A-major']['root_pitch_class'],9)
        self.assertEqual(self.output['expected-profile.json']['degree_roots']['Bb-major']['root_pitch_class'],10)
    def test_source_card_and_secondary_parity(self):
        lines,pages,notes=c.source_facts()
        self.assertEqual(len(notes[0]),36); self.assertEqual(len(notes[1]),36)
        self.assertEqual(len({(n['group'],n['slot']) for n in notes[0]}),36)
        self.assertEqual(notes[0][17]['degree'],8); self.assertEqual(notes[0][18]['degree'],8)
        self.assertEqual(notes[1][35]['source_tone'],'Bb')
        self.assertEqual(self.output['package.json']['sources']['L14-TXT-RUNG01-56-67']['first_line'],56)
        self.assertEqual(self.output['package.json']['sources']['L14-TXT-RUNG02-70-81']['first_line'],70)
        self.assertEqual(self.output['package.json']['sources']['L14-PDF-CARDS-P3']['page'],3)
    def test_identity_and_native_nonadmission(self):
        audit=json.loads((OUT/'identity-audit.json').read_text())
        self.assertEqual(audit['status'],'PASS'); self.assertFalse(audit['matches']); self.assertFalse(audit['canonical_reservation'])
        self.assertEqual(set(self.output['candidate-allocation.json']['records']),set(c.ITEMS))
        self.assertEqual(hashlib.sha256(NATIVE.read_bytes()).hexdigest(),NATIVE_SHA)
        report=json.loads((OUT/'native-report.json').read_text())
        self.assertTrue(report['valid_reference']); self.assertFalse(report['curriculum_playback_authorized'])
        self.assertEqual((report['coverage']['observed_records'],report['coverage']['events'],report['coverage']['variants'],
                          report['coverage']['variant_event_memberships']),(2,108,4,216))
        self.assertEqual([(x['code'],x['record']) for x in report['issues']],
                         [('MODEL_not_admitted',c.ITEMS[0]),('MODEL_not_admitted',c.ITEMS[1])])
    def test_derivation_refusals(self):
        selected=c.source_facts()[2]; original=[selected[0],selected[0]+selected[1]]
        changed=copy.deepcopy(original); changed[1][36]['fret']=7
        cases=[({'changed_contacts':changed},'CANDIDATE_CONTACT_DRIFT'),
               ({'changed_onsets':[[[0,1]]*36,[[0,1]]*72]},'CANDIDATE_TIMING_DRIFT'),
               ({'changed_durations':[[[1,4]]*36,[[1,4]]*72]},'CANDIDATE_DURATION_DRIFT'),
               ({'changed_route':[['A'],['A','B']]},'CANDIDATE_ROUTE_DRIFT'),
               ({'changed_strokes':{c.VARIANTS[0][0]:['D']*36}},'CANDIDATE_STROKE_DRIFT'),
               ({'forced_bpm':100},'FIXED_BPM_UNAUTHORIZED'),
               ({'force_eligible':True},'FORCED_ELIGIBILITY'),
               ({'reserved_item':'fg:item:999999'},'FOREIGN_ID')]
        for kwargs,code in cases:
            with self.subTest(code=code),self.assertRaisesRegex(c.CandidateError,code): c.derive(**kwargs)
    def test_native_negative_fixtures(self):
        expected={'pitch':'MODEL_pitch_position','string':'RECORD_FIDELITY','fret':'RECORD_FIDELITY',
                  'finger':'RECORD_FIDELITY','degree':'RECORD_FIDELITY','tempo':'UNKNOWN_FIELD',
                  'onset':'RECORD_FIDELITY','duration':'RECORD_FIDELITY','group_boundary':'RECORD_FIDELITY',
                  'pause':'RECORD_FIDELITY','route':'RECORD_FIDELITY','source':'SOURCE_HASH',
                  'identity':'RECORD_IDENTITY','forced_eligibility':'RUNTIME_NOT_ADMITTED'}
        fixtures={}
        for name,required in expected.items():
            package=copy.deepcopy(self.output['package.json']); record=package['records'][1]; event=record['events'][36]
            if name=='pitch': event['midi']+=1
            elif name=='string': event['string']=5
            elif name=='fret': event['fret']=7
            elif name=='finger': event['finger']=4
            elif name=='degree': event['degree_contexts']['Bb-major']['ordinal']=2
            elif name=='tempo': record['timing']['fixed_bpm']=120
            elif name=='onset': event['onset_q']=[14,1]
            elif name=='duration': event['duration_q']=[1,4]
            elif name=='group_boundary': record['events'][3]['onset_q']=[2,1]
            elif name=='pause': event['onset_q']=[12,1]
            elif name=='route': record['context']['route']='A to B instead of Bb'
            elif name=='source': package['sources']['L14-TXT-RUNG02-70-81']['sha256']='0'*64
            elif name=='identity': record['id']='fg:item:999999'
            elif name=='forced_eligibility': record['runtime_eligible']=True
            pp=OUT/f'negative-{name}-package.json'; data=c.encode(package)
            if pp.exists(): self.assertEqual(pp.read_bytes(),data)
            else: pp.write_bytes(data)
            suffix=1
            while (OUT/f'negative-{name}-report-r{suffix:02d}.json').exists(): suffix+=1
            rp=OUT/f'negative-{name}-report-r{suffix:02d}.json'; profile=OUT/'expected-profile.json'
            cmd=[str(NATIVE),'--package',str(pp),'--registry',str(OUT/'identity-registry.json'),
                 '--profile',str(profile),'--profile-sha256',hashlib.sha256(profile.read_bytes()).hexdigest(),
                 '--source-root',str(c.ROOT),'--report',str(rp)]
            run=subprocess.run(cmd,capture_output=True,text=True); report=json.loads(rp.read_text())
            self.assertEqual(run.returncode,1,(name,run.stdout,run.stderr))
            self.assertFalse(report['valid_reference'],name)
            codes=[issue['code'] for issue in report['issues']]
            self.assertIn(required,codes,(name,codes))
            fixtures[name]={'exit_code':run.returncode,'required_code':required,'issue_codes':codes,
                            'package_sha256':hashlib.sha256(data).hexdigest(),
                            'report_sha256':hashlib.sha256(rp.read_bytes()).hexdigest()}
        (OUT/'negative-checks.json').write_bytes(c.encode(fixtures))
    def test_deterministic_output_and_boundary(self):
        cmd=[PYTHON,'-B',str(c.ROOT/'Tools/parallel48_level014_triplet_candidate.py')]
        verify=subprocess.run(cmd+['verify'],capture_output=True,text=True)
        self.assertEqual(verify.returncode,0,verify.stderr)
        build=subprocess.run(cmd+['build'],capture_output=True,text=True)
        self.assertNotEqual(build.returncode,0); self.assertIn('OUTPUT_EXISTS',build.stderr)
        escape=subprocess.run(cmd+['build','--out','Build/parallel-48/escape'],capture_output=True,text=True)
        self.assertNotEqual(escape.returncode,0); self.assertIn('OUTPUT_SCOPE',escape.stderr)
if __name__=='__main__': unittest.main()
