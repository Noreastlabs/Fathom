#!/usr/bin/env python3
"""Finite, source-bound Level2 private export. This grants no runtime capability."""
from __future__ import annotations
import argparse
from fractions import Fraction
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import subprocess
import sys

BASE = 'manager-resume-r01/level002-finite-exporter-r01'
SELF = 'Tools/' + BASE + '/export_level002.py'
PACKET = 'Build/fullscope-private-a-r01/level002-r01/packet.jsonl'
TXT = 'Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_2_Two_String_Transfer.txt'
PDF = 'Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_2_Two_String_Transfer.pdf'
REVIEW = 'Results/manager-resume-r01/level002-all108-source-review-r01/source-review.json'
GUIDANCE = 'Build/fullscope-private-a-r01/level002-guidance-supplement-r01/guidance.json'
PINS = {
    PACKET: '534471bc4827c4f95c4e48d388e832a9db4b61394963b1b54d0c39ea1cac07cc',
    TXT: '49ca027e8c7fee7b2c5437f93f8a5b5576e272e6cf888dbb1a82632749cec31a',
    PDF: 'cfcc4b3414400f5bfc2510c30c407f0d72e573ef8e899a184820202d67671ac8',
    REVIEW: '9a1d71e6fa11fde557ebb15ebbdc9bd13515a12054105c9d4786abd780c1e1fe',
    'Results/manager-resume-r01/level002-all108-source-review-r01/review-report.md': 'e60ee7f14b52c6cd8a06252385a2ece2f5d77ef3946aa485eb89c432bac7489a',
    'Results/manager-resume-r01/level002-all108-source-review-r01/artifact-manifest.json': 'b2910f603bb961c33b4fb02356a27d846c36abe71f7d3ad9ecccb28f02ef81b7',
    'Results/primary/20260927T1236Z-level002-all108-private-source-family-adoption.md': '30cc18d13d08de4c66b2448e7d0b9cf9667cd9a9769e72a2a62a050cad13fc49',
    'Prompts/manager-resume-r01/20260927T1236Z-level002-private-finite-exporter-release.md': '48ef4298eb302ba0096b212e43a5986da9aba59d80de098d7f09062ebcf7f8a7',
    GUIDANCE: '5424c0a3656ccb885008e9f80d321b40ca53acc610f5508588a7bb3e1c3b3227',
    'Build/fullscope-private-a-r01/level002-guidance-supplement-r01/original-page1-extraction.txt': '2123bfb15b2aea242812cc9efece9799e42c7c49fc0a048bec2f05a5d405bf4e',
}
MAX_INT = (1 << 63) - 1
MAX_FILE_BYTES = 8 * 1024 * 1024
LOW_STRINGS = 'EADGBe'
OPEN_MIDI = dict(zip(LOW_STRINGS, (40, 45, 50, 55, 59, 64)))
CODES = [''.join(x) for x in itertools.product('1234', repeat=4)
         if all(x[i] != x[i + 1] for i in range(3))]
PAIRS = list(zip(LOW_STRINGS[:-1], LOW_STRINGS[1:])) + list(zip(LOW_STRINGS[:0:-1], LOW_STRINGS[-2::-1]))
ROOT_KEYS = set('schema_version package_key source_identity level existing_parent_id source_refs source_payload implementation timing_authority unresolved_reasons provenance status'.split())
IMPLEMENTATION_KEYS = set('kind ordered_contacts task_steps ordered_rest_locations ordering_basis runtime_eligible canonical_ids_allocated mastery_or_credit relative_variants'.split())
CONTACT_KEYS = set('ordinal kind block_index grid_column string_label string_low_to_high fret finger onset_q duration_q midi annotations source_line source_column_1based technique_symbols same_column_contact_count attack_authority midi_basis'.split())
VARIANT_KEYS = set('start_stroke contact_ordinals strokes end_q basis'.split())
GUIDANCE_CLAUSES = {
    'set_scope': 'Choose one 12-exercise set.',
    'rhythm_scope': 'Use one rhythmic grouping for that session.',
    'continuous_traversal': 'Play every exercise up and down continuously.',
    'both_pick_starts': 'Repeat with the opposite starting pick stroke.',
    'tempo_advance': 'After three clean loops, add 2 BPM next time.',
    'tempo_reduce': 'After two errors or rising tension,\nreduce 4-6 BPM.',
    'full_set_progression': 'Advance when a full set is clean in both pick-start directions on two separate days.',
    'fifth_position': 'No position shift is added yet.',
    'session_limit': 'Do not run all 108 in one session.',
}


class Refusal(ValueError):
    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(detail)


