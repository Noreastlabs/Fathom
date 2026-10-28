"""Private source-bound cue task; external providers, manual responses, no clock/audio."""
from copy import deepcopy
from math import isfinite
from uuid import uuid4
KEYS=tuple(f'exercise-completeness-r01/level075/modulec/p006-card{i:02d}/cuecell{i}oldsectionnewsection' for i in range(1,5))
TABLE={
 'visual':('Visual','head nod / hand lift','look on beat 3','change on next bar 1'),
 'count':('Count','spoken 4 / 2-bar count','hear while playing','do not slow to listen'),
 'musical':('Musical','drum fill / held chord','recognize pattern','prepare destination'),
 'chart':('Chart','rehearsal mark','know bar number','eyes return before change')}
PATTERNS={'visual':('head nod','hand lift'),'count':('spoken 4','2-bar count'),'musical':('drum fill','held chord'),'chart':('rehearsal mark',)}
PROVIDERS={'visual':('external_human','external_video'),'count':('external_human','external_audio','external_video'),
 'musical':('external_human','external_audio','external_video'),'chart':('original_chart','learner_prepared_chart')}
DIAGRAM=('Count|1---2---3---4---|','Play |P---P---P---P---|','Look |------------>---|','Move |--------------->|')
PROSE='Keep playing while the eyes or ears receive the cue. The fretting hand begins moving only after the final old-section attack.'
TXT='96 contacts. Visual, spoken-count, musical, and chart cues. Receive the cue while continuing to play; change exactly at the destination barline.'
COMMON=('pulse_and_tempo_held','four_old_attacks_in_order','cue_received_while_playing','move_only_after_final_old_attack',
 'destination_barline_on_time','old_realization_followed','destination_realization_followed','new_section_continued','external_source_used_as_planned')
DUTIES={'visual':('look_on_beat3_table_route','change_on_next_bar1'),'count':('heard_count_while_playing','did_not_slow_to_listen'),
 'musical':('recognized_cue_pattern','prepared_destination'),'chart':('knew_bar_number','eyes_returned_before_change')}
YN=('yes','no','uncertain');STRINGS=('E','A','D','G','B','e')
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(o,keys):require(type(o) is dict and set(o)==set(keys),'field set')
def text(x):return type(x) is str and bool(x.strip())
def tempo(x):
    if type(x) not in (int,float):return False
    try:return isfinite(x) and x>0
    except OverflowError:return False
def voicing(v):
    require(type(v) is list and 1<=len(v)<=6,'chosen guitar voicing');used=set()
    for c in v:
        fields(c,('string','fret'));require(type(c['string']) is str and c['string'] in STRINGS and c['string'] not in used and type(c['fret']) is int and 0<=c['fret']<=24,'unique chosen standard-tuning contacts');used.add(c['string'])
def validate_plan(p):
    fields(p,('prerequisites','bpm','sections','old_attacks','destination_entry','new_continuation','cue','diagram_timing_unresolved_ack'))
    fields(p['prerequisites'],('own_instrument','original_workbook'));require(all(x is True for x in p['prerequisites'].values()),'manual prerequisites')
    require(tempo(p['bpm']) and p['diagram_timing_unresolved_ack'] is True,'chosen tempo and unresolved diagram acknowledgment')
    fields(p['sections'],('old','new'));require(all(text(x) for x in p['sections'].values()) and text(p['new_continuation']),'concrete sections and continuation')
    require(type(p['old_attacks']) is list and len(p['old_attacks'])==4,'four chosen old-attack voicings')
    for v in p['old_attacks']:voicing(v)
    voicing(p['destination_entry']);c=p['cue'];fields(c,('kind','pattern','provider','source_preparation','source_execution','parameters'))
    kind=c['kind'];require(type(kind) is str and kind in TABLE,'source cue kind')
    require(c['pattern'] in PATTERNS[kind] and c['source_preparation']==TABLE[kind][2] and c['source_execution']==TABLE[kind][3],'source mode/pattern/obligations')
    provider=c['provider'];fields(provider,('kind','reference','ready'))
    require(provider['kind'] in PROVIDERS[kind] and text(provider['reference']) and provider['ready'] is True,'available external source provider')
    x=c['parameters']
    if kind=='visual':
        fields(x,('look_on_beat','destination_beat'));require(type(x['look_on_beat']) is int and x['look_on_beat']==3 and type(x['destination_beat']) is int and x['destination_beat']==1,'separate visual table route')
    elif kind=='count':
        fields(x,('listen_while_playing','keep_tempo'));require(x['listen_while_playing'] is True and x['keep_tempo'] is True,'source count behavior')
    elif kind=='musical':
        fields(x,('recognition_description','destination_preparation'));require(all(text(v) for v in x.values()),'named pattern and destination preparation')
    else:
        fields(x,('rehearsal_mark','current_bar','destination_bar'));require(text(x['rehearsal_mark']) and type(x['current_bar']) is int and x['current_bar']>=1 and type(x['destination_bar']) is int and x['destination_bar']==x['current_bar']+1,'known next chart bar')
