"""Source closure, program obligations and fail-closed export checks; no audio."""
from pathlib import Path
import copy,importlib.util,json,unittest

ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('manual_compiler',ROOT/'Tools/exercise-family-compiler/compile_manual_curriculum.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.rows,cls.closure,cls.metrics=m.build(ROOT);cls.expected=(cls.rows,cls.closure)
    def test_complete_exact_source_roundtrip(self):
        self.assertTrue(m.validate_bundle(self.rows,self.closure,expected=self.expected))
        self.assertEqual(len(self.rows),96);self.assertEqual(len(self.closure['program_counts']),18)
        selection=m.strict((ROOT/m.SELECTION).read_bytes());pins={x['path']:x for x in selection['cached_input_pins']};cache={}
        for row in self.rows:
            ref=row['payload_ref'];p=ref['path']
            if p not in cache:cache[p]=(ROOT/p).read_bytes().splitlines()
            raw=cache[p][ref['jsonl_line']-1]
            self.assertEqual(m.sha(raw),row['original_row_sha256']);self.assertEqual(m.strict(raw),row['original_record'])
            self.assertEqual(ref['sha256'],pins[p]['sha256']);self.assertFalse(row['program']['performance_observed']);self.assertFalse(row['program']['grants_credit'])
    def test_distinct_source_programs(self):
        by={r['program']['name']:r['program'] for r in self.rows}
        self.assertEqual(sum(x['hidden_self_check'] is not None for x in (r['program'] for r in self.rows)),48)
        for name in ('l055_written_analysis','l055_written_transposition','l056_written_analysis','l056_written_transposition'):
            p=by[name];self.assertEqual([s['action'] for s in p['steps']],['submit','reveal','compare']);self.assertIsNotNone(p['hidden_self_check'])
            self.assertNotIn('answer:',json.dumps([s['instruction'] for s in p['steps']]));self.assertNotIn('const',json.dumps(p['steps'][0]['schema']))
            self.assertNotIn('answer:',json.dumps(p['learner_instruction_context']));self.assertNotIn('Self-check key',json.dumps(p['learner_instruction_context']))
        self.assertEqual(len(by['l055_silent_spelling']['steps']),42);self.assertEqual(len(by['l056_silent_spelling']['steps']),48)
        self.assertEqual(len(by['l059_triad_atlas']['steps']),96)
        for name in ('l055_functional_hearing','l056_functional_hearing'):
            self.assertEqual(by[name]['source_facts']['relative_beats_per_chord'],4);self.assertEqual(sum(s['activates_release'] for s in by[name]['steps']),4)
        mechanics=by['l063_technique_mechanics'];self.assertEqual(mechanics['source_facts']['initial_work_seconds'],15);self.assertEqual(len(mechanics['source_facts']['stop_conditions']),4)
        self.assertTrue(any(c['kind']=='minimum' and c['value']==30 for s in by['l054_progression_mastery_audit']['steps'] for c in s['constraints']))
        self.assertTrue(any(c['kind']=='distinct_dates' for s in by['l057_progression_mastery_audit']['steps'] for c in s['constraints']))
        self.assertTrue(any(s['name']=='actual_recording_references' for s in by['l063_progression_mastery_audit']['steps']))
    def test_no_automatic_manual_inputs(self):
        for row in self.rows:
            for step in row['program']['steps']:
                self.assertNotIn('default',json.dumps(step['schema']));self.assertFalse(step['schema']['additionalProperties'])
                self.assertEqual(set(step['schema']['properties']),set(step['schema']['required']))
    def test_bundle_corruption_and_scope_mutants(self):
        mutants=[]
        a=copy.deepcopy(self.rows);a[0]['source_key']='foreign';mutants.append((a,self.closure))
        a=copy.deepcopy(self.rows);a[-1]=copy.deepcopy(a[0]);mutants.append((a,self.closure))
        a=copy.deepcopy(self.rows);a[0]['schema']='foreign';mutants.append((a,self.closure))
        a=copy.deepcopy(self.rows);del a[0]['original_record'];mutants.append((a,self.closure))
        a=copy.deepcopy(self.rows);a[0]['program']['steps'][0]['schema']['properties']['root_fret']['enum']=[99];a[0]['contract_sha256']=m.sha(m.encoded(a[0]['program']));c=copy.deepcopy(self.closure);c['contracts'][a[0]['source_key']]=a[0]['contract_sha256'];mutants.append((a,c))
        c=copy.deepcopy(self.closure);c['runtime_admitted']=True;mutants.append((self.rows,c))
        c=copy.deepcopy(self.closure);c['contexts'].pop(next(iter(c['contexts'])));mutants.append((self.rows,c))
        c=copy.deepcopy(self.closure);c['cached_inputs'][0]['path']='../../escape';mutants.append((self.rows,c))
        for rows,closure in mutants:
            with self.assertRaises(m.Refusal):m.validate_bundle(rows,closure,expected=self.expected)
    def test_strict_duplicate_nonfinite_input(self):
        for data in ('{"a":1,"a":2}','{"n":NaN}','{"n":Infinity}'):
            with self.assertRaises(m.Refusal):m.strict(data)

if __name__=='__main__':unittest.main()
