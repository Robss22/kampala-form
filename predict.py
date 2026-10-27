import requests, json, time, os
from datetime import date, timedelta

API_TOKEN = os.getenv("FOOTBALL_TOKEN")
headers = {"X-Auth-Token": API_TOKEN}

def get_last5_goals_count(team_id):
    url = f"https://api.football-data.org/v4/teams/{team_id}/matches?limit=5"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return 0, 0
        matches = r.json().get('matches', [])
        count_over = 0
        for m in matches:
            ft = m.get('score', {}).get('fullTime', {})
            h = ft.get('home'); a = ft.get('away')
            if h is not None and a is not None and (h + a) >= 2:
                count_over += 1
        time.sleep(6)
        return count_over, len(matches)
    except Exception as e:
        print(f"Error team {team_id}: {e}")
        time.sleep(6)
        return 0, 0

def check_result(match_id):
    # check if match finished and if Over 1.5 won
    try:
        r = requests.get(f"https://api.football-data.org/v4/matches/{match_id}", headers=headers, timeout=10)
        if r.status_code != 200:
            return "PENDING"
        m = r.json()
        ft = m.get('score', {}).get('fullTime', {})
        h = ft.get('home'); a = ft.get('away')
        if h is None or a is None:
            return "PENDING"
        return "WON" if (h + a) >= 2 else "LOST"
    except:
        return "PENDING"

# CREATE HISTORY FOLDER
os.makedirs("history", exist_ok=True)

# 1. GET TODAY'S MATCHES
url = "https://api.football-data.org/v4/matches"
try:
    all_matches = requests.get(url, headers=headers, timeout=15).json().get('matches', [])
except:
    all_matches = []

all_candidates = []
for m in all_matches[:15]:
    home = m['homeTeam']['name']
    away = m['awayTeam']['name']
    home_over,_ = get_last5_goals_count(m['homeTeam']['id'])
    away_over,_ = get_last5_goals_count(m['awayTeam']['id'])
    total_over = home_over + away_over
    
    all_candidates.append({
        "id": m['id'],
        "match": f"{home} vs {away}",
        "home": home,
        "away": away,
        "time": m['utcDate'][11:16],
        "utcDate": m['utcDate'],
        "market": "Over 1.5 Goals",
        "pick": "Over 1.5 Goals",
        "stat": f"Last 10 combined: {total_over}/10 had 2+ goals",
        "stats": f"Last 10 combined: {total_over}/10 had 2+ goals",
        "reason": f"Last 10 combined: {total_over}/10 had 2+ goals - {home} {home_over}/5, {away} {away_over}/5",
        "score": total_over,
        "probability": f"{total_over*10}%",
        "odds": "1.25-1.40",
        "odds_range": "1.25-1.40",
        "result": "PENDING"
    })

# SORT by best score and TAKE ONLY TOP 3
all_candidates.sort(key=lambda x: x['score'], reverse=True)
final_picks = all_candidates[:3]

# Remove internal score field before saving
for p in final_picks: 
    p.pop('score', None)

today = str(date.today())

# 2. TRY TO UPDATE YESTERDAY'S RESULTS FOR HISTORY
yesterday = str(date.today() - timedelta(days=1))
yesterday_file = f"history/{yesterday}.json"
if os.path.exists(yesterday_file):
    try:
        with open(yesterday_file) as f:
            y_data = json.load(f)
        updated = False
        for pick in y_data.get('picks', []):
            if pick.get('result') == 'PENDING' and pick.get('id'):
                res = check_result(pick['id'])
                if res != "PENDING":
                    pick['result'] = res
                    updated = True
                time.sleep(2)
        if updated:
            with open(yesterday_file, 'w') as f:
                json.dump(y_data, f, indent=2)
    except Exception as e:
        print(f"Could not update yesterday: {e}")

# 3. Save today's file
with open('picks.json', 'w') as f:
    json.dump({"date": today, "picks": final_picks}, f, indent=2)

# 4. Save to history folder
with open(f'history/{today}.json', 'w') as f:
    json.dump({"date": today, "picks": final_picks}, f, indent=2)

# 5. Update master history file (keep only last 7 days)
history_files = sorted(os.listdir("history"))[-7:]
master = []
for file in history_files:
    try:
        with open(f"history/{file}") as f:
            master.append(json.load(f))
    except:
        pass

with open('history.json', 'w') as f:
    json.dump(master[::-1], f, indent=2)

# 6. Create empty live.json if not exists
if not os.path.exists("live.json"):
    with open('live.json','w') as f:
        json.dump({}, f)

print(f"DONE! Saved {len(final_picks)} picks for {today}. History has {len(master)} days")
