#!/usr/bin/env python3
"""Package only the reviewed, hash-bound Level80 R02 supplemental extension."""
import argparse,hashlib,json
from pathlib import Path

def package(root,output):
    source=root/'Content/runtime/level080-module-a-pass1-r02-extension-v1'
    raw=(source/'manifest.json').read_bytes();manifest=json.loads(raw)
    if manifest['version']!='level080-module-a-pass1-r02-extension-bundle.1':raise ValueError('Unsupported Level80 extension manifest')
    files={'manifest.json':raw}
    for entry in manifest['files']:
        name=entry['path'];rel=Path(name)
        if rel.is_absolute() or any(x in ('.','..','') for x in name.split('/')) or '\\' in name:raise ValueError('Unsafe extension path')
        path=(source if name in ('decision.json','agent-curriculum-decision.md') else root)/rel
        if any(x.is_symlink() for x in (path,*path.parents)):raise ValueError('Extension symlink refused')
        data=path.read_bytes()
        if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:raise ValueError('Changed extension asset: '+name)
        if name in files:raise ValueError('Duplicate extension asset')
        files[name]=data
    if not output.is_absolute() or any(x.is_symlink() for x in (output,*output.parents)):raise ValueError('Absolute nonsymlink output required')
    if output.exists():
        actual={str(p.relative_to(output)) for p in output.rglob('*') if p.is_file() or p.is_symlink()}
        if actual!=set(files) or any((output/p).is_symlink() or (output/p).read_bytes()!=b for p,b in files.items()):
            raise ValueError('Existing extension differs; retain it and choose a fresh build')
    else:
        output.mkdir(parents=True)
        for name,data in files.items():
            target=output/name;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as stream:stream.write(data)
    print('Verified exact Level80 R02 supplemental extension',len(files),'files',sum(map(len,files.values())),'bytes')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();package(args.source_root.resolve(strict=True),args.output)
