"""All-key pin/source/contact arithmetic and two small causal examples; broad QA deferred."""
from copy import deepcopy
import datetime
import itertools
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
LANE = Path('fullscope-private-c-r01/coherent-level083-fixed-top-r65')
sys.path.insert(0, str(ROOT / 'Tools' / LANE))
import fixed_top_model as m
from produce import pin, verify

checks = refusals = 0
labels = []


def check(ok, label):
    global checks
    assert ok, label
    checks += 1


def refuse(call, label, flow=None):
    global refusals
    before = deepcopy(flow.__dict__) if flow else None
    try:
        call()
    except (ValueError, AssertionError):
        if flow:
            check(flow.__dict__ == before, label + ': no mutation')
        refusals += 1
        labels.append(label)
    else:
        raise AssertionError('Expected refusal: ' + label)


def top_choice(flow, midi=None):
    midi = midi if midi is not None else 72 + m.PC[flow.card['literal_top']]
    contact = next({'string': s, 'fret': midi - base, 'midi': midi} for s, base in reversed(list(m.TUNING.items())) if 0 <= midi - base <= 24)
    return {'key': flow.key, 'literal_top': flow.card['literal_top'], 'contact': contact,
            'original_workbook': True, 'own_instrument': True}


def voicing(flow):
    c = flow.current(); pcs, _ = m.chord(c['harmony']); top = deepcopy(flow.top)
    desired = [m.PC[c['literal_top']]] if c['stage'] == 'melody' else (
        [pcs[0], m.PC[c['literal_top']]] if c['stage'] in ('root_melody', 'bass_melody_reduction') else
        [pcs[1], pcs[3], m.PC[c['literal_top']]] if c['stage'] == 'shell_melody' else list(pcs))
    desired.remove(top['midi'] % 12)
    options = [[{'string': s, 'fret': fret, 'midi': base + fret}
                for s, base in m.TUNING.items() if s != top['string']
                for fret in range(25) if base + fret < top['midi'] and (base + fret) % 12 == pc] for pc in desired]
    for chosen in itertools.product(*options):
        contacts = list(chosen) + [top]
        if len({x['string'] for x in contacts}) != len(contacts):
            continue
        plan = dict({n: c[n] for n in ('key', 'harmony', 'stage')}, contacts=contacts, rationale='Synthetic explicitly chosen voicing; no physical playability/listening observation.')
        try:
            flow.validate_voicing(plan)
        except m.Refusal:
            continue
        return plan
    raise AssertionError('No finite chosen source-consistent fixture voicing')


def report(flow, melody='yes', role=None):
    return dict({n: flow.current()[n] for n in ('key', 'harmony', 'stage')}, contacts=deepcopy(flow.plan['contacts']),
        attack_counts=[1] * len(flow.plan['contacts']), duties={n: melody if n == 'melody_clear' else 'yes' for n in flow.duties()},
        diagnosis='' if melody == 'yes' else 'Synthetic lost melody declaration; reduce to bass+melody.',
        notes='Synthetic manual source duty report, no actual hearing/playing observation.')


def step(flow):
    flow.sing_top(flow.token(), {'sung_before_voicing': 'yes', 'notes': 'Synthetic manual singing declaration.'})
    flow.choose_voicing(flow.token(), voicing(flow))
    flow.name_role(flow.token(), {'role': flow.expected_role(), 'notes': 'Symbolic manual role fixture.'})
    flow.play(flow.token(), True)
    flow.release(flow.token(), {'learner_released': True})
    flow.report(flow.token(), report(flow))
    flow.advance(flow.token())


def audit(flow, unknown=False):
    names = m.C_AUDIT if flow.card['module'] == 'C' else m.AB_AUDIT
    answers = {n: 'Manual musical judgment; no automatic audible assessment.' for n in names}
    if unknown:
        answers[names[0]] = None
    return {'answers': answers, 'notes': 'Synthetic source-choice audit.',
            'diagnosis': 'Retained unknown musical judgment requires another explicit audit.' if unknown else ''}


