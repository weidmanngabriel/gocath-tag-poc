"""Persistent and resumable RC catalog; no automatic schedule."""
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from .rc_delta import event_id, fingerprints, canonical_event, digest
from .decisions_classify import MODEL

def now():
    return datetime.now(timezone.utc).isoformat()

def read(path):
    path=Path(path)
    state=json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema_version":1,"events":{},"active_questionnaire":None,"campaign":None}
    if state.get("schema_version")!=1 or not isinstance(state.get("events"),dict):
        raise ValueError("Invalid catalog state")
    return state

def write(path,data):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(path)

def publish_questions(state,config):
    rev=digest(config["criteria"])
    state["active_questionnaire"]={"revision":rev,"criteria":copy.deepcopy(config["criteria"]),
                                  "tags":copy.deepcopy(config.get("tags",[])),"published_at":now()}
    return rev

def active_config(state):
    q=state.get("active_questionnaire")
    if not q: raise RuntimeError("Publish the questionnaire before classification")
    return {"criteria":q["criteria"],"tags":q.get("tags",[])}

def criterion_signature(criterion):
    """Semantic fingerprint: display labels and thresholds do not invalidate AI answers."""
    return digest({"type":criterion.get("type","predicate"),
                   "label":criterion.get("label",""),
                   "description":criterion.get("description",""),
                   "options":criterion.get("options",[])})

def presentation_scores(classification, questionnaire):
    """Show only answers that still match the active question's semantic definition."""
    if not classification:
        return []
    current = {c["id"]:c for c in (questionnaire or {}).get("criteria",[])}
    signatures = classification.get("criterion_signatures",{})
    out = []
    for original in classification.get("scores",[]):
        criterion = current.get(original["id"])
        if criterion is None:
            continue
        # Legacy classifications have no per-question signature. Treat as unknown
        # when the questionnaire revision differs.
        if signatures:
            if signatures.get(original["id"]) != criterion_signature(criterion):
                continue
        elif classification.get("questionnaire_revision") != (questionnaire or {}).get("revision"):
            continue
        row = copy.deepcopy(original)
        row["category"] = criterion.get("category", row.get("category",""))
        row["label"] = criterion.get("label", row.get("label",""))
        if criterion.get("type","predicate") == "predicate":
            row["matched"] = row["score"] >= criterion.get("threshold",0.65)
        out.append(row)
    return out

def relevance(scores,config):
    weights={c["id"]:c["weight"] for c in config["criteria"]}
    signals=[s["score"]*weights.get(s["id"],0) for s in scores if weights.get(s["id"],0)>0]
    strong=any(s>=.7 for s in signals) or sum(s>=.45 for s in signals)>=2
    return {"score":round(min(1,max(signals,default=0)),4),
            "status":"likely_relevant" if strong else "review" if any(s>=.25 for s in signals) else "likely_not_relevant"}

def start_campaign(state):
    if not state.get("active_questionnaire"): raise RuntimeError("No active questionnaire")
    if state.get("campaign") and state["campaign"]["pending"]:
        raise RuntimeError("Full reclassification already in progress")
    state["campaign"]={"revision":state["active_questionnaire"]["revision"],"started_at":now(),
                       "pending":sorted(state["events"])}
    return len(state["campaign"]["pending"])

def permanent_classification_failure(exc):
    return isinstance(exc, ValueError) and (str(exc).startswith("Decisions ") or str(exc) == "Incomplete score set")

