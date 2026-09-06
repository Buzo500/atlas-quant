"""Exercise the running local UI proxy and deterministic workflow, without paid calls."""
import json
from pathlib import Path
import time
import urllib.request

BASE = "http://127.0.0.1:3000"


def request(path,body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE+path,data=data,headers={
        "Content-Type":"application/json","X-Atlas-Client":"local-v1","Origin":BASE})
    with urllib.request.urlopen(req,timeout=30) as response:
        return json.load(response)


for attempt in range(20):
    try:
        with urllib.request.urlopen(BASE+"/",timeout=5) as response:
            assert response.status==200
        break
    except (OSError,urllib.error.URLError):
        if attempt==19:
            raise
        time.sleep(.5)
health = request("/api/health")
assert health["status"]=="ok" and health["live_available"] is False
demo = request("/api/datasets/demo",{})
portfolio = request("/api/datasets/"+demo["id"]+"/portfolio")
assert portfolio["nav"]>0 and len(portfolio["positions"])==3
state = request("/api/state")
job = next((j for j in state["experiments"] if j.get("prompt")=="Prueba técnica de ATLAS: comparar reglas sobre activos sintéticos sin IA ni dinero real."),None)
if not job:
    job = request("/api/experiments",{"dataset_id":demo["id"],"symbol":"DEMO_WORLD",
        "prompt":"Prueba técnica de ATLAS: comparar reglas sobre activos sintéticos sin IA ni dinero real.",
        "provider":"none","budget_usd":0,"hours":48,"auto_paper":False})
for _ in range(30):
    job = request("/api/experiments/"+job["id"])
    if job["status"] not in ("queued","running"):
        break
    time.sleep(1)
assert job["status"]=="observing",job.get("error")
assert job["gate"]["passed"] is False
assert job["spent_usd"]==0 and job["paper_account"] is None
assert job["research"]["out_of_sample"]["metrics"]["observations"]>=100
result = {"health":health,"dataset_id":demo["id"],"synthetic":True,"portfolio_nav":portfolio["nav"],
    "experiment_id":job["id"],"status":job["status"],"ai_spend_usd":job["spent_usd"],
    "gate_passed":job["gate"]["passed"],"oos_metrics":job["research"]["out_of_sample"]["metrics"],
    "ui_http_status":200,"api_proxy":"verified","browser_interactions":"not_tested"}
output = Path(__file__).resolve().parents[1]/"output/validation"
output.mkdir(parents=True,exist_ok=True)
(output/"runtime_v01.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(result,ensure_ascii=True))
