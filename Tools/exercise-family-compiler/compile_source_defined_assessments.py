#!/usr/bin/env python3
"""Compile closed cached A67 assessment DATA, without native/factory admission.

The original literal is partitioned into source-backed criterion witnesses. Reports
are manual evidence after the source musical extent, never inferred performance.
This future graph declares every new owner/guard bridge; current recipes are not
modified. Cached rows/contexts are read once and original TXT/PDF are never read.
"""
import argparse, collections, copy, datetime, hashlib, json, re, time
from pathlib import Path

BASE = 'Build/manager-resume-r03/manual-source-assessments67-r01'
SELECTION = BASE + '/selection.json'
SELECTION_SHA = 'db7e4bee5a67e96af25237203e09dcd100f9f2a150bff5946bdbd3ec1de98ea2'
LEDGER_SHA = 'ce8ad63e95cf1670804f058833ec43538d42a611f260d5d1711ee17fc5925d4b'
OUT = BASE + '/generated-r03'
WORDS = dict(zip('one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen twenty twenty-four'.split(), [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20,24]))
NUMBER = r'(?:\d+(?:,\d{3})*|' + '|'.join(sorted(WORDS, key=len, reverse=True)) + ')'
UNIT_LIST = ['local pairs','seam conversations','seam phrases','target cells','voice-leading routes','model choruses','root passes','placement cards','rest studies','call-and-response studies','stop-time studies','turnaround entries','click-displacement passes','random-entry cards','color pairs','legato cells','one-pick seam chains','one-pick chains','seam slides','whole-step bends','pre-bend releases','A roots','cadence phrases','horizontal lanes','seam-slide phrases','resolution triplets','four-note cells','passing/rest comparisons','slide chains','rhythmic placements','audit cards','blue-third sites','lick families','rhythmic forms','register conversations','ending choices','functional turnarounds','recombination choices','third-control sites','position phrases','call-and-response pairs','core licks','reference cells','degree identities','drones','positions','modules','pitches','roots','pairs','ways','seams','choruses','circuits','cells','trips','attacks','tones','notes','beats','bars','keys','lanes','bends','pickups','cadences','phrases','articulations','transformations','recordings','passes','strings','motif','block','circuit','beat','chorus','position','articulation','response transformation']
COUNT_UNITS = r'(?:'+'|'.join(map(re.escape,sorted(UNIT_LIST,key=len,reverse=True)))+')'
ADJECTIVES = r'(?:clean|complete|connected|linked|sounding|picked|full|conspicuous|deliberate|timed|three-key|drone|four-bar|single-note|twelve-bar|Module [AB])'
VERBS = r'name|preserve|land|complete|maintain|keep|recover|identify|play|perform|make|use|end|shift|locate|record|execute|match|hold|link|distinguish|resolve|hear|sing|say|repeat|transform|score|finish|treat'

class BindingError(ValueError): pass
def require(x, why):
    if not x: raise BindingError(why)
def encoded(x): return json.dumps(x, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
def sha(x): return hashlib.sha256(x).hexdigest()
def strict(raw):
    def pairs(items):
        out = {}
        for k,v in items:
            require(k not in out, 'DUPLICATE_JSON_PROPERTY'); out[k] = v
        return out
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda x: (_ for _ in ()).throw(BindingError('NONFINITE_JSON')))
def text(nullable=False, maximum=1024): return {'type':['string','null'] if nullable else 'string','minLength':1,'maxLength':maximum,'input_role':'manual_report'}
def integer(nullable=True, maximum=100000): return {'type':['integer','null'] if nullable else 'integer','minimum':0,'maximum':maximum,'input_role':'manual_report'}
def menu(values, nullable=False): return {'type':['string','null'] if nullable else 'string','enum':[*values,*([None] if nullable else [])],'input_role':'manual_report'}
def boolean(): return {'type':['boolean','null'],'input_role':'manual_report'}
def schema(fields): return {'type':'object','properties':fields,'required':list(fields),'additionalProperties':False}
def ref(scope,*path): return {'scope':scope,'path':list(path)}
def source_ref(i): return {'original_contract_path':['ordered_source_instructions',i]}
def number(x): return WORDS[x.lower()] if x.lower() in WORDS else int(x.replace(',',''))
def slug(x): return re.sub(r'[^a-z0-9]+','_',x.lower()).strip('_')

class Inputs:
    def __init__(self, root): self.root = Path(root).resolve(strict=True); self.cache = {}; self.hashes = 0
    def pinned(self, r):
        name=r['path']; p=Path(name)
        require(not p.is_absolute() and all(x not in ('','.','..') for x in name.split('/')), 'INPUT_PATH')
        if name not in self.cache:
            full=self.root
            for part in name.split('/'):
                full/=part; require(not full.is_symlink(), 'INPUT_SYMLINK')
            require(full.is_file(), 'INPUT_NOT_FILE'); b=full.read_bytes(); self.cache[name]=(len(b),sha(b),b); self.hashes+=1
        size,digest,b=self.cache[name]; require(size==r['bytes'] and digest==r['sha256'], 'INPUT_PIN_DRIFT'); return b