def sync(state,events,classify,max_paid=25,mode="delta",missing_grace=3):
    if not 1<=max_paid<=100: raise ValueError("max_paid must be 1..100")
    config=active_config(state)
    source={}
    for event in events:
        key=event_id(event)
        if key in source: raise ValueError("Duplicate event ID: "+key)
        source[key]=event
    if not source: raise ValueError("Empty RC source; refusing destructive sync")
    prior_active=sum(not e.get("inactive") for e in state["events"].values())
    if prior_active>=20 and len(source)<prior_active*.6:
        raise ValueError("Suspicious drop in source count; refusing partial sync")
    at=now()
    for key,event in source.items():
        prev=state["events"].get(key,{})
        normalized=canonical_event(event)
        hashes=fingerprints(event)
        row=dict(prev)
        row["event"]=normalized
        row["display_hash"]=hashes["display_hash"]
        row["missing_checks"]=0
        row["inactive"]=False
        state["events"][key]=row
    if mode=="continue":
        campaign=state.get("campaign")
        if not campaign: raise RuntimeError("No active reclassification campaign")
        if campaign["revision"]!=state["active_questionnaire"]["revision"]:
            raise RuntimeError("Questionnaire revision changed during campaign; re-publish after finishing")
        candidates=[key for key in campaign["pending"] if key in source]
    elif mode=="refresh":
        candidates=[]  # Correct display metadata without any API calls.
    elif mode=="delta":
        candidates=[key for key,event in source.items() if
                    (state["events"][key].get("last_attempt_hash") or state["events"][key].get("classification_hash"))!=fingerprints(event)["classification_hash"]]
    else: raise ValueError("Unknown mode")
    successes=0
    failures=[]
    for key in candidates[:max_paid]:
        usage={}
        try:
            result=classify(canonical_event(source[key]),config,usage)
            scores=result["criteria_scores"]
            if len(scores)!=len(config["criteria"]): raise ValueError("Incomplete score set")
        except Exception as exc:
            permanent=permanent_classification_failure(exc)
            record=state["events"][key]
            if permanent:
                record["last_attempt_hash"]=fingerprints(source[key])["classification_hash"]
                record["classification_status"]="failed"
                record["classification_error"]={"type":type(exc).__name__,"reason":str(exc)[:240]}
            failures.append({"id":key,"type":type(exc).__name__, "reason":str(exc)[:240], "retry_on_change_only":permanent})
            if mode=="continue" and permanent:
                state["campaign"]["pending"].remove(key)
            continue
        record=state["events"][key]
        record["classification"]={"scores":scores,"relevance":relevance(scores,config),
            "model":MODEL,"classified_at":at,"questionnaire_revision":state["active_questionnaire"]["revision"],
            "criterion_signatures":{c["id"]:criterion_signature(c) for c in config["criteria"]},
            "usage":usage,"estimated_cost_usd":round(usage.get("input_tokens",0)*.10/1000000,8)}
        record["classification_hash"]=fingerprints(source[key])["classification_hash"]
        record["last_attempt_hash"]=record["classification_hash"]
        record["classification_status"]="success"
        record.pop("classification_error",None)
        successes+=1
        if mode=="continue": state["campaign"]["pending"].remove(key)
    if mode=="continue" and not state["campaign"]["pending"]:
        state["campaign"]=None
    for key,row in state["events"].items():
        if key not in source:
            row["missing_checks"]=row.get("missing_checks",0)+1
            if row["missing_checks"]>=missing_grace:row["inactive"]=True
    state["last_sync_at"]=at
    state["last_run"]={"mode":mode,"source_count":len(source),"queued":len(candidates),
                       "classified":successes,"failures":failures,
                       "remaining_campaign":len(state["campaign"]["pending"]) if state.get("campaign") else 0}
    return state["last_run"]

def public_feed(state):
    return {"generated_at":state.get("last_sync_at"),
            "questionnaire":copy.deepcopy(state.get("active_questionnaire")),
            "events":[{"id":key,"event":item["event"],"classification":({**item["classification"],
                       "scores":presentation_scores(item["classification"],state.get("active_questionnaire")),
                       "pending_criteria":[c["id"] for c in (state.get("active_questionnaire") or {}).get("criteria",[])
                          if c["id"] not in {s["id"] for s in presentation_scores(item["classification"],state.get("active_questionnaire"))}]}
                          if item.get("classification") else None),
                       "inactive":item.get("inactive",False),
                       "stale":bool(item.get("classification") and item.get("classification_hash")!=
                                    fingerprints(item["event"])["classification_hash"])}
                      for key,item in sorted(state["events"].items()) if item.get("event")]}
