from pathlib import Path
from dataclasses import replace
import copy, datetime, hashlib, json, re, resource, sys, time
ROOT = Path(__file__).resolve().parents[3]
LANE = Path('fullscope-private-c-r01/level073-r23')
sys.path.insert(0, str(ROOT/'Tools'/LANE))
from pivot_route_contract import PivotRouteSession
checks = 0
start = time.monotonic()

def ck(v, label):
    global checks
    checks += 1
    if not v:
        raise AssertionError(label)

def refused(fn):
    try:
        fn()
    except ValueError:
        return True
    return False

def unchanged_refusal(s, fn, label):
    before, token = s.snapshot(), s.token()
    ck(refused(fn), label)
    ck(s.snapshot() == before and s.token() == token, label+' leaves state intact')

def setup(s):
    s.setup(s.token(), True, 'Synthetic learner pulse', 'Synthetic placement while retaining four bars',
            'Synthetic learner restatement of '+s.c['pivot_dual_function'])

def finish_bars(s, failed_bar=None, pivot='yes'):
    for n in range(1,5):
        bar = s.current_bar()
        ck(bar == s.c['bars'][n-1], 'actual current bar retains full source contacts')
        bar['printed_contacts'][0]['fret'] = -1
        ck(s.current_bar()['printed_contacts'][0]['fret'] >= 0, 'detached presentation cannot edit source')
        token = s.token()
        s.report_bar(token, n, 'no' if n == failed_bar else 'yes', 'Synthetic own-instrument report',
                     **({'pivot_extra_beat': pivot, 'hold_placement': 'Synthetic learner placement'}
                        if s.pass_number == 1 and n == 2 else {}))
        unchanged_refusal(s, lambda: s.report_bar(token, n, 'yes', 'duplicate'), 'same displayed action cannot acknowledge next bar')
    ck(s.current_bar() is None and s.stage == 'summary', 'four bars stop for pass report')

def summary(s, four='yes', tonic='yes', emphasis='yes'):
    s.report_pass(s.token(), four, tonic, 'Synthetic tonal-center self-report',
                  **({'extra_emphasis_removed': emphasis, 'harmony_only_comparison': 'Synthetic comparison between held pivot and harmony alone'}
                     if s.pass_number == 2 else {}))

