#!/usr/bin/env python3
"""Add finite degree-pass and paired-cadence tasks, preserving every source note."""
import copy
import datetime
import hashlib
import json
import re
import resource
import time
from pathlib import Path
import pdfplumber
import tasks

ROOT = Path(__file__).resolve().parents[3]
LANE = 'fullscope-private-a-r01'
OLD, OUT = [ROOT / f'Build/{LANE}/level039-{r}' for r in ('r04', 'r05')]
RES = ROOT / f'Results/{LANE}/level039-r05'
PROMPT = ROOT / f'Prompts/{LANE}/level039-task-passes-r01/full-template-prompt.md'
CHANGED = list(range(6, 11)) + list(range(18, 28))


def ref(path):
    path = Path(path)
    return {'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def dump(path, value):
    with path.open('x') as out:
        json.dump(value, out, indent=2, ensure_ascii=False)
        out.write('\n')


def main():
    start = datetime.datetime.now(datetime.timezone.utc)
    timer = time.perf_counter()
    assert ref(OLD / 'packet.jsonl')['sha256'] == '59cd7f5d6194f9d8f15f6f75353bf0529d15a509321a92ab1844919659724abe'
    prior_manifest = ROOT / f'Results/{LANE}/level039-r04/artifact-manifest.json'
    assert ref(prior_manifest)['sha256'] == '8069bdd07c635969fe75301cced64416774d73329d5cfdd3a1c275a80a1d22ad'
    assert ref(PROMPT)['sha256'] == '7e72fb8c9c5f520705bf5447e165aecf5330a9f082d4046914a844e3771d5185'
    if OUT.exists() or RES.exists():
        raise FileExistsError('Fresh output roots required; no overwrite')
    raw = (OLD / 'packet.jsonl').read_text().splitlines(keepends=True)
    records = [json.loads(s) for s in raw]
    original_records = copy.deepcopy(records)
    originals = [{k: v for k, v in x.items() if k != 'locator'} for x in records[5]['source_refs'][:2]]
    assert all(ref(ROOT / x['path']) == x for x in originals)
    text = (ROOT / originals[0]['path']).read_text().splitlines()
    panels = {}
    with pdfplumber.open(ROOT / originals[1]['path']) as pdf:
        pages = {n: pdf.pages[n - 1].extract_text() for n in (1, 2, 4, 5, 9, 12)}
        root_heading = next(w for w in pdf.pages[1].extract_words() if w['text'] == 'Root-location')
        root_box = (root_heading['x0'] - 1, root_heading['top'] - 1, pdf.pages[1].width, 580)
        root_context = pdf.pages[1].crop(root_box).extract_text()
        page = pdf.pages[8]
        headings = [w for w in page.extract_words() if w['text'] in ['P1', 'P2', 'P3', 'P4', 'P5']]
        assert len(headings) == 5
        for heading in headings:
            left = heading['x0'] < page.width / 2
            later = [w['top'] for w in headings if (w['x0'] < page.width / 2) == left and w['top'] > heading['top']]
            bottom = min(later) if later else min(w['top'] for w in page.extract_words() if w['text'] == 'Do')
            box = (0 if left else page.width / 2, heading['top'] - 1,
                   page.width / 2 if left else page.width, bottom - 1)
            panel = page.crop(box).extract_text()
            assert panel.startswith(heading['text'] + ' - common seed')
            panels[heading['text']] = {'bbox': box, 'text': panel}
    normalized = {n: ' '.join(s.split()) for n, s in pages.items()}
    normalized[2] += ' ' + ' '.join(root_context.split())
    for n, phrase in [(2, 'Before every phrase, point to the nearest F# root.'),
                      (2, 'After the phrase, sing F# without touching the guitar. Then verify it on the instrument.'),
                      (4, 'Accent only F# roots'), (9, 'Play the pair back to back'),
                      (9, 'call the destination at the last possible moment.'),
                      (9, 'Do not add extra notes after the cadence.'),
                      (9, 'Silence is part of the proof'),
                      (12, 'Loop the final two notes alone, then attach only the last two notes of the shared seed.')]:
        assert phrase in normalized[n], (n, phrase)
    assert 'Play each established 24-note vertical cell on separate passes: A-major degree names, F#-minor degree names, then F#-root accents.' in text
    audit = []
    checks = 9
    b_grid_checks = e_grid_checks = 0
    for row in CHANGED:
        record = records[row - 1]
        before = original_records[row - 1]
        loc = record['source_refs'][0]['locator']
        assert text[loc['line_start'] - 1:loc['line_end']] == record['source_payload']['exact_unit_lines']
        block = record['source_payload']['notation_blocks'][0]
        notation = {r['label']: r['body'] for r in block['notation_rows']}
        if row <= 10:
            page_number = 4 if row <= 7 else 5
            local_index = row - (6 if row <= 7 else 8)
            for label in ('Nte', 'AMj', 'F#m', 'Fng', 'e', 'B', 'G', 'D', 'A', 'E'):
                found = re.findall(r'^' + re.escape(label) + r'\|([^\s]+)', pages[page_number], re.M)
                assert found[local_index] == notation[label], (row, label)
                b_grid_checks += 1
            contract = tasks.box(before)
            assert tasks.validate(contract, before)
            field = 'source_task_passes'
        else:
            partner_row = row + 1 if row % 2 == 0 else row - 1
            partner = original_records[partner_row - 1]
            binding = {'packet': ref(OLD / 'packet.jsonl'), 'line': partner_row,
                       'package_key': partner['package_key'], 'source_identity': partner['source_identity'],
                       'record_canonical_sha256': tasks.digest(partner)}
            contract = tasks.cadence(before, partner, binding)
            assert tasks.validate(contract, before, partner, binding)
            field = 'source_cadence_relationship'
            panel = panels[contract['position_label']]['text']
            a, sharp = panel.split('A CADENCE\n', 1)[1].split('F# CADENCE\n', 1)
            chosen = a if contract['center'] == 'A' else sharp
            pdf_notation = dict(re.findall(r'^(Nte|F#m|[eBGDAE])\|([^\s]+)', chosen, re.M))
            expected_labels = {'Nte', 'F#m'} | {label for label in ('e', 'B', 'G', 'D', 'A', 'E') if re.search(r'\d', notation[label])}
            assert set(pdf_notation) == expected_labels, (row, pdf_notation, expected_labels)
            for label, body in pdf_notation.items():
                assert body == notation[label], (row, label)
                e_grid_checks += 1
        contract['source_authority'] = {'originals': originals, 'txt_unit_locator': loc,
                                        'pdf_physical_pages': [2, 4, 5] if row <= 10 else [2, 9, 12],
                                        'selection': 'source task order and physical-note relationships only'}
        record['implementation'][field] = contract
        record['provenance']['source_task_pass_supplement'] = {
            'predecessor_packet': ref(OLD / 'packet.jsonl'), 'predecessor_record_sha256': tasks.digest(before),
            'producer': ref(Path(__file__)), 'task_code': ref(Path(__file__).with_name('tasks.py')),
            'source_originals': originals, 'independent_review': False}
        assert {k: v for k, v in record['implementation'].items() if k != field} == before['implementation']
        for key in ('source_payload', 'timing_authority', 'status', 'unresolved_reasons', 'capabilities'):
            assert record[key] == before[key]
        checks += 8
        audit.append({'row': row, 'package_key': record['package_key'], 'source_identity': record['source_identity'],
                      'prior_record_canonical_sha256': tasks.digest(before), 'new_record_canonical_sha256': tasks.digest(record),
                      'added_contract': field, 'existing_payload_timing_status_unchanged': True})
    assert len(records) == 37 and sum(len(r['implementation']['ordered_contacts']) for r in records) == 386
    OUT.mkdir()
    RES.mkdir()
    dump(OUT / 'original-task-context.json', {'source_originals': originals, 'full_pdf_pages': pages,
         'cadence_panels': panels, 'root_location_column': {'bbox': root_box, 'text': root_context},
         'pdf_coverage_note': 'B all ten grid rows; E all five printed grids using source heading-derived panel boxes. TXT-only AMj/Fng and empty strings are retained, not claimed PDF-present.',
         'exploratory_note': 'An initial read-only crop trial exceeded the landscape page height and was refused. First producer attempt refused the interleaved PDF2 sentence before creating outputs. Final guidance extraction uses its actual column; final cadence boxes derive from source headings and page dimensions.'})
    dump(OUT / 'changed-key-audit.json', audit)
    with (OUT / 'packet.jsonl').open('x') as out:
        for row, record in enumerate(records, 1):
            out.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n' if row in CHANGED else raw[row - 1])
    actual = (OUT / 'packet.jsonl').read_text().splitlines(keepends=True)
    assert all(actual[row - 1] == raw[row - 1] for row in range(1, 38) if row not in CHANGED)
    context = json.loads((OLD / 'level-source-context.json').read_text())
    context['finite_task_passes_and_cadences'] = {
        'rows': CHANGED, 'source': ref(OUT / 'original-task-context.json'),
        'box_task_passes': 15, 'box_pass_memberships': 360, 'cadence_pair_contracts': 5,
        'printed_workout_count_unchanged': 462, 'source_notes_timing_status_unchanged': True}
    dump(OUT / 'level-source-context.json', context)
    dump(OUT / 'remaining-keys.json', [])
    dump(RES / 'semantic-checks.json', {'status': 'PASS', 'preservation_instruction_checks': checks,
         'B_PDF_grid_rows_checked': b_grid_checks, 'E_PDF_grid_rows_checked': e_grid_checks,
         'changed_rows': CHANGED, 'unchanged_record_bytes': 22, 'literal_contacts': 386,
         'box_tasks': 5, 'box_task_passes': 15, 'box_pass_memberships': 360,
         'cadence_pair_contracts': 5, 'cadence_records': 10, 'conditional_repair_contracts': 10,
         'printed_workout_count_unchanged': 462, 'source_supported_implemented': 2,
         'partial_source_unresolved': 35, 'new_independent_native_integrated_accepted': 0})
    previous = json.loads((ROOT / f'Results/{LANE}/level039-r04/seal.json').read_text())
    inputs = {x['path']: x for x in previous['source_inputs']}
    for path in [OLD / 'packet.jsonl', OLD / 'level-source-context.json', prior_manifest, PROMPT,
                 Path(__file__), Path(__file__).with_name('tasks.py'), OUT / 'original-task-context.json', OUT / 'changed-key-audit.json']:
        entry = ref(path)
        inputs[entry['path']] = entry
    seal = {**previous, 'started_utc': start.isoformat(), 'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'elapsed_seconds': time.perf_counter() - timer, 'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'packet': ref(OUT / 'packet.jsonl'), 'context': ref(OUT / 'level-source-context.json'),
            'remaining_keys_reference': ref(OUT / 'remaining-keys.json'), 'source_inputs': list(inputs.values()),
            'targeted_checks': ref(RES / 'semantic-checks.json'),
            'command': 'Bundled Python -B Tools/fullscope-private-a-r01/level039-task-passes-r01/produce.py',
            'limits': 'Finite source task relationships only. All original clocks/gates/drone realizations and readiness unchanged. No automatic learner response, partner call or credit.'}
    dump(RES / 'seal.json', seal)
    (RES / 'handoff.md').write_text('# Level 39 r05 — degree passes and cadence relationships\n\n'
        'Five Module B rows 6–10 now expose fifteen separate source passes: degree reading in each tonic followed by F#-only root accents. Their 120 printed contacts yield 360 pass memberships, without changing the source workout count. Repeated high endpoints and all printed fingers stay intact.\n\n'
        'Ten Module E rows 18–27 bind five same-position cadence pairs to their exact immutable predecessors. Each preserves the four-note physical seed and two-note destination, back-to-back practice, later externally called destination, qualitative postcadence silence, and the conditional final-two/last-two-seed repair. No partner call, branch, repeated performance, note release time or sung pitch is generated. The original page 2 point/sing/verify duty is retained as a manual instruction.\n\n'
        'All 37 identities, 386 literal contacts and 462 written source-workout count remain. Twenty-two unrelated record bytes are identical. Counts remain 2 complete private contracts and 35 partial. Numeric phrase timing/gates and drone rendering remain unavailable; no source independent acceptance, native/integrated/Accepted or learner credit is added. App/native/GUI/performance checks NOT_RUN. Producer remains OPEN_CONTINUING_IMPLEMENTATION_BACKLOG.\n')
    print(json.dumps({'packet': seal['packet'], 'checks': checks + b_grid_checks + e_grid_checks,
                      'runtime_seconds': seal['elapsed_seconds'], 'peak_rss_bytes': seal['process_peak_rss_bytes']}))


if __name__ == '__main__':
    main()
