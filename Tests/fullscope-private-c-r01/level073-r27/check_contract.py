from pathlib import Path
from dataclasses import replace
from copy import deepcopy
from pypdf import PdfReader
import json, hashlib, re, sys, importlib.util, resource, datetime

R = Path(__file__).resolve().parents[3]
L = Path('fullscope-private-c-r01/level073-r27')
spec = importlib.util.spec_from_file_location('study_r27', R/'Tools'/L/'study_contract.py')
m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)
checks = 0
def check(value, why):
    global checks
    checks += 1
    if not value: raise AssertionError(why)
def refused(fn, session):
    old = session.snapshot()
    try: fn()
    except ValueError: check(old == session.snapshot(), 'refusal leaves exact state unchanged')
    else: raise AssertionError('unexpected accepted mutation')
def positive():
    return {'printed_order': 'yes', 'four_tones_each_bar': 'yes', 'modulation_route_addressed': 'yes',
            'destination_confirmed': 'yes', 'destination_bars': [6,7,8], 'audit_response': 'named',
            'exact_bar': 6, 'reflection': ''}
def reported_session(c):
    s = m.StudySession(c); s.configure(s.token(), True, 'learner chosen relaxed pulse')
    s.begin(s.token()); s.release(s.token(), True); return s
def suspend_restore(s):
    before = s.snapshot(); stale = s.token(); s.cancel(stale)
    refused(lambda: s.reopen(stale, True), s)
    refused(lambda: s.reopen(s.token(), False), s)
    s.reopen(s.token(), True)
    after = s.snapshot()
    for k in ('route','stage','pass','choice','report','history','source_script','manual_reports_complete'):
        check(after[k] == before[k], 'cancel/reopen retains '+k)
    check(after['generation'] == before['generation']+2, 'cancel and reopen invalidate queued tokens')

