"""Source risk/transition obligations, manual chosen realization; no playback."""
from copy import deepcopy
from fractions import Fraction
from math import isfinite
from uuid import uuid4
ROWS=(('versepre','Verse -> Pre','texture + chord','high','Verse','Pre'),
      ('prechorus','Pre -> Chorus','density + dynamic','high','Pre','Chorus'),
      ('chorusverse','Chorus -> Verse','muting reset','medium','Chorus','Verse'),
      ('versebridge','Verse -> Bridge','meter/accent feel','high','Verse','Bridge'),
      ('bridgesolo','Bridge -> Solo','role change','high','Bridge','Solo'),
      ('solochorus','Solo -> Chorus','register + role','high','Solo','Chorus'),
      ('chorusoutro','Chorus -> Outro','density collapse','medium','Chorus','Outro'),
      ('d7gmaj7','D7 -> Gmaj7','key-center shift','high','D7','Gmaj7'))
KEYS=tuple(f'exercise-completeness-r01/level075/modulef/p012-t1-r{i}/{r[0]}' for i,r in enumerate(ROWS,1))+('exercise-completeness-r01/level075/modulef/p012-supplement01/eightcontacttransitionloop',)
PROFILES={
 'Verse A':(5,('Cmaj7','G/B','Am7','Em7','Fmaj7','C/E','Dm7','G7'),'Rhythm: 8th-note partials; Dynamic: p; Texture: palm-muted low register.'),
 'Pre-Chorus':(13,('Am7','Em7','Fmaj7','G7'),'Rhythm: quarters -> 8ths; Dynamic: mp -> mf; Texture: rising register.'),
 'Chorus':(17,('Cmaj7','G7','Am7','Fmaj7','Cmaj7','G7','Fmaj7','G7'),'Rhythm: 16th comping; Dynamic: f; Texture: open attack / upper triads.'),
 'Verse B':(25,('Cmaj7','G/B','Am7','Em7','Fmaj7','C/E','Dm7','G7'),'Rhythm: 8th-note partials; Dynamic: mp; Texture: variation + fills.'),
 'Bridge':(33,('Am7','Fmaj7','Cmaj7','G7','Am7','Fmaj7','D7','G7'),'Rhythm: 3+3+2 accents; Dynamic: mf; Texture: wide register / modulation cue.'),
 'Solo':(41,('Dm7','G7','Cmaj7','Cmaj7','Am7','D7','Gmaj7','G7'),'Rhythm: motif + chord targets; Dynamic: mf -> f; Texture: lead; rhythm reduced.'),
 'Final Chorus':(49,('Cmaj7','G7','Am7','Fmaj7','Cmaj7','G7','Fmaj7','G7'),'Rhythm: 16th comping; Dynamic: f; Texture: full texture.'),
 'Outro':(57,('Cmaj7','Am7','Dm7','Cmaj7'),'Rhythm: quarters -> whole; Dynamic: f -> pp; Texture: decelerating density.')}
ALIASES={'Verse':('Verse A','Verse B'),'Pre':('Pre-Chorus',),'Chorus':('Chorus','Final Chorus'),
         'Bridge':('Bridge',),'Solo':('Solo',),'Outro':('Outro',),'D7':('Solo D7 at46',),'Gmaj7':('Solo Gmaj7 at47',)}
DEST=('chord','register','articulation','dynamic','texture')
GLOBAL=('pulse_held','no_extra_count_in','chosen_spacing_followed','priority_plan_followed','complete_phase')
YN=('yes','no','uncertain')
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(x,names):require(type(x) is dict and set(x)==set(names),'field set')
def text(x):return type(x) is str and bool(x.strip())
def bpm(x):
    if type(x) not in (int,float):return False
    try:return isfinite(x) and x>0
    except OverflowError:return False
def rational(x):
    require(type(x) is list and len(x)==2 and all(type(v) is int for v in x) and x[1]>0,'rational chosen onset')
    return Fraction(*x)
def source_bar(profile,offset):
    start,chords,instruction=PROFILES[profile]
    return {'source_profile':profile,'source_bar':start+offset,'source_chord':chords[offset],'source_profile_instruction':instruction}
def context_for(route,old,new):
    require(type(route) is int and 0<=route<8,'finite risk route')
    require(old in ALIASES[ROWS[route][4]] and new in ALIASES[ROWS[route][5]],'permitted source profile choice')
    if route==7:return [source_bar('Solo',i) for i in range(2,8)]+[source_bar('Final Chorus',i) for i in range(2)]
    return [source_bar(old,i) for i in range(len(PROFILES[old][1])-4,len(PROFILES[old][1]))]+[source_bar(new,i) for i in range(4)]