def need(condition, code, detail):
    if not condition:
        raise Refusal(code, detail)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def strict_json(raw: bytes):
    need(len(raw) <= MAX_FILE_BYTES, 'INPUT_SIZE', 'JSON exceeds private input bound')
    def pairs(items):
        obj = {}
        for key, value in items:
            need(key not in obj, 'JSON_DUPLICATE_KEY', key)
            obj[key] = value
        return obj
    def nonfinite(token):
        raise Refusal('JSON_NONFINITE', token)
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=nonfinite)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise Refusal('JSON_SYNTAX', str(error)) from error


def shape(value, keys, detail):
    need(type(value) is dict and set(value) == keys, 'UNSUPPORTED_FIELD', detail)


def reduced(n, d):
    need(type(n) is int and type(d) is int, 'RATIONAL_INTEGER', 'Exact integer pair required')
    need(n >= 0 and d > 0, 'RATIONAL_SIGN', 'Nonnegative numerator and positive denominator required')
    need(n <= MAX_INT and d <= MAX_INT, 'RATIONAL_OVERFLOW', 'Signed64 input component exceeded')
    divisor = math.gcd(n, d)
    return [n // divisor, d // divisor]


def source_quarter(value):
    need(type(value) in (int, float), 'RATIONAL_INTEGER', 'Legacy source metric value must be numeric')
    need(type(value) is int or math.isfinite(value), 'RATIONAL_NONFINITE', 'Finite source metric value required')
    q = Fraction(str(value))
    return reduced(q.numerator, q.denominator)


def verify_input_bytes(path, raw):
    need(path in PINS, 'UNREVIEWED_INPUT', path)
    need(len(raw) <= MAX_FILE_BYTES, 'INPUT_SIZE', path)
    need(sha(raw) == PINS[path], 'INPUT_SHA', path)
    return raw


def expected_source(txt: str):
    lines = txt.splitlines()
    labels = [(i, re.fullmatch(r'Exercise (\d{3}): ([1-4]{4})', line))
              for i, line in enumerate(lines)]
    labels = [(i, m) for i, m in labels if m]
    need([(m[1], m[2]) for _, m in labels] == [(f'{i+1:03}', c) for i, c in enumerate(CODES)],
         'SOURCE_CODE_ORDER', 'Original finite108 code enumeration changed')
    specs = []
    for i, (start, match) in enumerate(labels):
        code = match[2]
        unit = lines[start:start + 15]
        need(len(unit) == 15 and unit[1] == 'ASCEND' and unit[8] == 'DESCEND',
             'SOURCE_DIRECTION', str(i + 1))
        tokens = []
        for block, offset in enumerate((2, 9), 1):
            group = []
            for local_row, line in enumerate(unit[offset:offset + 6]):
                m = re.fullmatch(r'([eBGDAE])\|([5-8|\-]+)', line)
                need(m is not None, 'SOURCE_GRAMMAR', line)
                for token in re.finditer('[5-8]', m[2]):
                    group.append((token.start(), m[1], int(token[0]), start+offset+local_row+1, token.start()+3, block))
            need(len(group) == 20 and len({t[0] for t in group}) == 20, 'SOURCE_CONTACT_COUNT', str(i + 1))
            tokens.extend(sorted(group))
        expected = [(string, int(finger)+4, int(finger)) for pair in PAIRS
                    for string, finger in zip([pair[0]]*2 + [pair[1]]*2, code)]
        need([(t[1], t[2]) for t in tokens] == [(x[0], x[1]) for x in expected],
             'SOURCE_ROUTE', str(i + 1))
        set_number = i // 12 + 1
        identity = f'printed:l002:set-{set_number}-of-9-exercises-{(set_number-1)*12+1:03}-{set_number*12:03}:exercise-{i+1:03}-{code}'
        specs.append({'source_identity': identity, 'package_key': 'proposed-'+identity.replace(':', '-'),
                      'code': code, 'unit': unit, 'tokens': tokens, 'contacts': expected,
                      'set': set_number, 'ordinal': i + 1, 'page': set_number + 1})
    return specs


def validate_guidance(guidance):
    need(type(guidance) is dict, 'GUIDANCE_SHAPE', 'Object required')
    clauses = guidance.get('obligations')
    need(type(clauses) is list and len(clauses) == 9, 'GUIDANCE_OBLIGATIONS', 'Exactly nine reviewed clauses required')
    observed = {}
    for clause in clauses:
        shape(clause, {'key', 'verbatim', 'extracted_char_start', 'extracted_char_end'}, 'source guidance clause')
        need(clause['key'] not in observed, 'GUIDANCE_OBLIGATIONS', 'Duplicate clause')
        observed[clause['key']] = clause['verbatim']
    need(observed == GUIDANCE_CLAUSES, 'GUIDANCE_OBLIGATIONS', 'Unreviewed or invented source obligation')
    need(guidance['source']['sha256'] == PINS[PDF] and guidance['source']['physical_page'] == 1,
         'GUIDANCE_SOURCE', 'Original PDF page1 required')
    need(guidance['supplement_to_immutable_packet']['sha256'] == PINS[PACKET], 'GUIDANCE_SOURCE', 'Packet differs')
    app = guidance['applicability']
    need(all(app[k] is False for k in ('individual_exercise_pass_is_set_mastery', 'automatic_mastery_or_credit',
                                      'actual_clean_loops_errors_days_or_performance_observed')),
         'NO_CREDIT', 'Guidance may not assert observed performance or credit')


def project_record(record, spec, review):
    shape(record, ROOT_KEYS, 'source record')
    need(record['schema_version'] == 'fathom-private-source-implementation.1', 'UNSUPPORTED_SCHEMA', 'Source packet version')
    need(record['package_key'] == spec['package_key'] and record['source_identity'] == spec['source_identity'],
         'SOURCE_IDENTITY_ORDER', 'Missing/unreviewed/reordered source key')
    need(record['level'] == 2 and record['existing_parent_id'] == '2.3.1.1.1', 'SOURCE_SCOPE', 'Level/parent differs')
    need(record['source_payload']['exact_unit_lines'] == spec['unit'], 'SOURCE_TEXT', 'Exact original unit differs')
    need(record['unresolved_reasons'] == [], 'SOURCE_UNRESOLVED', 'No source conflict may be silently normalized')
    implementation = record['implementation']
    shape(implementation, IMPLEMENTATION_KEYS, 'implementation')
    need(implementation['kind'] == 'ordered_contact_transcription', 'UNSUPPORTED_KIND', 'Contact transcription required')
    need(all(implementation[key] is False for key in ('runtime_eligible', 'canonical_ids_allocated', 'mastery_or_credit')),
         'NO_CREDIT', 'No capability, canonical IDs or credit may be asserted')
    need(implementation['ordered_rest_locations'] == [], 'SOURCE_REST', 'Selected continuous traversal has no rest')
    contacts = implementation['ordered_contacts']
    need(type(contacts) is list and len(contacts) == 40, 'CONTACT_COUNT', 'Exactly40 source contacts required')
    events = []
    for i, (contact, expected, token) in enumerate(zip(contacts, spec['contacts'], spec['tokens'])):
        shape(contact, CONTACT_KEYS, 'contact')
        string, fret, finger = expected
        need(contact['kind'] == 'printed_fret_contact', 'UNSUPPORTED_KIND', 'Printed contact required')
        need(contact['ordinal'] == i+1 and contact['string_label'] == string and contact['fret'] == fret and contact['finger'] == finger,
             'CONTACT_ORDER_VALUE', f"{spec['ordinal']}:{i+1}")
        need(contact['midi'] == OPEN_MIDI[string]+fret and contact['string_low_to_high'] == LOW_STRINGS.index(string)+1,
             'CONTACT_PITCH', f"{spec['ordinal']}:{i+1}")
        need((contact['grid_column'], contact['source_line'], contact['source_column_1based'], contact['block_index']) ==
             (token[0], token[3], token[4], token[5]), 'CONTACT_SOURCE_TOKEN', str(i+1))
        onset, duration = source_quarter(contact['onset_q']), source_quarter(contact['duration_q'])
        need(onset == reduced(i, 4) and duration == [1, 4], 'METRIC_GRID', 'Selected straight-sixteenth source metric changed')
        need(contact['annotations'] == {} and contact['technique_symbols'] == '' and contact['same_column_contact_count'] == 1,
             'CONTACT_TECHNIQUE', 'Unreviewed articulation or simultaneous contact')
        events.append({'source_ordinal': i+1, 'string_label': string, 'string_low_to_high': LOW_STRINGS.index(string)+1,
                       'fret': fret, 'finger': finger, 'written_standard_tuning_midi': OPEN_MIDI[string]+fret,
                       'onset_q': onset, 'metric_duration_q': duration, 'acoustic_gate_q': None,
                       'attack': 'picked', 'source_token': {'txt_line': token[3], 'column_1based': token[4], 'block': token[5]}})
    variants = implementation['relative_variants']
    need(type(variants) is list and len(variants) == 2, 'VARIANT_COUNT', 'Exactly two start variants required')
    output_variants = []
    for variant, start in zip(variants, ('D', 'U')):
        shape(variant, VARIANT_KEYS, 'variant')
        expected_strokes = [start if i % 2 == 0 else ('U' if start == 'D' else 'D') for i in range(40)]
        need(variant['start_stroke'] == start and variant['contact_ordinals'] == list(range(1, 41)) and variant['strokes'] == expected_strokes,
             'VARIANT_ORDER', 'Start, membership or declared alternating continuation differs')
        need(source_quarter(variant['end_q']) == [10, 1], 'METRIC_EXTENT', 'Full selected traversal ends atq10')
        output_variants.append({'source_local_label': 'start-'+start, 'start_stroke': start,
                                'event_ordinals': list(range(1, 41)), 'declared_strokes': expected_strokes, 'end_q': [10, 1]})
    timing = record['timing_authority']
    need(timing['fixed_bpm'] is None and timing['ascii_spacing_is_duration'] is False and
         timing['selected_projection'] == 'straight_sixteenth' and timing['unselected_options'] == ['triplet', 'quintuplet'],
         'TIMING_AUTHORITY', 'Source option/BPM/ASCII timing assertion changed')
    need(source_quarter(timing['duration_q']) == [1, 4] and source_quarter(timing['end_q']) == [10, 1],
         'METRIC_EXTENT', 'Timing authority disagrees')
    need(review['package_key'] == spec['package_key'] and review['source_identity'] == spec['source_identity'] and
         review['packet_line'] == spec['ordinal'], 'REVIEW_IDENTITY', 'Review source binding differs')
    # Complete reviewed record equality also covers fields not projected by this adapter.
    need(sha(canonical(record)) == review['record_sha256_sorted_keys'], 'REVIEW_RECORD_SHA', 'Complete source record differs from independent review')
    return {'schema': 'fathom-private-level002-projection.1', 'status': 'NOT_ADMITTED',
            'package_key': spec['package_key'], 'source_identity': spec['source_identity'], 'level': 2,
            'set': spec['set'], 'source_exercise_ordinal': spec['ordinal'], 'printed_code': spec['code'],
            'source_refs': record['source_refs'], 'source_packet_line': spec['ordinal'],
            'source_record_sha256': review['record_sha256_sorted_keys'], 'review_sha256': PINS[REVIEW],
            'metric_unit': 'quarter', 'selected_projection': 'straight_sixteenth',
            'duration_semantics': 'metric_slot_not_acoustic_note_off', 'events': events, 'variants': output_variants,
            'policy_ref': 'source-policy.json', 'runtime_admitted': False, 'canonical_ids_allocated': False,
            'learner_performance_observed': False, 'credit_awarded': False}


def compile_projection(rows, review, original_txt, guidance):
    need(type(rows) is list and len(rows) == 108, 'RECORD_COUNT', 'Exactly108 source records required')
    keys = [row.get('package_key') if type(row) is dict else None for row in rows]
    need(all(type(key) is str for key in keys) and len(set(keys)) == 108, 'DUPLICATE_OR_MISSING_KEY', '108 unique source keys required')
    reviewed = review.get('records')
    need(type(reviewed) is list and len(reviewed) == 108, 'REVIEW_COVERAGE', '108 reviewed records required')
    need(len({row['package_key'] for row in reviewed}) == 108, 'REVIEW_COVERAGE', 'Duplicate reviewed key')
    validate_guidance(guidance)
    specs = expected_source(original_txt)
    records = [project_record(row, spec, checked) for row, spec, checked in zip(rows, specs, reviewed)]
    policy = {
        'schema': 'fathom-private-level002-policy.1', 'status': 'NOT_ADMITTED',
        'printed': {'tuning': 'standard', 'open_midi_low_to_high': [40, 45, 50, 55, 59, 64],
                    'fifth_position_finger_frets': {'1': 5, '2': 6, '3': 7, '4': 8}, 'start_strokes': ['D', 'U']},
        'selected_source_option': {'name': 'straight_sixteenth', 'duration_q': [1, 4], 'txt_lines': [10, 11]},
        'authored_reviewed_interpretation': {'name': 'continuous_alternating_pick.1', 'basis': 'bounded interpretation; source prints D/U starts, not each stroke',
                                            'reset_at_turn': False, 'review_sha256': PINS[REVIEW]},
        'unselected_rhythm_options': ['triplet', 'quintuplet'],
        'unspecified': {'fixed_bpm': None, 'meter': None, 'acoustic_sounding_gates': None, 'active_capo': None, 'performance_outcome': None},
        'source_guidance': {'pin': {'path': GUIDANCE, 'sha256': PINS[GUIDANCE]}, 'pdf_sha256': PINS[PDF], 'physical_page': 1,
                            'clauses': [{'key': key, 'text': value} for key, value in GUIDANCE_CLAUSES.items()],
                            'progression_unit': 'full12-exercise set; both pick starts; two separate clean days',
                            'automatic_credit': False, 'observed_clean_days': None},
        'source_local_labels_are_canonical_ids': False, 'runtime_admitted': False, 'credit_awarded': False,
    }
    return records, policy


def read_bounded(root, relative):
    path = root / relative
    need(path.is_file() and not any(p.is_symlink() for p in [path, *path.parents] if p != root.parent),
         'INPUT_PATH', relative)
    with path.open('rb') as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    need(len(data) <= MAX_FILE_BYTES, 'INPUT_SIZE', relative)
    return data


def load_inputs(root):
    raw = {path: verify_input_bytes(path, read_bounded(root, path)) for path in PINS}
    rows = [strict_json(line) for line in raw[PACKET].splitlines()]
    review, guidance = strict_json(raw[REVIEW]), strict_json(raw[GUIDANCE])
    records, policy = compile_projection(rows, review, raw[TXT].decode('utf-8'), guidance)
    provenance = [{'path': path, 'bytes': len(data), 'sha256': sha(data)} for path, data in sorted(raw.items())]
    code = read_bounded(root, SELF)
    provenance.append({'path': SELF, 'bytes': len(code), 'sha256': sha(code)})
    return records, policy, provenance


def export_bundle(root: Path, destination: Path):
    root = root.resolve(strict=True)
    try:
        git_root = Path(subprocess.check_output(['git', '-C', str(root), 'rev-parse', '--show-toplevel'], text=True).strip()).resolve()
    except subprocess.CalledProcessError as error:
        raise Refusal('ROOT', 'A verified Git root is required') from error
    need(root == git_root, 'ROOT', 'Use the repository root')
    allowed = root / 'Build' / BASE
    destination = destination if destination.is_absolute() else root / destination
    # Resolve only parents; never follow a preexisting destination symlink.
    need(not destination.exists() and not destination.is_symlink(), 'OUTPUT_EXISTS', str(destination))
    resolved = destination.parent.resolve(strict=True) / destination.name
    need(allowed.resolve() in resolved.parents, 'OUTPUT_SCOPE', 'Output must be inside this private Build root')
    need(all(not p.is_symlink() for p in [destination.parent, *destination.parent.parents]), 'OUTPUT_PATH', 'Symlink output parent refused')
    records, policy, inputs = load_inputs(root)
    files = {'records.jsonl': b''.join(canonical(record)+b'\n' for record in records),
             'source-policy.json': canonical(policy)+b'\n'}
    counts = {'records': len(records), 'contacts': sum(len(r['events']) for r in records),
              'variants': sum(len(r['variants']) for r in records),
              'variant_memberships': sum(len(v['event_ordinals']) for r in records for v in r['variants'])}
    need(counts == {'records': 108, 'contacts': 4320, 'variants': 216, 'variant_memberships': 8640}, 'OUTPUT_COUNTS', 'Finite coverage mismatch')
    manifest = {'schema': 'fathom-private-finite-export-manifest.1', 'status': 'NOT_ADMITTED', 'counts': counts,
                'inputs': inputs, 'files': [{'path': name, 'bytes': len(data), 'sha256': sha(data)} for name, data in sorted(files.items())],
                'manifest_self_excluded': True, 'canonical_ids_allocated': False, 'runtime_admitted': False, 'credit_awarded': False}
    files['manifest.json'] = canonical(manifest)+b'\n'
    # All input/semantic checks finish before any output directory exists. The manifest
    # is written last. On I/O failure, retain incomplete private output for diagnosis;
    # no caller may consume a directory lacking its verified final manifest.
    try:
        resolved.mkdir()
        for name, data in files.items():
            with (resolved / name).open('xb') as stream:
                stream.write(data)
    except FileExistsError as error:
        raise Refusal('OUTPUT_EXISTS', str(resolved)) from error
    except OSError as error:
        raise Refusal('OUTPUT_WRITE_INCOMPLETE', str(resolved)) from error
    return {'status': 'NOT_ADMITTED', 'output': str(resolved.relative_to(root)), 'counts': counts,
            'files': [{'path': name, 'bytes': len(data), 'sha256': sha(data)} for name, data in sorted(files.items())]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = export_bundle(args.root, args.output)
    except (Refusal, KeyError, TypeError, IndexError, OSError) as error:
        print(json.dumps({'status': 'REFUSED', 'code': getattr(error, 'code', 'INPUT_SHAPE_OR_IO'), 'detail': str(error)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
