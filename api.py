"""Simple FastAPI wrapper for Hugging Face Spaces deployment."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import os
import json

from environment import CorpExpenseAudit
from graders import run_easy_grader, run_medium_grader, run_hard_grader

app = FastAPI(
    title="CorpExpenseAudit API",
    description="Enterprise Expense Claim Auditing with AI",
    version="1.0.0"
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "CorpExpenseAudit",
        "version": "1.0.0"
    }


@app.post("/audit/easy")
async def audit_easy(num_steps: int = 30):
    """Run easy audit task."""
    try:
        env = CorpExpenseAudit(task_difficulty="easy")
        state = env.reset()
        
        # Simple deterministic strategy for demo
        pending = state['pending_claims'][:]
        actions_taken = 0
        
        for claim_id in pending[:min(5, len(pending))]:
            action = {
                "action_type": "inspect_claim",
                "action_data": {"claim_id": claim_id}
            }
            state, reward, done, info = env.step(action)
            actions_taken += 1
            
            if actions_taken >= num_steps:
                break
        
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
            "categorization_accuracy": metrics.detailed_results['categorization']['accuracy'],
            "gst_accuracy": metrics.gst_accuracy
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit/medium")
async def audit_medium(num_steps: int = 40):
    """Run medium audit task."""
    try:
        env = CorpExpenseAudit(task_difficulty="medium")
        state = env.reset()
        
        # Simple deterministic strategy
        pending = state['pending_claims'][:]
        
        for claim_id in pending[:min(8, len(pending))]:
            action = {"action_type": "inspect_claim", "action_data": {"claim_id": claim_id}}
            state, reward, done, info = env.step(action)
            
            if env.state.current_step >= num_steps:
                break
        
        action = {"action_type": "export_final_report", "action_data": {}}
        state, reward, done, info = env.step(action)
        
        metrics = run_medium_grader(env)
        
        return {
            "task": "medium",
            "score": metrics.final_score,
            "steps_used": env.state.current_step,
            "claims_processed": len(env.state.reviewed_decisions),
            "fraud_detected": metrics.correctly_detected_fraud,
            "total_fraudulent": metrics.total_fraudulent,
            "fraud_detection_rate": metrics.detailed_results['fraud_detection']['detection_rate']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit/hard")
async def audit_hard(num_steps: int = 50):
    """Run hard audit task."""
    try:
        env = CorpExpenseAudit(task_difficulty="hard")
        state = env.reset()
        
        # Simple deterministic strategy
        pending = state['pending_claims'][:]
        
        for claim_id in pending[:min(10, len(pending))]:
            action = {"action_type": "inspect_claim", "action_data": {"claim_id": claim_id}}
            state, reward, done, info = env.step(action)
            
            if env.state.current_step >= num_steps:
                break
        
        action = {"action_type": "export_final_report", "action_data": {}}
        state, reward, done, info = env.step(action)
        
        metrics = run_hard_grader(env)
        
        return {
            "task": "hard",
            "score": metrics.final_score,
            "steps_used": env.state.current_step,
            "claims_processed": len(env.state.reviewed_decisions),
            "fraud_detected": metrics.correctly_detected_fraud,
            "total_fraudulent": metrics.total_fraudulent,
            "fraud_detection_rate": metrics.detailed_results['fraud_detection']['detection_rate'],
            "false_positive_rate": metrics.detailed_results['fraud_detection']['false_positive_rate']
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
    """Root endpoint."""
    return {
        "name": "CorpExpenseAudit",
        "description": "Enterprise Expense Claim Auditing with AI",
        "endpoints": {
            "health": "/health",
            "easy_audit": "POST /audit/easy",
            "medium_audit": "POST /audit/medium",
            "hard_audit": "POST /audit/hard",
            "spec": "GET /spec"
        }
    }
