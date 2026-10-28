"""Causal identity-guard tests; all current closures here are TEST_FIXTURE."""
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'Build/manager-resume-r01/two-pilot-admission-exporter-r02'
TOOL = ROOT / 'Tools/manager-resume-r01/two-pilot-admission-exporter-r02/export_descriptor.py'
module_spec = importlib.util.spec_from_file_location('finite_exporter', TOOL)
ex = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(ex)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ref(path):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw)}


def write(path, data):
    path.write_text(json.dumps(data, sort_keys=True, indent=2) + '\n')
    return ref(path)


def fixture(directory):
    prefix = ROOT / 'Results/primary/20260912T204759Z-2.3.1.1.1-r14-evidence'
    parts = {
        'registry': json.loads((prefix / 'allocation01/cumulative-registry.json').read_text()),
        'allocation': json.loads((prefix / 'allocation01/cumulative-allocation.json').read_text()),
        'lineage': json.loads((prefix / 'handoff01/lineage-baseline.json').read_text()),
        'source_bindings': {'entries': []}, 'reservations': {'entries': []},
    }
    for case in ex.CASES:
        spec = json.loads((BASE / (case + '-input.json')).read_text())
        parts['source_bindings']['entries'].append({'source_identity': spec['source_identity'], 'item': spec['item'], 'record_sha256': spec['canonical_record_sha256']})
    union = {'schema': 'fathom-cumulative-identity-union.1', 'classification': 'TEST_FIXTURE', 'generation': 'synthetic-001', 'components': {key: write(directory / (key + '.json'), value) for key, value in parts.items()}}
    auth = {'schema': 'fathom-controller-current-union-authority.1', 'classification': 'TEST_FIXTURE', 'generation': 'synthetic-001', 'union': write(directory / 'union.json', union),
            'coverage': {'all_current_components': True, 'all_held_and_permanent_reservations': True},
            'evidence': [write(directory / 'fixture-evidence.json', {'classification': 'TEST_FIXTURE', 'live_current_state_proved': False})],
            'live_anchors': [{'role': role, 'ref': write(directory / ('anchor-' + role + '.json'), {'role': role, 'classification': 'TEST_FIXTURE', 'generation': 'synthetic-001'})} for role in sorted(ex.ANCHORS)]}
    return parts, union, auth


def seal_fixture(directory, parts, union, auth):
    for key, value in parts.items():
        union['components'][key] = write(directory / (key + '.json'), value)
    auth['union'] = write(directory / 'union.json', union)
    return write(directory / 'authority.json', auth)


