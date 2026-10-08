from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import os

async def enforce_governance(request: Request, call_next):
    """Enforce governance policies for Hospital service"""
    try:
        # Add governance logic here - for now, just pass through
        # In production, this would validate:
        # - Tenant authorization
        # - Rate limiting
        # - Audit logging
        # - Policy compliance
        response = await call_next(request)
        return response
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Governance enforcement failed", "detail": str(e)}
        )