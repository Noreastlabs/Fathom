#!/usr/bin/env python3
"""P78: source-bound Level20 A-major learning-mode circuit, nonadmitted."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path

from pypdf import PdfReader
import curriculum_level020_whole_synthesis_candidate as p05

ROOT = Path(__file__).resolve().parents[1]
OUT = Path('Build/parallel-78/controlled-open-level020-first-circuit-r01')
TXT, PDF = p05.TXT_REL, p05.PDF_REL
P05 = Path('Build/parallel-05/2.3.1.1.1-level020-whole-r01/candidate-c.json')
P12 = Path('Build/parallel-12/level020-schema1-unallocated-r01/field-proposal.json')
BASE = Path('Content/controls/curriculum-v1')
NATIVE = Path('Build/parallel-13/four-shard-source-bundle-r01/bundle/bin/fathom_content_validate')
NATIVE_SHA = 'a85c1b25d8cded12cbe273e4620bd5f33a711d06311d29583a0fdbed7748f714'
PINS = {
    TXT: 'd64e78142630e4b6e22ce49055df87938062d9051eb44d792a1a46448e54d410',
    PDF: 'b3160de6f22ffbb1b2fe8ca42bd02474a813fe2088a747cea628968fc7914dd5',
    P05: '3a0bbd3093afb093a96432b2d6e46c676d5a217e23d4c2b0d430577f433b5bff',
    P12: 'fd52fa993d7b31e8a2cc5279e7b6e1e79b241eb005632946ce5f7d85637ea0a8',
    BASE/'package.json': '766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255',
    BASE/'identity-registry.json': '5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5',
    BASE/'expected-profile.json': '21009e3596f325a4b9f73c9532b71cd361703e0f682b40088ff58bff7ba57c8a',
}
ITEM = 'fg:item:009780'
MODULE = 'fg:module:009780'
VARIANTS = ('fg:variant:009780', 'fg:variant:009781')
WORKBOOK = 'fg:workbook:000020'
STRINGS = {'E': 1, 'A': 2, 'D': 3, 'G': 4, 'B': 5, 'e': 6}
OPEN_MIDI = {'E': 40, 'A': 45, 'D': 50, 'G': 55, 'B': 59, 'e': 64}
MODULE_COUNTS = (30, 78, 96, 52, 66)
BOUNDARIES = (0, 30, 108, 204, 256, 322)
NAMES = ('package.json', 'identity-registry.json', 'expected-profile.json',
         'candidate-allocation.json', 'identity-baseline.json',
         'allocation-baseline.json', 'lineage-baseline.json',
         'source-provenance.json', 'summary.json')

class CandidateError(ValueError):
    pass

def need(ok, code):
    if not ok:
        raise CandidateError(code)

def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))+'\n').encode()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read(path):
    return json.loads((ROOT/path).read_bytes())

def pin():
    top = Path(subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', '--show-toplevel'], text=True).strip())
    need(top.resolve() == ROOT.resolve(), 'ROOT_DRIFT')
    for path, digest in PINS.items():
        need(sha((ROOT/path).read_bytes()) == digest, 'PIN_DRIFT:'+str(path))
    need(sha((ROOT/NATIVE).read_bytes()) == NATIVE_SHA, 'NATIVE_DRIFT')

def identity_scan():
    cmd = ['rg', '-l', '--no-messages', '-e', r'fg:(?:item|module):009780',
           '-e', r'fg:variant:00978[01]', '--glob', '*.json', '--glob', '*.hpp',
           '--glob', '*.cpp', 'Content', 'Source', 'Build']
    run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    need(run.returncode in (0, 1), 'IDENTITY_SCAN_FAILED')
    hits = sorted(x for x in run.stdout.splitlines() if not x.startswith(str(OUT)+'/'))
    need(not hits, 'PROVISIONAL_ID_COLLISION')
    return {'status': 'PASS', 'method': cmd, 'scope': ['Content', 'Source', 'Build'],
            'wanted': [ITEM, MODULE, *VARIANTS], 'matches': hits,
            'canonical_reservation': False,
            'classification': 'P78 provisional nonadmitted IDs only; P02 serial allocation required'}

def source_ref(path, fmt, value, **where):
    return {'path': str(path), 'format': fmt, 'sha256': PINS[path], **where,
            'text': value, 'text_sha256': sha(value.encode())}

def source_facts():
    pin()
    whole = p05.build_candidate()
    need(json.loads(encode(whole)) == read(P05), 'P05_REBUILD_DRIFT')
    rung = whole['rungs'][0]
    need(rung['key'] == 'A' and rung['contact_count'] == 322, 'SOURCE_RUNG_SCOPE')
    modules = rung['modules']
    need(tuple(m['contact_count'] for m in modules) == MODULE_COUNTS, 'SOURCE_MODULE_COUNTS')
    proposal = read(P12)['records'][:5]
    need([(r['key'], r['module_number']) for r in proposal] ==
         [('A', i) for i in range(1, 6)], 'P12_SCOPE')
    lines = (ROOT/TXT).read_text().splitlines()
    pages = [(page.extract_text() or '').splitlines() for page in PdfReader(str(ROOT/PDF)).pages]
    need(len(pages) == 31, 'PDF_PAGE_COUNT')
    need('Learning mode: one note per metronome click through the complete circuit.' in lines,
         'LEARNING_MODE_MISSING')
    need(any('Remove the pauses while retaining a light accent on each new module root.' in row
             for row in lines),
         'CONTINUOUS_MODE_MISSING')
    need('LEARNING MODE' in pages[1] and
         any('one note per click' in row.lower() for row in pages[1]),
         'PDF_LEARNING_MODE_MISSING')
    need(any('Remove the pauses' in row for row in pages[0]), 'PDF_CONTINUITY_MISSING')
    for midx, (module, prior) in enumerate(zip(modules, proposal), 1):
        need(module['module_number'] == midx and module['pdf_page'] == (3 if midx <= 3 else 4),
             'SOURCE_MODULE_ORDER')
        a, b = module['txt_line_span']
        need(prior['schema1_fields']['context']['circuit_contact_ordinals'] ==
             [BOUNDARIES[midx-1]+1, BOUNDARIES[midx]], 'P12_BOUNDARY')
        need(module['printed_heading'] == lines[a-1], 'TXT_MODULE_HEADING')
        page = pages[module['pdf_page']-1]
        for row in module['source_rows']:
            need(lines[row['txt_line']-1] == row['printed_row'] and row['printed_row'] in page,
                 'TXT_PDF_ROW_PARITY')
        fields = prior['schema1_fields']['events']
        need(len(fields) == len(module['contacts']), 'P12_CONTACT_COUNT')
        for local, (contact, field) in enumerate(zip(module['contacts'], fields), 1):
            degree = field['degree_contexts']['A-major']
            need((field['string'], field['fret'], field['finger'], field['midi'],
                  field['spelling'], degree['source_label']) ==
                 (STRINGS[contact['string']], contact['fret'], contact['printed_finger'],
                  OPEN_MIDI[contact['string']]+contact['fret'], contact['printed_note_spelling'],
                  str(contact['printed_degree'])), 'P12_CONTACT_PARITY')
            need(contact['ordinal_in_circuit'] == BOUNDARIES[midx-1]+local,
                 'SOURCE_CONTACT_ORDER')
            sr = contact['source_refs']
            need(lines[sr['txt_degree_line']-1].startswith('Deg|') and
                 lines[sr['txt_finger_line']-1].startswith('Fng|') and
                 lines[sr['txt_tab_line']-1].startswith(contact['string']+'  |'),
                 'CONTACT_SOURCE_ROWS')
        for group, pg in zip(module['groups'], prior['group_memberships']):
            need((group['contact_ordinals'], group['direction'],
                  group['printed_interval_or_harmony']) ==
                 (pg['event_local_ordinals'], pg['direction'],
                  pg['printed_interval_or_harmony']), 'P12_GROUP_PARITY')
        need(len(module['groups']) == len(prior['group_memberships']), 'P12_GROUP_COUNT')
    return lines, pages, modules, proposal

def derive(*, force_eligible=False, forced_bpm=None, grouping='source_event_time'):
    need(not force_eligible, 'FORCED_ELIGIBILITY')
    need(forced_bpm is None, 'FIXED_BPM_UNAUTHORIZED')
    need(grouping == 'source_event_time', 'LEARNING_TIME_REQUIRED')
    audit = read(OUT/'identity-audit.json')
    need(audit['status'] == 'PASS' and not audit['matches'] and
         audit['wanted'] == [ITEM, MODULE, *VARIANTS], 'IDENTITY_AUDIT_DRIFT')
    lines, pages, modules, proposal = source_facts()
    refs = (['L20-TXT-GUIDANCE', 'L20-PDF-PROTOCOL', 'L20-PDF-ROUTE'] +
            [f'L20-TXT-A-MODULE{i}' for i in range(1,6)] +
            ['L20-PDF-A-MODULES1-3', 'L20-PDF-A-MODULES4-5'])
    sources = {
        refs[0]: source_ref(TXT, 'txt', '\n'.join(lines[:75]), first_line=1, last_line=75),
        refs[1]: source_ref(PDF, 'pdf', '\n'.join(pages[0]), page=1),
        refs[2]: source_ref(PDF, 'pdf', '\n'.join(pages[1]), page=2),
        refs[8]: source_ref(PDF, 'pdf', '\n'.join(pages[2]), page=3),
        refs[9]: source_ref(PDF, 'pdf', '\n'.join(pages[3]), page=4),
    }
    for midx, module in enumerate(modules, 1):
        a, b = module['txt_line_span']
        sources[refs[midx+2]] = source_ref(TXT, 'txt', '\n'.join(lines[a-1:b]),
                                          first_line=a, last_line=b)
    base_package, base_registry, base_profile = (
        read(BASE/name) for name in ('package.json', 'identity-registry.json', 'expected-profile.json'))
    events, sidecar, event_sources = [], {}, {}
    for midx, (module, prior) in enumerate(zip(modules, proposal), 1):
        for local, (contact, field) in enumerate(zip(module['contacts'],
                                                     prior['schema1_fields']['events']), 1):
            ordinal = contact['ordinal_in_circuit']
            eid = f'{ITEM}:event:{ordinal:04d}'
            event = copy.deepcopy(field)
            event.update(event_id=eid, onset_q=[ordinal-1,1], duration_q=[1,1])
            # The linear card prints 1–7 again above the octave. P12 carries
            # 8–15 scale-step ordinals for those contacts; the native degree
            # contract pairs ordinal with the *printed* degree label instead.
            # Retain the distinct octave/scale step below in provenance.
            event['degree_contexts']['A-major']['ordinal'] = contact['printed_degree']
            events.append(event)
            txt_ref = refs[midx+2]
            pdf_ref = refs[8 if midx <= 3 else 9]
            event_sources[eid] = txt_ref
            group = next(g for g in module['groups'] if local in g['contact_ordinals'])
            sidecar[eid] = {
                'source_local_event_key': f'L020-R01:A:CIRCUIT:M{midx}:{local:03d}',
                'source_txt_ref': txt_ref, 'source_pdf_ref': pdf_ref,
                'source_txt_lines': contact['source_refs'],
                'source_pdf_page': module['pdf_page'],
                'source_module': midx, 'source_module_contact': local,
                'source_circuit_contact': ordinal, 'source_group': group['group'],
                'source_group_direction': group['direction'],
                'source_group_slot': group['contact_ordinals'].index(local)+1,
                'printed_interval_or_harmony': contact['printed_interval_or_harmony'],
                'printed_note_spelling': contact['printed_note_spelling'],
                'printed_degree': contact['printed_degree'],
                'scale_step': contact['scale_step'],
                'p12_scale_step_ordinal': field['degree_contexts']['A-major']['ordinal'],
                'printed_finger': contact['printed_finger'],
                'string_label': contact['string'], 'string': field['string'],
                'fret': contact['fret'], 'midi': field['midi'],
                'distinct_source_contact': ordinal,
                'rearticulated_module_root': local == 1 and midx > 1,
                'same_root_as_previous_contact': local == 1 and midx > 1 and
                    (contact['string'],contact['fret']) ==
                    (modules[midx-2]['contacts'][-1]['string'],
                     modules[midx-2]['contacts'][-1]['fret']),
                'timing_txt_ref': refs[0], 'timing_pdf_ref': refs[2],
                'nominal_slot_q': [ordinal-1,1],
                'selected_mode': 'one_sequential_note_per_click',
                'native_pulse_guidance_unselected': module['printed_pulse_description'],
            }
    need(len(events) == len(sidecar) == 322 and len(set(event_sources)) == 322,
         'EVENT_PROVENANCE_COVERAGE')
    need([(events[i]['onset_q'],events[i]['duration_q']) for i in (30,108,204,256,321)] ==
         [([i,1],[1,1]) for i in (30,108,204,256,321)], 'BOUNDARY_TIMING')
    strokes = {}
    variants = []
    for vid, start in zip(VARIANTS, ('D','U')):
        strokes[vid] = [start if i % 2 == 0 else ('U' if start == 'D' else 'D')
                        for i in range(322)]
        variants.append({'id': vid, 'label': f'l020-r01-a-full-circuit-{start}-start',
                         'role':'notation_practice','route':'complete_a_major_five_module_circuit',
                         'source_refs':refs,'event_ids':list(event_sources),
                         'pick_start':start,'pick_start_origin':'source_authored',
                         'grouping':{'kind':'source_event_time','notes_per_beat':None,
                                     'beat_unit_q':None,'marking_factor':[1,1],
                                     'source_label':'Original Level20 learning mode: one sequential picked contact per metronome click; no module pauses'},
                         'accent_policy':'source_unspecified','tail_pause':None,'unresolved':[]})
    title = 'Level 20 Rung01 A-major complete 322-contact synthesis circuit'
    record = {'id':ITEM,'module_id':MODULE,'workbook_id':WORKBOOK,
              'content_revision':1,'lineage':{'kind':'new'},'kind':'notation',
              'legacy_level':20,'status':'converted_candidate','runtime_eligible':False,
              'title':title,'source_refs':refs,'authored_text_refs':refs,
              'events':events,'variants':variants,'resource_requirements':[],
              'rubric':None,'control_scope':{'extent':'complete_selected_case',
                  'local_case':'L020-R01:A:FULL_FIVE_MODULE_LEARNING_CIRCUIT',
                  'source_event_count':322,'basis_refs':refs,
                  'whole_workbook_complete':False,
                  'unresolved':['Rungs02-13 and 25-circuit route outside this case.',
                                'Runtime admission and whole Level20 remain Pending.']},
              'context':{'local_code':'L020-R01:A:FULL_FIVE_MODULE_LEARNING_CIRCUIT',
                         'route':'A-major modules 1-5 without stopping',
                         'position':'low-E root fret5; frame4-7; no shift in selected case',
                         'pick_start_variants':['D','U'],
                         'pick_start':'source-authored continuous D/U or U/D without reset at groups, strings, turns or modules',
                         'tuning_open_midi':[40,45,50,55,59,64],
                         'capo':0,'source_tempo_rules_ref':refs[0]},
              'timing':{'status':'source_defined','unit':'quarter','meter':None,
                        'basis':'Original Level20 learning mode one sequential picked note per click; continuous complete circuit; q322 terminal span. Native-pulse q113 is unselected.'},
              'ambiguities':['No fixed BPM, performed sustain/correctness, mastery or route completion inferred.',
                             'Capo zero is untransposed standard-tuning representation, not an authored capo instruction.'],
              'normalization':[{'kind':'representation_metadata','basis':refs[0],
                                'text':'One complete five-module A-major learning circuit; low roots re-articulated immediately at module boundaries.'}]}
    package = {k:copy.deepcopy(v) for k,v in base_package.items()
               if k not in ('records','sources','workbook_catalog')}
    package.update(content_version='curriculum-v1-level020-a-full-circuit-build-only.1',
                   records=[record],sources=sources)
    entities = [base_registry['entities'][0],
                {'id':WORKBOOK,'kind':'workbook','label':'Legacy Level20','parent':'fg:course:000001'},
                {'id':MODULE,'kind':'module','label':title,'parent':WORKBOOK},
                {'id':ITEM,'kind':'item','label':title,'parent':MODULE},
                *({'id':v['id'],'kind':'variant','label':v['label'],'parent':ITEM} for v in variants)]
    registry = {'identity_version':base_registry['identity_version'],
                'rules':base_registry['rules'],'entities':entities}
    identity_baseline = {'identity_version':registry['identity_version'],
                         'rules':registry['rules'],'entities':[entities[0]]}
    allocation_baseline = {'version':'control-allocation.1','authority':'P78 provisional only','records':{}}
    lineage_baseline = {'version':'lineage-baseline.1','records':{}}
    allocation = {'version':'control-allocation.1',
                  'authority':'P78 provisional nonadmitted; P02 canonical serial scan required',
                  'records':{ITEM:{'legacy_level':20,
                                   'occurrences':{row['source_local_event_key']:eid
                                                  for eid,row in sidecar.items()},
                                   'variants':{v['label']:v['id'] for v in variants}}}}
    profile = {k:copy.deepcopy(v) for k,v in base_profile.items()
               if k not in ('reference_package','reference_registry','event_sources',
                            'authority_artifacts','workbook_catalog')}
    profile['degree_roots']={'A-major':{'basis':'Original Level20 A-major Rung01 source card; pitch class only',
                                        'root_pitch_class':9}}
    profile.update(reference_package=package,reference_registry=registry,
                   event_sources=event_sources)
    profile['authority_artifacts']=[copy.deepcopy(a) for a in base_profile['authority_artifacts']
                                     if a['role'] in ('source_manifest','source_acceptance',
                                                      'current_schema_freeze')]
    for role,name,value in (('identity_baseline','identity-baseline.json',identity_baseline),
                            ('allocation_baseline','allocation-baseline.json',allocation_baseline),
                            ('lineage_baseline','lineage-baseline.json',lineage_baseline),
                            ('candidate_identity_allocation','candidate-allocation.json',allocation)):
        profile['authority_artifacts'].append({'path':str(OUT/name),'role':role,
                                               'sha256':sha(encode(value))})
    summary = {'status':'source_interpreted_nonadmitted_reference',
               'record_count':1,'event_count':322,'variant_count':2,
               'projected_membership_target':644,'item_id':ITEM,'module_id':MODULE,
               'variant_ids':list(VARIANTS),'runtime_eligible':False,'admitted':False,
               'whole_workbook_complete':False,'case_end_q':[322,1],
               'module_boundaries_before_events':[31,109,205,257],
               'module_boundary_q':[30,108,204,256],
               'source_txt_sha256':PINS[TXT],'source_pdf_sha256':PINS[PDF],
               'p05_parity_sha256':PINS[P05],'p12_parity_sha256':PINS[P12],
               'identity_audit_sha256':sha((ROOT/OUT/'identity-audit.json').read_bytes()),
               'interpretation':'A-major complete 322-contact five-module circuit; learning mode one sequential picked contact per click; continuous alternating pick and no module pauses; native-pulse q113 unselected.'}
    return {'package.json':package,'identity-registry.json':registry,
            'expected-profile.json':profile,'candidate-allocation.json':allocation,
            'identity-baseline.json':identity_baseline,
            'allocation-baseline.json':allocation_baseline,
            'lineage-baseline.json':lineage_baseline,
            'source-provenance.json':{'source_txt_refs':[refs[0],*refs[3:8]],
                                      'source_pdf_refs':[refs[1],refs[2],refs[8],refs[9]],
                                      'events':sidecar,'variant_strokes':strokes,
                                      'stroke_basis':'Original Level20 continuous D/U or U/D through all five even-sized modules.'},
            'summary.json':summary}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('audit','build','verify'))
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    dest, allowed = (ROOT/args.out).resolve(), (ROOT/OUT).resolve()
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
            need((dest/name).read_bytes() == encode(output[name]), 'OUTPUT_DRIFT:'+name)
    print(json.dumps(output['summary.json'], sort_keys=True))

if __name__ == '__main__':
    main()
