#!/usr/bin/env python3
"""Bounded source motif relationships and symbolic action ownership checks."""
import copy, hashlib, importlib.util, json, resource, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LANE = 'fullscope-private-a-r01'
BASE = ROOT / f'Tools/{LANE}/level048-motif-relations-r01'


def module(name):
    spec = importlib.util.spec_from_file_location(name, BASE / f'{name}.py')
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


actions, relations = module('actions'), module('relations')
old = [json.loads(x) for x in (ROOT / f'Build/{LANE}/level048-r07/packet.jsonl').read_text().splitlines()]
new = [json.loads(x) for x in (ROOT / f'Build/{LANE}/level048-r08/packet.jsonl').read_text().splitlines()]
seed = old[9]
start = time.perf_counter()
positive, negative = [], []
for row in range(10, 18):
    before, after = old[row - 1], new[row - 1]
    built = actions.build(before)
    assert built == actions.build(copy.deepcopy(before)) == after['implementation']['symbolic_action_segments']
    link = relations.relation(seed, before, row)
    emitted = copy.deepcopy(after['implementation']['printed_motif_relation'])
    binding = emitted.pop('seed_source_binding')
    assert link == relations.relation(copy.deepcopy(seed), copy.deepcopy(before), row) == emitted
    assert binding['line'] == 10 and binding['package_key'] == seed['package_key']
    assert before['implementation']['sounding_events'] == after['implementation']['sounding_events']
    assert before['unresolved_reasons'] == after['unresolved_reasons']
    assert before['status'] == after['status'] and before['timing_authority'] == after['timing_authority']
    assert all(s['numeric_onset'] is None and s['numeric_acoustic_gate'] is None for s in built['contact_segments'])
    assert not built['capabilities']['native_projection_complete']
    positive.append({'row': row, 'kind': link['kind'], 'deterministic_materialized_match': True,
                     'source_events_and_unresolved_status_retained': True, 'no_numeric_gate_or_clock': True})

# Explicit positive controls for the non-generic printed transformations.
assert new[13]['implementation']['printed_motif_relation']['per_event_semitone_changes'] == [24, 24, 24, 24, 24, 12]
assert new[13]['implementation']['printed_motif_relation']['source_articulation_changes'] == [
    {'event_ordinal': 2, 'seed': 'hammer_on', 'variant': 'picked'}]
assert new[15]['implementation']['printed_motif_relation']['retimed_seed_event_ordinals'] == [3, 4, 5, 6]
assert new[16]['implementation']['printed_motif_relation']['literal_seed_subsequence'] is False
held = [a for a in new[16]['implementation']['symbolic_action_segments']['actions'] if a['kind'] == 'hold']
assert len(held) == 1 and held[0]['owner_event_ordinal'] == 3 and not held[0]['new_pick_attack']


def reject(name, row, mutate, check):
    bad = copy.deepcopy(old[row - 1])
    mutate(bad)
    try:
        check(bad)
    except (ValueError, AssertionError) as error:
        negative.append({'case': name, 'row': row, 'refusal_type': type(error).__name__, 'detail': str(error)})
    else:
        raise AssertionError(f'Mutation was not refused: {name}')


def event(index, **changes):
    return lambda r: r['implementation']['sounding_events'][index].update(changes)


def relate(row):
    return lambda r: relations.relation(seed, r, row)


reject('echo altered pitch', 11, event(0, source_note='B'), relate(11))
reject('echo altered articulation', 11, event(1, attack='picked'), relate(11))
reject('displacement retained seed start', 12,
       event(0, relative_position={'bar': 1, 'beat': 1, 'phase': 'beat'}), relate(12))
reject('reversal retains forward order', 13,
       lambda r: r['implementation'].update(sounding_events=copy.deepcopy(seed['implementation']['sounding_events'])), relate(13))
reject('register shift falsely uniform two octaves', 14, event(5, pitch_encoding_midi=91), relate(14))
reject('recolor discards printed major third', 15, event(2, source_note='C'), relate(15))
reject('expansion changes retained source contact', 16, event(0, physical_fret=6), relate(16))
reject('reduction incorrectly treated as seed deletion', 17, event(1, source_note='C'), relate(17))
reject('outside finite motif scope', 10, lambda r: None, relate(18))
reject('unpicked arrival receives new attack', 10, event(1, pick_attack=True), actions.build)
reject('unpicked cross-string arrival', 10, event(1, string_label='G'), actions.build)
reject('rest receives new attack', 10,
       lambda r: r['implementation']['symbolic_count_slots'][2].update(attack_mark='P'), actions.build)
reject('orphan initial hold', 10,
       lambda r: r['implementation']['symbolic_count_slots'][0].update(kind='hold', note='=', attack_mark='=', source_contact_ordinals=[]), actions.build)
reject('hold assigned an extra contact', 17,
       lambda r: r['implementation']['symbolic_count_slots'][5].update(source_contact_ordinals=[3]), actions.build)
reject('source slot order reversed', 10,
       lambda r: r['implementation']['symbolic_count_slots'].reverse(), actions.build)

report = {'status': 'PASS', 'positive_cases': positive, 'causal_refusals': negative,
          'test_scope': 'Finite relationships and source action ownership; not a general external record validator.',
          'native_audio_app_tests': 'NOT_RUN', 'elapsed_seconds': time.perf_counter() - start,
          'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
path = ROOT / f'Results/{LANE}/level048-r08/motif-tests.json'
with path.open('x') as out:
    json.dump(report, out, indent=2)
    out.write('\n')
print(json.dumps({'positive': len(positive), 'causal_refusals': len(negative),
                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}))
