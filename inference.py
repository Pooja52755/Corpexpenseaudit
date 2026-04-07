#!/usr/bin/env python3
"""
CorpExpenseAudit inference agent using OpenAI-compatible API.

Matches OpenEnv STDOUT format:
  [START] task=<task> env=<env> model=<model>
  [STEP] step=<n> action=<action> reward=<r> done=<bool> error=<msg>
  [END] success=<bool> steps=<n> score=<score> rewards=<r1,r2,...>

Supports:
- OpenAI API
- Groq API  (grok-2-latest, grok-beta)
- Hugging Face Router
- Any OpenAI-compatible endpoint

Environment variables:
- API_BASE_URL: Base URL for the API (default: https://api.openai.com/v1)
- MODEL_NAME: Model to use (default: gpt-4-turbo-preview)
- OPENAI_API_KEY: OpenAI API key
- GROQ_API_KEY: Groq API key (for Groq endpoint)
- HF_TOKEN: Hugging Face token
"""

import os
import json
import sys
from datetime import datetime
from typing import Optional, Any, Dict, List
import re

from dotenv import load_dotenv
from openai import OpenAI
from environment import CorpExpenseAudit
from graders import run_easy_grader, run_medium_grader, run_hard_grader, print_grader_results

# Load environment variables from .env file
load_dotenv()


def log_start(task: str, env: str, model: str) -> None:
    """Emit [START] line to stdout."""
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    """Emit [STEP] line to stdout."""
    error_val = error if error else "null"
    done_str = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_str} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    """Emit [END] line to stdout."""
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)