packet = ROOT/'Build'/LANE/'pivot-route-overlays.jsonl'
rows = list(map(json.loads, packet.read_text().splitlines()))
base = list(map(json.loads, (ROOT/'Build/fullscope-private-c-r01/level073-r07/implementation-packet.jsonl').read_text().splitlines()))[5:11]
ck([r['package_key'] for r in rows] == [r['package_key'] for r in base], 'six exact original keys in source order')
ck(len(rows) == len({r['package_key'] for r in rows}) == 6, 'six unique keys')
source = next((ROOT/'Notes/music/guitar project/TXT version').glob('*Level_73_*'))
lines = source.read_text().splitlines()
opens = {'e':64, 'B':59, 'G':55, 'D':50, 'A':45, 'E':40}
for r, b in zip(rows, base):
    c = r['implementation']['task']['contract']
    events = r['implementation']['events']
    ck(events == b['implementation']['events'], 'original event objects retained exactly')
    ck(r['source_refs'] == b['source_refs'] and r['source_payload'] == b['source_payload'], 'original source custody intact')
    ck(all(e['onset_q'] is None and e['duration_q'] is None and e['finger'] is None for e in events), 'no invented timing/fingering')
    ck(c['source_instruction'].endswith('relies on harmony alone.'), 'wrapped final obligation complete')
    ck(c['fixed_timing_projection']['status'] == 'UNRESOLVED' and c['source_obligations']['route_bar_count'] == 4, 'manual completeness separate from metric projection')
    join = r['provenance']['exact_conversion_joins'][0]
    lo, hi = join['txt_event_lines']
    literal = lines[lo-1:hi]
    ck(len(literal) == 8 and literal[0].startswith('Nte|') and literal[1].startswith('Rol|'), 'exact TXT event block')
    nte = literal[0].split('|')[1:-1]
    rol = literal[1].split('|')[1:-1]
    extracted = []
    for bar in range(4):
        for string_line in literal[2:]:
            name = string_line.split('|')[0].strip()
            cell = string_line.split('|')[bar+1]
            for match in re.finditer(r'\d+', cell):
                col = match.start()
                note = re.match(r'[A-G][#b]?', nte[bar][col:]).group()
                role = re.match(r'[^-]+', rol[bar][col:]).group()
                extracted.append((bar+1, col, name, int(match.group()), note, role))
    extracted.sort(key=lambda x:(x[0],x[1]))
    ck(len(extracted) == 16, 'independent exact TXT parser finds sixteen contacts')
    for e, exp in zip(events, extracted):
        ck((e['printed_bar'],e['printed_column'],e['string_name'],e['fret'],e['printed_note'],e['printed_role']) == exp, 'contact/string/fret/note/role/position matches original text')
        ck(e['written_pitch_theory']['midi_at_stated_standard_tuning'] == opens[exp[2]]+exp[3], 'literal pitch calculation parity')
    ck([e for bar in c['bars'] for e in bar['printed_contacts']] == events, 'both passes reference all sixteen original contacts')
    ck([bar['chord_symbol'] for bar in c['bars']] == join['facts']['chords'], 'exact harmonic route')
    ck(c['pivot_dual_function'] == lines[lo-3] and c['progression'] == lines[lo-2], 'exact printed dual function and progression')
    for ref in [*r['source_refs'],c['state_engine_ref'],c['source_instruction_ref']['verification']]:
        ck(hashlib.sha256((ROOT/ref['path']).read_bytes()).hexdigest() == ref['sha256'], 'live source/engine/verification pin')
    s = PivotRouteSession(c)
    ck(s.current_bar() is None, 'no premature source action before setup')
    unchanged_refusal(s, lambda: s.begin_pass(s.token()), 'setup prerequisite')
    unchanged_refusal(s, lambda: s.setup(s.token(), False, 'pulse', 'hold', 'pivot'), 'own instrument is disclosed prerequisite')
    unchanged_refusal(s, lambda: s.setup(s.token(), True, '', 'hold', 'pivot'), 'empty chosen pulse refused')
    foreign = PivotRouteSession(c)
    unchanged_refusal(s, lambda: s.setup(foreign.token(), True, 'pulse', 'hold', 'pivot'), 'foreign instance token refused')
    unchanged_refusal(s, lambda: s.setup(replace(s.token(),route='wrong'),True,'p','h','f'), 'wrong route token refused')
    initial = s.token()
    setup(s)
    unchanged_refusal(s, lambda: s.setup(initial,True,'p','h','f'), 'stale setup refused')
    ready = s.token()
    s.begin_pass(ready)
    unchanged_refusal(s, lambda: s.begin_pass(ready), 'duplicate start refused')
    unchanged_refusal(s, lambda: s.report_bar(s.token(),2,'yes','skip'), 'bar order not skippable')
    unchanged_refusal(s, lambda: s.report_bar(s.token(),True,'yes','bool'), 'bool bar index refused')
    unchanged_refusal(s, lambda: s.report_bar(s.token(),1,True,'bool'), 'bool report refused')
    unchanged_refusal(s, lambda: s.report_bar(s.token(),1,'yes','foreign',pivot_extra_beat='yes',hold_placement='h'), 'hold belongs to pivot only')
    unchanged_refusal(s, lambda: s.report_pass(s.token(),'yes','yes','early'), 'summary cannot precede bars')
    finish_bars(s)
    unchanged_refusal(s, lambda: s.report_pass(s.token(),'yes','yes','bad',extra_emphasis_removed='yes',harmony_only_comparison='bad'), 'first pass cannot pretend second comparison')
    summary(s)
    unchanged_refusal(s, lambda: s.begin_pass(s.token()), 'explicit release before next pass')
    unchanged_refusal(s, lambda: s.release(s.token(),False), 'negative release not accepted')
    release_token = s.token()
    s.release(release_token,True)
    ck(s.pass_number == 2 and s.stage == 'ready' and len(s.history[0]['bars']) == 4, 'first report retained before second pass')
    unchanged_refusal(s, lambda: s.release(release_token,True), 'stale release cannot advance second pass')
    s.begin_pass(s.token())
    unchanged_refusal(s, lambda: s.report_bar(replace(s.token(),pass_number=1),1,'yes','oldpass'), 'old pass refused even current action stage')
    finish_bars(s)
    unchanged_refusal(s, lambda: s.report_pass(s.token(),'yes','yes','missing'), 'second comparison and emphasis report required')
    summary(s)
    ck(not s.snapshot()['manual_task_reports_complete'], 'report completion awaits explicit final release')
    s.release(s.token(),True)
    ck(s.snapshot()['manual_task_reports_complete'] and len([h for h in s.history if h['kind']=='released_pass']) == 2, 'six full two-pass report campaigns')
    ck(not any(s.snapshot()[f] for f in ['performance_observed','app_audio_supplied','Attempt_credit','mastery_awarded','persistence_supplied']), 'reports never imply acoustic/canonical progress')
    old = s.token()
    retained = copy.deepcopy((s.bars,s.summary,s.context))
    s.cancel(old)
    ck(not s.snapshot()['manual_task_reports_complete'], 'cancelled completion not active')
    unchanged_refusal(s, lambda: s.request_retry(old,'stale'), 'cancel fences queued actions')
    cancelled = s.token()
    unchanged_refusal(s, lambda: s.reopen(cancelled,False), 'manual release before reopen')
    s.reopen(cancelled,True)
    ck((s.bars,s.summary,s.context) == retained and s.snapshot()['manual_task_reports_complete'], 'reopen retains original report state')
    unchanged_refusal(s, lambda: s.request_retry(old,'stale'), 'reopen invalidates old action')
    s.request_retry(s.token(),'Synthetic deliberate repeat')
    ck(s.stage == 'retry_release', 'repeat requires own release')
    unchanged_refusal(s, lambda: s.retry_after_release(s.token(),False), 'retry release refusal')
    s.retry_after_release(s.token(),True)
    ck(s.stage == 'ready' and s.pass_number == 2 and s.bars == [] and s.summary is None and len(s.history)>=5, 'repeat resets current pass only and preserves history')