def select(root):
    path=Path(root)/SELECTION; raw=path.read_bytes(); require(sha(raw)==SELECTION_SHA, 'SELECTION_PIN'); s=strict(raw); c=Inputs(root)
    ledger=c.pinned(s['ledger']); require(sha(ledger)==LEDGER_SHA, 'LEDGER_PIN')
    # Only the saved exact target set is joined. No filesystem census or new scope.
    targeted={r['package_key']:r for r in map(strict,ledger.splitlines()) if r['package_key'] in {x['source_key'] for x in s['rows']}}
    require(len(targeted)==67 and len(s['rows'])==67, 'EXACT67')
    d=strict(c.pinned(s['descriptor_preimage'])); accepted={o['selection']['package_key'] for o in d['current_status_resolution']['operations'] if o['current_overlay']['status']=='Accepted'}
    c.pinned(s['reused_source_policy_cache'])
    for r in s['cached_inputs']: c.pinned(r)
    originals={}; contexts={}; identities=set()
    for r in s['rows']:
        t=targeted[r['source_key']]; p=t['current_payload']; require(p['owner']=='A' and p['implementation_kind']=='source_defined_task' and p['normalized_producer_category']=='MANUAL_SOURCE_CONTRACT' and not t['dispatch_ownership']['broad_lane_excluded'], 'EXACT_SCOPE_CATEGORY')
        require(r['source_key'] not in accepted and r['source_identity'] not in identities, 'STATUS_OR_IDENTITY'); identities.add(r['source_identity'])
        require(p['ref']==r['payload_ref'] and t['source_pins']==r['source_pins'], 'LEDGER_ROW_REF')
        line=c.pinned(r['payload_ref']).splitlines()[r['payload_ref']['jsonl_line']-1]; o=strict(line)
        require(sha(line)==r['original_row_sha256'] and sha(encoded(o))==r['original_compact_sha256'] and sha(json.dumps(o,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode())==r['original_canonical_sha256'], 'EXACT_ROW_HASHES')
        require((o['package_key'],o['source_identity'],o['level'])==(r['source_key'],r['source_identity'],r['level']), 'ROW_IDENTITY')
        impl=o['implementation']; contract=impl['task_contract']
        require(impl['kind']=='source_defined_task' and impl['ordered_contacts']==[] and impl['runtime_eligible'] is False and impl['mastery_or_credit'] is False and contract['performance_observed'] is False, 'SOURCE_MANUAL_BOUNDARY')
        require(impl['task_steps']==contract['ordered_source_instructions']==o['source_payload']['instruction_lines'], 'ALL_ORDERED_SOURCE_INSTRUCTIONS')
        ctx=strict(c.pinned(r['context_ref'])); require(ctx['level']==r['level'], 'CONTEXT_LEVEL')
        for kind in ('txt','pdf'):
            if r['source_pins'][kind+'_sha256'] is not None: require(ctx['originals'][kind]['sha256']==r['source_pins'][kind+'_sha256'], 'CONTEXT_ORIGINAL_PIN')
        originals[r['source_key']]=o; contexts[r['level']]=ctx
    return s,c,originals,contexts

def partition(contract):
    """Exact char witnesses; linewrap joining is explicit and reversible by refs."""
    lines=contract['ordered_source_instructions']; joined=' '.join(x['text'] for x in lines); spans=[]; cursor=0
    for i,x in enumerate(lines): spans.append((cursor,cursor+len(x['text']),i)); cursor+=len(x['text'])+1
    metadata=[]; criteria=[]; pending=[]
    def references(a,b): return [source_ref(i) for l,h,i in spans if h>a and l<b]
    def emit(a,b,**extra):
        while a<b and joined[a].isspace():a+=1
        while b>a and joined[b-1].isspace():b-=1
        if a<b: criteria.append({'id':'criterion_'+str(len(criteria)+1).zfill(3),'literal':joined[a:b],'source_excerpt':{'start':a,'end':b,'normalization':'single space between exact original instruction lines'},'source_action_refs':references(a,b),**extra})
    def flush():
        if not pending:return
        a,b=pending[0][0],pending[-1][1]; start=a
        # Commas only split when a new printed predicate follows, not noun lists.
        pattern=r'[.;?!](?=\s|$)|,\s*(?:and\s+|then\s+)?(?=(?:'+VERBS+r')\b)'
        for m in re.finditer(pattern,joined[a:b],re.I):
            end=a+m.end()
            if re.fullmatch(r'\d+\.',joined[start:end]):
                metadata.append({'literal':joined[start:end],'source_excerpt':{'start':start,'end':end},'source_action_refs':references(start,end),'role':'source_list_number'})
            else: emit(start,end)
            start=end
        emit(start,b); pending.clear()
    rubric38=lines[0]['text']=='Score 0-2'
    rubric48='RUBRIC - SCORE EACH 0, 1, OR 2' in lines[0]['text']
    table=set(range(1,28)) if rubric38 else set()
    for a,b,i in spans:
        value=lines[i]['text']; heading=i==0 or not value.strip() or bool(re.fullmatch(r'[-=]+',value)) or (value.isupper() and value.startswith('CHORUS ')) or (rubric38 and i==28)
        if i in table:
            flush()
            if i>=4 and (i-4)%4==0:
                hi=spans[i+3][1]; emit(a,hi,rubric={'dimension':value,'values':{str(n):lines[i+1+n]['text'] for n in range(3)},'maximum':2});
            continue
        if heading:
            flush(); metadata.append({'literal':value,'source_excerpt':{'start':a,'end':b},'source_action_refs':[source_ref(i)],'role':'rubric_scale' if rubric38 and 1<=i<=3 else 'heading_or_separator'}); continue
        if rubric48 and 1<=i<=8:
            flush();m=re.fullmatch(r'(.+): 0 (.+) / 1 (.+) / 2 (.+)\.',value);require(m is not None,'EXACT_RUBRIC48');emit(a,b,rubric={'dimension':m[1],'values':{str(n):m[2+n] for n in range(3)},'maximum':2});continue
        numbered=bool(re.match(r'\d+\.\s',value)); bullet=value.lstrip().startswith('- ')
        standalone_check=bool(re.match(r'(?:A-(?:major|natural-minor).*clean with [DU] start|At least one three-key block|Five modules identifiable)',value))
        if numbered or bullet or standalone_check:flush()
        pending.append((a,b,i))
        if value.endswith(('.', '?','!')) or numbered or bullet or standalone_check:flush()
    flush()
    # Numeric scale rows are metadata; rubric criteria cover the remaining table.
    if rubric38:
        metadata.extend({'literal':lines[i]['text'],'source_excerpt':{'start':spans[i][0],'end':spans[i][1]},'source_action_refs':[source_ref(i)],'role':'rubric_scale'} for i in range(1,4))
    mask=[False]*len(joined)
    for x in metadata+criteria:
        a=x['source_excerpt']['start'];b=x['source_excerpt']['end'];require(joined[a:b]==x['literal'],'LITERAL_SPAN'); mask[a:b]=[True]*(b-a)
    require(all(mark or char.isspace() for mark,char in zip(mask,joined)), 'UNBOUND_LITERAL_CHARACTER')
    return joined,metadata,criteria

def quantities(literal):
    """Closed quantitative duty patterns; geometry/form locations stay literal facts."""
    out=[]; pattern=r'(?<![\w#])(?P<prefix>at least |no more than |maximum |all )?(?P<n>'+NUMBER+r')\s+(?P<adjectives>(?:'+ADJECTIVES+r'\s+){0,3})(?P<unit>'+COUNT_UNITS+r')\b'
    for m in re.finditer(pattern,literal,re.I):
        n=number(m['n']); unit=m['unit'].lower(); prefix=(m['prefix'] or '').lower(); fragment=m.group(0)
        if unit in ('notes','attacks','cells','circuits','beats') and ('route contains' in literal.lower() or 'route count:' in literal.lower() or 'count:' in literal.lower() or re.search(r'\bx\s*\d',literal,re.I)):role='inventory_fact'
        elif unit in ('beats','bars') and not prefix:role='form_or_metric_fact'
        else:role='manual_count_criterion'
        comparison='minimum' if prefix=='at least ' or re.search(r'after three clean trips',literal,re.I) and unit=='trips' else 'maximum' if prefix in ('no more than ','maximum ') else 'exact'
        out.append({'id':'quantity_'+str(len(out)+1),'literal':fragment,'start':m.start(),'end':m.end(),'value':n,'unit':unit,'comparison':comparison,'role':role})
    for m in re.finditer(r'\bboth (?P<unit>'+COUNT_UNITS+r')\b',literal,re.I):
        out.append({'id':'quantity_'+str(len(out)+1),'literal':m.group(0),'start':m.start(),'end':m.end(),'value':2,'unit':m['unit'].lower(),'comparison':'exact','role':'manual_count_criterion'})
    return out

def report(instruction,fields,expected,next_node,refs,*,constraints=None,physical=False,tag=None,save=None):
    return {'kind':'report','action':'submit','instruction':instruction,'schema':schema(fields),'expected':expected,'constraints':constraints or [],'save_as':save,'physical':physical,'pass_tag':tag,'next':next_node,'completion_effects':[],'source_action_refs':refs}
def choice(instruction,field,values,routes,**fields):
    return {'kind':'choice','action':'choose','instruction':instruction,'schema':schema({field:menu(values),**fields}),'expected':{},'constraints':[],'route_field':field,'routes':routes,'save_as':None,'physical':False,'completion_effects':[]}
def end(status): return {'kind':'end','status':status,'grants_credit':False}

def program(original):
    c=original['implementation']['task_contract']; joined,metadata,criteria=partition(c); body=' '.join(x['literal'] for x in criteria); two_days=bool(re.search(r'two separate (?:clean )?days|two separate clean days',body,re.I)); rubric=[x for x in criteria if 'rubric' in x]; nodes={}; extensions=set(); source_exceptions=[]
    # All criterion reports happen after the complete source musical extent.
    # Physical extent is a single manual boundary, not generated music or a clock.
    physical=bool(re.search(r'\b(?:play|perform|shift|bend|execute)\b',body,re.I))
    nodes['source_extent']=report('Use your original source for the complete extent below. Preserve uninterrupted routes/choruses and any printed intermediate release/stop/relocation; enter reports after the extent. No notes, clock, recording or audio result is generated. '+body,
        {'source_extent_evidence':text(maximum=4096),'unresolved_source_issue':menu(['none_reported','unresolved_issue_reported','unknown'],True)}, {'unresolved_source_issue':'none_reported'},criteria[0]['id'],[source_ref(i) for i in range(len(c['ordered_source_instructions']))],constraints=[{'kind':'nonempty_trimmed_text','field':'source_extent_evidence','minimum':1,'maximum':4096}],physical=physical,tag='source_extent')
    extensions.add('nonempty_trimmed_text')
    rubric_fields=[]
    for i,x in enumerate(criteria):
        literal=x['literal']; low=literal.lower(); next_node=criteria[i+1]['id'] if i+1<len(criteria) else 'end_unit'; fields={'reported_outcome':menu(['reported_met','reported_not_met','unknown'],True),'manual_evidence':text(True,2048)}; expected={'reported_outcome':'reported_met'}; guards=[{'kind':'nonempty_trimmed_text','field':'manual_evidence','minimum':1,'maximum':2048}]
        x['quantities']=quantities(literal); x['evidence_kind']='source_criterion_manual_report'; x['observed']=False
        # Dates are claims, not scheduled practice or native mastery. Each date
        # gets its own criterion outcome/evidence and source count/start debt.
        dates=bool(re.search(r'two separate (?:clean )?days|two separate clean days',literal,re.I))
        sessions=[1,2] if dates else [0]
        if dates:
            for day in (1,2):
                fields['date_'+str(day)]=text(True,10);fields['day_'+str(day)+'_criterion_outcome']=menu(['reported_met','reported_not_met','unknown'],True);fields['day_'+str(day)+'_evidence']=text(True,2048);expected['day_'+str(day)+'_criterion_outcome']='reported_met';guards.append({'kind':'nonempty_trimmed_text','field':'day_'+str(day)+'_evidence','minimum':1,'maximum':2048})
            guards.append({'kind':'distinct_dates','fields':['date_1','date_2']});x['two_distinct_manual_dates']=True
        starts=bool(re.search(r'both pick starts|each starting stroke|opposite starting (?:pick )?stroke|opposite starting stroke|opposite starting pick stroke|opposite start|D-start and U-start|downstroke-start and upstroke-start',literal,re.I))
        if starts:
            for session in sessions:
                for stroke in ('D','U'):
                    suffix=('_day_'+str(session)) if session else '';key='reported_'+stroke+suffix;fields[key]=boolean();expected[key]=True;fields[key+'_evidence']=text(True,1024);guards.append({'kind':'nonempty_trimmed_text','field':key+'_evidence','minimum':1,'maximum':1024})
            x['both_start_debt']=True
        for q in x['quantities']:
            if q['role']!='manual_count_criterion':continue
            for session in sessions:
                name=q['id']+('_day_'+str(session) if session else '')+'_reported_'+slug(q['unit']);fields[name]=integer(maximum=max(100000,q['value']));q.setdefault('report_fields',[]).append(name)
                if q['comparison']=='exact':expected[name]=q['value']
                else:guards.append({'kind':q['comparison'],'field':name,'value':q['value']});extensions.add(q['comparison'])
        # Printed score thresholds; a total is manual, not computer grading.
        threshold=re.search(r'(?:score at least |after )(?P<n>\d+)\s*(?:/|of )\s*(?P<d>\d+)',literal,re.I)
        if not threshold and rubric and re.search(r'13 or higher',literal,re.I):threshold={'n':'13','d':'16'}
        if threshold:
            n,d=int(threshold['n']),int(threshold['d']);attempts=[1,2] if dates or re.search(r'ear test twice',literal,re.I) else [1]
            x['score_gate']={'minimum':n,'maximum':d,'attempts':len(attempts),'manual_only':True}
            for attempt in attempts:
                name='reported_score_'+str(attempt);fields[name]=integer(maximum=d);guards.append({'kind':'minimum','field':name,'value':n})
            if rubric:
                for attempt in attempts:
                    fs=[]
                    for r in rubric:
                        name='rating_'+str(attempt)+'_'+slug(r['rubric']['dimension']);fields[name]=integer(maximum=2);fs.append(name)
                        guards.append({'kind':'same_as_saved','left':ref('payload',name),'right':ref('saved',r['id'],name)})
                        if d==16 and r['rubric']['dimension'] in ('Form awareness','Chord targeting','Recovery after an error'):guards.append({'kind':'minimum','field':name,'value':1})
                    guards.append({'kind':'reported_score_sum','fields':fs,'total_field':'reported_score_'+str(attempt)});extensions.add('reported_score_sum')
        if 'rubric' in x:
            fields['reported_outcome']=menu(['rating_reported','unknown'],True);expected['reported_outcome']='rating_reported';x['evidence_kind']='manual_rubric_rating_not_inferred_control'
            for attempt in ([1,2] if two_days else [1]):
                name='rating_'+str(attempt)+'_'+slug(x['rubric']['dimension']);fields[name]=integer(maximum=2);rubric_fields.append(name)
            # No expected rating of2: lower valid manual ratings are retained;
            # printed total/no-zero gate decides the later source criterion.
        # Source same-tempo comparisons use learner-entered BPM only. No default.
        if 'one bpm' in low or 'without changing tempo' in low:
            count=3 if 'sparse, medium, and dense' in low or 'three straight/shuffle' in low else 2
            fields['reported_bpm_1']=integer(maximum=10000)
            for j in range(2,count+1):fields['reported_bpm_'+str(j)]=integer(maximum=10000);guards.append({'kind':'equal','fields':['reported_bpm_1','reported_bpm_'+str(j)]})
            guards.append({'kind':'minimum','field':'reported_bpm_1','value':1});x['bpm_is_manual_report_not_source_clock']=True
        if re.search(r'different (?:material|exercise|key)',low):
            fields['material_1']=text(True,1024);fields['material_2']=text(True,1024);guards.append({'kind':'different','fields':['material_1','material_2']});x['material_evidence_limit']='Different reported identifiers do not establish different musical content; source duties and evidence remain manual.'
        if 'pulse and chord changes must remain identical' in low:
            for category in ('pulse','chord_changes'):
                for version in (1,2):fields['reported_'+category+'_'+str(version)]=text(True,1024)
                guards.append({'kind':'equal','fields':['reported_'+category+'_1','reported_'+category+'_2']})
            x['comparison_is_manual']='Text identifiers compare the learner reports only; no pulse or chord-change listening inference.'
        duration=re.search(r'(\d+)-second phrase',literal,re.I)
        if duration:
            fields['reported_recording_duration_seconds']=integer();expected['reported_recording_duration_seconds']=int(duration[1]);x['source_duration_is_manual_not_clock']=True
        if 'either a tonic close or a functional E7 turnaround' in literal:
            fields['reported_ending_choice']=menu(['tonic_close','functional_E7_turnaround'],True);x['source_alternatives']=['tonic_close','functional_E7_turnaround']
        if 'Replace bar 12 with an A-tonic closing phrase if desired' in literal:
            fields['reported_optional_bar12']=menu(['retain_printed_E7_turnaround','choose_A_tonic_closing_phrase'],True);x['source_alternatives']=['retain_printed_E7_turnaround','choose_A_tonic_closing_phrase']
        if 'half a beat' in low:
            fields['reported_rest_progression']= {'type':['array','null'],'minItems':3,'maxItems':3,'items':menu(['1/1','1/2','0/1']) ,'input_role':'manual_report'};expected['reported_rest_progression']=['1/1','1/2','0/1'];x['manual_fractional_rest_progression_not_clock']=True
        if 'State the completed bar number' in literal:
            fields.update({'reported_completed_bar':integer(),'reported_current_chord':text(True,64),'reported_next_chord':text(True,64)})
            for name in ('reported_current_chord','reported_next_chord'):guards.append({'kind':'nonempty_trimmed_text','field':name,'minimum':1,'maximum':64})
            x['external_partner_evidence_limit']='Typed bar/chord reports retain the response; no context-dependent chord answer or partner stop event is generated.'
        if 'Resume on the following bar' in literal:
            fields['reported_resumed_bar']=integer();fields['chorus_not_restarted']=boolean();expected['chorus_not_restarted']=True
        if 'release' in low and 'pre-bend releases' not in low:
            fields['printed_release_sequence_reported']=boolean();expected['printed_release_sequence_reported']=True;x['printed_release_is_manual_not_acoustic']=True
        if 'optional endurance badge' in low or 'endurance badge' in low:
            # The route count stays a source fact; declining this optional branch
            # never discharges any required circuit/key/start duty.
            x['optional']=True;nodes[x['id']+'_choose']=choice('The printed full endurance route is optional. Select it explicitly or leave it unselected; required circuit/block duties remain unchanged.','optional_endurance',['perform_source_option','leave_unselected'],{'perform_source_option':{'next':x['id']},'leave_unselected':{'next':next_node}})
            for node in nodes.values():
                if node.get('next')==x['id']:node['next']=x['id']+'_choose'
            for q in x['quantities']:q['role']='optional_inventory_fact'
            for key in [k for k in fields if k.startswith('quantity_')]:fields.pop(key);expected.pop(key,None)
            guards=[g for g in guards if not str(g.get('field','')).startswith('quantity_')]
        nodes[x['id']]=report(literal+' Report this criterion and your evidence only. Unknown or unmet reports retain the diagnosis; no performance is detected.',fields,expected,next_node,x['source_action_refs'],constraints=guards,tag=x['id'],save=x['id'])
        # Scope/ordering facts remain exactly source-bound, without generated
        # routes/pitches/alternative realizations or a claim of musical equivalence.
        x['source_numeric_literals']=[m.group(0) for m in re.finditer(r'\d[\d,]*(?:/\d+)?|\b(?:'+ '|'.join(WORDS)+r')\b',literal,re.I)]
    # Source-conditional physical repair: tonic check has an actual printed branch.
    if original['source_payload']['printed_label']=='Minor-center check':
        first=criteria[0]['id'];nodes['tonic_choice']=choice('After source bar4, mute the strings and sing the tonic. Report the tonic you actually sang. A requires the printed low-F# drone and reduced density before repeating; other/unknown remains unresolved.','reported_tonic',['F#','A','other','unknown'],{'F#':{'next':first},'A':{'next':'tonic_repair'},'other':{'next':'unresolved_tonic'},'unknown':{'next':'unresolved_tonic'}})
        nodes['tonic_repair']=report('Repeat the source phrase with a low F# drone and reduce density. Report both prescribed repairs; no drone or pitches are generated.',{'low_F_sharp_drone_used':boolean(),'density_reduced':boolean(),'repair_evidence':text(True,2048)},{'low_F_sharp_drone_used':True,'density_reduced':True},'tonic_choice',[source_ref(i) for i in range(len(c['ordered_source_instructions']))],constraints=[{'kind':'nonempty_trimmed_text','field':'repair_evidence','minimum':1,'maximum':2048}],physical=True,tag='source_extent')
        nodes['unresolved_tonic']=report('The source only prescribes the A-to-F# repair. Other or unknown tonic remains unresolved; stop or restart with an explicit diagnosis.',{'reported_outcome':menu(['reported_not_met','unknown'],True),'manual_evidence':text(True,2048)},{'reported_outcome':'reported_met'},'end_unit',[source_ref(1)],tag=first)
        nodes['source_extent']['next']='tonic_choice';source_exceptions.append({'kind':'source_conditional_limit','literal':'Only A instead of F# has a prescribed low-F# drone/density repair; other/unknown does not invent a musical repair.'})
    # Source tempo rule gets a separate selected branch and manual number reports.
    if 'add 2 BPM after three clean trips' in joined:
        tempo=next(x for x in criteria if 'add 2 BPM' in x['literal']);down=next(x for x in criteria if 'reduce 4-6 BPM' in x['literal']);tempo_id=tempo['id'];down_id=down['id'];after=nodes[down_id]['next']
        extent=nodes['source_extent'];extent['schema']['properties'].update({'reported_error_count':integer(),'reported_tension':boolean()});extent['schema']['required']=list(extent['schema']['properties'])
        nodes[tempo_id+'_choose']=choice('Use only the printed tempo rule. Holding tempo is allowed; increase requires three clean complete trips. Two errors or tension require the 4–6 BPM reduction. Enter manual BPM reports; this owner supplies no clock.','tempo_decision',['hold','increase_after_three_clean_trips','reduce_after_errors_or_tension'],{'hold':{'next':after},'increase_after_three_clean_trips':{'next':tempo_id},'reduce_after_errors_or_tension':{'next':down_id}},prior_manual_bpm=integer(maximum=10000),reported_error_count=integer(),reported_tension=boolean())
        ch=nodes[tempo_id+'_choose'];ch['save_as']='tempo_choice';ch['constraints']=[{'kind':'minimum','field':'prior_manual_bpm','value':1},{'kind':'source_policy_reported','policy':'tempo_choice_trigger','choice_field':'tempo_decision','error_count_field':'reported_error_count','tension_field':'reported_tension','error_threshold':2}];extensions.add('source_policy_reported')
        for n in nodes.values():
            if n is not ch and n.get('next')==tempo_id:n['next']=tempo_id+'_choose'
        for id,delta in [(tempo_id,[2,2]),(down_id,[-6,-4])]:
            n=nodes[id];n['next']=after;n['schema']['properties'].update({'prior_manual_bpm':integer(maximum=10000),'new_manual_bpm':integer(maximum=10000)});n['schema']['required']=list(n['schema']['properties']);n['constraints'] += [{'kind':'same_as_saved','left':ref('payload','prior_manual_bpm'),'right':ref('saved','tempo_choice','prior_manual_bpm')},{'kind':'source_policy_reported','policy':'reported_bpm_delta','before_field':'prior_manual_bpm','after_field':'new_manual_bpm','minimum_delta':delta[0],'maximum_delta':delta[1]}]
            if id==tempo_id:n['schema']['properties']['reported_clean_complete_trips']=integer();n['schema']['required'].append('reported_clean_complete_trips');n['constraints'].append({'kind':'minimum','field':'reported_clean_complete_trips','value':3})
        source_exceptions.append({'kind':'future_owner_persistent_debt','criterion_ids':[tempo_id,down_id],'requirement':'An error/tension reduction debt and reported BPM ceiling must survive retry/cancel/restart and cannot be undone by a hold/increase choice. Pure guard DATA is not sufficient owner proof.'})
    nodes['end_unit']=end('user_reported_source_criteria_finished_only_no_mastery_or_credit')
    state_protocols=[]
    if 'add 2 BPM after three clean trips' in joined:
        state_protocols.append({'kind':'source_tempo_reduction_debt','source_rule_refs':tempo['source_action_refs']+down['source_action_refs'],'owner_binding':'exact source_key and native owner; no payload-supplied state','activate':{'nodes':['source_extent',tempo_id+'_choose'],'error_count_field':'reported_error_count','source_reported_error_threshold':2,'tension_field':'reported_tension','reported_tension':True,'unknown_error_or_tension':'unresolved debt cannot be cleared by a restart','negative_reports_retained_and_activate_debt':True},'retain_across':['retry','cancel','navigation','restart','unknown report'],'reduction_node':down_id,'reduction_delta':[-6,-4],'increase_node':tempo_id,'increase_delta':2,'required_clean_complete_trips':3,'hold_or_increase_cannot_clear_debt':True,'reported_bpm_ceiling':'Retain the last validated reduced manual BPM; a new increase requires the printed clean-trip condition. No native clock.'})
    tags=['source_extent',*[x['id'] for x in criteria]]
    nodes['repair_bind']=report('Identify the exact failed source criterion and describe the repair or stop reason. This report cannot replace the failed evidence.',{'failed_criterion':menu(tags),'diagnosis':text(True,2048)},{},'repair_choice',[],constraints=[{'kind':'same_as_failed_pass','payload_ref':ref('payload','failed_criterion')},{'kind':'nonempty_trimmed_text','field':'diagnosis','minimum':1,'maximum':2048}],save='repair')
    nodes['repair_choice']=choice('Restart the complete source extent and all criterion reports, or stop with explicit release. Retain the failed report/history. Source-specific musical repairs remain as printed; no synthetic repair is supplied.','repair_action',['restart_complete_source_extent','stop'],{'restart_complete_source_extent':{'next':'source_extent'},'stop':{'next':'end_unit','native_protocol':'stop'}})
    entry='source_extent'
    if original['source_payload']['printed_label']=='Optional partner test':
        nodes['optional_partner']=choice('This source partner test is optional. Select it only with an actual partner; otherwise retain it as unselected.','partner_test',['perform_with_partner','leave_unselected'],{'perform_with_partner':{'next':'source_extent'},'leave_unselected':{'next':'end_optional_unselected'}});nodes['end_optional_unselected']=end('optional_source_test_unselected');entry='optional_partner'
        source_exceptions.append({'kind':'external_partner_protocol','requirement':'Partner calls STOP after an arbitrary completed bar; exact chord/bar/resume evidence stays manual. No partner events, chord answers or interrupted chorus are generated.'})
    return {'name':'source_defined_assessment','mode':'graph','steps':[], 'graph':{'schema':'fathom.manual-procedure-graph.1','entry':entry,'nodes':nodes,'domains':{},'failure_policy':{'terminal_current_pass':True,'diagnosis_required':True,'physical_failure_requires_release':True,'nonphysical_failure_activates_physical':False,'active_retry_stop_navigation_require_exit_release':True,'explicit_restart_entry':entry,'failed_pass_repair_entry':'repair_bind'},'source_state_protocols':state_protocols,'call_semantics':'No row calls or generated music; musical full extent precedes criterion forms.','loop_semantics':'Finite source repair/retest routes only; no automatic loop, clock, random stop, partner event or practice completion.'},'source_criteria':criteria,'source_metadata':metadata,'source_literal_sha256':sha(joined.encode()),'source_literal_ref':{'original_contract_path':['ordered_source_instructions'],'normalization':'single space between original instruction lines'},'source_kind':'source_defined_task','source_task_kind':c['task_kind'],'learner_instruction_context_ref':{'original_record_paths':[['source_payload','printed_label'],['source_payload','parent_path']],'original_contract_paths':[['ordered_source_instructions']]},'source_obligations_ref':{'context_ref_required':True,'broader_context_discharged':False,'unselected_optional_options_discharged':False,'full_parent_or_book_gate':False},'source_limits':source_exceptions,'future_guard_extensions':sorted(extensions), 'source_clock':None,'sounding_span':None,'hidden_self_check':None,'fixed_bpm':None,'performance_observed':False,'recording_observed':False,'grants_credit':False,'automatic_mastery':False,'runtime_admitted':False}

def validate_program(p,original):
    joined,metadata,criteria=partition(original['implementation']['task_contract']); require(p['source_literal_sha256']==sha(joined.encode()),'SOURCE_LITERAL_SHA')
    require(p==program(original),'DETERMINISTIC_PROGRAM');nodes=p['graph']['nodes']; require(p['graph']['entry'] in nodes,'ENTRY')
    reachable=set();pending=[p['graph']['entry'],'repair_bind']
    while pending:
        name=pending.pop()
        if name in reachable:continue
        require(name in nodes,'UNKNOWN_EDGE');reachable.add(name);n=nodes[name]
        if n['kind']=='end':require(n['grants_credit'] is False,'END_CREDIT');continue
        require(n['schema']['additionalProperties'] is False and set(n['schema']['required'])==set(n['schema']['properties']),'CLOSED_REQUIRED_SCHEMA')
        require('default' not in json.dumps(n['schema']), 'NO_PREFILLED_REPORTS')
        if n['kind']=='choice':
            require(set(n['routes'])==set(n['schema']['properties'][n['route_field']]['enum']), 'ALL_CLOSED_ROUTES');pending.extend(r['next'] for r in n['routes'].values())
        else:pending.append(n['next'])
        for r in n.get('source_action_refs',[]):
            path=r['original_contract_path'];require(len(path)==2 and path[0]=='ordered_source_instructions' and type(path[1]) is int and 0<=path[1]<len(original['implementation']['task_contract']['ordered_source_instructions']),'SOURCE_ACTION_REF')
    # Tempo alternatives deliberately avoid a mandatory addition and reduction
    # chain; all source criteria still have an explicit route or manual source fact.
    require(set(nodes)==reachable,'UNREACHABLE_NODE'); require(len(criteria)==len(p['source_criteria']) and len({x['id'] for x in criteria})==len(criteria),'EXACT_CRITERIA')
    require(p['fixed_bpm'] is None and p['source_clock'] is None and p['sounding_span'] is None and all(p[k] is False for k in ('runtime_admitted','performance_observed','recording_observed','grants_credit','automatic_mastery')), 'MANUAL_AUTHORITY')

def build(root):
    start=time.perf_counter();s,c,originals,contexts=select(root); rows=[]; profiles=collections.Counter();extensions=collections.Counter()
    for r in s['rows']:
        o=originals[r['source_key']];p=program(o);validate_program(p,o);profiles[o['implementation']['task_contract']['task_kind']]+=1;extensions.update(p['future_guard_extensions'])
        rows.append({'schema':'fathom.manual-procedure-reference-definition.1','source_key':r['source_key'],'source_identity':r['source_identity'],'level':r['level'],'original_row_sha256':r['original_row_sha256'],'original_compact_sha256':r['original_compact_sha256'],'original_canonical_sha256':r['original_canonical_sha256'],'payload_ref':r['payload_ref'],'retained_contract_path':r['retained_contract_path'],'source_pins':r['source_pins'],'context_ref':r['context_ref'],'contract_sha256':sha(encoded(p)),'program':p,'qualification':'Future source-bound criterion graph DATA only. Native/installed/independent/whole-child acceptance pending.'})
    closure={'schema':'fathom.manual-procedure-reference-closure.1','selection':{'path':SELECTION,'sha256':SELECTION_SHA},'exact_key_count':67,'keys':[x['source_key'] for x in rows],'contracts':{x['source_key']:x['contract_sha256'] for x in rows},'cached_witnesses':s['cached_inputs'],'contexts':{str(k):contexts[k] for k in sorted(contexts)},'source_kind':'source_defined_task','source_contract_profile_counts':dict(profiles),'profile_counts_are_not_behavior_equivalence':True,'source_obligation_limits':['Full source routes, scores, dates, different material, recordings, random stops, partner actions and tempo are learner reports. Musical realizations and clock/acoustic/listening facts are not generated.','Broader cached source context remains retained manual debt; no source criterion report establishes parent, book or automatic mastery.'],'bridge_requirements':['Admit exact closed67 reference witnesses of source_defined_task/task_contract without weakening current kind or source binding.','Resolve ordered_source_instructions source-action pointers, arbitrary closed criterion pass tags and current owner failure/history/release protocol.','Bridge exact existing minimum/equal/different/distinct_dates into graph guard whitelist.','Implement separately declared bounded maximum/reported_score_sum/nonempty_trimmed_text/source_policy_reported guards.','Preserve source tempo reduction debt/ceiling through retry/cancel/restart; native causal owner regression is mandatory before release.'],'future_guard_usage':dict(extensions),'native_execution':False,'runtime_admitted':False,'grants_credit':False,'official_acceptance_increment':0}
    metrics={'seconds':time.perf_counter()-start,'cached_files_hashed_once':c.hashes,'rows':len(rows),'source_contexts':len(contexts),'source_criteria':sum(len(x['program']['source_criteria']) for x in rows),'graph_nodes':sum(len(x['program']['graph']['nodes']) for x in rows),'quantitative_descriptors':sum(len(c['quantities']) for x in rows for c in x['program']['source_criteria']),'literal_instruction_lines':sum(len(o['implementation']['task_contract']['ordered_source_instructions']) for o in originals.values()),'source_contract_profiles':dict(profiles),'source_profiles_are_not_behavior_equivalence':True}
    return rows,closure,metrics,originals

def operators():
    return {'schema':'fathom.manual-source-criterion-operator-proposal.1','native_supported':False,'criterion_witness':{'source_kind':'source_defined_task','retained_contract_path':['implementation','task_contract'],'action_path':['ordered_source_instructions','closed integer index'],'literal_excerpt':'Exact start/end into single-space joined original instruction lines; source literal hash binds all characters, including headings/list numbers as metadata.','criterion_pass_tags':'Closed source_extent plus criterion_NNN IDs; tag binds actual failed criterion, never a supplied successful answer.','outcome':'reported_met/reported_not_met/unknown/null; rubric ratings instead rating_reported/unknown/null.','evidence':'Raw learner text, nullable; nonempty_trimmed_text diagnoses blank evidence and never rewrites history.','dates':'Two separately entered Gregorian date strings with independently reported daily outcomes/evidence, plus exact source count and D/U fields where directed.','optional':'Explicit choice route may leave only an authored optional duty unselected; all required duties remain.'},'existing_linear_shapes':{'minimum':{'kind':'minimum','field':'explicit payload field','value':'source integer floor'},'equal':{'kind':'equal','fields':['explicit field1','explicit field2']},'different':{'kind':'different','fields':['explicit field1','explicit field2']},'distinct_dates':{'kind':'distinct_dates','fields':['explicit field1','explicit field2']}},'proposed_closed_guards':{'maximum':{'fields':['kind','field','value'],'semantics':'Typed reported integer at or below the exact source ceiling; valid excess is diagnosed, not malformed.'},'reported_score_sum':{'fields':['kind','fields','total_field'],'semantics':'Exact finite reported rubric dimension integer sum equals the reported total; no listening/grading inference. All component reports retained; same_as_saved binds each rating to its earlier owned manual report.'},'nonempty_trimmed_text':{'fields':['kind','field','minimum','maximum'],'semantics':'Whitespace-only valid typed evidence is unresolved/diagnosed, retained unchanged. No trimming of saved learner evidence.'},'source_policy_reported':{'policies':{'tempo_choice_trigger':{'fields':['kind','policy','choice_field','error_count_field','tension_field','error_threshold'],'semantics':'Exact source threshold2 or reported tension requires reduction; below threshold and no tension permits hold or source-gated increase. Any unknown is unresolved; persistent native reduction debt remains mandatory.'},'reported_bpm_delta':{'fields':['kind','policy','before_field','after_field','minimum_delta','maximum_delta'],'semantics':'Positive manual prior/new BPM reports with exact source delta bound; no default or clock.'}}}},'failure':'Malformed/missing/type/unknown operator must refuse unchanged; well-formed negative/null criterion preserves report/history/diagnosis and owned release debt. Current owner execution remains deferred.'}

def validate_payload(s,value):
    types=s['type'] if isinstance(s['type'],list) else [s['type']]
    native='null' if value is None else 'boolean' if type(value) is bool else 'integer' if type(value) is int else 'string' if type(value) is str else 'array' if type(value) is list else 'object' if type(value) is dict else 'unsupported'
    require(native in types,'REPORT_TYPE')
    if 'enum' in s:require(any(type(value) is type(x) and value==x for x in s['enum']),'REPORT_ENUM')
    if value is None:return
    if native=='object':
        require(set(value)==set(s['required'])==set(s['properties']) and s['additionalProperties'] is False,'REPORT_PROPERTIES')
        for k,v in value.items():validate_payload(s['properties'][k],v)
    elif native=='array':
        require(s.get('minItems',0)<=len(value)<=s.get('maxItems',100000),'REPORT_ARRAY_LENGTH')
        for v in value:validate_payload(s['items'],v)
    elif native=='integer':require(s.get('minimum',-100000)<=value<=s.get('maximum',100000),'REPORT_INTEGER_RANGE')
    elif native=='string':require(s.get('minLength',0)<=len(value)<=s.get('maxLength',100000),'REPORT_TEXT_LENGTH')

def data_guard(g,payload,saved=None,failed=None):
    """Pure proposed DATA oracle, never native Task execution or learner autofill."""
    saved=saved or {};failed=failed or {};kind=g['kind']
    shapes={'minimum':{'kind','field','value'},'maximum':{'kind','field','value'},'equal':{'kind','fields'},'different':{'kind','fields'},'distinct_dates':{'kind','fields'},'nonempty_trimmed_text':{'kind','field','minimum','maximum'},'reported_score_sum':{'kind','fields','total_field'},'same_as_saved':{'kind','left','right'},'same_as_failed_pass':{'kind','payload_ref'}}
    if kind=='source_policy_reported':
        shapes[kind]={'kind','policy','choice_field','error_count_field','tension_field','error_threshold'} if g.get('policy')=='tempo_choice_trigger' else {'kind','policy','before_field','after_field','minimum_delta','maximum_delta'} if g.get('policy')=='reported_bpm_delta' else set()
    require(kind in shapes and set(g)==shapes[kind], 'CLOSED_GUARD_SHAPE')
    def get(name):require(name in payload,'MISSING_REPORT_FIELD');return payload[name]
    def resolve(r):
        val={'payload':payload,'saved':saved,'failed':failed}[r['scope']]
        for k in r['path']:require(isinstance(val,dict) and k in val,'MISSING_GUARD_REF');val=val[k]
        return val
    if kind in ('minimum','maximum'):
        x=get(g['field']);require(type(g['value']) is int and type(x) in (int,type(None)),'INTEGER_GUARD_TYPE');return x is not None and (x>=g['value'] if kind=='minimum' else x<=g['value'])
    if kind in ('equal','different','distinct_dates'):
        require(type(g['fields']) is list and len(g['fields'])==2 and all(type(x) is str for x in g['fields']),'COMPARE_FIELDS');a,b=[get(k) for k in g['fields']]
        if a is None or b is None:return False
        if kind=='distinct_dates':
            try:return bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}',a) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',b) and datetime.date.fromisoformat(a)!=datetime.date.fromisoformat(b))
            except (ValueError,TypeError):return False
        require(type(a) is type(b),'COMPARE_TYPE');return a==b if kind=='equal' else a!=b
    if kind=='nonempty_trimmed_text':
        x=get(g['field']);require(type(x) in (str,type(None)) and type(g['minimum']) is int and type(g['maximum']) is int and 0<g['minimum']<=g['maximum'],'TEXT_GUARD_TYPE');return type(x) is str and g['minimum']<=len(x.strip())<=g['maximum']
    if kind=='reported_score_sum':
        require(type(g['fields']) is list and 0<len(g['fields'])<=16 and len(set(g['fields']))==len(g['fields']),'SCORE_FIELDS');xs=[get(k) for k in g['fields']];total=get(g['total_field']);require(all(type(x) in (int,type(None)) for x in [*xs,total]),'SCORE_TYPES');return all(x is not None for x in [*xs,total]) and sum(xs)==total
    if kind=='same_as_saved':
        a,b=resolve(g['left']),resolve(g['right']);return a is not None and type(a) is type(b) and a==b
    if kind=='same_as_failed_pass':return resolve(g['payload_ref'])==failed.get('pass_tag') and failed.get('pass_tag') is not None
    if kind=='source_policy_reported':
        if g['policy']=='tempo_choice_trigger':
            errors=get(g['error_count_field']);tension=get(g['tension_field']);choice=get(g['choice_field']);return type(errors) is int and errors>=0 and type(tension) is bool and (choice=='reduce_after_errors_or_tension' if errors>=g['error_threshold'] or tension else choice in ('hold','increase_after_three_clean_trips'))
        if g['policy']=='reported_bpm_delta':
            a,b=get(g['before_field']),get(g['after_field']);return type(a) is int and type(b) is int and a>0 and b>0 and g['minimum_delta']<=b-a<=g['maximum_delta']
    raise BindingError('UNSUPPORTED_PROPOSED_GUARD')

