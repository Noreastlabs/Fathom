"""Minor guide motions plus external-partner dominant-third additions, manual only."""
from copy import deepcopy
from uuid import uuid4
KEY='exercise-completeness-r01/level077/modulec/p008-supplement01/minoriivivoiceleading'
CHORDS=('E7','A7','D7','G7','C7','B7');THIRDS=('G#','C#','F#','B','E','D#')
VOCAL=('lower','upper','resolution');LINES={'lower':['D','D','C'],'upper':['A','G#','G'],'resolution':['G#','A']}
PC={'C':0,'C#':1,'D':2,'D#':3,'E':4,'F#':6,'G':7,'G#':8,'A':9,'B':11}
TUNING={'E':40,'A':45,'D':50,'G':55,'B':59,'e':64};YN=('yes','no','uncertain')
V_DUTIES=('sung_exact_order','pitch_targets_correct','heard_before_hand_moves')
D_DUTIES=('partial_chord_heard','third_omitted','third_sung_correct','partner_chord_present_during_addition','single_silent_setup','no_searching','added_third_correct','source_order')
CRITICAL='Critical sung motion: A -> G# -> G and G# -> A.'
DOMINANT='Dominant test: partner plays E7 without its third. Player sings G# and adds it on the guitar. Repeat for A7, D7, G7, C7, and B7.'
NO_SEARCH='After the target is sung, use one silent setup and one attack. Diagnose a wrong attack; do not slide around until the note is found.'
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(o,keys):require(type(o) is dict and set(o)==set(keys),'exact typed field set')
def text(v):return type(v) is str and bool(v.strip())
def validate_plan(p):
    fields(p,('prerequisites','vocal_midi','partner','dominant_realizations'));fields(p['prerequisites'],('own_instrument','original_workbook'))
    require(all(v is True for v in p['prerequisites'].values()),'manual prerequisites');fields(p['vocal_midi'],VOCAL)
    for voice in VOCAL:
        notes=p['vocal_midi'][voice];require(type(notes) is list and len(notes)==len(LINES[voice]) and all(type(n) is int and 0<=n<=127 for n in notes),'chosen vocal MIDI sequence')
        require([n%12 for n in notes]==[PC[n] for n in LINES[voice]],'source vocal target pitch classes')
    lo=p['vocal_midi']['lower'];hi=p['vocal_midi']['upper'];res=p['vocal_midi']['resolution']
    require(lo==[lo[0],lo[0],lo[0]-2] and hi==[hi[0],hi[0]-1,hi[0]-2] and res==[hi[1],hi[0]] and all(a<b for a,b in zip(lo,hi)),'explicit chosen close-register realization')
    partner=p['partner'];fields(partner,('kind','reference','chord_capabilities'));require(partner['kind']=='external_human' and text(partner['reference']),'actual external human partner')
    fields(partner['chord_capabilities'],CHORDS)
    for chord in CHORDS:
        x=partner['chord_capabilities'][chord];fields(x,('reference','can_supply_without_third'));require(text(x['reference']) and x['can_supply_without_third'] is True,'declared per-chord external capability')
    fields(p['dominant_realizations'],CHORDS)
    for chord,third in zip(CHORDS,THIRDS):
        x=p['dominant_realizations'][chord];fields(x,('sung_third_midi','contact'));n=x['sung_third_midi'];c=x['contact'];fields(c,('string','fret'))
        require(type(n) is int and 0<=n<=127 and n%12==PC[third],'chosen dominant third pitch class')
        require(type(c['string']) is str and c['string'] in TUNING and type(c['fret']) is int and 0<=c['fret']<=24 and TUNING[c['string']]+c['fret']==n,'chosen exact third contact')
