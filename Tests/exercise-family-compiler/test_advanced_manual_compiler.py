"""56-row roundtrip/invariants and five behavior strata through the family API.

Synthetic manual reports exercise software; they are not source listening,
learner performance, native integration or acceptance evidence.
"""
from copy import deepcopy
from pathlib import Path
import importlib.util
import json
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('advanced_manual_compiler',ROOT/'Tools/exercise-family-compiler/compile_advanced_manual.py')
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)


class AdvancedCompilerTests(unittest.TestCase):
    assertions = 0
    refusals = 0
    strata = set()
    all_rows_checked = 0
    @classmethod
    def setUpClass(cls):
        cls.family = c.FrozenFamilies(ROOT)

    def check(self, ok, label):
        self.assertTrue(ok,label)
        type(self).assertions += 1

    def refuse(self, fn, label, workflow=None):
        before = deepcopy(workflow._flow.__dict__) if workflow else None
        with self.assertRaises((ValueError,TypeError,KeyError),msg=label):
            fn()
        if workflow:
            self.check(workflow._flow.__dict__==before,label+' atomic refusal')
        type(self).refusals += 1

    def apply(self, flow, action, *args):
        return flow.apply(action,flow.capture(),*args)

    def top(self, key, midi=None):
        card = self.family.row(key)['contract']['source_card']
        pc = self.family.models[c.FIXED_TOP_MODEL].PC[card['literal_top']]
        midi = 72+pc if midi is None else midi
        contact = next(x for x in self.family.contacts(card['literal_top']) if x['midi']==midi)
        return {'key':key,'literal_top':card['literal_top'],'contact':contact,'original_workbook':True,'own_instrument':True}

    def voicing(self, flow):
        view = flow.view()
        top = {'key':view['key'],'literal_top':view['literal_top'],'contact':view['chosen_top'],'original_workbook':True,'own_instrument':True}
        candidates = self.family.voicings(view['key'],top,view['harmony'],view['stage'],1)
        self.check(bool(candidates),'finite explicitly chosen fixture realization')
        return candidates[0]

    def fixed_report(self, flow, melody='yes'):
        view = flow.view()
        return {'key':view['key'],'harmony':view['harmony'],'stage':view['stage'],'contacts':deepcopy(view['chosen_plan']['contacts']),
          'attack_counts':[1]*len(view['chosen_plan']['contacts']),
          'duties':{n:melody if n=='melody_clear' else 'yes' for n in flow._flow.duties()},
          'diagnosis':'' if melody=='yes' else 'Synthetic melody loss; immediate source reduction required.',
          'notes':'Synthetic manual report; no hearing/performance observation.'}

    def fixed_step(self, flow, melody='yes'):
        self.apply(flow,'sing_top',{'sung_before_voicing':'yes','notes':'Synthetic source duty.'})
        self.apply(flow,'choose_voicing',self.voicing(flow))
        self.apply(flow,'name_role',{'role':flow._flow.expected_role(),'notes':'Symbolic fixture; source role remains literal.'})
        self.apply(flow,'play',True)
        self.apply(flow,'release',{'learner_released':True})
        self.apply(flow,'report',self.fixed_report(flow,melody))
        if melody=='yes':
            self.apply(flow,'advance')

    def fixed_finish(self, flow):
        count = 0
        while flow.snapshot()['state']!='audit':
            if flow.snapshot()['state']=='need_additional':
                key = flow.view()['key']
                extra = self.family.allowed_choices(key)['additional_siblings'][0]
                self.apply(flow,'choose_additional',{'key':key,'harmony':extra,'rationale':'Chosen source-sibling fixture, no new identity.'})
            self.fixed_step(flow)
            count += 1
        self.apply(flow,'audit',{'answers':{q:'Manual judgment fixture; not verified audibly.' for q in self.family.row(flow.view()['key'])['contract']['audit_questions']},
                                'notes':'Synthetic audit.','diagnosis':''})
        self.apply(flow,'finish')
        return count

    def test_all56_exact_roundtrip_and_allrow_invariants(self):
        f = self.family
        payloads = f.payloads()
        self.check(payloads==f.payloads(),'deterministic repeat export in memory')
        rows = [c.strict_json(raw) for raw in payloads['definitions.jsonl'].splitlines()]
        closure = c.strict_json(payloads['family-closure.json'])
        f.validate_bundle(rows,closure)
        exported = ROOT/c.OUTPUT
        if exported.exists():
            self.check((exported/'definitions.jsonl').read_bytes()==payloads['definitions.jsonl'] and (exported/'family-closure.json').read_bytes()==payloads['family-closure.json'],'saved generated payloads match deterministic fresh in-memory roundtrip')
        self.check(len(rows)==56 and closure['recipe_counts']=={'chord_tone_transfer':14,'full_reconstruction':1,'fixed_top_reduction':41},'closed56=14+1+41')
        self.check(len(f.source_pins)==4,'four original source pins hashed once by compiler cache')
        for row in rows:
            f.validate_row(row)
            self.check(c.encoded(row)==c.encoded(f.row(row['source_key'])),'lossless current contract row/order')
            self.check(c.digest(row['contract'])==row['contract_sha256'],'all-row contract hash')
            packet = c.strict_json(f.cache[row['packet']['path']].splitlines()[row['packet']['jsonl_line']-1])
            self.check(c.digest(packet)==row['record_sha256'],'all-row frozen record hash')
            original_raw = f.cache[row['original_record']['path']].splitlines(keepends=True)[row['original_record']['jsonl_line']-1]
            self.check(c.hashlib.sha256(original_raw).hexdigest()==row['original_record']['raw_line_sha256'],'all-row original raw-line hash')
            self.check(c.digest(c.strict_json(original_raw))==row['original_record']['record_sha256'],'all-row original decoded record hash')
            self.check(c.digest(closure['contexts'][row['context_ref']],sort=True)==row['context_ref'],'shared operational context hash')
            w = f.new_workflow(row['source_key'])
            self.check(w.view()['key']==row['source_key'],'exact workflow binding')
            self.refuse(lambda:w.apply('finish',w.capture()),'early finish',w)
            if row['recipe']=='fixed_top_reduction':
                top = self.top(row['source_key'])
                f.validate_choice(row['source_key'],'top',top)
                for stage in f.models[c.FIXED_TOP_MODEL].STAGES:
                    choices = f.voicings(row['source_key'],top,row['contract']['source_card']['source_harmonies'][0],stage,1)
                    self.check(len(choices)==1,'all fixed-top source texture realizations')
                    f.validate_choice(row['source_key'],'voicing',{'top':top,'plan':choices[0]})
            else:
                view = w.view()
                self.check('reference_pitch' not in view and 'source_reference' not in view and 'visible_source_reference' not in view,'no hidden reference in initial learner view')
                domain = f.allowed_choices(row['source_key'])
                self.check(domain['default_choice'] is None and len(domain['contacts'])==150,'full chosen contact domain, no default answer')
            type(self).all_rows_checked += 1

    def test_bad_schema_key_scope_drift_and_choices(self):
        f = self.family
        row = f.row(f.keys[0])
        self.refuse(lambda:f.row('foreign/new/key'),'foreign source key')
        self.refuse(lambda:f.row(True),'boolean source key')
        for mutation in ('schema','contract','hash','missing','extra','range'):
            wrong = deepcopy(row)
            if mutation=='schema':wrong['schema']='unknown.2'
            elif mutation=='contract':wrong['contract']['source_fields']['Role']='unknown'
            elif mutation=='hash':wrong['contract_sha256']='0'*64
            elif mutation=='missing':wrong.pop('context_ref')
            elif mutation=='extra':wrong['new_key']='invented'
            else:wrong['packet']['jsonl_line']=0
            self.refuse(lambda wrong=wrong:f.validate_row(wrong),'definition '+mutation)
        self.refuse(lambda:f.validate_bundle(f.rows[:-1],f.closure()),'missing row')
        self.refuse(lambda:f.validate_bundle([f.rows[0]]*56,f.closure()),'duplicate closed source key')
        wrongclosure = f.closure();wrongclosure['shared_behavior_descriptors']['fixed_top_reduction'].pop('mandatory_reduction')
        self.refuse(lambda:f.validate_bundle(f.rows,wrongclosure),'missing recovery descriptor')
        self.refuse(lambda:c.strict_json('{"x":1,"x":2}'),'duplicate JSON field')
        self.refuse(lambda:c.strict_json('{"x":NaN}'),'nonfinite JSON')
        original_read = Path.read_bytes
        def drift(file):
            raw = original_read(file)
            return raw+b' ' if str(file)==str(ROOT/c.TRANSFER_MODEL) else raw
        with patch.object(Path,'read_bytes',drift):
            self.refuse(lambda:c.FrozenFamilies(ROOT),'immutable model hash drift')
        k = f.keys[15]
        top = self.top(k);bad = deepcopy(top);bad['contact']['fret']=True
        self.refuse(lambda:f.validate_choice(k,'top',bad),'boolean contact fret')
        self.refuse(lambda:f.voicings(k,top,'foreign harmony','melody'),'foreign harmony')
        self.refuse(lambda:f.voicings(k,top,'Cmaj7','invented stage'),'unknown texture')
        self.refuse(lambda:f.voicings(k,top,'Cmaj7','melody',True),'boolean range limit')
        flow = f.new_workflow(k)
        self.refuse(lambda:flow.apply('__dict__',flow.capture()),'non-action attribute')
        self.refuse(lambda:flow.apply('set_top',flow.capture(),top,'extra'),'action arity',flow)
        self.refuse(lambda:flow.apply('set_top',('foreign owner',),top),'foreign owner',flow)
        old = flow.capture();self.apply(flow,'set_top',top)
        self.refuse(lambda:flow.apply('sing_top',old,{'sung_before_voicing':'yes','notes':'Synthetic.'}),'stale owner',flow)

    def test_transfer_all14_two_sets_hidden_reveal_and_schema(self):
        f = self.family
        for key in f.keys[:14]:
            row = f.row(key);contract = row['contract'];flow = f.new_workflow(key)
            type(self).strata.add('transfer '+row['behavior_stratum'])
            plan = {'prerequisites':{'original_workbook':True,'own_instrument':True},
                    'cue_provider':{'kind':'external_human','reference':'Synthetic human cue fixture; no actual hearing.','ready':True}}
            f.validate_choice(key,'plan',plan)
            self.apply(flow,'set_plan',plan)
            chord,role,name = (contract['source_fields'][k] for k in ('Chord','Role','Pitch'))
            name = name.split(' / ')[0]
            pc = f.models[c.TRANSFER_MODEL].PC[name]
            contact1 = {'string':'B','fret':1+pc,'midi':60+pc}
            contact2 = {'string':'e','fret':8+pc,'midi':72+pc}
            arrangement = {'string_set_1':{'strings':['B'],'target':contact1,'voicing':[contact1]},
                           'string_set_2':{'strings':['e'],'target':contact2,'voicing':[contact2]}}
            f.validate_choice(key,'arrangements',arrangement)
            bad = deepcopy(arrangement);bad['string_set_2']=deepcopy(bad['string_set_1'])
            self.refuse(lambda:f.validate_choice(key,'arrangements',bad),'duplicate chosen string set')
            for stage in range(2):
                self.apply(flow,'begin',{'key':key,'chord':chord,'role':role,'ready':True}) if stage==0 else self.apply(flow,'begin')
                if stage==0:
                    self.apply(flow,'heard',{'heard_chord_and_role':'yes'})
                    self.apply(flow,'sung_name',{'pitch_name':name,'singing_attempted':True})
                    self.apply(flow,'choose_arrangements',arrangement)
                    self.check('reference_pitch' not in flow.view(),'reference hidden before playing')
                    self.refuse(lambda:self.apply(flow,'reveal'),'pre-attack reveal',flow)
                self.apply(flow,'setup_target',True);self.apply(flow,'attack',True)
                self.refuse(lambda:self.apply(flow,'report',{}),'report before release',flow)
                self.apply(flow,'release',True)
                if stage==0:
                    self.apply(flow,'reveal')
                    self.check(flow.view()['reference_pitch']==contract['source_fields']['Pitch'],'literal reference revealed after release')
                m = f.models[c.TRANSFER_MODEL]
                target = contact1 if stage==0 else contact2
                self.apply(flow,'report',{'key':key,'chord':chord,'role':role,'string_set':m.SETS[stage],'target':target,
                    'named_pitch':name,'attack_count':1,'common':{n:'yes' for n in m.COMMON},
                    'stage_duties':{'sung_pitch_correct':'yes'} if stage==0 else {n:'yes' for n in m.TRANSFER},
                    'response_speed':'uncertain','diagnosis':'','notes':'Synthetic manual report; no actual observation.'})
                self.apply(flow,'next_set') if stage==0 else self.apply(flow,'finish')
            self.check(flow.snapshot()['state']=='completed' and not flow.snapshot()['credit_awarded'],'all14 complete two-set manual flow, no credit')

    def test_full_reconstruction_64_uniform_targets_scores_and_terminal_retry(self):
        f = self.family;key = f.keys[14];row=f.row(key);m=f.models[c.RECONSTRUCTION_MODEL];flow=f.new_workflow(key)
        type(self).strata.add('reconstruction whole16bars64targets')
        plan = {'prerequisites':{'original_workbook':True,'own_instrument':True},
                'recording':{'kind':'external_recording','reference':'Synthetic external-recording reference fixture.','declared_sha256':None,'ready':True},
                'source_declarations':{'recorded_once':'yes','transcriber_did_not_study_source_card':'yes'}}
        f.validate_choice(key,'source',plan);self.apply(flow,'set_source',plan)
        for name in m.PASSES:
            self.apply(flow,'begin_written',{'key':key,'pass':name,'recording_reference':plan['recording']['reference'],'ready':True})
            self.apply(flow,'heard',{'heard_source':'yes'});self.apply(flow,'request_stop');self.apply(flow,'release',{'learner_released':True,'external_source_stopped':True})
            bars = [r['pitches'] for r in row['contract']['source_bars']] if name=='exact_notes' else (
                    [{'chord':r['chord'],'function':'Manual function fixture.'} for r in row['contract']['source_bars']] if name=='chord_function' else ['Manual response fixture.']*16)
            if name=='contour':bars[0]=None
            response = {'bars':bars,'notes':'Synthetic written learner fixture, not a copied observed answer.'}
            f.validate_choice(key,'written',{'pass':name,'response':response});self.apply(flow,'commit_written',response);self.apply(flow,'next_written')
        names = [n for r in row['contract']['source_bars'] for n in r['pitches']]
        first = [{'string':'B','fret':1+m.PC[n],'midi':60+m.PC[n]} for n in names]
        second = [{'string':'B','fret':13+m.PC[n],'midi':72+m.PC[n]} for n in names]
        firstplan = {'position':{'minimum_fret':0,'maximum_fret':12,'rationale':'Explicit synthetic authored position.'},'contacts':first,'source_scope_ack':True}
        secondplan = {'position':{'minimum_fret':12,'maximum_fret':24,'rationale':'Chosen uniform upper octave.'},'contacts':second,'source_scope_ack':True,'octave_shift_semitones':12}
        f.validate_choice(key,'first_position',{'plan':firstplan,'written_pitch_names':names})
        malformed_names = list(names);malformed_names[0] = True
        self.refuse(lambda:f.validate_choice(key,'first_position',{'plan':firstplan,'written_pitch_names':malformed_names}),'boolean written pitch')
        missing_position = deepcopy(firstplan);missing_position['position'].pop('rationale')
        self.refuse(lambda:f.validate_choice(key,'first_position',{'plan':missing_position,'written_pitch_names':names}),'missing position rationale')
        f.validate_choice(key,'second_position',{'plan':secondplan,'written_pitch_names':names,'first_contacts':first})
        wrong = deepcopy(secondplan);wrong['contacts'][0]=first[0]
        self.refuse(lambda:f.validate_choice(key,'second_position',{'plan':wrong,'written_pitch_names':names,'first_contacts':first}),'nonuniform octave target')
        short = deepcopy(firstplan);short['contacts'].pop()
        self.refuse(lambda:f.validate_choice(key,'first_position',{'plan':short,'written_pitch_names':names}),'missing64 target')
        self.apply(flow,'choose_first_position',firstplan)
        self.refuse(lambda:self.apply(flow,'reveal_source'),'early first-register reveal',flow)
        for register in range(2):
            for bar in range(16):
                self.apply(flow,'sung_bar',True);self.apply(flow,'play_bar',True);self.apply(flow,'release',{'learner_released':True,'external_source_stopped':True})
                contacts = (first if register==0 else second)[bar*4:bar*4+4]
                self.apply(flow,'report_bar',{'key':key,'bar':bar+1,'contacts':contacts,'sing_count':1,'attack_counts':[1,1,1,1],
                     'common':{n:'yes' for n in m.COMMON},'diagnosis':'','notes':'Synthetic manual bar report.'})
                self.apply(flow,'next_bar')
            if register==0:
                self.check('source_reference' not in flow.view(),'reference hidden through all first16 bars')
                self.apply(flow,'reveal_source');self.check(len(flow.view()['source_reference'])==16,'complete16 source revealed')
                self.apply(flow,'begin_second_register',secondplan)
        scores = {b:{'hearing_accuracy':0,'first_attack_fretboard_accuracy':0} for b in m.BLOCKS}
        bad = deepcopy(scores);bad['13-16']['hearing_accuracy']=True
        self.refuse(lambda:self.apply(flow,'declare_scores',bad),'boolean score',flow)
        out_of_range = deepcopy(scores);out_of_range['1-4']['hearing_accuracy'] = 3
        self.refuse(lambda:self.apply(flow,'declare_scores',out_of_range),'score outside0-2',flow)
        incomplete = deepcopy(scores);incomplete.pop('13-16')
        self.refuse(lambda:self.apply(flow,'declare_scores',incomplete),'missing score block',flow)
        unknown = deepcopy(scores);unknown['9-12']['hearing_accuracy'] = None
        self.apply(flow,'declare_scores',unknown)
        self.check(flow._flow.score_declarations['9-12']['hearing_accuracy'] is None and flow.snapshot()['state']=='both_registers_reported','unknown score retained, no invented value')
        self.apply(flow,'declare_scores',scores)
        self.refuse(lambda:self.apply(flow,'finish'),'unknown written contour terminal cannot finish',flow)
        old_history = deepcopy(flow.snapshot()['history']);self.apply(flow,'restart_written','Diagnosed missing contour; prior reveal and response history retained.')
        self.check(flow.snapshot()['state']=='ready_written' and flow.snapshot()['history'][:len(old_history)]==old_history and 'source_reference' in flow.view(),'terminal-written retry remains reachable and exposed history retained')
        self.refuse(lambda:self.apply(flow,'choose_partial_position',{}),'partial legacy escape excluded',flow)
        self.check(len(first)==len(second)==64 and all(b['midi']-a['midi']==12 for a,b in zip(first,second)),'all64 targets uniformly transferred')

    def test_fixedtop_AB_C_and_mandatory_reduction_transport(self):
        f = self.family
        for key in (f.keys[15],f.keys[50]):
            row = f.row(key);type(self).strata.add('fixedtop '+row['behavior_stratum'])
            flow = f.new_workflow(key);self.apply(flow,'set_top',self.top(key))
            textures = self.fixed_finish(flow)
            self.check(textures==(4 if row['behavior_stratum']=='AB' else 16),'AB/C complete ordered textures/additional sibling/audit')
            self.check(flow.snapshot()['state']=='completed' and not flow.snapshot()['runtime_admitted'],'manual completion no runtime admission')
        key = f.keys[15];lost = f.new_workflow(key);self.apply(lost,'set_top',self.top(key,48));self.fixed_step(lost,'no')
        self.check(lost.snapshot()['state']=='needs_reduction','source melody-loss debt')
        self.apply(lost,'diagnose','Mandatory bass+melody in current chosen low register.')
        self.apply(lost,'sing_top',{'sung_before_voicing':'yes','notes':'Synthetic.'})
        self.check(f.voicings(key,self.top(key,48),'Cmaj7','bass_melody_reduction',1)==[],'genuine unrepresentable lower-root register')
        self.apply(lost,'cannot_realize','No lower C contact for chosen C48; choose usable register.')
        choice = self.top(key);choice['diagnosis']='Whole chosen-register recovery preserves mandatory reduction.';self.apply(lost,'restart_top',choice)
        self.check(lost._flow.reduction_required and lost.view()['stage']=='bass_melody_reduction','restart cannot erase mandatory source reduction')
        self.apply(lost,'cancel');self.apply(lost,'reopen')
        self.refuse(lambda:self.apply(lost,'finish'),'cancel/reopen completion bypass',lost)
        self.refuse(lambda:self.apply(lost,'sing_top',{'sung_before_voicing':'yes','notes':'Synthetic.'}),'reopen physical release fence',lost)
        self.apply(lost,'release',{'learner_released':True});self.fixed_step(lost)
        self.check(not lost._flow.reduction_required and lost.view()['stage']=='melody','positive required reduction then full source rerender')
        self.fixed_finish(lost)
        self.check(lost.snapshot()['state']=='completed','register recovery completes with mandatory reduction retained in history')


if __name__=='__main__':
    start = time.perf_counter()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AdvancedCompilerTests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    print(json.dumps({'outcome':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,
       'assertions':AdvancedCompilerTests.assertions,'refusals':AdvancedCompilerTests.refusals,
       'all_rows_checked':AdvancedCompilerTests.all_rows_checked,'behavior_strata':sorted(AdvancedCompilerTests.strata),
       'seconds':time.perf_counter()-start,'synthetic_manual_reports_are_observations':False,
       'source_research':False,'native_build':False,'official_acceptance_increment':0}))
    sys.exit(0 if result.wasSuccessful() else 1)
