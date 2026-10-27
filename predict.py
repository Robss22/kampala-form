
import requests, json, time, os
from datetime import date, timedelta
API_TOKEN = os.getenv("FOOTBALL_TOKEN")
headers = {"X-Auth-Token": API_TOKEN}

def get_last5_goals_count(team_id):
    url = f"https://api.football-data.org/v4/teams/{team_id}/matches?limit=5"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        matches = r.json().get('matches', [])
        count_over = 0
        for m in matches:
            ft = m.get('score', {}).get('fullTime', {})
            h = ft.get('home'); a = ft.get('away')
            if h is not None and a is not None and (h + a) >= 2:
                count_over += 1
        time.sleep(6)
        return count_over, len(matches)
    except:
        return 0, 0

# CREATE HISTORY FOLDER
os.makedirs("history", exist_ok=True)

url = "https://api.football-data.org/v4/matches"
all_matches = requests.get(url, headers=headers).json().get('matches', [])

all_candidates = []
for m in all_matches[:15]:
    home = m['homeTeam']['name']
    away = m['awayTeam']['name']
    home_over,_ = get_last5_goals_count(m['homeTeam']['id'])
    away_over,_ = get_last5_goals_count(m['awayTeam']['id'])
    total_over = home_over + away_over
    
    all_candidates.append({
        "match": f"{home} vs {away}",
        "time": m['utcDate'][11:16] + " UTC",
        "market": "Over 1.5 Goals",
        "stat": f"Last 10 combined: {total_over}/10 had 2+ goals",
        "score": total_over, # for sorting
        "probability": f"{total_over*10}%",
        "odds_range": "1.25-1.40"
    })

# SORT by best score and TAKE ONLY TOP 3
all_candidates.sort(key=lambda x: x['score'], reverse=True)
final_picks = all_candidates[:3]

# Remove score field before saving
for p in final_picks: p.pop('score', None)

today = str(date.today())

# 1. Save today's file
with open('picks.json', 'w') as f:
    json.dump({"date": today, "picks": final_picks}, f, indent=2)

# 2. Save to history folder
with open(f'history/{today}.json', 'w') as f:
    json.dump({"date": today, "picks": final_picks}, f, indent=2)

# 3. Update master history file (keep only last 7 days)
history_files = sorted(os.listdir("history"))[-7:]
master = []
for file in history_files:
    with open(f"history/{file}") as f:
        master.append(json.load(f))

with open('history.json', 'w') as f:
    json.dump(master[::-1], f, indent=2) # newest first

print(f"DONE! Saved {len(final_picks)} picks for {today}. History has {len(master)} days")
