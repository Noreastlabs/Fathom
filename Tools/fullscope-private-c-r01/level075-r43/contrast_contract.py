"""Five source texture contrasts, one continuous forward/reverse manual take."""
from copy import deepcopy
from math import isfinite
from uuid import uuid4
ROWS=(('versechorus','Verse -> Chorus','muted 8ths','open 16ths','p -> f'),
 ('chorusverse','Chorus -> Verse','wide triads','low partials','f -> mp'),
 ('prechorus','Pre -> Chorus','rising quarters','full groove','crescendo'),
 ('bridgesolo','Bridge -> Solo','3+3+2 comp','sparse lead','mf -> space'),
 ('solochorus','Solo -> Chorus','lead register','rhythm register','f -> f'))
CONTEXT_SIXTH=('Chorus -> Outro','dense 16ths','quarters / whole','f -> pp','same tempo')
KEYS=tuple(f'exercise-completeness-r01/level075/moduled/p009-t1-r{i}/{r[0]}' for i,r in enumerate(ROWS,1))
EXAMPLE=('BAR 1 - VERSE','Count|1 & 2 & 3 & 4 &|','Play |P x P x P x P x|',
         'BAR 2 - CHORUS','Count|1e&a2e&a3e&a4e&a|','Play |P-x-P-x-P-x-P-x-|')
FOOTER=('Repeat the same Cmaj7 harmony while changing only attack zone, muting, subdivision, and dynamics. '
        'Then reverse the order without inserting a setup pause.')
TUNING={'E':40,'A':45,'D':50,'G':55,'B':59,'e':64};CHORD_PCS=(0,4,7,11)
SIDE_ORDER=('old','new','new','old')
CONTROLS=('attack_zone','muting','subdivision','dynamic_realization','register_role')
BAR_DUTIES=('texture_matched','planned_side_dynamic_matched','harmony_held','attack_zone_matched','muting_matched','subdivision_matched','register_role_matched','chosen_voicing_followed')
COMMON=('pulse_and_tempo_held','same_cmaj7_harmony','contrast_audible','forward_then_reverse','no_setup_pause',
        'table_authorized_changes_followed','source_forward_dynamic_followed','reverse_returns_chosen_states')
YN=('yes','no','uncertain')
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(o,names):require(type(o) is dict and set(o)==set(names),'field set')
def text(x):return type(x) is str and bool(x.strip())
def bpm(x):
    if type(x) not in (int,float):return False
    try:return isfinite(x) and x>0
    except OverflowError:return False
def validate_plan(p,index):
    fields(p,('prerequisites','bpm','harmony','source_dynamic_transition','states'))
    fields(p['prerequisites'],('own_instrument','original_workbook'));require(all(v is True for v in p['prerequisites'].values()),'manual prerequisites')
    require(bpm(p['bpm']) and p['harmony']=='Cmaj7' and p['source_dynamic_transition']==ROWS[index][4],'source harmony/dynamic and chosen tempo')
    fields(p['states'],('old','new'))
    for side,texture in zip(('old','new'),ROWS[index][2:4]):
        s=p['states'][side];fields(s,('source_texture','voicing','controls','source_accent_groups'))
        require(s['source_texture']==texture,'exact old/new source texture')
        voicing=s['voicing'];require(type(voicing) is list and 1<=len(voicing)<=6,'chosen partial/full guitar voicing')
        strings=set()
        for c in voicing:
            fields(c,('string','fret'))
            require(type(c['string']) is str and c['string'] in TUNING and c['string'] not in strings and type(c['fret']) is int and 0<=c['fret']<=24,'unique standard-tuning contacts')
            require((TUNING[c['string']]+c['fret'])%12 in CHORD_PCS,'bounded Cmaj7 chord-tone realization');strings.add(c['string'])
        fields(s['controls'],CONTROLS);require(all(text(v) for v in s['controls'].values()),'complete chosen controls')
        expected=[3,3,2] if index==3 and side=='old' else []
        require(type(s['source_accent_groups']) is list and all(type(v) is int for v in s['source_accent_groups']) and s['source_accent_groups']==expected,'source3+3+2 only where printed')