# Negative and uncertain obligations each retain the failed report and require explicit retry.
c = rows[0]['implementation']['task']['contract']
for failure in ('bar','pivot','bar_count','tonic','second_emphasis'):
    s = PivotRouteSession(c); setup(s); s.begin_pass(s.token())
    finish_bars(s, failed_bar=3 if failure=='bar' else None, pivot='uncertain' if failure=='pivot' else 'yes')
    summary(s,four='no' if failure=='bar_count' else 'yes',tonic='uncertain' if failure=='tonic' else 'yes')
    s.release(s.token(),True)
    if failure == 'second_emphasis':
        s.begin_pass(s.token()); finish_bars(s); summary(s,emphasis='no'); s.release(s.token(),True)
    ck(s.stage == 'retry_required' and not s.snapshot()['manual_task_reports_complete'], failure+' not treated as completion')
    failed = copy.deepcopy(s.history[-1])
    unchanged_refusal(s, lambda: s.begin_pass(s.token()), failure+' cannot auto-progress')
    old = s.token(); s.request_retry(old,'Synthetic corrective retry')
    s.retry_after_release(s.token(),True)
    ck(failed in s.history and s.stage == 'ready' and s.bars == [], failure+' retained across retry')
    unchanged_refusal(s, lambda: s.request_retry(old,'stale'), failure+' old action invalidated')
# Cancel mid-route preserves position and blocks old callbacks after reopening.
s = PivotRouteSession(c); setup(s); s.begin_pass(s.token())
s.report_bar(s.token(),1,'yes','Synthetic bar1')
old = s.token(); before = copy.deepcopy(s.bars); s.cancel(old)
ck(s.current_bar() is None, 'cancel hides executable current action')
s.reopen(s.token(),True)
ck(s.current_bar()['bar_number'] == 2 and s.bars == before, 'mid-route reopen preserves reports and current source position')
unchanged_refusal(s, lambda: s.report_bar(old,2,'yes','queued',pivot_extra_beat='yes',hold_placement='h'), 'queued pre-cancel response refused')
unchanged_refusal(s, lambda: s.report_bar(s.token(),2,'yes','missing'), 'first pivot requires hold and placement reports')
result = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'result':'PASS','checks':checks,
          'elapsed_seconds':time.monotonic()-start,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          'packet_sha256':hashlib.sha256(packet.read_bytes()).hexdigest(), 'six_complete_two_pass_campaigns':True,
          'all_performance_reports_synthetic':True,'native_app_gui':'NOT_RUN', 'original_source_contacts':96}
out = ROOT/'Results'/LANE/'integrity.json'
assert not out.exists()
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
