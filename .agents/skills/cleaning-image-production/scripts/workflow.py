"""Source-faithful, local-only image queue. No network or generation API calls."""
import argparse
import csv
import hashlib
import json
import re
import shutil
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from bs4 import BeautifulSoup

FORBIDDEN = 'recovered images - do not scan'
REVIEW_CHECKS = ('task_visible','service_correct','realistic','equipment_correct','scene_diverse','crop_readable','pair_continuity','result_visible')

def safe(path):
    p = Path(path)
    if FORBIDDEN in str(p).lower(): raise ValueError('Protected directory is excluded before access')
    resolved = p.resolve()
    if FORBIDDEN in str(resolved).lower(): raise ValueError('Protected resolved directory is excluded')
    return resolved

def sha(path): return hashlib.sha256(safe(path).read_bytes()).hexdigest()
def slug(value): return re.sub(r'[^a-z0-9]+','-',value.lower()).strip('-')[:96] or 'image'
def now(): return datetime.now(timezone.utc).isoformat()
def text(node): return node.get_text(' ',strip=True) if node else ''

def selector(node):
    parts=[]
    while getattr(node,'name',None) and node.name!='[document]':
        siblings=node.parent.find_all(node.name,recursive=False) if node.parent else [node]
        parts.append(f'{node.name}:nth-of-type({siblings.index(node)+1})');node=node.parent
    return ' > '.join(reversed(parts))

def child(base,relative):
    base=safe(base);p=safe(base/relative)
    if base not in p.parents:raise ValueError('Path escaped output directory')
    return p

def load(output): return json.loads(child(output,'state.json').read_text(encoding='utf-8'))

@contextmanager
def state_lock(output):
    output=safe(output);output.mkdir(parents=True,exist_ok=True)
    with child(output,'.workflow.lock').open('a+b') as f:
        f.seek(0,2)
        if f.tell()==0:f.write(b'0');f.flush()
        f.seek(0)
        try:
            if os.name=='nt':
                import msvcrt;msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl;fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as e:raise ValueError('Another state writer is active; retry after it completes') from e
        try:yield
        finally:
            f.seek(0)
            if os.name=='nt':msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(f.fileno(),fcntl.LOCK_UN)

def save(output,state):
    output=safe(output)
    with state_lock(output):
        target=child(output,'state.json');temporary=child(output,'state.json.tmp')
        old=json.loads(target.read_text(encoding='utf-8')) if target.exists() else {}
        if old.get('revision',0)!=state.get('revision',0):raise ValueError('Stale state writer rejected; reload checkpoint before retry')
        state['revision']=old.get('revision',0)+1;state['updated_utc']=now()
        groups={}
        for r in state['slots']:groups.setdefault(r['page_folder'],[]).append(r)
        old_groups={}
        for r in old.get('slots',[]):old_groups.setdefault(r['page_folder'],[]).append(r)
        for folder,records in groups.items():
            page=safe(folder)
            if output not in page.parents:raise ValueError('Page folder escaped output')
            if records!=old_groups.get(folder):child(page,'slots.json').write_text(json.dumps(records,indent=2,ensure_ascii=False),encoding='utf-8')
        temporary.write_text(json.dumps(state,indent=2,ensure_ascii=False),encoding='utf-8');temporary.replace(target)

