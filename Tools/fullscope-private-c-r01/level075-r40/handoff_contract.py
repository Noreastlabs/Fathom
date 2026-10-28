"""Six printed role preparations with distinct learner choices and manual duties."""
from copy import deepcopy
from fractions import Fraction
from math import isfinite
from uuid import uuid4
ROWS=(('rhythmlead','Rhythm -> lead','G7 bar 8','leave beat 4 open','lead enters bar 9'),
 ('leadrhythm','Lead -> rhythm','Cmaj7 bar 4','resolve by beat 3','comp enters next bar'),
 ('lowupper','Low -> upper','pre-chorus','guide-tone climb','upper triad on chorus 1'),
 ('upperlow','Upper -> low','chorus end','sustain top voice','low root on verse 1'),
 ('densesparse','Dense -> sparse','bridge -> solo','final accent','rest then motif'),
 ('sparsedense','Sparse -> dense','solo -> chorus','target on beat 3','full groove barline'))
KEYS=tuple(f'exercise-completeness-r01/level075/moduleg/p015-t1-r{i}/{r[0]}' for i,r in enumerate(ROWS,1))
PCS=('C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B')
COMMON=('pulse_and_tempo_held','old_role_texture_correct','destination_role_texture_correct','chosen_realization_followed')
DUTIES=(('g7_at_local_bar8','beat4_left_open','lead_enters_local_bar9'),
 ('cmaj7_at_local_bar4','resolved_by_beat3','comp_enters_next_bar','resolution_fits_harmony'),
 ('guide_tones_climb','upper_triad_on_chorus1','chosen_notes_fit_harmony','chosen_upper_voicing_is_triad'),
 ('top_voice_sustained','low_root_on_verse1','root_fits_verse_harmony'),
 ('final_accent_given','rest_before_motif','chosen_rest_observed','chosen_motif_followed'),
 ('target_on_beat3','full_groove_on_barline','target_fits_harmony'))
CHOICE_FIELDS=(('old_chord','old_local_bar','beat4_plan','lead_entry_local_bar','lead_material'),
 ('old_chord','old_local_bar','resolution_beat','resolution_pitch_class','register','harmonic_rationale','next_bar_comp'),
 ('guide_tone_midi','old_register_anchor_midi','upper_triad_midi','harmonic_basis'),
 ('sustained_top_midi','destination_root_midi','verse_harmony_root_rationale','sustain_handoff_description'),
 ('final_accent_realization','rest_beats','motif_pitch_classes','motif_rhythm_description'),
 ('target_beat','target_pitch_class','harmonic_rationale','groove_entry','full_groove_realization'))
YN=('yes','no','uncertain')
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(o,names):require(type(o) is dict and set(o)==set(names),'field set')
def text(x):return type(x) is str and bool(x.strip())
def midi(x):return type(x) is int and 0<=x<=127
def rational(x):
    require(type(x) is list and len(x)==2 and all(type(v) is int for v in x) and x[1]>0,'rational beat choice');return Fraction(*x)
def bpm(x):
    if type(x) not in (int,float):return False
    try:return isfinite(x) and x>0
    except OverflowError:return False
def validate_choice(c,index):
    fields(c,CHOICE_FIELDS[index])
    if index==0:
        require(c['old_chord']=='G7' and type(c['old_local_bar']) is int and c['old_local_bar']==8,'source G7/local8')
        require(c['beat4_plan']=='intentional_no_rhythm_attack_space' and type(c['lead_entry_local_bar']) is int and c['lead_entry_local_bar']==9 and text(c['lead_material']),'source open4/lead9')
    elif index==1:
        require(c['old_chord']=='Cmaj7' and type(c['old_local_bar']) is int and c['old_local_bar']==4,'source Cmaj7/local4')
        require(1<=rational(c['resolution_beat'])<=3 and c['resolution_pitch_class'] in PCS,'chosen resolve by3')
        require(all(text(c[k]) for k in ('register','harmonic_rationale','next_bar_comp')),'resolution/comp realization')
    elif index==2:
        g=c['guide_tone_midi'];t=c['upper_triad_midi'];anchor=c['old_register_anchor_midi']
        require(type(g) is list and len(g)>=2 and all(midi(n) for n in g) and all(a<b for a,b in zip(g,g[1:])),'chosen ascending guide route')
        require(midi(anchor) and type(t) is list and len(t)==3 and all(midi(n) for n in t) and all(a<b for a,b in zip(t,t[1:])) and min(t)>anchor,'chosen upper voicing relation')
        require(text(c['harmonic_basis']),'manual harmonic basis required')
    elif index==3:
        require(midi(c['sustained_top_midi']) and midi(c['destination_root_midi']) and c['destination_root_midi']<c['sustained_top_midi'],'upper-to-lower chosen relation')
        require(text(c['verse_harmony_root_rationale']) and text(c['sustain_handoff_description']),'root/sustain realization')
    elif index==4:
        require(text(c['final_accent_realization']) and rational(c['rest_beats'])>0,'explicit accent and positive chosen rest')
        require(type(c['motif_pitch_classes']) is list and len(c['motif_pitch_classes'])>=1 and all(p in PCS for p in c['motif_pitch_classes']),'chosen ordered motif')
        require(text(c['motif_rhythm_description']),'motif realization')
    else:
        require(type(c['target_beat']) is int and c['target_beat']==3 and c['target_pitch_class'] in PCS,'source target3 and pitch choice')
        require(c['groove_entry']=='next_barline' and text(c['harmonic_rationale']) and text(c['full_groove_realization']),'source full-groove barline')