class ContrastFlow:
    def __init__(self,key):
        require(key in KEYS,'five exact existing source contrasts');self.key=key;self.index=KEYS.index(key);self.instance=uuid4().hex
        self.generation=self.cycle=self.action=0;self.state='setup';self.plan=None;self.history=[];self.resume=None
    def token(self):return (self.instance,self.key,self.generation,self.cycle,self.action,self.state)
    def check(self,t,states):require(type(t) is tuple and t==self.token(),'stale/foreign token');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'cycle':self.cycle,'data':deepcopy(data)});self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','needs_retry','reported','completed'));validate_plan(p,self.index)
        self.plan=deepcopy(p);self.generation+=1;self.cycle=0;self.record('plan',p,'ready')
    def begin(self,t):
        self.check(t,('ready',));self.cycle+=1;self.record('begin',{'continuous_side_order':list(SIDE_ORDER),
            'report_between_directions':False,'host_clock_used':False,'audio_supplied':False},'performing')
    def end_take(self,t,ended):self.check(t,('performing',));require(ended is True,'complete take end before review');self.record('take_end',{},'await_release')
    def release(self,t,ack):
        self.check(t,('await_release','reopen_release'));require(ack is True,'physical release')
        if self.state=='await_release':self.record('release',{},'reporting')
        else:
            state=self.resume;require(state is not None,'resume state');self.resume=None;self.record('reopen_release',{},state)
    def report(self,t,r):
        self.check(t,('reporting',));fields(r,('bars','common','notes'));fields(r['common'],COMMON)
        require(all(v in YN for v in r['common'].values()) and text(r['notes']),'full source duties')
        require(type(r['bars']) is list and len(r['bars'])==4,'continuous forward/reverse four bars')
        ok=all(v=='yes' for v in r['common'].values())
        for i,(b,side) in enumerate(zip(r['bars'],SIDE_ORDER),1):
            fields(b,('bar','side','source_texture','duties'))
            require(type(b['bar']) is int and b['bar']==i and b['side']==side and b['source_texture']==self.plan['states'][side]['source_texture'],'source side/bar binding')
            fields(b['duties'],BAR_DUTIES);require(all(v in YN for v in b['duties'].values()),'every bar source/control duty')
            ok=ok and all(v=='yes' for v in b['duties'].values())
        self.record('report',{'response':r,'manual_requirements_reported':ok,'performance_verified':False,
            'audible_contrast_measured':False,'automatic_score':False},'reported' if ok else 'needs_retry')
    def retry(self,t,note):self.check(t,('reported','needs_retry'));require(text(note),'retry note');self.record('retry',{'note':note},'ready')
    def finish(self,t):self.check(t,('reported',));self.record('finish',{'manual_only':True,'source_acceptance':False},'completed')
    def cancel(self,t):
        self.check(t,('setup','ready','performing','await_release','reporting','reported','needs_retry','completed','reopen_release'))
        if self.state!='reopen_release':self.resume='ready' if self.state in ('performing','await_release','reporting') else self.state
        self.generation+=1;self.record('cancel',{},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')
def contract(index):
    row=ROWS[index]
    return {'schema_version':'fathom-private-texture-contrast-manual.1','key':KEYS[index],
        'source_row':dict(zip(('change','old_texture','new_texture','dynamic','audit'),(*row[1:],'same tempo'))),
        'source_heading':'CONTRAST MUST BE AUDIBLE EVEN WITH THE SAME CHORD PROGRESSION','source_context_header':'128 CONTACTS',
        'source_context_sixth_row':dict(zip(('change','old_texture','new_texture','dynamic','audit'),CONTEXT_SIXTH)),
        'source_example_lines':list(EXAMPLE),'source_example_footer':FOOTER,'new_context_key_created':False,
        'source_note_events':[],'fixed_source_contact_count':None,'example_pulse_grid_adopted':False,
        'example_symbol_reference':{'P':'played attack symbol, pitch not fixed','x':'muted/percussive attack symbol, not rest','-':'layout/rhythm mark, no automatic silence event'},
        'plan_schema':{'prerequisites':['own_instrument','original_workbook'],'bpm':'finite positive external choice','harmony':'Cmaj7',
            'source_dynamic_transition':row[4],'states':'old/new exact source textures; unique standard-tuning chord-tone contacts, five control descriptions, source accent groups'},
        'response_schema':{'bars':'one continuous old/new/new/old four-bar take','bar_duties':list(BAR_DUTIES),'common':list(COMMON),'enum':list(YN),'notes':'required'},
        'authored_policies':['Reuse sameCmaj7 and continuous forward/reverse method from example for each named table row; explicit authored realization.',
            'Example four-control restriction does not erase other rows printed register/role/voicing changes.',
            'Forward dynamic column applies forward; reverse returns chosen side states, without inventing a printed reverse dynamic.',
            'Voicings limited here to C/E/G/B chord tones and unique strings; partials allowed, not proof of audible harmony/texture.',
            'Source space remains a literal dynamic/texture instruction, not invented velocity/rest duration.',
            'No source events/grid inferred from example; sixth contextual row creates no official child.',
            'One complete take before end/release/report; no direction-switch report break. Negative/uncertain retained.',
            'Current instance/key/generation/cycle/action/state; cancel/reopen repeats take after release; new plan resets completion, history retained.'],
        'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'timing_scheduled':False,
        'audible_contrast_measured':False,'mastery_awarded':False,'credit_awarded':False,'persistence':False,'canonical_binding':None}
