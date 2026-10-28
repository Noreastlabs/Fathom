#!/usr/bin/env python3
"""Build private partial components, conserving ambiguous facts without a winner."""
import argparse
import collections
import hashlib
import json
import pathlib
from observe import ROOT, CLASS, canonical


def head_candidate(alternatives):
    nodes = {}
    parents = {}
    for alt in alternatives:
        v = alt['value']
        n = (v['content_revision'], v['record_sha256'])
        nodes[n] = True
        lineage = v.get('lineage') or {}
        if lineage.get('kind') == 'revision':
            p = (lineage['predecessor_revision'], lineage['predecessor_sha256'])
            if n in parents and parents[n] != p:
                return None, 'DIVERGENT_DECLARED_PREDECESSORS'
            if n[0] != p[0] + 1:
                return None, 'NONCONSECUTIVE_DECLARED_REVISION'
            parents[n] = p
    if len(nodes) == 1:
        n = next(iter(nodes))
        return {'content_revision': n[0], 'record_sha256': n[1]}, 'UNCONTESTED_OBSERVATION'
    leaves = set(nodes) - set(parents.values())
    if len(leaves) != 1:
        return None, 'COMPETING_HEADS_RETAINED'
    leaf = next(iter(leaves))
    reached = set()
    cursor = leaf
    while cursor in nodes and cursor not in reached:
        reached.add(cursor)
        cursor = parents.get(cursor)
    if reached != set(nodes):
        return None, 'DISCONNECTED_OR_CYCLIC_HISTORY'
    return {'content_revision': leaf[0], 'record_sha256': leaf[1]}, 'DECLARED_REVISION_CHAIN_CANDIDATE'


