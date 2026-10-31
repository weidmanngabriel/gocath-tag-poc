#!/usr/bin/env bash
set -euo pipefail

# One durable rc-data commit after every batch of at most ten paid classifications.
# Losing a job at its time limit can therefore discard only the current batch.
total_limit="${RC_LIMIT:-200}"
mode="${RC_MODE:-delta}"
if ! [[ "$total_limit" =~ ^[0-9]+$ ]] || (( total_limit < 1 || total_limit > 200 )); then
  echo "RC_LIMIT must be 1..200" >&2; exit 2
fi
if [[ "$mode" == "publish-questions" || "$mode" == "refresh" ]]; then
  batch_count=1
else
  batch_count=$(( (total_limit + 9) / 10 ))
fi
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git fetch origin rc-data:refs/remotes/origin/rc-data || true

for ((index=0; index<batch_count; index++)); do
  size=10
  remaining=$((total_limit-index*10))
  if (( remaining < size )); then size=$remaining; fi
  if [[ "$mode" == "publish-questions" || "$mode" == "refresh" ]]; then size=1; fi
  mkdir -p state public
  rm -f state/rc-no-changes.flag state/rc-run-record.json
  git show origin/rc-data:catalog.json > state/catalog.json 2>/dev/null || rm -f state/catalog.json

  echo "RC checkpoint $((index+1))/$batch_count: mode=$mode, max_paid=$size"
  python -m src.rc_runtime --mode "$mode" --max-paid "$size" --state state/catalog.json --public public/catalog.json

  checkpoint_dir="$(mktemp -d)"
  for name in catalog public; do
    src="state/catalog.json"
    if [[ "$name" == "public" ]]; then src="public/catalog.json"; fi
    if [[ -f "$src" ]]; then cp "$src" "$checkpoint_dir/$name.json"; fi
  done
  if [[ -f state/rc-run-record.json ]]; then cp state/rc-run-record.json "$checkpoint_dir/run.json"; fi

  if git show-ref --quiet refs/remotes/origin/rc-data; then
    git switch -C rc-data origin/rc-data
  else
    git switch --orphan rc-data
    git rm -rf --ignore-unmatch .
  fi
  if [[ ! -f state/rc-no-changes.flag ]]; then
    cp "$checkpoint_dir/catalog.json" catalog.json
    cp "$checkpoint_dir/public.json" public.json
    git add catalog.json public.json
  fi
  if [[ -f "$checkpoint_dir/run.json" ]]; then
    RC_CHECKPOINT_FILE="$checkpoint_dir/run.json" RC_CHECKPOINT_INDEX="$index" python - <<'PY'
import json, os
from pathlib import Path
path = Path("runs.json")
prior = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"runs":[]}
record = json.loads(Path(os.environ["RC_CHECKPOINT_FILE"]).read_text(encoding="utf-8"))
record["checkpoint"] = int(os.environ["RC_CHECKPOINT_INDEX"]) + 1
prior["runs"] = [x for x in prior.get("runs",[]) if not (x.get("run_id") == record["run_id"] and x.get("checkpoint") == record["checkpoint"])]
prior["runs"].append(record)
prior["runs"] = prior["runs"][-1000:]
path.write_text(json.dumps(prior,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY
    git add runs.json
  fi
  if ! git diff --cached --quiet; then
    git commit -m "RC checkpoint $((index+1)): up to $size classifications"
    git push origin HEAD:rc-data
    git fetch origin rc-data:refs/remotes/origin/rc-data
  fi
  git switch - >/dev/null
  rm -rf "$checkpoint_dir"

  if [[ "$mode" == "publish-questions" || "$mode" == "refresh" ]]; then break; fi
  # For an explicit full campaign, never restart it in the next batch.
  if [[ "$mode" == "reclassify" ]]; then mode="continue"; fi
  campaign_pending="$(python - <<'PY'
import json
from pathlib import Path
s=json.loads(Path("state/catalog.json").read_text(encoding="utf-8"))
print(len((s.get("campaign") or {}).get("pending") or []))
PY
)"
  if [[ "$mode" == "continue" && "$campaign_pending" == "0" ]]; then break; fi
  # For delta, stop if fewer candidates were found than this batch's limit.
  if [[ "$mode" == "delta" ]]; then
    queued="$(python - <<'PY'
import json
from pathlib import Path
s=json.loads(Path("state/catalog.json").read_text(encoding="utf-8"))
print((s.get("last_run") or {}).get("queued",0))
PY
)"
    if (( queued <= size )); then break; fi
  fi
done
