"""Morning picks for SMART STATS UG.

Method (Over 1.5 goals):
  1. Pull every finished match this season for each league playing today (1 API call/league).
  2. Poisson model: expected goals for each side from venue-specific attack/defence
     strength, shrunk toward the league average so early-season samples don't mislead.
  3. Blend 70% model + 30% "last 5 games over 1.5" form for both teams.
  4. Keep only matches above MIN_PROB, best first, max MAX_PICKS.
"""
import json, math, os, sys, time
from datetime import datetime, timezone

import requests

TOKEN = os.getenv("FOOTBALL_TOKEN")
HEADERS = {"X-Auth-Token": TOKEN or ""}
BASE = "https://api.football-data.org/v4"

COMPETITIONS = ["SA", "PL", "BL1", "PD"]
MAX_PICKS = 3
MIN_PROB = 0.75      # raise for fewer/safer picks, lower for more picks
MIN_GAMES = 4        # each team needs at least this many games played
FORM_N = 5
PRIOR_GAMES = 6      # shrinkage strength toward league average
W_MODEL = 0.7
CALL_GAP = 6.5       # free tier = 10 requests/minute
FORCE = os.getenv("FORCE", "").lower() in ("1", "true", "yes")

today = datetime.now(timezone.utc).date().isoformat()
_last_call = 0.0


def api(path, params=None):
    global _last_call
    for _ in range(3):
        wait = CALL_GAP - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()
        r = requests.get(BASE + path, headers=HEADERS, params=params, timeout=20)
        if r.status_code == 429:
            time.sleep(30)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"rate limited: {path}")


def p_over15(lam):
    """P(total goals >= 2) when total ~ Poisson(lam)."""
    return 1 - math.exp(-lam) * (1 + lam)


def build_stats(finished):
    finished = sorted(finished, key=lambda m: m["utcDate"])
    teams, lh, la, n = {}, 0, 0, 0
    for m in finished:
        ft = m.get("score", {}).get("fullTime", {})
        h, a = ft.get("home"), ft.get("away")
        if h is None or a is None:
            continue
        lh += h; la += a; n += 1
        for tid, venue, gf, ga in ((m["homeTeam"]["id"], "home", h, a),
                                   (m["awayTeam"]["id"], "away", a, h)):
            t = teams.setdefault(tid, {"home": [0, 0, 0], "away": [0, 0, 0], "recent": []})
            t[venue][0] += gf; t[venue][1] += ga; t[venue][2] += 1
            t["recent"].append(h + a)
    if n == 0:
        return None
    return {"teams": teams, "lg_home": lh / n, "lg_away": la / n}


def predict_match(stats, hid, aid):
    th, ta = stats["teams"].get(hid), stats["teams"].get(aid)
    if not th or not ta:
        return None
    if th["home"][2] + th["away"][2] < MIN_GAMES or ta["home"][2] + ta["away"][2] < MIN_GAMES:
        return None
    lgh, lga = stats["lg_home"], stats["lg_away"]

    def strength(goals, games, league_avg):
        return ((goals + PRIOR_GAMES * league_avg) / (games + PRIOR_GAMES)) / league_avg

    att_h = strength(th["home"][0], th["home"][2], lgh)   # home side scoring at home
    def_a = strength(ta["away"][1], ta["away"][2], lgh)   # away side conceding away
    att_a = strength(ta["away"][0], ta["away"][2], lga)
    def_h = strength(th["home"][1], th["home"][2], lga)
    lam_h, lam_a = lgh * att_h * def_a, lga * att_a * def_h
    p_model = p_over15(lam_h + lam_a)

    fh, fa = th["recent"][-FORM_N:], ta["recent"][-FORM_N:]
    over_h, over_a = sum(t >= 2 for t in fh), sum(t >= 2 for t in fa)
    p_form = (over_h / len(fh) + over_a / len(fa)) / 2

    prob = W_MODEL * p_model + (1 - W_MODEL) * p_form
    return {"prob": prob, "lam_h": lam_h, "lam_a": lam_a,
            "over_h": over_h, "n_h": len(fh), "over_a": over_a, "n_a": len(fa)}


def main():
    if not TOKEN:
        sys.exit("FOOTBALL_TOKEN is not set")

    if not FORCE:
        try:
            with open("picks.json") as f:
                existing = json.load(f)
            if existing.get("date") == today and existing.get("picks"):
                print("Today's picks already exist - keeping them (set FORCE=1 to rebuild).")
                return
        except Exception:
            pass

    candidates, errors = [], 0
    for comp in COMPETITIONS:
        try:
            fixtures = api(f"/competitions/{comp}/matches",
                           {"dateFrom": today, "dateTo": today}).get("matches", [])
            fixtures = [m for m in fixtures if m["status"] in ("TIMED", "SCHEDULED")]
            if not fixtures:
                continue
            finished = api(f"/competitions/{comp}/matches", {"status": "FINISHED"}).get("matches", [])
            stats = build_stats(finished)
            if not stats:
                continue
            for m in fixtures:
                res = predict_match(stats, m["homeTeam"]["id"], m["awayTeam"]["id"])
                if not res:
                    continue
                hn, an = m["homeTeam"]["name"], m["awayTeam"]["name"]
                pct = round(res["prob"] * 100)
                detail = (f"{hn} {res['over_h']}/{res['n_h']} + {an} {res['over_a']}/{res['n_a']} "
                          f"recent games over 1.5 • expected goals {res['lam_h']:.2f}-{res['lam_a']:.2f}")
                candidates.append({
                    "id": m["id"], "match": f"{hn} vs {an}", "competition": m["competition"]["name"],
                    "utcDate": m["utcDate"], "time": m["utcDate"], "status": m["status"],
                    "market": "Over 1.5 Goals", "pick": "Over 1.5 Goals",
                    "prob": pct, "confidence": pct, "percent": pct,
                    "xg": round(res["lam_h"] + res["lam_a"], 2),
                    "fairOdds": round(1 / res["prob"], 2),
                    "formDetail": detail, "explanation": detail, "reason": detail,
                    "_p": res["prob"], "result": "PENDING",
                })
        except Exception as e:
            errors += 1
            print(f"{comp} failed: {e}")

    if errors == len(COMPETITIONS):
        sys.exit("All competitions failed - leaving picks.json untouched")

    good = sorted((c for c in candidates if c["_p"] >= MIN_PROB), key=lambda c: -c["_p"])[:MAX_PICKS]
    for c in good:
        del c["_p"]
    good.sort(key=lambda c: c["utcDate"])

    with open("picks.json", "w") as f:
        json.dump({"date": today, "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "picks": good}, f, indent=2)
    print(f"{len(candidates)} matches scored, {len(good)} picks saved")


if __name__ == "__main__":
    main()
