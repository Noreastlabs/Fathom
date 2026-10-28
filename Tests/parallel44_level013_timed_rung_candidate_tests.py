"""Focused source, timing, native and refusal checks for the P44 Level13 packet."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Tools'))
import parallel44_level013_timed_rung_candidate as candidate

OUT = candidate.ROOT / candidate.OUT
NATIVE = candidate.ROOT / 'Build/parallel-13/four-shard-source-bundle-r01/bundle/bin/fathom_content_validate'
NATIVE_SHA = 'a85c1b25d8cded12cbe273e4620bd5f33a711d06311d29583a0fdbed7748f714'
PYTHON = sys.executable


class TimedRungCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = candidate.derive()

    def test_source_parity_and_nominal_two_cell_timing(self):
        records = self.output['package.json']['records']
        self.assertEqual([len(r['events']) for r in records], [30, 60])
        self.assertEqual([r['context']['local_code'] for r in records],
                         ['L013-R01:A:EVEN_EIGHTH',
                          'L013-R01-R02:A_BB:EVEN_EIGHTH_ONE_BEAT_PAUSE'])
        self.assertIn('excerpt of neighbor-stage', records[0]['title'])
        self.assertIn('first-mastery stage itself does not specify a separate rhythm',
                      records[0]['ambiguities'][0])
        first = records[0]['events']
        pair = records[1]['events']
        self.assertEqual([(e['string'], e['fret'], e['finger'], e['midi'], e['spelling'])
                          for e in first],
                         [(e['string'], e['fret'], e['finger'], e['midi'], e['spelling'])
                          for e in pair[:30]])
        self.assertEqual([e['onset_q'] for e in first],
                         [list(candidate.Fraction(i, 2).as_integer_ratio()) for i in range(30)])
        self.assertEqual([e['duration_q'] for e in pair], [[1, 2]] * 60)
        self.assertEqual((pair[28]['onset_q'], pair[29]['onset_q'], pair[30]['onset_q'],
                          pair[-1]['onset_q']),
                         ([14, 1], [29, 2], [16, 1], [61, 2]))
        self.assertEqual(pair[14]['midi'], pair[15]['midi'])
        self.assertEqual(pair[44]['midi'], pair[45]['midi'])
        self.assertEqual([(pair[i]['string'], pair[i]['fret'], pair[i]['midi'])
                          for i in (0, 29, 30, 59)],
                         [(1, 5, 45), (1, 5, 45), (1, 6, 46), (1, 6, 46)])
        self.assertTrue(all(r['runtime_eligible'] is False and r['rubric'] is None and
                            not r['control_scope']['whole_workbook_complete'] for r in records))
        self.assertTrue(all('fixed_bpm' not in r['context'] for r in records))
        self.assertEqual(self.output['expected-profile.json']['degree_roots']['A-major']['root_pitch_class'], 9)
        self.assertEqual(self.output['expected-profile.json']['degree_roots']['Bb-major']['root_pitch_class'], 10)

    def test_source_event_provenance_and_strokes(self):
        package = self.output['package.json']
        sidecar = self.output['source-provenance.json']
        ids = {e['event_id'] for r in package['records'] for e in r['events']}
        self.assertEqual(len(ids), 90)
        self.assertEqual(ids, set(sidecar['events']))
        self.assertEqual(ids, set(self.output['expected-profile.json']['event_sources']))
        self.assertEqual(len({e['source_local_event_key'] for e in sidecar['events'].values()}), 90)
        self.assertEqual(sum(e['one_beat_pause_after_first_cell'] for e in sidecar['events'].values()), 1)
        self.assertEqual(sum(e['whole_frame_move_fret'] for e in sidecar['events'].values()), 1)
        self.assertEqual([e['source_rung'] for e in list(sidecar['events'].values())[30:]],
                         [1]*30 + [2]*30)
        for pair, n in zip(candidate.VARIANTS, (30, 60)):
            for variant, first in zip(pair, ('D', 'U')):
                strokes = sidecar['variant_strokes'][variant]
                self.assertEqual(len(strokes), n)
                self.assertEqual(strokes[0], first)
                self.assertEqual(strokes[14:17], ([first, 'U' if first == 'D' else 'D', first]))
                if n == 60:
                    self.assertEqual(strokes[28:32], [first, 'U' if first == 'D' else 'D',
                                                      first, 'U' if first == 'D' else 'D'])
        self.assertEqual(package['sources']['L13-TXT-RUNG01-52-63']['first_line'], 52)
        self.assertEqual(package['sources']['L13-TXT-RUNG02-66-77']['first_line'], 66)
        self.assertEqual(package['sources']['L13-PDF-CARDS-P3']['page'], 3)

    def test_provisional_identity_and_native_nonadmission(self):
        audit = json.loads((OUT / 'identity-audit.json').read_text())
        self.assertEqual(audit['status'], 'PASS')
        self.assertFalse(audit['matches'])
        self.assertFalse(audit['canonical_reservation'])
        self.assertEqual(set(self.output['candidate-allocation.json']['records']), set(candidate.ITEMS))
        self.assertEqual(self.output['expected-profile.json']['reference_package'],
                         self.output['package.json'])
        self.assertEqual(hashlib.sha256(NATIVE.read_bytes()).hexdigest(), NATIVE_SHA)
        report = json.loads((OUT / 'native-report.json').read_text())
        self.assertEqual(report['exit_code'], 2)
        self.assertTrue(report['valid_reference'])
        self.assertFalse(report['curriculum_playback_authorized'])
        self.assertEqual((report['coverage']['observed_records'], report['coverage']['events'],
                          report['coverage']['variants'], report['coverage']['variant_event_memberships']),
                         (2, 90, 4, 180))
        self.assertEqual([(i['code'], i['record']) for i in report['issues']],
                         [('MODEL_not_admitted', candidate.ITEMS[0]),
                          ('MODEL_not_admitted', candidate.ITEMS[1])])

    def test_derivation_refuses_source_pitch_timing_route_tempo_and_eligibility(self):
        original = candidate.TXT_SHA
        try:
            candidate.TXT_SHA = '0' * 64
            with self.assertRaisesRegex(candidate.CandidateError, 'TXT_PIN_DRIFT'):
                candidate.derive()
        finally:
            candidate.TXT_SHA = original
        contacts = [r['notes'] for r in candidate.source_facts()[2]]
        selected = [contacts[0], contacts[0] + contacts[1]]
        altered = copy.deepcopy(selected); altered[1][30]['fret'] = 7
        cases = [({'changed_contacts': altered}, 'CANDIDATE_CONTACT_DRIFT'),
                 ({'changed_onsets': [[[0,1]]*30, [[0,1]]*60]}, 'CANDIDATE_TIMING_DRIFT'),
                 ({'changed_durations': [[[1,4]]*30, [[1,4]]*60]}, 'CANDIDATE_DURATION_DRIFT'),
                 ({'changed_route': [['A'], ['A','B']]}, 'CANDIDATE_ROUTE_DRIFT'),
                 ({'changed_strokes': {candidate.VARIANTS[0][0]: ['D']*30}}, 'CANDIDATE_STROKE_DRIFT'),
                 ({'forced_bpm': 100}, 'FIXED_BPM_UNAUTHORIZED'),
                 ({'force_eligible': True}, 'FORCED_ELIGIBILITY'),
                 ({'reserved_item': 'fg:item:999999'}, 'FOREIGN_ID')]
        for kwargs, code in cases:
            with self.subTest(code=code), self.assertRaisesRegex(candidate.CandidateError, code):
                candidate.derive(**kwargs)

    def test_frozen_native_negative_fixtures(self):
        expected = {'pitch': 'MODEL_pitch_position', 'string': 'RECORD_FIDELITY',
                    'fret': 'RECORD_FIDELITY', 'finger': 'RECORD_FIDELITY',
                    'degree': 'RECORD_FIDELITY', 'tempo': 'UNKNOWN_FIELD',
                    'onset': 'RECORD_FIDELITY', 'duration': 'RECORD_FIDELITY',
                    'route': 'RECORD_FIDELITY', 'source': 'SOURCE_HASH',
                    'identity': 'RECORD_IDENTITY', 'forced_eligibility': 'RUNTIME_NOT_ADMITTED'}
        fixtures = {}
        for name, required in expected.items():
            altered = copy.deepcopy(self.output['package.json'])
            record = altered['records'][1]
            event = record['events'][30]
            if name == 'pitch': event['midi'] += 1
            elif name == 'string': event['string'] = 5
            elif name == 'fret': event['fret'] = 7
            elif name == 'finger': event['finger'] = 4
            elif name == 'degree': event['degree_contexts']['Bb-major']['ordinal'] = 2
            elif name == 'tempo': record['timing']['fixed_bpm'] = 120
            elif name == 'onset': event['onset_q'] = [15, 1]
            elif name == 'duration': event['duration_q'] = [1, 4]
            elif name == 'route': record['context']['route'] = 'A to B instead of Bb'
            elif name == 'source': altered['sources']['L13-TXT-RUNG02-66-77']['sha256'] = '0'*64
            elif name == 'identity': record['id'] = 'fg:item:999999'
            elif name == 'forced_eligibility': record['runtime_eligible'] = True
            package_path = OUT / f'negative-{name}-package.json'
            data = candidate.encode(altered)
            if package_path.exists():
                self.assertEqual(package_path.read_bytes(), data)
            else:
                package_path.write_bytes(data)
            suffix = 1
            while (OUT / f'negative-{name}-report-r{suffix:02d}.json').exists():
                suffix += 1
            report_path = OUT / f'negative-{name}-report-r{suffix:02d}.json'
            profile = OUT / 'expected-profile.json'
            cmd = [str(NATIVE), '--package', str(package_path),
                   '--registry', str(OUT/'identity-registry.json'), '--profile', str(profile),
                   '--profile-sha256', hashlib.sha256(profile.read_bytes()).hexdigest(),
                   '--source-root', str(candidate.ROOT), '--report', str(report_path)]
            run = subprocess.run(cmd, capture_output=True, text=True)
            report = json.loads(report_path.read_text())
            self.assertEqual(run.returncode, 1, (name, run.stdout, run.stderr))
            self.assertFalse(report['valid_reference'], name)
            codes = [issue['code'] for issue in report['issues']]
            self.assertIn(required, codes, (name, codes))
            fixtures[name] = {'exit_code': run.returncode, 'required_code': required,
                              'issue_codes': codes,
                              'package_sha256': hashlib.sha256(data).hexdigest(),
                              'report_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest()}
        (OUT/'negative-checks.json').write_bytes(candidate.encode(fixtures))

    def test_written_bytes_and_boundary(self):
        command = [PYTHON, str(candidate.ROOT/'Tools/parallel44_level013_timed_rung_candidate.py')]
        verify = subprocess.run(command+['verify'], capture_output=True, text=True)
        self.assertEqual(verify.returncode, 0, verify.stderr)
        build = subprocess.run(command+['build'], capture_output=True, text=True)
        self.assertNotEqual(build.returncode, 0)
        self.assertIn('OUTPUT_EXISTS', build.stderr)
        escape = subprocess.run(command+['build', '--out', 'Build/parallel-44/escape'],
                                capture_output=True, text=True)
        self.assertNotEqual(escape.returncode, 0)
        self.assertIn('OUTPUT_SCOPE', escape.stderr)


if __name__ == '__main__':
    unittest.main()
