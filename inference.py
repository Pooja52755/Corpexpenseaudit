#!/usr/bin/env python3
"""
CorpExpenseAudit inference agent using OpenAI-compatible API.

Supports:
- OpenAI API
- Groq API
- Hugging Face Router
- Any OpenAI-compatible endpoint

Environment variables:
- API_BASE_URL: Base URL for the API (e.g., https://api.openai.com/v1)
- OPENAI_API_KEY: OpenAI API key
- GROQ_API_KEY: Groq API key
- HF_TOKEN: Hugging Face token
- MODEL_NAME: Model to use (default: gpt-4-turbo or groq model)
"""

import os
import json
import sys
from datetime import datetime
from typing import Optional, Any, Dict
import re

from dotenv import load_dotenv
from openai import OpenAI
from environment import CorpExpenseAudit
from graders import run_easy_grader, run_medium_grader, run_hard_grader, print_grader_results

# Load environment variables from .env file
load_dotenv()


class ExpenseAuditAgent:
    """AI agent for expense claim auditing."""
    
    def __init__(self, task_difficulty: str = "easy", max_steps: int = 50):
        """Initialize the agent."""
        self.task_difficulty = task_difficulty
        self.max_steps = max_steps
        
        # Initialize OpenAI client with flexible base URL
        api_base_url = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
        hf_token = os.getenv("HF_TOKEN")
        api_key = hf_token if hf_token else self._get_api_key()
        
        if not api_key:
            raise ValueError(
                "No API key found. Please set one of: HF_TOKEN, OPENAI_API_KEY, GROQ_API_KEY"
            )
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base_url if api_base_url else None
        )
        
        print("[+] Initialized ExpenseAuditAgent")
        print(f"    Task Difficulty: {task_difficulty}")
        print(f"    Model: {os.getenv('MODEL_NAME', 'gpt2')}")
        print(f"    API Base URL: {api_base_url}")
        
        self.model = os.getenv("MODEL_NAME", "gpt-4-turbo-preview")
        self.env = CorpExpenseAudit(task_difficulty=task_difficulty)
        self.conversation_history = []
    
    @staticmethod
    def _get_api_key() -> Optional[str]:
        """Get API key from environment variables."""
        # Try Gemini first
        key = os.getenv("GEMINI_API_KEY")
        if key:
            return key
        
        # Try OpenAI
        key = os.getenv("OPENAI_API_KEY")
        if key:
            return key
        
        # Try Groq
        key = os.getenv("GROQ_API_KEY")
        if key:
            return key
        
        # Try Hugging Face
        key = os.getenv("HF_TOKEN")
        if key:
            return key
        
        return None
    
    def run_audit(self) -> Dict[str, Any]:
        """Run the complete audit task."""
        print(f"\n{'='*70}")
        print(f"Starting CorpExpenseAudit Task: {self.task_difficulty.upper()}")
        print(f"{'='*70}")
        
        # Reset environment
        initial_state = self.env.reset()
        self._print_task_summary(initial_state)
        
        step_count = 0
        done = False
        
        # Main loop
        while not done and step_count < self.max_steps:
            print(f"\n--- Step {step_count + 1} / {self.max_steps} ---")
            
            # Get agent's action
            action = self._get_agent_action(initial_state if step_count == 0 else None)
            
            if not action:
                print("[-] Failed to get agent action")
                break
            
            # Execute action in environment
            state, reward, done, info = self.env.step(action)
            
            print(f"Action: {action['action_type']}")
            print(f"Reward: {reward:+.4f}")
            print(f"Cumulative Reward: {state['total_reward']:+.4f}")
            
            if "error" in info:
                print(f"[!] Error: {info['error']}")
            
            step_count += 1
            
            # Check if audit is complete
            if done:
                print(f"\n[+] Audit completed in {step_count} steps")
                break
        
        # Generate final report
        if step_count >= self.max_steps and not done:
            print(f"\n[!] Max steps reached. Generating final report...")
            # Force export
            action = {"action_type": "export_final_report", "action_data": {}}
            state, reward, done, info = self.env.step(action)
        
        # Grade the task
        print(f"\n{'='*70}")
        print("GRADING RESULTS")
        print(f"{'='*70}")
        
        if self.task_difficulty == "easy":
            metrics = run_easy_grader(self.env)
        elif self.task_difficulty == "medium":
            metrics = run_medium_grader(self.env)
        else:
            metrics = run_hard_grader(self.env)
        
        print_grader_results(metrics)
        
        return {
            "task_difficulty": self.task_difficulty,
            "steps_used": step_count,
            "final_score": metrics.final_score,
            "metrics": metrics.dict()
        }
    
    def _print_task_summary(self, state: Dict[str, Any]) -> None:
        """Print a summary of the task."""
        print(f"\nTask Summary:")
        print(f"  - Total Claims: {state['total_claims']}")
        print(f"  - Max Steps: {state['max_steps']}")
        print(f"\nSample Claims:")
        for i, claim in enumerate(state['claims_summary'][:3]):
            print(f"  {i+1}. {claim['description']}")
            print(f"     Claim ID: {claim['claim_id']}, Amount: Rs{claim['amount']:.0f}")
    
    def _get_agent_action(self, initial_state: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Get the next action from the agent using LLM - ULTRA TOKEN-OPTIMIZED."""
        state = initial_state or self.env.state_dict() if self.env.state else None
        
        if not state:
            return None
        
        # ULTRA MINIMAL prompt - saves 90% tokens
        system_prompt = """Audit claims. JSON only:{"action_type":"inspect_claim|categorize_claim|verify_gst|flag_fraud|approve_claim|reject_claim|export_final_report","action_data":{},"reasoning":""}"""

        pending = state['pending_claims'][:1] if state['pending_claims'] else []
        if not pending:
            pending = [c['claim_id'] for c in state['claims_summary'][:1]]
        
        # Minimal message
        user_message = f"Step {state['current_step']}/{state['max_steps']}. Pending claims:{len(state['pending_claims'])}. Act on: {pending[0] if pending else 'next'}"

        # Only keep LAST message (not history) to save tokens
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=100  # ULTRA reduced
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                action_json = json_match.group()
                action = json.loads(action_json)
                return action
            else:
                return self._fallback_action(state)
            
        except json.JSONDecodeError as e:
            print(f"[!] JSON error: {e}")
            return self._fallback_action(state)
        except Exception as e:
            print(f"[-] LLM call failed: {e}")
            return self._fallback_action(state)
    
    def _fallback_action(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Return a fallback action when LLM fails."""
        # Simple heuristic: inspect pending claims
        pending = state['pending_claims']
        if pending:
            return {
                "action_type": "inspect_claim",
                "action_data": {"claim_id": pending[0]},
                "reasoning": "Fallback: inspect next pending claim"
            }
        else:
            return {
                "action_type": "export_final_report",
                "action_data": {},
                "reasoning": "Fallback: no pending claims, export report"
            }


def main():
    """Main entry point."""
    print("="*70)
    print("CorpExpenseAudit - AI-Powered Expense Audit System")
    print("="*70)
    
    # Run all 3 tasks
    difficulties = ["easy", "medium", "hard"]
    results = []
    
    for difficulty in difficulties:
        print(f"\n\n{'#'*70}")
        print(f"# Running {difficulty.upper()} Task")
        print(f"{'#'*70}")
        
        try:
            agent = ExpenseAuditAgent(task_difficulty=difficulty)
            result = agent.run_audit()
            results.append(result)
        except Exception as e:
            print(f"[-] Error running {difficulty} task: {e}")
            import traceback
            traceback.print_exc()
    
    # Print summary
    print(f"\n\n{'='*70}")
    print("FINAL SUMMARY - All Tasks")
    print(f"{'='*70}")
    
    for result in results:
        print(f"\n{result['task_difficulty'].upper()} Task:")
        print(f"  - Steps Used: {result['steps_used']}")
        print(f"  - Final Score: {result['final_score']:.4f} / 1.0000")
    
    if results:
        avg_score = sum(r['final_score'] for r in results) / len(results)
        print(f"\nAverage Score: {avg_score:.4f}")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()
