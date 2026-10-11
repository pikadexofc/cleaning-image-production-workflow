"""Supported recovery entrypoint. Legacy workflow.py is a low-level state library."""
import argparse
import json
from pathlib import Path
import workflow as w
import policy

def record_review(output, slot_id, observations, evidence):
    state, slot = w.checked(output, slot_id)
    w.verify_asset(slot)
    proof=w.safe(evidence)
    if not proof.is_file() or not proof.read_text(encoding='utf-8').strip():
        raise ValueError('A real saved review evidence file is required')
    decoded=policy.technical(slot['asset_path'])
    policy.acceptance(slot, observations)
    if slot.get('pair_id'):
        others=[r for r in state['slots'] if r.get('pair_id')==slot['pair_id'] and r['slot_id']!=slot_id]
        if len(others)!=1 or not others[0].get('asset_path'):
            raise ValueError('Opposite pair asset missing; cannot certify continuity')
        w.verify_asset(others[0]);policy.technical(others[0]['asset_path'])
        if others[0]['asset_sha256']==slot['asset_sha256']:
            raise ValueError('Before and after have identical bytes; no result difference')
    slot['policy_review']={'version':policy.POLICY_VERSION,'observations':observations,
        'technical':decoded,'evidence_path':str(proof),'evidence_sha256':w.sha(proof),
        'asset_sha256':slot['asset_sha256'],'time':w.now()}
    slot['review']={'checks':{k:True for k in w.REVIEW_CHECKS},'evidence':str(proof),
                   'asset_sha256':slot['asset_sha256'],'time':w.now()}
    slot['status']='reviewed';w.save(output,state);w.event(output,'policy_review',slot_id,slot['policy_review'])

def approve(output, slot_id, evidence):
    state,slot=w.checked(output,slot_id);review=slot.get('policy_review',{})
    if review.get('version')!=policy.POLICY_VERSION or review.get('asset_sha256')!=slot['asset_sha256']:
        raise ValueError('Current policy review is required, legacy review is insufficient')
    if w.sha(review['evidence_path'])!=review['evidence_sha256']:
        raise ValueError('Review evidence changed')
    policy.acceptance(slot,review['observations']);policy.technical(slot['asset_path'])
    owner=w.safe(evidence)
    if not owner.is_file() or slot['asset_sha256'] not in owner.read_text(encoding='utf-8'):
        raise ValueError('Direct owner approval record must identify the exact asset hash')
    w.approve(output,slot_id,str(owner))

def next_item(output,page=None):
    state=w.load(output)
    blocked=[r for r in state['slots'] if r.get('status')=='blocked' and (not page or r['page_file']==page)]
    if blocked:return {**blocked[0],'next_action':'resolve_block','blocked_reason':blocked[0].get('blocked_reason','')}
    return w.next_slot(output,page)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['next','status','preflight','register','review','approve','block','unblock','authorize-retry','import-existing'])
    p.add_argument('--output',required=True);p.add_argument('--slot');p.add_argument('--page');p.add_argument('--asset');p.add_argument('--evidence');p.add_argument('--observations');p.add_argument('--equipment');p.add_argument('--reason');p.add_argument('--approach');p.add_argument('--provenance',choices=['AI_ILLUSTRATIVE','OWNER_SUPPLIED'])
    a=p.parse_args()
    try:
        if a.command=='next':result=next_item(a.output,a.page)
        elif a.command=='status':
            s=w.load(a.output);counts={}
            for r in s['slots']:counts[r['status']]=counts.get(r['status'],0)+1
            result={'counts':counts,'slots':len(s['slots']),'policy_version':policy.POLICY_VERSION}
        else:
            if not a.slot:raise ValueError('--slot required')
            if a.command=='review':
                if not a.observations or not a.evidence:raise ValueError('--observations and --evidence required')
                record_review(a.output,a.slot,json.loads(w.safe(a.observations).read_text(encoding='utf-8')),a.evidence)
            elif a.command=='approve':approve(a.output,a.slot,a.evidence or '')
            elif a.command=='register':
                if not a.asset or not a.provenance:raise ValueError('--asset and --provenance required')
                policy.technical(a.asset);w.register(a.output,a.slot,a.asset,a.provenance)
            elif a.command=='preflight':
                if not a.evidence:raise ValueError('Checker evidence file required')
                evidence=json.loads(w.safe(a.evidence).read_text(encoding='utf-8'))
                for k in ('service','task','purpose','reason','catalogue_sha256','equipment'):
                    if k not in evidence:raise ValueError('Incomplete checker evidence: '+k)
                if not a.equipment:raise ValueError('--equipment required')
                selected=[] if a.equipment=='none' else a.equipment.split(',')
                actual=[x if isinstance(x,str) else x.get('id') for x in evidence['equipment']]
                if set(selected)!=set(actual):raise ValueError('Selected equipment differs from checker evidence')
                w.preflight(a.output,a.slot,a.equipment,a.reason or evidence['reason'],a.evidence)
            elif a.command=='authorize-retry':w.authorize_retry(a.output,a.slot,a.evidence or '',a.approach or '')
            elif a.command=='import-existing':
                if not a.asset:raise ValueError('--asset required')
                policy.technical(a.asset);w.import_existing(a.output,a.slot,a.asset,a.evidence or '')
            else:
                state,slot=w.checked(a.output,a.slot)
                if not a.reason:raise ValueError('Concrete blocker or resolution reason required')
                if a.command=='block':slot.update(status='blocked',blocked_reason=a.reason,resume_status=slot['status'])
                else:
                    if slot['status']!='blocked':raise ValueError('Slot is not blocked')
                    slot['status']=slot.get('resume_status','pending');slot['resolution_evidence']=a.reason
                w.save(a.output,state);w.event(a.output,a.command,a.slot,{'reason':a.reason})
            result={'saved':True}
        print(json.dumps(result,indent=2))
    except (ValueError,OSError,KeyError,TypeError) as e:p.exit(2,str(e)+'\n')

if __name__=='__main__':main()
