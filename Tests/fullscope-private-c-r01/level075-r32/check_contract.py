from pathlib import Path
from copy import deepcopy
from dataclasses import replace
import datetime, hashlib, importlib.util, json, resource, sys

R = Path(__file__).resolve().parents[3]
L = Path('fullscope-private-c-r01/level075-r32')
spec = importlib.util.spec_from_file_location('reduction_contract', R/'Tools'/L/'reduction_contract.py')
m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)
checks = 0; refusals = 0
def check(value, label):
    global checks
    checks += 1
    if not value:
        raise AssertionError(label)
def snapshot(flow):
    return deepcopy(flow.__dict__)
def refuses(flow, call, label):
    global refusals
    before = snapshot(flow)
    try:
        call()
    except m.Refusal:
        refusals += 1
    else:
        raise AssertionError('accepted '+label)
    check(snapshot(flow) == before, 'refusal mutated '+label)
def plan(chords):
    return {'prerequisites': {'own_instrument': True, 'original_workbook': True},
            'chords': [{'source_position': i, 'source_chord': s,
                        'root': 'Synthetic learner root choice',
                        'guide_tones': ['Synthetic learner guide choice'],
                        'voicing': ['Synthetic learner full voicing choice'],
                        'bass': 'Synthetic learner lowest structural note'} for i, s in enumerate(chords, 1)],
            'measure_pulse_plan': 'Learner-selected measure scope and pulse; not a printed timing claim.',
            'role_pattern': {'mode': 'reference_only', 'rationale': 'Keep abstract roles visible without asserting a fixed alignment.', 'mapping': []},
            'analysis': {name: {'mode': 'none', 'values': [], 'notes': 'Synthetic learner response; not a correct-answer claim.'}
                         for name in ('dominants', 'repeated_sections', 'high_risk_transitions')}}
def good_report(flow):
    return {'chords': [{'source_position': i, 'covered': 'yes'} for i in range(1, 5)],
            'full_scope': 'yes', 'criterion': m.CRITERIA[flow.phase], 'criterion_report': 'yes',
            'form_clear': 'yes' if flow.phase == 2 else None, 'notes': 'Synthetic manual report only.'}
def ready(key):
    f = m.ReductionFlow(key); f.set_plan(f.token(), plan(f.chords)); return f
def performing(f):
    f.begin(f.token()); return f
def reporting(f):
    performing(f); f.release(f.token(), True); return f
def pass_phase(f):
    reporting(f); f.report(f.token(), good_report(f)); f.advance(f.token())
