"""Source-symbol handoff cell and explicitly chosen forward/reverse realization."""
from copy import deepcopy
from fractions import Fraction
from math import isfinite
from uuid import uuid4
KEY='exercise-completeness-r01/level075/moduleg/p015-supplement01/handoffcell'
BODIES=('P---P---P---P---','P---P---P-------','----C-E-G-B-A-G--','E-D-C-----------')
ROLES=('RHYTHM','RHYTHM','LEAD','LEAD')
FOOTER=('The empty space at the end of the rhythm part is intentional preparation, not missing material. Reverse '
        'the cell by ending the lead phrase early and entering the rhythm texture exactly on the next bar 1.')
TUNING={'E':40,'A':45,'D':50,'G':55,'B':59,'e':64};PC={'C':0,'D':2,'E':4,'G':7,'A':9,'B':11}
COMMON=('all_source_symbols_in_order','intentional_rhythm_end_space','pulse_and_tempo_held','role_textures_correct','chosen_spacing_followed','chosen_realization_followed')
REVERSE=('lead_ended_and_released_before_boundary','rhythm_entered_exactly_next_bar1')
YN=('yes','no','uncertain')
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(o,names):require(type(o) is dict and set(o)==set(names),'field set')
def text(x):return type(x) is str and bool(x.strip())
def rational(x):
    require(type(x) is list and len(x)==2 and all(type(v) is int for v in x) and x[1]>0,'rational chosen onset');return Fraction(*x)
def bpm(x):
    if type(x) not in (int,float):return False
    try:return isfinite(x) and x>0
    except OverflowError:return False
def source_events():
    events=[]
    for bar,(role,body) in enumerate(zip(ROLES,BODIES),1):
        local=0
        for col,token in enumerate(body):
            if token=='-':continue
            local+=1;events.append({'source_order':len(events)+1,'source_bar':bar,'source_bar_attack':local,'source_role':role,
                'source_column_zero_based':col,'source_body_width':len(body),'source_token':token,
                'kind':'harmonic_attack_symbol' if token=='P' else 'named_pitch_class',
                'pitch_class':None if token=='P' else token,'octave':None,'string':None,'fret':None,'midi':None,
                'onset_q':None,'duration_q':None,'sounded_duration_q':None,'is_rest':False})
    return events
EVENTS=source_events();HARMONIC=EVENTS[:7];LEAD=EVENTS[7:]
def phase_events(phase):
    require(type(phase) is int and phase in (0,1),'finite phase')
    bars=(1,2,3,4) if phase==0 else (3,4,1,2)
    return [deepcopy(e) for bar in bars for e in EVENTS if e['source_bar']==bar]
def validate_plan(p):
    fields(p,('prerequisites','bpm','harmonic_slots','lead_contacts','bars','spacing_rationale'))
    fields(p['prerequisites'],('own_instrument','original_workbook'));require(all(v is True for v in p['prerequisites'].values()),'manual prerequisites')
    require(bpm(p['bpm']) and text(p['spacing_rationale']),'chosen external tempo/spacing')
    require(type(p['harmonic_slots']) is list and len(p['harmonic_slots'])==7,'seven rhythm source symbols')
    for c,e in zip(p['harmonic_slots'],HARMONIC):
        fields(c,('source_order','voicing_reference','articulation'))
        require(type(c['source_order']) is int and c['source_order']==e['source_order'] and text(c['voicing_reference']) and text(c['articulation']),'source-bound rhythm choice')
    require(type(p['lead_contacts']) is list and len(p['lead_contacts'])==9,'nine source pitch classes')
    for c,e in zip(p['lead_contacts'],LEAD):
        fields(c,('source_order','source_pitch_class','string','fret'))
        require(type(c['source_order']) is int and c['source_order']==e['source_order'] and c['source_pitch_class']==e['pitch_class'],'source-bound lead choice')
        require(type(c['string']) is str and c['string'] in TUNING and type(c['fret']) is int and 0<=c['fret']<=24,'standard tuning chosen fret')
        require((TUNING[c['string']]+c['fret'])%12==PC[e['pitch_class']],'chosen contact pitch class')
    require(type(p['bars']) is list and len(p['bars'])==4,'four source bars')
    for bar,(c,count) in enumerate(zip(p['bars'],(4,3,6,3)),1):
        fields(c,('source_bar','chosen_onsets'));require(type(c['source_bar']) is int and c['source_bar']==bar,'source bar order')
        onsets=c['chosen_onsets'];require(type(onsets) is list and len(onsets)==count,'source attack count per bar')
        q=[rational(x) for x in onsets];require(all(0<=x<1 for x in q) and all(a<b for a,b in zip(q,q[1:])),'chosen onset domain/order')
        require(q[0]>0 if bar==3 else q[0]==0,'chosen first attack/lead space')
        if bar==2:require(q[-1]<Fraction(3,4),'chosen rhythm preparation window')