def event(output,action,slot_id,details):
    with child(output,'events.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps({'time':now(),'action':action,'slot_id':slot_id,'details':details})+'\n')

def initialize(source,output,city):
    source=safe(source);output=safe(output)
    if source==output or source in output.parents or output in source.parents: raise ValueError('Source and output trees must be disjoint')
    files=sorted(source.glob('*.html')) # Deliberately no recursion or whole-drive scan.
    files=[safe(p) for p in files]
    if not files: raise ValueError('No top-level source HTML files; specify the exact source folder')
    fingerprints={str(p):sha(p) for p in files}
    if child(output,'state.json').exists():
        previous=load(output)
        if previous['source_hashes']!=fingerprints or previous['city']!=city: raise ValueError('Source/city drift; preserve current queue and reconcile affected pages explicitly')
        return previous
    state={'schema_version':1,'city':city,'source':str(source),'output':str(output),'source_hashes':fingerprints,'created_utc':now(),'slots':[],'deployment_access_allowed':False}
    for p in files:
        soup=BeautifulSoup(p.read_bytes(),'html.parser');sections=soup.find_all('section');page_title=text(soup.h1)
        canonical=soup.find('link',rel='canonical');url=canonical.get('href','') if canonical else ''
        category='Commercial' if '/commercial/' in url else 'Residential' if '/residential/' in url else 'Residential and Commercial'
        page=child(output,Path('pages')/category/p.stem);page.mkdir(parents=True,exist_ok=True);child(page,'images').mkdir(exist_ok=True)
        shutil.copy2(p,child(page,'source.html'))
        if sha(child(page,'source.html'))!=fingerprints[str(p)]:raise ValueError('Source changed during copy')
        page_slots=[]
        def add(node,role,n,pair_id='',caption=''):
            sec=node.find_parent('section');index=next((i+1 for i,x in enumerate(sections) if x is sec),0);heading=text(sec.find(['h1','h2'])) if sec else ''
            context=' | '.join(text(x) for x in sec.find_all('p')[:4])[:1800] if sec else ''
            slot_id=f'{p.stem}--section-{index:02}--{role}-{n:02}'
            name=f'{slot_id}--{slug(caption or heading)}.webp'
            query=f'{city} {page_title} {caption or heading} professional cleaning photograph'
            pair_rule='Preserve the same room, fixtures and target object as the opposite side; camera angle can vary only if identity remains clear.' if pair_id else ''
            work_rule='Show the rug boundaries and a human using an appropriate professional cleaning tool.' if role=='before' and 'rug' in p.stem else 'Show the task and target clearly; use equipment only if appropriate.'
            if role=='after':work_rule='Show the finished target with a clearly visible improvement. Do not force a person or machine into the AFTER scene.'
            brief=f'Create an illustrative professional cleaning photograph for {page_title}, {city}, Australia. Role: {role}. Section: {heading}. Target context: {caption or context}. {work_rule} {pair_rule} Use natural believable light, intact anatomy, plausible material textures and tool contact. Keep the target readable at card size. Match actual owner equipment references when applicable; otherwise record equipment none with a reason. Vary service-appropriate architecture, viewpoint and materials across the page, without scene drift within a pair. No decorative ribbons, graphic airflow, fake brand/model text, customer-job claim, invented business address or rendered marketing text. Source prose is context, not independently verified business evidence.'
            img=node.find('img');existing=img.get('src','') if img else ''
            if not existing:
                match=re.search(r'url\([\s\"\']*([^\)\"\']+)',node.get('style',''))
                if match:existing=match.group(1).strip()
            r={'slot_id':slot_id,'page_file':p.name,'page_title':page_title,'category':category,'section_number':index,'section_heading':heading,'dom_selector':selector(node),'role':role,'pair_id':pair_id,'caption':caption,'source_context':context,'source_sha256':fingerprints[str(p)],'source_path':str(p),'page_folder':str(page),'filename':name,'google_images_url':'https://www.google.com/search?tbm=isch&q='+quote(query),'prompt_brief':brief,'existing_source':existing,'status':'existing_assignment' if existing else 'pending','attempts':0,'equipment_preflight':None,'asset_path':'','asset_sha256':'','provenance':'EXISTING_SOURCE_UNVERIFIED' if existing else 'UNASSIGNED','job_verified':False,'review':None,'owner_approved':False,'approval_evidence':''}
            page_slots.append(r);state['slots'].append(r)
        for n,node in enumerate(soup.select('.ph'),1):
            sec=node.find_parent('section');index=next((i+1 for i,x in enumerate(sections) if x is sec),0)
            gallery=any('job-imgs' in a.get('class',[]) for a in node.parents if getattr(a,'attrs',None) is not None)
            add(node,'hero' if index==1 else 'gallery' if gallery else 'supporting',n)
        for n,pair in enumerate(soup.select('.ba'),1):
            cap=pair.parent.select_one('.cap');control=pair.select_one('input.ba-range');caption=text(cap) or (control.get('aria-label','') if control else '')
            layers=pair.select('.ba-layer')
            if len(layers)!=2:raise ValueError(f'{p.name}: comparison must have exactly two layers')
            for layer in layers:add(layer,'before' if layer.has_attr('data-before') or 'ba-before' in layer.get('class',[]) else 'after',n,f'{p.stem}--pair-{n:02}',caption)
        child(page,'slots.json').write_text(json.dumps(page_slots,indent=2,ensure_ascii=False),encoding='utf-8')
        child(page,'PROMPTS.md').write_text('\n\n'.join('## '+r['slot_id']+'\n\n'+r['prompt_brief'] for r in page_slots),encoding='utf-8')
    if len({r['slot_id'] for r in state['slots']})!=len(state['slots']):raise ValueError('Duplicate slot identities')
    save(output,state)
    with child(output,'datasheet.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['slot_id','page_file','page_title','category','section_number','section_heading','dom_selector','role','pair_id','caption','source_context','source_sha256','filename','google_images_url','prompt_brief']
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(state['slots'])
    event(output,'initialize','',{'pages':len(files),'image_positions':len(state['slots'])});return state

def get_slot(state,slot_id):
    for r in state['slots']:
        if r['slot_id']==slot_id:return r
    raise ValueError('Unknown slot ID')

def checked(output,slot_id,allow_existing=False):
    state=load(output);r=get_slot(state,slot_id)
    if r['owner_approved']:raise ValueError('Owner-approved asset locked')
    if r['status']=='existing_assignment' and not allow_existing:raise ValueError('Existing source assignment preserved; use import-existing with direct evidence')
    if sha(r['source_path'])!=r['source_sha256']:raise ValueError('Source drift for this page')
    return state,r

def preflight(output,slot_id,equipment,reason,evidence):
    state,r=checked(output,slot_id)
    if not equipment or not reason.strip() or not evidence.strip():raise ValueError('Equipment selection, task reason and reference-check evidence required')
    r['equipment_preflight']={'equipment':equipment,'reason':reason,'reference_check_evidence':evidence,'recorded_at':now()};save(output,state);event(output,'preflight',slot_id,r['equipment_preflight'])

def authorize_retry(output,slot_id,evidence,changed_approach):
    state,r=checked(output,slot_id)
    if not evidence.strip() or not changed_approach.strip():raise ValueError('Direct owner authorization and a changed approach are required')
    r['retry_authorization']={'owner_evidence':evidence,'changed_approach':changed_approach,'time':now(),'previous_total_attempts':r['attempts']}
    r['attempts_since_authorization']=0;r['equipment_preflight']=None;r['status']='pending';save(output,state);event(output,'authorize_retry',slot_id,r['retry_authorization'])

def register(output,slot_id,asset,provenance='OWNER_SUPPLIED',allow_existing=False):
    state,r=checked(output,slot_id,allow_existing);asset=safe(asset)
    if r.get('attempts_since_authorization',r['attempts'])>=3:raise ValueError('Three attempts reached; use authorize-retry only with actual owner permission and changed approach')
    if provenance not in ['OWNER_SUPPLIED','AI_ILLUSTRATIVE']:raise ValueError('Unsupported provenance')
    if provenance=='AI_ILLUSTRATIVE' and not r['equipment_preflight']:raise ValueError('Equipment preflight missing')
    suffix=asset.suffix.lower()
    if suffix not in ['.webp','.jpg','.jpeg','.png']:raise ValueError('Unsupported image extension')
    if not asset.is_file() or asset.stat().st_size==0:raise ValueError('Asset missing or empty')
    page=safe(r['page_folder']);output=safe(output)
    if output not in page.parents:raise ValueError('Page folder escaped output')
    version=r['attempts']+1;dest=safe(page/'images'/(Path(r['filename']).stem+f'--v{version}'+suffix))
    if output not in dest.parents or dest.exists():raise ValueError('Unsafe or existing asset destination')
    shutil.copy2(asset,dest);r.update(asset_path=str(dest),asset_sha256=sha(dest),status='generated',provenance=provenance,attempts=version,attempts_since_authorization=r.get('attempts_since_authorization',r['attempts'])+1,job_verified=False,review=None,last_equipment_preflight=r['equipment_preflight'],equipment_preflight=None)
    save(output,state);event(output,'register',slot_id,{'asset':str(dest),'sha256':r['asset_sha256'],'provenance':provenance});return r

def import_existing(output,slot_id,asset,evidence):
    state,r=checked(output,slot_id,allow_existing=True)
    if r['status']!='existing_assignment' or not evidence.strip():raise ValueError('Existing assignment and explicit owner mapping evidence required')
    r['assignment_import_evidence']=evidence;save(output,state)
    return register(output,slot_id,asset,'OWNER_SUPPLIED',allow_existing=True)

def verify_asset(r):
    if not r['asset_path'] or sha(r['asset_path'])!=r['asset_sha256']:raise ValueError('Asset missing or changed since registration')

def review(output,slot_id,checks,evidence):
    state,r=checked(output,slot_id);verify_asset(r)
    if not evidence.strip() or any(checks.get(k) is not True for k in REVIEW_CHECKS):raise ValueError('Every visual check and concrete review evidence required; record non-applicable check reasons separately')
    r['review']={'checks':checks,'evidence':evidence,'asset_sha256':r['asset_sha256'],'time':now()};r['status']='reviewed';save(output,state);event(output,'review',slot_id,r['review'])

def approve(output,slot_id,evidence):
    state,r=checked(output,slot_id);verify_asset(r)
    if r['status']!='reviewed' or not r['review'] or r['review']['asset_sha256']!=r['asset_sha256'] or not evidence.strip():raise ValueError('Exact revision review and direct owner approval evidence required')
    r.update(owner_approved=True,approval_evidence=evidence,status='owner_approved');save(output,state);event(output,'approve',slot_id,{'evidence':evidence,'asset_sha256':r['asset_sha256']})

def next_slot(output,page_file=None):
    state=load(output);active=[r for r in state['slots'] if not r['owner_approved'] and r['status'] in ['pending','generated'] and (not page_file or r['page_file']==page_file)]
    if not active:
        waiting=[r for r in state['slots'] if r['status'] in ['reviewed','existing_assignment'] and (not page_file or r['page_file']==page_file)]
        if not waiting:return None
        r=waiting[0]
        if sha(r['source_path'])!=r['source_sha256']:raise ValueError('Source drift; stale context must not be used')
        return {**r,'next_action':'request_owner_approval' if r['status']=='reviewed' else 'reconcile_existing_assignment'}
    pages=sorted({r['page_file'] for r in active});current=pages[0]
    order={'hero':0,'before':1,'after':2,'supporting':3,'gallery':4}
    within=sorted([r for r in active if r['page_file']==current],key=lambda r:(0 if r['status']=='generated' else 1,order[r['role']],r['slot_id']))
    r=within[0]
    if sha(r['source_path'])!=r['source_sha256']:raise ValueError('Source drift; stale context must not be used')
    return {**r,'next_action':'review' if r['status']=='generated' else 'generate'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);subs=parser.add_subparsers(dest='command',required=True)
    init=subs.add_parser('init');init.add_argument('--source',required=True);init.add_argument('--output',required=True);init.add_argument('--city',required=True)
    for name in ['next','status','preflight','register','review','approve','authorize-retry','import-existing']:
        sub=subs.add_parser(name);sub.add_argument('--output',required=True)
        if name not in ['next','status']:sub.add_argument('--slot',required=True)
        if name=='next':sub.add_argument('--page')
        if name=='preflight':
            sub.add_argument('--equipment',required=True);sub.add_argument('--reason',required=True);sub.add_argument('--evidence',required=True)
        if name=='register':sub.add_argument('--asset',required=True);sub.add_argument('--provenance',required=True,choices=['OWNER_SUPPLIED','AI_ILLUSTRATIVE'])
        if name=='review':sub.add_argument('--checks',required=True);sub.add_argument('--evidence',required=True)
        if name=='approve':sub.add_argument('--evidence',required=True)
        if name=='authorize-retry':sub.add_argument('--evidence',required=True);sub.add_argument('--approach',required=True)
        if name=='import-existing':sub.add_argument('--asset',required=True);sub.add_argument('--evidence',required=True)
    a=parser.parse_args()
    try:
        if a.command=='init':s=initialize(a.source,a.output,a.city);result={'pages':len(s['source_hashes']),'image_positions':len(s['slots'])}
        elif a.command=='next':result=next_slot(a.output,a.page)
        elif a.command=='status':
            s=load(a.output);result={'slots':len(s['slots']),'counts':{k:sum(r['status']==k for r in s['slots']) for k in ['pending','generated','reviewed','owner_approved','existing_assignment']}}
        elif a.command=='preflight':preflight(a.output,a.slot,a.equipment,a.reason,a.evidence);result={'recorded':True}
        elif a.command=='register':result=register(a.output,a.slot,a.asset,a.provenance)
        elif a.command=='review':review(a.output,a.slot,json.loads(safe(a.checks).read_text(encoding='utf-8')),a.evidence);result={'reviewed':True}
        elif a.command=='authorize-retry':authorize_retry(a.output,a.slot,a.evidence,a.approach);result={'new_retry_cycle_authorized':True}
        elif a.command=='import-existing':result=import_existing(a.output,a.slot,a.asset,a.evidence)
        else:approve(a.output,a.slot,a.evidence);result={'owner_approved':True}
        print(json.dumps(result,indent=2,ensure_ascii=False))
    except (ValueError,OSError,KeyError) as error:parser.exit(2,str(error)+'\n')

if __name__=='__main__':main()