def validate_plan(p,index):
    fields(p,('prerequisites','bpm','meter','route','old_profile','new_profile','provider','priority_order','chosen_loop_onsets','context_bars'))
    fields(p['prerequisites'],('own_instrument','original_workbook'));require(all(v is True for v in p['prerequisites'].values()),'manual prerequisite')
    require(bpm(p['bpm']) and text(p['meter']),'tempo/meter choice');route=p['route']
    require(type(route) is int and 0<=route<8 and (index==8 or route==index),'exact bound risk route')
    context=context_for(route,p['old_profile'],p['new_profile'])
    e=p['provider'];fields(e,('kind','reference','can_cue_during_old_attacks'))
    require(e['kind'] in ('human','external_source') and text(e['reference']) and e['can_cue_during_old_attacks'] is True,'capable external cue provider')
    order=p['priority_order'];require(type(order) is list and len(order)==8 and all(type(k) is str for k in order) and set(order)==set(KEYS[:8]),'eight exact priority routes')
    ranks=[0 if ROWS[KEYS.index(k)][3]=='high' else 1 for k in order];require(ranks==sorted(ranks),'high risks before medium')
    onsets=p['chosen_loop_onsets'];require(type(onsets) is list and len(onsets)==8,'eight chosen attack onsets')
    q=[rational(x) for x in onsets];require(q[0]==0 and q[4]==1 and all(a<b for a,b in zip(q,q[1:])) and q[3]<1 and q[-1]<2,'two-bar chosen onset bounds')
    bars=p['context_bars'];require(type(bars) is list and len(bars)==8,'four before and four after')
    for i,(bar,source) in enumerate(zip(bars,context),1):
        fields(bar,('context_bar','source_chord','voicing','register','articulation','dynamic','texture_realization'))
        require(type(bar['context_bar']) is int and bar['context_bar']==i and bar['source_chord']==source['source_chord'],'exact context source chord/order')
        require(all(text(bar[k]) for k in ('voicing','register','articulation','dynamic','texture_realization')),'complete learner realization')
