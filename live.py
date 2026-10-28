"""Updates live scores, settles results, and keeps history.json complete.

- Refreshes live.json for today's picks (only matches that have kicked off).
- Writes WON/LOST into picks.json.
- Upserts today's picks into history.json, so History never depends on a separate archive step.
- Settles any older PENDING history picks by asking the API for the final score.
"""
import json, os, time
from datetime import datetime, timedelta, timezone

import requests

TOKEN = os.getenv("FOOTBALL_TOKEN")
HEADERS = {"X-Auth-Token": TOKEN or ""}
BASE = "https://api.football-data.org/v4"
CALL_GAP = 6.5
MAX_SETTLE_CALLS = 6
KEEP_DAYS = 60
SLIM = ("id", "match", "competition", "utcDate", "market", "prob", "fairOdds", "result", "finalScore")

_last_call = 0.0


def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def fetch_match(mid):
    global _last_call
    for _ in range(3):
        wait = CALL_GAP - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()
        r = requests.get(f"{BASE}/matches/{mid}", headers=HEADERS, timeout=15)
        if r.status_code == 429:
            time.sleep(30)
            continue
        r.raise_for_status()
        return r.json()
    return None


def settle(pick, m):
    status = m.get("status")
    ft = m.get("score", {}).get("fullTime", {})
    if status == "FINISHED" and ft.get("home") is not None and ft.get("away") is not None:
        pick["result"] = "WON" if ft["home"] + ft["away"] >= 2 else "LOST"
        pick["finalScore"] = f"{ft['home']}-{ft['away']}"
    elif status in ("POSTPONED", "CANCELLED"):
        pick["result"] = "VOID"


def parse(utc):
    return datetime.fromisoformat(utc.replace("Z", "+00:00"))


def main():
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    data = load("picks.json", {"picks": []})
    picks = data.get("picks", [])
    live = load("live.json", {})

    # 1. today's live scores
    for p in picks:
        mid = p.get("id")
        if not mid:
            continue
        key = str(mid)
        prev = live.get(key, {})
        if prev.get("status") in ("FINISHED", "POSTPONED", "CANCELLED"):
            settle(p, prev)
            continue
        live.setdefault(key, {"status": p.get("status", "TIMED"), "score": {}, "minute": "",
                              "utcDate": p.get("utcDate", "")})
        if p.get("utcDate") and now < parse(p["utcDate"]) - timedelta(minutes=10):
            continue  # not started yet - save an API call
        try:
            m = fetch_match(mid)
            if not m:
                continue
            live[key] = {"status": m.get("status", "TIMED"), "score": m.get("score", {}),
                         "minute": m.get("minute", ""), "utcDate": m.get("utcDate", p.get("utcDate", ""))}
            settle(p, m)
        except Exception as e:
            print(f"live {mid}: {e}")

    live = {k: v for k, v in live.items() if k in {str(p.get("id")) for p in picks}}
    data["picks"] = picks
    if picks or "date" in data:
        save("picks.json", data)
    save("live.json", live)

    # 2. history: upsert today, settle older pending
    hist = load("history.json", [])
    if data.get("date") and picks:
        entry = {"date": data["date"], "picks": [{k: p[k] for k in SLIM if k in p} for p in picks]}
        hist = [d for d in hist if d.get("date") != data["date"]] + [entry]

    cutoff = (now - timedelta(days=KEEP_DAYS)).date().isoformat()
    hist = sorted((d for d in hist if d.get("date", "") >= cutoff), key=lambda d: d["date"], reverse=True)

    calls = 0
    for day in hist:
        if day["date"] == data.get("date"):
            continue
        for hp in day.get("picks", []):
            if hp.get("result", "PENDING") != "PENDING" or not hp.get("id") or calls >= MAX_SETTLE_CALLS:
                continue
            try:
                m = fetch_match(hp["id"])
                calls += 1
                if m:
                    settle(hp, m)
            except Exception as e:
                print(f"settle {hp['id']}: {e}")

    save("history.json", hist)
    print(f"live: {len(live)} games, history: {len(hist)} days, settled-lookups: {calls}")


if __name__ == "__main__":
    main()