def complete(flow, check_unknown_audit=False):
    flow.set_top(flow.token(), top_choice(flow))
    stages = 0
    while flow.state != 'audit':
        if flow.state == 'need_additional':
            extra = next(h for h in flow.contract['source_sibling_candidates'] if h not in flow.card['source_harmonies'])
            flow.choose_additional(flow.token(), {'key': flow.key, 'harmony': extra,
                'rationale': 'Explicit synthetic additional source-vocabulary choice.'})
        step(flow); stages += 1
    if check_unknown_audit:
        flow.audit(flow.token(), audit(flow, True))
        refuse(lambda: flow.finish(flow.token()), 'unknown choice audit cannot finish', flow)
        before = deepcopy(flow.audit_history)
        flow.diagnose(flow.token(), 'Repeat the incomplete musical choice audit.')
        check(flow.state == 'audit' and flow.audit_history == before, 'unknown audit recovery remains reachable/history preserved')
    flow.audit(flow.token(), audit(flow))
    flow.finish(flow.token())
    return stages


def main():
    tick = time.monotonic()
    seal = json.loads((ROOT / 'Results' / LANE / 'seal.json').read_text())
    for n in ('model', 'packet', 'producer', 'reservation', 'source_cards', 'shared_contract', 'source_check', 'source_render_inspection'):
        verify(seal[n]); check(True, 'sealed ' + n)
    res = json.loads((ROOT / seal['reservation']['path']).read_text())
    scope = json.loads((ROOT / res['exact_key_source_row_scope']['path']).read_text())
    original = (ROOT / res['original_packet']['path']).read_text().splitlines()
    rows = [json.loads(x) for x in (ROOT / seal['packet']['path']).read_text().splitlines()]
    check(len(rows) == 41 and [r['package_key'] for r in rows] == res['exact_keys'], 'whole ordered41 exact-key packet')
    chosen_geometry = 0
    for row, selected, card in zip(rows, scope['rows'], m.cards()):
        old = json.loads(original[selected['current_payload']['jsonl_line'] - 1])
        for n in ('package_key', 'source_identity', 'existing_parent_id', 'source_refs', 'source_payload', 'timing_authority', 'field_limitations'):
            check(row[n] == old[n], 'all-key original source/identity ' + n)
        for n in ('events', 'tab_blocks', 'source_field_occurrences', 'canonical_ids_allocated', 'playback_admitted'):
            check(row['implementation'][n] == old['implementation'][n], 'all-key original implementation ' + n)
        check(row['implementation']['task']['table_fields'] == old['implementation']['task']['table_fields'], 'all-key raw table retained')
        check(row['status'] == 'IMPLEMENTED_PRIVATE_QA_PENDING' and row['contract_category'] == 'COMPLETE_MANUAL_NONPLAYBACK_CONTRACT'
              and not row['contract_capabilities']['Accepted'] and not row['contract_capabilities']['native_valid'], 'all-key private construction only')
        f = m.FixedTopFlow(row['package_key']); f.set_top(f.token(), top_choice(f))
        for h in card['source_harmonies']:
            pcs, roles = m.chord(h)
            check(m.PC[card['literal_top']] in pcs, 'all-key source fixed-top pitch arithmetic')
        # Pure chosen-contact arithmetic for every texture, no state/permutation execution campaign.
        for stage in range(4):
            f.stage_index = stage
            f.validate_voicing(voicing(f)); chosen_geometry += 1
            check(True, 'all-key finite chosen texture geometry')
    ab = m.FixedTopFlow(rows[0]['package_key'])
    refuse(lambda: ab.finish(ab.token()), 'early finish', ab)
    refuse(lambda: m.FixedTopFlow('new-or-transferred-key'), 'foreign unreserved key')
    ab_stages = complete(ab, True)
    check(ab_stages == 4 and ab.state == 'completed', 'one completeAB four-texture sample')
    check(ab.history[-1]['data']['mastery_awarded'] is False and ab.history[-1]['data']['official_acceptance'] is False, 'manual finish no mastery/acceptance')
    c = m.FixedTopFlow(rows[35]['package_key']); c_stages = complete(c)
    check(c_stages == 16 and c.harmonies[:3] == c.card['source_harmonies'] and len(c.harmonies) == 4, 'one completeC three source harmonies plus one chosen substitute')
    bad = m.FixedTopFlow(rows[0]['package_key']);bad.set_top(bad.token(), top_choice(bad));bad.sing_top(bad.token(), {'sung_before_voicing':'yes','notes':'Synthetic declaration.'})
    plan = voicing(bad); malformed = deepcopy(plan);malformed['contacts'][0]['fret'] = True
    refuse(lambda: bad.choose_voicing(bad.token(), malformed), 'boolean fret', bad)
    wrong = deepcopy(plan); wrong['contacts'][0] = {'string':'e','fret':9,'midi':73}
    refuse(lambda: bad.choose_voicing(bad.token(), wrong), 'changed literal sounding top', bad)
    bad.choose_voicing(bad.token(), plan);bad.name_role(bad.token(), {'role':None,'notes':'Explicit unknown role retained.'})
    oldtoken=bad.token();bad.play(bad.token(),True)
    refuse(lambda:bad.release(oldtoken,{'learner_released':True}), 'stale action token', bad)
    refuse(lambda:bad.release(bad.token(),{'learner_released':False}), 'physical release refusal', bad)
    bad.release(bad.token(),{'learner_released':True});r=report(bad);r['diagnosis']='Unknown role needs diagnosed retry.';bad.report(bad.token(),r)
    check(bad.state=='needs_retry' and bad.response_history[-1]['report']==r, 'unknown role retained with reachable retry')
    before=deepcopy(bad.response_history);bad.diagnose(bad.token(),'Name the role on another manual attempt.')
    check(bad.state=='need_sing' and bad.response_history==before, 'role diagnosis retains history')
    bad.cancel(bad.token());bad.reopen(bad.token())
    refuse(lambda:bad.sing_top(bad.token(),{'sung_before_voicing':'yes','notes':'Synthetic.'}), 'reopen release fence', bad)
    bad.release(bad.token(),{'learner_released':True});step(bad)
    # Melody-loss recovery repeats the interrupted texture after a real reduction task.
    lost=m.FixedTopFlow(rows[0]['package_key']);lost.set_top(lost.token(),top_choice(lost));step(lost)
    lost.sing_top(lost.token(),{'sung_before_voicing':'yes','notes':'Synthetic.'});lost.choose_voicing(lost.token(),voicing(lost));lost.name_role(lost.token(),{'role':lost.expected_role(),'notes':'Synthetic.'});lost.play(lost.token(),True);lost.release(lost.token(),{'learner_released':True});lost.report(lost.token(),report(lost,'no'))
    check(lost.state=='needs_reduction','lost melody requires bass+melody reduction')
    stage=lost.stage_index;lost.diagnose(lost.token(),'Reduce immediately, then repeat the interrupted texture.');step(lost)
    check(lost.state=='need_sing' and not lost.recovery and lost.stage_index==stage,'reduction does not skip interrupted source texture')
    low=m.FixedTopFlow(rows[0]['package_key']);low.set_top(low.token(),top_choice(low,48));low.sing_top(low.token(),{'sung_before_voicing':'yes','notes':'Synthetic.'});low.cannot_realize(low.token(),'The chosen register cannot support this finite voicing.')
    previous=deepcopy(low.history);choice=top_choice(low);choice['diagnosis']='Choose a new whole-attempt register rather than invent lower guitar notes.';low.restart_top(low.token(),choice)
    check(low.state=='need_sing' and low.top['midi']==72 and low.history[:len(previous)]==previous,'unrealizable chosen register has full same-key recovery')
    print(json.dumps({'schema_version':'fathom-private-cheap-all-key-integrity.1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'elapsed_seconds':time.monotonic()-tick,'checks_passed':checks,'causal_refusals_passed':refusals,'refusal_criteria':labels,
        'exact_keys_checked':41,'chosen_texture_arithmetic_checks':chosen_geometry,'complete_AB_walkthroughs':1,'complete_C_walkthroughs':1,
        'completed_sample_textures':ab_stages+c_stages,'source_harmonies_checked':53,'source_unresolved':0,'outcome':'PASS',
        'inputs':[pin(Path('Tests')/LANE/'check_integrity_r02.py'),seal['model'],seal['packet']],
        'synthetic_reports_are_observations':False,'independently_behavior_reviewed':0,'Accepted':0,
        'not_run':seal['deferred_qa']}))


if __name__ == '__main__':
    main()