def pin(p):
    b = (R/p).read_bytes(); return {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

base_path = Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
base = [json.loads(x) for x in (R/base_path).read_text().splitlines()][1:9]
packet_path = Path('Build')/L/'harmonic-reduction-overlay.jsonl'
rows = [json.loads(x) for x in (R/packet_path).read_text().splitlines()]
check(len(rows) == 8, 'exact card count')
for i, (old, row) in enumerate(zip(base, rows)):
    c = row['implementation']['task']['contract']
    for field in ('package_key', 'source_identity', 'level', 'existing_parent_id', 'source_refs', 'source_payload', 'timing_authority'):
        check(row[field] == old[field], 'unchanged original '+field)
    check(row['implementation']['events'] == old['implementation']['events'] == [], 'empty events exact')
    check(row['implementation']['tab_blocks'] == old['implementation']['tab_blocks'], 'tab unchanged')
    check(c['key'] == m.KEYS[i] and c['source_chords'] == list(m.CARDS[i][2]), 'finite exact card')
    check([x['literal'] for x in c['source_role_occurrences']] == list(m.ROLES), 'abstract roles exact')
    check(all(x['kind'] == 'harmonic_degree' and x['root_not_rest'] == (x['literal'] == 'R') for x in c['source_role_occurrences']), 'R root never rest')
    check(c['extent']['literal_header'] == '12 CELLS | 96 CONTACTS' and c['extent']['visible_card_count'] == 8, 'extent facts')
    check(not c['extent']['larger_page_extent_complete'] and not c['fixed_playback_realization_complete'], 'pending fixed extent and realization')
    check(c['source_instructions'] == [m.INSTRUCTION, m.FOOTER], 'full source instructions')
    check(c['module_txt_analysis_instruction'] == m.ANALYSIS, 'TXT analysis full')
    check('MASTER 60-BAR FICTIONAL REPERTOIRE STUDY' in c['master_chart_context']['text'], 'master context visible')
    for flag in ('automatic_evaluation', 'performance_observed', 'credit_awarded', 'mastery_awarded', 'audio_supplied', 'persistence'):
        check(c[flag] is False, flag)
    check(c['canonical_binding'] is None and c['source_scope']['fixed_contact_count'] is None, 'no ID or contacts')

    # Every finite card runs all four actual manual source duties in order.
    f = ready(m.KEYS[i]); chosen = deepcopy(f.plan)
    for phase in range(4):
        check(f.phase == phase and f.stage == 'ready', 'ordered phase')
        refuses(f, lambda: f.advance(f.token()), 'advance before report')
        saved = f.token(); f.begin(saved)
        refuses(f, lambda: f.begin(saved), 'duplicate begin')
        refuses(f, lambda: f.report(f.token(), good_report(f)), 'report before release')
        refuses(f, lambda: f.release(f.token(), False), 'release not acknowledged')
        refuses(f, lambda: f.release(f.token(), 1), 'truthy release not bool')
        refuses(f, lambda: f.set_plan(f.token(), chosen), 'plan while instrument active')
        release_token = f.token(); f.release(release_token, True)
        refuses(f, lambda: f.release(release_token, True), 'duplicate release')
        reply_token = f.token(); reply = good_report(f); f.report(reply_token, reply)
        reply['notes'] = 'outside mutation'
        check(f.history[-1]['data']['response']['notes'] == 'Synthetic manual report only.', 'response custody')
        refuses(f, lambda: f.report(reply_token, good_report(f)), 'duplicate report')
        check(f.stage == 'pass_reported' and not f.history[-1]['data']['performance_verified'], 'manual report only')
        advance_token = f.token(); f.advance(advance_token)
        refuses(f, lambda: f.advance(advance_token), 'duplicate advancement')
    check(f.stage == 'completed' and f.plan == chosen, 'all source duties recorded')
    old_history = deepcopy(f.history); token = f.token(); changed = deepcopy(chosen)
    changed['chords'][0]['root'] = 'New learner root choice'
    f.set_plan(token, changed)
    check(f.phase == 0 and f.stage == 'ready' and f.history[:-1] == old_history, 'plan revision resets progress retains history')
    changed['chords'][0]['root'] = 'external mutation'
    check(f.plan['chords'][0]['root'] == 'New learner root choice', 'plan custody')
    refuses(f, lambda: f.advance(token), 'old completion token after new plan')

    # Negative/uncertain coverage, scope and criterion cannot bypass any pass.
    for phase in range(4):
        for field in ['full_scope', 'criterion_report'] + [f'chord{n}' for n in range(4)] + (['form_clear'] if phase == 2 else []):
            for value in ('no', 'uncertain'):
                g = ready(m.KEYS[i])
                for _ in range(phase): pass_phase(g)
                reporting(g); response = good_report(g)
                if field.startswith('chord'): response['chords'][int(field[-1])]['covered'] = value
                else: response[field] = value
                g.report(g.token(), response)
                check(g.stage == 'needs_retry' and g.phase == phase, 'unsatisfied pass retained')
                check(g.history[-1]['data']['response'] == response, 'negative reply retained')
                refuses(g, lambda: g.advance(g.token()), 'unclear incomplete source duty')
                refuses(g, lambda: g.begin(g.token()), 'explicit retry required')
                g.retry(g.token(), 'Manually isolate and retry this source duty.')
                check(g.phase == phase and g.stage == 'ready', 'retry current pass only')
                pass_phase(g)
                check(g.phase == min(phase+1, 3), 'retry can complete')

# Atomic shape/source/prerequisite refusals; no answer is judged for pitch correctness.
f = m.ReductionFlow(m.KEYS[0]); valid = plan(f.chords)
mutations = []
def mutated(label, fn):
    q = deepcopy(valid); fn(q); mutations.append((label, q))
mutated('prerequisite false', lambda q: q['prerequisites'].__setitem__('own_instrument', False))
mutated('prerequisite truthy', lambda q: q['prerequisites'].__setitem__('original_workbook', 1))
mutated('empty measure plan', lambda q: q.__setitem__('measure_pulse_plan', ' '))
mutated('missing chord', lambda q: q['chords'].pop())
mutated('extra chord', lambda q: q['chords'].append(q['chords'][0]))
mutated('reordered chord', lambda q: q['chords'].reverse())
mutated('altered source chord', lambda q: q['chords'][0].__setitem__('source_chord', 'C7'))
mutated('boolean source position', lambda q: q['chords'][0].__setitem__('source_position', True))
for name in ('root', 'bass'):
    mutated('empty '+name, lambda q, name=name: q['chords'][0].__setitem__(name, ''))
for name in ('guide_tones', 'voicing'):
    for value in ([], '', ['']):
        mutated('invalid '+name, lambda q, name=name, value=value: q['chords'][0].__setitem__(name, value))
mutated('reference with projection', lambda q: q['role_pattern'].__setitem__('mapping', [1]))
mutated('missing rationale', lambda q: q['role_pattern'].__setitem__('rationale', ''))
mutated('extra fields', lambda q: q.__setitem__('fixed_bpm', 120))
for name in ('dominants', 'repeated_sections', 'high_risk_transitions'):
    mutated('none with values '+name, lambda q, name=name: q['analysis'][name].__setitem__('values', ['x']))
    mutated('empty list '+name, lambda q, name=name: q['analysis'][name].__setitem__('mode', 'list'))
    mutated('no notes '+name, lambda q, name=name: q['analysis'][name].__setitem__('notes', ''))
for value in ([0], [5], [True], [1, 1], ['1']):
    mutated('bad dominant location', lambda q, value=value: q['analysis'].__setitem__('dominants', {'mode': 'list', 'values': value, 'notes': 'synthetic'}))
for label, q in mutations:
    refuses(f, lambda q=q: f.set_plan(f.token(), q), label)

projection = deepcopy(valid)
projection['role_pattern'] = {'mode': 'learner_realization', 'rationale': 'Explicit learner projection, not source alignment.',
                              'mapping': [{'source_role_position': i, 'source_role': r,
                                           'chosen_chord_position': (i-1) % 4+1,
                                           'realization': 'Learner-chosen role realization'} for i, r in enumerate(m.ROLES, 1)]}
for slot in range(8):
    for field, value in [('source_role_position', 9), ('source_role', 'rest'), ('chosen_chord_position', 0), ('realization', '')]:
        q = deepcopy(projection); q['role_pattern']['mapping'][slot][field] = value
        refuses(f, lambda q=q: f.set_plan(f.token(), q), 'source role mapping boundary')
f.set_plan(f.token(), projection)
check(f.plan['role_pattern'] == projection['role_pattern'], 'explicit learner role plan retained')
for name in ('dominants', 'repeated_sections', 'high_risk_transitions'):
    g = m.ReductionFlow(m.KEYS[0]); q = deepcopy(valid)
    q['analysis'][name]['mode'] = 'uncertain'; g.set_plan(g.token(), q)
    check(g.stage == 'needs_plan_revision', 'uncertain source analysis held')
    refuses(g, lambda: g.begin(g.token()), 'unresolved analysis')
    q['analysis'][name] = {'mode': 'list', 'values': [4] if name == 'dominants' else ['Learner-marked chart reference'], 'notes': 'Learner revised choice, correctness unverified.'}
    g.set_plan(g.token(), q)
    check(g.stage == 'ready' and len(g.history) == 2, 'analysis revision retains original uncertainty')

# Current owner/generation/action/stage fencing independent of musical answers.
f = ready(m.KEYS[0]); t = f.token()
for kwargs in ({'instance': 'foreign'}, {'key': m.KEYS[1]}, {'generation': 99}, {'phase': 1},
               {'cycle': 99}, {'action': 99}, {'stage': 'performing'}):
    forged = replace(t, **kwargs)
    refuses(f, lambda forged=forged: f.begin(forged), 'forged callback '+str(kwargs))
other = ready(m.KEYS[0]); refuses(f, lambda: f.begin(other.token()), 'another instance same card')
for stage in ('setup', 'ready', 'performing', 'awaiting_report', 'needs_retry', 'pass_reported', 'needs_plan_revision', 'completed'):
    g = m.ReductionFlow(m.KEYS[0])
    if stage != 'setup': g.set_plan(g.token(), valid)
    if stage in ('performing', 'awaiting_report', 'needs_retry', 'pass_reported'): g.begin(g.token())
    if stage in ('awaiting_report', 'needs_retry', 'pass_reported'): g.release(g.token(), True)
    if stage in ('needs_retry', 'pass_reported'):
        q = good_report(g)
        if stage == 'needs_retry': q['full_scope'] = 'no'
        g.report(g.token(), q)
    if stage == 'needs_plan_revision':
        q = deepcopy(valid); q['analysis']['dominants']['mode'] = 'uncertain'; g.set_plan(g.token(), q)
    if stage == 'completed':
        for _ in range(4): pass_phase(g)
    check(g.stage == stage, 'cancel setup')
    oldplan = deepcopy(g.plan); oldhistory = deepcopy(g.history); oldtoken = g.token()
    g.cancel(oldtoken); refuses(g, lambda: g.cancel(oldtoken), 'duplicate cancel')
    g.reopen(g.token()); check(g.stage == 'release_after_reopen', 'reopen release fence')
    refuses(g, lambda: g.begin(oldtoken), 'old action after reopen')
    refuses(g, lambda: g.begin(g.token()), 'begin before reopen release')
    g.cancel(g.token()); g.reopen(g.token()); g.release(g.token(), True)
    check(g.stage == ('ready' if stage in ('performing', 'awaiting_report') else stage), 'reopen preserves stage or restarts incomplete pass')
    check(g.plan == oldplan and g.history[:len(oldhistory)] == oldhistory, 'cancel plan/history retention')

# Report shape errors do not consume the held report or change history.
for phase in range(4):
    f = ready(m.KEYS[0])
    for _ in range(phase): pass_phase(f)
    reporting(f); good = good_report(f)
    bads = []
    for field, value in [('criterion', 'wrong_pass'), ('full_scope', True), ('criterion_report', 'probably'),
                          ('notes', ''), ('form_clear', None if phase == 2 else 'yes')]:
        q = deepcopy(good); q[field] = value; bads.append(q)
    q = deepcopy(good); q['chords'].pop(); bads.append(q)
    q = deepcopy(good); q['chords'][0]['source_position'] = True; bads.append(q)
    q = deepcopy(good); q['chords'][0]['covered'] = 1; bads.append(q)
    for q in bads: refuses(f, lambda q=q: f.report(f.token(), q), 'malformed current report')
    f.report(f.token(), good); check(f.stage == 'pass_reported', 'same held report still usable')

try:
    m.ReductionFlow('exercise-completeness-r01/level075/modulea/p003-card09/invented')
except m.Refusal:
    check(True, 'unsupported ninth card refused')
else:
    raise AssertionError('invented key accepted')
out = R/'Results'/L/'integrity.json'; assert not out.exists()
result = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'result': 'PASS',
          'checks': checks, 'causal_refusals': refusals, 'exact_cards': 8,
          'packet': pin(packet_path), 'base': pin(base_path),
          'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          'synthetic_manual_responses_only': True, 'actual_performance_observed': False,
          'source_extent_disposition': 'Pending', 'native_runs': 0, 'app_runs': 0}
out.write_text(json.dumps(result, indent=2)+'\n'); print(json.dumps(result))
