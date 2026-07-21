from pathlib import Path
import pandas as pd
from gold_core.quality_intelligence import build_gold_core_quality_intelligence

def test_strike_iv_classifies_and_persists_failure_memory(tmp_path: Path):
    detail=pd.DataFrame([{
        'server':551,'rank':12,'expected_name':'Joncollins21','expected_alliance_display':'[ABC]',
        'gold_core_blocker_before_elimination':True,'gold_core_blocker_after_elimination':True,
        'gold_core_elimination_candidate':True,'gold_core_elimination_reason':'strike_iii_blocked_unresolved_fragments',
        'display_reconstruction_unresolved_targets':1,'display_reconstruction_observed_votes':0,
        'core_alliance_match':True,'alignment_context_gap':False,
    }])
    summary, rows, memory=build_gold_core_quality_intelligence(detail,tmp_path)
    assert rows.iloc[0]['root_cause']=='character_segmentation'
    assert rows.iloc[0]['operational_truth_modified'] == False
    assert (tmp_path/'gold_core_failure_memory.json').exists()
    _,_,memory2=build_gold_core_quality_intelligence(detail,tmp_path)
    assert int(memory2.iloc[0]['times_seen'])==2
