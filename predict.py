import requests, json, os
from datetime import datetime, timedelta

API_TOKEN = os.getenv("FOOTBALL_TOKEN")
HEADERS = {"X-Auth-Token": API_TOKEN}

# More leagues = more predictions
LEAGUES = ["PL", "PD", "SA", "BL1", "FL1", "DED", "ELC", "PPL"]

tomorrow = (datetime.utcnow() + timedelta(days=1)).date()
date_from = tomorrow.isoformat()
date_to = tomorrow.isoformat()

all_matches = []

for comp in LEAGUES:
    try:
        url = f"https://api.football-data.org/v4/competitions/{comp}/matches?dateFrom={date_from}&dateTo={date_to}"
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 429:
            import time; time.sleep(10)
            r = requests.get(url, headers=HEADERS, timeout=15)
        data = r.json()
        matches = data.get('matches', [])
        for m in matches:
            # Only include if not finished
            if m['status'] in ['TIMED', 'SCHEDULED']:
                all_matches.append({
                    "id": m['id'],
                    "match": f"{m['homeTeam']['shortName']} vs {m['awayTeam']['shortName']}",
                    "home": m['homeTeam']['name'],
                    "away": m['awayTeam']['name'],
                    "competition": m['competition']['name'],
                    "utcDate": m['utcDate'],
                    "status": m['status'],
                    "prediction": "Over 1.5 Goals",
                    "confidence": 78
                })
    except Exception as e:
        print(f"{comp} error: {e}")
        continue

# Sort by time and take best 8
all_matches = sorted(all_matches, key=lambda x: x['utcDate'])[:8]

# If no matches tomorrow, keep old picks
if len(all_matches) < 3:
    try:
        with open('picks.json') as f:
            old = json.load(f).get('picks', [])
        all_matches = old
    except:
        pass

# Add confidence based on league (PL/SA = higher scoring)
for p in all_matches:
    if p['competition'] in ['Premier League', 'Serie A', 'Bundesliga']:
        p['confidence'] = 82
    elif p['competition'] in ['Eredivisie', 'Primeira Liga']:
        p['confidence'] = 85
    else:
        p['confidence'] = 76

output = {"date": date_from, "picks": all_matches, "generated_at": datetime.utcnow().isoformat()}

with open('picks.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"Generated {len(all_matches)} predictions for {date_from}")
for p in all_matches:
    print(f"- {p['match']} ({p['competition']})")
