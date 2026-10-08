"""
Agent Registry REST API

FastAPI-based REST API for agent registry management.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, Path, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from .service import AgentRegistryService
from .monitoring import MonitoringSystem
from .mm_dashboard import MMReviewDashboard


# Pydantic models for API

class AgentSummary(BaseModel):
    """Agent summary for listings"""
    agent_id: str
    title: str
    version: str
    environment: str
    autonomy_level: int
    status: str


class AgentStatusUpdate(BaseModel):
    """Request model for status updates"""
    status: str = Field(..., description="New status value")
    user: str = Field(default="", description="User making the change")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    service: str = "agent-registry-api"


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    details: Optional[List[str]] = None


# Initialize FastAPI app
app = FastAPI(
    title="AML University Agent Registry API",
    description="REST API for managing AI agent registrations with hospital-metaphor governance",
    version="1.0.0"
)

# Global service instances (in production, use dependency injection)
registry_service = AgentRegistryService()
monitoring_service = MonitoringSystem()
mm_dashboard = MMReviewDashboard()


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "service": "AML University Agent Registry API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat()
    )


@app.get("/system/health", response_model=Dict[str, Any])
async def system_health():
    """Get system health metrics"""
    try:
        health = monitoring_service.get_system_health()
        return health
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents", response_model=List[Dict[str, Any]])
async def list_agents(
    status: Optional[str] = Query(None, description="Filter by status"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    autonomy_level: Optional[int] = Query(None, description="Filter by autonomy level")
):
    """List agents with optional filters"""
    try:
        agents = registry_service.list_agents(status, environment, autonomy_level)
        return [agent.to_dict() for agent in agents]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/{agent_id}", response_model=Dict[str, Any])
async def get_agent(
    agent_id: str = Path(..., description="Agent identifier")
):
    """Get agent by ID"""
    try:
        agent = registry_service.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
        return agent.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents", response_model=Dict[str, Any])
async def register_agent(
    agent_data: Dict[str, Any] = Body(..., description="Agent registration data"),
    user: str = Query("", description="User performing registration")
):
    """Register a new agent"""
    try:
        success, db_id, errors = registry_service.register_agent(agent_data, user)
        
        if not success:
            return JSONResponse(
                status_code=400,
                content={"error": "Registration failed", "details": errors}
            )
        
        return {
            "success": True,
            "db_id": db_id,
            "agent_id": agent_data.get('agent_id')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/agents/{agent_id}/status", response_model=Dict[str, Any])
async def update_agent_status(
    agent_id: str = Path(..., description="Agent identifier"),
    update: AgentStatusUpdate = Body(..., description="Status update")
):
    """Update agent status"""
    try:
        success, errors = registry_service.update_status(
            agent_id,
            update.status,
            update.user
        )
        
        if not success:
            return JSONResponse(
                status_code=400,
                content={"error": "Status update failed", "details": errors}
            )
        
        return {"success": True, "agent_id": agent_id, "new_status": update.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/{agent_id}/approve", response_model=Dict[str, Any])
async def approve_agent(
    agent_id: str = Path(..., description="Agent identifier"),
    user: str = Query("", description="User performing approval")
):
    """Approve agent (advance through workflow)"""
    try:
        success, errors = registry_service.approve_agent(agent_id, user)
        
        if not success:
            return JSONResponse(
                status_code=400,
                content={"error": "Approval failed", "details": errors}
            )
        
        return {"success": True, "agent_id": agent_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/{agent_id}/deprecate", response_model=Dict[str, Any])
async def deprecate_agent(
    agent_id: str = Path(..., description="Agent identifier"),
    user: str = Query("", description="User performing deprecation")
):
    """Deprecate an agent"""
    try:
        success, errors = registry_service.deprecate_agent(agent_id, user)
        
        if not success:
            return JSONResponse(
                status_code=400,
                content={"error": "Deprecation failed", "details": errors}
            )
        
        return {"success": True, "agent_id": agent_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/{agent_id}/health", response_model=Dict[str, Any])
async def get_agent_health(
    agent_id: str = Path(..., description="Agent identifier"),
    days: int = Query(30, description="Number of days to look back")
):
    """Get agent health metrics"""
    try:
        health = registry_service.get_agent_health(agent_id, days)
        return health
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/{agent_id}/metrics", response_model=Dict[str, Any])
async def get_agent_metrics(
    agent_id: str = Path(..., description="Agent identifier"),
    days: int = Query(30, description="Number of days to look back")
):
    """Get agent metrics summary"""
    try:
        metrics = monitoring_service.get_agent_metrics_summary(agent_id, days)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/{agent_id}/violations", response_model=List[Dict[str, Any]])
async def get_agent_violations(
    agent_id: str = Path(..., description="Agent identifier"),
    days: int = Query(30, description="Number of days to look back"),
    resolved: Optional[bool] = Query(None, description="Filter by resolution status")
):
    """Get agent violations"""
    try:
        violations = monitoring_service.db.get_violations(
            agent_id=agent_id,
            resolved=resolved,
            days=days
        )
        return violations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/{agent_id}/audit", response_model=List[Dict[str, Any]])
async def get_agent_audit_trail(
    agent_id: str = Path(..., description="Agent identifier"),
    days: int = Query(30, description="Number of days to look back"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(100, description="Maximum number of records")
):
    """Get agent audit trail"""
    try:
        audit = monitoring_service.get_audit_trail(
            agent_id=agent_id,
            event_type=event_type,
            days=days,
            limit=limit
        )
        return audit
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/environments/{environment_name}/roster", response_model=List[Dict[str, Any]])
async def get_environment_roster(
    environment_name: str = Path(..., description="Environment name")
):
    """Get all active agents in an environment (ward roster)"""
    try:
        agents = registry_service.get_environment_roster(environment_name)
        return [agent.to_dict() for agent in agents]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/high-risk", response_model=List[Dict[str, Any]])
async def get_high_risk_agents():
    """Get high-risk agents (high autonomy + internet access)"""
    try:
        agents = registry_service.get_high_risk_agents()
        return agents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/monitoring/violations", response_model=Dict[str, Any])
async def get_violations_summary(
    days: int = Query(30, description="Number of days to look back")
):
    """Get violation summary"""
    try:
        summary = monitoring_service.get_violation_summary(days=days)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/monitoring/tools", response_model=Dict[str, Any])
async def get_tool_usage_stats(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    days: int = Query(30, description="Number of days to look back")
):
    """Get tool usage statistics"""
    try:
        stats = monitoring_service.get_tool_usage_stats(agent_id=agent_id, days=days)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/monitoring/escalations", response_model=Dict[str, Any])
async def get_escalation_report(
    days: int = Query(30, description="Number of days to look back")
):
    """Get escalation report"""
    try:
        report = monitoring_service.get_escalation_report(days=days)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/monitoring/dashboard", response_model=Dict[str, Any])
async def get_performance_dashboard(
    days: int = Query(7, description="Number of days to look back")
):
    """Get performance dashboard data"""
    try:
        dashboard = monitoring_service.get_performance_dashboard(days=days)
        return dashboard
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mm-review/candidates", response_model=List[Dict[str, Any]])
async def get_review_candidates(
    days: int = Query(30, description="Number of days to look back")
):
    """Get agents that need M&M review"""
    try:
        candidates = mm_dashboard.get_review_candidates(days=days)
        return candidates
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mm-review/{agent_id}", response_model=Dict[str, Any])
async def get_mm_review_report(
    agent_id: str = Path(..., description="Agent identifier"),
    days: int = Query(30, description="Number of days to look back")
):
    """Generate M&M review report for an agent"""
    try:
        report = mm_dashboard.generate_review_report(agent_id, days=days)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mm-review/monthly/{year}/{month}", response_model=Dict[str, Any])
async def get_monthly_mm_summary(
    year: int = Path(..., description="Year"),
    month: int = Path(..., ge=1, le=12, description="Month (1-12)")
):
    """Get monthly M&M summary"""
    try:
        summary = mm_dashboard.get_monthly_summary(year, month)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/validate", response_model=Dict[str, Any])
async def validate_agent_data(
    agent_data: Dict[str, Any] = Body(..., description="Agent registration data to validate")
):
    """Validate agent registration data without registering"""
    try:
        from .validator import AgentValidator
        validator = AgentValidator()
        
        is_valid, errors = validator.validate(agent_data)
        
        return {
            "valid": is_valid,
            "errors": errors if not is_valid else []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the API server"""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
