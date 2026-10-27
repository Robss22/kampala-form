import requests, json, os
from datetime import datetime

API_TOKEN = os.getenv("FOOTBALL_TOKEN")
HEADERS = {"X-Auth-Token": API_TOKEN}
LEAGUES = ["PL","PD","SA","BL1","FL1","DED","ELC","PPL"]

today = datetime.utcnow().date().isoformat()

matches=[]
for comp in LEAGUES:
    try:
        url=f"https://api.football-data.org/v4/competitions/{comp}/matches?dateFrom={today}&dateTo={today}"
        r=requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code==429:
            import time; time.sleep(12)
            r=requests.get(url, headers=HEADERS, timeout=15)
        for m in r.json().get('matches',[]):
            if m['status'] in ['TIMED','SCHEDULED','IN_PLAY','PAUSED']:
                matches.append({
                  "id": m['id'],
                  "match": f"{m['homeTeam']['shortName']} vs {m['awayTeam']['shortName']}",
                  "competition": m['competition']['name'],
                  "utcDate": m['utcDate'],
                  "time": m['utcDate'],
                  "prediction": "Over 1.5",
                  "tip": "Over 1.5",
                  "pick": "Over 1.5",
                  "market": "Over 1.5",
                  "odds": 1.30,
                  "odd": 1.30
                })
    except: continue

matches = sorted(matches, key=lambda x: x['utcDate'])[:8]

# If API gives 0 today (no games), keep yesterday's picks as fallback
if len(matches) < 2:
    try:
        with open('picks.json') as f:
            old = json.load(f).get('picks', [])
        if old:
            matches = old
    except: pass

with open('picks.json','w') as f:
    json.dump({"date": today, "picks": matches, "generated_at": datetime.utcnow().isoformat()}, f, indent=2)

print(f"Saved {len(matches)} TODAY picks for {today}")
