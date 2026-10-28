#!/usr/bin/env python3
"""Build P44's source-closed, nonadmitted Level13 timed-cell reference."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
from fractions import Fraction
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = Path('Build/parallel-44/controlled-open-level013-timed-rung-batch-r01')
STEM = 'Scale_Exercises_Section_II_Level_13_Major_Scale_Two_Octave_Six_String_Neck_Ladder'
TXT = Path(f'Notes/music/guitar project/TXT version/{STEM}.txt')
PDF = Path(f'Notes/music/guitar project/PDF version/{STEM}.pdf')
P10 = Path('Build/parallel-10/2.3.1.1.1-level013-whole-ladder-r01/candidate-01.json')
P12 = Path('Build/parallel-12/level013-local-shard-r01/package.json')
BASE = Path('Content/controls/curriculum-v1')
TXT_SHA = '973b9c614546e432282dcc0ba415a21c0bc28858e61e7910ef2d0559329a0956'
PDF_SHA = '0730f903d6d7a992b1f366f0e4977c05ba59d6467666fde5a7ea15ff20ca040c'
P10_SHA = 'eb3f51993f59803ce3d1df5305e5c7140fc6dadcdc8e1994a77c162420bb531e'
P12_SHA = '97a826ed6b42865d54f73e624f7a64e3b2bb87033f77490736c7437951f3d1b6'
ITEMS = ('fg:item:001153', 'fg:item:001154')
MODULES = ('fg:module:001153', 'fg:module:001154')
VARIANTS = (('fg:variant:007428', 'fg:variant:007429'),
            ('fg:variant:007430', 'fg:variant:007431'))
WORKBOOK = 'fg:workbook:000013'
NAMES = ('package.json', 'identity-registry.json', 'expected-profile.json',
         'candidate-allocation.json', 'identity-baseline.json', 'allocation-baseline.json',
         'lineage-baseline.json', 'source-provenance.json', 'summary.json')
OPEN_MIDI = {'E': 40, 'A': 45, 'D': 50, 'G': 55, 'B': 59, 'e': 64}
STRING = {'E': 1, 'A': 2, 'D': 3, 'G': 4, 'B': 5, 'e': 6}


class CandidateError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise CandidateError(code)


def encode(obj: object) -> bytes:
    return (json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')) + '\n').encode()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(path: Path) -> dict:
    return json.loads((ROOT / path).read_bytes())


def passage(path: Path, digest: str, fmt: str, value: str, **where: int) -> dict:
    return {'path': str(path), 'sha256': digest, 'format': fmt, **where,
            'text': value, 'text_sha256': sha(value.encode())}


def identity_scan() -> dict:
    """Fresh provisional collision check; P02 re-audits before canonical allocation."""
    wanted = [*ITEMS, *MODULES, *(v for pair in VARIANTS for v in pair)]
    patterns = [r'fg:(?:item|module):00115[34]', r'fg:variant:0074(?:28|29|30|31)']
    cmd = ['rg', '-l', '--no-messages', '-e', patterns[0], '-e', patterns[1],
           '--glob', '*.json', '--glob', '*.cpp', '--glob', '*.hpp',
           'Content', 'Source', 'Build']
    run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    need(run.returncode in (0, 1), 'IDENTITY_SCAN_FAILED')
    matches = sorted(x for x in run.stdout.splitlines() if not x.startswith(str(OUT) + '/'))
    need(not matches, 'PROVISIONAL_ID_COLLISION')
    return {'status': 'PASS', 'scope': ['Content', 'Source', 'Build'],
            'method': cmd, 'wanted': wanted, 'matches': matches,
            'classification': 'No current Content/Source/Build reference; P12 historical Level13 local allocation 001128-001140/007378-007403 is distinct. P02 must re-audit at canonical integration.',
            'canonical_reservation': False}


def source_facts() -> tuple[list[str], list[str], list[dict], dict]:
    need(sha((ROOT / TXT).read_bytes()) == TXT_SHA, 'TXT_PIN_DRIFT')
    need(sha((ROOT / PDF).read_bytes()) == PDF_SHA, 'PDF_PIN_DRIFT')
    need(sha((ROOT / P10).read_bytes()) == P10_SHA, 'P10_PIN_DRIFT')
    need(sha((ROOT / P12).read_bytes()) == P12_SHA, 'P12_PIN_DRIFT')
    lines = (ROOT / TXT).read_text().splitlines()
    pages = [(p.extract_text() or '') for p in PdfReader(str(ROOT / PDF)).pages]
    need(len(pages) == 7, 'PDF_PAGE_COUNT')
    rule = '\n'.join(lines[28:49])
    need('The result is 30 notes, so the next key begins with the same pick orientation.' in rule and
         'D-start: strict D-U alternate picking' in rule and
         'U-start: strict U-D alternate picking' in rule and
         'Do not restart the pick cycle' in rule and
         'First master the A-major cell alone. Then use 2-3 neighboring' in rule and
         'rungs, play even eighth notes, and pause one beat after each 30-note cell' in rule and
         'Repeat with both pick starts.' in rule, 'TXT_TIMING_PICK_RULE_DRIFT')
    need('Use 2-3 neighboring rungs' in pages[0] and 'pause one beat after' in pages[0] and
         'D-start and U-start' in pages[2] and 'A -> Bb -> B' in pages[0],
         'PDF_GUIDANCE_DRIFT')
    need('01' in pages[1] and 'A major' in pages[1] and 'Bb major' in pages[1] and
         '02' in pages[1] and 'Rungs 01-03' in pages[2], 'PDF_ROUTE_DRIFT')
    p10 = read(P10)
    need(p10['source']['txt_sha256'] == TXT_SHA and p10['source']['pdf_sha256'] == PDF_SHA and
         len(p10['rungs']) == 13 and not p10['exceptions'], 'P10_PARITY_DRIFT')
    p12 = read(P12)
    selected = p10['rungs'][:2]
    for idx, rung in enumerate(selected):
        root = 5 + idx
        need(rung['rung'] == idx + 1 and rung['key'] == ('A', 'Bb')[idx] and
             rung['low_e_root_fret'] == root and rung['pdf_page'] == 3 and
             rung['txt_header_line'] == 52 + 14 * idx and len(rung['notes']) == 30,
             'RUNG_SELECTION_DRIFT')
        need(rung['notes'][14]['midi'] == rung['notes'][15]['midi'] and
             rung['notes'][14]['string'] == rung['notes'][15]['string'] == 'e' and
             rung['notes'][0]['string'] == rung['notes'][-1]['string'] == 'E' and
             rung['notes'][0]['fret'] == rung['notes'][-1]['fret'] == root,
             'RUNG_TURN_DRIFT')
        tab_rows = rung['txt_rows']
        need('B' in tab_rows and 'e' in tab_rows and
             f'{root}--{root+2}' in tab_rows['B'] and
             f'{root-1}--{root}' in tab_rows['e'], 'B_STRING_OFFSET_DRIFT')
        prior = p12['records'][idx]
        need(len(prior['events']) == 30 and all(e['onset_q'] is None and e['duration_q'] is None
                                                for e in prior['events']), 'P12_UNTIMED_PARITY_DRIFT')
        for note, event in zip(rung['notes'], prior['events']):
            need((STRING[note['string']], note['fret'], note['finger'], note['midi'],
                  note['source_tone'], note['degree']) ==
                 (event['string'], event['fret'], event['finger'], event['midi'],
                  event['spelling'], next(iter(event['degree_contexts'].values()))['ordinal']),
                 'P12_CONTACT_PARITY_DRIFT')
        first = rung['txt_header_line']
        block = lines[first-1:first+11]
        need(block[0].startswith(f'RUNG {idx+1:02d} OF 13') and
             block[3] == tab_rows['Deg'] and block[4] == tab_rows['Fng'] and
             all(row in pages[2] for row in [block[3], block[4], *[tab_rows[s] for s in ('e','B','G','D','A','E')]]),
             'TXT_PDF_CARD_DRIFT')
    return lines, pages, selected, p12


def derive(*, changed_contacts: list | None = None, changed_onsets: list | None = None,
           changed_durations: list | None = None, changed_strokes: dict | None = None,
           changed_route: list | None = None, forced_bpm: int | None = None,
           force_eligible: bool = False, reserved_item: str = ITEMS[0]) -> dict[str, dict]:
    need(not force_eligible, 'FORCED_ELIGIBILITY')
    need(forced_bpm is None, 'FIXED_BPM_UNAUTHORIZED')
    need(reserved_item == ITEMS[0], 'FOREIGN_ID')
    audit_path = ROOT / OUT / 'identity-audit.json'
    need(audit_path.exists(), 'IDENTITY_AUDIT_MISSING')
    audit = json.loads(audit_path.read_bytes())
    need(audit['status'] == 'PASS' and not audit['matches'] and
         set(audit['wanted']) == set([*ITEMS, *MODULES, *(v for pair in VARIANTS for v in pair)]),
         'IDENTITY_AUDIT_DRIFT')
    audit_sha = sha(audit_path.read_bytes())
    lines, pages, selected, _p12 = source_facts()
    contacts = [selected[0]['notes'], selected[0]['notes'] + selected[1]['notes']]
    need(changed_contacts is None or changed_contacts == contacts, 'CANDIDATE_CONTACT_DRIFT')
    route = [['A'], ['A', 'Bb']]
    need(changed_route is None or changed_route == route, 'CANDIDATE_ROUTE_DRIFT')
    onsets = [ [list(Fraction(i, 2).as_integer_ratio()) for i in range(30)],
               [list(Fraction(i, 2).as_integer_ratio()) for i in range(30)] +
               [list((Fraction(16) + Fraction(i, 2)).as_integer_ratio()) for i in range(30)] ]
    durations = [[[1,2]]*30, [[1,2]]*60]
    need(changed_onsets is None or changed_onsets == onsets, 'CANDIDATE_TIMING_DRIFT')
    need(changed_durations is None or changed_durations == durations, 'CANDIDATE_DURATION_DRIFT')
    strokes = {vid: [start if i % 2 == 0 else ('U' if start == 'D' else 'D')
                     for i in range(n)]
               for pair, n in zip(VARIANTS, (30, 60)) for vid, start in zip(pair, ('D','U'))}
    need(changed_strokes is None or changed_strokes == strokes, 'CANDIDATE_STROKE_DRIFT')
    refs = ('L13-TXT-RULE-29-49', 'L13-PDF-GUIDANCE-P1', 'L13-TXT-RUNG01-52-63',
            'L13-TXT-RUNG02-66-77', 'L13-PDF-CARDS-P3')
    sources = {
        refs[0]: passage(TXT, TXT_SHA, 'txt', '\n'.join(lines[28:49]), first_line=29, last_line=49),
        refs[1]: passage(PDF, PDF_SHA, 'pdf', pages[0], page=1),
        refs[2]: passage(TXT, TXT_SHA, 'txt', '\n'.join(lines[51:63]), first_line=52, last_line=63),
        refs[3]: passage(TXT, TXT_SHA, 'txt', '\n'.join(lines[65:77]), first_line=66, last_line=77),
        refs[4]: passage(PDF, PDF_SHA, 'pdf', pages[2], page=3),
    }
    records, entities, event_sources, provenance, allocations = [], [], {}, {}, {}
    entities.append({'id': WORKBOOK, 'kind': 'workbook', 'label': 'Legacy Level13', 'parent': 'fg:course:000001'})
    for case_idx, (item, module, vids, case_contacts) in enumerate(zip(ITEMS, MODULES, VARIANTS, contacts)):
        local = ('L013-R01:A:EVEN_EIGHTH', 'L013-R01-R02:A_BB:EVEN_EIGHTH_ONE_BEAT_PAUSE')[case_idx]
        title = ('Level 13 Rung01 A-major 30-note excerpt of neighbor-stage even-eighth cell',
                 'Level 13 Rung01 A-major to Rung02 Bb-major two-cell even-eighth ladder')[case_idx]
        event_list, sidecar = [], {}
        for i, note in enumerate(case_contacts):
            eid = f'{item}:event:{i+1:04d}'
            rung_idx = 0 if i < 30 else 1
            source_ref = refs[2 + rung_idx]
            degree = note['degree']
            key = ('A-major', 'Bb-major')[rung_idx]
            event_list.append({'event_id': eid, 'kind': 'note', 'string': STRING[note['string']],
                               'fret': note['fret'], 'finger': note['finger'], 'midi': note['midi'],
                               'spelling': note['source_tone'], 'attack': 'picked',
                               'onset_q': onsets[case_idx][i], 'duration_q': durations[case_idx][i],
                               'tie_from': None,
                               'degree_contexts': {key: {'ordinal': degree, 'alteration': 0,
                                                        'source_label': str(degree)}}})
            event_sources[eid] = source_ref
            sidecar[eid] = {'source_local_event_key': f'{local}:R{rung_idx+1:02d}:{note["index"]:02d}',
                            'source_txt_ref': source_ref, 'source_pdf_ref': refs[4],
                            'source_txt_line': 52 + rung_idx*14,
                            'source_pdf_page': 3, 'source_rung': rung_idx+1,
                            'string_label': note['string'], 'string': STRING[note['string']],
                            'fret': note['fret'], 'finger_digit': note['finger'],
                            'degree': degree, 'spelling': note['source_tone'], 'midi': note['midi'],
                            'phase': note['phase'], 'repeated_high_root_at_turn': note['repeated_high_root_at_turn'],
                            'timing_txt_ref': refs[0], 'timing_pdf_ref': refs[1],
                            'nominal_slot_q': onsets[case_idx][i],
                            'one_beat_pause_after_first_cell': case_idx == 1 and i == 29,
                            'whole_frame_move_fret': 1 if case_idx == 1 and i == 29 else 0}
        provenance.update(sidecar)
        variants = []
        for vid, start in zip(vids, ('D','U')):
            variants.append({'id': vid, 'label': f'{local.lower()}-{start}-start',
                             'role': 'notation_practice',
                             'route': 'standalone_rung01' if case_idx == 0 else 'rung01_to_rung02_neighbor_training',
                             'source_refs': list(refs), 'event_ids': list(sidecar),
                             'pick_start': start, 'pick_start_origin': 'source_authored',
                             'grouping': {'kind': 'source_event_time', 'notes_per_beat': None,
                                          'beat_unit_q': None, 'marking_factor': [1,1],
                                          'source_label': 'TXT practice even eighths; pause one beat after 30-note cell in two-neighbor stage'},
                             'accent_policy': 'even', 'tail_pause': None, 'unresolved': []})
        record = {'id': item, 'module_id': module, 'workbook_id': WORKBOOK,
                  'content_revision': 1, 'lineage': {'kind': 'new'}, 'kind': 'notation',
                  'legacy_level': 13, 'status': 'converted_candidate', 'runtime_eligible': False,
                  'title': title, 'source_refs': list(refs), 'authored_text_refs': list(refs),
                  'events': event_list, 'variants': variants, 'resource_requirements': [], 'rubric': None,
                  'control_scope': {'extent': 'complete_selected_case', 'local_case': local,
                                    'source_event_count': len(event_list), 'basis_refs': list(refs),
                                    'whole_workbook_complete': False,
                                    'unresolved': ['Rungs03-13 and the full 25-cell round trip are outside this case.',
                                                   'Runtime admission and whole Level13 remain Pending.']},
                  'context': {'local_code': local, 'route': 'A standalone neighbor-stage excerpt' if case_idx == 0 else 'A to Bb first two-neighbor stage',
                              'position': 'low-E root fret5' if case_idx == 0 else 'low-E root fret5 to fret6',
                              'pick_start_variants': ['D','U'],
                              'pick_start': 'source-authored strict D/U or U/D without reset at strings, turn or relocation',
                              'tuning_open_midi': [40,45,50,55,59,64], 'capo': 0,
                              'source_tempo_rules_ref': refs[0]},
                  'timing': {'status': 'source_defined', 'unit': 'quarter', 'meter': None,
                             'basis': 'Nominal even-eighth quarter-note slots from TXT practice rule. Two-neighbor case inserts one full quarter beat after first 30-note cell before Bb onset. No fixed BPM or measured sustain.'},
                  'ambiguities': ['Standalone A even-eighth grid is the first authored cell practiced alone within the neighbor-training stage; first-mastery stage itself does not specify a separate rhythm.',
                                  'PDF page1 confirms one-beat pause and D/U starts but TXT supplies the explicit even-eighth note value.',
                                  'Relative tempo/progression guidance does not establish fixed BPM, clean performance, mastery or credit.',
                                  'Capo zero is untransposed standard-tuning representation, not a capo instruction.'],
                  'normalization': [{'kind': 'representation_metadata', 'basis': refs[0],
                                     'text': 'Rung01 standalone or A-to-Bb first two-neighbor even-eighth stage, 30 notes per cell, repeated high root and strict continuous alternate picking. One-beat pause only between cells in paired case.'}]}
        records.append(record)
        entities.extend([{'id': module, 'kind': 'module', 'label': title, 'parent': WORKBOOK},
                         {'id': item, 'kind': 'item', 'label': title, 'parent': module},
                         *({'id': v['id'], 'kind': 'variant', 'label': v['label'], 'parent': item}
                           for v in variants)])
        allocations[item] = {'legacy_level': 13,
                             'occurrences': {p['source_local_event_key']: eid for eid,p in sidecar.items()},
                             'variants': {v['label']: v['id'] for v in variants}}
    base_package, base_registry, base_profile = (read(BASE/name) for name in
                                                  ('package.json','identity-registry.json','expected-profile.json'))
    package = {k: copy.deepcopy(v) for k,v in base_package.items()
               if k not in ('records','sources','workbook_catalog')}
    package.update(content_version='curriculum-v1-level013-rung01-a-and-a-bb-timed-build-only.1',
                   records=records, sources=sources)
    registry = {'identity_version': base_registry['identity_version'], 'rules': base_registry['rules'],
                'entities': [base_registry['entities'][0], *entities]}
    identity_baseline = {'identity_version': registry['identity_version'],
                         'rules': registry['rules'], 'entities': [registry['entities'][0]]}
    allocation_baseline = {'version': 'control-allocation.1', 'authority': 'P44 provisional only', 'records': {}}
    lineage_baseline = {'version': 'lineage-baseline.1', 'records': {}}
    allocation = {'version': 'control-allocation.1',
                  'authority': 'P44 provisional nonadmitted allocation; P02 canonical re-audit required',
                  'records': allocations}
    profile = {k: copy.deepcopy(v) for k,v in base_profile.items()
               if k not in ('reference_package','reference_registry','event_sources',
                            'authority_artifacts','workbook_catalog')}
    profile['degree_roots'] = {
        'A-major': {'basis': 'Level13 original Rung01 A major source card; pitch class only',
                    'root_pitch_class': 9},
        'Bb-major': {'basis': 'Level13 original Rung02 Bb major source card; pitch class only',
                     'root_pitch_class': 10}}
    profile.update(reference_package=package, reference_registry=registry,
                   event_sources=event_sources)
    profile['authority_artifacts'] = [copy.deepcopy(a) for a in base_profile['authority_artifacts']
                                      if a['role'] in ('source_manifest','source_acceptance','current_schema_freeze')]
    for role,name,value in (('identity_baseline','identity-baseline.json',identity_baseline),
                            ('allocation_baseline','allocation-baseline.json',allocation_baseline),
                            ('lineage_baseline','lineage-baseline.json',lineage_baseline),
                            ('candidate_identity_allocation','candidate-allocation.json',allocation)):
        profile['authority_artifacts'].append({'path': str(OUT/name), 'role': role,
                                               'sha256': sha(encode(value))})
    need(set(event_sources) == set(provenance) ==
         {e['event_id'] for r in records for e in r['events']}, 'EVENT_PROVENANCE_COVERAGE')
    summary = {'status': 'source_interpreted_nonadmitted_reference',
               'item_ids': list(ITEMS), 'variant_ids': [v for pair in VARIANTS for v in pair],
               'record_count': 2, 'event_count': 90, 'variant_count': 4,
               'runtime_eligible': False, 'admitted': False, 'whole_workbook_complete': False,
               'source_txt_sha256': TXT_SHA, 'source_pdf_sha256': PDF_SHA,
               'p10_parity_sha256': P10_SHA, 'p12_parity_sha256': P12_SHA,
               'identity_audit_sha256': audit_sha,
               'first_case_end_q': [15,1], 'second_case_end_q': [31,1],
               'interpretation': 'A standalone as first even-eighth neighbor-stage cell; A-to-Bb two-neighbor with one-beat intercell pause; no fixed BPM or mastery. Independent P47 review required.'}
    return {'package.json': package, 'identity-registry.json': registry,
            'expected-profile.json': profile, 'candidate-allocation.json': allocation,
            'identity-baseline.json': identity_baseline, 'allocation-baseline.json': allocation_baseline,
            'lineage-baseline.json': lineage_baseline,
            'source-provenance.json': {'source_txt_refs': [refs[0],refs[2],refs[3]],
                                       'source_pdf_refs': [refs[1],refs[4]],
                                       'events': provenance, 'variant_strokes': strokes,
                                       'stroke_basis': 'TXT strict alternate D/U or U/D through all crossings, turn and relocation; 30 even contacts preserve next-cell orientation.'},
            'summary.json': summary}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('audit','build','verify'))
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    dest = (ROOT / args.out).resolve()
    allowed = (ROOT / OUT).resolve()
    need(dest == allowed or allowed in dest.parents, 'OUTPUT_SCOPE')
    if args.command == 'audit':
        result = identity_scan()
        dest.mkdir(parents=True, exist_ok=True)
        target = dest/'identity-audit.json'
        need(not target.exists(), 'OUTPUT_EXISTS')
        target.write_bytes(encode(result))
        print(json.dumps(result, sort_keys=True))
        return
    output = derive()
    if args.command == 'build':
        dest.mkdir(parents=True, exist_ok=True)
        need(all(not (dest/name).exists() for name in NAMES), 'OUTPUT_EXISTS')
        for name in NAMES:
            (dest/name).write_bytes(encode(output[name]))
    else:
        for name in NAMES:
            need((dest/name).read_bytes() == encode(output[name]), f'OUTPUT_DRIFT:{name}')
    print(json.dumps(output['summary.json'], sort_keys=True))


if __name__ == '__main__':
    main()
