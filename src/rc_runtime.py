"""Manual RC catalog workflow."""
import argparse,copy,json,os
from datetime import datetime,timezone
from pathlib import Path
from .rc_catalog import read,write,publish_questions,start_campaign,sync,public_feed
from .config import settings
from .decisions_classify import classify_decisions
from .rc_import import fetch_all_events
from .rc_delta import event_id

def classify_with_fallback(event, api_key, config, usage):
    """Recover one malformed Decisions response using smaller question batches."""
    try:
        return classify_decisions(event,api_key,config,usage)
    except ValueError as exc:
        if not str(exc).startswith("Decisions ") or len(config["criteria"])<2:
            raise
        print("Invalid Decisions response; retrying as two criterion batches:", str(exc), flush=True)
        criteria=config["criteria"]
        split=(len(criteria)+1)//2
        combined=[]
        cumulative=dict(usage)
        for part in (criteria[:split],criteria[split:]):
            part_config=dict(config,criteria=part)
            part_usage={}
            try:
                result=classify_decisions(event,api_key,part_config,part_usage)
                combined.extend(result["criteria_scores"])
            finally:
                for name in ("input_tokens","output_tokens","thinking_tokens","cached_tokens","cache_write_tokens","cache_write_12h_tokens","total_tokens"):
                    cumulative[name]=cumulative.get(name,0)+part_usage.get(name,0)
                usage.update(cumulative)
        usage.update(cumulative)
        return {"criteria_scores":combined}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("delta","publish-questions","reclassify","continue","refresh"),required=True)
    p.add_argument("--state",default="state/catalog.json")
    p.add_argument("--public",default="public/catalog.json")
    p.add_argument("--max-paid",type=int,default=200)
    a=p.parse_args()
    state=read(a.state)
    before=copy.deepcopy(state)
    started_at=datetime.now(timezone.utc).isoformat()
    run_usage={k:0 for k in ('input_tokens','output_tokens','thinking_tokens','cached_tokens','cache_write_tokens','cache_write_12h_tokens','total_tokens')}
    attempts=0
    _,editable=settings(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"],os.environ["GOOGLE_SHEET_ID"])
    prices={k:float(editable[k]) for k in ("rc_input_per_million_usd","rc_cached_input_per_million_usd","rc_cache_write_per_million_usd","rc_cache_write_12h_per_million_usd","rc_output_per_million_usd")}
    if any(not (0<=v<1000000) for v in prices.values()):raise ValueError("RC prices must be nonnegative finite values")
    if editable["rc_model"]!="gpt-6-luna":raise ValueError("Unsupported RC Decisions model")
    if a.mode=="publish-questions":
        revision=publish_questions(state,editable)
        print("Published questionnaire revision:", revision,
              "active criteria:", len(state["active_questionnaire"]["criteria"]), flush=True)
        if not state["active_questionnaire"]["criteria"]:
            raise ValueError("No active Criteria in the configured Google Sheet; refusing empty questionnaire publication")
    else:
        events=fetch_all_events()
        mode=a.mode
        if a.mode=="reclassify":
            for ev in events:state["events"].setdefault(event_id(ev),{"event":ev})
            print("Queued:",start_campaign(state))
            mode="continue"
        def measured_classify(event,config,usage):
            nonlocal attempts
            attempts+=1
            try:
                return classify_with_fallback(event,os.environ["GOCATH_OPENAI"],config,usage)
            finally:
                for name in run_usage:
                    run_usage[name]+=int(usage.get(name,0) or 0)
        result=sync(state,events,measured_classify,max_paid=a.max_paid,mode=mode)
        print(json.dumps(result,ensure_ascii=False))
        read_tokens=run_usage["cached_tokens"]
        written_tokens=run_usage["cache_write_tokens"]
        written_12h=min(written_tokens,run_usage["cache_write_12h_tokens"])
        ordinary_tokens=run_usage["input_tokens"]-read_tokens-written_tokens
        if ordinary_tokens<0:
            raise ValueError("Invalid Decisions usage: cached and written tokens exceed input tokens")
        cost=(ordinary_tokens*prices["rc_input_per_million_usd"]
              +read_tokens*prices["rc_cached_input_per_million_usd"]
              +(written_tokens-written_12h)*prices["rc_cache_write_per_million_usd"]
              +written_12h*prices["rc_cache_write_12h_per_million_usd"]
              +run_usage["output_tokens"]*prices["rc_output_per_million_usd"])/1000000
        record={"run_id":os.environ.get("GITHUB_RUN_ID","manual"),"started_at":started_at,
                "finished_at":datetime.now(timezone.utc).isoformat(),"mode":mode,
                "source_count":result["source_count"],"queued":result["queued"],
                "attempted":attempts,"classified":result["classified"],
                "failed":len(result["failures"]),"usage":run_usage,
                "cost_usd_estimated":round(cost,8),
                "prices_per_million_usd":dict(prices),
                "pricing_model":editable["rc_model"],
                "cost_note":"Estimate based on configured per-million-token prices; not an API invoice"}
        Path("state/rc-run-record.json").write_text(json.dumps(record,ensure_ascii=False),encoding="utf-8")
    def material(data):
        return {key:value for key,value in data.items() if key not in ("last_run","last_sync_at")}
    if material(before)==material(state):
        print("No catalog changes; skipping rc-data publication",flush=True)
        Path("state/rc-no-changes.flag").write_text("unchanged",encoding="utf-8")
        return
    write(a.state,state)
    dest=Path(a.public)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(public_feed(state),ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__":main()