class CueFlow:
    def __init__(self,key):
        require(key in KEYS,'four existing cue cells');self.key=key;self.instance=uuid4().hex;self.generation=self.cycle=self.action=0
        self.state='setup';self.plan=None;self.history=[];self.resume=None
    def token(self):return (self.instance,self.key,self.generation,self.cycle,self.action,self.state)
    def check(self,t,states):require(type(t) is tuple and t==self.token(),'stale/foreign token');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'cycle':self.cycle,'data':deepcopy(data)});self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','needs_retry','reported','completed'));validate_plan(p);self.plan=deepcopy(p)
        self.generation+=1;self.cycle=0;self.record('plan',p,'ready')
    def begin(self,t,external_source_ready):
        self.check(t,('ready',));require(external_source_ready is True,'current external source readiness');self.cycle+=1
        self.record('begin',{'cue_kind':self.plan['cue']['kind'],'four_old_attack_beats':[1,2,3,4],'destination':'next_bar_1',
          'diagram_timing_resolved':False,'audio_supplied':False,'clock_used':False},'performing')
    def end_take(self,t,ended):self.check(t,('performing',));require(ended is True,'complete take end');self.record('take_end',{},'await_release')
    def release(self,t,ack):
        self.check(t,('await_release','reopen_release'));require(ack is True,'physical release')
        if self.state=='await_release':self.record('release',{},'reporting')
        else:
            state=self.resume;require(state is not None,'resume');self.resume=None;self.record('reopen_release',{},state)
    def report(self,t,r):
        self.check(t,('reporting',));fields(r,('cue_kind','old_attacks','destination_beat','common','source_duties','notes'))
        kind=self.plan['cue']['kind'];require(r['cue_kind']==kind and type(r['destination_beat']) is int and r['destination_beat']==1 and text(r['notes']),'source cue/destination response binding')
        fields(r['common'],COMMON);fields(r['source_duties'],DUTIES[kind]);values=list(r['common'].values())+list(r['source_duties'].values())
        require(all(x in YN for x in values),'manual enum');require(type(r['old_attacks']) is list and len(r['old_attacks'])==4,'four source attack reports')
        for i,a in enumerate(r['old_attacks'],1):
            fields(a,('source_beat','symbol','chosen_realization_followed'));require(type(a['source_beat']) is int and a['source_beat']==i and a['symbol']=='P' and a['chosen_realization_followed'] in YN,'source attack binding');values.append(a['chosen_realization_followed'])
        ok=all(x=='yes' for x in values);self.record('report',{'response':r,'manual_requirements_reported':ok,
          'performance_verified':False,'cue_measured':False,'diagram_timing_resolved':False,'automatic_score':False},'reported' if ok else 'needs_retry')
    def retry(self,t,note):self.check(t,('reported','needs_retry'));require(text(note),'retry note');self.record('retry',{'note':note},'ready')
    def finish(self,t):self.check(t,('reported',));self.record('finish',{'manual_only':True,'source_acceptance':False},'completed')
    def cancel(self,t):
        self.check(t,('setup','ready','performing','await_release','reporting','reported','needs_retry','completed','reopen_release'))
        if self.state!='reopen_release':self.resume='ready' if self.state in ('performing','await_release','reporting') else self.state
        self.generation+=1;self.record('cancel',{},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')
def contract(i):
    return {'schema_version':'fathom-private-cue-cell-manual.1','key':KEYS[i],
      'source_label':f'Cue cell {i+1}: old section -> new section','source_context_header':'12 CUE CELLS | 96 CONTACTS',
      'source_table':{k:list(v) for k,v in TABLE.items()},'source_diagram':list(DIAGRAM),'source_prose':PROSE,'source_txt_module':TXT,
      'source_abstract_attacks':[{'source_order':b,'source_beat_label':b,'symbol':'P','source_pitch':None,'source_fret':None,'gate':None} for b in range(1,5)],
      'source_note_events':[],'source_fixed_contact_count':None,'numbered_card_to_cue_kind_mapping':None,
      'source_interpretation_questions':[
        {'kind':'UNRESOLVED_TABLE_DIAGRAM_RELATION','table_literal':'look on beat 3','diagram_literal':'Look |------------>---|',
         'diagram_arrow_layout_column_zero_based':12,'count_label_at_same_layout_column':'4','absolute_diagram_look_time':None,
         'decision':'Keep table route and literal diagram separately; no adjudication or fixed arrow clock.'},
        {'kind':'UNRESOLVED_SOURCE_EXTENT','printed_header':'12 CUE CELLS | 96 CONTACTS','actual_enumerated_cards_on_page':4,'invented_keys':0}],
      'plan_schema':{'external_provider_types':PROVIDERS,'source_cue_patterns':PATTERNS,'source_cue_choices':'All four selectable for each identical numbered card; no invented fixed mapping.',
         'instrument_choices':'Four old-attack voicings and destination voicing: unique standard-tuning strings/frets0..24; learner choices only.',
         'diagram_timing_unresolved_ack':True,'current_readiness_required_at_begin':True},
      'response_schema':{'common':list(COMMON),'source_duties':{k:list(v) for k,v in DUTIES.items()},'old_attacks':'four ordered source P/beat1..4 reports','enum':list(YN)},
      'authored_policies':['Choice of table method is separate from unresolved diagram timing; visual follows explicit table beat3/nextbar1 without claiming diagram resolved.',
        'Provider is a human, external media or original/prepared chart appropriate to cue kind; app supplies none.',
        'Source played P symbols are abstract attacks, not four single-note contacts; no source chord/pitch count inferred.',
        'Keep playing, move after final old attack, enter destination barline and continue before end/release/report.',
        'Negative/uncertain is retry; plan/generation/action tokens and cancellation/reopen preserve custody; new plan resets completion with history.'],
      'automatic_evaluation':False,'performance_observed':False,'source_complete_timing':False,'audio_supplied':False,
      'timing_scheduled':False,'cue_measured':False,'credit_awarded':False,'mastery_awarded':False,'persistence':False,'canonical_binding':None}
