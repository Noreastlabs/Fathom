"""Private manual cue task. External people/devices provide every actual cue."""
from copy import deepcopy
from math import isfinite
from uuid import uuid4

ROWS=(('introverse','Intro -> Verse','Cmaj7','visual',('visual',),'Verse A: bars 5-12'),
      ('versepre','Verse -> Pre','Am7','2-bar count',('audio',),'Pre-Chorus: bars 13-16'),
      ('prechorus','Pre -> Chorus','Cmaj7','drum fill',('audio','musical'),'Chorus: bars 17-24'),
      ('chorusverse','Chorus -> Verse','Cmaj7','held vocal note',('audio','musical'),'Verse B: bars 25-32'),
      ('versebridge','Verse -> Bridge','Am7','visual + count',('visual','audio'),'Bridge: bars 33-40'),
      ('bridgesolo','Bridge -> Solo','Dm7','4-count',('audio',),'Solo: bars 41-48'),
      ('solofinalchorus','Solo -> Final Chorus','Cmaj7','band hit',('audio','musical'),'Final Chorus: bars 49-56'),
      ('finalchorusoutro','Final Chorus -> Outro','Cmaj7','double nod',('visual',),'Outro: bars 57-60'))
KEYS=tuple(f'exercise-completeness-r01/level075/modulec/p007-t1-r{i}/{row[0]}' for i,row in enumerate(ROWS,1))
NOLOOK=('Have a partner or random timer call one of the eight destination sections while you maintain quarter-note Cmaj7. '
        'On the next barline, enter the requested section using its first chord and texture. If the cue is '
        'missed, continue the current bar and join one bar later; do not stop.')
SUPPORT=('Keep playing while the eyes or ears receive the cue. The fretting hand begins moving only after the final old-section attack.')
CALLS=('CALL: VERSE  -> Cmaj7 muted eighths','CALL: CHORUS -> Cmaj7 open sixteenths',
       'CALL: BRIDGE -> Am7 3+3+2 accents','CALL: SOLO   -> Dm7 sparse target phrase')
TRANSITION=('cue_received_while_playing','pulse_uninterrupted','hand_after_final_old_attack',
            'destination_first_chord','destination_texture','entry_next_barline')
RECOVERY=('quarter_note_cmaj7_waiting','request_understood','no_stop','destination_first_chord',
          'destination_texture','entry_at_barline','tempo_held')
YN=('yes','no','uncertain')
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(x,names):require(type(x) is dict and set(x)==set(names),'field set')
def text(x):return type(x) is str and bool(x.strip())
def bpm(x):
    if type(x) not in (float,int):return False
    try:return isfinite(x) and x>0
    except OverflowError:return False
def validate_plan(p,index):
    fields(p,('prerequisites','bpm','old_chord','old_voicing','waiting_chord','waiting_voicing','cue','provider','destinations'))
    fields(p['prerequisites'],('own_instrument','original_workbook'))
    require(all(x is True for x in p['prerequisites'].values()),'manual prerequisite')
    require(bpm(p['bpm']) and p['old_chord']=='G7' and p['waiting_chord']=='Cmaj7','source chord/tempo')
    require(text(p['old_voicing']) and text(p['waiting_voicing']) and p['cue']==ROWS[index][3],'voicing/cue choice')
    provider=p['provider'];fields(provider,('type','capabilities','provision_description'))
    require(provider['type'] in ('human','external_source') and text(provider['provision_description']),'external cue provider')
    fields(provider['capabilities'],('visual','audio','musical','named_section'))
    require(all(type(x) is bool for x in provider['capabilities'].values()),'explicit provider capability')
    require(all(provider['capabilities'][x] for x in (*ROWS[index][4],'named_section')),'required cue capability unavailable')
    fields(p['destinations'],KEYS)
    for key,row in zip(KEYS,ROWS):
        choice=p['destinations'][key];fields(choice,('source_first_chord','voicing','texture_realization'))
        require(choice['source_first_chord']==row[2] and text(choice['voicing']) and text(choice['texture_realization']),'destination choice/source first chord')

