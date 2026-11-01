"""Tag-only RC runner."""
import argparse,json,os
from datetime import datetime,timezone
from pathlib import Path
from .rc_catalog import read,write,publish_questions,sync,public_feed
from .rc_import import fetch_all_events
from .config import settings
from .rc_tags import generate,tag_sync

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("delta","retag","refresh"),required=True)
    p.add_argument("--state",default="state/catalog.json")
    p.add_argument("--public",default="public/catalog.json")
    p.add_argument("--max-paid",type=int,default=10)
    p.add_argument("--config-snapshot")
    a=p.parse_args()
    started_at=datetime.now(timezone.utc).isoformat()
    state=read(a.state)
    config=json.loads(Path(a.config_snapshot).read_text(encoding="utf-8")) if a.config_snapshot else settings(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"],os.environ["GOOGLE_SHEET_ID"])[1]
    publish_questions(state,config)
    events=fetch_all_events()
    sync(state,events,lambda *args:None,mode="refresh")
    def make_tags(event,config,usage,classification):
        return generate(event,os.environ["GOCATH_OPENAI"],config,usage,classification)
    usage={}
    result=tag_sync(state,events,config,make_tags,mode=a.mode,limit=a.max_paid,run_usage=usage)
    attempts=result["tagged"]+len(result["failures"])
    input_rate=config.get("tag_input_per_million_usd")
    output_rate=config.get("tag_output_per_million_usd")
    cost=None
    if input_rate not in (None,"") and output_rate not in (None,""):
        rates=(float(input_rate),float(output_rate))
        if any(not (0<=v<1000000) for v in rates):raise ValueError("Invalid tag pricing")
        cost=round((usage.get("input_tokens",0)*rates[0]+usage.get("output_tokens",0)*rates[1])/1000000,8)
    record={"kind":"tagging","run_id":os.environ.get("GITHUB_RUN_ID","manual"),
        "started_at":started_at,"finished_at":datetime.now(timezone.utc).isoformat(),
        "mode":a.mode,"source_count":len(events),"queued":result["queued"],
        "attempted":attempts,"tagged":result["tagged"],"failed":len(result["failures"]),
        "usage":usage,"pricing_model":config["tag_model"],"cost_usd_estimated":cost,
        "cost_note":"Estimate using configured tag token prices; null when not configured"}
    Path("state/rc-run-record.json").write_text(json.dumps(record,ensure_ascii=False),encoding="utf-8")
    write(a.state,state)
    path=Path(a.public)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(public_feed(state),ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