rows = [json.loads(x) for x in (R/'Build'/L/'eight-bar-study-overlays.jsonl').read_text().splitlines()]
base = [json.loads(x) for x in (R/'Build/fullscope-private-c-r01/level073-r07/implementation-packet.jsonl').read_text().splitlines()][34:38]
source = json.loads((R/'Build'/L/'source-check.json').read_text())
lines = (R/source['original_txt']['path']).read_text().splitlines()
pdf = PdfReader(R/source['original_pdf']['path'])
tuning = {'e':64, 'B':59, 'G':55, 'D':50, 'A':45, 'E':40}
numbers = {'e':1, 'B':2, 'G':3, 'D':4, 'A':5, 'E':6}
pcs = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'B':11}
contacts = 0
for r, old in zip(rows, base):
    check(r['package_key'] == old['package_key'] and r['source_identity'] == old['source_identity'], 'identity exact')
    check(r['implementation']['events'] == old['implementation']['events'], 'all old event objects unchanged')
    c = r['implementation']['task']['contract']; page = pdf.pages[c['source_script']['pdf_physical_page']-1].extract_text()
    norm = ' '.join(page.split())
    for text in (c['source_header'], c['source_audit_prompt'], c['source_script']['explanation']):
        check(text in norm, 'full original printed obligation preserved')
    parsed = []
    for j in old['provenance']['exact_conversion_joins']:
        lo,hi = j['txt_event_lines']; block = lines[lo-1:hi]
        for line in block: check(line.strip() in page, 'literal original TXT TAB agrees with PDF stream')
        notes = block[0].split('|')[1:-1]; roles = block[1].split('|')[1:-1]
        raw = {line.strip().split('|')[0]: line.strip().split('|')[1:-1] for line in block[2:]}
        for b, segment in enumerate(notes):
            for note in re.finditer(r'[A-G](?:#|b)?', segment):
                col = note.start(); found = [(s,int(f.group())) for s,cells in raw.items()
                                             for f in re.finditer(r'\d+', cells[b]) if f.start() == col]
                check(len(found) == 1, 'one exact printed contact')
                string,fret = found[0]
                role = re.match(r'[A-Za-z0-9#]+', roles[b][col:]).group()
                parsed.append((string,fret,note.group(),role,j['facts']['absolute_bars'][b]))
    check(len(parsed) == 32, '32 source contacts')
    for expected, e in zip(parsed, r['implementation']['events']):
        string,fret,note,role,bar = expected; midi = tuning[string]+fret
        check((e['string_name'],e['fret'],e['printed_note'],e['printed_role'],e['source_absolute_bar']) == expected, 'original contact/role/bar exact')
        check(e['string_number'] == numbers[string] and e['written_pitch_theory']['midi_at_stated_standard_tuning'] == midi and midi%12 == pcs[note], 'independent string/fret/note MIDI parity')
        check(e['onset_q'] is None and e['duration_q'] is None and e['finger'] is None, 'no timing/fingering invented')
        contacts += 1
    for b in c['source_script']['bars']:
        selected = [e for e in r['implementation']['events'] if e['source_absolute_bar'] == b['source_bar']]
        check(len(selected) == 4 and b['source_orders'] == [e['source_order'] for e in selected], 'four source tones per exact bar')
        check(all(e['harmonic_context']['chord_symbol'] == b['printed_chord'] for e in selected), 'chord function preserved')
    s = m.StudySession(c); suspend_restore(s)
    refused(lambda: s.begin(s.token()), s)
    for instrument in (False, None, 1): refused(lambda x=instrument:s.configure(s.token(),x,'choice'),s)
    for choice in ('', ' ', None, 7): refused(lambda x=choice:s.configure(s.token(),True,x),s)
    t=s.token();s.configure(t,True,'first chosen timing');refused(lambda:s.configure(t,True,'stale'),s)
    s.configure(s.token(),True,'revised chosen timing');check(len(s.history)==1,'prior timing choice retained')
    suspend_restore(s);t=s.token();other=m.StudySession(c)
    for bad in (other.token(),replace(t,route='other'),replace(t,pass_number=9),replace(t,action=99)):
        refused(lambda x=bad:s.begin(x),s)
    s.begin(t);refused(lambda:s.begin(t),s);suspend_restore(s)
    refused(lambda:s.respond(s.token(),positive()),s)
    refused(lambda:s.release(s.token(),False),s)
    rel=s.token();s.release(rel,True);refused(lambda:s.release(rel,True),s);suspend_restore(s)
    check(not s.snapshot()['manual_reports_complete'],'release does not claim performance')
    for changes in ({'destination_bars':[6,6,8]}, {'destination_bars':[0,7,8]}, {'destination_bars':[6,7,9]},
                    {'destination_bars':[True,7,8]}, {'destination_bars':'6,7,8'}, {'destination_bars':[6,'7',8]},
                    {'exact_bar':True}, {'exact_bar':0}, {'exact_bar':9}, {'exact_bar':None},
                    {'audit_response':'unknown'}, {'audit_response':'uncertain'}, {'reflection':None},
                    {'printed_order':True}, {'extra':'not allowed'}):
        rbad=positive();rbad.update(changes);refused(lambda q=rbad:s.respond(s.token(),q),s)
    missing=positive();del missing['modulation_route_addressed'];refused(lambda:s.respond(s.token(),missing),s)
    answer=positive();token=s.token();s.respond(token,answer);answer['destination_bars'].clear()
    check(s.report['destination_bars']==[6,7,8],'caller cannot mutate captured report')
    refused(lambda:s.respond(token,positive()),s)
    check(s.snapshot()['manual_reports_complete'],'complete reports captured');suspend_restore(s)
    for flag in ('performance_observed','app_audio_supplied','automatic_evaluation','Attempt_credit','mastery_awarded','persistence_supplied'):
        check(s.snapshot()[flag] is False, 'no '+flag)
    refused(lambda:s.request_retry(s.token(),''),s)
    saved=deepcopy(s.report);choice=deepcopy(s.choice);stale=s.token();s.request_retry(stale,'repeat the study');suspend_restore(s)
    refused(lambda:s.retry_release(s.token(),False),s);s.retry_release(s.token(),True)
    check(s.pass_number==2 and s.choice==choice and s.report is None,'retry retains choice/new pass')
    check(any(x.get('response')==saved for x in s.history),'prior report retained')
    refused(lambda:s.request_retry(stale,'old pass'),s)
    # Every printed obligation can be reported negative/uncertain without false completion.
    for field in ('printed_order','four_tones_each_bar','modulation_route_addressed','destination_confirmed'):
        for value in ('no','uncertain'):
            ss=reported_session(c);q=positive();q[field]=value;ss.respond(ss.token(),q)
            check(ss.stage=='retry_required' and ss.report[field]==value,'unsatisfied printed obligation retained')
            suspend_restore(ss)
    for bars in ([],[8],[7,8]):
        ss=reported_session(c);q=positive();q['destination_bars']=bars;ss.respond(ss.token(),q)
        check(ss.stage=='retry_required' and ss.report['destination_bars']==bars,'under-three coverage retained incomplete')
    for unresolved in ('uncertain','not_heard'):
        ss=reported_session(c);q=positive();q.update(audit_response=unresolved,exact_bar=None);ss.respond(ss.token(),q)
        check(ss.stage=='retry_required' and ss.report['exact_bar'] is None,'unresolved audit retained')
    # A subjective audit has no invented fixed correct bar/tonic-only answer.
    for exact in (1,8):
        ss=reported_session(c);q=positive();q.update(exact_bar=exact,destination_bars=[2,5,8]);ss.respond(ss.token(),q)
        check(ss.stage=='complete_manual_reports','manual report does not fabricate harmonic grading')
    check(c['source_script']==m.StudySession(c).snapshot()['source_script'],'original script stable')

check(contacts==128 and len(rows)==4,'finite exact batch')
for ref in (source['original_pdf'],source['original_txt']):
    b=(R/ref['path']).read_bytes();check(len(b)==ref['bytes'] and hashlib.sha256(b).hexdigest()==ref['sha256'],'source pin unchanged')
out={'status':'PASS','checks':checks,'source_contacts_independently_parsed':contacts,'complete_manual_cases':4,
     'physical_pages_text_checked':[13,14,15,16],'synthetic_manual_responses_only':True,
     'new_source_events':0,'native_runs':0,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
     'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