def allocation_candidate(alternatives):
    merged = {'occurrences': {}, 'variants': {}}
    levels = {a['value'].get('legacy_level') for a in alternatives}
    if len(levels) != 1:
        return None, 'DIVERGENT_LEGACY_LEVEL'
    merged['legacy_level'] = levels.pop()
    for alt in alternatives:
        for field in ['occurrences', 'variants']:
            for key, value in alt['value'].get(field, {}).items():
                if key in merged[field] and merged[field][key] != value:
                    return None, 'SOURCE_LOCAL_KEY_REMAP'
                merged[field][key] = value
    for field in ['occurrences', 'variants']:
        if len(set(merged[field].values())) != len(merged[field]):
            return None, 'DUPLICATE_ALLOCATION_TARGET'
    return merged, 'EXACT_APPEND_UNION_OBSERVED'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--observation', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    source = ROOT / args.observation
    output = ROOT / args.output
    assert output.is_relative_to(ROOT / 'Build/manager-resume-r01/current-identity-union-intake-r01')
    output.mkdir(parents=True, exist_ok=False)
    def read(name):
        return json.loads((source / name).read_text())
    def save(name, obj):
        (output / name).write_bytes(canonical(obj) + b'\n')
    obs = {k: read(k + '-observations.json')['entries'] for k in ['registry', 'allocation', 'lineage', 'source_bindings']}
    provenance = read('provenance.json')
    ref_index = {x['path']: x for x in provenance['inputs']}
    assert read('freshness.json')['snapshot_stable']
    registry = []
    for entity, alts in obs['registry'].items():
        assert len(alts) == 1, ('Competing registry parents', entity)
        registry.append(alts[0]['value'])
    items = {r['id'] for r in registry if r['kind'] == 'item'}
    allocation, lineage, unresolved, dispositions = {}, {}, [], []
    for item in sorted(items):
        al, why = allocation_candidate(obs['allocation'].get(item, []))
        if al is None:
            unresolved.append({'item': item, 'component': 'allocation', 'reason': why})
        else:
            allocation[item] = al
        head, why = head_candidate(obs['lineage'].get(item, []))
        dispositions.append({'item': item, 'lineage_candidate_reason': why})
        if head is None:
            unresolved.append({'item': item, 'component': 'lineage', 'reason': why, 'alternatives': obs['lineage'][item]})
        else:
            lineage[item] = head
    registry_variants = {r['id'] for r in registry if r['kind'] == 'variant'}
    allocated_variants = {v for record in allocation.values() for v in record['variants'].values()}
    assert registry_variants == allocated_variants
    owners = {}
    for item, record in allocation.items():
        for v in record['variants'].values():
            assert v not in owners or owners[v] == item
            owners[v] = item
        for e in record['occurrences'].values():
            assert e.startswith(item + ':event:')
    reg_by_id = {r['id']: r for r in registry}
    for variant, owner in owners.items():
        assert reg_by_id[variant]['parent'] == owner
    # Exact explicit source identities only. Local labels and record_id maps
    # remain separate evidence and cannot manufacture global source identities.
    bindings, source_gaps = [], []
    for item in sorted(items):
        values = obs['source_bindings'].get(item, [])
        explicit = {v['value']['source_identity'] for v in values if v['value'].get('source_identity')}
        if len(explicit) == 1 and item in lineage:
            bindings.append({'source_identity': explicit.pop(), 'item': item, 'record_sha256': lineage[item]['record_sha256'], 'classification': 'OBSERVED_BINDING_JOIN_REQUIRES_CONTROLLER_ADOPTION'})
        else:
            source_gaps.append({'item': item, 'reason': 'MULTIPLE_EXPLICIT_SOURCE_IDENTITIES' if explicit else 'NO_EXPLICIT_GLOBAL_SOURCE_IDENTITY', 'explicit_source_identities': sorted(explicit), 'local_mapping_observations': len(values)})
    excluded = {item: obs['allocation'][item] for item in sorted(set(obs['allocation']) - items)}
    classification = {'classification': CLASS, 'controller_authorized': False, 'coverage_closed': False}
    save('registry-candidate.json', {**classification, 'entities': registry})
    save('allocation-candidate.json', {**classification, 'records': allocation})
    save('lineage-candidate.json', {**classification, 'records': lineage, 'unresolved': unresolved})
    save('source-bindings-candidate.json', {**classification, 'entries': bindings, 'gaps': source_gaps})
    save('reservation-evidence-candidate.json', {**classification, 'census_complete': None, 'typed_status_resolution': 'NOT_ASSERTED', 'observed': read('reservations-observed.json')['entries'], 'journal_evidence_ref': {'path': str((source/'journal-reservation-observations.json').relative_to(ROOT)), 'sha256': hashlib.sha256((source/'journal-reservation-observations.json').read_bytes()).hexdigest()}, 'requires': 'Controller must classify all current, held, permanent, retired and private-only identities in a current pinned census. Historical journal order is not an authority selector.'})
    save('head-dispositions.json', {'classification': CLASS, 'entries': dispositions})
    save('excluded-private-allocations.json', {'classification': CLASS, 'allocations_absent_from_observed_canonical_registry': excluded, 'additional_private_reference': ref_index['Build/level-oracle/levels/level004/all105-r01/producer-r01/packet-r04/package.json'], 'additional_private_id': 'fg:item:004901', 'scope': 'Retained provenance only. Exclusion is not permission to recycle an ID.'})
    selected = lineage['fg:item:000240']
    assert selected == {'content_revision': 1, 'record_sha256': 'de7b72f58de406164a7d03d6bfbf175d36a7e8c01b73ff8e48c08f276b877b50'}
    assert len(allocation['fg:item:000240']['occurrences']) == 40
    assert len(allocation['fg:item:000240']['variants']) == 12
    proof = {'classification': CLASS, 'item': 'fg:item:000240', 'observed_head': selected, 'source_bindings': [x for x in bindings if x['item'] == 'fg:item:000240'], 'retained_allocation': allocation['fg:item:000240'], 'historical_native_evidence': read('historical-predecessor-report-observations.json')['reports'], 'no_observed_competing_head': True, 'controller_current_head_certified': False, 'current_global_native_predecessor_report': None, 'missing': 'Current controller release that declares a closed global registry/allocation/lineage/reservation census and binds the selected predecessor at use time.'}
    save('selected-pilot-proof.json', proof)
    summary = {**classification, 'input_snapshot': read('summary.json')['observed_utc'], 'registry_entities': len(registry), 'registry_items': len(items), 'allocation_items': len(allocation), 'lineage_candidates': len(lineage), 'lineage_unresolved': unresolved, 'explicit_source_binding_candidates': len(bindings), 'source_binding_gaps': len(source_gaps), 'registered_variants': len(registry_variants), 'allocated_variants': len(allocated_variants), 'exact_reverse_variant_coverage': True, 'head_methods': dict(collections.Counter(x['lineage_candidate_reason'] for x in dispositions)), 'excluded_private_allocation_items': sorted(excluded), 'all_prior_observed_ids_retained': True, 'all_possible_current_ids_known': None, 'reference_gaps': len(provenance['reference_gaps']), 'live_authority_file_emitted': False, 'native_runs': 0}
    save('candidate-summary.json', summary)
    components = {}
    for filename in ['registry-candidate.json','allocation-candidate.json','lineage-candidate.json','source-bindings-candidate.json','reservation-evidence-candidate.json','selected-pilot-proof.json']:
        fp=output/filename;b=fp.read_bytes();components[filename]={'path':str(fp.relative_to(ROOT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    save('candidate-intake.json', {'schema':'fathom-private-current-identity-intake.1', **classification, 'components':components,'coverage':{'all_current_components':None,'all_held_and_permanent_reservations':None},'different_review':'PENDING','controller_adoption':'PENDING'})
    print(json.dumps({k:v for k,v in summary.items() if k!='lineage_unresolved'},indent=2))


if __name__ == '__main__':
    main()
