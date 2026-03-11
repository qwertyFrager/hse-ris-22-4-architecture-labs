from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware  
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from uuid import uuid4

from sqlalchemy import create_engine, Column, String, Float, Integer, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

import os
import json

API_KEY = os.getenv("API_KEY", "demo")
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# --- DB models ---
class Account(Base):
    __tablename__ = "accounts"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    direct_account_id = Column(String, nullable=False)

class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    run_id = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey("accounts.id"), nullable=False)
    date_from = Column(String, nullable=False)
    date_to = Column(String, nullable=False)
    status = Column(String, nullable=False)

    recommendations = relationship("Recommendation", back_populates="run", cascade="all, delete-orphan")

class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(String, primary_key=True)
    run_id = Column(String, ForeignKey("analysis_runs.run_id"), nullable=False)
    campaign_id = Column(String, nullable=False)
    rule = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    evidence_json = Column(Text, nullable=False)

    run = relationship("AnalysisRun", back_populates="recommendations")

class Rule(Base):
    __tablename__ = "rules"
    id = Column(String, primary_key=True)
    code = Column(String, nullable=False)
    enabled = Column(Integer, nullable=False)  # 1/0
    threshold = Column(Float, nullable=False)

def require_key(x_api_key: Optional[str]):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail={"error": {"code": "UNAUTHORIZED", "message": "Missing/invalid X-API-Key"}})

app = FastAPI(title="Lab5 DSS API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    # seed rules if empty
    with SessionLocal() as db:
        count = db.query(Rule).count()
        if count == 0:
            db.add_all([
                Rule(id="r1", code="SPEND_WITHOUT_CONVERSIONS", enabled=1, threshold=1000.0),
                Rule(id="r2", code="LOW_CTR", enabled=1, threshold=0.01),
            ])
            db.commit()

# --- DTO ---
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
    with SessionLocal() as db:
        acc = Account(id=acc_id, name=payload.name, direct_account_id=payload.direct_account_id)
        db.add(acc)
        db.commit()
    return {"id": acc_id, "name": payload.name, "direct_account_id": payload.direct_account_id}

@app.get("/api/v1/accounts")
def list_accounts(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_key(x_api_key)
    with SessionLocal() as db:
        rows = db.query(Account).all()
        return [{"id": r.id, "name": r.name, "direct_account_id": r.direct_account_id} for r in rows]

@app.post("/api/v1/analysis-runs", status_code=201)
def create_run(payload: RunCreate, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_key(x_api_key)
    run_id = str(uuid4())
    with SessionLocal() as db:
        acc = db.query(Account).filter(Account.id == payload.account_id).first()
        if not acc:
            raise HTTPException(status_code=404, detail={"error": {"code": "ACCOUNT_NOT_FOUND", "message": "Account not found"}})

        run = AnalysisRun(run_id=run_id, account_id=payload.account_id, date_from=payload.date_from, date_to=payload.date_to, status="DONE")
        db.add(run)

        # Demo recommendations
        reco = Recommendation(
            id=str(uuid4()),
            run_id=run_id,
            campaign_id="c1",
            rule="SPEND_WITHOUT_CONVERSIONS",
            message="Высокий расход при нулевых конверсиях — проверить ключевые фразы/минус-слова/посадочную.",
            evidence_json=json.dumps({"spend": 1200, "conversions": 0}, ensure_ascii=False),
        )
        db.add(reco)
        db.commit()

    return {"run_id": run_id, "status": "DONE"}

@app.get("/api/v1/analysis-runs/{run_id}/recommendations")
def get_recommendations(run_id: str, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_key(x_api_key)
    with SessionLocal() as db:
        run = db.query(AnalysisRun).filter(AnalysisRun.run_id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail={"error": {"code": "RUN_NOT_FOUND", "message": "Run not found"}})
        recos = db.query(Recommendation).filter(Recommendation.run_id == run_id).all()
        return [{
            "campaign_id": r.campaign_id,
            "rule": r.rule,
            "message": r.message,
            "evidence": json.loads(r.evidence_json),
        } for r in recos]

@app.get("/api/v1/rules")
def list_rules(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_key(x_api_key)
    with SessionLocal() as db:
        rows = db.query(Rule).all()
        return [{"id": r.id, "code": r.code, "enabled": bool(r.enabled), "threshold": r.threshold} for r in rows]

# PUT/DELETE для полноты
@app.put("/api/v1/rules/{rule_id}")
def update_rule(rule_id: str, payload: RuleUpdate, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_key(x_api_key)
    with SessionLocal() as db:
        r = db.query(Rule).filter(Rule.id == rule_id).first()
        if not r:
            raise HTTPException(status_code=404, detail={"error": {"code": "RULE_NOT_FOUND", "message": "Rule not found"}})
        r.enabled = 1 if payload.enabled else 0
        r.threshold = payload.threshold
        db.commit()
        return {"id": r.id, "code": r.code, "enabled": bool(r.enabled), "threshold": r.threshold}

@app.delete("/api/v1/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: str, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_key(x_api_key)
    with SessionLocal() as db:
        r = db.query(Rule).filter(Rule.id == rule_id).first()
        if not r:
            raise HTTPException(status_code=404, detail={"error": {"code": "RULE_NOT_FOUND", "message": "Rule not found"}})
        db.delete(r)
        db.commit()
    return