def generate(root,out=OUT):
    rows,closure,metrics,_=build(root);target=Path(root)/out;require(not Path(out).is_absolute() and '..' not in Path(out).parts and target.resolve().is_relative_to(Path(root).resolve()),'OUTPUT_PATH');target.mkdir(exist_ok=False,parents=True)
    files={'definitions.jsonl':b''.join(encoded(x)+b'\n' for x in rows),'family-closure.json':encoded(closure)+b'\n','operator-proposal.json':encoded(operators())+b'\n'}
    # One shared bulk table; no original rows/source context copied per child.
    header=['#pragma once','#include <array>','namespace fathom::tasks::manual_source_assessments_generated {','struct Row { const char* key; const char* value; };','inline constexpr const char* closureSha256='+json.dumps(sha(encoded(closure)))+';','inline const std::array<Row,67> rows = {{']
    header += ['{'+json.dumps(x['source_key'])+','+json.dumps(encoded(x).decode(),ensure_ascii=False)+'},' for x in rows];header+=['}};','}'];files['GeneratedManualSourceAssessments.hpp']=('\n'.join(header)+'\n').encode()
    pins=[]
    for name,raw in files.items():
        path=target/name;path.open('xb').write(raw);pins.append({'path':str(path.relative_to(Path(root))),'bytes':len(raw),'sha256':sha(raw)})
    result={'outcome':'CLOSED67_SOURCE_CRITERION_GRAPH_DATA_PASS_NATIVE_AND_INDEPENDENT_PENDING','metrics':metrics,'files':pins,'original_txt_pdf_reads':0,'native_paths_executed':0,'official_acceptance_increment':0,'remaining_gates':closure['bridge_requirements']};(target/'generation-receipt.json').open('x').write(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',required=True);a.add_argument('--out',default=OUT);args=a.parse_args();print(json.dumps(generate(args.root,args.out)))
