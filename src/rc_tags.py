"""Independent tag generation for RC events."""
import json
import requests
from .rc_delta import digest,fingerprints,event_id

def revision(cfg):
    return digest({k:cfg[k] for k in ("tag_prompt","tag_model","tag_limit")})

def generate(event,key,cfg,usage):
    if cfg["tag_limit"]==0:return []
    payload={"model":cfg["tag_model"],"instructions":"Generate only German search tags supported by the event. Return only tags, no reasons, no standard tags. Max "+str(cfg["tag_limit"])+" tags. Use topical guidance, ignoring its old output format:\n"+cfg["tag_prompt"],"input":json.dumps(event,ensure_ascii=False),"text":{"format":{"type":"json_schema","name":"rc_tags","strict":True,"schema":{"type":"object","additionalProperties":False,"properties":{"tags":{"type":"array","items":{"type":"string"}}},"required":["tags"]}}}}
    response=requests.post("https://api.openai.com/v1/responses",headers={"Authorization":"Bearer "+key},json=payload,timeout=(10,90))
    response.raise_for_status()
    body=response.json()
    if body.get("status")!="completed":raise ValueError("Tag generation incomplete")
    outputs=[c["text"] for item in body.get("output",[]) for c in item.get("content",[]) if c.get("type")=="output_text"]
    if len(outputs)!=1:raise ValueError("Missing tag output")
    raw=json.loads(outputs[0])["tags"]
    if not isinstance(raw,list) or any(not isinstance(x,str) for x in raw):raise ValueError("Invalid tag output")
    tags=[]
    for value in raw:
        tag=" ".join(value.split())
        if 2<=len(tag)<=60 and tag.casefold() not in {t.casefold() for t in tags}:tags.append(tag)
    usage.update({k:int((body.get("usage") or {}).get(k,0)) for k in ("input_tokens","output_tokens","total_tokens")})
    return tags[:cfg["tag_limit"]]

def tag_sync(state,events,cfg,tagger,mode="delta",limit=10):
    if mode not in ("delta","retag","refresh"):raise ValueError("Unknown mode")
    rev=revision(cfg)
    pending=[]
    if mode!="refresh":
        for event in events:
            key=event_id(event)
            if key not in state["events"]:continue
            old=state["events"][key].get("tagging") or {}
            content=fingerprints(event)["classification_hash"]
            if not old or old.get("content_hash")!=content or (mode=="retag" and old.get("revision")!=rev):
                pending.append((key,event,content))
    failures=[]
    successes=0
    for key,event,content in pending[:limit]:
        try:
            tags=tagger(event,cfg,{})
            state["events"][key]["tagging"]={"tags":tags,"revision":rev,"content_hash":content}
            successes+=1
        except Exception as exc:
            failures.append({"id":key,"type":type(exc).__name__})
    state["last_tag_run"]={"queued":len(pending),"tagged":successes,"failures":failures,"mode":mode}
    return state["last_tag_run"]
