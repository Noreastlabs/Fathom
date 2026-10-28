#!/usr/bin/env python3
"""Source expressive constraints/recovery actions; no selected pitch motion."""
import copy, datetime, hashlib, json, re, resource, time
from pathlib import Path
import pdfplumber
from actions import build as actions
from contracts import model, recovery
ROOT = Path(__file__).resolve().parents[3]
LANE = 'fullscope-private-a-r01'
OLD, OUT = [ROOT / f'Build/{LANE}/level048-{r}' for r in ('r12', 'r13')]
RES = ROOT / f'Results/{LANE}/level048-r13'
PROMPT = ROOT / f'Prompts/{LANE}/level048-expressive-recovery-actions-r01/full-template-prompt.md'


def ref(path):
    path = Path(path)
    return {'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def dump(path, value):
    with path.open('x') as out:
        json.dump(value, out, indent=2, ensure_ascii=False)
        out.write('\n')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def grid(body, width):
    if len(body) != width * 8:
        raise ValueError('Expected eight source count columns')
    return [[slot, token] for slot in range(8) if (token := body[slot * width:(slot + 1) * width].strip('-'))]


def main():
    start = datetime.datetime.now(datetime.timezone.utc)
    timer = time.perf_counter()
    assert ref(OLD / 'packet.jsonl')['sha256'] == 'c331702130db2efd5e43325a8232915a4f8621c0f4b687dabf702dd37bcecece'
    assert ref(PROMPT)['sha256'] == '4584ff592dcf7c5bc6265f0f65fa05535bda9b944c5712805daebe4be734f605'
    if OUT.exists() or RES.exists():
        raise FileExistsError('Fresh output roots required')
    raw = (OLD / 'packet.jsonl').read_text().splitlines(keepends=True)
    records = [json.loads(s) for s in raw]
    originals = [{k: v for k, v in x.items() if k != 'locator'} for x in records[24]['source_refs'][:2]]
    assert all(ref(ROOT / x['path']) == x for x in originals)
    text = (ROOT / originals[0]['path']).read_text().splitlines()
    with pdfplumber.open(ROOT / originals[1]['path']) as pdf:
        pages = {n: pdf.pages[n - 1].extract_text() for n in (14, 15, 19, 20)}
    additional = next(s for s in pages[19].splitlines() if s.startswith('Additional repairs:'))
    audit, mismatches = [], []
    checks, expressive = 0, 0
    counts = {'sounding_events': 0, 'picked_excitation_groups': 0, 'unpicked_arrivals': 0, 'holds': 0, 'rest_slots': 0}
    selected = [25, 45, 46, 47, 48, 49, 50]
    for row in selected:
        record = records[row - 1]
        before = copy.deepcopy(record)
        loc = record['source_refs'][0]['locator']
        assert text[loc['line_start'] - 1:loc['line_end']] == record['source_payload']['exact_unit_lines']
        checks += 1
        if row == 25 or row <= 47:
            for number, block in enumerate(record['source_payload']['notation_blocks'], 1):
                page = 14 + (number - 1) // 6 if row == 25 else 19
                card = (number - 1) % 6 if row == 25 else row - 45
                width, expected = (4, 6) if row == 25 else (3, 3)
                labels = ['Cnt', 'Nte', 'Rol', 'Atk', 'e', 'B', 'G', 'D', 'A', 'E'] + (['Deg', 'Col'] if row == 25 else [])
                for label in labels:
                    original = [r for r in block['notation_rows'] if r['label'] == label]
                    pdf_rows = re.findall(r'(?:^|\s)' + label + r'\|([^\s]+)', pages[page])
                    assert len(original) == 1 and len(pdf_rows) == expected
                    assert grid(original[0]['body'], 5) == grid(pdf_rows[card], width), (row, number, label)
                    checks += 1
        action = actions(record, row)
        record['implementation']['symbolic_action_segments'] = action
        record['implementation']['source_gate_rule'] = action['source_gate_constraint']
        if row == 25:
            form = model(record)
            for bar in form['bars']:
                page = 14 + (bar['bar'] - 1) // 6
                assert f"{bar['bar']}. {bar['chord']} {bar['phrase_role']} - {bar['position']}" in pages[page]
                assert f"Beat-1 target: {bar['declared_beat_one_target']} root" in pages[page]
                checks += 2
            form['source_pdf'] = originals[1]
            form['physical_pages'] = [14, 15]
            record['implementation']['source_expressive_model'] = form
            mismatches.append({'row': row, 'package_key': record['package_key'], 'source_identity': record['source_identity'],
                'source_originals': originals, 'txt_line_locator': loc, 'physical_pdf_pages': [14, 15],
                'bar_discrepancies': form['source_guidance_reconciliation']})
            record['unresolved_reasons'].append({'field': 'model_G_beat_one_target_headings', 'code': 'SOURCE_UNRESOLVED',
                'reason': 'Both originals label bar2/4/6/8 beat-one targets A/A/D/A, while written downbeats are G/G/C/G and the named targets occur later. Literal headings/events retained; no pitch/timing repair, Curriculum reconciliation pending.'})
        else:
            task = recovery(record, row, action)
            task['source_coverage'] = {'full_written_grid_in_original_txt': True, 'original_pdf_page': 19,
                'full_written_grid_in_pdf': row <= 47, 'pdf_additional_repair_prose': additional if row >= 48 else None,
                'no_unavailable_pdf_grid_comparison_claimed': True}
            record['implementation']['source_recovery_actions'] = task
        record['provenance']['expressive_recovery_actions_supplement'] = {'predecessor': ref(OLD / 'packet.jsonl'),
            'producer': ref(Path(__file__)), 'action_code': ref(Path(__file__).with_name('actions.py')),
            'expression_code': ref(Path(__file__).with_name('expression.py')), 'contract_code': ref(Path(__file__).with_name('contracts.py')),
            'source_originals': originals, 'independent_review': False}
        assert record['implementation']['ordered_contacts'] == before['implementation']['ordered_contacts']
        assert record['implementation']['sounding_events'] == before['implementation']['sounding_events']
        assert record['source_payload'] == before['source_payload']
        assert record['unresolved_reasons'][:len(before['unresolved_reasons'])] == before['unresolved_reasons']
        assert record['status'] == before['status'] and record['timing_authority'] == before['timing_authority']
        checks += 5
        for key, value in action['counts'].items():
            counts[key] += value
        expressive += sum('expressive_source_constraint' in a for a in action['actions'])
        audit.append({'row': row, 'package_key': record['package_key'], 'source_identity': record['source_identity'],
            'old_record_canonical_sha256': digest(before), 'new_record_canonical_sha256': digest(record),
            'source_counts': action['counts'], 'source_music_timing_status_unchanged': True,
            'expressive_constraints_unselected': sum('bend' in e for e in record['implementation']['sounding_events']),
            'new_source_guidance_reconciliation': row == 25})
    assert counts['sounding_events'] == 97 and counts['picked_excitation_groups'] == 69 and expressive == 4
    complete = [r for r in records if r['implementation'].get('sounding_events')]
    assert len(complete) == 38 and all(r['implementation'].get('symbolic_action_segments') for r in complete)
    assert sum(r['implementation']['symbolic_action_segments']['counts']['sounding_events'] for r in complete) == 614
    assert sum(r['implementation']['symbolic_action_segments']['counts']['picked_excitation_groups'] for r in complete) == 517
    OUT.mkdir()
    RES.mkdir()
    dump(OUT / 'original-expressive-recovery-pages.json', {'source_pdf': originals[1], 'pages': pages,
        'source_coverage_note': 'PDF19 contains first three written recovery grids plus prose for remaining three. Their exact grids are TXT-only; no PDF literal-grid claim for rows48–50.'})
    dump(OUT / 'changed-key-audit.json', audit)
    dump(OUT / 'source-model-g-target-mismatches.json', mismatches)
    with (OUT / 'packet.jsonl').open('x') as out:
        for number, record in enumerate(records, 1):
            out.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n' if number in selected else raw[number - 1])
    actual = (OUT / 'packet.jsonl').read_text().splitlines(keepends=True)
    assert all(actual[n - 1] == raw[n - 1] for n in range(1, 63) if n not in selected)
    context = json.loads((OLD / 'level-source-context.json').read_text())
    context['expressive_recovery_source_actions'] = {'rows': selected, 'source': ref(OUT / 'original-expressive-recovery-pages.json'),
        'source_guide_mismatches': ref(OUT / 'source-model-g-target-mismatches.json'),
        'all38_written_cards_have_symbolic_actions': True, 'source_sounding_events': 614, 'source_picked_attacks': 517,
        'expressive_trajectories_selected': 0, 'shuffle_ratio_selected': False}
    dump(OUT / 'level-source-context.json', context)
    dump(OUT / 'remaining-keys.json', [])
    info = {'status': 'PASS', 'source_grid_instruction_preservation_checks': checks, 'changed_rows': selected,
        'unchanged_record_bytes': 55, 'source_counts': counts, 'symbolic_slots': 144, 'expressive_constraints': 4,
        'all38_written_cards_symbolic_actions': True, 'all_written_sounding_events': 614, 'all_written_picked_attacks': 517,
        'new_target_guidance_discrepancies': 4, 'readiness_and_status_changes': 0, 'new_independent_native_integrated_accepted': 0}
    dump(RES / 'semantic-checks.json', info)
    previous = json.loads((ROOT / f'Results/{LANE}/level048-r12/seal.json').read_text())
    inputs = {x['path']: x for x in previous['source_inputs']}
    for path in [OLD / 'packet.jsonl', OLD / 'level-source-context.json', PROMPT, Path(__file__),
        Path(__file__).with_name('actions.py'), Path(__file__).with_name('expression.py'), Path(__file__).with_name('contracts.py'),
        OUT / 'original-expressive-recovery-pages.json', OUT / 'changed-key-audit.json', OUT / 'source-model-g-target-mismatches.json']:
        entry = ref(path)
        inputs[entry['path']] = entry
    seal = {**previous, 'started_utc': start.isoformat(), 'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'elapsed_seconds': time.perf_counter() - timer, 'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'packet': ref(OUT / 'packet.jsonl'), 'context': ref(OUT / 'level-source-context.json'),
        'remaining_keys_reference': ref(OUT / 'remaining-keys.json'), 'source_inputs': list(inputs.values()),
        'targeted_checks': ref(RES / 'semantic-checks.json'),
        'command': 'Bundled Python -B Tools/fullscope-private-a-r01/level048-expressive-recovery-actions-r01/produce.py',
        'limits': 'Symbolic expression/recovery only, all four expressive trajectories and shuffle projection unselected; source guidance discrepancies retained, no acceptance or native claim.'}
    dump(RES / 'seal.json', seal)
    (RES / 'handoff.md').write_text('# Level48 r13 — expressive/recovery source actions\n\n'
        'Seven exact rows25/45–50 add97 source events/69 picked groups across144 symbolic slots. Full bend and blue-third shade events each start one picked excitation with unchanged physical/target/direction constraints; all four source expressive trajectories remain unselected, with fixed scalar playback forbidden. Six recovery examples retain printed attacks and manual conditional duties, with no detected learner errors or automatic branch execution.\n\n'
        'All38 written cards now have symbolic action contracts totaling614 sounding events/517 picked groups. This does not resolve numeric shuffle timing or expressive/acoustic curves. Counts remain3manual/21choice/38partial and native/integrated/Accepted remain zero.55 unrelated records are byte-identical; all original events, source payloads, timing and status flags persist.\n\n'
        'ModuleG bar2/4/6/8 target headings name beat-one A/A/D/A but both originals print G/G/C/G downbeats and later target arrivals. These four discrepancies stay explicit in one unresolved row; no source repair is applied. PDF19 has only the first three recovery grids; last three exact grids are TXT-only and the related PDF repair prose is preserved. Native/app/GUI/performance checks NOT_RUN.\n')
    print(json.dumps({'packet': seal['packet'], 'source_counts': counts, 'checks': checks, 'expressive_constraints': expressive,
        'runtime_seconds': seal['elapsed_seconds'], 'peak_rss_bytes': seal['process_peak_rss_bytes']}))


if __name__ == '__main__':
    main()
