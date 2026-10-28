"""One six-key manual guide-voice task. Chosen articulation is not source timing."""
from copy import deepcopy
from uuid import uuid4
KEY='exercise-completeness-r01/level077/modulec/p007-supplement01/majoriivivoiceleading'
TONICS=('C','G','D','A','E','F')
SCALES={'C':('C','D','E','F','G','A','B'),'G':('G','A','B','C','D','E','F#'),
 'D':('D','E','F#','G','A','B','C#'),'A':('A','B','C#','D','E','F#','G#'),
 'E':('E','F#','G#','A','B','C#','D#'),'F':('F','G','A','Bb','C','D','E')}
PC={'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'Bb':10,'B':11}
TUNING={'E':40,'A':45,'D':50,'G':55,'B':59,'e':64};VOICES=('lower','upper');MODES=('lower_alone','upper_alone','combined')
COMMON=('sung_three_target_line','from_chord_name_and_function','not_copied_by_fret_distance','source_order')
COMBINED=('voices_coordinated','other_voice_played','no_searching','chosen_common_tone_policy');YN=('yes','no','uncertain')
PRACTICE='Sing each line alone; then sing one while playing the other.'
TRANSPOSE='Transposition command: move the ii-V-I guide-tone pair through G, D, A, E, and F major. The voice must be sung from the chord name and function, not copied by fret distance.'
def reference(key):
    s=SCALES[key]
    return {'key':key,'chords':[s[1]+'m7',s[4]+'7',s[0]+'maj7'],'functions':['ii','V','I'],
      'lower':[s[3],s[3],s[2]],'upper':[s[0],s[6],s[6]],'lower_roles':['b3','b7','3'],'upper_roles':['b7','3','7'],
      'provenance':'printed C source' if key=='C' else 'derived from explicit source transposition request','onset_duration':None}
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(o,keys):require(type(o) is dict and set(o)==set(keys),'exact typed field set')
def text(x):return type(x) is str and bool(x.strip())
def validate_plan(p):
    fields(p,('prerequisites','keys'));fields(p['prerequisites'],('own_instrument','original_workbook'));require(all(v is True for v in p['prerequisites'].values()),'manual prerequisites')
    fields(p['keys'],TONICS)
    for key in TONICS:
        k=p['keys'][key];fields(k,('combined_sung_voice','midi','contacts','articulations'))
        require(type(k['combined_sung_voice']) is str and k['combined_sung_voice'] in VOICES,'explicit combined sung voice')
        for group in ('midi','contacts','articulations'):fields(k[group],VOICES)
        ref=reference(key)
        for voice in VOICES:
            notes=k['midi'][voice];contacts=k['contacts'][voice];arts=k['articulations'][voice]
            require(type(notes) is list and len(notes)==3 and all(type(n) is int and 0<=n<=127 for n in notes),'three chosen MIDI targets')
            require([n%12 for n in notes]==[PC[n] for n in ref[voice]],'source/derived voice pitch classes')
            expected=[notes[0],notes[0],notes[0]-1] if voice=='lower' else [notes[0],notes[0]-1,notes[0]-1]
            require(notes==expected,'explicit chosen close voice-leading realization')
            require(type(contacts) is list and len(contacts)==3 and type(arts) is list and len(arts)==3,'three contacts and selected articulations')
            for j,(note,c,art) in enumerate(zip(notes,contacts,arts)):
                fields(c,('string','fret'));s=c['string'];f=c['fret']
                require(type(s) is str and s in TUNING and type(f) is int and 0<=f<=24 and TUNING[s]+f==note,'selected voice contact exact MIDI')
                changed=j==0 or note!=notes[j-1]
                require(type(art) is str and art in (('attack',) if changed else ('hold','rearticulate')),'chosen articulation respects common/new pitch')
                if art=='hold':require(c==contacts[j-1],'held common tone keeps same contact')
        require(all(a<b for a,b in zip(k['midi']['lower'],k['midi']['upper'])),'chosen lower/upper voice ordering')
class VoiceLeadingFlow:
    def __init__(self,key):
        require(key==KEY,'exact one supplement only');self.key=key;self.instance=uuid4().hex
        self.generation=self.key_index=self.phase=self.station=self.cycle=self.action=0;self.state='setup';self.plan=None;self.history=[];self.resume=None
    def token(self):return (self.instance,self.key,self.generation,self.key_index,self.phase,self.station,self.cycle,self.action,self.state)
    def check(self,t,states):require(type(t) is tuple and t==self.token(),'current source/key/phase/station/action owner');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'key_index':self.key_index,'phase':self.phase,'station':self.station,'cycle':self.cycle,'data':deepcopy(data)});self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','reported','needs_retry','completed'));validate_plan(p);self.plan=deepcopy(p);self.generation+=1
        self.key_index=self.phase=self.station=self.cycle=0;self.record('plan',p,'ready')
    def assignment(self):
        require(self.plan is not None,'plan required');k=self.plan['keys'][TONICS[self.key_index]]
        sung=VOICES[self.phase] if self.phase<2 else k['combined_sung_voice'];played=None if self.phase<2 else ('upper' if sung=='lower' else 'lower')
        return {'sung':sung,'played':played}
    def view(self):
        ref=reference(TONICS[self.key_index]);out={'state':self.state,'mode':MODES[self.phase],'source_reference':ref,'audio_supplied':False,'source_fixed_note_events':[]}
        if self.plan is not None:
            assign=self.assignment();p=self.plan['keys'][ref['key']];j=self.station
            out.update(assignment=assign,current_cue={'source_station':j+1,'chord':ref['chords'][j],'function':ref['functions'][j],
              'sung_pitch':ref[assign['sung']][j],'chosen_sung_midi':p['midi'][assign['sung']][j],
              'played_contact':None if assign['played'] is None else deepcopy(p['contacts'][assign['played']][j]),
              'chosen_played_articulation':None if assign['played'] is None else p['articulations'][assign['played']][j]})
        return out
    def begin(self,t,ready):self.check(t,('ready',));require(ready is True,'current learner/instrument readiness');self.cycle+=1;self.station=0;self.record('begin',{},'cue')
    def cue_read(self,t,chord,function):
        self.check(t,('cue',));ref=reference(TONICS[self.key_index]);require(chord==ref['chords'][self.station] and function==ref['functions'][self.station],'exact named chord/function cue')
        self.record('cue_read',{'chord':chord,'function':function},'perform')
    def perform_station(self,t,ack):
        self.check(t,('perform',));require(ack is True,'manual station attempted');j=self.station
        self.record('perform_station',{'station':j+1,'performance_observed':False},'end_take' if j==2 else 'cue')
        if j<2:self.station+=1
    def end_take(self,t,ack):self.check(t,('end_take',));require(ack is True,'manual take ended');self.record('end_take',{},'await_release')
    def release(self,t,ack):
        self.check(t,('await_release','reopen_release'));require(ack is True,'physical release required')
        if self.state=='await_release':self.record('release',{},'reporting')
        else:
            state=self.resume;require(state is not None,'resume state');self.resume=None
            if state=='ready':self.station=0
            self.record('reopen_release',{},state)
    def expected_counts(self):
        require(self.phase==2,'solo has no forced guitar attacks');p=self.plan['keys'][TONICS[self.key_index]];voice=self.assignment()['played']
        return [0 if x=='hold' else 1 for x in p['articulations'][voice]]
    def report(self,t,r):
        self.check(t,('reporting',));names=('key','mode','chords','sung_voice','played_voice','duties','diagnosis','notes')
        if self.phase==2:names+=('played_contacts','actual_attack_counts','combined_duties')
        fields(r,names);fields(r['duties'],COMMON);key=TONICS[self.key_index];ref=reference(key);assignment=self.assignment()
        require(r['key']==key and r['mode']==MODES[self.phase] and r['chords']==ref['chords'] and r['sung_voice']==assignment['sung'] and r['played_voice']==assignment['played'],'exact source/key/phase/voice report binding')
        require(all(type(v) is str and v in YN for v in r['duties'].values()) and type(r['diagnosis']) is str and text(r['notes']),'complete manual report')
        ok=all(v=='yes' for v in r['duties'].values());counts=None
        if self.phase==2:
            fields(r['combined_duties'],COMBINED);require(all(type(v) is str and v in YN for v in r['combined_duties'].values()),'combined manual outcomes')
            p=self.plan['keys'][key];contacts=r['played_contacts'];require(contacts==p['contacts'][assignment['played']] and type(contacts) is list and all(type(c) is dict and set(c)=={'string','fret'} and type(c['fret']) is int for c in contacts),'chosen played contact binding')
            actual=r['actual_attack_counts'];require(type(actual) is list and len(actual)==3 and all(type(x) is int and x>=0 for x in actual),'three actual manual attack counts')
            counts=self.expected_counts();ok=ok and all(v=='yes' for v in r['combined_duties'].values()) and actual==counts
        if not ok:require(text(r['diagnosis']),'wrong/uncertain/count failure diagnosis')
        self.record('report',{'response':r,'chosen_articulation_expected_counts':counts,'source_fixed_attack_count':False,'manual_requirements_reported':ok,'performance_verified':False},'reported' if ok else 'needs_retry')
    def next_subpass(self,t):
        self.check(t,('reported',));require(not(self.key_index==5 and self.phase==2),'all eighteen complete, no extra key')
        if self.phase<2:self.phase+=1
        else:self.key_index+=1;self.phase=0
        self.station=self.cycle=0;self.record('next_subpass',{},'ready')
    def retry(self,t,diagnosis):self.check(t,('reported','needs_retry'));require(text(diagnosis),'retry diagnosis');self.station=0;self.record('retry',{'diagnosis':diagnosis},'ready')
    def finish(self,t):
        self.check(t,('reported',));require(self.key_index==5 and self.phase==2,'all six keys and three phases required');self.record('finish',{'manual_only':True,'source_acceptance':False,'mastery_awarded':False},'completed')
    def cancel(self,t):
        self.check(t,('setup','ready','cue','perform','end_take','await_release','reporting','reported','needs_retry','completed','reopen_release'))
        if self.state!='reopen_release':self.resume=self.state if self.state in ('setup','ready','reported','needs_retry','completed') else 'ready'
        self.generation+=1;self.record('cancel',{},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')
def contract():
    return {'schema_version':'fathom-private-major-voiceleading-manual.1','key':KEY,
      'printed_C_reference':reference('C'),'derived_requested_transpositions':[reference(k) for k in TONICS[1:]],
      'source_practice':PRACTICE,'source_transposition':TRANSPOSE,'source_extent_header':'10 VOICES | 60 SUNG TARGETS',
      'source_note_events':[],'source_fixed_octaves_frets_timing':None,'printed_guide_pitch_class_occurrences':6,'derived_transposed_guide_targets':30,
      'plan_schema':{'keys':list(TONICS),'phases':list(MODES),'combined_sung_voice':['lower','upper'],
        'chosen_voice_lines':'lower[x,x,x-1], upper[y,y-1,y-1], lower below upper, exact derived pitch classes',
        'contacts':'chosen MIDI-matching standard-tuning string/fret0..24 per voice/station',
        'articulation':'initial/new pitch attack; common pitch chosen hold with same contact or rearticulate'},
      'response_schema':{'common':list(COMMON),'combined':list(COMBINED),'outcome_enum':list(YN),'combined_counts':'three actual self-reported counts checked against chosen articulation, not source-fixed attacks'},
      'authored_policies':['Six keys in source-list order, each lower alone/upper alone/chosen one sung while other played;18 manual subpasses, not18 source fixed-time events.',
        'Selected close-register MIDI and common-tone hold/rearticulation are authored learner choices, not printed octaves, ties or attack counts.',
        'Named chord/function cues guard source order; no fret-distance-copy shortcut or automatic acoustic check.',
        'No inter-station report required; end/release before whole-subpass report. Solo phases have no forced guitar attacks.',
        'Current source/key/phase/station/action tokens, cancellation/release/retry, reset-to-C on new plan with history retained.'],
      'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'audio_inspected':False,'timing_scheduled':False,
      'credit_awarded':False,'mastery_awarded':False,'persistence':False,'canonical_binding':None}
