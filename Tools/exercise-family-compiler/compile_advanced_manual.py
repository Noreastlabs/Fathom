#!/usr/bin/env python3
"""Deterministic export of56 reviewed advanced manual rows; no native admission.

Use FrozenFamilies.allowed_choices/validate_choice and new_workflow. Learner UI
must use Workflow.view(), never render the trusted source-player contract as its
view. Workflow.apply delegates to the pinned models, preserving their owners,
release/reveal order, retained responses, retry and reduction debt semantics.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import importlib.util
import inspect
import itertools
import json
from pathlib import Path
import subprocess
import sys
import time

SCHEMA = 'fathom.compiled-advanced-manual-definition.1'
CLOSURE_SCHEMA = 'fathom.compiled-advanced-manual-closure.1'
OUTPUT = 'Build/manager-resume-r03/advanced-manual-generation-r01'
PINS = {
 'Tools/fullscope-private-c-r01/level077-r61/degree_contract.py': '147a170f0adefb093ea90b2f518c0e11a69ec3cb241ede55fa450e44479e9141',
 'Tools/fullscope-private-c-r01/coherent-batch-resume-r62/chord_tone_contract.py': 'f41bb213aac564509af785444b010991da6c2cafd93e57cd65aed6007280c30f',
 'Tools/fullscope-private-c-r01/source-reviewed-row-correction-r64/source_reviewed_chord_tone.py': 'f3116198b7fdf65b82c63ae3e2728027e3a9fa47fbfd5d742abbc840f7fd2602',
 'Tools/fullscope-private-c-r01/coherent-batch-resume-r63/reconstruction_contract.py': 'cc6ed74a97ed6a86ed43e64235b6cc50129fddea545655b85e73c4ea4afe6799',
 'Tools/fullscope-private-c-r01/coherent-batch-resume-r63/reconstruction_contract_r04.py': '6bd7a81e98590e540f722031b43b7a18360596cc68db221da18bf14938e223f4',
 'Tools/fullscope-private-c-r01/coherent-level083-reduction-repair-r67/fixed_top_model.py': 'ea61e1073780125b6b4c828c9cfb9875ce2ef29bcfbcb92620683b9b6c060642',
 'Build/fullscope-private-c-r01/coherent-batch-resume-r62/chord-tone-overlay.jsonl': '2561ffd9f39c60b3a28c18a210e60739952688e680d926c75f034573b5754ca1',
 'Build/fullscope-private-c-r01/source-reviewed-row-correction-r64/source-reviewed-chord-tone-overlay.jsonl': 'c615908e8624a9591b0382a332595f31ae907e6e2ce81b8ddc97a2651464dd9c',
 'Build/fullscope-private-c-r01/coherent-batch-resume-r63/model-reconstruction-overlay-r04.jsonl': 'e4946d8cb9b728fe8953a756f4db7490780420ffd6fb6f26c22181bc0a077e1f',
 'Build/fullscope-private-c-r01/coherent-level083-reduction-repair-r67/fixed-top-overlay.jsonl': '2874f1f1426e3052396b2175fe8088704fcb3c838bc1302101d37d826057e889',
 'Build/fullscope-private-c-r01/coherent-level083-fixed-top-r65/source-cards.json': '0cd6ca0f7fc86508fae0555881a8ed3565b12171d867dc665118823d8d6e3779',
 'Build/fullscope-private-c-r01/coherent-level083-fixed-top-r65/shared-task-contract.json': 'f599520e6b6a0d2331a5fffb5dae9b8878eac2dee5f31936b720ede0ca56cd0c',
 'Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl': 'e8b2221c7bbb8389f2c20892ae6f08b34379bb5e88ead50c971819740b0a3791',
 'Build/fullscope-private-c-r01/level083-r06/implementation-packet.jsonl': 'b0db6a6fc5cc09cd947a755f11c899d72d4c3e21bbad02c26c8fbc1fe89df6a7',
 'Results/manager-resume-r02/private-source-bulk-review-r01/source-decisions.json': '80abbfbaedf4393d44fe2aac21329ca2382892263e23f69c1943037a41bad8d0',
 'Results/manager-resume-r02/private-source-bulk-review-r01/final-decisions.json': '9102b746e437f46af1e37da1786c980863c67d044fbecdb2ad0da5736873cb21',
 'Results/manager-resume-r02/private-coherent-bulk-review-r02/final-decisions.json': '3482b4d4816c837d5d2517993588bf84ef70e3222f63158bbd78b030f92d562f',
}
TRANSFER_MODEL = 'Tools/fullscope-private-c-r01/coherent-batch-resume-r62/chord_tone_contract.py'
CORRECTED_TRANSFER_MODEL = 'Tools/fullscope-private-c-r01/source-reviewed-row-correction-r64/source_reviewed_chord_tone.py'
RECONSTRUCTION_MODEL = 'Tools/fullscope-private-c-r01/coherent-batch-resume-r63/reconstruction_contract_r04.py'
FIXED_TOP_MODEL = 'Tools/fullscope-private-c-r01/coherent-level083-reduction-repair-r67/fixed_top_model.py'
TRANSFER_PACKET = 'Build/fullscope-private-c-r01/coherent-batch-resume-r62/chord-tone-overlay.jsonl'
CORRECTED_TRANSFER_PACKET = 'Build/fullscope-private-c-r01/source-reviewed-row-correction-r64/source-reviewed-chord-tone-overlay.jsonl'
RECONSTRUCTION_PACKET = 'Build/fullscope-private-c-r01/coherent-batch-resume-r63/model-reconstruction-overlay-r04.jsonl'
FIXED_TOP_PACKET = 'Build/fullscope-private-c-r01/coherent-level083-reduction-repair-r67/fixed-top-overlay.jsonl'
REVIEW1 = 'Results/manager-resume-r02/private-source-bulk-review-r01/final-decisions.json'
REVIEW2 = 'Results/manager-resume-r02/private-coherent-bulk-review-r02/final-decisions.json'
ACTIONS = {
 'chord_tone_transfer': ('set_plan','begin','heard','sung_name','choose_arrangements','cannot_respond','setup_target','attack','release','reveal','report','next_set','retry','finish','cancel','reopen'),
 'full_reconstruction': ('set_source','begin_written','heard','request_stop','release','commit_written','next_written','choose_first_position','diagnose_unable','sung_bar','play_bar','report_bar','next_bar','retry_bar','reveal_source','restart_written','begin_second_register','declare_scores','finish','cancel','reopen'),
 'fixed_top_reduction': ('set_top','restart_top','sing_top','choose_voicing','cannot_realize','name_role','play','release','report','advance','choose_additional','audit','diagnose','finish','cancel','reopen'),
}


class Refusal(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise Refusal(reason)


def encoded(value, *, sort=False):
    return json.dumps(value,ensure_ascii=False,sort_keys=sort,separators=(',',':'),allow_nan=False).encode()


def digest(value, *, sort=False):
    return hashlib.sha256(encoded(value,sort=sort)).hexdigest()


def strict_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out,'DUPLICATE_JSON_KEY')
            out[key] = value
        return out
    def nonfinite(_):
        raise Refusal('NONFINITE_JSON')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=nonfinite)


def exact_fields(value, names):
    require(type(value) is dict and set(value) == set(names),'EXACT_TYPED_FIELDS')


class Workflow:
    """Thin action facade over the reviewed model; no duplicate state machine."""
    def __init__(self, family, row):
        family.validate_row(row)
        self.recipe = row['recipe']
        self._flow = family._new_flow(row)

    def capture(self):
        return self._flow.token()

    def view(self):
        return deepcopy(self._flow.learner_view())

    def source_player_view(self):
        return deepcopy(self._flow.source_player_view()) if hasattr(self._flow,'source_player_view') else None

    def snapshot(self):
        return {'state':self._flow.state,'history':deepcopy(self._flow.history),
                'release_or_hearing_observed':False,'runtime_admitted':False,'credit_awarded':False}

    def apply(self, action, owner, *args):
        require(type(action) is str and action in ACTIONS[self.recipe],'EXACT_WORKFLOW_ACTION')
        method = getattr(self._flow, action)
        try:
            inspect.signature(method).bind(owner,*args)
        except TypeError as error:
            raise Refusal('EXACT_ACTION_PAYLOAD_ARITY') from error
        return method(owner,*args)


class FrozenFamilies:
    """Closed56 registry, cached source custody, choice and workflow adapters."""
    def __init__(self, root):
        self.root = Path(root).absolute()
        require(self.root.resolve() == self.root,'ROOT_SYMLINK')
        self.cache, self.inputs, self.models, self.rows, self.contexts = {}, {}, {}, [], {}
        for path, sha in PINS.items():
            self._read(path,sha)
        self.reviews = [self.inputs[REVIEW1],self.inputs[REVIEW2]]
        review1, review2 = (strict_json(self.cache[p]) for p in (REVIEW1,REVIEW2))
        for path in (TRANSFER_MODEL,CORRECTED_TRANSFER_MODEL,RECONSTRUCTION_MODEL,FIXED_TOP_MODEL):
            spec = importlib.util.spec_from_file_location('advanced_frozen_'+Path(path).stem,self.root/path)
            module = importlib.util.module_from_spec(spec)
            previous = sys.dont_write_bytecode
            try:
                sys.dont_write_bytecode = True
                spec.loader.exec_module(module)
            finally:
                sys.dont_write_bytecode = previous
            self.models[path] = module
        transfer = self.models[TRANSFER_MODEL]
        correction = self.models[CORRECTED_TRANSFER_MODEL]
        reconstruction = self.models[RECONSTRUCTION_MODEL]
        fixed = self.models[FIXED_TOP_MODEL]
        first = self._packet(TRANSFER_PACKET,14)
        final = self._packet(CORRECTED_TRANSFER_PACKET,1)[0]
        require([r['package_key'] for r in first] == list(transfer.KEYS),'EXACT_TRANSFER_FOURTEEN')
        require(final['package_key'] == transfer.KEYS[-1] == correction.KEY,'EXACT_CORRECTION_KEY')
        require(set(transfer.KEYS).issubset(review1['exact_ordered_unique_keys']),'TRANSFER_REVIEW_KEY_CLOSURE')
        fdecision = next(d for d in review1['decisions'] if d['family'] == 'F')
        require(fdecision['private_source_model_QA_decision']=='Accept','TRANSFER_REVIEW_ACCEPT')
        reviewed = {r['path']:r['sha256'] for r in fdecision['exact_artifacts']}
        require(all(reviewed.get(p)==PINS[p] for p in (TRANSFER_MODEL,TRANSFER_PACKET,CORRECTED_TRANSFER_MODEL,CORRECTED_TRANSFER_PACKET)),'TRANSFER_REVIEW_ARTIFACT_CLOSURE')
        for i, row in enumerate(first):
            chosen, packet, line, model = (final,CORRECTED_TRANSFER_PACKET,1,CORRECTED_TRANSFER_MODEL) if i==13 else (row,TRANSFER_PACKET,i+1,TRANSFER_MODEL)
            contract = correction.contract() if i==13 else transfer.contract(i)
            require(encoded(contract)==encoded(chosen['implementation']['task']['contract']),'EXACT_TRANSFER_CONTRACT')
            self._add('chord_tone_transfer',chosen,packet,line,contract,model,'source_reviewed_occluded' if i==13 else 'visible',REVIEW1)
        h = self._packet(RECONSTRUCTION_PACKET,1)[0]
        hdecision = next(d for d in review1['decisions'] if d['family']=='H')
        self._check_review(hdecision,RECONSTRUCTION_MODEL,RECONSTRUCTION_PACKET,[reconstruction.KEY])
        require(h['package_key']==reconstruction.KEY and encoded(reconstruction.contract())==encoded(h['implementation']['task']['contract']),'EXACT_RECONSTRUCTION_CONTRACT')
        self._add('full_reconstruction',h,RECONSTRUCTION_PACKET,1,reconstruction.contract(),RECONSTRUCTION_MODEL,'whole16bars64targets',REVIEW1)
        fixed_rows = self._packet(FIXED_TOP_PACKET,41)
        cards = fixed.cards()
        require([r['package_key'] for r in fixed_rows]==[c['package_key'] for c in cards],'EXACT_FIXED_TOP_KEYS')
        decision = next(d for d in review2['decisions'] if d['family']=='Level83 fixed-top AB35+C6')
        self._check_review(decision,FIXED_TOP_MODEL,FIXED_TOP_PACKET,[c['package_key'] for c in cards])
        require(decision['package_keys']==[c['package_key'] for c in cards],'FIXED_TOP_REVIEW_KEY_CLOSURE')
        for line, (row,card) in enumerate(zip(fixed_rows,cards),1):
            self._add('fixed_top_reduction',row,FIXED_TOP_PACKET,line,fixed.contract(row['package_key']),FIXED_TOP_MODEL,'AB' if card['module']=='AB' else 'C',REVIEW2)
        self.by_key = {r['source_key']:r for r in self.rows}
        require(len(self.rows)==len(self.by_key)==56,'EXACT_UNIQUE_FIFTY_SIX')
        self.keys = tuple(self.by_key)
        self.source_pins = [ref for path,ref in self.inputs.items() if path.startswith('Notes/')]
        require(len(self.source_pins)==4,'FOUR_ORIGINAL_SOURCE_FILES')

    def _read(self, path, sha):
        require(type(path) is str and not Path(path).is_absolute() and '..' not in Path(path).parts,'RELATIVE_INPUT_SCOPE')
        if path in self.cache:
            require(self.inputs[path]['sha256']==sha,'CONFLICTING_CACHED_PIN')
            return self.cache[path]
        file = self.root/path
        require(not any(p.is_symlink() for p in (file,*file.parents)),'INPUT_SYMLINK')
        raw = file.read_bytes()
        require(hashlib.sha256(raw).hexdigest()==sha,'FROZEN_INPUT_DRIFT:'+path)
        self.cache[path] = raw
        self.inputs[path] = {'path':path,'bytes':len(raw),'sha256':sha}
        return raw

    def _packet(self, path, count):
        rows = [strict_json(line) for line in self.cache[path].splitlines()]
        require(len(rows)==count and len({r['package_key'] for r in rows})==count,'CLOSED_PACKET_COUNT')
        return rows

    def _check_review(self, decision, model, packet, keys):
        require(decision['private_source_model_QA_decision']=='Accept' and decision['model']['path']==model
                and decision['model']['sha256']==PINS[model] and decision['packet']['path']==packet
                and decision['packet']['sha256']==PINS[packet],'REVIEW_ARTIFACT_CLOSURE')
        if 'package_keys' in decision:
            require(decision['package_keys']==keys,'REVIEW_KEY_CLOSURE')

    def _add(self, recipe, row, packet, line, contract, model, stratum, review):
        require(row['existing_parent_id']=='2.3.1.3.1' and not row['implementation']['canonical_ids_allocated']
                and not row['implementation']['playback_admitted'] and not row['contract_capabilities']['Accepted'],'NO_ADMISSION_OR_ACCEPTANCE')
        require(row['implementation']['manual_model']['path']==model,'CURRENT_MODEL_REFERENCE')
        require(contract.get('key',contract.get('source_card',{}).get('package_key'))==row['package_key'],'MODEL_CONTRACT_KEY')
        for ref in row['source_refs']:
            raw = self._read(ref['path'],ref['sha256'])
            require(len(raw)==ref['bytes'],'SOURCE_LENGTH_CLOSURE')
        if recipe in ('chord_tone_transfer','full_reconstruction'):
            lineage = row['provenance']['manual_r62' if recipe=='chord_tone_transfer' else 'manual_r63']
            original_ref = lineage['base_packet']
            original_line = lineage['base_jsonl_line']
        else:
            original_ref = row['provenance']['manual_r65']['previous_payload']
            original_line = original_ref['jsonl_line']
        original_raw = self._read(original_ref['path'],original_ref['sha256']).splitlines(keepends=True)[original_line-1]
        original = strict_json(original_raw)
        require(original['package_key']==row['package_key'] and original['source_identity']==row['source_identity'],'ORIGINAL_EXACT_IDENTITY')
        for field in ('source_refs','source_payload','timing_authority','field_limitations'):
            require(encoded(original[field])==encoded(row[field]),'ORIGINAL_SOURCE_FIELD:'+field)
        context = {'recipe':recipe,'source_task':deepcopy(row['implementation']['task']),
                   'source_payload':deepcopy(row['source_payload']),'timing_authority':deepcopy(row['timing_authority']),
                   'field_limitations':deepcopy(row['field_limitations'])}
        context_ref = digest(context,sort=True)
        self.contexts[context_ref] = context
        self.rows.append({'schema':SCHEMA,'source_key':row['package_key'],'source_identity':row['source_identity'],
          'recipe':recipe,'behavior_stratum':stratum,'contract':deepcopy(contract),'contract_sha256':digest(contract),
          'record_sha256':digest(row),'raw_record_sha256':hashlib.sha256(self.cache[packet].splitlines(keepends=True)[line-1]).hexdigest(),
          'packet':dict(self.inputs[packet],jsonl_line=line),'original_record':dict(self.inputs[original_ref['path']],jsonl_line=original_line,
            raw_line_sha256=hashlib.sha256(original_raw).hexdigest(),record_sha256=digest(original)),
          'context_ref':context_ref,'choice_domain_ref':recipe,'model':dict(self.inputs[model],class_name=row['implementation']['manual_model']['class']),
          'retained_review_ref':review,'source_locators':[{'path':r['path'],'locator':r.get('locator')} for r in row['source_refs']]})

    def row(self, key):
        require(type(key) is str and key in self.by_key,'EXACT_FAMILY_SCOPE')
        return deepcopy(self.by_key[key])

    def validate_row(self, row):
        require(type(row) is dict and type(row.get('source_key')) is str and row['source_key'] in self.by_key,'EXACT_FAMILY_SCOPE')
        require(encoded(row)==encoded(self.by_key[row['source_key']]),'EXACT_FROZEN_DEFINITION')
        require(digest(row['contract'])==row['contract_sha256'],'CONTRACT_HASH')

    def validate_bundle(self, rows, closure):
        require(type(rows) is list and len(rows)==56,'CLOSED_56_COUNT')
        require([r.get('source_key') for r in rows if type(r) is dict]==list(self.keys),'CLOSED_ORDERED_KEYS')
        for row in rows:
            self.validate_row(row)
        require(encoded(closure,sort=True)==encoded(self.closure(),sort=True),'EXACT_SHARED_CLOSURE')

    def _new_flow(self, row):
        model = self.models[row['model']['path']]
        return getattr(model,row['model']['class_name'])(row['source_key'])

    def new_workflow(self, key):
        return Workflow(self,self.row(key))

    def contacts(self, pitch_name=None):
        primitives = self.models[TRANSFER_MODEL]
        require(pitch_name is None or (type(pitch_name) is str and pitch_name in primitives.PC),'CHOSEN_PITCH_SCHEMA')
        return [{'string':s,'fret':f,'midi':base+f} for s,base in primitives.TUNING.items() for f in range(25)
                if pitch_name is None or (base+f)%12==primitives.PC[pitch_name]]

    def allowed_choices(self, key, chosen_pitch=None):
        row = self.row(key)
        common = {'package_key':key,'contract_sha256':row['contract_sha256'],'default_choice':None,
                  'source_clock':None,'source_contacts_fixed':False}
        if row['recipe']=='chord_tone_transfer':
            common.update({'pitch_names':list(self.models[TRANSFER_MODEL].PC),'pitch_names_nullable':True,
                           'contacts':self.contacts(chosen_pitch),'string_sets':list(self.models[TRANSFER_MODEL].SETS),
                           'distinct_string_sets_required':True,'voicing_membership_required':True,
                           'answer_filter_applied':False,'cue_provider':'chosen external_human'})
        elif row['recipe']=='full_reconstruction':
            common.update({'pitch_names':list(self.models[TRANSFER_MODEL].PC),'written_passes':list(self.models[RECONSTRUCTION_MODEL].PASSES),
                           'contacts':self.contacts(chosen_pitch),'target_count':64,'minimum_fret_range':[0,24],
                           'maximum_fret_range':[0,24],'octave_shift':'explicit uniform nonzero multiple of12, within chosen contact range',
                           'score_fields':{b:['hearing_accuracy','first_attack_fretboard_accuracy'] for b in self.models[RECONSTRUCTION_MODEL].BLOCKS},
                           'score_domain':[0,1,2,None],'hidden_source_filter_applied':False,'recording':'actual external reference or declared hash unknown'})
        else:
            require(chosen_pitch is None,'FIXED_TOP_LITERAL_PITCH')
            card = row['contract']['source_card']
            common.update({'top_contacts':self.contacts(card['literal_top']),'literal_top':card['literal_top'],
                           'stages':list(self.models[FIXED_TOP_MODEL].STAGES),'source_harmonies':deepcopy(card['source_harmonies']),
                           'additional_siblings':[c for c in row['contract']['source_sibling_candidates'] if c not in card['source_harmonies']] if card['module']=='C' else [],
                           'audit_fields':list(row['contract']['audit_questions']),
                           'voicing_api':'voicings(key,chosen_top,harmony,stage,limit); no auto-selection'})
        return common

    def validate_choice(self, key, kind, request):
        row = self.row(key)
        model = self.models[row['model']['path']]
        if row['recipe']=='chord_tone_transfer':
            require(kind in ('plan','arrangements'),'EXACT_CHOICE_KIND')
            validator = model.base if row['model']['path']==CORRECTED_TRANSFER_MODEL else model
            (validator.validate_plan if kind=='plan' else validator.validate_arrangements)(request)
        elif row['recipe']=='full_reconstruction':
            require(kind in ('source','written','first_position','second_position'),'EXACT_CHOICE_KIND')
            if kind=='source':
                model._legacy.validate_source_plan(request)
            elif kind=='written':
                exact_fields(request,('pass','response'))
                require(type(request['pass']) is str and request['pass'] in model.PASSES,'EXACT_WRITTEN_PASS')
                model._legacy.validate_written(request['pass'],request['response'])
            else:
                exact_fields(request,('plan','written_pitch_names') if kind=='first_position' else ('plan','written_pitch_names','first_contacts'))
                names = request['written_pitch_names']
                require(type(names) is list and len(names)==64 and all(type(n) is str and n in model.PC for n in names),'EXACT_64_WRITTEN_TARGETS')
                plan = request['plan']
                if kind=='second_position':
                    exact_fields(plan,('position','contacts','source_scope_ack','octave_shift_semitones'))
                    shift = plan['octave_shift_semitones']
                    require(type(shift) is int and shift!=0 and shift%12==0,'UNIFORM_NONZERO_OCTAVE')
                    first = request['first_contacts']
                    require(type(first) is list and len(first)==64,'EXACT_64_FIRST_CONTACTS')
                    for contact in first:
                        model.validate_contact(contact)
                    require(type(plan['contacts']) is list and len(plan['contacts'])==64,'EXACT_64_SECOND_CONTACTS')
                    for contact in plan['contacts']:
                        model.validate_contact(contact)
                    require(all(b['midi']-a['midi']==shift for a,b in zip(first,plan['contacts'])),'UNIFORM_ALL64_TRANSFER')
                    plan = {k:plan[k] for k in ('position','contacts','source_scope_ack')}
                model.validate_position(plan,names)
        else:
            require(kind in ('top','voicing'),'EXACT_CHOICE_KIND')
            if kind=='top':
                self._validate_top(key,request)
            else:
                exact_fields(request,('top','plan'))
                flow = self._validate_top(key,request['top'])
                plan = request['plan']
                exact_fields(plan,('key','harmony','stage','contacts','rationale'))
                require(plan['harmony'] in row['contract']['source_card']['source_harmonies']+row['contract']['source_sibling_candidates'],'EXACT_SOURCE_HARMONY_DOMAIN')
                require(plan['stage'] in model.STAGES+('bass_melody_reduction',),'EXACT_TEXTURE_DOMAIN')
                flow.harmonies = [plan['harmony']]
                flow.stage_index = model.STAGES.index(plan['stage']) if plan['stage'] in model.STAGES else 0
                flow.recovery = plan['stage']=='bass_melody_reduction'
                flow.validate_voicing(plan)
        return deepcopy(request)

    def _validate_top(self, key, request):
        flow = self.models[FIXED_TOP_MODEL].FixedTopFlow(key)
        flow.set_top(flow.token(),request)
        return flow

    def voicings(self, key, chosen_top, harmony, stage, limit=16):
        row = self.row(key)
        require(row['recipe']=='fixed_top_reduction','FIXED_TOP_RECIPE')
        require(type(limit) is int and 1<=limit<=128,'ENUMERATION_LIMIT')
        model = self.models[FIXED_TOP_MODEL]
        require(type(harmony) is str and harmony in row['contract']['source_sibling_candidates'],'EXACT_SIBLING_HARMONY')
        require(type(stage) is str and stage in model.STAGES+('bass_melody_reduction',),'EXACT_TEXTURE_DOMAIN')
        flow = self._validate_top(key,chosen_top)
        flow.harmonies = [harmony]
        flow.stage_index = model.STAGES.index(stage) if stage in model.STAGES else 0
        flow.recovery = stage=='bass_melody_reduction'
        pcs,_ = model.chord(harmony)
        target = [model.PC[flow.card['literal_top']]] if stage=='melody' else (
          [pcs[0],model.PC[flow.card['literal_top']]] if stage in ('root_melody','bass_melody_reduction') else
          [pcs[1],pcs[3],model.PC[flow.card['literal_top']]] if stage=='shell_melody' else list(pcs))
        top = flow.top
        target.remove(top['midi']%12)
        menus = [[c for c in self.contacts() if c['string']!=top['string'] and c['midi']<top['midi'] and c['midi']%12==pc] for pc in target]
        choices = []
        for contacts in itertools.product(*menus):
            plan = {'key':key,'harmony':harmony,'stage':stage,'contacts':list(contacts)+[deepcopy(top)],
                    'rationale':'Explicit finite authored choice; no source fingering or observed performance.'}
            try:
                flow.validate_voicing(plan)
            except ValueError:
                continue
            choices.append(plan)
            if len(choices)==limit:
                break
        return choices

    def closure(self):
        descriptors = {
          'chord_tone_transfer':{'actions':list(ACTIONS['chord_tone_transfer']),'hidden_reference':'learner_view excludes answer until first attack, physical release and explicit reveal; source_player_view is separate',
            'string_sets':list(self.models[TRANSFER_MODEL].SETS),'common_duties':list(self.models[TRANSFER_MODEL].COMMON),'transfer_duties':list(self.models[TRANSFER_MODEL].TRANSFER),
            'cue':'chosen external human; heard/sung responses retained before reference comparison','contact_domain':'standard tuning, fret0..24; two distinct chosen sets, chosen target inside each voicing; transfer preserves chosen pitch class',
            'recovery':'Wrong/unknown/manual duty failure requires diagnosis; cancellation/reopen has physical release fence; source exposure survives without a new blind claim',
            'source_reviewed_correction_key':self.models[CORRECTED_TRANSFER_MODEL].KEY},
          'full_reconstruction':{'actions':list(ACTIONS['full_reconstruction']),'written_passes':list(self.models[RECONSTRUCTION_MODEL].PASSES),'bars_per_register':16,'targets_per_register':64,'registers':2,
            'hidden_reference':'Complete first16-bar/64-target register before reveal; full second register uses a uniform chosen nonzero octave shift',
            'score_fields':{b:['hearing_accuracy','first_attack_fretboard_accuracy'] for b in self.models[RECONSTRUCTION_MODEL].BLOCKS},'score_domain':[0,1,2,None],
            'recovery':'Unknown written fields or scores block finish; terminal-reported diagnosed written restart remains available; all source-reveal/response history remains retained',
            'partial_legacy_escape_actions_excluded':['begin_final_bar','reveal_supported_source','choose_partial_position']},
          'fixed_top_reduction':{'actions':list(ACTIONS['fixed_top_reduction']),'texture_order':list(self.models[FIXED_TOP_MODEL].STAGES),'common_duties':['fixed_top_preserved','melody_clear','no_melody_change_for_easier_grip','role_named_before_chord'],
            'extra_C_duty':'smallest_available_bass_inner_motion','AB_audit':list(self.models[FIXED_TOP_MODEL].AB_AUDIT),'C_audit':list(self.models[FIXED_TOP_MODEL].C_AUDIT),
            'mandatory_reduction':'Melody loss retains debt on interrupted harmony through register restart/cancel/unknown retry. Only a positive bass+melody report and advance clears debt before source rerender.',
            'additional_sibling':'C completes three source harmonies in order plus one chosen additional substitute outside original3, from same fixed-top sibling vocabulary',
            'recovery':'Sing before forming every texture; name role before play; retain histories; release before report/reopen; reachable unknown audit/role and low-register recovery'},
        }
        return {'schema':CLOSURE_SCHEMA,'rows':56,'recipe_counts':{'chord_tone_transfer':14,'full_reconstruction':1,'fixed_top_reduction':41},
          'ordered_source_keys':list(self.keys),'ordered_key_set_sha256':digest(list(self.keys)),
          'contexts':deepcopy(self.contexts),'shared_behavior_descriptors':descriptors,
          'source_pins':deepcopy(self.source_pins),'cached_inputs':[deepcopy(r) for r in self.inputs.values()],
          'retained_private_reviews':deepcopy(self.reviews),'contract_encoding':'UTF-8 ensure_ascii=false compact JSON preserving frozen insertion order',
          'shared_context_encoding':'UTF-8 compact sorted-key JSON','learner_view_api':'new_workflow(key).view(); trusted source-player contracts/context must not be displayed before reveal',
          'api':['row(key)','validate_row(row)','validate_bundle(rows,closure)','allowed_choices(key,chosen_pitch=None)','validate_choice(key,kind,request)','voicings(key,chosen_top,harmony,stage,limit=16)','new_workflow(key)','Workflow.capture/view/source_player_view/snapshot/apply'],
          'source_clock':None,'fixed_bpm':None,'actual_performance_observed':False,'runtime_admitted':False,'official_accepted':False,
          'native_contract_gaps':['Export and Python pinned-model facade only; native shared recipe factory, UI state/report/reveal parity and exact-unit Learn/Practice integration remain required.',
            'No acoustic recognition, physical observation, scheduler, source timing, Attempt/credit, workbook mastery or canonical allocation/admission is supplied.',
            'Cached prior private source/model Accept remains separate from future compiler-independent/native/installed acceptance.']}

    def payloads(self):
        raw = b''.join(encoded(row)+b'\n' for row in self.rows)
        closure = self.closure()
        decoded = [strict_json(line) for line in raw.splitlines()]
        self.validate_bundle(decoded,strict_json(encoded(closure,sort=True)))
        require(encoded(decoded)==encoded(self.rows),'EXACT_ORDERED_CONTRACT_ROUNDTRIP')
        return {'definitions.jsonl':raw,'family-closure.json':encoded(closure,sort=True)+b'\n'}


def compile_family(root, output):
    start = time.perf_counter()
    root,output = Path(root).absolute(),Path(output).absolute()
    top = subprocess.run(['git','-C',str(root),'rev-parse','--show-toplevel'],text=True,capture_output=True)
    require(top.returncode==0 and root.resolve()==root and Path(top.stdout.strip())==root,'ROOT_SCOPE')
    require(output.resolve()==output and not output.exists() and output==root/OUTPUT,'OUTPUT_SCOPE')
    family = FrozenFamilies(root)
    payloads = family.payloads()
    output.mkdir(parents=True)
    refs = []
    for name,raw in payloads.items():
        (output/name).open('xb').write(raw)
        refs.append({'path':str((output/name).relative_to(root)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    receipt = {'schema':'fathom.family-generation.1','rows':56,'recipe_counts':{'chord_tone_transfer':14,'full_reconstruction':1,'fixed_top_reduction':41},
      'payloads':refs,'seconds':time.perf_counter()-start,'source_files_rehashed_once':len(family.source_pins),'cached_input_count':len(family.inputs),
      'contexts':len(family.contexts),'retained_private_reviews':family.reviews,'per_row_models_or_prompts':0,'new_source_research':False,
      'native_build':False,'runtime_admitted':False,'official_accepted':False,'contract_gaps':family.closure()['native_contract_gaps']}
    (output/'generation-receipt.json').open('x').write(json.dumps(receipt,indent=2)+'\n')
    return receipt


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True)
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    print(json.dumps(compile_family(args.root,args.output)))
