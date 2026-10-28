from pathlib import Path
from copy import deepcopy
from dataclasses import replace
from pypdf import PdfReader
import json,hashlib,math,re,sys,importlib.util,resource,datetime
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level074-r29');checks=0
sp=importlib.util.spec_from_file_location('atlas_r29',R/'Tools'/L/'atlas_contract.py');m=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m;sp.loader.exec_module(m)
def check(v,why):
    global checks
    checks+=1
    if not v:raise AssertionError(why)
def refused(fn,s):
    before=s.snapshot()
    try:fn()
    except ValueError:check(before==s.snapshot(),'refusal preserves state')
    else:raise AssertionError('unexpected accepted mutation')
def yes(s):return {f:'yes' for f in s.view()['response_fields']}
def at(c,step):
    s=m.AtlasReview(c)
    for n in range(step):s.respond(s.token(),yes(s),'')
    return s
def suspend(s):
    before=s.snapshot();token=s.token();s.cancel(token);refused(lambda:s.reopen(token),s)
    refused(lambda:s.respond(s.token(),yes(s),''),s);s.reopen(s.token());after=s.snapshot()
    for k in ('key','cycle','step','stage','responses','view','reference_review_complete'):
        check(after[k]==before[k],'reopen retains '+k)
    check(after['generation']==before['generation']+2,'generation updated')
r=json.loads((R/'Build'/L/'reference-atlas-overlay.jsonl').read_text());c=r['implementation']['task']['contract']
old=json.loads((R/'Build/fullscope-private-c-r01/level074-r06/implementation-packet.jsonl').read_text().splitlines()[0])
source=json.loads((R/'Build'/L/'source-check.json').read_text());pdf=PdfReader(R/source['original_pdf']['path']);text=pdf.pages[1].extract_text();norm=' '.join(text.split())
txt=(R/source['original_txt']['path']).read_text().splitlines()
check(r['package_key']==old['package_key'] and r['source_identity']==old['source_identity'],'official identity unchanged')
check(r['implementation']['events']==old['implementation']['events']==[],'no invented contact/rest events')
check(c['source_heading'] in norm and len(c['concept_comparisons'])==5,'four-question heading and allfive rows retained')
for row in c['concept_comparisons']:
    check(' '.join(row.values()) in norm,'exact source comparison row')
    check(set(row)=={'concept','what_changes','what_remains_fixed','repair_cue'},'structured complete concept schema')
grid=c['sixteenth_grid'];count=re.search(r'Count\|([^|]+)\|',text).group(1).split('--')[:-1]
hands=re.search(r'Hand\s*\|([^|]+)\|',text).group(1).split('--')[:-1]
check(len(count)==len(hands)==16,'original16 count/hand slots')
for i,slot in enumerate(grid['slots']):
    check(slot['slot']==i+1 and slot['spoken_count']==count[i] and slot['printed_hand']==hands[i],'exact original labels/hand path')
    check(slot['beat_number']==i//4+1 and slot['slot_within_beat']==i%4+1,'explicit sixteenth indexing')
check(grid['accent_rule'] in norm and 'does not restart' in grid['accent_rule'],'accent overlay nohandrestart')
for row in c['full_cycle_returns']:
    group=row['group'];length=math.lcm(16,group)
    check(length==row['sixteenth_slots'] and length//16==row['bars'] and length//group==row['accents']==16,'independent full-cycle arithmetic')
    check(' '.join(str(v) for v in row.values()) in norm,'printed PDF return row')
    check(f'Group of {group} returns after {length} slots = {row["bars"]} bars = 16 groups.' in txt,'paired TXT arithmetic')
    accent_slots=list(range(0,length,group))
    check(len(accent_slots)==16 and any(n%16 for n in accent_slots),'accent drift across barline')
    check(all(('D' if n%2==0 else 'U')==hands[n%16] for n in accent_slots),'accent positions do not reset D/U')
check(c['body_pulse']['full_instruction'] in norm and c['body_pulse']['specific_large_groups'] is None,'full body instruction no fabricated group')
check(c['source_event_count']==0 and not c['instrument_required_for_reference_review'],'reference no invented performance prerequisite')
s=m.AtlasReview(c)
for step in range(8):
    check(s.step==step and s.stage=='review','finite source step order')
    check(s.view()==c['review_steps'][step],'full structured source payload shown')
    v=s.view();v['response_fields'].append('bad external mutation');check(s.view()==c['review_steps'][step],'defensive source view')
    suspend(s);t=s.token()
    for token in (m.AtlasReview(c).token(),replace(t,key='other'),replace(t,step=99),replace(t,cycle=77)):
        refused(lambda z=token:s.respond(z,yes(s),''),s)
    q=yes(s);q.pop(next(iter(q)));refused(lambda:s.respond(s.token(),q,''),s)
    q=yes(s);q['extra']='yes';refused(lambda:s.respond(s.token(),q,''),s)
    q=yes(s);q[next(iter(q))]=True;refused(lambda:s.respond(s.token(),q,''),s)
    refused(lambda:s.respond(s.token(),yes(s),None),s)
    refused(lambda:s.review_again(s.token(),'premature'),s)
    q=yes(s);t=s.token();s.respond(t,q,'read, no performance claimed');q.clear()
    check(len(s.responses[-1]['acknowledgments'])==3,'retained acknowledgment detached')
    refused(lambda:s.respond(t,{},''),s)
    check(s.snapshot()['reference_review_complete']==(step==7),'only complete after all8 stages')
suspend(s)
for flag in ('practice_performed','audio_supplied','knowledge_graded','Attempt_credit','mastery_awarded','persistence_supplied'):
    check(s.snapshot()[flag] is False,'no '+flag)
prior=deepcopy(s.responses);stale=s.token();refused(lambda:s.review_again(s.token(),''),s)
s.review_again(s.token(),'revisit reference');check(s.cycle==2 and s.step==0 and all(x in s.responses for x in prior),'repeat keepsprior responses')
refused(lambda:s.respond(stale,yes(s),''),s)
for step in range(8):
    for field in c['review_steps'][step]['response_fields']:
        for value in ('no','uncertain'):
            s=at(c,step);q=yes(s);q[field]=value;s.respond(s.token(),q,'keep this unresolved')
            check(s.stage=='needs_review' and s.step==step,'negative or uncertainty cannot advance')
            check(s.responses[-1]['acknowledgments']==q and s.responses[-1]['notes']=='keep this unresolved','retain exact manual response')
            refused(lambda:s.respond(s.token(),yes(s),''),s);suspend(s)
            s.review_again(s.token(),'read exact source again');check(s.step==step,'same-step repeat')
            s.respond(s.token(),yes(s),'reviewed');check(s.step==min(step+1,7),'then one step only')
for ref in (source['original_pdf'],source['original_txt']):
    b=(R/ref['path']).read_bytes();check(len(b)==ref['bytes'] and hashlib.sha256(b).hexdigest()==ref['sha256'],'source final pin')
out={'status':'PASS','checks':checks,'manual_reference_cases':1,'concept_rows':5,'reference_slots':16,'return_rows':3,
     'source_events':0,'review_steps':8,'synthetic_review_responses_only':True,'practice_performed':False,'native_runs':0,
     'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
