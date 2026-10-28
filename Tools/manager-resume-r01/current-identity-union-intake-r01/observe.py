#!/usr/bin/env python3
"""Read-only bounded identity intake. Never authorizes a union or chooses a head.

Sources are reached from current CMake/compiled catalog, current profiles and
explicit checkpoint history. Alternatives are retained, including old revisions.
The output is an observation graph, deliberately not exporter authority syntax.
"""
import argparse
import collections
import hashlib
import json
import pathlib
import re
import subprocess
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[3]
DEFAULT = 'Build/manager-resume-r01/current-identity-union-intake-r01/observation-r01'
CLASS = 'PRIVATE_INTAKE_CANDIDATE'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique_keys(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise ValueError('Duplicate JSON key: ' + k)
        d[k] = v
    return d


class Observer:
    def __init__(self):
        self.inputs = {}
        self.edges = []
        self.gaps = []
        self.groups = []
        self.facts = {k: collections.defaultdict(dict) for k in ['registry', 'allocation', 'lineage', 'source_bindings']}
        self.reservations = []
        self.checked_profiles = set()
        self.selected = []

    def pin(self, path, role):
        path = pathlib.Path(path)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Non-repository path: ' + str(path))
        full = ROOT / path
        data = full.read_bytes()
        key = path.as_posix()
        ref = {'path': key, 'bytes': len(data), 'sha256': digest(data)}
        if key in self.inputs and self.inputs[key]['sha256'] != ref['sha256']:
            raise RuntimeError('Input changed during observation: ' + key)
        self.inputs.setdefault(key, {**ref, 'roles': []})['roles'].append(role)
        return ref

    def read(self, path, role):
        self.pin(path, role)
        return json.loads((ROOT / path).read_text(), object_pairs_hook=unique_keys)

    def resolve(self, ref, parent, base=None):
        declared = ref['path']
        choices = []
        if base:
            choices.append(pathlib.Path(base) / declared)
        choices.append(pathlib.Path(declared))
        if declared.startswith('Results/') and not declared.startswith('Results/primary/'):
            choices.append(pathlib.Path('Results/primary') / declared[8:])
        attempts = []
        for p in dict.fromkeys(choices):
            if not (ROOT / p).is_file():
                attempts.append({'path': str(p), 'state': 'ABSENT'})
                continue
            actual = self.pin(p, 'declared_reference')
            ok = (not ref.get('sha256') or actual['sha256'] == ref['sha256']) and (not ref.get('bytes') or actual['bytes'] == ref['bytes'])
            attempts.append({'path': str(p), 'state': 'MATCH' if ok else 'MISMATCH', 'actual': actual})
            if ok:
                self.edges.append({'from': parent, 'declared': ref, 'resolved': actual, 'resolution_attempts': attempts})
                return p
        self.gaps.append({'type': 'UNRESOLVED_DECLARED_REFERENCE', 'from': parent, 'declared': ref, 'attempts': attempts})
        return None

    def fact(self, component, key, value, path, role):
        sig = digest(canonical(value))
        item = self.facts[component][key].setdefault(sig, {'value': value, 'evidence': []})
        e = {'path': str(path), 'role': role}
        if e not in item['evidence']:
            item['evidence'].append(e)

    def component(self, path, kind, role):
        d = self.read(path, role)
        if kind == 'registry':
            for e in d.get('entities', []):
                self.fact(kind, e['id'], {k: e.get(k) for k in ['id', 'kind', 'parent']}, path, role)
            for key in ['reserved_ranges', 'reservations']:
                if key in d:
                    self.reservations.append({'role': role, 'path': str(path), 'field': key, 'value': d[key]})
        elif kind in ['allocation', 'lineage']:
            for item, value in d.get('records', {}).items():
                self.fact(kind, item, value, path, role)
        return d

    def package(self, path, role):
        d = self.read(path, role)
        for record in d.get('records', []):
            item = record['id']
            v = {'content_revision': record['content_revision'], 'record_sha256': digest(canonical(record)), 'lineage': record.get('lineage'), 'legacy_level': record.get('legacy_level')}
            self.fact('lineage', item, v, path, role)
            if item == 'fg:item:000240':
                self.selected.append({'path': str(path), **v, 'event_ids': [e['event_id'] for e in record['events']], 'variant_ids': [v.get('id', v.get('variant_id')) for v in record['variants']]})
        return d

    def profile(self, path, base=None):
        if str(path) in self.checked_profiles:
            return
        self.checked_profiles.add(str(path))
        d = self.read(path, 'profile')
        roles = {'identity_baseline': 'registry', 'allocation_baseline': 'allocation', 'lineage_baseline': 'lineage', 'candidate_identity_allocation': 'allocation', 'current_source_identity_allocation': 'source_map', 'source_identity_allocation': 'source_map'}
        for ref in d.get('authority_artifacts', []):
            found = self.resolve(ref, str(path), base)
            if found and ref.get('role') in roles:
                kind = roles[ref['role']]
                if kind == 'source_map':
                    self.source_map(found, 'declared_source_map')
                else:
                    self.component(found, kind, ref['role'])

    def source_map(self, path, role):
        d = self.read(path, role)
        # Retain exact mapping objects; never infer a printed source identity
        # from a label, numeric position or title.
        entries = d if isinstance(d, list) else d.get('entries', d.get('records', d))
        iterator = enumerate(entries) if isinstance(entries, list) else entries.items()
        for local, value in iterator:
            if isinstance(value, dict) and any(k in value for k in ['item', 'item_id', 'record_id', 'source_identity']):
                item = value.get('item_id', value.get('item', value.get('record_id', value.get('source_identity'))))
                self.fact('source_bindings', str(item), {'source_local_key': str(local), 'mapping': value}, path, role)

    def installed(self):
        cmake = (ROOT / 'CMakeLists.txt').read_text()
        header = (ROOT / 'Source/content/InstalledExtensionRegistry.hpp').read_text()
        paths = dict((macro, path) for path, macro in re.findall(r'file\(SHA256 "\$\{CMAKE_CURRENT_SOURCE_DIR\}/([^"]+)" (FATHOM_[A-Z0-9_]+)\)', cmake))
        entries = re.findall(r'\{"([\w-]+extension)", "([^"]+)", (FATHOM_[A-Z0-9_]+)', header)
        assert len(entries) == 38 and len(set(n for n, _, _ in entries)) == 38
        entries.insert(0, ('representative', 'lesson-bundle.1', 'FATHOM_LESSON_MANIFEST_SHA'))
        for name, version, macro in entries:
            path = pathlib.Path(paths[macro])
            m = self.read(path, 'compiled_installed_manifest')
            assert m['version'] == version
            resolved = {}
            base = path.parent if name != 'representative' else None
            for ref in m['files']:
                resolved[ref['path']] = self.resolve(ref, str(path), base)
            p = resolved.get(m['entries']['package'])
            reg = resolved.get(m['entries']['registry'])
            pro = resolved.get(m['entries']['profile'])
            if p:
                package = self.package(p, 'compiled_installed_package:' + name)
            else:
                package = {'records': []}
            if reg:
                self.component(reg, 'registry', 'compiled_installed_registry:' + name)
            if pro:
                self.profile(pro, base)
            for declared, found in resolved.items():
                if found and pathlib.Path(declared).name in ['candidate-allocation.json', 'identity-allocation.json']:
                    self.component(found, 'allocation', 'installed_manifest_allocation:' + name)
            self.groups.append({'name': name, 'manifest': str(path), 'package': str(p), 'registry': str(reg), 'profile': str(pro), 'items': [r['id'] for r in package['records']], 'manifest_files': len(m['files']), 'resolved_files': sum(v is not None for v in resolved.values())})

    def foundation_and_shards(self):
        self.package(pathlib.Path('Content/controls/curriculum-v1/package.json'), 'current_foundation')
        self.component(pathlib.Path('Content/controls/curriculum-v1/identity-registry.json'), 'registry', 'current_foundation')
        self.profile(pathlib.Path('Content/controls/curriculum-v1/expected-profile.json'))
        src = re.search(r'set\(FATHOM_SHARD_SOURCE "\$\{CMAKE_CURRENT_SOURCE_DIR\}/([^"]+)"\)', (ROOT / 'CMakeLists.txt').read_text()).group(1)
        hp = pathlib.Path(src) / 'handoff.json'
        h = self.read(hp, 'cmake_shard_handoff')
        base = pathlib.Path(src) / h['bundle_root']
        for ref in [h['inventory'], h['manifest'], *h['foundation'].values()]:
            self.resolve(ref, str(hp), base)
        for shard in h['shards']:
            out = {}
            for kind, ref in shard['artifacts'].items():
                p = self.resolve(ref, str(hp), base)
                out[kind] = str(p)
                if not p:
                    continue
                if kind == 'package':
                    self.package(p, 'compiled_readonly_shard')
                elif kind in ['registry', 'identity_baseline']:
                    self.component(p, 'registry', kind)
                elif kind in ['allocation_baseline', 'candidate_allocation']:
                    self.component(p, 'allocation', kind)
                elif kind == 'lineage_baseline':
                    self.component(p, 'lineage', kind)
                elif kind == 'profile':
                    self.profile(p, base)
                elif kind == 'source_map':
                    self.source_map(p, kind)
            self.groups.append({'name': 'read_only_shard_level' + str(shard['legacy_level']), 'artifacts': out})

    def checkpoint_history(self):
        # This exact old head is explicitly retained/reserved by the current
        # checkpoint. It is not selected as today's head.
        p = pathlib.Path('Results/primary/20260912T212701Z-2.3.1.1.1-r15-evidence/handoff01/identity-head.json')
        h = self.read(p, 'checkpoint_retained_unfinalized_r15_head')
        for kind in ['registry', 'allocation', 'lineage', 'source_candidate']:
            found = self.resolve(h[kind], str(p))
            if found:
                if kind == 'source_candidate':
                    self.package(found, 'historical_reserved_unfinalized_r15')
                else:
                    self.component(found, kind, 'historical_reserved_unfinalized_r15')
        self.reservations.append({'path': str(p), 'status': 'RETAINED_NOT_RECYCLED', 'basis': 'Current checkpoint explicitly retains505 new entities of prepared r15; final current disposition is not asserted.'})
        parent = self.resolve(h['parent'], str(p))
        h14 = self.read(parent, 'r15_parent_not_current_global')
        for kind in ['registry', 'allocation', 'lineage']:
            found = self.resolve(h14[kind], str(parent))
            if found:
                self.component(found, kind, 'historical_r14_parent')
        self.predecessor_reports = []
        for ref in h14['source_predecessor_reports']:
            found = self.resolve(ref, str(parent))
            if found:
                report = self.read(found, 'historical_predecessor_report_not_current_global')
                selected = [r for r in report.get('records', []) if isinstance(r, dict) and r.get('id', r.get('item_id')) == 'fg:item:000240']
                if selected:
                    compact = [{k: r.get(k) for k in ['id', 'content_revision', 'record_sha256', 'valid_reference', 'technically_renderable', 'curriculum_playback_authorized']} for r in selected]
                    self.predecessor_reports.append({'path': str(found), 'package_sha256': report.get('package_sha256'), 'registry_sha256': report.get('registry_sha256'), 'profile_sha256': report.get('profile_sha256'), 'valid_reference': report.get('valid_reference'), 'exit_code': report.get('exit_code'), 'selected_record': compact})
        # Exact Level1 variant reservation is bound by installed manifest and
        # journal. Preserve its explicit map instead of generating a range.
        p = pathlib.Path('Results/primary/manager-resume-r01/level001-variant-reservation.json')
        r = self.read(p, 'manager_exact_variant_reservation')
        proposal = self.resolve(r['allocation_proposal'], str(p))
        self.reservations.append({'path': str(p), 'status': r['status'], 'mapping': str(proposal), 'first': r['first'], 'last': r['last'], 'count': r['count']})

    def bounded_supplement(self):
        self.pin('Results/primary/20260926T2307Z-level013-r03-installed-accept-adoption.md', 'installed_branch_adoption_not_global_lineage_reconciliation')
        # The current journal explicitly cites this historical audit. Follow
        # only its113 declared registry refs, not an unbounded Build crawl.
        audit_path = pathlib.Path('Build/parallel-02/level012-rung03-shard-r01/identity-audit.json')
        audit = self.read(audit_path, 'journal_declared_historical_identity_audit')
        assert len(audit['registries']) == 113
        self.audit_results = []
        known = set(self.facts['registry'])
        for ref in audit['registries']:
            p = self.resolve(ref, str(audit_path))
            if p:
                d = self.read(p, 'historical_audit_registry_observation')
                extra = [e for e in d['entities'] if e['id'] not in known]
                self.audit_results.append({'path': str(p), 'additional_entities': extra, 'classification': 'HISTORICAL_AUDIT_OBSERVATION_NOT_AUTOMATIC_CURRENT_COMPONENT'})
        # Distinct unadmitted Level13 local shard is documented by that audit.
        # Preserve its facts and competing installed item1130 revision1, rather
        # than choosing either by time or highest revision.
        base = pathlib.Path('Build/parallel-12/level013-local-shard-r01')
        self.component(base / 'identity-registry.json', 'registry', 'historical_unadmitted_level013_shard')
        self.package(base / 'package.json', 'historical_unadmitted_level013_shard')
        self.profile(base / 'expected-profile.json')
        # The abandoned Rung02 attempt at1128 is kept in separate evidence; it
        # is not a new canonical allocation. Its current disposition is a gap.
        for filename in ['identity-registry.json', 'candidate-allocation.json', 'package.json', 'summary.json']:
            self.pin(pathlib.Path('Build/parallel-02/level012-rung02-vertical-r01/attempt-01') / filename, 'abandoned_rung02_attempt_not_merged')
        # Explicitly separate the private Oracle Level4 pilot from canonical
        # printed Level4 identities and the selected Level3 source.
        self.pin('Build/level-oracle/levels/level004/all105-r01/producer-r01/packet-r04/package.json', 'private_noncanonical_oracle004901_not_merged')
        pilot = pathlib.Path('Build/manager-resume-r01/two-pilot-admission-exporter-r02/l003-modeb001-input.json')
        d = self.read(pilot, 'adopted_exporter_selected_input')
        self.pilot_spec = d
        for value in d.values():
            refs = value if isinstance(value, list) else [value]
            for ref in refs:
                if isinstance(ref, dict) and 'path' in ref and 'sha256' in ref:
                    self.resolve(ref, str(pilot))
        self.fact('source_bindings', d['item'], {'source_identity': d['source_identity'], 'item': d['item'], 'record_sha256': d['canonical_record_sha256']}, pilot, 'explicit_selected_controller_adopted_binding')
        learn = pathlib.Path('Content/runtime/learn-source-index-v1')
        self.read(learn / 'index.json', 'current_learn_descriptor')
        base_ref = self.pin(learn / 'exercises.jsonl', 'current_learn_source_rows')
        overlay = self.read(learn / 'accepted-overlay.json', 'current_learn_installed_bindings')
        assert overlay['base_exercises_sha256'] == base_ref['sha256']
        for line in (ROOT / learn / 'exercises.jsonl').read_text().splitlines():
            row = json.loads(line, object_pairs_hook=unique_keys)
            for binding in row['frozen_installed_bindings']:
                self.fact('source_bindings', binding['item_id'], {'source_identity': row['source_identity'], 'binding': binding}, learn / 'exercises.jsonl', 'frozen_installed_source_binding')
        for entry in overlay['entries']:
            self.fact('source_bindings', entry['binding']['item_id'], entry, learn / 'accepted-overlay.json', 'current_installed_source_overlay')
        annex = self.read('Planning/Fathom-Exercise-WBS-Annex-v1.json', 'current_official_child_identity_bindings')
        for op in annex['current_status_resolution']['operations']:
            overlay = op['current_overlay']
            if overlay.get('item_id'):
                self.fact('source_bindings', overlay['item_id'], {'source_identity': op['selection']['source_identity'], 'package_key': op['selection']['package_key'], 'current_overlay': overlay}, 'Planning/Fathom-Exercise-WBS-Annex-v1.json', 'current_official_child_operation')

    def journals(self):
        out = []
        for rel in ['Prompts/parallel-02/Lane-Reservations-Current.md', 'Results/primary/Fathom-Loop-State.md']:
            self.pin(rel, 'live_reservation_or_checkpoint')
            lines = (ROOT / rel).read_text().splitlines()
            heading = ''
            for n, line in enumerate(lines, 1):
                if line.startswith('## '):
                    heading = line
                exact = re.findall(r'fg:(?:item|module|variant):\d{6}(?::event:\d{4})?', line)
                relevant = bool(re.search(r'reserv|permanent|not.?recycl|no.?reuse|allocated', line, re.I) and (exact or re.search(r'\b\d{6}\b', line)))
                if relevant:
                    out.append({'path': rel, 'line': n, 'heading': heading, 'text': line, 'explicit_typed_ids': sorted(set(exact)), 'status': 'UNNORMALIZED_JOURNAL_EVIDENCE_NOT_CURRENT_STATE'})
        return out

    def write(self, output):
        output.mkdir(parents=True, exist_ok=False)
        def save(name, obj):
            (output / name).write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
        for kind, values in self.facts.items():
            save(kind + '-observations.json', {'classification': CLASS, 'schema': 'fathom-identity-component-observations.1', 'component': kind, 'entries': {k: list(v.values()) for k, v in sorted(values.items())}, 'head_selection': 'NONE; competing observed facts retained'})
        save('reservations-observed.json', {'classification': CLASS, 'entries': self.reservations, 'closed_census': False})
        save('provenance.json', {'classification': CLASS, 'inputs': [self.inputs[k] for k in sorted(self.inputs)], 'edges': self.edges, 'groups': self.groups, 'reference_gaps': self.gaps})
        save('selected-pilot-observations.json', {'classification': CLASS, 'item': 'fg:item:000240', 'observations': self.selected, 'controller_current_predecessor_proved': False})
        save('historical-predecessor-report-observations.json', {'classification': CLASS, 'reports': self.predecessor_reports, 'current_global_native_report': None})
        save('historical-audit-supplement.json', {'classification': CLASS, 'registries': self.audit_results, 'warning': 'Historical audit evidence is not a controller-certified current census.'})
        counts = {k: {'identities': len(v), 'multiple_distinct_values': sum(len(x) > 1 for x in v.values())} for k, v in self.facts.items()}
        summary = {'classification': CLASS, 'schema': 'fathom-current-identity-intake.1', 'observed_utc': datetime.now(timezone.utc).isoformat(), 'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'counts': counts, 'groups': len(self.groups), 'input_files': len(self.inputs), 'reference_edges': len(self.edges), 'unresolved_references': len(self.gaps), 'coverage': {'all_current_components': None, 'all_held_and_permanent_reservations': None}, 'controller_authorized': False, 'exporter_live_guard_run': False, 'allocated_ids': 0, 'admission_increment': 0}
        save('summary.json', summary)
        return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default=DEFAULT)
    args = parser.parse_args()
    output = ROOT / args.output
    if not output.is_relative_to(ROOT / 'Build/manager-resume-r01/current-identity-union-intake-r01'):
        raise ValueError('Output outside private lane')
    o = Observer()
    for path in ['CMakeLists.txt', 'Source/content/InstalledExtensionRegistry.hpp', 'Source/content/LessonCatalog.cpp', 'Source/content/CurriculumShardCatalog.cpp', 'Content/controls/curriculum-v1/generation.json', 'Content/controls/curriculum-v1/workbook-coverage.json', 'Planning/Fathom-Exercise-WBS-Annex-v1.json']:
        o.pin(path, 'live_root')
    journal = o.journals()
    o.foundation_and_shards()
    o.installed()
    o.checkpoint_history()
    o.bounded_supplement()
    # No output is described as a stable snapshot unless every pinned input
    # still matches; failed observations are retained in the private Build root.
    drift = []
    for path, ref in o.inputs.items():
        data = (ROOT / path).read_bytes()
        if len(data) != ref['bytes'] or digest(data) != ref['sha256']:
            drift.append(path)
    summary = o.write(output)
    (output / 'journal-reservation-observations.json').write_text(json.dumps({'classification': CLASS, 'entries': journal, 'warning': 'Historical prose; no automatic newest-line state selection.'}, indent=2) + '\n')
    (output / 'freshness.json').write_text(json.dumps({'checked': len(o.inputs), 'drift': drift, 'snapshot_stable': not drift}, indent=2) + '\n')
    print(json.dumps({**summary, 'freshness_drift': drift}, indent=2))
    if drift:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
