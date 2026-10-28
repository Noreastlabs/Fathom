"""P78 original Level20 source, learning-time, projection and refusal checks."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'Tools'))
import parallel78_level020_first_circuit as c

OUT = c.ROOT/c.OUT
NATIVE = c.ROOT/c.NATIVE

def native(package, profile, report):
    if report.exists():
        raise AssertionError(f'refusing to overwrite native evidence: {report}')
    run = subprocess.run([str(NATIVE), '--package', str(package),
                          '--registry', str(OUT/'identity-registry.json'),
                          '--profile', str(profile),
                          '--profile-sha256', hashlib.sha256(profile.read_bytes()).hexdigest(),
                          '--source-root', str(c.ROOT), '--report', str(report)],
                         capture_output=True, text=True)
    return run, json.loads(report.read_text())

class Level20FirstCircuitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = c.derive()

    def test_original_five_cards_and_p05_p12_parity(self):
        lines,pages,modules,proposal = c.source_facts()
        self.assertEqual(len(pages),31)
        self.assertEqual([m['contact_count'] for m in modules],list(c.MODULE_COUNTS))
        self.assertEqual([m['pdf_page'] for m in modules],[3,3,3,4,4])
        self.assertIn('Learning mode: one note per metronome click through the complete circuit.',lines)
        self.assertIn('LEARNING MODE',pages[1])
        self.assertTrue(any('one note per click' in row.lower() for row in pages[1]))
        self.assertTrue(any('Remove the pauses' in row for row in pages[0]))
        self.assertEqual([p['schema1_fields']['context']['circuit_contact_ordinals']
                          for p in proposal],[[1,30],[31,108],[109,204],[205,256],[257,322]])
        for module in modules:
            for row in module['source_rows']:
                self.assertEqual(lines[row['txt_line']-1],row['printed_row'])
                self.assertIn(row['printed_row'],pages[module['pdf_page']-1])

    def test_all_322_source_contacts_learning_time_and_harmony(self):
        events=self.output['package.json']['records'][0]['events']
        provenance=self.output['source-provenance.json']['events']
        self.assertEqual(len(events),322)
        self.assertEqual(len(provenance),322)
        self.assertEqual(set(provenance),set(self.output['expected-profile.json']['event_sources']))
        _,_,modules,_=c.source_facts()
        for index,event in enumerate(events):
            ordinal=index+1
            midx=next(k for k in range(5) if ordinal<=c.BOUNDARIES[k+1])
            local=ordinal-c.BOUNDARIES[midx]
            source=modules[midx]['contacts'][local-1]
            side=provenance[event['event_id']]
            self.assertEqual(event['event_id'],f'{c.ITEM}:event:{ordinal:04d}')
            self.assertEqual((event['string'],event['fret'],event['finger'],event['midi'],
                              event['spelling']),
                             (c.STRINGS[source['string']],source['fret'],source['printed_finger'],
                              c.OPEN_MIDI[source['string']]+source['fret'],source['printed_note_spelling']))
            self.assertEqual(event['degree_contexts']['A-major']['ordinal'],source['printed_degree'])
            self.assertEqual(event['degree_contexts']['A-major']['source_label'],str(source['printed_degree']))
            self.assertEqual((event['onset_q'],event['duration_q']),([index,1],[1,1]))
            self.assertEqual((side['source_module'],side['source_module_contact'],
                              side['source_circuit_contact']), (midx+1,local,ordinal))
            self.assertEqual(side['source_txt_lines'],source['source_refs'])
            self.assertEqual(side['printed_interval_or_harmony'],source['printed_interval_or_harmony'])
            self.assertEqual(side['scale_step'],source['scale_step'])
            self.assertEqual(side['nominal_slot_q'],[index,1])
        for idx in (30,108,204,256):
            self.assertEqual((events[idx-1]['string'],events[idx-1]['fret']),
                             (events[idx]['string'],events[idx]['fret']))
            self.assertEqual(events[idx]['onset_q'],[idx,1])
            self.assertTrue(provenance[events[idx]['event_id']]['rearticulated_module_root'])
            self.assertTrue(provenance[events[idx]['event_id']]['same_root_as_previous_contact'])
        self.assertEqual((events[14]['string'],events[14]['fret']),
                         (events[15]['string'],events[15]['fret']))
        self.assertNotEqual(events[14]['event_id'],events[15]['event_id'])
        self.assertEqual(events[-1]['onset_q'],[321,1])
        self.assertEqual([provenance[e['event_id']]['printed_interval_or_harmony']
                          for e in events[204:206]],['M3','M3'])
        self.assertEqual([provenance[e['event_id']]['printed_interval_or_harmony']
                          for e in events[256:259]],['I']*3)

    def test_nonadmission_and_continuous_two_pick_variants(self):
        record=self.output['package.json']['records'][0]
        side=self.output['source-provenance.json']
        self.assertFalse(record['runtime_eligible'])
        self.assertIsNone(record['rubric'])
        self.assertFalse(record['control_scope']['whole_workbook_complete'])
        self.assertNotIn('fixed_bpm',record['timing'])
        self.assertEqual(len(record['variants']),2)
        for variant,start in zip(record['variants'],('D','U')):
            self.assertEqual(variant['grouping']['kind'],'source_event_time')
            self.assertEqual(variant['pick_start'],start)
            expected=[start if i%2==0 else ('U' if start=='D' else 'D') for i in range(322)]
            self.assertEqual(side['variant_strokes'][variant['id']],expected)
            self.assertEqual([expected[i] for i in c.BOUNDARIES[:-1]],[start]*5)
        with self.assertRaisesRegex(c.CandidateError,'FORCED_ELIGIBILITY'):
            c.derive(force_eligible=True)
        with self.assertRaisesRegex(c.CandidateError,'FIXED_BPM_UNAUTHORIZED'):
            c.derive(forced_bpm=120)
        with self.assertRaisesRegex(c.CandidateError,'LEARNING_TIME_REQUIRED'):
            c.derive(grouping='even_subdivision')

    def test_frozen_native_644_memberships_and_no_playback(self):
        self.assertEqual(hashlib.sha256(NATIVE.read_bytes()).hexdigest(),c.NATIVE_SHA)
        report=json.loads((OUT/'native-report-r02.json').read_text())
        self.assertEqual(report['exit_code'],2)
        self.assertTrue(report['valid_reference'])
        self.assertFalse(report['curriculum_playback_authorized'])
        self.assertEqual((report['coverage']['observed_records'],report['coverage']['events'],
                          report['coverage']['variants'],
                          report['coverage']['variant_event_memberships']),(1,322,2,644))
        self.assertEqual([(x['code'],x['record']) for x in report['issues']],
                         [('MODEL_not_admitted',c.ITEM)])
        authored=self.output['package.json']['records'][0]['events']
        refs=self.output['expected-profile.json']['event_sources']
        for variant in report['variants']:
            projected=variant['model']['events']
            self.assertEqual(len(projected),322)
            self.assertFalse(variant['curriculum_playback_authorized'])
            for expected,actual in zip(authored,projected):
                self.assertEqual((actual['event_id'],actual['onset_q'],actual['duration_q'],
                                  actual['source_ref']),
                                 (expected['event_id'],expected['onset_q'],
                                  expected['duration_q'],refs[expected['event_id']]))
                self.assertEqual(actual['pick'],'')  # Later typed runtime binding remains P02-owned.

    def test_frozen_rebuild_output_scope_and_causal_native_refusals(self):
        cmd=[sys.executable,'-B',str(c.ROOT/'Tools/parallel78_level020_first_circuit.py')]
        self.assertEqual(subprocess.run(cmd+['verify'],capture_output=True).returncode,0)
        run=subprocess.run(cmd+['build'],capture_output=True,text=True)
        self.assertNotEqual(run.returncode,0)
        self.assertIn('OUTPUT_EXISTS',run.stderr)
        run=subprocess.run(cmd+['build','--out','Build/parallel-78/escape'],
                           capture_output=True,text=True)
        self.assertNotEqual(run.returncode,0)
        self.assertIn('OUTPUT_SCOPE',run.stderr)
        expected={'pitch':'MODEL_pitch_position','finger':'RECORD_FIDELITY',
                  'degree':'RECORD_FIDELITY','tempo':'UNKNOWN_FIELD',
                  'onset':'RECORD_FIDELITY','duration':'RECORD_FIDELITY',
                  'module_pause':'RECORD_FIDELITY','source':'SOURCE_HASH',
                  'identity':'RECORD_IDENTITY','forced_eligibility':'RUNTIME_NOT_ADMITTED',
                  'variant_pick':'RECORD_FIDELITY'}
        fixtures={}
        for name,required in expected.items():
            package=copy.deepcopy(self.output['package.json'])
            record=package['records'][0]
            event=record['events'][30]
            if name=='pitch':event['midi']+=1
            elif name=='finger':event['finger']=4
            elif name=='degree':event['degree_contexts']['A-major']['ordinal']=2
            elif name=='tempo':record['timing']['fixed_bpm']=120
            elif name=='onset':event['onset_q']=[32,1]
            elif name=='duration':event['duration_q']=[1,2]
            elif name=='module_pause':event['onset_q']=[31,1]
            elif name=='source':package['sources']['L20-TXT-A-MODULE2']['sha256']='0'*64
            elif name=='identity':record['id']='fg:item:999999'
            elif name=='forced_eligibility':record['runtime_eligible']=True
            elif name=='variant_pick':record['variants'][0]['pick_start']='U'
            data=c.encode(package)
            package_path=OUT/f'negative-{name}-package.json'
            package_path.write_bytes(data)
            report_path=OUT/f'negative-{name}-report.json'
            run,result=native(package_path,OUT/'expected-profile.json',report_path)
            self.assertEqual(run.returncode,1,(name,run.stdout,run.stderr))
            self.assertFalse(result['valid_reference'],name)
            codes=[issue['code'] for issue in result['issues']]
            self.assertIn(required,codes,(name,codes))
            fixtures[name]={'exit_code':run.returncode,'required_code':required,
                            'issue_codes':codes,
                            'package_sha256':hashlib.sha256(data).hexdigest(),
                            'report_sha256':hashlib.sha256(report_path.read_bytes()).hexdigest()}
        (OUT/'negative-checks.json').write_bytes(c.encode(fixtures))

if __name__ == '__main__':
    unittest.main()