def main(work_dir, report_path):
    start = time.monotonic()
    checks = 0
    refusals = []
    positives = []
    def check(condition, why):
        nonlocal checks
        checks += 1
        if not condition:
            raise AssertionError(why)
    def refused(name, fn, out, contains=None):
        try:
            fn()
        except (ex.Refusal, OSError, KeyError, TypeError, ValueError) as error:
            check(contains is None or contains in str(error), name + ': wrong refusal ' + str(error))
            check(not out.exists(), name + ': published output')
            check(not list(out.parent.glob('.descriptor-*')), name + ': leaked staging')
            refusals.append({'name': name, 'error': str(error), 'no_output_or_staging': True})
        else:
            raise AssertionError(name + ': unexpected acceptance')
    def args(directory, authority, case='l003-modeb001', name='out'):
        return {'root': ROOT, 'case': case, 'output': str((directory / (name + '.json')).relative_to(ROOT)), 'authority': authority['path'], 'authority_sha256': authority['sha256'], 'synthetic': True}
    work_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='guard-tests-', dir=work_dir) as tmp:
        directory = Path(tmp)
        parts, union, auth = fixture(directory)
        authority = seal_fixture(directory, parts, union, auth)
        for case, item, variants, count, endpoint in [('l003-modeb001', 'fg:item:000240', ['fg:variant:000827', 'fg:variant:000829'], 40, 10), ('l004-ex002', 'fg:item:000445', ['fg:variant:003287', 'fg:variant:003289'], 32, 8)]:
            first = ex.export(**args(directory, authority, case, case))
            second = ex.export(**args(directory, authority, case, case + '-repeat'))
            check(first == second, 'Determinism')
            check(first['item'] == item and first['selected_runtime_variant_ids'] == variants, 'Exact finite selection')
            check(first['status'] == 'SYNTHETIC_GUARD_PASS_NOT_ADMITTED', 'Synthetic boundary')
            check(len(first['retained_present_variant_ids']) == 12 and first['retained_memberships'] == count * 12 and first['selected_memberships'] == count * 2, 'All memberships')
            check(first['metric_end_q'] == [endpoint, 1] and first['metric_slot_q'] == [1, 4], 'Metric facts')
            for field in ['native_validated', 'runtime_admitted', 'queue_reserved', 'installed', 'learner_performance_observed', 'credit_awarded']:
                check(first[field] is False, field)
            for i, event in enumerate(first['events'], 1):
                check(event['existing_event_id'] == item + ':event:' + str(i).zfill(4), 'Event identity')
                check(event['acoustic_gate_q'] is None, 'Unknown acoustic gate')
            positives.append({'case': case, 'sha256': sha((directory / (case + '.json')).read_bytes()), 'events': count, 'retained_variants': 12, 'selected_variants': variants, 'status': first['status']})
        out = directory / 'refused.json'
        plain = args(directory, authority)
        plain['output'] = str(out.relative_to(ROOT))
        for name, changes, expected in [
            ('missing-current-union', {'authority': None, 'authority_sha256': None}, 'CURRENT_GLOBAL_UNION_REQUIRED'),
            ('wrong-authority-pin', {'authority_sha256': '0' * 64}, 'AUTHORITY_DIGEST_STALE'),
            ('synthetic-as-live', {'synthetic': False}, 'AUTHORITY_CLASSIFICATION'),
            ('mode-a-prototype', {'case': 'l003-modea001'}, 'UNSUPPORTED_CASE'),
            ('level4-exercise001', {'case': 'l004-ex001'}, 'UNSUPPORTED_CASE'),
            ('historical64-pilot', {'case': 'fg:item:004901'}, 'UNSUPPORTED_CASE'),
            ('cross-case-alias', {'case': 'l003-modeb002'}, 'UNSUPPORTED_CASE'),
            ('draft-with-authority', {'draft': True}, 'DRAFT_CANNOT_CARRY_AUTHORITY'),
        ]:
            refused(name, lambda c=changes: ex.export(**dict(plain, **c)), out, expected)
        historical = ref(ROOT / 'Results/primary/20260912T204759Z-2.3.1.1.1-r14-evidence/handoff01/identity-head.json')
        refused('historical-head-not-current', lambda: ex.export(**dict(plain, authority=historical['path'], authority_sha256=historical['sha256'])), out, 'NOT_CURRENT_UNION_AUTHORITY')
        mutations = [
            ('later-selected-revision', lambda p,u,a: p['lineage']['records']['fg:item:000240'].update(content_revision=2), 'STALE_CURRENT_PREDECESSOR'),
            ('changed-selected-record', lambda p,u,a: p['lineage']['records']['fg:item:000240'].update(record_sha256='1'*64), 'STALE_CURRENT_PREDECESSOR'),
            ('lost-unselected-retained-variant', lambda p,u,a: p['allocation']['records']['fg:item:000240']['variants'].pop('triplets-up_and_down-D-even'), 'PRIOR_ALLOCATION_REMAPPED'),
            ('remapped-occurrence', lambda p,u,a: p['allocation']['records']['fg:item:000240']['occurrences'].update({'ascending:1':'fg:item:000240:event:9999'}), 'PRIOR_ALLOCATION_REMAPPED'),
            ('unrelated-prior-allocation-lost', lambda p,u,a: (p['allocation']['records'].pop('fg:item:000445'), p['lineage']['records'].pop('fg:item:000445')), 'CUMULATIVE_ITEM_SET'),
            ('review-unrelated-item-reparent', lambda p,u,a: next(e for e in p['registry']['entities'] if e['id']=='fg:item:000445').update(parent='fg:module:000240'), 'PRIOR_REGISTRY_REMAPPED'),
            ('review-unrelated-module-reparent', lambda p,u,a: next(e for e in p['registry']['entities'] if e['id']=='fg:module:000445').update(parent='fg:workbook:000003'), 'PRIOR_REGISTRY_REMAPPED'),
            ('review-registry-only-item', lambda p,u,a: p['registry']['entities'].append({'id':'fg:item:999999','kind':'item','parent':'fg:module:000445','label':'TEST_FIXTURE'}), 'CUMULATIVE_ITEM_SET'),
            ('registry-only-orphan-variant', lambda p,u,a: p['registry']['entities'].append({'id':'fg:variant:999999','kind':'variant','parent':'fg:item:000445','label':'TEST_FIXTURE'}), 'CUMULATIVE_VARIANT_REVERSE_COVERAGE'),
            ('unrelated-prior-variant-remapped', lambda p,u,a: p['allocation']['records']['fg:item:000445']['variants'].update({'triplets-up_and_down-D-even':'fg:variant:999999'}), 'PRIOR_ALLOCATION_REMAPPED'),
            ('extra-selected-variant', lambda p,u,a: p['allocation']['records']['fg:item:000240']['variants'].update({'invented':'fg:variant:000827'}), 'DUPLICATE_ALLOCATION_VALUE'),
            ('duplicate-registry-id', lambda p,u,a: p['registry']['entities'].append(copy.deepcopy(p['registry']['entities'][0])), 'DUPLICATE_REGISTRY_ID'),
            ('orphan-entity', lambda p,u,a: p['registry']['entities'][0].update(parent='fg:course:999999'), 'DANGLING_REGISTRY_PARENT'),
            ('wrong-parent-kind', lambda p,u,a: next(e for e in p['registry']['entities'] if e['id']=='fg:workbook:000004').update(parent='fg:item:000445'), 'REGISTRY_PARENT_KIND'),
            ('missing-cumulative-lineage', lambda p,u,a: p['lineage']['records'].pop('fg:item:000445'), 'INCOMPLETE_CUMULATIVE_LINEAGE'),
            ('invalid-unrelated-lineage', lambda p,u,a: p['lineage']['records']['fg:item:000445'].update(content_revision=True), 'INVALID_LINEAGE_HEAD'),
            ('missing-case-source-binding', lambda p,u,a: p['source_bindings']['entries'].pop(0), 'CURRENT_SOURCE_BINDING_MISSING'),
            ('duplicate-source-binding', lambda p,u,a: p['source_bindings']['entries'].append(copy.deepcopy(p['source_bindings']['entries'][0])), 'DUPLICATE_SOURCE_BINDING'),
            ('stale-source-record', lambda p,u,a: p['source_bindings']['entries'][0].update(record_sha256='2'*64), 'STALE_SOURCE_BINDING'),
            ('wrong-case-source-item', lambda p,u,a: p['source_bindings']['entries'][0].update(item='fg:item:000445',record_sha256=p['lineage']['records']['fg:item:000445']['record_sha256']), 'SOURCE_ITEM_REMAP'),
            ('retained-unselected-reservation-collision', lambda p,u,a: p['reservations']['entries'].append({'reservation_id':'held-1','status':'HELD','source_identity':'different-source','ids':['fg:variant:000826']}), 'ALLOCATED_RESERVATION_OWNER_CONFLICT'),
            ('unrelated-permanent-reservation-collision', lambda p,u,a: p['reservations']['entries'].append({'reservation_id':'held-2','status':'PERMANENT','source_identity':'different-source','ids':['fg:variant:003286']}), 'ALLOCATED_RESERVATION_OWNER_CONFLICT'),
            ('unrelated-module-reservation-collision', lambda p,u,a: p['reservations']['entries'].append({'reservation_id':'held-module','status':'HELD','source_identity':'different-source','ids':['fg:module:000445']}), 'ALLOCATED_RESERVATION_OWNER_CONFLICT'),
            ('same-owner-expanded-reservation', lambda p,u,a: p['reservations']['entries'].append({'reservation_id':'held-3','status':'HELD','source_identity':p['source_bindings']['entries'][0]['source_identity'],'ids':['fg:item:000240','fg:variant:999999']}), 'CASE_RESERVATION_SCOPE_CHANGED'),
            ('invalid-reservation-status', lambda p,u,a: p['reservations']['entries'].append({'reservation_id':'held-4','status':'FREE','source_identity':'other','ids':['fg:item:999999']}), 'RESERVATION_STATUS'),
            ('malformed-reservation-id', lambda p,u,a: p['reservations']['entries'].append({'reservation_id':'held-bad','status':'HELD','source_identity':'other','ids':[123]}), 'RESERVATION_ID_FORMAT'),
            ('integer-not-closure-boolean', lambda p,u,a: a['coverage'].update(all_current_components=1), 'CONTROLLER_CLOSURE_REQUIRED'),
            ('missing-current-components', lambda p,u,a: a['coverage'].update(all_current_components=False), 'CONTROLLER_CLOSURE_REQUIRED'),
            ('missing-reservation-census', lambda p,u,a: a['coverage'].update(all_held_and_permanent_reservations=False), 'CONTROLLER_CLOSURE_REQUIRED'),
            ('missing-live-anchor', lambda p,u,a: a['live_anchors'].pop(), 'LIVE_ANCHOR_CENSUS'),
            ('duplicate-live-anchor-path', lambda p,u,a: a['live_anchors'][1].update(ref=a['live_anchors'][0]['ref']), 'DUPLICATE_LIVE_ANCHOR'),
            ('missing-controller-evidence', lambda p,u,a: a.update(evidence=[]), 'CONTROLLER_EVIDENCE_REQUIRED'),
            ('wrong-union-generation', lambda p,u,a: u.update(generation='old-generation'), 'UNION_GENERATION_OR_CLASS'),
        ]
        for name, mutate, expected in mutations:
            p,u,a = copy.deepcopy((parts,union,auth))
            mutate(p,u,a)
            reference = seal_fixture(directory,p,u,a)
            current = dict(plain, authority=reference['path'], authority_sha256=reference['sha256'])
            refused(name, lambda c=current: ex.export(**c), out, expected)
        authority = seal_fixture(directory, parts, union, auth)
        plain.update(authority=authority['path'],authority_sha256=authority['sha256'])
        (directory / 'union.json').write_text('{}')
        refused('union-bytes-drift', lambda: ex.export(**plain), out, 'REFERENCE_DRIFT')
        authority = seal_fixture(directory, parts, union, auth)
        plain.update(authority=authority['path'],authority_sha256=authority['sha256'])
        anchor = ROOT / auth['live_anchors'][0]['ref']['path']
        old = anchor.read_bytes()
        anchor.write_bytes(b'changed live state')
        refused('live-anchor-stale', lambda: ex.export(**plain), out, 'REFERENCE_DRIFT')
        anchor.write_bytes(old)
        authority = seal_fixture(directory, parts, union, auth)
        raw = (directory / 'authority.json').read_text().replace('"generation": "synthetic-001",', '"generation": "synthetic-001", "generation": "synthetic-001",')
        (directory / 'authority.json').write_text(raw)
        duplicate = ref(directory / 'authority.json')
        refused('duplicate-json-key', lambda: ex.export(**dict(plain,authority_sha256=duplicate['sha256'])), out, 'DUPLICATE_JSON_KEY')
        authority = seal_fixture(directory, parts, union, auth)
        plain.update(authority=authority['path'],authority_sha256=authority['sha256'])
        original_recheck = ex.Reader.recheck
        def late_drift(reader):
            anchor.write_bytes(b'late changed live state')
            original_recheck(reader)
        ex.Reader.recheck = late_drift
        try:
            refused('late-drift-before-publication', lambda: ex.export(**plain), out, 'REFERENCE_DRIFT')
        finally:
            ex.Reader.recheck = original_recheck
            anchor.write_bytes(old)
        for name, target in [('path-traversal', 'Build/../bad.json'), ('shared-output', 'Content/bad.json')]:
            refused(name, lambda t=target: ex.export(**dict(plain,output=t)), out, 'PATH' if name == 'path-traversal' else 'OUTPUT_MUST')
        (directory / 'symbolic').symlink_to(directory, target_is_directory=True)
        refused('symlink-output', lambda: ex.export(**dict(plain,output=str((directory/'symbolic/out.json').relative_to(ROOT)))), out, 'SYMLINK')
        existing = directory / 'existing.json'
        existing.write_bytes(b'preserve me')
        try:
            ex.export(**dict(plain,output=str(existing.relative_to(ROOT))))
        except ex.Refusal as error:
            check('OUTPUT_EXISTS' in str(error) and existing.read_bytes()==b'preserve me', 'Existing output retained')
            refusals.append({'name':'existing-output','error':str(error),'existing_bytes_preserved':True})
        else:
            raise AssertionError('Output overwrite accepted')
        command = [sys.executable, '-B', str(TOOL), '--root', str(ROOT), '--case', 'l003-modeb001', '--output', str(out.relative_to(ROOT))]
        result = subprocess.run(command, capture_output=True, text=True)
        check(result.returncode == 2 and 'CURRENT_GLOBAL_UNION_REQUIRED' in result.stderr and not out.exists(), 'CLI missing union refusal')
        refusals.append({'name':'cli-missing-union','exit_code':result.returncode,'error':result.stderr.strip(),'no_output':True})
    report = {'schema':'fathom-two-pilot-exporter-tests.1','status':'PASS','checks':checks,'positives':positives,'causal_refusals':refusals,'refusal_count':len(refusals),'classification':'TEST_FIXTURE_ONLY','current_live_global_union_proved':False,'native_runs':0,'elapsed_seconds':time.monotonic()-start,'tool':ref(TOOL)}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['positives','causal_refusals']}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    cli=parser.parse_args()
    main(cli.work_dir.resolve(), cli.report.resolve())
