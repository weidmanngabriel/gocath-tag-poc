"""Stable RC event identity, normalization and incremental classification planning."""
import hashlib
import json
import re
import unicodedata
from urllib.parse import urlparse, parse_qs

# Only editorial/event fields, never render time, visit counter or HTML layout.
CLASSIFICATION_FIELDS = ("title", "description", "organizer", "target_groups", "categories")
DISPLAY_FIELDS = CLASSIFICATION_FIELDS + ("location", "starts_at", "ends_at", "url")


def canonical_text(value):
    value = unicodedata.normalize("NFC", str(value or ""))
    return re.sub(r"\\s+", " ", value).strip()


def canonical_event(event):
    """Normalize structured source fields; preserve meaning, ignore page noise."""
    normalized = {}
    for field in DISPLAY_FIELDS:
        value = event.get(field, [] if field in ("target_groups", "categories") else "")
        if field in ("target_groups", "categories"):
            normalized[field] = sorted(set(canonical_text(v) for v in value if canonical_text(v)))
        else:
            normalized[field] = canonical_text(value)
    return normalized


def event_id(event):
    url = urlparse(event["url"])
    vid = parse_qs(url.query).get("vid", [""])[0]
    if url.hostname not in ("www.regnumchristi.eu", "regnumchristi.eu") or not vid.isdecimal():
        raise ValueError("RC event has no stable numeric vid")
    return "rc-" + vid


def digest(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fingerprints(event):
    normalized = canonical_event(event)
    return {
        "classification_hash": digest({field: normalized[field] for field in CLASSIFICATION_FIELDS}),
        "display_hash": digest({field: normalized[field] for field in DISPLAY_FIELDS}),
    }


def plan_delta(events, stored):
    """Plan without mutating the store. Questionnaire edits alone never trigger AI."""
    seen = set()
    decisions = []
    for event in events:
        identity = event_id(event)
        if identity in seen:
            raise ValueError("Duplicate RC event identity: " + identity)
        seen.add(identity)
        hashes = fingerprints(event)
        previous = stored.get(identity)
        classify = previous is None or previous.get("classification_hash") != hashes["classification_hash"] or not previous.get("classification")
        update_display = previous is None or previous.get("display_hash") != hashes["display_hash"]
        decisions.append({
            "id": identity, "event": canonical_event(event), "hashes": hashes,
            "classify": classify, "update_display": update_display,
        })
    return decisions
