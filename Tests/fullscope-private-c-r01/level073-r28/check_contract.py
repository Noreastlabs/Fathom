from pathlib import Path
from dataclasses import replace
from copy import deepcopy
from pypdf import PdfReader
import json,hashlib,re,sys,importlib.util,resource,datetime
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level073-r28')
spec=importlib.util.spec_from_file_location('capstone_r28',R/'Tools'/L/'capstone_contract.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
checks=0
def check(v,why):
    global checks
    checks+=1
    if not v:raise AssertionError(why)
def refused(fn,s):
    before=s.snapshot()
    try:fn()
    except ValueError:check(before==s.snapshot(),'exact refusal no mutation')
    else:raise AssertionError('unexpected accepted action')
def positive():
    return {'performed_pass_form':'yes','sixteen_bar_schedule':'yes','reflection':'',
            'blocks':[{'block':i,**{k:'yes' for k in m.CapstoneSession.block_fields}} for i in range(1,5)]}
def suspend(s):
    before=s.snapshot();old=s.token();s.cancel(old)
    refused(lambda:s.reopen(old,True),s);refused(lambda:s.reopen(s.token(),False),s)
    s.reopen(s.token(),True);after=s.snapshot()
    for k in ('route','stage','cycle','pass','timing_choice','phrase_choice','current_report','completed_passes','history','source_script','manual_reports_complete'):
        check(after[k]==before[k],'cancel/reopen retains '+k)
    check(after['generation']==before['generation']+2,'queued callback generation invalidated')
def report_ready(c,target=1,phrase=True):
    s=m.CapstoneSession(c);s.configure(s.token(),True,'learner chosen counted pulse with beat4 speech')
    if phrase:s.choose_phrase(s.token(),'learner free phrase outline preserving all sixteen source bars')
    for p in range(1,target+1):
        s.begin(s.token());s.release(s.token(),True)
        if p<target:s.respond(s.token(),positive())
    return s

r=json.loads((R/'Build'/L/'capstone-overlay.jsonl').read_text())
old=[json.loads(x) for x in (R/'Build/fullscope-private-c-r01/level073-r07/implementation-packet.jsonl').read_text().splitlines()][38]
c=r['implementation']['task']['contract'];source=json.loads((R/'Build'/L/'source-check.json').read_text())
lines=(R/source['original_txt']['path']).read_text().splitlines();pdf=PdfReader(R/source['original_pdf']['path'])
check(r['package_key']==old['package_key'] and r['source_identity']==old['source_identity'],'exact official key')
check(r['implementation']['events']==old['implementation']['events'],'all64 old event objects unchanged')
for page in (17,18):
    norm=' '.join(pdf.pages[page-1].extract_text().split())
    for text in (c['source_header'],c['full_source_instruction'],c['source_pass_footer']):check(text in norm,'complete joined original instruction')
check(c['source_txt_pass_instructions']==lines[562:565],'all original TXT pass lines')
tuning={'e':64,'B':59,'G':55,'D':50,'A':45,'E':40};numbers={'e':1,'B':2,'G':3,'D':4,'A':5,'E':6}
pcs={'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'B':11};parsed=[]
for j in old['provenance']['exact_conversion_joins']:
    lo,hi=j['txt_event_lines'];tab=lines[lo-1:hi];page=pdf.pages[j['pdf_physical_page']-1].extract_text()
    for line in tab:check(line.strip() in page,'literal original TAB parity')
    notes=tab[0].split('|')[1:-1];roles=tab[1].split('|')[1:-1]
    raw={line.strip().split('|')[0]:line.strip().split('|')[1:-1] for line in tab[2:]}
    for b,segment in enumerate(notes):
        for note in re.finditer(r'[A-G](?:#|b)?',segment):
            column=note.start();found=[(s,int(f.group())) for s,parts in raw.items() for f in re.finditer(r'\d+',parts[b]) if f.start()==column]
            check(len(found)==1,'exact original contact');string,fret=found[0]
            role=re.match(r'[A-Za-z0-9#]+',roles[b][column:]).group()
            parsed.append((string,fret,note.group(),role,j['facts']['absolute_bars'][b]))
check(len(parsed)==64,'64contacts parsed')
for expected,e in zip(parsed,r['implementation']['events']):
    string,fret,note,role,bar=expected;midi=tuning[string]+fret
    check((e['string_name'],e['fret'],e['printed_note'],e['printed_role'],e['source_absolute_bar'])==expected,'original event semantics')
    check(e['string_number']==numbers[string] and e['written_pitch_theory']['midi_at_stated_standard_tuning']==midi and midi%12==pcs[note],'independent MIDI parity')
    check(e['onset_q'] is None and e['duration_q'] is None and e['finger'] is None,'null original timing/fingering')
lookup={e['source_order']:e for e in r['implementation']['events']}
check(c['pass_contracts'][0]['source_orders']==list(range(1,65)),'first pass64 original references')
check(len(c['pass_contracts'][1]['guide_dyads'])==16,'one guide-dyad projection per bar')
for dyad in c['pass_contracts'][1]['guide_dyads']:
    refs=[lookup[o] for o in dyad['source_orders']]
    check(len(refs)==2 and refs[0]['printed_role'] in ('3','b3') and refs[1]['printed_role'] in ('7','b7'),'exact guide-tone roles')
    check(all(e['source_absolute_bar']==dyad['source_bar'] for e in refs),'no crossing bar source refs')
    check(refs[0]['string_name']!=refs[1]['string_name'],'dyad uses distinct strings')
    check(abs(refs[0]['fret']-refs[1]['fret'])<=4,'bounded inspected fret span, no inferred new fingering')
    for e,p in zip(refs,dyad['positions']):
        check(p=={'string_name':e['string_name'],'fret':e['fret'],'printed_note':e['printed_note'],'midi':e['written_pitch_theory']['midi_at_stated_standard_tuning']},'projection copies no substituted contact')
    check(dyad['onset_q'] is None and dyad['duration_q'] is None,'no projected native timing')
check(c['pass_contracts'][2]['fixed_source_note_sequence'] is False and c['pass_contracts'][2]['learner_choice'] is None,'free phrase remains choice')
for i,b in enumerate(c['source_script']['blocks']):
    start=4*i+1
    check([b[k]['bar'] for k in ('current_tonic','shared_pivot','next_dominant','new_tonic')]==list(range(start,start+4)),'four-bar functional order')
    cue=b['spoken_destination_cue'];check(cue['bar']==start+1 and cue['beat_in_bar']==4 and cue['say']==['G major','D major','A major','E major'][i],'exact printed destination cue')
    check(cue['quarter_time'] is None and cue['coincident_source_order'] is None,'speech is not a fabricated attack or quarter projection')

s=m.CapstoneSession(c);suspend(s);refused(lambda:s.begin(s.token()),s)
for value in (False,None,1):refused(lambda x=value:s.configure(s.token(),x,'pulse'),s)
for value in ('',' ',None,5):
    refused(lambda x=value:s.configure(s.token(),True,x),s)
    refused(lambda x=value:s.choose_phrase(s.token(),x),s)
s.choose_phrase(s.token(),'initial phrase');check(s.stage=='setup','phrase alone does not supply instrument/timing')
s.configure(s.token(),True,'first timing');s.configure(s.token(),True,'revised timing');s.choose_phrase(s.token(),'revised phrase')
check(len(s.history)==2,'old timing/phrase choices preserved');suspend(s)
for number in (1,2,3):
    check(s.pass_number==number and s.stage=='ready','exact next pass')
    token=s.token();foreign=m.CapstoneSession(c).token()
    for invalid in (foreign,replace(token,route='other'),replace(token,cycle=99),replace(token,pass_number=4),replace(token,action=99)):
        refused(lambda t=invalid:s.begin(t),s)
    s.begin(token);refused(lambda:s.begin(token),s);suspend(s)
    refused(lambda:s.respond(s.token(),positive()),s);refused(lambda:s.release(s.token(),False),s)
    rel=s.token();s.release(rel,True);refused(lambda:s.release(rel,True),s);suspend(s)
    refused(lambda:s.repeat_cycle(s.token(),'premature'),s)
    for mutate in ('missing_block','extra_block','reverse','bool_block','missing_cue','extra_field','bad_reply'):
        q=positive()
        if mutate=='missing_block':q['blocks'].pop()
        elif mutate=='extra_block':q['blocks'].append(deepcopy(q['blocks'][0]))
        elif mutate=='reverse':q['blocks'].reverse()
        elif mutate=='bool_block':q['blocks'][0]['block']=True
        elif mutate=='missing_cue':del q['blocks'][0]['destination_announced_on_pivot_beat4']
        elif mutate=='extra_field':q['blocks'][0]['claimed_audio_score']=100
        else:q['performed_pass_form']=True
        refused(lambda x=q:s.respond(s.token(),x),s)
    q=positive();t=s.token();s.respond(t,q);q['blocks'][0]['new_tonic']='no'
    check(s.completed_passes[number]['blocks'][0]['new_tonic']=='yes','captured response detached from caller')
    refused(lambda:s.respond(t,positive()),s)
    check(len(s.completed_passes)==number,'one pass exactly per report')
    check(s.snapshot()['manual_reports_complete']==(number==3),'no early completion')
suspend(s)
for flag in ('performance_observed','audio_supplied','automatic_evaluation','Attempt_credit','mastery_awarded','persistence_supplied'):
    check(s.snapshot()[flag] is False,'no '+flag)
history=deepcopy(s.history);choices=(s.timing_choice,s.phrase_choice);old=s.token()
s.repeat_cycle(old,'repeat complete exercise');suspend(s);refused(lambda:s.repeat_release(s.token(),False),s)
s.repeat_release(s.token(),True);check(s.cycle==2 and s.pass_number==1 and not s.completed_passes,'explicit fresh cycle')
check((s.timing_choice,s.phrase_choice)==choices and all(x in s.history for x in history),'cycle retains source choices/reports')
refused(lambda:s.repeat_cycle(old,'stale'),s)

# Missing free-phrase choice refuses pass3 without losing the successful earlier passes.
s=report_ready(c,2,False);s.respond(s.token(),positive());check(s.stage=='choose_phrase' and len(s.completed_passes)==2,'required pass3 choice fence')
refused(lambda:s.begin(s.token()),s);suspend(s);s.choose_phrase(s.token(),'learner-described freely chosen realization')
check(s.stage=='ready' and s.pass_number==3,'choice opens only correct pass')

# Every source obligation/cue is causally required in all three passes.
for target in (1,2,3):
    for field in ('performed_pass_form','sixteen_bar_schedule',*m.CapstoneSession.block_fields):
        indexes=(None,) if field in ('performed_pass_form','sixteen_bar_schedule') else range(4)
        for index in indexes:
            for value in ('no','uncertain'):
                ss=report_ready(c,target);q=positive()
                if index is None:q[field]=value
                else:q['blocks'][index][field]=value
                prior=deepcopy(ss.completed_passes);token=ss.token();ss.respond(token,q)
                check(ss.stage=='retry_required' and ss.pass_number==target,'unsatisfied duty cannot advance')
                check(ss.current_report==q and ss.completed_passes==prior,'negative/uncertain and earlier reports retained')
                refused(lambda:ss.begin(ss.token()),ss);refused(lambda:ss.respond(token,positive()),ss)
                ss.request_retry(ss.token(),'rehearse current pass again');refused(lambda:ss.retry_release(ss.token(),False),ss)
                ss.retry_release(ss.token(),True);check(ss.pass_number==target and ss.completed_passes==prior,'retry only current pass')
                ss.begin(ss.token());ss.release(ss.token(),True);ss.respond(ss.token(),positive())
                check(target in ss.completed_passes and any(x.get('response')==q for x in ss.history),'successful retry preserves unsuccessful evidence')
check(c['source_script']==m.CapstoneSession(c).snapshot()['source_script'],'source remains stable')
for ref in (source['original_pdf'],source['original_txt']):
    b=(R/ref['path']).read_bytes();check(len(b)==ref['bytes'] and hashlib.sha256(b).hexdigest()==ref['sha256'],'original source pins unchanged')
out={'status':'PASS','checks':checks,'source_contacts_independently_parsed':64,'guide_dyad_reference_uses':32,
     'complete_manual_cases':1,'passes':3,'spoken_cues_per_pass':4,'physical_pages_text_checked':[17,18],
     'synthetic_manual_responses_only':True,'new_source_events':0,'native_runs':0,
     'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
     'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
