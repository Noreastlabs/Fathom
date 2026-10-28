"""Seven source recovery rows; external rehearsal and manual after-take reports only."""
from copy import deepcopy
from fractions import Fraction
from math import isfinite
from uuid import uuid4
ROWS=(('wrongnote','Wrong note','nearest chord tone','same beat'),
      ('wrongchord','Wrong chord','shell of active chord','next beat'),
      ('missedcue','Missed cue','stay current texture','join next bar'),
      ('lostsubdivision','Lost subdivision','quarter notes','keep bar count'),
      ('lostbarcount','Lost bar count','listen for harmonic landmark','rejoin at section boundary'),
      ('brokenstringgear','Broken string / gear','mute / simplify','preserve ensemble time'),
      ('leadphraseoverrun','Lead phrase overrun','stop phrase','enter rhythm next bar'),
      ('filltoolong','Fill too long','drop final notes','protect beat 1'))
KEYS=tuple(f'exercise-completeness-r01/level075/modulei/p019-t1-r{i}/{r[0]}' for i,r in enumerate(ROWS[:7],1))
BANK=tuple(r[0] for r in ROWS)
LADDER=('KEEP PULSE','FIND ACTIVE BAR','PLAY ROOT OR SHELL','FIND NEXT SECTION LANDMARK','RESTORE TEXTURE','REVIEW ONLY AFTER TAKE ENDS')
GLOBAL=('randomized_one_failure_per_eight_bars','uninterrupted_take','review_only_after_take_ends','full_chosen_material')
LOCAL=('specific_action_performed','source_deadline_or_priority_followed','pulse_preserved','earliest_safe_landmark')
CAPABILITIES=('unpredictable_failure_every_eight_bars','continuing_harmonic_section_reference')
YN=('yes','no','uncertain')
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(x,names):require(type(x) is dict and set(x)==set(names),'field set')
def text(x):return type(x) is str and bool(x.strip())
def positive(x):return type(x) is int and x>0
def bpm(x):
    if type(x) not in (int,float):return False
    try:return isfinite(x) and x>0
    except OverflowError:return False
def impact(x):
    require(type(x) is list and len(x)==2 and type(x[0]) is int and type(x[1]) is int and x[0]>=0 and x[1]>0,'nonnegative rational measures')
    return Fraction(*x)
def validate_plan(p):
    fields(p,('prerequisites','external_source','bpm','material','meter','eight_bar_blocks','bar_reference'))
    fields(p['prerequisites'],('own_instrument','original_workbook'))
    require(all(v is True for v in p['prerequisites'].values()),'manual prerequisites')
    e=p['external_source'];fields(e,('kind','reference','capabilities'))
    require(e['kind'] in ('external_partner','external_practice_track') and text(e['reference']),'external source required')
    fields(e['capabilities'],CAPABILITIES);require(all(v is True for v in e['capabilities'].values()),'external source capability')
    require(bpm(p['bpm']) and text(p['material']) and text(p['meter']),'chosen tempo/material/meter')
    require(positive(p['eight_bar_blocks']),'positive eight-bar blocks')
    require(type(p['bar_reference']) is list and len(p['bar_reference'])==8*p['eight_bar_blocks'],'complete chosen bar reference')
    for i,b in enumerate(p['bar_reference'],1):
        fields(b,('bar','active_chord','root_or_shell','nearest_chord_tone_options','texture','section','section_boundary'))
        require(type(b['bar']) is int and b['bar']==i,'ordered bar reference')
        require(all(text(b[k]) for k in ('active_chord','root_or_shell','nearest_chord_tone_options','texture','section')),'chosen harmonic/texture reference')
        require(type(b['section_boundary']) is bool,'typed section-boundary choice')
    require(any(b['section_boundary'] for b in p['bar_reference']),'at least one reference section boundary')
