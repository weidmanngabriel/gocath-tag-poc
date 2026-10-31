"""Manual RC catalog workflow."""
import argparse,json,os
from pathlib import Path
from .rc_catalog import read,write,publish_questions,start_campaign,sync,public_feed
from .config import settings
from .decisions_classify import classify_decisions
from .rc_import import fetch_all_events
from .rc_delta import event_id

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("delta","publish-questions","reclassify","continue","refresh"),required=True)
    p.add_argument("--state",default="state/catalog.json")
    p.add_argument("--public",default="public/catalog.json")
    p.add_argument("--max-paid",type=int,default=25)
    p.add_argument("--confirm",default="")
    a=p.parse_args()
    state=read(a.state)
    _,editable=settings(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"],os.environ["GOOGLE_SHEET_ID"])
    if a.mode=="publish-questions":
        print("Revision:",publish_questions(state,editable))
    else:
        events=fetch_all_events()
        mode=a.mode
        if a.mode=="reclassify":
            if a.confirm!="YES":raise ValueError("Full reclassification requires YES")
            for ev in events:state["events"].setdefault(event_id(ev),{"event":ev})
            print("Queued:",start_campaign(state))
            mode="continue"
        result=sync(state,events,lambda event,config,usage:
            classify_decisions(event,os.environ["GOCATH_OPENAI"],config,usage),max_paid=a.max_paid,mode=mode)
        print(json.dumps(result,ensure_ascii=False))
    write(a.state,state)
    dest=Path(a.public)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(public_feed(state),ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__":main()