class HandoffCellFlow:
    def __init__(self,key=KEY):
        require(key==KEY,'one exact existing source key');self.key=key;self.instance=uuid4().hex
        self.generation=self.phase=self.cycle=self.action=0;self.state='setup';self.plan=None;self.history=[];self.resume=None
    def token(self):return (self.instance,self.key,self.generation,self.phase,self.cycle,self.action,self.state)
    def check(self,t,states):require(type(t) is tuple and t==self.token(),'stale/foreign token');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'phase':self.phase,'cycle':self.cycle,'data':deepcopy(data)});self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','needs_retry','reported','completed'));validate_plan(p)
        self.plan=deepcopy(p);self.generation+=1;self.phase=self.cycle=0;self.record('plan',p,'ready')
    def begin(self,t):
        self.check(t,('ready',));self.cycle+=1;self.record('begin',{'source_order_route':[e['source_order'] for e in phase_events(self.phase)],
            'chosen_onsets_are_source_timing':False,'host_clock_used':False,'audio_supplied':False},'performing')
    def end_take(self,t,ended):self.check(t,('performing',));require(ended is True,'take end before review');self.record('take_end',{},'await_release')
    def release(self,t,ack):
        self.check(t,('await_release','reopen_release'));require(ack is True,'physical release')
        if self.state=='await_release':self.record('release',{},'reporting')
        else:
            state=self.resume;require(state is not None,'resume state');self.resume=None;self.record('reopen_release',{},state)
    def report(self,t,r):
        self.check(t,('reporting',));fields(r,('source_symbols','duties','notes'));duties=COMMON+(REVERSE if self.phase else ())
        fields(r['duties'],duties);require(all(v in YN for v in r['duties'].values()) and text(r['notes']),'full source duties')
        require(type(r['source_symbols']) is list and len(r['source_symbols'])==16,'complete source symbol report')
        ok=all(v=='yes' for v in r['duties'].values())
        for i,(reply,event) in enumerate(zip(r['source_symbols'],phase_events(self.phase)),1):
            fields(reply,('performance_order','source_order','played'))
            require(type(reply['performance_order']) is int and reply['performance_order']==i and type(reply['source_order']) is int and reply['source_order']==event['source_order'] and reply['played'] in YN,'source symbol route binding')
            ok=ok and reply['played']=='yes'
        self.record('report',{'response':r,'manual_requirements_reported':ok,'performance_verified':False,'automatic_score':False},'reported' if ok else 'needs_retry')
    def advance(self,t):
        self.check(t,('reported',))
        if self.phase==0:self.phase=1;self.cycle=0;self.record('next_phase',{},'ready')
        else:self.record('finish',{'manual_only':True,'source_acceptance':False},'completed')
    def retry(self,t,note):self.check(t,('reported','needs_retry'));require(text(note),'retry note');self.record('retry',{'note':note},'ready')
    def cancel(self,t):
        self.check(t,('setup','ready','performing','await_release','reporting','reported','needs_retry','completed','reopen_release'))
        if self.state!='reopen_release':self.resume='ready' if self.state in ('performing','await_release','reporting') else self.state
        self.generation+=1;self.record('cancel',{},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')
def contract():
    return {'schema_version':'fathom-private-handoffcell-manual.1','key':KEY,'source_bodies':list(BODIES),'source_roles':list(ROLES),
        'source_heading':'CHANGE ROLE WITHOUT CHANGING THE CLOCK','source_footer':FOOTER,'source_symbols':source_events(),
        'source_display_widths':[len(x) for x in BODIES],'dash_tokens_converted_to_events':False,
        'plan_schema':{'prerequisites':['own_instrument','original_workbook'],'bpm':'finite positive external choice',
            'harmonic_slots':'7ordered source-bound voicing/articulation choices','lead_contacts':'9source-bound standard-tuning string/fret0..24 choices matching printed pitch classes',
            'bars':'four ordered rational normalized-bar chosen-onset arrays of lengths4/3/6/3','spacing_rationale':'required; choices are not printed timing'},
        'response_schema':{'source_symbols':'16ordered performance/source-order bindings with yes/no/uncertain, each phase',
            'forward_duties':list(COMMON),'reverse_duties':list(COMMON+REVERSE),'notes':'required','enum':list(YN)},
        'authored_policies':['Forward sourcebarorder1/2/3/4; reverse role blocks3/4/1/2 without reversing internal melody order.',
            'Display widths16/16/17/16 are preserved; no fixed equal-column pulse interpretation or extra trailing event.',
            'Chosen onset domains preserve lead opening space and quarter-bar rhythm-end preparation; source timing/gates remain null.',
            'Nine source pitch classes are distinct from chosen octave/fret/MIDI; seven P symbols have no fixed chord/pitch.',
            'Physical release/take end before report; reverse requires lead release before boundary and rhythm exactly nextbar1.',
            'Current instance/key/generation/phase/cycle/action/state; negative/uncertain retained, cancel/reopen repeats interrupted phase.',
            'Idle plan change resets phase0; no storage, actual performance recognition, Attempt or credit.'],
        'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'timing_scheduled':False,
        'mastery_awarded':False,'credit_awarded':False,'persistence':False,'canonical_binding':None}