class RecoveryFlow:
    def __init__(self,key):
        require(key in KEYS,'seven existing source keys only');self.key=key;self.index=KEYS.index(key)
        self.instance=uuid4().hex;self.generation=self.cycle=self.action=0;self.state='setup'
        self.plan=None;self.history=[];self.resume=None
    def token(self):return (self.instance,self.key,self.generation,self.cycle,self.action,self.state)
    def check(self,t,states):
        require(type(t) is tuple and t==self.token(),'stale/foreign token');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'cycle':self.cycle,'data':deepcopy(data)})
        self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','needs_retry','reported','completed'));validate_plan(p)
        self.plan=deepcopy(p);self.generation+=1;self.cycle=0;self.record('plan',p,'ready')
    def begin(self,t,external_ready):
        self.check(t,('ready',));require(external_ready is True,'fresh external source readiness')
        self.cycle+=1;self.record('begin',{'external_ready_self_report':True,'audio_supplied':False,
            'failure_cues_supplied':False,'host_tempo_changed':False,'chosen_external_bpm':self.plan['bpm']},'performing')
    def end_take(self,t,ended):
        self.check(t,('performing',));require(ended is True,'take must end before review')
        self.record('take_ended',{'manual_self_report':True},'await_release')
    def release(self,t,released):
        self.check(t,('await_release','reopen_release'));require(released is True,'manual instrument release')
        if self.state=='await_release':self.record('release',{},'reporting')
        else:
            state=self.resume;require(state is not None,'resume state');self.resume=None;self.record('reopen_release',{},state)
    def report(self,t,r):
        self.check(t,('reporting',));fields(r,('blocks','global','notes'))
        fields(r['global'],GLOBAL);require(all(v in YN for v in r['global'].values()) and text(r['notes']),'full global report')
        require(type(r['blocks']) is list and len(r['blocks'])==self.plan['eight_bar_blocks'],'one reported failure per block')
        ok=all(v=='yes' for v in r['global'].values());target_seen=False;comparisons=[]
        for i,b in enumerate(r['blocks'],1):
            fields(b,('block','bar_in_block','failure','duties','ladder','impact_measures','recovery_account'))
            require(type(b['block']) is int and b['block']==i,'ordered unique blocks')
            require(type(b['bar_in_block']) is int and 1<=b['bar_in_block']<=8 and b['failure'] in BANK,'exact external failure binding')
            require(text(b['recovery_account']),'manual recovery account')
            fields(b['duties'],LOCAL);require(all(v in YN for v in b['duties'].values()),'typed recovery duty')
            require(type(b['ladder']) is list and len(b['ladder'])==6,'complete source ladder')
            ladder_ok=True
            for step,(a,expected) in enumerate(zip(b['ladder'],LADDER),1):
                fields(a,('step','source_instruction','followed'))
                require(type(a['step']) is int and a['step']==step and a['source_instruction']==expected and a['followed'] in YN,'source ladder order/binding')
                ladder_ok=ladder_ok and a['followed']=='yes'
            measure=b['impact_measures'];below=measure is not None and impact(measure)<1
            comparisons.append({'block':i,'reported_impact_less_than_one_measure':below,'performance_verified':False})
            target_seen=target_seen or b['failure']==BANK[self.index]
            ok=ok and below and ladder_ok and all(v=='yes' for v in b['duties'].values())
        ok=ok and target_seen
        self.record('report',{'response':r,'comparisons':comparisons,'target_failure_reported':target_seen,
            'manual_requirements_reported':ok,'performance_verified':False,'automatic_score':False},'reported' if ok else 'needs_retry')
    def retry(self,t,note):
        self.check(t,('reported','needs_retry'));require(text(note),'retry note');self.record('retry',{'note':note},'ready')
    def finish(self,t):self.check(t,('reported',));self.record('finish',{'manual_only':True,'source_acceptance':False},'completed')
    def cancel(self,t):
        self.check(t,('setup','ready','performing','await_release','reporting','reported','needs_retry','completed','reopen_release'))
        if self.state!='reopen_release':self.resume='ready' if self.state in ('performing','await_release','reporting') else self.state
        self.generation+=1;self.record('cancel',{},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')
def contract(index):
    row=ROWS[index]
    return {'schema_version':'fathom-private-recovery-manual.1','key':KEYS[index],
        'source_recovery_row':{'failure':row[1],'immediate_action':row[2],'deadline':row[3],'priority':None},
        'source_ladder':[{'step':i,'instruction':s} for i,s in enumerate(LADDER,1)],
        'source_context_failure_bank':[{'kind':r[0],'failure':r[1],'immediate_action':r[2],'deadline':r[3],
            'priority':None,'new_key_created':False} for r in ROWS],
        'source_context_header':'240 CONTACTS','source_randomization':'Randomize one failure every eight bars during rehearsal.',
        'source_criterion':'The exercise is passed when the injected error changes less than one measure of the performance.',
        'txt_module_instruction':'240 contacts. Inject wrong notes, wrong chords, missed cues, lost subdivisions, and fill overruns. Preserve pulse and rejoin at the earliest safe landmark.',
        'fixed_source_contact_count':None,'source_note_events':[],
        'plan_schema':{'prerequisites':['own_instrument','original_workbook'],
            'external_source':{'kinds':['external_partner','external_practice_track'],'reference':'required local/external description',
                'capabilities':list(CAPABILITIES),'fresh_readiness_at_begin':True,'app_supplied':False},
            'bpm':'finite positive external choice','material':'chosen rehearsal material','meter':'chosen reference, no inferred4/4',
            'eight_bar_blocks':'positive chosen integer; authored rehearsal extent, not source take length',
            'bar_reference':'8*blocks ordered active chord/root-shell/nearest-tone options/texture/section/boundary choices; not certified source facts'},
        'response_schema':{'blocks':'one externally randomized occurrence per eight-bar block, exact source bank kind and reported bar1..8',
            'duties':list(LOCAL),'ladder':'six source-bound ordered yes/no/uncertain self-reports',
            'impact_measures':'nonnegative rational estimate or null when uncertain; strict <1 is source criterion',
            'global':list(GLOBAL),'notes':'required','enum':list(YN)},
        'authored_policies':['External source owns hidden upcoming cue schedule; retained previous reports/reveals are not erased.',
            'All eight printed failures remain context; only the seven selected existing keys acquire contracts.',
            'Current key must be reported among randomized occurrences; otherwise retry, not inferred coverage.',
            'End-take declaration plus physical release precedes report; no live review or app clocks.',
            'Long wait to a valid section boundary can fail strict less-than-one-measure criterion; no forced success.',
            'Broken-string/gear trouble may be simulated; no actual equipment damage required.',
            'Negative/uncertain replies retained; explicit retry; immutable copy of plans/replies in local object history.',
            'Current instance/key/generation/cycle/action/state token; reopen release; interrupted take restarts.',
            'Idle plan change resets completion; chosen reference correctness remains a manual judgment.'],
        'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'failure_cues_supplied':False,
        'timing_scheduled':False,'mastery_awarded':False,'credit_awarded':False,'persistence':False,'canonical_binding':None}
