import requests, json, os
API_TOKEN = os.getenv("FOOTBALL_TOKEN")
headers = {"X-Auth-Token": API_TOKEN}
try:
 with open('picks.json') as f: picks = json.load(f).get('picks', [])
except: picks=[]
live={}
try:
 with open('live.json') as f: live = json.load(f)
except: live={}
for p in picks:
 mid=p['id']
 try:
  r=requests.get(f"https://api.football-data.org/v4/matches/{mid}", headers=headers, timeout=10)
  if r.status_code==429:
   import time; time.sleep(65)
   r=requests.get(f"https://api.football-data.org/v4/matches/{mid}", headers=headers, timeout=10)
  data=r.json()
  live[str(mid)]={"status":data.get('status','TIMED'),"score":data.get('score',{}),"minute":data.get('minute',''),"utcDate":data.get('utcDate','')}
  print(f"{p['match']}: {data.get('status')}")
 except Exception as e:
  print(e); continue
with open('live.json','w') as f: json.dump(live,f,indent=2)
print("Done")
