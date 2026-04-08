"""OpenEnv API wrapper for CorpExpenseAudit environment - FastAPI implementation."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import os
import json
import uuid
from typing import Optional, Dict, Any

from environment import CorpExpenseAudit
from graders import run_easy_grader, run_medium_grader, run_hard_grader

app = FastAPI(
    title="CorpExpenseAudit OpenEnv API",
    description="Enterprise Expense Claim Auditing with AI - OpenEnv Compatible",
    version="1.0.0"
)

# Store environment instances by session ID
environments: Dict[str, Dict[str, Any]] = {}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "CorpExpenseAudit",
        "version": "1.0.0"
    }


# ============ OpenEnv Specification Endpoints ============

@app.post("/reset")
async def reset(difficulty: str = "easy"):
    """
    OpenEnv reset() endpoint.
    
    Returns: StepResult with initial observation
    """
    try:
        session_id = str(uuid.uuid4())[:8]
        
        # Validate difficulty
        if difficulty not in ["easy", "medium", "hard"]:
            raise ValueError("difficulty must be 'easy', 'medium', or 'hard'")
        
        env = CorpExpenseAudit(task_difficulty=difficulty)
        state_dict = env.reset()
        
        # Store environment for this session
        environments[session_id] = {
            "env": env,
            "difficulty": difficulty,
            "last_action": None
        }
        
        # Return in OpenEnv format
        return {
            "session_id": session_id,
            "observation": {
                "state": state_dict,
                "info": {}
            },
            "reward": 0.0,
            "done": False,
            "info": {
                "difficulty": difficulty,
                "total_claims": state_dict["total_claims"],
                "max_steps": state_dict["max_steps"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step/{session_id}")
async def step(session_id: str, action: Dict[str, Any]):
    """
    OpenEnv step() endpoint.
    
    Args:
        session_id: Session ID from reset()
        action: {"action_type": "...", "action_data": {...}}
    
    Returns: StepResult with observation, reward, done, info
    """
    try:
        if session_id not in environments:
            raise ValueError(f"Invalid or expired session_id: {session_id}")
        
        env = environments[session_id]["env"]
        
        # Execute step with original sync API (logic preserved)
        state_dict, reward, done, info = env.step(action)
        
        # Return in OpenEnv format
        return {
            "session_id": session_id,
            "observation": {
                "state": state_dict,
                "info": info
            },
            "reward": reward,
            "done": done,
            "info": info
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state/{session_id}")
async def get_state(session_id: str):
    """
    OpenEnv state() endpoint - get current state without step.
    """
    try:
        if session_id not in environments:
            raise ValueError(f"Invalid or expired session_id: {session_id}")
        
        env = environments[session_id]["env"]
        state_dict = env.state_dict()
        
        return {
            "session_id": session_id,
            "state": state_dict,
            "info": {
                "difficulty": env.task_difficulty,
                "current_step": env.state.current_step,
                "max_steps": env.state.max_steps
            }
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ Demo / Grading Endpoints ============

@app.post("/audit/easy")
async def audit_easy():
    """Run easy audit task with deterministic strategy."""
    try:
        env = CorpExpenseAudit(task_difficulty="easy")
        state = env.reset()
        
        # Simple deterministic strategy for demo
        pending = state['pending_claims'][:]
        
        for claim_id in pending[:min(5, len(pending))]:
            action = {
                "action_type": "inspect_claim",
                "action_data": {"claim_id": claim_id}
            }
            state, reward, done, info = env.step(action)
        
        # Export final report
        action = {"action_type": "export_final_report", "action_data": {}}
        state, reward, done, info = env.step(action)
        
        metrics = run_easy_grader(env)
        
        return {
            "task": "easy",
            "score": metrics.final_score,
            "steps_used": env.state.current_step,
            "claims_processed": len(env.state.reviewed_decisions),
            "fraud_detected": metrics.correctly_detected_fraud,
            "gst_accuracy": metrics.gst_accuracy
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit/medium")
async def audit_medium():
    """Run medium audit task with deterministic strategy."""
    try:
        env = CorpExpenseAudit(task_difficulty="medium")
        state = env.reset()
        
        # Simple deterministic strategy
        pending = state['pending_claims'][:]
        
        for claim_id in pending[:min(8, len(pending))]:
            action = {"action_type": "inspect_claim", "action_data": {"claim_id": claim_id}}
            state, reward, done, info = env.step(action)
        
        action = {"action_type": "export_final_report", "action_data": {}}
        state, reward, done, info = env.step(action)
        
        metrics = run_medium_grader(env)
        
        return {
            "task": "medium",
            "score": metrics.final_score,
            "steps_used": env.state.current_step,
            "claims_processed": len(env.state.reviewed_decisions),
            "fraud_detected": metrics.correctly_detected_fraud
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit/hard")
async def audit_hard():
    """Run hard audit task with deterministic strategy."""
    try:
        env = CorpExpenseAudit(task_difficulty="hard")
        state = env.reset()
        
        # Simple deterministic strategy
        pending = state['pending_claims'][:]
        
        for claim_id in pending[:min(10, len(pending))]:
            action = {"action_type": "inspect_claim", "action_data": {"claim_id": claim_id}}
            state, reward, done, info = env.step(action)
        
        action = {"action_type": "export_final_report", "action_data": {}}
        state, reward, done, info = env.step(action)
        
        metrics = run_hard_grader(env)
        
        return {
            "task": "hard",
            "score": metrics.final_score,
            "steps_used": env.state.current_step,
            "claims_processed": len(env.state.reviewed_decisions),
            "fraud_detected": metrics.correctly_detected_fraud
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/spec")
async def get_spec():
    """Get OpenEnv specification."""
    try:
        import yaml
        with open("openenv.yaml", "r") as f:
            spec = yaml.safe_load(f)
        return spec
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "name": "CorpExpenseAudit",
        "version": "1.0.0",
        "description": "Enterprise Expense Claim Auditing with AI - OpenEnv Compatible",
        "openenv_endpoints": {
            "reset": "POST /reset (difficulty: easy|medium|hard)",
            "step": "POST /step/{session_id}",
            "state": "GET /state/{session_id}"
        },
        "demo_endpoints": {
            "audit_easy": "POST /audit/easy",
            "audit_medium": "POST /audit/medium",
            "audit_hard": "POST /audit/hard"
        },
        "utils": {
            "health": "GET /health",
            "spec": "GET /spec"
        }
    }
