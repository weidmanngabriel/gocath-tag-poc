#!/usr/bin/env bash
set -euo pipefail
mode="${RC_MODE:-delta}"
limit="${RC_LIMIT:-25}"
if [[ "$mode" != "delta" && "$mode" != "reclassify" && "$mode" != "refresh" ]]; then
  echo "Unsupported RC_MODE: $mode" >&2; exit 2
fi
if ! [[ "$limit" =~ ^[0-9]+$ ]] || ((limit<1 || limit>200)); then
  echo "RC_LIMIT must be 1..200" >&2; exit 2
fi
mkdir -p state public
# Freeze one Google Sheet snapshot for all checkpoints in this workflow.
python - <<'PY'
import json,os
from pathlib import Path
from src.config import settings
_, config=settings(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"],os.environ["GOOGLE_SHEET_ID"])
Path("state/config-snapshot.json").write_text(json.dumps(config,ensure_ascii=False),encoding="utf-8")
PY
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git fetch origin rc-data:refs/remotes/origin/rc-data
worktree="$RUNNER_TEMP/rc-catalog-data"
git worktree add --detach "$worktree" origin/rc-data
for ((offset=0;offset<limit;offset+=10)); do
  batch=10
  if ((limit-offset<batch)); then batch=$((limit-offset)); fi
  if [[ "$mode" == "refresh" ]]; then batch=1; fi
  cp "$worktree/catalog.json" state/catalog.json
  rm -f state/rc-no-changes.flag state/rc-run-record.json
  echo "Classifying batch of at most $batch at offset $offset"
  python -m src.rc_runtime --mode "$mode" --max-paid "$batch" --config-snapshot state/config-snapshot.json --state state/catalog.json --public public/catalog.json
  if [[ ! -f state/rc-no-changes.flag ]]; then
    cp state/catalog.json "$worktree/catalog.json"
    cp public/catalog.json "$worktree/public.json"
  fi
  if [[ -f state/rc-run-record.json ]]; then
    RC_RECORD_PATH="$PWD/state/rc-run-record.json" RC_CHECKPOINT_OFFSET="$offset" RC_WORKTREE="$worktree" python - <<'PY'
import json,os
from pathlib import Path
path=Path(os.environ["RC_WORKTREE"])/"runs.json"
data=json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"runs":[]}
new=json.loads(Path(os.environ["RC_RECORD_PATH"]).read_text(encoding="utf-8"))
runs=data.setdefault("runs",[])
prior=next((r for r in runs if r.get("run_id")==new["run_id"]),None)
if prior:
    for key in ("attempted","classified","failed"):
        prior[key]=prior.get(key,0)+new.get(key,0)
    for key,value in new.get("usage",{}).items():
        prior.setdefault("usage",{})[key]=prior["usage"].get(key,0)+value
    prior["cost_usd_estimated"]=round(prior.get("cost_usd_estimated",0)+new.get("cost_usd_estimated",0),8)
    prior["finished_at"]=new["finished_at"]
    prior["remaining"]=new.get("remaining",0)
else:
    runs.append(new)
data["runs"]=runs[-1000:]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY
  fi
  git -C "$worktree" add catalog.json public.json runs.json
  if ! git -C "$worktree" diff --cached --quiet; then
    git -C "$worktree" commit -m "RC checkpoint after up to $((offset+batch)) attempts"
    git -C "$worktree" push origin HEAD:rc-data
  fi
  # Nothing remains from this batch, or metadata-only refresh.
  if [[ "$mode" == "refresh" ]]; then break; fi
  pending=$(python - <<'PY'
import json
from pathlib import Path
state=json.loads(Path("state/catalog.json").read_text(encoding="utf-8"))
print((state.get("last_run") or {}).get("queued",0))
PY
)
  if ((pending<=batch)); then break; fi
done