class MinorFlow:
    def __init__(self,key):
        require(key==KEY,'exact minor supplement only');self.key=key;self.instance=uuid4().hex
        self.generation=self.stage=self.cycle=self.action=0;self.state='setup';self.plan=None;self.history=[];self.resume=None
        self.partner_release_required=False;self.partner_stop_requested=False
    def token(self):return (self.instance,self.key,self.generation,self.stage,self.cycle,self.action,self.state)
    def check(self,t,states):require(type(t) is tuple and t==self.token(),'current source/stage/action owner');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'stage':self.stage,'cycle':self.cycle,'data':deepcopy(data)});self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','reported','needs_retry','completed'));require(not self.partner_release_required,'external role release still pending');validate_plan(p)
        self.plan=deepcopy(p);self.generation+=1;self.stage=self.cycle=0;self.partner_stop_requested=False;self.record('plan',p,'ready')
    def cue(self):
        if self.stage<3:
            voice=VOCAL[self.stage]
            return {'stage_id':'vocal_'+voice,'targets':deepcopy(LINES[voice]),'chord_context':['Bm7b5','E7','Am7'] if self.stage<2 else None,
              'function_context':['iiø','V','i'] if self.stage<2 else None,'target_authority':'printed source',
              'guide_roles':['b3','b7','b3'] if self.stage==0 else ['b7','3','b7'] if self.stage==1 else None,
              'also_covers_printed_critical_descending':self.stage==1}
        j=self.stage-3
        return {'stage_id':'dominant_'+CHORDS[j],'targets':[THIRDS[j]],'chord_context':[CHORDS[j]],'function_context':None,
          'target_authority':'printed E7 third' if j==0 else 'derived major third under explicit repeat command','guide_roles':['3'],'partner_omits':THIRDS[j]}
    def source_player_view(self):
        out={'cue':self.cue(),'audio_supplied_by_app':False,'actual_voicing_notes':None,'omission_acoustically_verified':False,
          'manual_partner_release_required':self.partner_release_required,'manual_stop_requested':self.partner_stop_requested}
        if self.stage>=3:out['instruction']='Stop/release the held source chord and confirm manually' if self.partner_stop_requested else 'Supply named dominant chord without its third; keep it present while learner sings/adds third; stop when requested'
        else:out['instruction']='No source-player audio required for this vocal route'
        return out
    def begin_vocal(self,t,ready):
        self.check(t,('ready',));require(self.stage<3 and ready is True,'vocal stage/current readiness');self.cycle+=1;self.record('begin_vocal',{},'read_cue')
    def cue_read(self,t,targets):
        self.check(t,('read_cue',));require(targets==self.cue()['targets'],'exact named vocal cue');self.record('cue_read',{},'sing_line')
    def sing_line(self,t,ack):self.check(t,('sing_line',));require(ack is True,'full vocal line attempted');self.record('sing_line',{},'end_take')
    def begin_dominant(self,t,confirmation):
        self.check(t,('ready',));require(self.stage>=3,'dominant stage');fields(confirmation,('chord','ready','third_omitted','chord_held'))
        require(confirmation['chord']==CHORDS[self.stage-3] and all(confirmation[k] is True for k in ('ready','third_omitted','chord_held')),'current named partial chord confirmed by external partner')
        self.cycle+=1;self.partner_release_required=True;self.partner_stop_requested=False;self.record('partner_started',{'confirmation':confirmation,'audio_observed':False},'hear_partial')
    def heard_partial(self,t,ack):self.check(t,('hear_partial',));require(ack is True,'partial chord hearing attempted');self.record('heard_partial',{},'sing_third')
    def sing_third(self,t,ack):self.check(t,('sing_third',));require(ack is True,'third singing attempted');self.record('sing_third',{},'silent_setup')
    def setup_target(self,t,ack):self.check(t,('silent_setup',));require(ack is True,'one silent setup');self.record('silent_setup',{},'add_third')
    def add_third(self,t,ack):self.check(t,('add_third',));require(ack is True,'one third attack attempted while source chord present');self.record('add_third',{'actual_attack_count_observed':None},'end_take')
    def end_take(self,t,ack):
        self.check(t,('end_take',));require(ack is True,'take ended/partner stop requested')
        if self.partner_release_required:self.partner_stop_requested=True
        self.record('end_take',{'manual_partner_stop_requested':self.partner_stop_requested,'actual_stop_observed':False},'await_release')
    def release(self,t,confirmation):
        self.check(t,('await_release','reopen_release'));fields(confirmation,('learner_released','partner_stopped'))
        require(confirmation['learner_released'] is True,'learner physical release')
        require(confirmation['partner_stopped'] is True if self.partner_release_required else confirmation['partner_stopped'] is None,'explicit pending external role stop, no invented partner for solo')
        self.partner_release_required=False;self.partner_stop_requested=False
        if self.state=='await_release':self.record('release',{'manual_confirmation':confirmation,'stop_acoustically_verified':False},'reporting')
        else:
            state=self.resume;require(state is not None,'resume state');self.resume=None;self.record('reopen_release',{'manual_confirmation':confirmation},state)
    def report(self,t,r):
        self.check(t,('reporting',));names=('stage_id','source_targets','duties','diagnosis','notes')
        if self.stage>=3:names+=('chosen_contact','attack_count')
        fields(r,names);fields(r['duties'],V_DUTIES if self.stage<3 else D_DUTIES)
        require(r['stage_id']==self.cue()['stage_id'] and r['source_targets']==self.cue()['targets'],'exact source stage/target report binding')
        require(all(type(x) is str and x in YN for x in r['duties'].values()) and type(r['diagnosis']) is str and text(r['notes']),'complete manual outcomes')
        ok=all(x=='yes' for x in r['duties'].values())
        if self.stage>=3:
            c=r['chosen_contact'];fields(c,('string','fret'));require(c==self.plan['dominant_realizations'][CHORDS[self.stage-3]]['contact'] and type(c['fret']) is int,'selected exact contact binding')
            require(type(r['attack_count']) is int and r['attack_count']>=0,'actual nonnegative attack count');ok=ok and r['attack_count']==1
        if not ok:require(text(r['diagnosis']),'failed/uncertain/count diagnosis')
        self.record('report',{'response':r,'manual_requirements_reported':ok,'performance_verified':False,'source_omission_acoustically_verified':False},'reported' if ok else 'needs_retry')
    def next_stage(self,t):
        self.check(t,('reported',));require(self.stage<8,'no tenth stage');self.stage+=1;self.cycle=0;self.record('next_stage',{},'ready')
    def retry(self,t,diagnosis):self.check(t,('reported','needs_retry'));require(text(diagnosis),'retry diagnosis');self.record('retry',{'diagnosis':diagnosis},'ready')
    def finish(self,t):self.check(t,('reported',));require(self.stage==8,'all nine stages required');self.record('finish',{'manual_only':True,'source_acceptance':False,'mastery_awarded':False},'completed')
    def cancel(self,t):
        self.check(t,('setup','ready','read_cue','sing_line','hear_partial','sing_third','silent_setup','add_third','end_take','await_release','reporting','reported','needs_retry','completed','reopen_release'))
        if self.state!='reopen_release':self.resume=self.state if self.state in ('setup','ready','reported','needs_retry','completed') else 'ready'
        if self.partner_release_required:self.partner_stop_requested=True
        self.generation+=1;self.record('cancel',{'manual_partner_stop_requested':self.partner_stop_requested,'actual_stop_observed':False},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')
def contract():
    return {'schema_version':'fathom-private-minor-voiceleading-dominant-manual.1','key':KEY,
      'printed_progression':['Bm7b5','E7','Am7'],'printed_lower':['D','D','C'],'printed_upper':['A','G#','G'],
      'printed_critical_descending':['A','G#','G'],'printed_critical_resolution':['G#','A'],
      'guide_role_context':{'lower':['b3','b7','b3'],'upper':['b7','3','b7'],'critical_resolution':None},
      'critical_descending_coverage':'same performed upper-line route; both printed references retained',
      'source_critical_instruction':CRITICAL,'source_dominant_instruction':DOMINANT,'source_no_search':NO_SEARCH,
      'dominant_targets':[{'chord':c,'third':p,'authority':'printed' if i==0 else 'derived +4 semitones under repeat instruction'} for i,(c,p) in enumerate(zip(CHORDS,THIRDS))],
      'source_extent_header':'10 VOICES | 60 SUNG TARGETS','source_note_events':[],'source_fixed_octave_fret_timing':None,
      'plan_schema':{'vocal_routes':list(VOCAL),'vocal_midi':'authored close-register lower[x,x,x-2], upper[y,y-1,y-2], resolution[y-1,y]',
        'partner':'actual external human with declared per-chord no-third capability; actual source voicing remains unspecified',
        'dominant_realizations':'chosen third MIDI and one exact standard-tuning contact per source chord'},
      'response_schema':{'vocal_duties':list(V_DUTIES),'dominant_duties':list(D_DUTIES),'manual_enum':list(YN),'dominant_attack_count':'actual nonnegative integer, positive report exactly one'},
      'authored_policies':['Three vocal routes then six dominant tests; upper route also covers the identical critical descending source motion.',
        'Chosen close-register MIDI and guitar contacts are explicit authored realizations, not source-fixed octaves or timings.',
        'Partner keeps the partial chord present while learner sings/adds its third. Stop is requested only afterward or on cancellation; release requires explicit manual stop confirmation.',
        'Manual source-role flags do not observe, generate or stop audio. Absence of third and acoustic correctness remain self-reported.',
        'Current-stage/action/release/retry/cancel/new-plan gates; history retained, no synthetic performance credit.'],
      'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'audio_inspected':False,'timing_scheduled':False,
      'credit_awarded':False,'mastery_awarded':False,'persistence':False,'canonical_binding':None}
