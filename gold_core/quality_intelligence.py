from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import pandas as pd


def _b(v: Any) -> bool:
    if isinstance(v, bool): return v
    return str(v).strip().lower() in {"1","true","yes","y"}

def _s(v: Any) -> str:
    return "" if v is None else str(v).strip()

def _case_id(row: pd.Series) -> str:
    return f"S{_s(row.get('server','?'))}-R{_s(row.get('rank','?'))}-{_s(row.get('expected_name','unknown'))}"

def _classify(row: pd.Series) -> tuple[str,float,str,str]:
    reason=_s(row.get('gold_core_elimination_reason',''))
    block=_s(row.get('display_promotion_block_reason',''))
    pos=_s(row.get('character_position_action',''))
    unresolved=int(float(row.get('display_reconstruction_unresolved_targets',0) or 0))
    observed=int(float(row.get('display_reconstruction_observed_votes',0) or 0))
    if 'crop' in reason.lower() or 'crop' in block.lower() or pos in {'forced_position_acquisition','position_adaptive_multicrop_retry'}:
        return 'crop_geometry',0.92,'Run adaptive multi-crop acquisition on the weak character positions.','P1'
    if observed>0 or 'observed_votes' in reason:
        return 'vote_conflict',0.94,'Inspect competing OCR votes and require same-snapshot consensus before promotion.','P1'
    if unresolved>0 or 'unresolved' in reason:
        return 'character_segmentation',0.90,'Re-acquire only unresolved character positions with tighter segmentation.','P1'
    if 'promotion' in reason.lower() or block:
        return 'promotion_guard',0.88,'Review the promotion guard evidence; do not relax it without a regression case.','P2'
    if 'alliance' in reason.lower() or not _b(row.get('core_alliance_match',False)):
        return 'alliance_tag_extraction',0.86,'Validate the Basic-Latin alliance-tag crop and bracket segmentation separately from player names.','P2'
    if 'confusion' in reason.lower() or 'substitution' in reason.lower():
        return 'glyph_confusion',0.84,'Collect position-level evidence for the known glyph-confusion family; never infer identity.','P2'
    if _b(row.get('alignment_context_gap',False)):
        return 'context_gap_read_only',0.99,'Keep the case read-only until same-snapshot evidence exists.','P1'
    return 'evidence_conflict',0.70,'Inspect the evidence bundle and create a dedicated Gold Core regression case.','P3'

def build_gold_core_quality_intelligence(detail: pd.DataFrame, output_dir: Path) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    output_dir=Path(output_dir); output_dir.mkdir(parents=True,exist_ok=True)
    rows=[]
    for _,r in detail.iterrows():
        before=_b(r.get('gold_core_blocker_before_elimination',r.get('gold_core_blocker',False)))
        after=_b(r.get('gold_core_blocker_after_elimination',r.get('gold_core_blocker',False)))
        if not (before or after or _b(r.get('gold_core_elimination_candidate',False))): continue
        cause,conf,rec,priority=_classify(r)
        rows.append({
            'case_id':_case_id(r),'server':r.get('server',''),'rank':r.get('rank',''),
            'expected_name':r.get('expected_name',''),'expected_alliance_display':r.get('expected_alliance_display',''),
            'root_cause':cause,'root_cause_confidence':conf,'priority':priority,
            'recommendation':rec,'elimination_action':r.get('gold_core_elimination_action',''),
            'elimination_reason':r.get('gold_core_elimination_reason',''),'blocker_before':before,'blocker_after':after,
            'resolved':bool(before and not after),'operational_truth_modified':False,
        })
    details=pd.DataFrame(rows)
    if details.empty:
        summary=pd.DataFrame([{'phase':'v0.9.5.143_gold_core_strike_iv','cases':0,'open_cases':0,'resolved_cases':0,'operational_truth_modified':False}])
    else:
        summary=details.groupby(['root_cause','priority'],dropna=False).agg(cases=('case_id','count'),open_cases=('blocker_after','sum'),resolved_cases=('resolved','sum'),avg_confidence=('root_cause_confidence','mean')).reset_index()
        summary.insert(0,'phase','v0.9.5.143_gold_core_strike_iv'); summary['operational_truth_modified']=False
    mem_path=output_dir/'gold_core_failure_memory.json'
    old={}
    if mem_path.exists():
        try: old={x['case_id']:x for x in json.loads(mem_path.read_text(encoding='utf-8')).get('cases',[])}
        except Exception: old={}
    now=datetime.now(timezone.utc).isoformat()
    memory=[]
    for row in rows:
        prev=old.get(row['case_id'],{})
        first=prev.get('first_seen',now)
        seen=int(prev.get('times_seen',0))+1
        memory.append({**row,'first_seen':first,'last_seen':now,'times_seen':seen,'resolved_at': now if row['resolved'] and not prev.get('resolved_at') else prev.get('resolved_at'),'regression_required':bool(row['resolved'])})
    memory_df=pd.DataFrame(memory)
    mem_path.write_text(json.dumps({'phase':'v0.9.5.143_gold_core_strike_iv','updated_at':now,'operational_truth_modified':False,'cases':memory},ensure_ascii=False,indent=2),encoding='utf-8')
    return summary,details,memory_df
