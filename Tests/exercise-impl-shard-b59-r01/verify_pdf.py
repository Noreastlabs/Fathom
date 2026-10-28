#!/usr/bin/env python3
"""Check every PDF card locator against original Level 59 page text."""
import hashlib
import json
import pathlib
import re
from pypdf import PdfReader

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / 'Results/exercise-impl-shard-b59-r01'

def norm(value):
    return re.sub(r'[^a-z0-9]+', '', value.lower())

def main():
    manifest = json.loads((OUT / 'packet-manifest.json').read_text())
    records = []
    for batch in manifest['batches']:
        records.extend(json.loads(line) for line in (ROOT / batch['packet_path']).read_text().splitlines())
    ref = records[0]['source']['original_pdf']
    path = ROOT / ref['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == ref['sha256']
    pages = [page.extract_text() or '' for page in PdfReader(path).pages]
    assert len(pages) == 20
    matched, txt_only = 0, 0
    for row in records:
        loc = row['source']['original_pdf']['locator']
        if loc is None:
            assert row['source']['authority'] == 'original_txt_card_pdf_not_equated'
            txt_only += 1
            continue
        label = loc['within_page_label']
        assert norm(label) and norm(label) in norm(pages[loc['physical_page']-1]), row['package_key']
        matched += 1
    assert (matched, txt_only) == (104, 2)
    result = {'source_path': ref['path'], 'source_sha256': ref['sha256'],
              'physical_pages': len(pages), 'card_labels_matched_to_original_pdf_page': matched,
              'separate_txt_only_units': txt_only, 'status': 'PASS'}
    (OUT / 'pdf-locator-verification.json').write_text(json.dumps(result, sort_keys=True, indent=2)+'\n')
    print(json.dumps(result, sort_keys=True))

if __name__ == '__main__':
    main()
