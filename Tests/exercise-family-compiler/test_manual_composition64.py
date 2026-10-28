#!/usr/bin/env python3
"""Cached source/DATA validation only; this is not a native owner implementation.

The small interpreter below evaluates closed descriptors against synthetic manual
declarations. It cannot establish actual playing/listening, token ownership,
release/navigation safety, runtime admission or acceptance.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('composition_compiler', ROOT / 'Tools/exercise-family-compiler/compile_manual_composition64.py')
compiler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compiler)
COUNTS = Counter()


def check(value, label):
    COUNTS['assertions'] += 1
    if not value:
        raise AssertionError(label)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def pinned(ref):
    path = ROOT / ref['path']
    check(not path.is_symlink(), 'no symlink')
    raw = path.read_bytes()
    check(len(raw) == ref['bytes'] and digest(raw) == ref['sha256'], 'exact byte pin: ' + ref['path'])
    return raw


def schema_valid(specification, value):
    if 'const' in specification:
        return type(value) is type(specification['const']) and value == specification['const']
    kinds = specification['type']
    kinds = kinds if isinstance(kinds, list) else [kinds]
    types = {'string': str, 'boolean': bool, 'integer': int, 'null': type(None), 'object': dict}
    if not any(type(value) is types[kind] for kind in kinds):
        return False
    if 'enum' in specification and not any(type(value) is type(item) and value == item for item in specification['enum']):
        return False
    if value is None:
        return True
    if isinstance(value, dict):
        return (set(value) == set(specification['properties']) == set(specification['required'])
                and specification['additionalProperties'] is False
                and all(schema_valid(specification['properties'][field], item) for field, item in value.items()))
    if isinstance(value, str):
        return specification.get('minLength', 0) <= len(value) <= specification.get('maxLength', 2 ** 31)
    if type(value) is int:
        return specification.get('minimum', -2 ** 31) <= value <= specification.get('maximum', 2 ** 31)
    return True


def reference(ref, payload, saved):
    check(set(ref) == {'scope', 'path'} and ref['scope'] in ['payload', 'saved'], 'finite reference')
    current = payload if ref['scope'] == 'payload' else saved
    for part in ref['path']:
        current = current[part]
    return current


def outcome(node, payload, saved):
    if not schema_valid(node['schema'], payload):
        return 'malformed'
    for field, expected in node['expected'].items():
        if type(payload[field]) is not type(expected) or payload[field] != expected:
            return 'diagnosed'
    for guard in node['constraints']:
        kind = guard['kind']
        if kind == 'required_manual_fields_resolved':
            valid = all(payload[field] is not None for field in guard['fields'])
        elif kind == 'nonempty_trimmed_text':
            text = payload[guard['field']]
            valid = isinstance(text, str) and guard['minimum'] <= len(text.strip()) <= guard['maximum']
        elif kind == 'different':
            left, right = (payload[field] for field in guard['fields'])
            valid = left is not None and right is not None and left != right
        elif kind == 'same_as_saved':
            left, right = reference(guard['left'], payload, saved), reference(guard['right'], payload, saved)
            valid = left is not None and type(left) is type(right) and left == right
        else:
            raise AssertionError('foreign guard ' + kind)
        if not valid:
            return 'diagnosed'
    return 'positive'


def fixture(node, saved, choice=None):
    payload = {}
    for field, specification in node['schema']['properties'].items():
        if 'const' in specification:
            payload[field] = copy.deepcopy(specification['const'])
        elif field in node['expected']:
            payload[field] = copy.deepcopy(node['expected'][field])
        elif 'enum' in specification:
            payload[field] = next(item for item in specification['enum'] if item is not None and item != 'unknown')
        elif 'string' in specification['type']:
            payload[field] = 'Synthetic declaration for ' + field
        elif 'integer' in specification['type']:
            payload[field] = specification['minimum']
        else:
            payload[field] = True
    for guard in node['constraints']:
        if guard['kind'] == 'same_as_saved':
            payload[guard['left']['path'][0]] = copy.deepcopy(reference(guard['right'], payload, saved))
    if node['kind'] == 'choice' and choice is not None:
        payload[node['route_field']] = choice
    return payload


class DataTrace:
    """Test-only descriptor traversal with explicit synthetic release markers."""
    def __init__(self, program):
        self.program = program
        self.current = program['graph']['entry']
        self.saved = {}
        self.history = []
        self.release_due = False
        self.pending_next = None

    @property
    def node(self):
        return self.program['graph']['nodes'][self.current]

    def apply(self, payload, requested_node=None):
        if self.release_due or requested_node not in [None, self.current] or self.node['kind'] == 'end':
            return 'refused'
        result = outcome(self.node, payload, self.saved)
        if result == 'malformed':
            return result
        self.history.append({'node': self.current, 'raw': copy.deepcopy(payload), 'result': result})
        if result == 'diagnosed':
            return result
        if self.node['save_as']:
            self.saved[self.node['save_as']] = copy.deepcopy(payload)
        next_node = self.node['routes'][payload[self.node['route_field']]]['next'] if self.node['kind'] == 'choice' else self.node['next']
        if self.node['physical']:
            self.release_due, self.pending_next = True, next_node
        else:
            self.current = next_node
        return result

    def release(self):
        check(self.release_due, 'explicit DATA release marker only when due')
        self.history.append({'synthetic_release': True})
        self.current, self.pending_next, self.release_due = self.pending_next, None, False

    def advance(self, choice=None):
        payload = fixture(self.node, self.saved, choice)
        check(self.apply(payload) == 'positive', 'synthetic descriptor positive: ' + self.current)
        if self.release_due:
            check(self.apply(payload) == 'refused', 'physical extent cannot accept another descriptor before marker')
            COUNTS['expected_refusals'] += 1
            self.release()
        return payload

    def run(self, choices=None):
        choices = choices or {}
        limit = 100
        while self.node['kind'] != 'end':
            check(limit > 0, 'bounded synthetic trace')
            limit -= 1
            self.advance(choices.get(self.current))
        return self


def expect_outcome(trace, payload, expected):
    prior = copy.deepcopy((trace.current, trace.saved, trace.history, trace.release_due))
    check(trace.apply(payload) == expected, 'material counterexample: ' + expected)
    if expected in ['malformed', 'refused']:
        check(prior == (trace.current, trace.saved, trace.history, trace.release_due), 'malformed descriptor is unchanged')
        COUNTS['expected_refusals'] += 1
    else:
        check(trace.current == prior[0] and trace.saved == prior[1] and trace.history[-1]['raw'] == payload, 'diagnosed raw declaration retained without advance')
        COUNTS['diagnosed_unknown_or_negative'] += 1


def structural(program):
    nodes = program['graph']['nodes']
    check(program['fixed_bpm'] is None and not program['performance_observed'] and not program['grants_credit'] and not program['runtime_admitted'], 'no clock/observation/credit/runtime claim')
    check(program['graph']['entry'] in nodes and program['steps'] == [], 'closed graph entry')
    saves = {node['save_as']: node for node in nodes.values() if node.get('save_as')}
    for name, node in nodes.items():
        check(node['kind'] in ['report', 'choice', 'end'], 'finite node kind')
        if node['kind'] == 'end':
            continue
        fields = node['schema']['properties']
        check(set(fields) == set(node['schema']['required']) and node['schema']['additionalProperties'] is False, 'closed required fields')
        check(all('default' not in specification for specification in fields.values()), 'blank/manual inputs without defaults')
        for field, specification in fields.items():
            check(specification['input_role'] in ['manual_report', 'source_binding'], 'learner whitelist role')
            check(('const' in specification) == (specification['input_role'] == 'source_binding'), 'source facts cannot be reported defaults')
            check('sha256' not in field and 'custody' not in field and 'source_key' not in field, 'no custody in forms')
        if node['kind'] == 'report':
            resolved = [g for g in node['constraints'] if g['kind'] == 'required_manual_fields_resolved']
            check(len(resolved) == 1 and resolved[0]['fields'] == [field for field, item in fields.items() if item['input_role'] == 'manual_report'], 'all required manual unknowns remain diagnosed')
            check(node['next'] in nodes, 'closed report target')
        else:
            check(set(node['routes']) == set(fields[node['route_field']]['enum']), 'closed explicit choice routes')
            check(all(item['next'] in nodes for item in node['routes'].values()), 'closed choice targets')
        for guard in node['constraints']:
            check(guard['kind'] in ['required_manual_fields_resolved', 'different', 'same_as_saved', 'nonempty_trimmed_text'], 'closed guard kind')
            if guard['kind'] == 'same_as_saved':
                saved_name, saved_field = guard['right']['path']
                check(saved_name in saves and saved_field in saves[saved_name]['schema']['properties'], 'bound saved source declaration')
                incoming = fields[guard['left']['path'][0]]
                retained = saves[saved_name]['schema']['properties'][saved_field]
                if 'maxLength' in retained:
                    check(incoming['maxLength'] >= retained['maxLength'], 'every allowed retained value can be reentered')
        COUNTS['typed_nodes'] += 1
        COUNTS['physical_nodes'] += int(node['physical'])


def program_oracles(programs):
    nodes = lambda name: programs[name]['graph']['nodes']
    def chain(name, ordered):
        n = nodes(name)
        check(programs[name]['graph']['entry'] == ordered[0], 'source first step ' + name)
        for first, second in zip(ordered, ordered[1:]):
            check(n[first]['next'] == second, 'source order ' + name + ':' + first)
    chain('motif_seed', ['sing', 'realization', 'first', 'second', 'end'])
    check('chosen_key' not in nodes('motif_seed')['sing']['schema']['properties'], 'key comes after contour/rhythm singing')
    chain('rhythm_motif', ['write', 'perform', 'end'])
    check(len([g for g in nodes('rhythm_motif')['write']['constraints'] if g['kind'] == 'different']) == 3, 'three distinct contours')
    chain('transformation', ['write', 'constraint', 'pair', 'audibility'])
    check(nodes('transformation')['pair']['physical'] and nodes('transformation')['audibility']['routes']['not_audible']['next'] == 'restore', 'source pair plus conditional identity restore')
    chain('harmony_first', ['functions', 'voicings', 'melody', 'perform', 'constraint', 'audit', 'remove_compare', 'end'])
    audit = nodes('harmony_first')['audit']['schema']['properties']
    check('strongest_departure_location' in audit and 'strongest_departure_bar' not in audit, 'source accepts section or bar without mandatory bar restriction')
    chain('melody_first', ['sing', 'write', 'chords', 'constraint', 'alternate_bass', 'test', 'reduction', 'inner_choice'])
    check(nodes('melody_first')['inner_choice']['routes']['not_useful']['next'] == 'rank' and nodes('melody_first')['inner_choice']['routes']['useful']['next'] == 'inner', 'inner voice conditional route after required reduction')
    check(len(nodes('melody_first')['rank']['schema']['properties']['six_source_versions_reference']['const']) == 6, 'six literal versions despite four heading')
    chain('bass_first', ['bass', 'sing_top', 'harmony', 'perform', 'constraint', 'end'])
    chain('independence', ['material'] + ['pass' + str(i) for i in range(1, 7)] + ['end'])
    check([nodes('independence')['pass' + str(i)]['schema']['properties']['source_harmony']['const'] for i in range(1, 5)] == ['roots only', 'triads', '7th chords', 'alternate inversions'], 'four fixed bass passes before simplify/new bass')
    chain('rhythm_first', ['muted', 'harmony', 'perform', 'constraint', 'end'])
    chain('fixed_harmony', ['write', 'compare', 'end'])
    check(nodes('fixed_harmony')['write']['schema']['properties']['source_progression']['const'] == ['Am7', 'Fmaj7', 'Cmaj7', 'G7'] * 2, 'source fixed progression')
    chain('constraint_lab', ['material', 'draft', 'constraint', 'perform', 'revise_choice'])
    check(nodes('constraint_lab')['draft']['expected'] == {'draft_bars': 8, 'revision_started_before_full_draft': False}, 'full eight-bar draft before revision')


def material_checks(resolved):
    # One representative per real program plus variant-aware checks on all64.
    choices = {'inner_choice': 'not_useful', 'revise_choice': 'retain_draft', 'audibility': 'audible'}
    for program in resolved.values():
        trace = DataTrace(program).run(choices)
        check(len(trace.history) > 1, 'full source-specific synthetic descriptor path')
        COUNTS['synthetic_descriptor_paths'] += 1
    representatives = {}
    for key, program in resolved.items():
        representatives.setdefault(program['name'], program)
    for program in representatives.values():
        trace = DataTrace(program)
        payload = fixture(trace.node, trace.saved)
        for mutation in [dict(payload, foreign_field=True), {k: v for k, v in payload.items() if k != next(iter(payload))}]:
            expect_outcome(trace, mutation, 'malformed')
        manual = next(field for field, specification in trace.node['schema']['properties'].items() if specification['input_role'] == 'manual_report')
        if isinstance(trace.node['schema']['properties'][manual].get('type'), list):
            expect_outcome(trace, dict(payload, **{manual: None}), 'diagnosed')
        expect_outcome(trace, dict(payload, **{manual: {'foreign': True}}), 'malformed')
        check(trace.apply(payload, requested_node='end') == 'refused', 'cannot submit future DATA stage')
        COUNTS['expected_refusals'] += 1

    def get(name):
        return next(program for program in resolved.values() if program['name'] == name)
    def go(name, target):
        trace = DataTrace(get(name))
        while trace.current != target:
            trace.advance(choices.get(trace.current))
        return trace
    trace = go('l100_motif_seed_sing_then_key_two_registers', 'realization')
    payload = fixture(trace.node, trace.saved)
    expect_outcome(trace, dict(payload, second_register=payload['first_register']), 'diagnosed')
    expect_outcome(trace, dict(payload, first_realization='\u00a0\t '), 'diagnosed')
    long_material = dict(payload, first_realization='x' * 4096)
    check(trace.apply(long_material) == 'positive', 'entire legal realization range')
    trace.advance()
    trace.advance()
    check(trace.node['kind'] == 'end', 'long legal realization remains completable')
    trace = go('l100_same_rhythm_three_contours', 'write')
    payload = fixture(trace.node, trace.saved)
    expect_outcome(trace, dict(payload, contour3=payload['contour1']), 'diagnosed')
    trace = go('l100_original_variant_conditional_identity_restore', 'audibility')
    trace.advance('not_audible'); check(trace.current == 'restore', 'negative audibility retains identity-repair route')
    trace.advance(); trace.advance(); trace.advance('audible')
    check(trace.node['kind'] == 'end' and 'restored' in trace.saved, 'restored variant can complete after actual declared recompare')
    trace = go('l100_original_variant_conditional_identity_restore', 'audibility')
    trace.advance('unknown'); expect_outcome(trace, {'relationship': 'unknown'}, 'diagnosed')
    trace = go('l100_function_voicing_melody_harmonic_audit', 'remove_compare')
    payload = fixture(trace.node, trace.saved)
    expect_outcome(trace, dict(payload, optional_chord_identity_reentry='foreign chord'), 'diagnosed')
    trace = go('l100_sing_write_harmonize_alternate_reduce_useful_inner_rank', 'reduction')
    payload = fixture(trace.node, trace.saved)
    expect_outcome(trace, dict(payload, bass_plus_melody_reduction_performed=False), 'diagnosed')
    check(trace.apply(payload, requested_node='rank') == 'refused', 'DATA reduction cannot be jumped')
    COUNTS['expected_refusals'] += 1
    trace.advance(); trace.advance('useful'); trace.advance(); trace.advance()
    check(trace.node['kind'] == 'end', 'useful-inner-voice branch after reduction')
    trace = go('l100_sing_write_harmonize_alternate_reduce_useful_inner_rank', 'inner_choice')
    trace.advance('unknown'); expect_outcome(trace, {'usefulness': 'unknown'}, 'diagnosed')
    trace = go('l100_bass_then_sung_top_line_then_harmony', 'harmony')
    expect_outcome(trace, dict(fixture(trace.node, trace.saved), top_line_reentry='replacement top line'), 'diagnosed')
    trace = go('l100_six_ordered_bass_harmony_independence_passes', 'pass6')
    expect_outcome(trace, dict(fixture(trace.node, trace.saved), new_bass=trace.saved['material']['fixed_bass']), 'diagnosed')
    trace = go('l100_muted_rhythm_identity_before_harmony', 'harmony')
    expect_outcome(trace, dict(fixture(trace.node, trace.saved), rhythm='replacement rhythm'), 'diagnosed')
    trace = go('l100_fixed_eight_bar_harmony_distinct_rhythmic_identity', 'write')
    expect_outcome(trace, dict(fixture(trace.node, trace.saved), source_progression=['C'] * 8), 'malformed')
    trace = go('l100_eight_bar_complete_draft_before_revision', 'draft')
    payload = fixture(trace.node, trace.saved)
    expect_outcome(trace, dict(payload, draft_bars=True), 'malformed')
    expect_outcome(trace, dict(payload, draft_bars=7), 'malformed')
    expect_outcome(trace, dict(payload, revision_started_before_full_draft=True), 'diagnosed')
    trace.advance(); trace.advance(); trace.advance(); trace.advance('revise')
    payload = fixture(trace.node, trace.saved)
    expect_outcome(trace, dict(payload, revised_draft=payload['original_draft_reentry']), 'diagnosed')
    trace.advance(); trace.advance(); check(trace.node['kind'] == 'end', 'distinct revision remains possible')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--generated', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    generated = ROOT / args.generated
    closure = json.loads((generated / 'family-closure.json').read_bytes())
    check(closure['rows'] == 64 and closure['shared_source_programs'] == 10 and closure['perrow_model_files'] == 0, 'factored64/10 scope')
    for ref in closure['files'] + [closure['compiler'], closure['selection'], closure['payload'], closure['source_scope'], closure['cached_context']]:
        pinned(ref)
    selection = json.loads(pinned(closure['selection']))
    payload_lines = pinned(closure['payload']).splitlines(keepends=True)
    source_scope = {row['package_key']: row for row in json.loads(pinned(closure['source_scope']))['rows']}
    pages = {row['physical_page']: row['text'] for row in json.loads(pinned(closure['cached_context']))['pages']}
    rows = [json.loads(line) for line in (generated / 'definitions.jsonl').read_bytes().splitlines()]
    shared = json.loads((generated / 'programs.json').read_bytes())
    contexts = json.loads((generated / 'contexts.json').read_bytes())
    keys = [row['source_key'] for row in rows]
    check(keys == sorted(set(keys)) == sorted(selection['keys']) == closure['keys'], 'complete closed key set, no duplicate or foreign key')
    check(len(rows) == len(source_scope) == 64 and len(shared['programs']) == 10, 'exact64 denominator')
    resolved = {}
    source_variants = Counter()
    for row in rows:
        selected = source_scope[row['source_key']]
        raw = payload_lines[row['payload_ref']['jsonl_line'] - 1]
        original = json.loads(raw)
        check(digest(raw) == row['raw_source_line_sha256'] == selected['raw_jsonl_line_sha256'], 'exact original line including newline')
        check(digest(compact(original)) == row['original_compact_sha256'], 'exact compact original export')
        check(digest(json.dumps(original, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()) == row['original_canonical_sha256'], 'canonical original hash')
        check(row['source_identity'] == original['source_identity'] and row['source_key'] == original['package_key'], 'identity unchanged')
        check(row['source_pins'] == original['source_refs'] and row['source_locator'] == selected['source_locator'], 'cached provenance unchanged')
        check(row['source_kind_preserved'] == original['implementation']['kind'] == 'structured_source_prescription', 'original kind unchanged')
        check(row['retained_contract_path'] == ['implementation', 'task', 'contract'], 'exact retained contract path')
        check(row['printed_components'] == original['implementation']['task']['printed_components'], 'all printed row components unchanged')
        check(row['source_task_instruction_refs'] == [['implementation', 'task', 'instructions', i] for i in range(len(original['implementation']['task']['instructions']))], 'all source instruction row refs')
        check(row['learner_instruction_row_refs'] == [['implementation', 'task', 'label']], 'source label projected safely')
        check(not row['native_executable'] and not row['performance_observed'] and not row['grants_credit'], 'DATA does not admit or accept')
        program = shared['programs'][row['program_ref']]
        value = compiler.materialize(program, row['parameters'], row['program_ref'])
        check(digest(compact(value)) == row['resolved_program_sha256'] == closure['resolved_program_hashes'][row['source_key']], 'deterministic resolved behavior hash')
        structural(value)
        resolved[row['source_key']] = value
        source_variants[row['program_ref']] += 1
        for malformed in [dict(row['parameters'], foreign_parameter=True), {k: v for k, v in row['parameters'].items() if k != next(iter(row['parameters']))}]:
            try:
                compiler.materialize(program, malformed, row['program_ref'])
                check(False, 'foreign/missing parameter must refuse')
            except AssertionError as error:
                check(str(error) == 'closed parameter fields', 'parameter refusal before expansion')
                COUNTS['expected_refusals'] += 1
    check(dict(source_variants) == closure['program_counts'], 'exact source program counts')
    for page, spans in contexts['learner_instruction_spans'].items():
        for span in spans:
            text = pages[int(page)][span['start']:span['end']]
            check(text == span['text'] and digest(text.encode()) == span['text_sha256'], 'exact Unicode cached source instruction span')
            COUNTS['cached_instruction_spans'] += 1
    check(contexts['source_table_headings_discrepancies'] == [{'page': 10, 'heading': 'One Melody, Four Harmonizations', 'printed_versions': 6}, {'page': 14, 'heading': 'Same Harmony, Four Rhythmic Identities', 'printed_versions': 6}], 'literal heading/count discrepancies retained')
    check(contexts['supporting_context_only']['blanket_recording_capstone_or_14of16_gate_on_selected64'] is False, 'H/I/J are supporting, not blanket gates')
    check('Selected seven' in contexts['family_duties']['G'], 'eighth G card family debt explicit')
    first_by_program = {}
    for row in rows:
        first_by_program.setdefault(row['program_ref'], resolved[row['source_key']])
    program_oracles(first_by_program)
    material_checks(resolved)
    output = ROOT / args.output
    check(not output.exists(), 'fresh proof only')
    value = {'schema': 'fathom.manual-composition64-data-proof.1', 'pass': True,
             'rows': 64, 'source_programs': 10, 'source_variants': dict(source_variants),
             'counts': dict(COUNTS), 'wall_seconds': time.perf_counter() - started,
             'test': compiler.pin(Path(__file__)), 'closure': compiler.pin(generated / 'family-closure.json'),
             'evidence_kind': 'cached source and closed DATA descriptor validation with synthetic manual declarations',
             'original_pdf_or_txt_reads': 0, 'native_execution': False, 'runtime_admission': False,
             'official_acceptance_increment': 0,
             'remaining_native_review': ['shared parameter/factory normalization', 'native required_manual_fields_resolved guard',
                                         'owner/revision/source/token lifetime and strict source-player versus learner projection',
                                         'persistent history/release/retry/navigation and family D/G audit debt',
                                         'changed native behavior, independent source/material review, shared-form and actual installed Home gates']}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(compact(value) + b'\n')
    print(json.dumps(value, ensure_ascii=False))


if __name__ == '__main__':
    main()
