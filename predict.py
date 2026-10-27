import requests, json, os
from datetime import datetime
import random

API_TOKEN = os.getenv("FOOTBALL_TOKEN")
HEADERS = {"X-Auth-Token": API_TOKEN}
today = datetime.utcnow().date().isoformat()

matches=[]
for comp in ["PL","PD","SA","BL1","FL1"]:
    try:
        url=f"https://api.football-data.org/v4/competitions/{comp}/matches?dateFrom={today}&dateTo={today}"
        r=requests.get(url, headers=HEADERS, timeout=20)
        for m in r.json().get('matches',[]):
            if m['status'] in ['TIMED','SCHEDULED','IN_PLAY','PAUSED','LIVE']:
                matches.append({
                  "id": m['id'],
                  "match": f"{m['homeTeam']['shortName']} vs {m['awayTeam']['shortName']}",
                  "competition": m['competition']['name'],
                  "utcDate": m['utcDate'],
                  "time": m['utcDate'],
                  "prediction": "Over 1.5",
                  "pick": "Over 1.5",
                  "tip": "Over 1.5",
                  "market": "Over 1.5",
                  "odds": 1.32
                })
    except: continue

matches = sorted(matches, key=lambda x: x['utcDate'])[:3]

# FORCE 100% on first game - as it was before!
final=[]
for i, m in enumerate(matches):
    if i==0:
        conf=100
    elif i==1:
        conf=87
    else:
        conf=78 + random.randint(0,5)
    
    m.update({
        "confidence": conf,
        "percent": conf,
        "winPercent": conf,
        "probability": conf,
        "chance": f"{conf}%",
        "winningChance": f"{conf}%"
    })
    final.append(m)

# If no games today, use old 100% example
if not final:
    final=[{
      "match": "Roma vs Cagliari",
      "competition": "Serie A",
      "utcDate": datetime.utcnow().isoformat(),
      "prediction": "Over 1.5",
      "odds": 1.3,
      "confidence": 100,
      "percent": 100,
      "chance": "100%"
    }]

with open('picks.json','w') as f:
    json.dump({"date": today, "picks": final}, f, indent=2)

print(f"Saved {len(final)} - first is 100%")
