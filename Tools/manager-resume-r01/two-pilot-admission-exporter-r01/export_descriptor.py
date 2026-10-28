#!/usr/bin/env python3
"""Finite private descriptors. No canonical writes, allocations or admission.

The expected authority digest is an EXTERNAL controller trust anchor. This tool
checks its declared union and live anchors, not the completeness of a census
outside that authority. Re-run under P02's serialization immediately before use.
"""
import argparse
import hashlib
import json
import os
import re
import tempfile
from fractions import Fraction
from pathlib import Path


CASE_ROOT = 'Build/manager-resume-r01/two-pilot-admission-exporter-r01'
CASES = {
    'l003-modeb001': '751dd9edb435b8ff496a3c66a1a45f426ca83b21fd498a6034ac1f11f0a93066',
    'l004-ex002': '7afe756d64bb9b8f14830463561f1c6166ffb345bce2b52871c1b1c7d2266b70',
}
COMPONENTS = {'registry', 'allocation', 'lineage', 'source_bindings', 'reservations'}
ANCHORS = {'installed_registry', 'allocation', 'lineage', 'source_bindings', 'reservations'}


class Refusal(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise Refusal(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'DUPLICATE_JSON_KEY: ' + key)
        result[key] = value
    return result


def decode(data):
    def bad_constant(value):
        raise Refusal('NONFINITE_JSON: ' + value)
    return json.loads(data, object_pairs_hook=unique_object, parse_constant=bad_constant)


class Reader:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        need((self.root / '.git').exists(), 'NOT_REPOSITORY_ROOT')
        self.refs = {}

    def path(self, rel):
        need(isinstance(rel, str) and rel != '' and '\\' not in rel, 'UNSAFE_PATH')
        need(not rel.startswith('/') and all(x not in ('', '.', '..') for x in rel.split('/')), 'UNSAFE_PATH')
        p = self.root
        for part in rel.split('/'):
            p = p / part
            need(not p.is_symlink(), 'SYMLINK_REFUSED: ' + rel)
        return p

    def read(self, ref):
        need(isinstance(ref, dict) and {'path', 'bytes', 'sha256'} <= set(ref), 'INVALID_REFERENCE')
        raw = self.path(ref['path']).read_bytes()
        need(type(ref['bytes']) is int and len(raw) == ref['bytes'] and digest(raw) == ref['sha256'], 'REFERENCE_DRIFT: ' + ref['path'])
        clean = {k: ref[k] for k in ('path', 'bytes', 'sha256')}
        need(ref['path'] not in self.refs or self.refs[ref['path']] == clean, 'CONFLICTING_REFERENCE')
        self.refs[ref['path']] = clean
        return raw

    def recheck(self):
        for ref in list(self.refs.values()):
            self.read(ref)


def one(rows, field, value, reason):
    found = [r for r in rows if r.get(field) == value]
    need(len(found) == 1, reason)
    return found[0]


def load_case(reader, case):
    need(case in CASES, 'UNSUPPORTED_CASE: prototype ModeA001 and Level4 Exercise001/historical64 require separate decisions')
    path = CASE_ROOT + '/' + case + '-input.json'
    raw = reader.path(path).read_bytes()
    need(digest(raw) == CASES[case], 'CASE_INPUT_DRIFT')
    spec = decode(reader.read({'path': path, 'bytes': len(raw), 'sha256': CASES[case]}))
    need(spec['schema'] == 'fathom-two-pilot-case-input.1' and spec['case'] == case, 'CASE_SCHEMA')
    for ref in spec['adoptions'] + spec['source_refs']:
        reader.read(ref)
    policy = decode(reader.read(spec['policy']))
    plan = [decode(line) for line in reader.read(spec['identity_plan']).splitlines()]
    binding = one(plan, 'source_identity', spec['source_identity'], 'IDENTITY_PLAN_MAPPING')
    need(binding['inspected_record_sha256'] == spec['canonical_record_sha256'], 'IDENTITY_PLAN_RECORD')
    need(binding['selected_existing_variants'] == spec['selected_variants'], 'IDENTITY_PLAN_SELECTION')
    exports = reader.read(spec['export']).splitlines()
    source = decode(exports[spec['export_line'] - 1])
    need(digest(canonical(source)) == spec['export_record_sha256'], 'EXPORT_RECORD_DRIFT')
    need(source['source_identity'] == spec['source_identity'] and source['package_key'] == spec['package_key'], 'SOURCE_IDENTITY')
    need(source['source_refs'] == spec['source_refs'], 'SOURCE_REFS')
    record = one(decode(reader.read(spec['canonical_package']))['records'], 'id', spec['item'], 'CANONICAL_CASE')
    need(digest(canonical(record)) == spec['canonical_record_sha256'], 'CANONICAL_RECORD_DRIFT')
    for key, expected in [('module_id', spec['module']), ('workbook_id', spec['workbook']), ('legacy_level', spec['level']), ('content_revision', spec['revision']), ('lineage', spec['lineage'])]:
        need(record[key] == expected, 'CANONICAL_' + key)
    original_allocation = decode(reader.read(spec['historical_allocation_ref']))['records'][spec['item']]
    need(original_allocation == spec['historical_allocation'], 'ORIGINAL_ALLOCATION')
    events = record['events']
    event_ids = [e['event_id'] for e in events]
    need(event_ids == spec['event_ids'] and len(set(event_ids)) == len(event_ids), 'EVENT_SET')
    need(len(source['events']) == len(events) == (40 if case == 'l003-modeb001' else 32), 'CONTACT_COUNT')
    for index, (event, origin) in enumerate(zip(events, source['events'])):
        need(event['kind'] == 'note' and event['attack'] == origin['attack'] == 'picked', 'EVENT_ATTACK')
        for target, src in [('string', 'string_low_to_high'), ('fret', 'fret'), ('finger', 'finger'), ('midi', 'written_standard_tuning_midi')]:
            need(event[target] == origin[src], 'SOURCE_CONTACT_' + target)
        q = Fraction(index, 4)
        need(origin['source_ordinal'] == index + 1 and origin['onset_q'] == [q.numerator, q.denominator] and origin['metric_duration_q'] == [1, 4], 'METRIC_PROJECTION')
        need(origin['acoustic_gate_q'] is None and event['onset_q'] is None and event['duration_q'] is None, 'UNKNOWN_ACOUSTIC_OR_CANONICAL_TIMING')
    variants = record['variants']
    need(sorted(v['id'] for v in variants) == spec['retained_variant_ids'] and len(variants) == 12, 'RETAINED_VARIANTS')
    for variant in variants:
        need(variant['event_ids'] == event_ids, 'COMPLETE_VARIANT_MEMBERSHIP')
    need([v['start'] for v in spec['selected_variants']] == ['D', 'U'], 'SELECTED_START_ORDER')
    for selected, start in zip(spec['selected_variants'], ['D', 'U']):
        v = one(variants, 'id', selected['id'], 'SELECTED_VARIANT')
        need(digest(canonical(v)) == selected['canonical_sha256'], 'SELECTED_VARIANT_DIGEST')
        need(v['pick_start'] == start and v['accent_policy'] == 'even' and v['grouping']['kind'] == 'even_subdivision' and v['grouping']['notes_per_beat'] == 4 and v['grouping']['beat_unit_q'] == [1, 1], 'SELECTED_GROUPING')
        sv = one(source['variants'], 'start_stroke', start, 'SOURCE_SELECTED_START')
        need(sv['event_ordinals'] == list(range(1, len(events) + 1)), 'SOURCE_MEMBERSHIP')
        need(sv['declared_strokes'] == [start if i % 2 == 0 else ('U' if start == 'D' else 'D') for i in range(len(events))], 'SOURCE_PICK_PARITY')
        need(sv['end_q'] == [len(events) // 4, 1], 'SOURCE_ENDPOINT')
    return spec, record, source, policy


def validate_union(reader, spec, authority_path, expected_digest, synthetic=False):
    need(authority_path and expected_digest, 'CURRENT_GLOBAL_UNION_REQUIRED')
    raw = reader.path(authority_path).read_bytes()
    need(digest(raw) == expected_digest, 'AUTHORITY_DIGEST_STALE')
    authority_ref = {'path': authority_path, 'bytes': len(raw), 'sha256': expected_digest}
    auth = decode(reader.read(authority_ref))
    need(auth.get('schema') == 'fathom-controller-current-union-authority.1', 'NOT_CURRENT_UNION_AUTHORITY')
    expected_class = 'TEST_FIXTURE' if synthetic else 'CONTROLLER_CURRENT_GLOBAL'
    need(auth.get('classification') == expected_class, 'AUTHORITY_CLASSIFICATION')
    need(isinstance(auth.get('generation'), str) and auth['generation'], 'AUTHORITY_GENERATION')
    coverage = auth.get('coverage', {})
    need(isinstance(coverage, dict) and set(coverage) == {'all_current_components', 'all_held_and_permanent_reservations'} and all(value is True for value in coverage.values()), 'CONTROLLER_CLOSURE_REQUIRED')
    anchors = auth.get('live_anchors', [])
    need(len(anchors) == 5 and {a['role'] for a in anchors} == ANCHORS, 'LIVE_ANCHOR_CENSUS')
    need(len({a['ref']['path'] for a in anchors}) == len(anchors), 'DUPLICATE_LIVE_ANCHOR')
    for anchor in anchors:
        reader.read(anchor['ref'])
    need(auth.get('evidence'), 'CONTROLLER_EVIDENCE_REQUIRED')
    for ref in auth['evidence']:
        reader.read(ref)
    union = decode(reader.read(auth['union']))
    need(union.get('schema') == 'fathom-cumulative-identity-union.1' and union.get('generation') == auth['generation'] and union.get('classification') == expected_class, 'UNION_GENERATION_OR_CLASS')
    need(set(union.get('components', {})) == COMPONENTS, 'UNION_COMPONENTS')
    parts = {key: decode(reader.read(ref)) for key, ref in union['components'].items()}
    entities = parts['registry']['entities']
    ids = [e['id'] for e in entities]
    need(len(set(ids)) == len(ids), 'DUPLICATE_REGISTRY_ID')
    entity = {e['id']: e for e in entities}
    parent_kinds = {'course': None, 'workbook': 'course', 'module': 'workbook', 'item': 'module', 'variant': 'item'}
    for ent in entities:
        need(ent['parent'] is None or ent['parent'] in entity, 'DANGLING_REGISTRY_PARENT')
        need(ent['kind'] in parent_kinds, 'UNKNOWN_REGISTRY_KIND')
        expected_parent_kind = parent_kinds[ent['kind']]
        need((ent['parent'] is None) if expected_parent_kind is None else (ent['parent'] is not None and entity[ent['parent']]['kind'] == expected_parent_kind), 'REGISTRY_PARENT_KIND')
    allocations, lineage = parts['allocation']['records'], parts['lineage']['records']
    need(set(allocations) == set(lineage), 'INCOMPLETE_CUMULATIVE_LINEAGE')
    # A new closure must preserve the complete known baseline, not just this
    # pilot. Later additions are supplied by the controller's cumulative census.
    baseline = decode(reader.read(spec['historical_allocation_ref']))['records']
    for item, previous in baseline.items():
        need(item in allocations, 'PRIOR_ALLOCATION_MISSING')
        for field in ('occurrences', 'variants'):
            for key, value in previous[field].items():
                need(allocations[item][field].get(key) == value, 'PRIOR_ALLOCATION_REMAPPED')
    owned = {}
    for item, allocation in allocations.items():
        need(item in entity and entity[item]['kind'] == 'item', 'MISSING_ALLOCATED_ITEM')
        head = lineage[item]
        need(type(head.get('content_revision')) is int and head['content_revision'] >= 1 and isinstance(head.get('record_sha256'), str) and len(head['record_sha256']) == 64 and all(c in '0123456789abcdef' for c in head['record_sha256']), 'INVALID_LINEAGE_HEAD')
        for field in ('occurrences', 'variants'):
            values = list(allocation[field].values())
            need(len(values) == len(set(values)), 'DUPLICATE_ALLOCATION_VALUE')
            for value in values:
                need(value not in owned, 'GLOBAL_ALLOCATION_COLLISION')
                owned[value] = item
                if field == 'occurrences':
                    need(value.startswith(item + ':event:'), 'REMAPPED_OCCURRENCE_OWNER')
                else:
                    need(value in entity and entity[value]['kind'] == 'variant' and entity[value]['parent'] == item, 'VARIANT_ANCESTRY')
    expected_lineage = {'content_revision': spec['revision'], 'record_sha256': spec['canonical_record_sha256']}
    need(lineage.get(spec['item']) == expected_lineage, 'STALE_CURRENT_PREDECESSOR')
    need(allocations.get(spec['item']) == spec['historical_allocation'], 'CURRENT_ALLOCATION_CHANGED')
    for ident, kind, parent in [(spec['item'], 'item', spec['module']), (spec['module'], 'module', spec['workbook'])]:
        need(ident in entity and entity[ident]['kind'] == kind and entity[ident]['parent'] == parent, 'CURRENT_CASE_ANCESTRY')
    need(spec['workbook'] in entity and entity[spec['workbook']]['kind'] == 'workbook', 'CURRENT_WORKBOOK')
    rows = parts['source_bindings']['entries']
    sources = [r['source_identity'] for r in rows]
    need(len(set(sources)) == len(sources), 'DUPLICATE_SOURCE_BINDING')
    for row in rows:
        need(row['item'] in allocations and row['record_sha256'] == lineage[row['item']]['record_sha256'], 'STALE_SOURCE_BINDING')
    selected_binding = one(rows, 'source_identity', spec['source_identity'], 'CURRENT_SOURCE_BINDING_MISSING')
    need(selected_binding['item'] == spec['item'], 'SOURCE_ITEM_REMAP')
    need([r['source_identity'] for r in rows if r['item'] == spec['item']] == [spec['source_identity']], 'CONFLICTING_SOURCE_ITEM')
    reservations = parts['reservations']['entries']
    need(len({r['reservation_id'] for r in reservations}) == len(reservations), 'DUPLICATE_RESERVATION')
    selected_ids = {spec['item'], spec['module'], *spec['event_ids'], *spec['retained_variant_ids']}
    claims = {}
    for reservation in reservations:
        need(reservation['status'] in ('HELD', 'PERMANENT'), 'RESERVATION_STATUS')
        need(isinstance(reservation['source_identity'], str) and reservation['source_identity'], 'RESERVATION_SOURCE')
        claimed = reservation['ids']
        need(isinstance(claimed, list) and all(isinstance(ident, str) and re.fullmatch(r'fg:(?:(?:item|module|variant):[0-9]{6}|item:[0-9]{6}:event:[0-9]{4})', ident) for ident in claimed), 'RESERVATION_ID_FORMAT')
        need(claimed and len(set(claimed)) == len(claimed), 'RESERVATION_IDS')
        for ident in claimed:
            need(ident not in claims or claims[ident] == reservation['source_identity'], 'CONFLICTING_RESERVATION')
            claims[ident] = reservation['source_identity']
            allocated_item = owned.get(ident, ident if ident in allocations else None)
            allocated_items = {allocated_item} if allocated_item is not None else {item for item in allocations if entity[item]['parent'] == ident}
            if allocated_items:
                owner_sources = {r['source_identity'] for r in rows if r['item'] in allocated_items}
                need(owner_sources == {reservation['source_identity']}, 'ALLOCATED_RESERVATION_OWNER_CONFLICT')
        if selected_ids.intersection(claimed):
            need(reservation['source_identity'] == spec['source_identity'], 'CASE_RESERVATION_COLLISION')
            need(set(claimed) <= selected_ids, 'CASE_RESERVATION_SCOPE_CHANGED')
    return {'authority': authority_ref, 'union': auth['union'], 'generation': auth['generation'],
            'classification': expected_class, 'byte_and_identity_checks': 'PASS',
            'census_completeness': 'externally asserted by pinned controller authority',
            'rerun_under_p02_serialization_at_use': True, 'native_or_admission_authority': False}


def export(root, case, output, *, draft=False, authority=None, authority_sha256=None, synthetic=False):
    reader = Reader(root)
    need(not (draft and (authority or authority_sha256 or synthetic)), 'DRAFT_CANNOT_CARRY_AUTHORITY')
    spec, record, source, policy = load_case(reader, case)
    closure = None if draft else validate_union(reader, spec, authority, authority_sha256, synthetic)
    selected = spec['selected_variants']
    descriptor = {
        'schema': 'fathom-finite-admission-descriptor.1', 'case': case,
        'status': 'DRAFT_CURRENT_UNION_REQUIRED' if draft else ('SYNTHETIC_GUARD_PASS_NOT_ADMITTED' if synthetic else 'CURRENT_UNION_GUARD_PASS_NOT_ADMITTED'),
        'source_identity': spec['source_identity'], 'package_key': spec['package_key'],
        'item': spec['item'], 'module': spec['module'], 'workbook': spec['workbook'],
        'canonical_revision': spec['revision'], 'canonical_lineage': spec['lineage'],
        'canonical_record_sha256': spec['canonical_record_sha256'],
        'canonical_package_ref': spec['canonical_package'],
        'retained_event_ids': spec['event_ids'], 'retained_present_variant_ids': spec['retained_variant_ids'],
        'selected_runtime_variant_ids': [v['id'] for v in selected], 'selected_variants': selected,
        'retained_memberships': sum(len(v['event_ids']) for v in record['variants']),
        'selected_memberships': len(spec['event_ids']) * 2,
        'existing_allocation': spec['historical_allocation'],
        'selected_pass': source['selected_pass'], 'metric_unit': 'quarter',
        'metric_slot_q': [1, 4], 'metric_end_q': source['variants'][0]['end_q'],
        'events': [dict(origin, existing_event_id=event['event_id']) for origin, event in zip(source['events'], record['events'])],
        'source_export_ref': spec['export'], 'source_export_line': spec['export_line'],
        'source_export_record_sha256': spec['export_record_sha256'],
        'source_policy_ref': spec['policy'], 'required_source_context': policy,
        'unselected_first_pass': source['unselected_first_pass'],
        'selected_source_variants': source['variants'], 'source_refs': spec['source_refs'],
        'identity_adoptions': spec['adoptions'], 'current_identity_closure': closure,
        'catalog_consumer_requirement': 'explicit complete present-variant set; selected runtime permission only for the two named IDs; preserve canonical bytes',
        'new_ids': 0, 'native_validated': False, 'runtime_admitted': False,
        'queue_reserved': False, 'installed': False, 'learner_performance_observed': False,
        'credit_awarded': False, 'fixed_bpm': None, 'acoustic_gate_q': None,
        'input_refs': sorted(reader.refs.values(), key=lambda r: r['path']),
    }
    out = reader.path(output)
    need(output.startswith('Build/') and output.endswith('.json'), 'OUTPUT_MUST_BE_NEW_BUILD_JSON')
    need(not out.exists() and output not in reader.refs, 'OUTPUT_EXISTS_OR_IS_INPUT')
    data = json.dumps(descriptor, sort_keys=True, indent=2, ensure_ascii=False).encode() + b'\n'
    out.parent.mkdir(parents=True, exist_ok=True)
    reader.path(output)
    # Publish one complete file without overwrite. Any validation or I/O failure
    # before the exclusive link leaves no descriptor or staging file behind.
    staging = None
    try:
        with tempfile.NamedTemporaryFile(dir=out.parent, prefix='.descriptor-', delete=False) as stream:
            staging = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        reader.recheck()
        os.link(staging, out)
    finally:
        if staging is not None:
            staging.unlink(missing_ok=True)
    return descriptor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--case', required=True)
    parser.add_argument('--output', required=True, help='new checkout-relative Build/*.json')
    parser.add_argument('--draft', action='store_true')
    parser.add_argument('--authority', help='controller-pinned current-union authority, checkout-relative')
    parser.add_argument('--authority-sha256', help='expected digest supplied independently by the controller')
    parser.add_argument('--synthetic', action='store_true', help='TEST_FIXTURE closures only; never live qualification')
    args = parser.parse_args()
    try:
        result = export(args.root, args.case, args.output, draft=args.draft, authority=args.authority, authority_sha256=args.authority_sha256, synthetic=args.synthetic)
    except (Refusal, OSError, KeyError, TypeError, IndexError, json.JSONDecodeError) as exc:
        parser.exit(2, 'REFUSED: ' + str(exc) + '\n')
    print(json.dumps({'case': result['case'], 'status': result['status'], 'output': args.output, 'new_ids': 0, 'runtime_admitted': False}))


if __name__ == '__main__':
    main()
