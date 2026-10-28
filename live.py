import requests, json, os
from datetime import datetime

TOKEN = os.getenv("FOOTBALL_TOKEN")
HEADERS = {"X-Auth-Token": TOKEN}

# Load picks
try:
    with open('picks.json') as f:
        data = json.load(f)
    picks = data.get('picks', [])
except:
    picks = []

live = {}
history_update = []

for p in picks:
    mid = p.get('id')
    if not mid:
        continue
    try:
        url = f"https://api.football-data.org/v4/matches/{mid}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        m = r.json()
        status = m.get('status')
        score = m.get('score',{})
        ft = score.get('fullTime',{})
        
        live[str(mid)] = {
            "status": status,
            "score": score,
            "minute": m.get('minute')
        }
        
        # Determine WON/LOST for Over 1.5
        if status == 'FINISHED' and ft.get('home') is not None:
            total = ft['home'] + ft['away']
            result = 'WON' if total >= 2 else 'LOST'
            p['result'] = result
            p['finalScore'] = f"{ft['home']}-{ft['away']}"
    except Exception as e:
        print(e)
        continue

# Save live
with open('live.json','w') as f:
    json.dump(live, f, indent=2)

# Update picks.json with results
try:
    with open('picks.json') as f:
        full = json.load(f)
    full['picks'] = picks
    with open('picks.json','w') as f:
        json.dump(full, f, indent=2)
except:
    pass

# Archive to history.json
try:
    with open('history.json') as f:
        hist = json.load(f)
except:
    hist = []

today = datetime.utcnow().date().isoformat()

# If history doesn't have today and we have finished games, add?
# Actually archive only when date changes in predict.py
# For now just ensure history entries have correct result from live
for day in hist:
    for hp in day.get('picks',[]):
        lid = str(hp.get('id',''))
        if lid in live:
            m = live[lid]
            if m['status'] == 'FINISHED':
                ft = m['score']['fullTime']
                total = ft['home'] + ft['away']
                hp['result'] = 'WON' if total >= 2 else 'LOST'

with open('history.json','w') as f:
    json.dump(hist, f, indent=2)

print(f"Live updated {len(live)} games")
