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
            result=classify_decisions(event,api_key,part_config,part_usage)
            combined.extend(result["criteria_scores"])
            for name in ("input_tokens","output_tokens","thinking_tokens","cached_tokens","total_tokens"):
                cumulative[name]=cumulative.get(name,0)+part_usage.get(name,0)
        usage.update(cumulative)
        return {"criteria_scores":combined}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("delta","publish-questions","reclassify","continue","refresh"),required=True)
    p.add_argument("--state",default="state/catalog.json")
    p.add_argument("--public",default="public/catalog.json")
    p.add_argument("--max-paid",type=int,default=25)
    p.add_argument("--confirm",default="")
    a=p.parse_args()
    state=read(a.state)
    before=copy.deepcopy(state)
    started_at=datetime.now(timezone.utc).isoformat()
    run_usage={k:0 for k in ('input_tokens','output_tokens','thinking_tokens','cached_tokens','total_tokens')}
    attempts=0
    _,editable=settings(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"],os.environ["GOOGLE_SHEET_ID"])
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
            if a.confirm!="YES":raise ValueError("Full reclassification requires YES")
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
        record={"run_id":os.environ.get("GITHUB_RUN_ID","manual"),"started_at":started_at,
                "finished_at":datetime.now(timezone.utc).isoformat(),"mode":mode,
                "source_count":result["source_count"],"queued":result["queued"],
                "attempted":attempts,"classified":result["classified"],
                "failed":len(result["failures"]),"usage":run_usage,
                "cost_usd_estimated":round(run_usage["input_tokens"]*.10/1000000,8),
                "cost_note":"Input-only estimate; output pricing not included"}
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
