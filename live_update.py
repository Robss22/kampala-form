import json, os, requests
API_TOKEN = os.getenv("FOOTBALL_TOKEN")
HEADERS = {"X-Auth-Token": API_TOKEN}
try:
  with open("picks.json") as f:
    data=json.load(f)
  picks=data.get("picks",[])
  live={}
  for p in picks:
    mid=p.get("id")
    if not mid: continue
    try:
      r=requests.get(f"https://api.football-data.org/v4/matches/{mid}", headers=HEADERS, timeout=10)
      if r.status_code==200:
        m=r.json()
        live[str(mid)]={
          "status": m.get("status"),
          "minute": m.get("minute"),
          "score": m.get("score"),
          "utcDate": m.get("utcDate")
        }
    except: pass
  with open("live.json","w") as f:
    json.dump(live,f,indent=2)
  print("live.json updated", live)
except Exception as e:
  print(e)
  open("live.json","w").write("{}")
