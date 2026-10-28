import json,subprocess,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for name in sys.argv[1:]:
 r=ROOT/'Results/fullscope-private-b-r01'/name;b=ROOT/'Build/fullscope-private-b-r01'/name
 assert not (r/'artifact-manifest.json').exists(),'already sealed'
 h=json.loads((r/'handoff.json').read_text());v=json.loads((r/'targeted-validation.json').read_text())
 assert v['packet']==h['packet']
 (b/'verify.py').write_bytes((ROOT/'Tests/fullscope-private-b-r01/verify.py').read_bytes())
 lines=['# '+name+' private implementation seal','',f"Attempted {h['counts']['attempted']}; source-supported {h['counts']['source_supported_implemented']}; partial-source-unresolved {h['counts']['partial_source_unresolved']}; unattempted in batch 0. Ordered event occurrences {v['events']}. New native/integrated/independent-review/Accepted all zero.",'',f"Started {h['start_utc']}; ended {h['end_utc']}; converter {h['elapsed_seconds']}s; process peak RSS {h['process_peak_rss_bytes']} bytes. Packet {h['packet']['bytes']} bytes, SHA256 {h['packet']['sha256']}.",'','Targeted baseline and four identity/event/admission/source corruption refusals pass. Context execution tasks retain printed module instructions with source locators, with qualitative pressure/release requirements distinct from acoustic timing. Source-defined manual tasks and learner selections remain non-playback contracts. Runtime/native/GUI/broad QA NOT RUN. Private producer validation is not independent review; downstream manager and P02 own source adoption, canonical allocation and admission.']
 if name=='level049-r02':lines+=['','Supersedes level049 r01 only for proposed downstream selection. Retains r01 unchanged. Adds scoped per-unit governing execution tasks, including ModuleE beat4 pressure reduction/preparation and exact p19 primary-mechanic table fields. Event data and partial Pass4 learner-choice boundary are unchanged.']
 (r/'report.md').write_text('\n'.join(lines)+'\n')
 args=['python3','Tools/fathom_evidence.py','manifest','--root',str(ROOT),'--output',str(r/'artifact-manifest.json')]
 for path in [r/'handoff.json',r/'targeted-validation.json',r/'report.md',b/'implementation.jsonl',b/'source-context.json',b/'conversion.py',b/'extended.py',b/'pdf_conversion.py',b/'source-exceptions.jsonl',b/'verify.py']:
  if path.exists():args+=['--artifact',str(path.relative_to(ROOT))+'|private batch artifact']
 subprocess.run(args,cwd=ROOT,check=True)
 print(name,hashlib.sha256((r/'artifact-manifest.json').read_bytes()).hexdigest())
