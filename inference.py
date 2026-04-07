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
import time
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
        
        # FIX: Error tracking to prevent infinite loops
        self.claim_errors = {}  # claim_id -> error count
        self.completed_claims = set()  # Claims that are fully processed
        self.blocked_claims = set()  # Claims that hit max errors
        self.last_error = None  # Last error from environment
        self.consecutive_errors = 0  # Track consecutive errors on same claim
        self.last_action = None  # Track last action for loop detection
        self.last_reward = None  # Track last reward for loop detection
        
        # AMNESIA FIX: Track full episode history for LLM context
        self.step_history = []  # List of {step, action_type, reward, error}
        
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
                
                # STATE SYNC FIX: Update claim_state ONLY on success (no error)
                # This prevents loops where we keep trying the same action on same claim
                if not info.get("error"):
                    action_type = action.get("action_type")
                    claim_id = action.get("action_data", {}).get("claim_id")
                    
                    if claim_id and claim_id in self.claim_states:
                        if action_type == "inspect_claim":
                            self.claim_states[claim_id]["inspected"] = True
                            # CAPTURE TRUE AMOUNT AND DESCRIPTION from claim_details in info or state
                            details = info.get('claim_details') or state.get('claim_details')
                            if details:
                                self.claim_states[claim_id]['true_amount'] = float(details.get('amount', 100.0))
                                self.claim_states[claim_id]['description'] = details.get('description', '')
                                print(f"[DEBUG] Stored in Memory from claim_details: amount={self.claim_states[claim_id]['true_amount']}, desc={self.claim_states[claim_id]['description']}", file=sys.stderr)
                            else:
                                # Fallback: try claims_summary
                                if 'claims_summary' in state:
                                    for claim in state['claims_summary']:
                                        if claim.get('claim_id') == claim_id:
                                            self.claim_states[claim_id]['true_amount'] = float(claim.get('amount', 100.0))
                                            self.claim_states[claim_id]['description'] = claim.get('description', '')
                                            print(f"[DEBUG] Stored in Memory from claims_summary: amount={self.claim_states[claim_id]['true_amount']}, desc={self.claim_states[claim_id]['description']}", file=sys.stderr)
                                            break
                        elif action_type == "categorize_claim":
                            self.claim_states[claim_id]["categorized"] = True
                        elif action_type == "verify_gst":
                            self.claim_states[claim_id]["verified_gst"] = True
                        elif action_type in ["approve_claim", "reject_claim", "flag_fraud"]:
                            self.claim_states[claim_id]["decided"] = True
                            self.completed_claims.add(claim_id)  # Mark as completed so we don't repeat it
                    
                    # STEP LIMIT: Break early if 6 claims completed or 35 steps reached
                    if len(self.completed_claims) >= 6 or step_num >= 35:
                        print(f"[DEBUG] Reached efficiency limit: {len(self.completed_claims)} claims completed or {step_num} steps. Forcing export.", file=sys.stderr)
                        action = {"action_type": "export_final_report", "action_data": {}}
                        state, reward, done, info = self.env.step(action)
                        final_state = state
                        self.step_count = step_num + 1
                        self.rewards.append(reward)
                        action_str = f"{action['action_type']}()"
                        error_msg = info.get("error") if "error" in info else None
                        log_step(step=step_num + 1, action=action_str, reward=reward, done=done, error=error_msg)
                        break
                
                # RATE LIMIT FIX: Add delay between requests (reduced to 0.7s for faster testing with smaller model)
                time.sleep(0.7)
                
                # AMNESIA FIX: Track this step in episode history for context
                self.step_history.append({
                    "step": step_num,
                    "action_type": action.get("action_type", "unknown"),
                    "reward": reward,
                    "error": info.get("error") if "error" in info else None
                })
                
                # Track last action and reward for loop detection
                self.last_action = action.get("action_type")
                self.last_reward = reward
                
                # FIX: Track errors to prevent infinite loops
                if "error" in info:
                    self.last_error = info["error"]
                    claim_id = action.get("action_data", {}).get("claim_id")
                    if claim_id:
                        self.claim_errors[claim_id] = self.claim_errors.get(claim_id, 0) + 1
                        # If claim has 3+ errors, mark it as blocked and force move to next
                        if self.claim_errors[claim_id] >= 3:
                            self.blocked_claims.add(claim_id)
                        self.consecutive_errors += 1
                    # Force break if too many consecutive errors (rate limit protection)
                    if self.consecutive_errors >= 5:
                        print(f"[DEBUG] Too many consecutive errors, breaking loop to prevent rate limit", file=sys.stderr)
                        break
                else:
                    # Success - reset error counter
                    self.consecutive_errors = 0
                    if action.get("action_type") == "export_final_report":
                        self.completed_claims.add("export_report")
                
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
        """Get next action with ERROR FEEDBACK and AUTO-CLAIM-SWITCHING to fix loops."""
        import time
        
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
        
        # FIX #3: AUTO-SWITCH to next unblocked claim
        # Find first claim that isn't blocked, isn't completed, and isn't in self.completed_claims
        target_claim_id = None
        for claim_id in pending:
            if claim_id not in self.blocked_claims and claim_id not in self.completed_claims:
                target_claim_id = claim_id
                break
        
        # If all pending claims are blocked, export report (forced decision)
        if target_claim_id is None:
            return {
                "action_type": "export_final_report",
                "action_data": {},
                "reasoning": "All remaining claims are blocked or completed. Exporting report."
            }
        
        # Initialize tracking for this claim
        if target_claim_id not in self.claim_states:
            self.claim_states[target_claim_id] = {
                "inspected": False,
                "categorized": False,
                "verified_gst": False,
                "decided": False,
                "true_amount": None,  # Will be set when inspect_claim succeeds
                "description": ""  # Will be set when inspect_claim succeeds
            }
        
        claim_state = self.claim_states[target_claim_id]
        
        # Determine what STAGE we're at for this claim
        if not claim_state["inspected"]:
            next_stage = "INSPECT"
        elif not claim_state["categorized"]:
            next_stage = "CATEGORIZE"
        elif not claim_state["verified_gst"]:
            next_stage = "VERIFY_GST"
        else:
            next_stage = "DECIDE"
        
        # AMNESIA FIX #1: Build complete episode history context
        history_context = ""
        if self.step_history:
            history_lines = []
            for entry in self.step_history[-5:]:  # Show last 5 steps (reduced from 10 to save tokens)
                step = entry['step']
                action = entry['action_type']
                reward = entry['reward']
                error = entry['error']
                error_str = f" | ERROR: {error}" if error else ""
                history_lines.append(f"  Step {step}: {action} → reward={reward:+.2f}{error_str}")
            
            history_context = f"""📋 EPISODE HISTORY (Last 5 steps):
{chr(10).join(history_lines)}

**LEARN FROM HISTORY**: Avoid actions that failed. Use errors to make better decisions.
"""
        
        # Include last error with explicit prohibition
        error_context = ""
        if self.last_error:
            error_context = f"""
⚠️ LAST ACTION ERROR:
"{self.last_error}"

IF THE ERROR SAYS "already inspected":
  You ARE FORBIDDEN from inspecting that claim again!
  You MUST choose a different action:
  - Try: action_type="categorize_claim" (if not yet categorized)
  - Try: action_type="verify_gst" (if not yet verified)
  - Try: action_type="approve_claim" or "reject_claim" or "flag_fraud" (if ready to decide)
  - Or try a DIFFERENT claim_id entirely

IF THE ERROR SAYS "already categorized":
  You ARE FORBIDDEN from categorizing that claim again!
  Move to: action_type="verify_gst" or action_type="approve_claim", etc.
"""
        
        system_prompt = ("You are an expense auditor. You are currently at STAGE: " + str(next_stage) + "\n\n" +
                        str(history_context) + "\n\n" +
                        str(error_context) + "\n\n" +
                        "CRITICAL: Category accuracy matters! Correct = +0.15, Wrong = -0.08. That's 0.23 difference per claim!\n" +
                        "REWARD EXAMPLES:\n" +
                        "- Hotel booking -> 'travel' = +0.15\n" +
                        "- Flight reservation -> 'travel' = +0.15\n" +
                        "- Lunch at restaurant -> 'meals' = +0.15\n" +
                        "- Laptop purchase -> 'equipment' = +0.15\n" +
                        "- Accommodation fee -> 'accommodation' = +0.15\n" +
                        "- Wrong lazy category = -0.08 penalty.\n" +
                        "FOCUS: Start by reading the claim description carefully before picking a category!\n\n" +
                        "═══ MANDATORY WORKFLOW ═══\n" +
                        "1. INSPECT: Look at claim details and REMEMBER THE AMOUNT\n" +
                        '   REQUIRED KEYS: action_type, action_data with claim_id\n' +
                        '   Example: {"action_type": "inspect_claim", "action_data": {"claim_id": "claim-123"}}\n' +
                        "   IMPORTANT: When you inspect, you will see the claim amount. REMEMBER IT for step 4!\n\n" +
                        "2. CATEGORIZE: Assign expense category based on the claim DESCRIPTION\n" +
                        "   Categories: travel, meals, accommodation, equipment, entertainment, miscellaneous\n" +
                        "   IMPORTANT: Pick the MOST SPECIFIC category based on what the claim is actually for.\n" +
                        "   If it's about food/restaurants: 'meals'\n" +
                        "   If it's about flights/hotels/taxis: 'travel'\n" +
                        "   If it's about computers/software/monitors: 'equipment'\n" +
                        "   If it's about temporary lodging beyond hotel: 'accommodation'\n" +
                        "   REWARDS: Correct category = +0.15, Wrong category = -0.08. BE ACCURATE!\n" +
                        '   REQUIRED KEYS: action_type, action_data with claim_id, category, confidence\n' +
                        '   The category MUST be one of: travel, meals, accommodation, equipment, entertainment, miscellaneous\n' +
                        '   Example: {"action_type": "categorize_claim", "action_data": {"claim_id": "claim-123", "category": "travel", "confidence": 0.85}}\n' +
                        "   NOTE: confidence must be between 0.0 and 1.0 (0.9 if you are confident, 0.6 if uncertain)\n" +
                        "   FORBIDDEN: Do NOT omit the category key! Read descriptions carefully!\n\n" +
                        "3. VERIFY_GST: Check GST invoice (status: compliant, non_compliant, not_applicable, unverifiable)\n" +
                        '   REQUIRED KEYS: action_type, action_data with claim_id\n' +
                        '   Example: {"action_type": "verify_gst", "action_data": {"claim_id": "claim-123"}}\n\n' +
                        "4. DECIDE: Approve, reject, or flag as fraud\n" +
                        '   REQUIRED KEYS for approve: action_type, action_data with claim_id AND approved_amount\n' +
                        "   CRITICAL: When you call approve_claim, you MUST include the approved_amount.\n" +
                        "   The approved_amount should be the amount you saw when you ran inspect_claim earlier.\n" +
                        "   If you don't remember, look at the history to find the inspect result.\n" +
                        '   Approve: {"action_type": "approve_claim", "action_data": {"claim_id": "claim-123", "approved_amount": 150.50}}\n' +
                        '   Reject: {"action_type": "reject_claim", "action_data": {"claim_id": "claim-123"}}\n' +
                        '   Flag Fraud: {"action_type": "flag_fraud", "action_data": {"claim_id": "claim-123"}}\n' +
                        "   IMPORTANT: Once you have approved, rejected, or flagged a claim, that task is COMPLETE.\n" +
                        "   You MUST move to the next available Claim ID immediately. Do NOT repeat the same claim_id!\n\n" +
                        "FORBIDDEN ACTIONS:\n" +
                        "- If a claim is already INSPECTED, you are STRICTLY FORBIDDEN from inspecting it again.\n" +
                        "  You MUST choose categorize_claim or verify_gst instead.\n" +
                        "- If a claim is already CATEGORIZED, you are STRICTLY FORBIDDEN from categorizing it again.\n" +
                        "  You MUST move to verify_gst or a decision action.\n" +
                        "- If you have already DECIDED (approved/rejected/flagged) a claim, you MUST move to the next claim_id.\n" +
                        "  Do NOT approve the same claim twice!\n" +
                        "- NEVER omit the 'category' key in categorize_claim\n" +
                        "- NEVER omit the 'approved_amount' key in approve_claim\n" +
                        "- NEVER use uppercase categories like 'Travel' or 'TRAVEL', always use lowercase\n" +
                        "- NEVER default to miscellaneous without thinking!\n\n" +
                        "RULES:\n" +
                        '- Use LOWERCASE action names: "inspect_claim" not "INSPECT_CLAIM"\n' +
                        '- Use LOWERCASE categories: "travel" not "Travel"\n' +
                        "- Each claim needs inspect → categorize → verify → decide in order\n" +
                        "- Once decided, MOVE TO NEXT CLAIM - do not repeat\n" +
                        "- IF YOU GET AN ERROR, DON'T REPEAT IT - move to next stage\n" +
                        "- Inspecting/categorizing same claim twice = -0.05 penalty\n" +
                        "- WRONG CATEGORY = -0.08 penalty. RIGHT CATEGORY = +0.15 reward.\n\n" +
                        "RETURN FORMAT:\n" +
                        "Return ONLY valid JSON on one line. No markdown, no code blocks.\n" +
                        'GOOD: {"action_type": "inspect_claim", "action_data": {"claim_id": "claim-001"}}\n' +
                        'GOOD: {"action_type": "categorize_claim", "action_data": {"claim_id": "claim-001", "category": "travel", "confidence": 0.85}}\n' +
                        'GOOD: {"action_type": "verify_gst", "action_data": {"claim_id": "claim-001"}}\n' +
                        'GOOD: {"action_type": "approve_claim", "action_data": {"claim_id": "claim-001", "approved_amount": 250.75}}\n' +
                       'BAD: Picking miscellaneous without reading the description\n' +
                        'BAD: Missing category in categorize_claim\n' +
                        'BAD: Missing approved_amount in approve_claim\n' +
                        'BAD: Uppercase category like "Travel"\n' +
                        'BAD: Approving the same claim twice\n' +
                        'BAD: Markdown or code blocks'
        )

        # FIX #2: Show completed and blocked claims so LLM knows to skip them
        claims_context = []
        for idx, claim_summary in enumerate(state['claims_summary'][:5]):
            cid = claim_summary['claim_id']
            
            # Show blocked status
            if cid in self.blocked_claims:
                status_str = "🚫 BLOCKED (too many errors, skip this)"
            else:
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
            action_instruction = f"Use action_type='categorize_claim' with claim_id='{target_claim_id}'. Pick ONE category: travel, meals, accommodation, equipment, entertainment, or miscellaneous."
        elif next_stage == "VERIFY_GST":
            action_instruction = f"Use action_type='verify_gst' with claim_id='{target_claim_id}'. Status must be: compliant, non_compliant, not_applicable, or unverifiable."
        else:  # DECIDE
            action_instruction = f"Use ONE of: action_type='approve_claim' OR 'reject_claim' OR 'flag_fraud' with claim_id='{target_claim_id}'."

        user_message = ("Step " + str(state['current_step']) + "/" + str(state['max_steps']) + "\n\n" +
                       "STAGE: " + str(next_stage) + "\n" +
                       "CURRENT TARGET: " + str(target_claim_id) + "\n\n" +
                       str(action_instruction) + "\n\n" +
                       "Pending claims: " + str(len(pending)) + "\n" +
                       "Processed: " + str(len(state['claims_summary']) - len(pending)) + "/" + str(len(state['claims_summary'])) + "\n\n" +
                       "Claims Status:\n" +
                       claims_text + "\n\n" +
                       "NOTE: If current target is blocked (🚫), the system will automatically switch to next claim next step.\n\n" +
                       "════════════════════════════════════════════\n" +
                       "JSON FORMAT EXAMPLES FOR THIS STAGE (COPY EXACTLY):\n" +
                       "════════════════════════════════════════════\n\n" +
                       "IF STAGE = INSPECT:\n" +
                       '  {"action_type": "inspect_claim", "action_data": {"claim_id": "' + target_claim_id + '"}}\n' +
                       "  (Remember the amount you see - you'll need it for DECIDE stage!)\n\n" +
                       "IF STAGE = CATEGORIZE (MUST HAVE: claim_id, category, confidence):\n" +
                       '  {"action_type": "categorize_claim", "action_data": {"claim_id": "' + target_claim_id + '", "category": "travel", "confidence": 0.85}}\n' +
                       "  Allowed categories: travel, meals, accommodation, equipment, entertainment, miscellaneous\n" +
                       "  IMPORTANT: Pick the BEST match based on the claim, not 'miscellaneous'!\n" +
                       "  IMPORTANT: category is REQUIRED - do NOT forget it!\n\n" +
                       "IF STAGE = VERIFY_GST:\n" +
                       '  {"action_type": "verify_gst", "action_data": {"claim_id": "' + target_claim_id + '"}}\n\n' +
                       "IF STAGE = DECIDE:\n" +
                       '  {"action_type": "approve_claim", "action_data": {"claim_id": "' + target_claim_id + '", "approved_amount": 125.50}}\n' +
                       "  ^^^ CRITICAL: Include approved_amount from the inspect result! ^^^\n" +
                       "  OR\n" +
                       '  {"action_type": "reject_claim", "action_data": {"claim_id": "' + target_claim_id + '"}}\n' +
                       "  OR\n" +
                       '  {"action_type": "flag_fraud", "action_data": {"claim_id": "' + target_claim_id + '"}}\n\n' +
                       "════════════════════════════════════════════\n" +
                       "CRITICAL RULES:\n" +
                       "1. Return ONLY the JSON object on ONE line\n" +
                       "2. No markdown, no code blocks, no explanation\n" +
                       "3. For CATEGORIZE: Always include the 'category' key - pick the BEST category, not miscellaneous\n" +
                       "4. For APPROVE: Always include 'approved_amount' from the inspect step\n" +
                       "5. Use lowercase everywhere: 'travel' not 'Travel'\n" +
                       "6. If you get an error, move to the NEXT stage (don't repeat)\n" +
                       "════════════════════════════════════════════"
        )

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            # FIX: Add small delay to prevent rate limiting
            time.sleep(0.1)
            
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
                
                # === CRITICAL: Code-level enforcement ===
                # 1. Block premature export
                if action.get("action_type") == "export_final_report":
                    if len(self.completed_claims) == 0 and state['current_step'] > 10:
                        # Override: force return to current stage instead
                        print(f"[DEBUG] Blocked premature export. No decisions made yet. Forcing {next_stage}", file=sys.stderr)
                        return self._fallback_action(state, next_stage, target_claim_id, claim_state)
                
                # 2. Block stage skipping - force correct action
                expected_actions = {
                    "INSPECT": "inspect_claim",
                    "CATEGORIZE": "categorize_claim",
                    "VERIFY_GST": "verify_gst",
                    "DECIDE": ["approve_claim", "reject_claim", "flag_fraud"]
                }
                
                expected = expected_actions.get(next_stage, [])
                if isinstance(expected, str):
                    expected = [expected]
                
                if action.get("action_type") not in expected and action.get("action_type") != "export_final_report":
                    # LLM tried to skip stages! Override it
                    wrong_action = action.get("action_type")
                    print(f"[DEBUG] Stage violation: tried {wrong_action}, expected {expected}, forcing {next_stage}", file=sys.stderr)
                    return self._fallback_action(state, next_stage, target_claim_id, claim_state)
                
                # 3. Prevent repeating same action on same claim
                if self.last_action == action.get("action_type") and self.last_action and self.last_reward < 0:
                    # Same action as last time AND last reward was negative = infinite loop!
                    print(f"[DEBUG] Repeat action {self.last_action} with negative reward, forcing next stage", file=sys.stderr)
                    return self._fallback_action(state, next_stage, target_claim_id, claim_state)
                
                # Ensure action_data exists and has claim_id
                if "action_data" not in action:
                    action["action_data"] = {}
                
                if action.get("action_type") != "export_final_report":
                    action["action_data"]["claim_id"] = target_claim_id
                    
                    # DYNAMIC DECISION AMOUNT: Use stored true_amount from inspect stage
                    if action.get("action_type") == "approve_claim":
                        true_amount = self.claim_states[target_claim_id].get('true_amount', 100.0)
                        action["action_data"]["approved_amount"] = true_amount
                        print(f"[DEBUG] Using stored true_amount {true_amount} for {target_claim_id}", file=sys.stderr)
                
                # SMART DEFAULTING: Override LLM's lazy guesses with our keyword logic
                if action.get("action_type") == "categorize_claim":
                    action_data = action.get("action_data", {})
                    valid_categories = ["travel", "meals", "accommodation", "office_supplies", "equipment", "entertainment", "miscellaneous"]
                    
                    # Check 1: Missing category entirely
                    if "category" not in action_data:
                        print(f"[DEBUG] LLM failed to provide category, using smart fallback", file=sys.stderr)
                        return self._fallback_action(state, next_stage, target_claim_id, claim_state)
                    
                    category = action_data.get("category", "").lower()
                    
                    # Check 2: Invalid category not in allowed list
                    if category not in valid_categories:
                        print(f"[DEBUG] LLM provided invalid category '{category}', using smart fallback", file=sys.stderr)
                        return self._fallback_action(state, next_stage, target_claim_id, claim_state)
                    
                    # Check 3: Dictionary-based keyword override - reads description to guarantee correct category
                    description = self.claim_states[target_claim_id].get('description', '').lower()
                    print(f"[DEBUG] Using stored description: {description}", file=sys.stderr)
                    
                    # Define keyword mappings for each category
                    keyword_map = {
                        'travel': ['cab', 'fare', 'flight', 'hotel', 'train', 'uber', 'taxi', 'stay'],
                        'meals': ['food', 'lunch', 'dinner', 'restaurant', 'meal', 'cafe'],
                        'equipment': ['laptop', 'monitor', 'keyboard', 'software', 'mouse']
                    }
                    
                    # Check which category keywords match the description
                    matched_category = None
                    for cat, keywords in keyword_map.items():
                        if any(kw in description for kw in keywords):
                            matched_category = cat
                            print(f"[DEBUG] Keyword match found for '{cat}' in description, LLM picked '{category}'", file=sys.stderr)
                            break
                    
                    # STRONG OVERRIDE: If keywords found, force to that category
                    if matched_category:
                        print(f"[DEBUG] FORCING category to '{matched_category}' (confident keyword-based decision)", file=sys.stderr)
                        action["action_data"]["category"] = matched_category
                        action["action_data"]["confidence"] = 1.0
                    elif category == "miscellaneous":
                        # If LLM defaults to miscellaneous with no keywords found, use smart fallback
                        print(f"[DEBUG] LLM defaulted to miscellaneous with no keyword match, using smart fallback", file=sys.stderr)
                        return self._fallback_action(state, next_stage, target_claim_id, claim_state)
                    else:
                        # Use LLM's category if valid and no keyword override matched
                        print(f"[DEBUG] No keyword override matched, using LLM category '{category}'", file=sys.stderr)
                        action["action_data"]["category"] = category
                
                # FORCE AMOUNT ASSIGNMENT: For DECIDE stage, explicitly set from stored memory
                if action.get("action_type") == "approve_claim":
                    action["action_data"]["approved_amount"] = self.claim_states[target_claim_id].get('true_amount', 100.0)
                    print(f"[DEBUG] FORCED approved_amount to {action['action_data']['approved_amount']} from stored true_amount", file=sys.stderr)
                
                # FINAL VERIFICATION: Log the complete action before returning
                print(f"[DEBUG] Final action before return: {action}", file=sys.stderr)
                
                # IMPORTANT: Do NOT update claim_state here! Update only after successful env.step() in run_audit
                # This prevents premature state updates that cause re-inspection loops
                
                return action
            else:
                return self._fallback_action(state, next_stage, target_claim_id, claim_state)
            
        except json.JSONDecodeError:
            return self._fallback_action(state, next_stage, target_claim_id, claim_state)
        except Exception as e:
            print(f"[DEBUG] LLM error: {e}", file=sys.stderr)
            return self._fallback_action(state, next_stage, target_claim_id, claim_state)
    
    def _fallback_action(self, state: Dict[str, Any], stage: str, claim_id: str, claim_state: Dict) -> Dict:
        """Smart fallback that moves through stages with keyword-based categorization."""
        if stage == "INSPECT":
            return {
                "action_type": "inspect_claim",
                "action_data": {"claim_id": claim_id},
                "reasoning": "Fallback: Start by inspecting"
            }
        elif stage == "CATEGORIZE":
            # Smart categorization: look at claim description and match keywords
            category = "travel"  # default to travel (most corporate expenses are travel-related)
            
            if state and 'claims_summary' in state:
                for claim_summary in state['claims_summary']:
                    if claim_summary['claim_id'] == claim_id:
                        description = claim_summary.get('description', '').lower()
                        
                        # Travel keywords
                        if any(kw in description for kw in ['flight', 'hotel', 'travel', 'stay', 'ticket', 'booking', 'taxi', 'uber', 'airbnb']):
                            category = "travel"
                        # Meals keywords
                        elif any(kw in description for kw in ['meal', 'food', 'dinner', 'restaurant', 'lunch', 'breakfast', 'cafe', 'coffee']):
                            category = "meals"
                        # Equipment keywords
                        elif any(kw in description for kw in ['laptop', 'monitor', 'software', 'computer', 'keyboard', 'mouse', 'phone', 'tablet']):
                            category = "equipment"
                        # Office supplies keywords
                        elif any(kw in description for kw in ['office', 'supplies', 'pen', 'paper', 'desk', 'chair', 'printer']):
                            category = "office_supplies"
                        # Accommodation keywords
                        elif any(kw in description for kw in ['accommodation', 'lodging', 'residence', 'apartment', 'room']):
                            category = "accommodation"
                        # Entertainment keywords
                        elif any(kw in description for kw in ['entertainment', 'movie', 'concert', 'event', 'show', 'ticket']):
                            category = "entertainment"
                        
                        break
            
            return {
                "action_type": "categorize_claim",
                "action_data": {
                    "claim_id": claim_id,
                    "category": category,
                    "confidence": 0.7
                },
                "reasoning": f"Fallback: Smart categorization to '{category}' based on keywords"
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
                "action_data": {"claim_id": claim_id, "approved_amount": 100.0},
                "reasoning": "Fallback: Approve with default amount"
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