class CueFlow:
    def __init__(self,key):
        require(key in KEYS,'finite source row only')
        self.key=key;self.index=KEYS.index(key);self.instance=uuid4().hex
        self.generation=self.phase=self.cycle=self.action=0;self.state='setup';self.plan=None;self.history=[];self.resume=None
    def token(self):return (self.instance,self.key,self.generation,self.phase,self.cycle,self.action,self.state)
    def check(self,t,states):
        require(type(t) is tuple and t==self.token(),'stale/foreign token');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'phase':self.phase,'cycle':self.cycle,'generation':self.generation,'data':deepcopy(data)})
        self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','needs_retry','reported','completed'));validate_plan(p,self.index)
        self.plan=deepcopy(p);self.generation+=1;self.phase=self.cycle=0;self.record('plan',p,'ready')
    def begin(self,t,provider_ready):
        self.check(t,('ready',));require(provider_ready is True,'fresh external cue provider readiness')
        self.cycle+=1;self.record('begin',{'manual_provider_ready':True,'requested_destination':None,'app_cue_generated':False},'performing')
    def release(self,t,released):
        self.check(t,('performing','reopen_release'));require(released is True,'manual instrument release')
        if self.state=='performing':self.record('release',{},'reporting')
        else:
            state=self.resume;require(state is not None,'resume state');self.resume=None;self.record('reopen_release',{},state)
    def report(self,t,r):
        self.check(t,('reporting',));fields(r,('attack_coverage','obligations','recovery','notes'))
        require(text(r['notes']),'response notes')
        names=TRANSITION if self.phase==0 else RECOVERY;fields(r['obligations'],names)
        require(all(x in YN for x in r['obligations'].values()),'typed source obligation')
        require(type(r['attack_coverage']) is list,'attack report type')
        if self.phase==0:
            require(len(r['attack_coverage'])==8 and r['recovery'] is None,'source eight-attack phase')
            for i,x in enumerate(r['attack_coverage'],1):
                fields(x,('source_order','covered'))
                require(type(x['source_order']) is int and x['source_order']==i and x['covered'] in YN,'source attack report')
            correct=all(x['covered']=='yes' for x in r['attack_coverage'])
        else:
            require(r['attack_coverage']==[],'waiting duration is not eight fixed attacks')
            q=r['recovery'];fields(q,('requested_destination_key','cue_missed','entry_delay_bars','continued_current_bar'))
            require(q['requested_destination_key'] in KEYS and type(q['cue_missed']) is bool,'external request/missed cue')
            require(type(q['entry_delay_bars']) is int and q['entry_delay_bars']>=0,'reported whole-bar delay')
            if q['cue_missed']:require(q['continued_current_bar'] in YN,'missed cue current-bar report')
            else:require(q['continued_current_bar'] is None,'no missed-cue branch')
            correct=(q['entry_delay_bars']==int(q['cue_missed']) and
                     (not q['cue_missed'] or q['continued_current_bar']=='yes'))
        ok=correct and all(x=='yes' for x in r['obligations'].values())
        self.record('report',{'response':r,'manual_requirements_reported':ok,'performance_verified':False,'cue_audio_inspected':False},'reported' if ok else 'needs_retry')
    def retry(self,t,note):
        self.check(t,('reported','needs_retry'));require(text(note),'retry note');self.record('retry',{'note':note},'ready')
    def advance(self,t):
        self.check(t,('reported',));self.record('advance',{},'completed' if self.phase==1 else 'ready')
        if self.phase==0:self.phase=1;self.cycle=0
    def cancel(self,t):
        self.check(t,('setup','ready','performing','reporting','reported','needs_retry','completed','reopen_release'))
        if self.state!='reopen_release':self.resume='ready' if self.state in ('performing','reporting') else self.state
        self.generation+=1;self.record('cancel',{},'cancelled')
    def reopen(self,t):
        self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')

def contract(index,contexts):
    row=ROWS[index]
    return {'schema_version':'fathom-private-section-cue-manual.1','key':KEYS[index],
        'source_transition':{'label':row[1],'last_chord':'G7','first_chord':row[2],'cue':row[3],'task':'4 old attacks + 4 new attacks'},
        'source_harmonic_attack_slots':[{'source_order':i,'phase':'old' if i<=4 else 'new',
            'chord_symbol':'G7' if i<=4 else row[2],'pitch':None,'fret':None,'onset_q':None,'duration_q':None} for i in range(1,9)],
        'source_no_look_instruction':NOLOOK,'source_example_calls':list(CALLS),'source_p6_support':SUPPORT,
        'no_look_destination_options':[{'existing_row_key':k,'source_transition_label':r[1],'first_chord':r[2],
            'master_chart_context':ctx,'association':'Authored source-row/order association to original master chart; no identity rewrite.'} for k,r,ctx in zip(KEYS,ROWS,contexts)],
        'plan_schema':{'prerequisites':['own_instrument','original_workbook'],'bpm':'chosen external finite positive',
            'old_chord':'G7','waiting_chord':'Cmaj7','voicings':'learner-chosen, no fixed source pitch/fret',
            'cue':row[3],'provider_types':['human','external_source'],
            'required_capabilities':list(row[4])+['named_section'],
            'destinations':'all8existing row options with source first-chord and learner voicing/texture realization'},
        'response_schema':{'transition':{'attack_coverage':8,'obligations':list(TRANSITION)},
            'no_look':{'attack_coverage':0,'obligations':list(RECOVERY),'external_requested_key':'one of8existing rows, not preselected by app',
                'cue_missed':'boolean','entry_delay_bars':'manual integer0ifontime,1ifmissed; otherreported delays retained asunsatisfied',
                'continued_current_bar':'yes/no/uncertain whenmissed'},'notes':'required','enum':list(YN)},
        'authored_policies':['Two manual phases: exactrow transition then external-choice no-look drill.',
            'No-look provider chooses among existing source-row destinations; app doesnot choose or synthesize cue.',
            'Provider readiness refreshed before each manual pass; release before reporting.',
            'All source obligations are manual self-report, no acoustic/tempo/destination recognition.',
            'Current instance/key/generation/phase/cycle/action/state token; retry/cancel/reopen preserves history; revised plan restartsphase0.'],
        'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'cue_generated':False,
        'cue_recognized':False,'mastery_awarded':False,'credit_awarded':False,'persistence':False,'canonical_binding':None}