class TransitionFlow:
    def __init__(self,key):
        require(key in KEYS,'finite existing transition only');self.key=key;self.index=KEYS.index(key);self.instance=uuid4().hex
        self.generation=self.phase=self.cycle=self.action=0;self.state='setup';self.plan=None;self.history=[];self.resume=None
    def token(self):return (self.instance,self.key,self.generation,self.phase,self.cycle,self.action,self.state)
    def check(self,t,states):require(type(t) is tuple and t==self.token(),'stale/foreign token');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'phase':self.phase,'cycle':self.cycle,'data':deepcopy(data)})
        self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','needs_retry','reported','completed'));validate_plan(p,self.index)
        self.plan=deepcopy(p);self.generation+=1;self.phase=self.cycle=0;self.record('plan',p,'ready')
    def begin(self,t,external_ready):
        self.check(t,('ready',));require(external_ready is True,'fresh external readiness');self.cycle+=1
        self.record('begin',{'phase':'four_loop_iterations' if self.phase==0 else 'context_window',
            'source_attack_timing_invented':False,'chosen_onsets':self.plan['chosen_loop_onsets'],'host_clock_used':False,
            'audio_supplied':False,'cue_supplied':False},'performing')
    def end_take(self,t,ended):self.check(t,('performing',));require(ended is True,'take end before review');self.record('take_end',{},'await_release')
    def release(self,t,ack):
        self.check(t,('await_release','reopen_release'));require(ack is True,'manual release')
        if self.state=='await_release':self.record('release',{},'reporting')
        else:
            state=self.resume;require(state is not None,'resume state');self.resume=None;self.record('reopen_release',{},state)
    def report(self,t,r):
        self.check(t,('reporting',));fields(r,('transitions','context_bars','global','notes'))
        fields(r['global'],GLOBAL);require(all(v in YN for v in r['global'].values()) and text(r['notes']),'global source response')
        require(type(r['transitions']) is list and len(r['transitions'])==(4 if self.phase==0 else 1),'source loop count')
        ok=all(v=='yes' for v in r['global'].values())
        for i,tr in enumerate(r['transitions'],1):
            fields(tr,('iteration','attacks','cue_received_old_attack','first_destination'))
            require(type(tr['iteration']) is int and tr['iteration']==i,'ordered loop iterations')
            require(type(tr['attacks']) is list and len(tr['attacks'])==8,'all eight structural attacks')
            for j,a in enumerate(tr['attacks'],1):
                fields(a,('attack','played'));require(type(a['attack']) is int and a['attack']==j and a['played'] in YN,'attack source order/report')
                ok=ok and a['played']=='yes'
            cue=tr['cue_received_old_attack'];require(cue is None or (type(cue) is int and 0<=cue<=5),'reported cue relation')
            fields(tr['first_destination'],DEST);require(all(v in YN for v in tr['first_destination'].values()),'destination source criteria')
            ok=ok and cue in (3,4) and all(v=='yes' for v in tr['first_destination'].values())
        require(type(r['context_bars']) is list and len(r['context_bars'])==(0 if self.phase==0 else 8),'phase-specific context report')
        for i,bar in enumerate(r['context_bars'],1):
            fields(bar,('bar','source_chord','played_to_plan'))
            require(type(bar['bar']) is int and bar['bar']==i and bar['source_chord']==self.plan['context_bars'][i-1]['source_chord'] and bar['played_to_plan'] in YN,'context source binding')
            ok=ok and bar['played_to_plan']=='yes'
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
def contract(index):
    return {'schema_version':'fathom-private-transition-risk-manual.1','key':KEYS[index],
        'source_risk_row':None if index==8 else {'transition':ROWS[index][1],'why_risky':ROWS[index][2],'risk':ROWS[index][3],'repair':'loop last bar + first bar'},
        'source_context_risk_rows':[{'key':KEYS[i],'transition':r[1],'why_risky':r[2],'risk':r[3],'repair':'loop last bar + first bar'} for i,r in enumerate(ROWS)],
        'source_context_header':'15 RISK CELLS | 120 CONTACTS','source_priority_instruction':'REHEARSE THE MOST EXPENSIVE FAILURE POINTS FIRST',
        'source_attack_slots':[{'order':i,'side':'old' if i<=4 else 'destination','side_attack':i if i<=4 else i-4,
            'pitch':None,'fret':None,'onset_q':None,'duration_q':None,'sounded_gate':None} for i in range(1,9)],
        'source_cue':'received during attacks 3-4','source_repeats':4,'source_no_extra_count_in':True,
        'source_context_instruction':'Then embed inside 4 bars before + 4 bars after.',
        'source_criterion':'A transition is passed only when the first destination attack has the correct chord, register, articulation, and dynamic. Correct pitch with the wrong texture is still a missed section change.',
        'source_master_profiles':{name:{'start_bar':v[0],'chords':list(v[1]),'instruction':v[2]} for name,v in PROFILES.items()},
        'plan_schema':{'prerequisites':['own_instrument','original_workbook'],'bpm':'finite positive external choice','meter':'learner reference',
            'route':'same risk index, or one of8 for existing supplement','old_profile_new_profile':'explicit allowed TXT source occurrence',
            'provider':'human/external_source reference, ability to cue old3–4 and fresh readiness',
            'priority_order':'permutation of8existing risk keys with high before medium',
            'chosen_loop_onsets':'8rational normalized-bar choices, four each bar; source times remain null',
            'context_bars':'8exact bound chord labels plus learner voicing/register/articulation/dynamic/texture choices'},
        'response_schema':{'transitions':'four ordered8attack reports in phase0, one in phase1; received old cue ordinal0..5 or null',
            'first_destination':list(DEST),'context_bars':'empty inphase0,8source-bound manual reports inphase1','global':list(GLOBAL),'enum':list(YN)},
        'authored_policies':['Choose4old-profile ending bars and4new-profile opening bars; selected transition is context boundary4/5.',
            'D7/Gmaj7 maps to master Solo46/47 with source context43–50; no canonical item inheritance.',
            'Verse and Chorus aliases require explicit choice; risk routes may connect nonadjacent master sections.',
            'Learner normalized-bar first attacks0/1 and chosen spacing are a bounded manual realization, not printed timing.',
            'Source attack slots carry no pitch/fret/gate; source bar chords and learner voiced realization remain distinct.',
            'External cue provider required, no app sound/clock; prior source underlayer visibility limitations retained.',
            'Manual phase0four loops then phase1context; end and release before response; negative/uncertain retained.',
            'Current instance/key/generation/phase/cycle/action/state tokens; cancel/reopen repeats interrupted phase.',
            'Idle plan change resets phase0; reports/plans remain in private object history, no persistence or credit.'],
        'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'timing_scheduled':False,
        'mastery_awarded':False,'credit_awarded':False,'persistence':False,'canonical_binding':None}