class ExpenseAuditAgent:
    """AI agent for expense claim auditing with OpenEnv format compliance."""
    
    def __init__(self, task_difficulty: str = "easy", max_steps: int = 50):
        """Initialize the agent."""
        self.task_difficulty = task_difficulty
        self.max_steps = max_steps
        
        # Get API config
        api_base_url = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
        api_key = self._get_api_key()
        
        if not api_key:
            raise ValueError(
                "No API key found. Please set one of: HF_TOKEN, OPENAI_API_KEY, GROQ_API_KEY"
            )
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base_url if api_base_url else None
        )
        
        self.model = os.getenv("MODEL_NAME", "gpt-4-turbo-preview")
        self.env = CorpExpenseAudit(task_difficulty=task_difficulty)
        
        # Track claim processing state to fix "short-term memory" issue
        self.claim_states = {}  # claim_id -> {"inspected": bool, "categorized": bool, "decided": bool}
        self.step_count = 0
        self.rewards = []
    
    @staticmethod
    def _get_api_key() -> Optional[str]:
        """Get API key from environment variables."""
        # Try HF Token first (router)
        key = os.getenv("HF_TOKEN")
        if key:
            return key
        
        # Try Groq
        key = os.getenv("GROQ_API_KEY")
        if key:
            return key
        
        # Try OpenAI
        key = os.getenv("OPENAI_API_KEY")
        if key:
            return key
        
        return None
    
    def run_audit(self) -> Dict[str, Any]:
        """Run the complete audit task with OpenEnv format compliance."""
        # Emit [START] line
        log_start(task=self.task_difficulty, env="CorpExpenseAudit", model=self.model)
        
        # Reset environment (no seeding for truly random claim IDs)
        initial_state = self.env.reset()
        
        done = False
        success = False
        score = 0.0
        final_state = None
        
        try:
            # Main loop
            for step_num in range(1, self.max_steps + 1):
                if done:
                    break
                
                # Get agent's action
                action = self._get_agent_action(initial_state if step_num == 1 else None)
                
                if not action:
                    # Fallback to export if model fails repeatedly
                    action = {"action_type": "export_final_report", "action_data": {}}
                
                # Execute action in environment
                state, reward, done, info = self.env.step(action)
                final_state = state
                self.step_count = step_num
                self.rewards.append(reward)
                
                # Emit [STEP] line
                action_str = f"{action['action_type']}({action.get('action_data', {})})"
                error_msg = info.get("error") if "error" in info else None
                log_step(step=step_num, action=action_str, reward=reward, done=done, error=error_msg)
                
                # Check if audit is complete
                if done:
                    break
            
            # Generate final report if not done
            if not done and self.step_count >= self.max_steps:
                action = {"action_type": "export_final_report", "action_data": {}}
                state, reward, done, info = self.env.step(action)
                final_state = state
                self.step_count += 1
                self.rewards.append(reward)
                log_step(
                    step=self.step_count,
                    action=f"{action['action_type']}()",
                    reward=reward,
                    done=done,
                    error=info.get("error") if "error" in info else None
                )
            
            # Grade the task
            if self.task_difficulty == "easy":
                metrics = run_easy_grader(self.env)
            elif self.task_difficulty == "medium":
                metrics = run_medium_grader(self.env)
            else:
                metrics = run_hard_grader(self.env)
            
            score = metrics.final_score
            success = score >= 0.5  # 50% threshold for success
            
        except Exception as e:
            print(f"[ERROR] {str(e)}", file=sys.stderr)
            success = False
            score = 0.0
        
        finally:
            # Emit [END] line
            log_end(success=success, steps=self.step_count, score=score, rewards=self.rewards)
        
        return {
            "task_difficulty": self.task_difficulty,
            "steps_used": self.step_count,
            "final_score": score,
            "success": success,
            "total_reward": sum(self.rewards),
            "rewards": self.rewards
        }
    
    def _get_agent_action(self, initial_state: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Get next action with SHORT-TERM MEMORY FIX and DECISION FORCING."""
        state = initial_state or self.env.state_dict() if self.env.state else None
        
        if not state:
            return None
        
        pending = state['pending_claims']
        
        # If NO pending claims left, force export report
        if not pending:
            return {
                "action_type": "export_final_report",
                "action_data": {},
                "reasoning": "All claims processed. Exporting final report."
            }
        
        # STAGE-BASED DECISION MAKING (fix approval gap)
        # Get the first pending claim
        target_claim_id = pending[0]
        
        # Initialize tracking for this claim
        if target_claim_id not in self.claim_states:
            self.claim_states[target_claim_id] = {
                "inspected": False,
                "categorized": False,
                "verified_gst": False,
                "decided": False
            }
        
        claim_state = self.claim_states[target_claim_id]
        
        # Determine what STAGE we're at for this claim
        # Stage 1: INSPECT
        if not claim_state["inspected"]:
            next_stage = "INSPECT"
        # Stage 2: CATEGORIZE (must inspect first)
        elif not claim_state["categorized"]:
            next_stage = "CATEGORIZE"
        # Stage 3: VERIFY GST (optional but helpful)
        elif not claim_state["verified_gst"]:
            next_stage = "VERIFY_GST"
        # Stage 4: MAKE FINAL DECISION (approve/reject/flag)
        else:
            next_stage = "DECIDE"
        
        # Build system prompt with stage guidance - LOWERCASE ACTION NAMES ONLY
        system_prompt = f"""You are an expense auditor. You are currently at STAGE: {next_stage}

CRITICAL: Follow the exact process:
1. INSPECT: Look at claim details using: action_type="inspect_claim"
2. CATEGORIZE: Assign expense category using: action_type="categorize_claim"
3. VERIFY_GST: Check GST invoice using: action_type="verify_gst"
4. DECIDE: Approve, reject, or flag using: action_type="approve_claim" or "reject_claim" or "flag_fraud"

PENALTIES:
- Inspecting same claim twice: -0.05 reward (error message will tell you)
- Categorizing same claim twice: -0.05 reward (error message will tell you)
- Approving fraudulent claims: Major penalty

LOWERCASE ONLY: Use lowercase action names like "inspect_claim", not "INSPECT_CLAIM" or "InspectClaim"

Return ONLY valid JSON with lowercase action_type:
{{"action_type":"inspect_claim","action_data":{{"claim_id":"..."}},"reasoning":"..."}}
{{"action_type":"categorize_claim","action_data":{{"claim_id":"...","category":"travel","confidence":0.8}},"reasoning":"..."}}
{{"action_type":"approve_claim","action_data":{{"claim_id":"..."}},"reasoning":"..."}}"""

        # Build rich context for LLM showing what's been done
        claims_context = []
        for idx, claim_summary in enumerate(state['claims_summary'][:5]):
            cid = claim_summary['claim_id']
            cs = self.claim_states.get(cid, {})
            
            status_parts = []
            if cs.get("inspected"):
                status_parts.append("✓Inspected")
            if cs.get("categorized"):
                status_parts.append("✓Categorized")
            if cs.get("verified_gst"):
                status_parts.append("✓GST-checked")
            if cs.get("decided"):
                status_parts.append("✓DECIDED")
            
            status_str = " ".join(status_parts) if status_parts else "❌ NOT STARTED"
            
            line = f"- {cid}: {claim_summary['description'][:40]} | {status_str}"
            claims_context.append(line)
        
        claims_text = "\n".join(claims_context)
        
        # Stage-specific prompts
        if next_stage == "INSPECT":
            action_instruction = f"Use action_type='inspect_claim' with claim_id='{target_claim_id}'. Look at ALL details."
        elif next_stage == "CATEGORIZE":
            action_instruction = f"Use action_type='categorize_claim' with claim_id='{target_claim_id}'. Pick ONE category: travel, meals, accommodation, office_supplies, equipment, entertainment, or miscellaneous."
        elif next_stage == "VERIFY_GST":
            action_instruction = f"Use action_type='verify_gst' with claim_id='{target_claim_id}'. Status must be: compliant, non_compliant, not_applicable, or unverifiable."
        else:  # DECIDE
            action_instruction = f"Use ONE of: action_type='approve_claim' OR 'reject_claim' OR 'flag_fraud' with claim_id='{target_claim_id}'."

        user_message = f"""Step {state['current_step']}/{state['max_steps']}

STAGE: {next_stage}
TARGET: {target_claim_id}

{action_instruction}

Pending claims: {len(pending)}
Processed: {len(state['claims_summary']) - len(pending)}/{len(state['claims_summary'])}

Claim status:
{claims_text}

REQUIRED: Return ONLY lowercase JSON. No markdown, no code blocks. Just the JSON object."""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.5,
                max_tokens=200
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            json_match = re.search(r'\{[\s\S]*?\}', response_text)
            if json_match:
                action_json = json_match.group()
                action = json.loads(action_json)
                
                # ENFORCE LOWERCASE action_type
                if "action_type" in action:
                    action["action_type"] = action["action_type"].lower()
                
                # Ensure action_data exists and has claim_id
                if "action_data" not in action:
                    action["action_data"] = {}
                
                if action.get("action_type") != "export_final_report":
                    action["action_data"]["claim_id"] = target_claim_id
                
                # Track that LLM attempted this stage
                if action.get("action_type") == "inspect_claim":
                    claim_state["inspected"] = True
                elif action.get("action_type") == "categorize_claim":
                    claim_state["categorized"] = True
                    if "confidence" not in action["action_data"]:
                        action["action_data"]["confidence"] = 0.7
                elif action.get("action_type") == "verify_gst":
                    claim_state["verified_gst"] = True
                elif action.get("action_type") in ["approve_claim", "reject_claim", "flag_fraud"]:
                    claim_state["decided"] = True
                
                return action
            else:
                return self._fallback_action(state, next_stage, target_claim_id, claim_state)
            
        except json.JSONDecodeError:
            return self._fallback_action(state, next_stage, target_claim_id, claim_state)
        except Exception as e:
            print(f"[DEBUG] LLM error: {e}", file=sys.stderr)
            return self._fallback_action(state, next_stage, target_claim_id, claim_state)
    
    def _fallback_action(self, state: Dict[str, Any], stage: str, claim_id: str, claim_state: Dict) -> Dict:
        """Smart fallback that moves through stages with LOWERCASE action names."""
        if stage == "INSPECT":
            return {
                "action_type": "inspect_claim",
                "action_data": {"claim_id": claim_id},
                "reasoning": "Fallback: Start by inspecting"
            }
        elif stage == "CATEGORIZE":
            return {
                "action_type": "categorize_claim",
                "action_data": {
                    "claim_id": claim_id,
                    "category": "travel",
                    "confidence": 0.6
                },
                "reasoning": "Fallback: Categorize as travel (default)"
            }
        elif stage == "VERIFY_GST":
            return {
                "action_type": "verify_gst",
                "action_data": {"claim_id": claim_id},
                "reasoning": "Fallback: Verify GST status"
            }
        else:  # DECIDE
            return {
                "action_type": "approve_claim",
                "action_data": {"claim_id": claim_id},
                "reasoning": "Fallback: Approve if verified"
            }


def main():
    """Main entry point - run audits and emit OpenEnv format."""
    difficulties = ["easy", "medium", "hard"]
    results = []
    
    for difficulty in difficulties:
        try:
            agent = ExpenseAuditAgent(task_difficulty=difficulty, max_steps=50)
            result = agent.run_audit()
            results.append(result)
        except Exception as e:
            print(f"[ERROR] Failed to run {difficulty} task: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    # Exit with appropriate code
    success_count = sum(1 for r in results if r.get("success", False))
    exit_code = 0 if success_count >= 2 else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
