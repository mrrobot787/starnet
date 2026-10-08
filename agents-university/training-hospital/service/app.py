from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .middleware import enforce_governance
from .policy import sign_policy_ticket
import os
import json
from datetime import datetime

app = FastAPI(title="Agent Hospital")
@app.middleware("http")
async def _gov(req, call_next): return await enforce_governance(req, call_next)

@app.get("/healthz")
def healthz(): return {"ok": True}

HOSPITAL_SHADOW = os.getenv("HOSPITAL_SHADOW","false").lower() in ("1","true","yes")

def _audit(event: str, tenant_id: str, **kwargs):
    """Write audit event to log file"""
    try:
        with open("logs/hospital_audit.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.utcnow().isoformat(),
                "event": event,
                "tenant_id": tenant_id,
                **kwargs
            }) + "\n")
    except Exception:
        pass  # Don't fail on audit write

class TicketReq(BaseModel):
    tenant_id: str
    role_id: str
    tools_requested: list[str]
    dh_tags: list[str]
    sissa_gate: str = "SISSA_HUNTER"
    ttl_seconds: int = 3600
    canary: dict = {"pct":0.1,"duration_s":3600,"rollback_on":{"LatencyZ":">1.0","EG_incidents":">0"}}

@app.post("/v1/policy/ticket")
def issue_ticket(req: TicketReq):
    # here you'd validate role & tools against policy and contraindications table
    token = sign_policy_ticket(
        tenant_id=req.tenant_id,
        roles_allowed=[req.role_id],
        tools_allowed=req.tools_requested,
        ttl_seconds=req.ttl_seconds,
        canary=req.canary,
        dh_tags=req.dh_tags,
        sissa_gate=req.sissa_gate
    )
    
    # Audit the ticket issuance
    _audit("order.submit", req.tenant_id, 
           role_id=req.role_id, 
           tools_requested=req.tools_requested,
           dh_tags=req.dh_tags,
           sissa_gate=req.sissa_gate)
    
    return {"approval_token": token, "ttl_seconds": req.ttl_seconds}