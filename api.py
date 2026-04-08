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


@app.get("/metadata")
async def metadata():
    """OpenEnv HTTP Standard: Metadata endpoint."""
    return {
        "name": "CorpExpenseAudit",
        "description": "Enterprise Expense Claim Auditing with AI - OpenEnv Environment",
        "version": "1.0.0",
        "author": "OpenEnv Hackathon",
        "support_url": "https://github.com/openenv/corpus-audit"
    }


@app.get("/schema")
async def schema():
    """OpenEnv HTTP Standard: Schema endpoint - returns action/observation/state schemas."""
    return {
        "action": {
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "enum": [
                        "inspect_claim",
                        "categorize_claim",
                        "verify_gst",
                        "flag_fraud",
                        "approve_claim",
                        "reject_claim",
                        "request_more_info",
                        "export_final_report"
                    ]
                },
                "action_data": {
                    "type": "object",
                    "description": "Action-specific parameters"
                }
            },
            "required": ["action_type", "action_data"]
        },
        "observation": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "task_difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                "current_step": {"type": "integer"},
                "max_steps": {"type": "integer"},
                "pending_claims": {"type": "array", "items": {"type": "string"}},
                "reviewed_count": {"type": "integer"},
                "total_claims": {"type": "integer"},
                "claims_summary": {"type": "array"},
                "total_reward": {"type": "number"},
                "audit_complete": {"type": "boolean"},
                "final_accuracy": {"type": "number"}
            }
        },
        "state": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "task_difficulty": {"type": "string"},
                "current_step": {"type": "integer"},
                "max_steps": {"type": "integer"},
                "pending_claims": {"type": "array"},
                "reviewed_count": {"type": "integer"},
                "total_claims": {"type": "integer"},
                "claims_summary": {"type": "array"},
                "total_reward": {"type": "number"},
                "audit_complete": {"type": "boolean"},
                "final_accuracy": {"type": "number"}
            }
        }
    }


@app.post("/mcp")
async def mcp_endpoint(request: Dict[str, Any]):
    """OpenEnv HTTP Standard: MCP (Model Context Protocol) endpoint for JSON-RPC."""
    try:
        # Validate JSON-RPC format
        if "jsonrpc" not in request:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request - missing jsonrpc field"
                }
            }
        
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")
        
        # Route to appropriate method
        if method == "reset":
            difficulty = params.get("difficulty", "easy")
            session_id = str(uuid.uuid4())[:8]
            
            env = CorpExpenseAudit(task_difficulty=difficulty)
            state_dict = env.reset()
            
            environments[session_id] = {
                "env": env,
                "difficulty": difficulty,
                "last_action": None
            }
            
            result = {
                "session_id": session_id,
                "observation": state_dict
            }
        
        elif method == "step":
            session_id = params.get("session_id")
            action = params.get("action", {})
            
            if session_id not in environments:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32001,
                        "message": f"Session not found: {session_id}"
                    },
                    "id": request_id
                }
            
            env = environments[session_id]["env"]
            state_dict, reward, done, info = env.step(action)
            
            result = {
                "observation": state_dict,
                "reward": reward,
                "done": done,
                "info": info
            }
        
        elif method == "state":
            session_id = params.get("session_id")
            
            if session_id not in environments:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32001,
                        "message": f"Session not found: {session_id}"
                    },
                    "id": request_id
                }
            
            env = environments[session_id]["env"]
            state_dict = env.state_dict()
            result = {"state": state_dict}
        
        else:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                },
                "id": request_id
            }
        
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        }
    
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            },
            "id": request.get("id")
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


# ============ OpenEnv Standard Endpoints (without path params) ============

@app.post("/step")
async def step_standard(request_data: Dict[str, Any]):
    """
    OpenEnv standard step() endpoint - accepts session_id in body.
    """
    try:
        session_id = request_data.get("session_id")
        action = request_data.get("action", {})
        
        if not session_id:
            raise ValueError("session_id required in request body")
        
        if session_id not in environments:
            raise ValueError(f"Invalid or expired session_id: {session_id}")
        
        env = environments[session_id]["env"]
        state_dict, reward, done, info = env.step(action)
        
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
        raise HTTPException(status_code=404, detail=f"Session not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state")
async def state_standard(session_id: str = None):
    """
    OpenEnv standard state() endpoint - accepts session_id as query param.
    """
    try:
        if not session_id:
            raise ValueError("session_id required as query parameter")
        
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
        raise HTTPException(status_code=404, detail=f"Session not found")
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
