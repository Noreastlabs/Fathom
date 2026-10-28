#!/usr/bin/env python3
"""Copy the pinned local lesson validation tree; no downloads or conversion."""
import argparse, hashlib, json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source-root',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
root=a.source_root.resolve(strict=True);out=a.output
if not out.is_absolute():raise SystemExit('Output must be absolute')
def source_for(root,rel):
 if len(rel.parts)>1 and rel.parts[0]=='Results' and rel.parts[1]!='primary':
  primary=root/'Results'/'primary'/Path(*rel.parts[1:])
  if primary.exists() or primary.is_symlink():return primary
 return root/rel
# Build output is reusable only when this tool previously marked the same exact tree.
manifest=(root/'Content/runtime/representative-v1-manifest.json').read_bytes();m=json.loads(manifest)
expected={'manifest.json':manifest}
for entry in m['files']:
 rel=Path(entry['path'])
 if rel.is_absolute() or any(part in ('.','..') for part in rel.parts):raise SystemExit('Unsafe manifest path')
 src=source_for(root,rel)
 if not src.resolve(strict=True).is_relative_to(root):raise SystemExit('Source escapes checkout')
 data=src.read_bytes()
 if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:raise SystemExit('Changed source: '+str(rel))
 expected[str(rel)]=data
if out.exists():
 if out.is_symlink() or not (out/'manifest.json').is_file() or (out/'manifest.json').read_bytes()!=manifest:raise SystemExit('Refusing unrelated or different existing output')
 actual={str(f.relative_to(out)) for f in out.rglob('*') if f.is_file() or f.is_symlink()}
 if actual!=set(expected):raise SystemExit('Existing bundle file set differs; preserve it and choose a new output')
 for rel,data in expected.items():
  dest=out/rel
  if any(x.is_symlink() for x in [dest,*dest.parents]) or dest.read_bytes()!=data:raise SystemExit('Existing bundle changed: '+rel)
 print('Verified unchanged bundle',out,len(expected),'files')
else:
 out.mkdir(parents=True)
 for rel,data in expected.items():
  dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True)
  with dest.open('xb') as f:f.write(data)
 print('Copied exact local bundle',out,len(expected),'files',sum(map(len,expected.values())),'bytes')
