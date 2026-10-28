"""Focused original-source, sixteenth, identity and native refusals for P59."""
from __future__ import annotations
import copy,hashlib,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
import parallel59_level016_first_batch as c

OUT=c.ROOT/c.OUT
NATIVE=c.ROOT/'Build/parallel-13/four-shard-source-bundle-r01/bundle/bin/fathom_content_validate'
NATIVE_SHA='a85c1b25d8cded12cbe273e4620bd5f33a711d06311d29583a0fdbed7748f714'
PYTHON=sys.executable

class Level16FirstBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.output=c.derive()

    def test_original_cards_source_parity_and_semantics(self):
        lines,pages,rows=c.source_facts()
        self.assertEqual([r['source_local_key'] for r in rows],['L16-rung01','L16-rung02'])
        self.assertEqual([r['root_fret'] for r in rows],[5,6])
        self.assertEqual(pages[2][7:15],rows[0]['raw_txt_card'][3:11])
        self.assertEqual(pages[2][21:29],rows[1]['raw_txt_card'][3:11])
        self.assertIn('pause one beat after each', '\n'.join(lines[:60]))
        for r in rows:
            notes=[n for g in r['groups'] for n in g['notes']]
            self.assertEqual(len(notes),40)
            self.assertEqual((notes[19]['degree'],notes[20]['degree']),(8,8))
            self.assertEqual((notes[19]['string'],notes[19]['fret']),
                             (notes[20]['string'],notes[20]['fret']))
            self.assertEqual((notes[0]['string'],notes[0]['fret']),
                             (notes[-1]['string'],notes[-1]['fret']))
            self.assertEqual(len({(n['ordinal_in_cell'],n['string'],n['fret']) for n in notes}),40)

    def test_candidate_grid_provenance_pick_and_nonadmission(self):
        records=self.output['package.json']['records']; side=self.output['source-provenance.json']
        self.assertEqual([len(r['events']) for r in records],[40,80])
        self.assertEqual(len(side['events']),120)
        self.assertEqual(set(side['events']),set(self.output['expected-profile.json']['event_sources']))
        a,pair=(r['events'] for r in records)
        self.assertEqual([(e['string'],e['fret'],e['finger'],e['midi'],e['spelling']) for e in a],
                         [(e['string'],e['fret'],e['finger'],e['midi'],e['spelling']) for e in pair[:40]])
        self.assertEqual([e['onset_q'] for e in a],[list(c.Fraction(i,4).as_integer_ratio()) for i in range(40)])
        self.assertEqual([e['duration_q'] for e in pair],[[1,4]]*80)
        self.assertEqual((pair[39]['onset_q'],pair[40]['onset_q'],pair[-1]['onset_q']),
                         ([39,4],[11,1],[83,4]))
        self.assertEqual([(pair[i]['string'],pair[i]['fret'],pair[i]['midi']) for i in (0,39,40,79)],
                         [(1,5,45),(1,5,45),(1,6,46),(1,6,46)])
        self.assertEqual([(pair[i]['string'],pair[i]['fret'],pair[i]['midi']) for i in (19,20,59,60)],
                         [(3,7,57),(3,7,57),(3,8,58),(3,8,58)])
        self.assertEqual(sum(x['one_beat_release_after_first_cell'] for x in side['events'].values()),1)
        self.assertEqual(sum(x['frame_move_frets'] for x in side['events'].values()),1)
        for ids,count in zip(c.VARIANTS,(40,80)):
            for vid,start in zip(ids,('D','U')):
                expected=[start if i%2==0 else ('U' if start=='D' else 'D') for i in range(count)]
                self.assertEqual(side['variant_strokes'][vid],expected)
                self.assertEqual(expected[40] if count==80 else expected[0],start)
        self.assertTrue(all(r['runtime_eligible'] is False and r['rubric'] is None and
                            not r['control_scope']['whole_workbook_complete'] for r in records))
        self.assertTrue(all('fixed_bpm' not in r['timing'] for r in records))

    def test_provisional_identity_and_native_nonadmission(self):
        audit=json.loads((OUT/'identity-audit.json').read_text())
        self.assertEqual(audit['status'],'PASS'); self.assertFalse(audit['matches'])
        self.assertFalse(audit['canonical_reservation'])
        self.assertEqual(set(self.output['candidate-allocation.json']['records']),set(c.ITEMS))
        self.assertEqual(hashlib.sha256(NATIVE.read_bytes()).hexdigest(),NATIVE_SHA)
        report=json.loads((OUT/'native-report-r01.json').read_text())
        self.assertTrue(report['valid_reference']); self.assertFalse(report['curriculum_playback_authorized'])
        self.assertEqual((report['coverage']['observed_records'],report['coverage']['events'],
                          report['coverage']['variants'],report['coverage']['variant_event_memberships']),
                         (2,120,4,240))
        self.assertEqual([(x['code'],x['record']) for x in report['issues']],
                         [('MODEL_not_admitted',c.ITEMS[0]),('MODEL_not_admitted',c.ITEMS[1])])
        self.assertEqual(json.loads((OUT/'native-exit.json').read_text())['exit_code'],2)

    def test_generator_refusals_and_output_boundary(self):
        rows=c.source_facts()[2]; original=[[n for g in r['groups'] for n in g['notes']] for r in rows]
        contacts=[original[0],original[0]+original[1]]
        altered=copy.deepcopy(contacts); altered[1][40]['fret']=7
        cases=[({'changed_contacts':altered},'CANDIDATE_CONTACT_DRIFT'),
               ({'changed_onsets':[[[0,1]]*40,[[0,1]]*80]},'CANDIDATE_TIMING_DRIFT'),
               ({'changed_durations':[[[1,3]]*40,[[1,3]]*80]},'CANDIDATE_DURATION_DRIFT'),
               ({'changed_route':[['A'],['A','B']]},'CANDIDATE_ROUTE_DRIFT'),
               ({'changed_strokes':{c.VARIANTS[0][0]:['D']*40}},'CANDIDATE_STROKE_DRIFT'),
               ({'forced_bpm':60},'FIXED_BPM_UNAUTHORIZED'),
               ({'force_eligible':True},'FORCED_ELIGIBILITY'),
               ({'reserved_item':'fg:item:999999'},'FOREIGN_ID')]
        for kwargs,code in cases:
            with self.subTest(code=code),self.assertRaisesRegex(c.CandidateError,code): c.derive(**kwargs)
        cmd=[PYTHON,'-B',str(c.ROOT/'Tools/parallel59_level016_first_batch.py')]
        self.assertEqual(subprocess.run(cmd+['verify'],capture_output=True).returncode,0)
        run=subprocess.run(cmd+['build'],capture_output=True,text=True)
        self.assertNotEqual(run.returncode,0); self.assertIn('OUTPUT_EXISTS',run.stderr)
        run=subprocess.run(cmd+['build','--out','Build/parallel-59/escape'],capture_output=True,text=True)
        self.assertNotEqual(run.returncode,0); self.assertIn('OUTPUT_SCOPE',run.stderr)

    def test_native_causal_refusals(self):
        expected={'pitch':'MODEL_pitch_position','string':'RECORD_FIDELITY','fret':'RECORD_FIDELITY',
                  'finger':'RECORD_FIDELITY','degree':'RECORD_FIDELITY','tempo':'UNKNOWN_FIELD',
                  'onset':'RECORD_FIDELITY','duration':'RECORD_FIDELITY','group_boundary':'RECORD_FIDELITY',
                  'pause':'RECORD_FIDELITY','route':'RECORD_FIDELITY','source':'SOURCE_HASH',
                  'identity':'RECORD_IDENTITY','forced_eligibility':'RUNTIME_NOT_ADMITTED',
                  'variant_pick':'RECORD_FIDELITY'}
        fixtures={}
        for name,required in expected.items():
            package=copy.deepcopy(self.output['package.json']); record=package['records'][1]; event=record['events'][40]
            if name=='pitch': event['midi']+=1
            elif name=='string': event['string']=5
            elif name=='fret': event['fret']=7
            elif name=='finger': event['finger']=4
            elif name=='degree': event['degree_contexts']['Bb-major']['ordinal']=2
            elif name=='tempo': record['timing']['fixed_bpm']=120
            elif name=='onset': event['onset_q']=[12,1]
            elif name=='duration': event['duration_q']=[1,3]
            elif name=='group_boundary': record['events'][3]['onset_q']=[2,1]
            elif name=='pause': event['onset_q']=[10,1]
            elif name=='route': record['context']['route']='A to B instead of Bb'
            elif name=='source': package['sources']['L16-TXT-RUNG02']['sha256']='0'*64
            elif name=='identity': record['id']='fg:item:999999'
            elif name=='forced_eligibility': record['runtime_eligible']=True
            elif name=='variant_pick': record['variants'][0]['pick_start']='U'
            data=c.encode(package); pp=OUT/f'negative-{name}-package.json'
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

if __name__=='__main__': unittest.main()
