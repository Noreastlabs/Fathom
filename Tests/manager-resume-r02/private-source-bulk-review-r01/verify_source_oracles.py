"""Validate reviewer oracles directly against original PDF and TXT, no model imports."""
from pathlib import Path
import datetime,hashlib,json,re,time
from pypdf import PdfReader
from source_oracles import I_NOTES,I_DEGREES,I_CONTACTS,K_PAIRS,F_ROWS,H_BARS
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'Results/manager-resume-r02/private-source-bulk-review-r01/source-oracle-checks.json'
start=time.monotonic();checks=0
def check(value,label):
    global checks
    if not value:raise AssertionError(label)
    checks+=1
pdf68=next((ROOT/'Notes/music/guitar project/PDF version').glob('*Level_68_*.pdf'))
txt68=next((ROOT/'Notes/music/guitar project/TXT version').glob('*Level_68_*.txt'))
pdf77=next((ROOT/'Notes/music/guitar project/PDF version').glob('*Level_77_*.pdf'))
rd68=PdfReader(pdf68);rd77=PdfReader(pdf77)
txt=txt68.read_text();pdftext=rd68.pages[14].extract_text()
string_numbers={'e':1,'B':2,'G':3,'D':4,'A':5,'E':6}
def tab_contacts(text,width,count):
    result=[None]*count
    for string,body in re.findall(r'^\s*([eBGDAE])\|([0-9-]+)\|?$',text,re.M):
        for match in re.finditer(r'\d+',body):
            col=match.start();check(col%width==0,'original TAB aligned contact')
            i=col//width;check(i<count and result[i] is None,'original one contact per column')
            result[i]=(string_numbers[string],int(match.group()))
    check(all(x is not None for x in result),'original complete TAB')
    return result
module_i=txt.split('MODULE I - MINOR CALLS AND DOMINANT ANSWERS')[1].split('MODULE J -')[0]
for i in range(1,6):
    call=module_i.split(f'P{i} CALL')[1].split(f'P{i} ANSWER')[0]
    answer=module_i.split(f'P{i} ANSWER')[1].split(f'P{i+1} CALL')[0]
    if i==5:answer=answer.split('====')[0]
    check(tab_contacts(call,4,8)+tab_contacts(answer,4,8)==I_CONTACTS[i-1],f'I P{i} exact TXT contacts')
    card=pdftext.split(f'P{i}\n')[1].split(f'P{i+1}\n')[0]
    if i==5:card=card.split('Variation:')[0]
    check(tab_contacts(card,3,16)==I_CONTACTS[i-1],f'I P{i} exact PDF contacts')
    nte=re.search(r'Nte\|([^\n|]+)',card).group(1)
    deg=re.search(r'Deg\|([^\n|]+)',card).group(1)
    check([nte[j*3:j*3+3].strip('-') for j in range(16)]==I_NOTES,'I exact PDF pitch grid')
    check([deg[j*3:j*3+3].strip('-') for j in range(16)]==I_DEGREES,'I exact PDF degree grid')
page19=' '.join(rd68.pages[18].extract_text().split())
for chord,a,b,ra,rb in K_PAIRS:
    check(f'{chord}: {a} -> {b} {ra} -> {rb}' in ' '.join(txt.split()),'K exact paired TXT pitches/roles')
    check(f'{chord}: {a} -> {b} {ra} -> {rb} 2 tones' in page19,'K exact original PDF pitches/roles')
check('TENSION SOUNDS RANDOM: name the target before playing the tension.' in txt,'K target-naming rule original TXT')
page14=' '.join(rd77.pages[13].extract_text().split())
for chord,role,pitch in F_ROWS:check(f'{chord} {role} {pitch}' in page14,'F original encoded chord/role/pitch')
page17=' '.join(rd77.pages[16].extract_text().split())
for i,(chord,notes,target) in enumerate(H_BARS,1):check(f'{i} {chord} {notes} {target}' in page17,'H original encoded four-note bar and target')
sources=[]
for p in [pdf68,txt68,pdf77,Path(__file__),Path(__file__).with_name('source_oracles.py')]:
    data=p.read_bytes();sources.append({'path':str(p.relative_to(ROOT)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'outcome':'PASS','checks_passed':checks,
        'elapsed_seconds':time.monotonic()-start,'source_refs':sources,'scope':'Direct original-source oracle verification, no producer model execution',
        'I_original_contacts_verified':80,'K_original_pitch_pairs_verified':12,'F_original_rows_verified':14,'H_original_bars_verified':16,
        'visual_occlusions_retained':['Level77 PDF14 lastG#7alt row','Level77 PDF17 bar16','Level77 PDF18 worksheet13-16'],
        'official_runtime_acceptance_increments':0}
if OUT.exists():raise RuntimeError('Immutable check exists; new revision required')
OUT.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['outcome','checks_passed','elapsed_seconds']}))
