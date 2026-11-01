"""Tag-only RC runner."""
import argparse,json,os
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
    state=read(a.state)
    config=json.loads(Path(a.config_snapshot).read_text(encoding="utf-8")) if a.config_snapshot else settings(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"],os.environ["GOOGLE_SHEET_ID"])[1]
    publish_questions(state,config)
    events=fetch_all_events()
    sync(state,events,lambda *args:None,mode="refresh")
    def make_tags(event,config,usage,classification):
        return generate(event,os.environ["GOCATH_OPENAI"],config,usage,classification)
    result=tag_sync(state,events,config,make_tags,mode=a.mode,limit=a.max_paid)
    write(a.state,state)
    path=Path(a.public)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(public_feed(state),ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