def validate_plan(p,index):
    fields(p,('prerequisites','bpm','old_material_texture','destination_material_texture','choice'))
    fields(p['prerequisites'],('own_instrument','original_workbook'));require(all(v is True for v in p['prerequisites'].values()),'manual prerequisites')
    require(bpm(p['bpm']) and text(p['old_material_texture']) and text(p['destination_material_texture']),'chosen material and external tempo')
    validate_choice(p['choice'],index)
class HandoffFlow:
    def __init__(self,key):
        require(key in KEYS,'finite exact source key');self.key=key;self.index=KEYS.index(key);self.instance=uuid4().hex
        self.generation=self.cycle=self.action=0;self.state='setup';self.plan=None;self.history=[];self.resume=None
    def token(self):return (self.instance,self.key,self.generation,self.cycle,self.action,self.state)
    def check(self,t,states):require(type(t) is tuple and t==self.token(),'stale/foreign token');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'cycle':self.cycle,'data':deepcopy(data)});self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','needs_retry','reported','completed'));validate_plan(p,self.index)
        self.plan=deepcopy(p);self.generation+=1;self.cycle=0;self.record('plan',p,'ready')
    def begin(self,t):
        self.check(t,('ready',));self.cycle+=1;self.record('begin',{'chosen_external_bpm':self.plan['bpm'],'host_clock_used':False,
            'source_midi_or_gate_invented':False,'audio_supplied':False},'performing')
    def end_take(self,t,ended):self.check(t,('performing',));require(ended is True,'take end before review');self.record('take_end',{},'await_release')
    def release(self,t,ack):
        self.check(t,('await_release','reopen_release'));require(ack is True,'physical release')
        if self.state=='await_release':self.record('release',{},'reporting')
        else:
            state=self.resume;require(state is not None,'resume state');self.resume=None;self.record('reopen_release',{},state)
    def report(self,t,r):
        self.check(t,('reporting',));fields(r,('common','source_duties','notes'));fields(r['common'],COMMON);fields(r['source_duties'],DUTIES[self.index])
        answers=[*r['common'].values(),*r['source_duties'].values()];require(all(v in YN for v in answers) and text(r['notes']),'typed full manual response')
        ok=all(v=='yes' for v in answers);self.record('report',{'response':r,'manual_requirements_reported':ok,
            'performance_verified':False,'harmonic_correctness_verified':False,'automatic_score':False},'reported' if ok else 'needs_retry')
    def retry(self,t,note):self.check(t,('reported','needs_retry'));require(text(note),'retry note');self.record('retry',{'note':note},'ready')
    def finish(self,t):self.check(t,('reported',));self.record('finish',{'manual_only':True,'source_acceptance':False},'completed')
    def cancel(self,t):
        self.check(t,('setup','ready','performing','await_release','reporting','reported','needs_retry','completed','reopen_release'))
        if self.state!='reopen_release':self.resume='ready' if self.state in ('performing','await_release','reporting') else self.state
        self.generation+=1;self.record('cancel',{},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')
def contract(index):
    row=ROWS[index]
    return {'schema_version':'fathom-private-role-handoff-manual.1','key':KEYS[index],
        'source_row':dict(zip(('handoff','location','preparation','destination'),row[1:])),
        'source_heading':'CHANGE ROLE WITHOUT CHANGING THE CLOCK','source_context_header':'240 CONTACTS',
        'source_local_bars_are_master_indices':False,'source_note_events':[],'fixed_source_contact_count':None,
        'plan_schema':{'prerequisites':['own_instrument','original_workbook'],'bpm':'finite positive external choice',
            'old_material_texture':'required choice','destination_material_texture':'required choice','specific_choice_fields':list(CHOICE_FIELDS[index]),
            'pitch_class_tokens':list(PCS),'choice_validator':'validate_choice(choice, exact row index); explicit authored realization bounds'},
        'response_schema':{'common':list(COMMON),'source_duties':list(DUTIES[index]),'enum':list(YN),'notes':'required'},
        'authored_policies':['Source localG7bar8/Cmaj7bar4 preserved; no master60-bar mapping or chord substitution.',
            'Source attack/gate/fret/tempo values are not invented; all chosen notes/registers/times stay in learner plan.',
            'Beat4 preparation means chosen no-new-rhythm-attack space; no sounded-gate inference.',
            'Resolve beat choice1..3, ascending guide route and upper/lower MIDI relation are interface realization bounds.',
            'Three-note upper-voicing shape is not harmonic certification; triad and harmony remain explicit manual duties.',
            'Dense-to-sparse has a genuine source rest instruction; positive duration is a learner choice, not a source gate.',
            'Take end and release before report; negative/uncertain source duties retained with explicit retry.',
            'Current instance/key/generation/cycle/action/state ownership; cancel/reopen release and interrupted-take repeat.',
            'Idle new plan resets completion; history retained in object only. Separate four-bar handoffcell untouched.'],
        'automatic_evaluation':False,'performance_observed':False,'harmonic_correctness_verified':False,'audio_supplied':False,
        'timing_scheduled':False,'mastery_awarded':False,'credit_awarded':False,'persistence':False,'canonical_binding':None}
