#!/usr/bin/env python3
"""Build a deterministic, detached Level 89 PDF/TXT source-mapping candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT_EXPECTED = Path(__file__).resolve().parents[1]
BUILD_REL = Path('Build/parallel-03/2.3.1.3.1-level089-source-music-r01')
MAP_DIR = Path('Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence')
COVERAGE_PATH = Path('Results/parallel-01/exercises/conversion/20260923T021155Z-2.3.1.3.1-pdf-txt-passage-coverage-r01-evidence/pdf-txt-coverage-report.json')
CATALOG_PATH = Path('Content/controls/curriculum-v1/package.json')
TXT_PATH = Path('Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XII_Level_89_Country_Americana_and_Hybrid_Picking_Groove_Alternating_Bass_Boom_Chuck_Train_Rhythm_Double_Stops_and_Controlled_Fills.txt')
PDF_PATH = Path('Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XII_Level_89_Country_Americana_and_Hybrid_Picking_Groove_Alternating_Bass_Boom_Chuck_Train_Rhythm_Double_Stops_and_Controlled_Fills.pdf')
EXPECTED = {
    TXT_PATH.as_posix(): (1459, '700365c24590c0579cff36906ad71434184f90146333dc9cee062b35ebd8e4df'),
    PDF_PATH.as_posix(): (26341, 'ffd3a2dbf7fe9c8f13c4006474ed965a24370af471d2a50601b924a5a356ea2c'),
    (MAP_DIR / 'curriculum-source-map.json').as_posix(): (199753, 'bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6'),
    (MAP_DIR / 'curriculum-source-map.tsv').as_posix(): (68536, 'f526ff4d9ce3bceaf9a7cc581a3ac2aee2c74917eba984dd57913adba574c123'),
    (MAP_DIR / 'source-inventory.json').as_posix(): (36518, '9c216852ddab1151745a9617f9ff3725a8fcd4608fd7d6915e8a04864bb54f73'),
    CATALOG_PATH.as_posix(): (24698658, '766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255'),
    COVERAGE_PATH.as_posix(): (3123277, '968318ab8d5559b742b2871e217d254fe424d6ee5efa72c084d91d44962b7631'),
}
PAGE_HEADINGS = [
    'Guitar Exercises - Section XII, Level 89', 'Reference - Right-Hand Roles',
    'Module A - Alternating Bass Independence', 'Module A - Alternating Bass with Chord Answers',
    'Module B - Boom-Chuck Balance', 'Module C - Train Rhythm',
    'Module C - Train-Rhythm Chord Integration', 'Module D - Hybrid-Picking Attack Balance',
    'Module E - Double-Stops and Sixths', 'Module E - Rhythmic Double-Stop Answers',
    'Module F - Bass-Run Approaches', 'Module F - Controlled Fill Windows',
    'Module G - Country/Americana Pocket Variations', 'Module G - Same Progression, Four Arrangements',
    'Module H - Study 1 - Boom-chuck two-step', 'Module H - Study 2 - Train-rhythm drive',
    'Module H - Study 3 - Hybrid-picking ballad', 'Module H - Study 4 - Fill-and-return',
    'Module I - Thirty-Two-Bar Country/Americana Capstone', 'Module J - Recovery, Mastery, and Roadmap',
]
PAGE_HASHES = [
    '2827ab8c06150f4252465cc8eaf559d666b6f0dcbe99f181886ee1b8bf778c67',
    'e9b353d3146cf8d274daeb4af4813b2bbb85cc3d292f665e82a7a6fb4b72cb9d',
    'e2fe19ae098203697cd69df25abc9669b91f194a1646ca3bf5359f18325d15d0',
    '565d112c4f12b47c4b2d4c4102c3a8b2d890113cbbd3a52abf106e608f3c5bf1',
    'd33c203bc1bb9693398af6971d0365d02cd53033d5da0d1e2ecc94e1ec24d6b9',
    '3baf5a733e31deccd4c2921701b7d4d3bac11d9d023208fb73ac1e33327d19f2',
    'f38cb044387f898c3d510bc69727968694518e6a46edbc748af7c93b04f13583',
    '965238ce766a473b6c6d042844bf1509e0b9634c1f5a2fbc76ab8506212e063f',
    '88171579fa5279325be86689a90002fee45ea3cad455357963f7dc87b9dd2487',
    '2e955ad7e443ba0fcea53e41adbaf9da4a214b9b051bb7519bab60052738f92e',
    'a7d008718f841980e22c9afe658946f5a3933be8adadb01bd5d70939a4941dbe',
    '5987f36d4a4a37d72dcb67b7248a3db1d025c6fcc6e50b4b6bd07fa33f101332',
    'aeee1b969acae8dbf1391eb86a4499869efc30e0ddcee660b372fbdabf01016d',
    'c4924a04cc341c0ae3a5d4dfce5e382aac7b96dbcb47c80de743a733748150fd',
    '295e1ae3d88154d7c47ef381e560146e41d5235e69bb36046c9d63d94fceece1',
    'fddca1854ec1c744d99b9bc75f28802a589dd72847871f91993920426cd3b4b3',
    'c24b47e7ef580bee7fe55821ba50841b2589579bdab3fa2a74d5b142c38a2d94',
    '75e387aeaa89d4339ae836e0f8d5170b5550d455a13daf73999436033bd696b1',
    'ec088814894d57b6e111be020db26fa11a9856cf4e75cc7f6a923e33c33f9bb8',
    'dde86a95baf86bd8d5d7460360335da72d11216323eaeea50243d10a0ea70354',
]
MODULES = [
    ('A','Alternating-bass independence',144), ('B','Boom-chuck and bass/chord balance',144),
    ('C','Train rhythm and muted subdivision',144), ('D','Hybrid-picking attack balance',128),
    ('E','Double-stops and sixths as rhythmic answers',128), ('F','Bass-run approaches and controlled fills',128),
    ('G','Country/Americana pocket variations',160), ('H','Four eight-bar groove studies',192),
    ('I','Thirty-two-bar country/Americana capstone',256), ('J','Recovery and pocket audit',64),
]


def sha(data: bytes | str) -> str:
    if isinstance(data, str): data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def fail(message: str) -> None:
    raise ValueError(message)


def no_symlink_path(root: Path, rel: Path) -> Path:
    cur = root
    for part in rel.parts:
        cur = cur / part
        if cur.is_symlink(): fail(f'symlink input path refused: {rel.as_posix()}')
    if not cur.is_file(): fail(f'non-regular or missing input: {rel.as_posix()}')
    return cur


def read_pinned(root: Path, rel: Path) -> tuple[bytes, dict[str, Any]]:
    p = no_symlink_path(root, rel)
    raw = p.read_bytes()
    expected = EXPECTED[rel.as_posix()]
    actual = (len(raw), sha(raw))
    if actual != expected:
        fail(f'stale or mismatched input {rel.as_posix()}: got {actual}, expected {expected}')
    return raw, {'path': rel.as_posix(), 'bytes': len(raw), 'sha256': sha(raw)}


def line_index(text: str) -> list[dict[str, Any]]:
    out, offset = [], 0
    for i, chunk in enumerate(text.splitlines(keepends=True), 1):
        body = chunk[:-1] if chunk.endswith('\n') else chunk
        out.append({'line_number': i, 'text': body, 'codepoint_span': [offset, offset + len(body)], 'sha256': sha(body)})
        offset += len(chunk)
    if not text or (text.endswith('\n') and out and out[-1]['line_number'] < len(text.splitlines())):
        pass
    return out


def find_header(lines: list[dict[str, Any]], header: list[str]) -> int:
    vals = [x['text'] for x in lines]
    for i in range(len(vals) - len(header) + 1):
        if vals[i:i+len(header)] == header: return i + len(header)
    fail(f'table header not found: {header}')


def table_rows(lines: list[dict[str, Any]], header: list[str], row_count: int, fields: int) -> list[list[dict[str, Any]]]:
    start = find_header(lines, header)
    cells = lines[start:start + row_count * fields]
    if len(cells) != row_count * fields:
        fail(f'table truncated after header {header}')
    return [cells[i:i+fields] for i in range(0, len(cells), fields)]


def token_spans(line: dict[str, Any], separators: str = r'\S+') -> list[dict[str, Any]]:
    text = line['text']; base = line['codepoint_span'][0]
    return [{'text': m.group(0), 'codepoint_span': [base + m.start(), base + m.end()], 'sha256': sha(m.group(0))}
            for m in re.finditer(separators, text)]


def field_ref(cell: dict[str, Any]) -> dict[str, Any]:
    return {'text': cell['text'], 'codepoint_span': cell['codepoint_span'], 'sha256': cell['sha256']}


def make_locator(page_no: int, module: str, row_id: str, field_name: str, token: dict[str, Any], page_hash: str) -> dict[str, Any]:
    prefix = f'src-l089-p{page_no:02d}-{module.lower()}-{row_id.lower()}-{field_name.lower()}'
    return {'source_locator': prefix, 'workbook_id': 'fg:workbook:000089', 'module': module,
            'page_number': page_no, 'page_text_sha256': page_hash, 'row': row_id, 'field': field_name,
            'literal': token['text'], 'codepoint_span': token['codepoint_span'], 'literal_sha256': token['sha256'],
            'canonical_id': None, 'canonical_identity': False, 'runtime_eligible': False,
            'temporal_semantics': 'source ordinal only; no onset or duration inferred'}


def build(root: Path) -> dict[str, Any]:
    if root.resolve() != ROOT_EXPECTED or root != ROOT_EXPECTED:
        fail('supplied --root must be the exact authoritative Git root')
    top = subprocess.run(['git','rev-parse','--show-toplevel'], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    if Path(top) != ROOT_EXPECTED: fail(f'Git root mismatch: {top}')

    input_manifest = []
    raw_by_path = {}
    for rel in EXPECTED:
        raw, meta = read_pinned(root, Path(rel)); raw_by_path[rel] = raw; input_manifest.append(meta)
    txt = raw_by_path[TXT_PATH.as_posix()].decode('utf-8')
    if b'\r' in raw_by_path[TXT_PATH.as_posix()] or not raw_by_path[TXT_PATH.as_posix()].endswith(b'\n'):
        fail('TXT must remain UTF-8/LF with terminal newline')
    txt_lines = line_index(txt)
    if len(txt_lines) != 42: fail(f'expected 42 TXT lines, found {len(txt_lines)}')

    map_doc = json.loads(raw_by_path[(MAP_DIR/'curriculum-source-map.json').as_posix()])
    map_rows = [r for r in map_doc['rows'] if r.get('level') == 89]
    if len(map_rows) != 1: fail('source map must have one Level 89 row')
    map_row = map_rows[0]
    if map_row.get('wbs_owner') != '2.3.1.3.1' or map_row.get('review') != 'Pending' or map_row.get('conversion_status') != 'not_converted' or map_row.get('admitted') is not False or map_row.get('runtime_eligible') is not False:
        fail('Level 89 source-map status drift')
    if (map_row.get('txt_path'),map_row.get('txt_bytes'),map_row.get('txt_sha256'),map_row.get('pdf_path'),map_row.get('pdf_bytes'),map_row.get('pdf_sha256')) != (TXT_PATH.as_posix(),1459,EXPECTED[TXT_PATH.as_posix()][1],PDF_PATH.as_posix(),26341,EXPECTED[PDF_PATH.as_posix()][1]):
        fail('source-map Level 89 source identities drift')
    inv_doc = json.loads(raw_by_path[(MAP_DIR/'source-inventory.json').as_posix()])
    # Inventory is a source-lineage binding; find the uniquely matching level/source identity recursively.
    inv_matches = []
    def walk(obj: Any):
        if isinstance(obj, dict):
            if obj.get('level') == 89 or obj.get('workbook_id') == 'fg:workbook:000089': inv_matches.append(obj)
            for v in obj.values(): walk(v)
        elif isinstance(obj, list):
            for v in obj: walk(v)
    walk(inv_doc)
    if not inv_matches: fail('Level 89 row absent from source inventory')
    inv_row = next((x for x in inv_doc.get('entries',[]) if x.get('level') == 89),None)
    if not inv_row or inv_row.get('bytes') != 1459 or inv_row.get('sha256') != EXPECTED[TXT_PATH.as_posix()][1] or inv_row.get('packaged') is not False:
        fail('source inventory Level 89 binding/status drift')
    package = json.loads(raw_by_path[CATALOG_PATH.as_posix()])
    if package.get('content_version') != 'curriculum-v1-level009-659-build-only-candidate.1': fail('catalog package version drift')
    catalog = package['workbook_catalog']['entries'][88]
    if catalog.get('workbook_id') != 'fg:workbook:000089' or catalog.get('review') != 'Pending' or catalog.get('conversion_status') != 'not_converted': fail('catalog Level 89 status drift')
    if any(catalog.get(k) is not False for k in ('admitted','imported','runtime_admitted','runtime_eligible','whole_workbook_complete')): fail('catalog admission state drift')
    if catalog.get('catalog_role') != 'read_only_source_preservation' or catalog.get('representative_status') != 'outside_representative_package': fail('catalog role drift')
    if catalog['txt']['path'] != TXT_PATH.as_posix() or catalog['pdf']['path'] != PDF_PATH.as_posix(): fail('catalog source paths drift')
    if catalog['pdf'].get('page_count') != 20 or catalog['pdf'].get('extraction') != {'engine':'pypdf','limitations':'Text extraction does not prove visual equivalence, notation, tables, diagrams, layout or rubric fidelity.','version':'6.10.0'}: fail('catalog PDF extraction authority drift')

    coverage_doc = json.loads(raw_by_path[COVERAGE_PATH.as_posix()])
    cov = [x for x in coverage_doc['workbooks'] if x.get('level') == 89]
    if len(cov) != 1 or cov[0].get('page_classification_counts') != {'no_exact_five_token_window_found':13,'partial_literal_overlap':7}: fail('lexical coverage classification drift')
    cov_pages = {x['page_number']: x for x in cov[0]['pages']}
    if len(cov_pages) != 20: fail('coverage page count drift')

    from pypdf import PdfReader, __version__ as pypdf_version
    if pypdf_version != '6.10.0': fail(f'pypdf version must be 6.10.0; found {pypdf_version}')
    reader = PdfReader(str(no_symlink_path(root, PDF_PATH)))
    if len(reader.pages) != 20: fail('live PDF page count must equal 20')
    page_texts = [p.extract_text() or '' for p in reader.pages]
    if len(catalog['pdf']['pages']) != 20: fail('catalog cache page count drift')
    pages = []
    page_lines: dict[int, list[dict[str, Any]]] = {}
    for i, (text, cached) in enumerate(zip(page_texts, catalog['pdf']['pages']), 1):
        h = sha(text)
        if cached.get('page_number') != i or cached.get('extracted_text') != text or cached.get('extracted_text_sha256') != h or h != PAGE_HASHES[i-1]:
            fail(f'live PDF/catalog extracted text mismatch on page {i}')
        lines = line_index(text); page_lines[i] = lines
        if not lines or lines[0]['text'] != PAGE_HEADINGS[i-1]: fail(f'page heading mismatch on page {i}')
        cv = cov_pages[i]
        pages.append({'page_number':i,'heading':PAGE_HEADINGS[i-1],'role':PAGE_HEADINGS[i-1],
                      'page_text_sha256':h,'catalog_page_sha256':cached['extracted_text_sha256'],
                      'lexical_coverage_classification':cv['classification'],
                      'lexical_coverage_matched_windows':cv['matched_window_count'],
                      'lexical_coverage_is_metadata_only':True,
                      'line_index':[{'line_number':x['line_number'],'codepoint_span':x['codepoint_span'],'sha256':x['sha256']} for x in lines]})

    # TXT exact literal structure; spans are Unicode code points in the decoded file.
    modules = []
    for idx, (code,name,count) in enumerate(MODULES, 12):
        line = txt_lines[idx-1]
        expected = f'{code}. {name} - {count} events'
        if line['text'] != expected: fail(f'TXT module declaration mismatch at line {idx}')
        modules.append({'module':code,'name':name,'declared_events':count,'txt_line':idx,
                        'literal':field_ref(line)})
    if sum(x[2] for x in MODULES) != 1488 or txt_lines[8]['text'] != 'COMPLETE WRITTEN WORKLOAD: 1488 events' or 'HARD STOP AFTER LEVEL 105' not in txt_lines[3]['text'] or not txt_lines[41]['text'].startswith('Level 90'):
        fail('TXT workload/hard-stop/Level 90 boundary mismatch')
    if page_lines[1][2]['text'].count('\x7f') != 5: fail('page 1 U+007F separator preservation mismatch')
    p1_rows=table_rows(page_lines[1],['Module','Exercise','Events'],10,3)
    for i,(row,(code,name,count)) in enumerate(zip(p1_rows,MODULES),1):
        if row[0]['text'] != code or row[1]['text'] != name or row[2]['text'] != str(count):
            fail(f'PDF page 1 module declaration differs from TXT at module {i}')
    if not any(page_lines[1][i]['text']=='TOTAL' and page_lines[1][i+1]['text']=='1488' for i in range(len(page_lines[1])-1)):
        fail('PDF page 1 total does not match the declared 1488')

    structures: dict[str, Any] = {}
    locators: list[dict[str, Any]] = []
    structures['p01_pdf_module_declarations']=[{'row':i,'module':field_ref(r[0]),'exercise':field_ref(r[1]),'events':field_ref(r[2])} for i,r in enumerate(p1_rows,1)]
    # Page 2 role reference table.
    rows = table_rows(page_lines[2], ['Symbol','Right hand','Typical job'], 5, 3)
    structures['p02_right_hand_roles'] = [{'symbol':field_ref(r[0]),'right_hand':field_ref(r[1]),'typical_job':field_ref(r[2])} for r in rows]
    role_map = {r[0]['text']: r[1]['text'] for r in rows}
    if role_map != {'P':'flat pick','m':'middle finger','a':'ring finger','x':'muted/dead contact','-':'air stroke / silence'}: fail('p2 role table mismatch')

    # A p3: ordered pitch-spelling tokens, with beat ordinals only.
    rows = table_rows(page_lines[3], ['Chord','Bass pattern','Count'], 8, 3)
    a3_rows = []
    for rowno,r in enumerate(rows,1):
        pitches = [x for x in re.finditer(r'[^-]+',r[1]['text'])]
        count_sequence = r[2]['text']
        count_tokens = [{'text':m.group(0),'codepoint_span':[r[2]['codepoint_span'][0]+m.start(),r[2]['codepoint_span'][0]+m.end()],'sha256':sha(m.group(0))} for m in re.finditer(r'\d+',count_sequence)]
        if len(pitches) != 4 or [x['text'] for x in count_tokens] != ['1','2','3','4']:
            fail(f'p3 A row {rowno} unexpected pattern/count')
        pitch_items=[]
        for beat,m in enumerate(pitches,1):
            t={'text':m.group(0),'codepoint_span':[r[1]['codepoint_span'][0]+m.start(),r[1]['codepoint_span'][0]+m.end()]}
            t['sha256']=sha(t['text']); t['count_label']=count_tokens[beat-1]
            t['chord_label']=field_ref(r[0]); pitch_items.append(t)
            loc=make_locator(3,'A',f'r{rowno:02d}',f'beat{beat:02d}',t,PAGE_HASHES[2])
            loc['row_context']={'chord':field_ref(r[0]),'count_label':count_tokens[beat-1],'printed_count_sequence':field_ref(r[2])}
            locators.append(loc)
        a3_rows.append({'row':rowno,'chord':field_ref(r[0]),'bass_pattern':field_ref(r[1]),'count':field_ref(r[2]),'pitch_spelling_targets':pitch_items})
    structures['p03_a_bass_patterns'] = a3_rows

    # A p4: exact four beat action cells per pattern.
    rows = table_rows(page_lines[4], ['Pattern','Beat 1','Beat 2','Beat 3','Beat 4'], 6, 5)
    structures['p04_a_chord_answers'] = [{'row':i,'pattern':field_ref(r[0]),'beat_actions':[field_ref(x) for x in r[1:]]} for i,r in enumerate(rows,1)]
    for i,r in enumerate(rows,1):
        for beat,cell in enumerate(r[1:],1): locators.append(make_locator(4,'A',f'r{i:02d}',f'beat{beat:02d}',cell,PAGE_HASHES[3]))

    # B p5: whitespace-delimited source pattern tokens (not onset data).
    rows = table_rows(page_lines[5], ['Cell','Pattern','Goal'], 6, 3)
    b_rows=[]
    for i,r in enumerate(rows,1):
        toks=token_spans(r[1]); b_rows.append({'row':i,'cell':field_ref(r[0]),'pattern':field_ref(r[1]),'ordered_pattern_slots':toks,'goal':field_ref(r[2])})
        for slot,t in enumerate(toks,1): locators.append(make_locator(5,'B',f'r{i:02d}',f'slot{slot:02d}',t,PAGE_HASHES[4]))
    if sum(len(x['ordered_pattern_slots']) for x in b_rows)!=28: fail('p5 pattern token count mismatch')
    structures['p05_b_patterns'] = b_rows

    # C p6: eight printed P/x contacts per grid.
    rows = table_rows(page_lines[6], ['Cell','Grid','Accent map'], 6, 3)
    c_rows=[]
    for i,r in enumerate(rows,1):
        toks=token_spans(r[1])
        if len(toks)!=8 or any(t['text'] not in ('P','x') for t in toks): fail(f'p6 grid row {i} malformed')
        for t in toks:
            t['role_reference']={'symbol':t['text'],**next(x for x in structures['p02_right_hand_roles'] if x['symbol']['text']==t['text'])}
        c_rows.append({'row':i,'cell':field_ref(r[0]),'grid':field_ref(r[1]),'contacts':toks,'accent_map':field_ref(r[2])})
        for slot,t in enumerate(toks,1): locators.append(make_locator(6,'C',f'r{i:02d}',f'contact{slot:02d}',t,PAGE_HASHES[5]))
    structures['p06_c_train_grids'] = c_rows
    structures['p07_c_chord_integration'] = [{'row':i,'progression':field_ref(r[0]),'bass_landmark':field_ref(r[1]),'chord_response':field_ref(r[2])} for i,r in enumerate(table_rows(page_lines[7],['Progression','Bass landmark','Chord response'],6,3),1)]

    # D/E pages retain literal table structures; E interpretation remains unresolved.
    structures['p08_d_attack_cells'] = [{'row':i,'cell':field_ref(r[0]),'string_order':field_ref(r[1]),'right_hand':field_ref(r[2])} for i,r in enumerate(table_rows(page_lines[8],['Cell','String order','Right hand'],8,3),1)]
    e_rows=table_rows(page_lines[9],['Key','Double-stop route','Function'],6,3)
    structures['p09_e_double_stop_routes']=[{'row':i,'key':field_ref(r[0]),'route_literal':field_ref(r[1]),'function':field_ref(r[2]),'interpretation':'unresolved_literal_route'} for i,r in enumerate(e_rows,1)]
    structures['p09_e_double_stop_routes'][0]['route_literal']['text'] == 'B3/e3 -> B5/e5 -> B7/e7' or fail('ambiguous E route changed')
    structures['p10_e_rhythmic_answers']=[{'row':i,'cell':field_ref(r[0]),'question':field_ref(r[1]),'answer_placement':field_ref(r[2])} for i,r in enumerate(table_rows(page_lines[10],['Cell','Question','Answer placement'],6,3),1)]

    # F p11 note spelling locators; rules remain literal.
    rows=table_rows(page_lines[11],['Destination','Bass run','Rule'],7,3)
    f_rows=[]
    for i,r in enumerate(rows,1):
        pitches=[m for m in re.finditer(r'[^-]+',r[1]['text'])]
        # A hyphen is a separator, except F# etc which are unaffected.
        if not pitches: fail(f'p11 run row {i} has no note tokens')
        items=[]
        for j,m in enumerate(pitches,1):
            t={'text':m.group(0),'codepoint_span':[r[1]['codepoint_span'][0]+m.start(),r[1]['codepoint_span'][0]+m.end()]}; t['sha256']=sha(t['text']); items.append(t)
            loc=make_locator(11,'F',f'r{i:02d}',f'note{j:02d}',t,PAGE_HASHES[10])
            loc['row_context']={'destination':field_ref(r[0]),'rule':field_ref(r[2])}
            locators.append(loc)
        f_rows.append({'row':i,'destination':field_ref(r[0]),'bass_run':field_ref(r[1]),'note_spelling_tokens':items,'rule':field_ref(r[2])})
    if sum(len(x['note_spelling_tokens']) for x in f_rows)!=30: fail('p11 note token count mismatch')
    structures['p11_f_bass_runs']=f_rows
    structures['p12_f_fill_windows']=[{'row':i,'window':field_ref(r[0]),'maximum_fill':field_ref(r[1]),'return_point':field_ref(r[2])} for i,r in enumerate(table_rows(page_lines[12],['Window','Maximum fill','Return point'],6,3),1)]

    structures['p13_g_pocket_variations']=[{'row':i,'pocket':field_ref(r[0]),'harmony_order':field_ref(r[1]),'primary_behavior':field_ref(r[2]),'bar_count':'not printed'} for i,r in enumerate(table_rows(page_lines[13],['Pocket','Harmony','Primary behavior'],8,3),1)]
    rows=table_rows(page_lines[14],['Version','Bass','Upper guitar','Fill'],4,4)
    progression_line=next(x for x in page_lines[14] if x['text']=='Use | G | C | D | G | for all four.')
    # Chords are tied to the explicit four-bar shared progression, repeated across each version.
    progression_tokens=[m for m in re.finditer(r'(?<=\|\s)([^|]+?)(?=\s*\|)', progression_line['text'])]
    # Use direct positions to avoid any ambiguity from the pipe delimiters.
    chord_fields=[]
    for chord in ['G','C','D','G']:
        found=next((m for m in re.finditer(r'(?<![A-Za-z0-9])'+re.escape(chord)+r'(?![A-Za-z0-9])',progression_line['text']) if m.start() not in [x['codepoint_span'][0]-progression_line['codepoint_span'][0] for x in chord_fields]),None)
        if found is None: fail('p14 progression chord span missing')
        ref={'text':chord,'codepoint_span':[progression_line['codepoint_span'][0]+found.start(),progression_line['codepoint_span'][0]+found.end()]}; ref['sha256']=sha(chord); chord_fields.append(ref)
    g14=[]
    for i,r in enumerate(rows,1):
        g14.append({'row':i,'version':field_ref(r[0]),'bass':field_ref(r[1]),'upper_guitar':field_ref(r[2]),'fill':field_ref(r[3]),'bars':[{'bar':bar,'harmony':chord_fields[bar-1]} for bar in range(1,5)]})
        for bar,chord in enumerate(chord_fields,1): locators.append(make_locator(14,'G',f'v{i:02d}-bar{bar:02d}','harmony',chord,PAGE_HASHES[13]))
    structures['p14_g_arrangements']=g14

    # H pages: explicit 8-bar harmony; pass requirements kept as separate source rows.
    h_struct=[]
    for page_no in range(15,19):
        lines=page_lines[page_no]
        progression=lines[1]
        chord_matches=list(re.finditer(r'\|\s*([^|]+?)\s*(?=\|)',progression['text']))
        if len(chord_matches)!=8: fail(f'p{page_no} expected eight harmony bar cells')
        bars=[]
        for barno,m in enumerate(chord_matches,1):
            chord=m.group(1)
            # Trim only the syntactic whitespace around a printed bar label.
            raw=progression['text']; start=m.start(1); end=m.end(1)
            while start<end and raw[start].isspace(): start+=1
            while end>start and raw[end-1].isspace(): end-=1
            ref={'text':raw[start:end],'codepoint_span':[progression['codepoint_span'][0]+start,progression['codepoint_span'][0]+end]}; ref['sha256']=sha(ref['text'])
            bars.append({'bar':barno,'harmony':ref})
            locators.append(make_locator(page_no,'H',f'study{page_no-14:02d}-bar{barno:02d}','harmony',ref,PAGE_HASHES[page_no-1]))
        pass_rows=table_rows(lines,['Pass','Requirement'],6,2)
        h_struct.append({'study':page_no-14,'page_number':page_no,'progression':field_ref(progression),'bars':bars,
                         'instruction':field_ref(lines[2]),'passes':[{'pass':field_ref(r[0]),'requirement':field_ref(r[1])} for r in pass_rows]})
    structures['p15_18_h_studies']=h_struct

    # I p19 eight 4-bar ranges; expand only the explicit ranges into bar locators.
    i_rows=table_rows(page_lines[19],['Bars','Harmony','Groove','Primary engine','Dynamic'],8,5)
    i_struct=[]
    for i,r in enumerate(i_rows,1):
        mm=re.fullmatch(r'(\d+)-(\d+)',r[0]['text'])
        if not mm: fail(f'p19 row {i} bar range malformed')
        lo,hi=map(int,mm.groups())
        if hi-lo!=3: fail(f'p19 row {i} is not a four-bar range')
        row={'row':i,'bars':field_ref(r[0]),'harmony':field_ref(r[1]),'groove':field_ref(r[2]),'primary_engine':field_ref(r[3]),'dynamic':field_ref(r[4]),'expanded_bars':[]}
        for bar in range(lo,hi+1):
            b={'bar':bar,'harmony':field_ref(r[1]),'section_row':i}; row['expanded_bars'].append(b)
            locators.append(make_locator(19,'I',f'r{i:02d}-bar{bar:02d}','harmony',field_ref(r[1]),PAGE_HASHES[18]))
        i_struct.append(row)
    structures['p19_i_capstone']=i_struct
    structures['p19_i_master_tempo_instruction'] = [field_ref(x) for x in page_lines[19] if x['text'].startswith('One master tempo')][0]
    j_rows=table_rows(page_lines[20],['Failure','Immediate repair'],8,2)
    mastery_idx=next(i for i,x in enumerate(page_lines[20]) if x['text'].startswith('Mastery:'))
    next_idx=next(i for i,x in enumerate(page_lines[20]) if x['text'].startswith('Next:'))
    roadmap_idx=next(i for i,x in enumerate(page_lines[20]) if x['text'].startswith('Fixed roadmap:'))
    structures['p20_j_recovery_mastery_roadmap']={'recovery_rows':[{'row':i,'failure':field_ref(r[0]),'immediate_repair':field_ref(r[1])} for i,r in enumerate(j_rows,1)],
       'mastery':field_ref(page_lines[20][mastery_idx]),'next_boundary':field_ref(page_lines[20][next_idx]),'fixed_roadmap':field_ref(page_lines[20][roadmap_idx]),
       'hard_stop':field_ref(next(x for x in page_lines[20] if x['text']=='Capstone. HARD STOP after 105.')),
       'status':'source_instruction_only_not_observed_learner_result'}

    if len(locators) != 32+24+28+48+30+16+32+32: fail(f'unexpected locator count: {len(locators)}')
    # All locator IDs must be unique and source-local.
    if len({x['source_locator'] for x in locators}) != len(locators): fail('duplicate source locator')
    return {
        'schema':'fathom.detached-source-mapping-candidate.v1',
        'workbook_id':'fg:workbook:000089','level':89,'section':'XII','wbs_owner':'2.3.1.3.1',
        'status':'pending_source_reconciliation','review':'Pending','canonical_ids_allocated':False,
        'canonical_record_emitted':False,'runtime_eligible':False,'imported':False,'admitted':False,
        'whole_workbook_complete':False,'playable_projection_emitted':False,
        'authority':{'original_txt_and_pdf_are_source_authority':True,'pdf_page_indices_authoritative':True,
                     'extracted_text_is_search_metadata_only':True,'canonical_catalog_role':catalog['catalog_role'],
                     'lexical_coverage_is_metadata_only':True,'prior_staged_outputs_opened_or_used':False},
        'input_identities':sorted(input_manifest,key=lambda x:x['path']),
        'source_bindings':{'map_row':{k:map_row[k] for k in ('level','section','wbs_owner','txt_path','txt_bytes','txt_sha256','pdf_path','pdf_bytes','pdf_sha256','pair_status','representative_status','review','conversion_status','stable_ids_assigned','runtime_eligible','imported','admitted','source_specific_ambiguities')},
                           'inventory_matches':len(inv_matches),'catalog_status':{k:catalog[k] for k in ('workbook_id','catalog_role','review','conversion_status','stable_identity_status','representative_status','whole_workbook_complete','runtime_eligible','imported','admitted','source_specific_ambiguities','unresolved_playable_fields')}},
        'txt':{'path':TXT_PATH.as_posix(),'sha256':sha(raw_by_path[TXT_PATH.as_posix()]),'encoding':'utf-8','newline':'LF','line_count':42,
               'lines':[{'line_number':x['line_number'],'literal':x['text'],'codepoint_span':x['codepoint_span'],'sha256':x['sha256']} for x in txt_lines],
               'modules':modules,'declared_workload':1488,'workload_is_not_event_count':True,'hard_stop_after_level':105,'next_boundary':90},
        'pdf':{'path':PDF_PATH.as_posix(),'sha256':sha(raw_by_path[PDF_PATH.as_posix()]),'pypdf_version':pypdf_version,'page_count':20,'pages':pages},
        'structures':structures,'source_music_locators':locators,
        'mapping_counts':{'a_p03_note_spelling_targets':32,'a_p04_action_cells':24,'b_p05_ordered_pattern_slots':28,
                          'c_p06_grid_contacts':48,'f_p11_note_spelling_tokens':30,'g_p14_arrangement_bar_harmonies':16,
                          'h_p15_18_bar_harmonies':32,'i_p19_bar_harmonies':32,'total_source_locators':len(locators)},
        'unresolved_semantics':{'p09_e_route':'B3/e3 route strings preserved literally; pitch/string/fret interpretation unresolved',
                                'p13_g_pocket_variations':'harmony order retained; no bar counts printed',
                                'timing':'only printed beat/grid/bar ordinal references; no seconds, tempo, onset, duration or velocity inferred',
                                'tone_and_technique':'no octave, string/fret, fingering, articulation, hand result or audio inferred',
                                'workload':'1488 is a declared workload total, not individually enumerated events',
                                'mastery':'printed rubric/instructions only; no learner observations or score'},
        'limitations':['No canonical IDs or events.','No runtime import or admission.','No playable projection.','PDF rendering confirms visible structure only, not musical performance or audible correctness.'],
    }


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    try:
        root=Path(args.root)
        output_arg=Path(args.output)
        if not output_arg.is_absolute(): fail('--output must be absolute')
        if '..' in output_arg.parts: fail('output traversal refused')
        resolved_root=root.resolve()
        if root != ROOT_EXPECTED or resolved_root != ROOT_EXPECTED: fail('root must be exact authoritative path')
        build_root=ROOT_EXPECTED/BUILD_REL
        output=output_arg
        if output.is_symlink(): fail('symlink output refused')
        try: output.relative_to(build_root)
        except ValueError: fail('output must be under the exact P03 Build directory')
        # Reject symlink ancestors and any non-regular existing destination.
        cur=ROOT_EXPECTED
        for part in output.relative_to(ROOT_EXPECTED).parts[:-1]:
            cur=cur/part
            if cur.exists() and cur.is_symlink(): fail('symlink output ancestor refused')
        if output.exists(): fail('overwrite refused')
        if not build_root.exists(): fail('named P03 Build directory must already exist')
        doc=build(root)
        output.parent.mkdir(parents=True,exist_ok=True)
        payload=(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')
        # exclusive creation avoids replacing a concurrent output.
        with output.open('xb') as f: f.write(payload)
        print(json.dumps({'output':str(output),'bytes':len(payload),'sha256':sha(payload),'locators':len(doc['source_music_locators'])},sort_keys=True))
        return 0
    except Exception as e:
        print(f'level089 candidate refused: {e}',file=sys.stderr)
        return 2

if __name__=='__main__': raise SystemExit(main())
