from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import uuid4

app = FastAPI(title="Lab4 API", version="1.0")

# ---- simple auth ----
def require_key(x_api_key: Optional[str]):
    if x_api_key != "demo":
        raise HTTPException(status_code=401, detail={"error": {"code": "UNAUTHORIZED", "message": "Missing/invalid X-API-Key"}})

# ---- storage ----
ACCOUNTS: Dict[str, dict] = {}
RUNS: Dict[str, dict] = {}
RECOS: Dict[str, list] = {}

# preset rules
RULES: Dict[str, dict] = {
    "r1": {"id": "r1", "code": "SPEND_WITHOUT_CONVERSIONS", "enabled": True, "threshold": 1000},
    "r2": {"id": "r2", "code": "LOW_CTR", "enabled": True, "threshold": 0.01},
}

# ---- DTO ----
class AccountCreate(BaseModel):
    name: str
    direct_account_id: str

class RunCreate(BaseModel):
    account_id: str
    date_from: str
    date_to: str

class RuleUpdate(BaseModel):
    enabled: bool
    threshold: float

@app.get("/api/v1/health")
def health(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_key(x_api_key)
    return {"status": "ok"}

@app.post("/api/v1/accounts", status_code=201)
def create_account(payload: AccountCreate, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_key(x_api_key)
    acc_id = str(uuid4())
    ACCOUNTS[acc_id] = {"id": acc_id, "name": payload.name, "direct_account_id": payload.direct_account_id}
    return ACCOUNTS[acc_id]

@app.get("/api/v1/accounts")
def list_accounts(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_key(x_api_key)
    return list(ACCOUNTS.values())

@app.post("/api/v1/analysis-runs", status_code=201)
def create_run(payload: RunCreate, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_key(x_api_key)
    if payload.account_id not in ACCOUNTS:
        raise HTTPException(status_code=404, detail={"error": {"code": "ACCOUNT_NOT_FOUND", "message": "Account not found"}})

    run_id = str(uuid4())
    RUNS[run_id] = {"run_id": run_id, "status": "DONE", "account_id": payload.account_id, "date_from": payload.date_from, "date_to": payload.date_to}

    # Demo recommendations
    RECOS[run_id] = [
        {
            "campaign_id": "c1",
            "rule": "SPEND_WITHOUT_CONVERSIONS",
            "message": "Высокий расход при нулевых конверсиях — проверить ключевые фразы/минус-слова/посадочную.",
            "evidence": {"spend": 1200, "conversions": 0},
        }
    ]
    return {"run_id": run_id, "status": "DONE"}

@app.get("/api/v1/analysis-runs/{run_id}/recommendations")
def get_recommendations(run_id: str, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_key(x_api_key)
    if run_id not in RECOS:
        raise HTTPException(status_code=404, detail={"error": {"code": "RUN_NOT_FOUND", "message": "Run not found"}})
    return RECOS[run_id]

@app.get("/api/v1/rules")
def list_rules(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_key(x_api_key)
    return list(RULES.values())

# ---- advanced (PUT/DELETE) ----
@app.put("/api/v1/rules/{rule_id}")
def update_rule(rule_id: str, payload: RuleUpdate, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_key(x_api_key)
    if rule_id not in RULES:
        raise HTTPException(status_code=404, detail={"error": {"code": "RULE_NOT_FOUND", "message": "Rule not found"}})
    RULES[rule_id]["enabled"] = payload.enabled
    RULES[rule_id]["threshold"] = payload.threshold
    return RULES[rule_id]

@app.delete("/api/v1/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: str, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_key(x_api_key)
    if rule_id not in RULES:
        raise HTTPException(status_code=404, detail={"error": {"code": "RULE_NOT_FOUND", "message": "Rule not found"}})
    del RULES[rule_id]
    return