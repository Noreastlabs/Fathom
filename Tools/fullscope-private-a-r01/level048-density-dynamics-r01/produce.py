#!/usr/bin/env python3
"""Source-supported private Modules D/E actions, density and qualitative dynamics."""
import copy, datetime, hashlib, json, re, resource, time
from pathlib import Path
import pdfplumber
from actions import build
from shapes import density, dynamics

ROOT = Path(__file__).resolve().parents[3]
LANE = 'fullscope-private-a-r01'
OLD = ROOT / f'Build/{LANE}/level048-r08'
OUT = ROOT / f'Build/{LANE}/level048-r09'
RES = ROOT / f'Results/{LANE}/level048-r09'
PROMPT = ROOT / f'Prompts/{LANE}/level048-density-dynamics-r01/full-template-prompt.md'


def ref(path):
    path = Path(path)
    return {'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def dump(path, value):
    with path.open('x') as out:
        json.dump(value, out, ensure_ascii=False, indent=2)
        out.write('\n')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def normalized_grid(line, step):
    result = []
    for bar, part in enumerate(line.strip().split('|')[1:], 1):
        for match in re.finditer(r'[^-]+', part):
            if match.start() % step:
                raise ValueError('Original grid token not aligned with source count columns')
            result.append([bar, match.start() // step, match.group()])
    return result


def main():
    start = datetime.datetime.now(datetime.timezone.utc)
    timer = time.perf_counter()
    assert ref(OLD / 'packet.jsonl')['sha256'] == '5a18644aad82045777e2564bd1a21530ead44f8be9983fa81ae4e125397edd97'
    assert ref(PROMPT)['sha256'] == '6033e2423656eb5300286a484069acfa054dbd43a460a818ff9403519ec1f745'
    if OUT.exists() or RES.exists():
        raise FileExistsError('Fresh batch roots required')
    raw = (OLD / 'packet.jsonl').read_text().splitlines(keepends=True)
    records = [json.loads(x) for x in raw]
    assert len(records) == 62
    sparse = copy.deepcopy(records[17])
    txt, pdf = [{k: v for k, v in x.items() if k != 'locator'} for x in sparse['source_refs'][:2]]
    assert ref(ROOT / txt['path']) == txt and ref(ROOT / pdf['path']) == pdf
    lines = (ROOT / txt['path']).read_text().splitlines()
    with pdfplumber.open(ROOT / pdf['path']) as document:
        pages = {n: document.pages[n - 1].extract_text() for n in (10, 11, 12)}
    counts = {'sounding_events': 0, 'picked_excitation_groups': 0, 'unpicked_arrivals': 0, 'holds': 0, 'rest_slots': 0}
    audit, mismatches = [], []
    checks = 0
    for row in range(18, 24):
        record = records[row - 1]
        before = copy.deepcopy(record)
        page = 10 if row < 21 else 11
        index = row - (18 if row < 21 else 21)
        step = 4 if row == 21 else 3
        loc = record['source_refs'][0]['locator']
        assert lines[loc['line_start'] - 1:loc['line_end']] == record['source_payload']['exact_unit_lines']
        checks += 1
        labels = ['Cnt', 'Nte', 'Rol', 'Atk', 'e', 'B', 'G', 'D', 'A', 'E'] + (['Dyn'] if row >= 21 else [])
        for label in labels:
            original = [s.strip() for s in record['source_payload']['exact_unit_lines'] if s.strip().startswith(label + '|')]
            pdf_rows = [s for s in pages[page].splitlines() if s.startswith(label + '|')]
            assert len(original) == 1 and len(pdf_rows) == 3
            assert normalized_grid(original[0], 4) == normalized_grid(pdf_rows[index], step), (row, label)
            checks += 1
        action = build(record, row)
        impl = record['implementation']
        impl['symbolic_action_segments'] = action
        impl['source_gate_rule'] = action['source_gate_constraint']
        if row < 21:
            shape = density(record, row, sparse)
            shape['target_comparison']['baseline_source_binding'] = {
                'packet': ref(OLD / 'packet.jsonl'), 'line': 18, 'record_canonical_sha256': digest(sparse)}
            shape['source_locator'] = {'pdf': pdf, 'physical_page': 10,
                                       'instruction': 'P1 -> P2 -> P3 -> P1.'}
            assert 'P1 -> P2 -> P3 -> P1.' in pages[10]
            impl['source_density_contract'] = shape
            if row == 20:
                mismatch = {'package_key': record['package_key'], 'source_identity': record['source_identity'],
                            'row': row, 'comparison': shape['target_comparison'], 'source_pdf': pdf,
                            'physical_page': 10, 'source_txt': txt, 'line_locator': loc}
                mismatches.append(mismatch)
                record['unresolved_reasons'].append({'field': 'density_bar3_target_schedule', 'code': 'SOURCE_UNRESOLVED',
                    'reason': 'Dense card says preserve target schedule but prints G (#9) on bar3 beat1 and G# (third) as an unpicked slide on the offbeat; sparse/medium put G# on beat1. Exact source retained; Curriculum reconciliation pending.'})
        else:
            shape = dynamics(record, row, action)
            shape['source_locator'] = {'pdf': pdf, 'physical_page': 11, 'txt': txt, 'line_locator': loc}
            route = ' -> '.join(p['source_position'] for p in shape['phrases']) + '.'
            assert route in pages[11]
            impl['source_dynamic_shape'] = shape
        record['provenance']['density_dynamic_supplement'] = {
            'previous_packet': ref(OLD / 'packet.jsonl'), 'producer': ref(Path(__file__)),
            'action_transducer': ref(Path(__file__).with_name('actions.py')),
            'shape_code': ref(Path(__file__).with_name('shapes.py')), 'source_originals': [txt, pdf],
            'independent_review': False}
        assert impl['ordered_contacts'] == before['implementation']['ordered_contacts']
        assert impl['sounding_events'] == before['implementation']['sounding_events']
        assert record['status'] == before['status'] and record['timing_authority'] == before['timing_authority']
        assert record['unresolved_reasons'][:len(before['unresolved_reasons'])] == before['unresolved_reasons']
        checks += 4
        for key, value in action['counts'].items():
            counts[key] += value
        audit.append({'row': row, 'package_key': record['package_key'], 'source_identity': record['source_identity'],
                      'original_record_canonical_sha256': digest(before), 'new_record_canonical_sha256': digest(record),
                      'source_counts': action['counts'], 'contacts_timing_status_unchanged': True,
                      'new_source_guidance_mismatches': int(row == 20)})
    assert counts['sounding_events'] == 120 and len(mismatches) == 1
    OUT.mkdir()
    RES.mkdir()
    dump(OUT / 'original-modules-de-pages.json', {'source_pdf': pdf, 'pages': pages,
         'extraction': 'Full original physical-page text and comparative grid-column audit; no raster observation claimed.'})
    dump(OUT / 'changed-key-audit.json', audit)
    dump(OUT / 'source-target-guidance-mismatch.json', mismatches)
    with (OUT / 'packet.jsonl').open('x') as out:
        for row, record in enumerate(records, 1):
            out.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n' if 18 <= row <= 23 else raw[row - 1])
    output = (OUT / 'packet.jsonl').read_text().splitlines(keepends=True)
    assert all(output[i - 1] == raw[i - 1] for i in range(1, 63) if not 18 <= i <= 23)
    context = json.loads((OLD / 'level-source-context.json').read_text())
    context['module_de_density_dynamics'] = {'source': ref(OUT / 'original-modules-de-pages.json'),
        'rows': list(range(18, 24)), 'guidance_mismatch': ref(OUT / 'source-target-guidance-mismatch.json'),
        'qualitative_dynamics_only': True, 'no_numeric_velocity_or_timing_selected': True}
    dump(OUT / 'level-source-context.json', context)
    dump(OUT / 'remaining-keys.json', [])
    info = {'status': 'PASS', 'source_checks': checks, 'changed_rows': list(range(18, 24)),
            'unchanged_record_bytes': 56, 'source_counts': counts, 'symbolic_slots': 192,
            'density_contracts': 3, 'dynamic_shape_contracts': 3, 'target_schedule_mismatches': 1,
            'source_events_generated': 0, 'readiness_change': 0, 'new_independent_native_integrated_accepted': 0}
    dump(RES / 'semantic-checks.json', info)
    previous = json.loads((ROOT / f'Results/{LANE}/level048-r08/seal.json').read_text())
    inputs = {x['path']: x for x in previous['source_inputs']}
    for path in [OLD / 'packet.jsonl', OLD / 'level-source-context.json', PROMPT, Path(__file__),
                 Path(__file__).with_name('actions.py'), Path(__file__).with_name('shapes.py'),
                 OUT / 'original-modules-de-pages.json', OUT / 'changed-key-audit.json', OUT / 'source-target-guidance-mismatch.json']:
        value = ref(path)
        inputs[value['path']] = value
    seal = {**previous, 'started_utc': start.isoformat(), 'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'elapsed_seconds': time.perf_counter() - timer, 'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'packet': ref(OUT / 'packet.jsonl'), 'context': ref(OUT / 'level-source-context.json'), 'source_inputs': list(inputs.values()),
            'remaining_keys_reference': ref(OUT / 'remaining-keys.json'), 'targeted_checks': ref(RES / 'semantic-checks.json'),
            'command': 'Bundled Python -B Tools/fullscope-private-a-r01/level048-density-dynamics-r01/produce.py',
            'limits': 'Source symbolic actions, exact density and qualitative dynamics only. One explicit source target-schedule seam retained. Clock/gate/native/admission remain unselected.'}
    dump(RES / 'seal.json', seal)
    (RES / 'handoff.md').write_text('# Level48 r09 — density and qualitative dynamic contracts\n\n'
        'Exact rows18–23 now bind192 symbolic slots to120 sounding events, source rest/hold/legato ownership, three density levels and three dynamic shapes. Dynamic p/mf/mp/f marks join each sounding and held slot; no numeric velocity or amplitude curve is invented. PDF position routes and constant pulse/subdivision duties are explicit.\n\n'
        'Row20 preserves the dense bar3 G-to-G# offbeat slide. The same-target-schedule prose is retained as SOURCE_GUIDANCE_RECONCILIATION_PENDING because sparse/medium begin bar3 on G#. No pitch/timing repair or source adjudication is applied. See the exact-key mismatch artifact.\n\n'
        'All62 identities remain;56 unrelated record byte sequences are unchanged. Counts remain3manual/21choice/38partial. Timing, acoustic gates, native execution, app/GUI, performance, admission and Accepted remain unclaimed/NOT_RUN. This is a private source-contract supplement, not executable playback or independent review.\n')
    print(json.dumps({'packet': seal['packet'], 'counts': counts, 'source_checks': checks,
                      'runtime_seconds': seal['elapsed_seconds'], 'peak_rss_bytes': seal['process_peak_rss_bytes']}))


if __name__ == '__main__':
    main()
