"""Focused Level15 Rung01 source, identity, triplet and native refusals."""
from __future__ import annotations
import copy,hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
import parallel55_level015_rung01_source as c
OUT=c.ROOT/c.OUT
NATIVE=c.ROOT/'Build/parallel-13/four-shard-source-bundle-r01/bundle/bin/fathom_content_validate'
NATIVE_SHA='a85c1b25d8cded12cbe273e4620bd5f33a711d06311d29583a0fdbed7748f714'
PYTHON=sys.executable
class SourcePacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.output=c.derive()
    def test_original_78_contact_parity_and_pdf_card(self):
        lines,pages,notes,current=c.source_facts()
        self.assertEqual(len(notes),78)
        self.assertEqual(len({(n['group'],n['slot']) for n in notes}),78)
        self.assertEqual([(n['string'],n['fret'],n['midi'],n['finger'],n['degree']) for n in notes[:3]],
                         [('E',5,45,2,1),('E',7,47,4,2),('A',4,49,1,3)])
        self.assertEqual([(n['string'],n['fret'],n['midi'],n['finger'],n['degree']) for n in notes[38:40]],
                         [('e',5,69,2,15)]*2)
        self.assertEqual({n['fret'] for n in notes if n['string']=='B'},{5,7})
        self.assertEqual(notes[-1]['spelling'],'A')
    def test_triplet_time_strokes_and_distinct_old_identity(self):
        rec=self.output['package.json']['records'][0]; events=rec['events']; side=self.output['source-provenance.json']
        self.assertEqual((rec['id'],rec['module_id'],rec['workbook_id']),
                         (c.ITEM,c.MODULE,c.WORKBOOK))
        self.assertEqual(rec['lineage'],{'kind':'new'}); self.assertEqual(rec['content_revision'],1)
        self.assertFalse(rec['runtime_eligible']); self.assertFalse(rec['control_scope']['whole_workbook_complete'])
        self.assertEqual([e['onset_q'] for e in events],[list(c.Fraction(i,3).as_integer_ratio()) for i in range(78)])
        self.assertEqual([e['duration_q'] for e in events],[[1,3]]*78)
        self.assertEqual(events[-1]['onset_q'],[77,3]); self.assertEqual(side['events'][events[-1]['event_id']]['nominal_slot_q'],[77,3])
        self.assertEqual(len(side['events']),78)
        self.assertEqual(set(side['events']),set(self.output['expected-profile.json']['event_sources']))
        self.assertEqual(sum(x['physical_contact_overlap_with_old_selected_illustration'] for x in side['events'].values()),3)
        overlap=side['existing_illustration_overlap']
        self.assertEqual((overlap['old_item'],overlap['shared_line_span'],overlap['old_content_revision']),
                         (c.OLD_ITEM,[70,81],3))
        self.assertFalse(overlap['same_case_or_history_identity'])
        self.assertTrue(set(overlap['old_event_ids']).isdisjoint(overlap['new_event_ids_first_three']))
        self.assertTrue(set(overlap['old_variant_ids']).isdisjoint(c.VARIANTS))
        for vid,start in zip(c.VARIANTS,('D','U')):
            expected=[start if i%2==0 else ('U' if start=='D' else 'D') for i in range(78)]
            self.assertEqual(side['variant_strokes'][vid],expected)
            self.assertNotEqual(expected[38],expected[39])
            self.assertNotEqual(expected[2],expected[3])
            self.assertEqual(rec['variants'][0]['grouping']['notes_per_beat'],3)
    def test_provisional_identity_and_native_nonadmission(self):
        audit=json.loads((OUT/'identity-audit.json').read_text())
        self.assertEqual(audit['status'],'PASS'); self.assertFalse(audit['matches']); self.assertFalse(audit['canonical_reservation'])
        self.assertEqual(set(self.output['candidate-allocation.json']['records']),{c.ITEM})
        self.assertEqual(hashlib.sha256(NATIVE.read_bytes()).hexdigest(),NATIVE_SHA)
        report=json.loads((OUT/'native-report-r01.json').read_text())
        self.assertTrue(report['valid_reference']); self.assertFalse(report['curriculum_playback_authorized'])
        self.assertEqual((report['coverage']['observed_records'],report['coverage']['events'],
                          report['coverage']['variants'],report['coverage']['variant_event_memberships']),
                         (1,78,2,156))
        self.assertEqual([(x['code'],x['record']) for x in report['issues']],[('MODEL_not_admitted',c.ITEM)])
        self.assertEqual(json.loads((OUT/'native-exit.json').read_text())['exit_code'],2)
    def test_derivation_refuses_contact_timing_pick_old_id_and_fixed_tempo(self):
        notes=c.source_facts()[2]
        altered=copy.deepcopy(notes); altered[44]['fret']=6
        cases=[({'changed_contacts':altered},'CANDIDATE_CONTACT_DRIFT'),
               ({'changed_onsets':[[0,1]]*78},'CANDIDATE_TIMING_DRIFT'),
               ({'changed_durations':[[1,4]]*78},'CANDIDATE_DURATION_DRIFT'),
               ({'changed_strokes':{c.VARIANTS[0]:['D']*78}},'CANDIDATE_STROKE_DRIFT'),
               ({'forced_bpm':120},'FIXED_BPM_UNAUTHORIZED'),
               ({'force_eligible':True},'FORCED_ELIGIBILITY'),
               ({'reserved_item':c.OLD_ITEM},'OLD_ID_REBIND_FORBIDDEN'),
               ({'old_item_rebound':True},'OLD_ID_REBIND_FORBIDDEN')]
        for kwargs,code in cases:
            with self.subTest(code=code),self.assertRaisesRegex(c.CandidateError,code): c.derive(**kwargs)
    def test_native_causal_refusals(self):
        expected={'pitch':'MODEL_pitch_position','string':'RECORD_FIDELITY','fret':'RECORD_FIDELITY',
                  'finger':'RECORD_FIDELITY','degree':'RECORD_FIDELITY','tempo':'UNKNOWN_FIELD',
                  'onset':'RECORD_FIDELITY','duration':'RECORD_FIDELITY','group_boundary':'RECORD_FIDELITY',
                  'turn':'MODEL_pitch_position','source':'SOURCE_HASH','identity':'RECORD_IDENTITY',
                  'old_identity':'RECORD_IDENTITY','forced_eligibility':'RUNTIME_NOT_ADMITTED',
                  'variant_pick':'RECORD_FIDELITY'}
        fixtures={}
        for name,required in expected.items():
            p=copy.deepcopy(self.output['package.json']); rec=p['records'][0]; event=rec['events'][44]
            if name=='pitch': event['midi']+=1
            elif name=='string': event['string']=4
            elif name=='fret': event['fret']=6
            elif name=='finger': event['finger']=3
            elif name=='degree': event['degree_contexts']['A-major']['ordinal']=7
            elif name=='tempo': rec['timing']['fixed_bpm']=120
            elif name=='onset': event['onset_q']=[15,1]
            elif name=='duration': event['duration_q']=[1,4]
            elif name=='group_boundary': rec['events'][3]['onset_q']=[2,1]
            elif name=='turn': rec['events'][39]['midi']+=1
            elif name=='source': p['sources']['L15-TXT1-70-91']['sha256']='0'*64
            elif name=='identity': rec['id']='fg:item:999999'
            elif name=='old_identity': rec['id']=c.OLD_ITEM
            elif name=='forced_eligibility': rec['runtime_eligible']=True
            elif name=='variant_pick': rec['variants'][0]['pick_start']='U'
            pp=OUT/f'negative-{name}-package.json'; data=c.encode(p)
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
        cmd=[PYTHON,'-B',str(c.ROOT/'Tools/parallel55_level015_rung01_source.py')]
        verify=subprocess.run(cmd+['verify'],capture_output=True,text=True)
        self.assertEqual(verify.returncode,0,verify.stderr)
        build=subprocess.run(cmd+['build'],capture_output=True,text=True)
        self.assertNotEqual(build.returncode,0); self.assertIn('OUTPUT_EXISTS',build.stderr)
        escape=subprocess.run(cmd+['build','--out','Build/parallel-55/escape'],capture_output=True,text=True)
        self.assertNotEqual(escape.returncode,0); self.assertIn('OUTPUT_SCOPE',escape.stderr)
if __name__=='__main__': unittest.main()
