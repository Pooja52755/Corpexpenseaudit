#!/usr/bin/env python3
"""
Demo: Model executing 40 steps with RL reward feedback explained.

Shows how RL is used:
1. Agent takes action (inspect, categorize, verify, approve/reject)
2. Environment returns REWARD signal
3. Reward reinforces good decisions
4. Agent learns to maximize cumulative reward
"""

import os
import sys
from dotenv import load_dotenv
from inference import ExpenseAuditAgent
import json

load_dotenv()


def print_step_demo(step_num, action_type, action_data, reward, cumulative_reward, done, info):
    """Pretty print a step showing RL feedback."""
    print(f"\n{'='*80}")
    print(f"STEP {step_num}: {action_type.upper()}")
    print(f"{'='*80}")
    
    # Show what action the agent decided to take
    claim_id = action_data.get("claim_id", "N/A")
    if action_type == "inspect_claim":
        print(f"📋 ACTION: Inspecting claim {claim_id}")
        print(f"   → Agent wants to gather information about this expense")
    
    elif action_type == "categorize_claim":
        category = action_data.get("category", "unknown")
        confidence = action_data.get("confidence", 0.0)
        print(f"🏷️  ACTION: Categorizing claim {claim_id}")
        print(f"   → Category: {category} (confidence: {confidence:.1%})")
    
    elif action_type == "verify_gst":
        print(f"✓ ACTION: Verifying GST compliance for claim {claim_id}")
        print(f"   → Agent checking if invoice is valid")
    
    elif action_type == "flag_fraud":
        reason = action_data.get("reason", "")
        print(f"🚩 ACTION: Flagging as FRAUD - {claim_id}")
        print(f"   → Reason: {reason}")
    
    elif action_type == "approve_claim":
        amount = action_data.get("approved_amount", 0)
        print(f"✅ ACTION: APPROVING claim {claim_id}")
        print(f"   → Approved amount: ${amount:.2f}")
    
    elif action_type == "reject_claim":
        reason = action_data.get("reason", "")
        print(f"❌ ACTION: REJECTING claim {claim_id}")
        print(f"   → Reason: {reason}")
    
    elif action_type == "export_final_report":
        print(f"📤 ACTION: Exporting final audit report")
        print(f"   → Wrapping up audit process")
    
    # Show the RL REWARD signal (this is the key RL part!)
    print(f"\n🎯 RL REWARD SIGNAL:")
    print(f"   Immediate Reward: {reward:+.4f}")
    print(f"   Cumulative Reward: {cumulative_reward:.4f}")
    
    # Explain what the reward means
    if reward > 0.3:
        print(f"   ⭐ EXCELLENT! Strong positive signal - this was a great decision!")
    elif reward > 0.1:
        print(f"   ⬆️  Good! Positive signal - agent is learning correct behavior")
    elif reward > -0.1:
        print(f"   ➡️  Neutral - this action had minimal impact")
    elif reward > -0.3:
        print(f"   ⬇️  Weak negative - not ideal but could be recoverable")
    else:
        print(f"   ❌ Strong negative signal - agent should avoid this action pattern")
    
    # Show any errors
    if "error" in info and info["error"]:
        print(f"\n⚠️  ERROR: {info['error']}")
    
    # Show claim details if available
    if "claim_details" in info:
        details = info["claim_details"]
        print(f"\n📄 CLAIM DETAILS:")
        print(f"   Amount: ${details.get('amount', 0):.2f}")
        print(f"   Description: {details.get('description', 'N/A')}")
        print(f"   Category: {details.get('correct_category', 'unknown')}")
        print(f"   Is Fraud: {details.get('is_fraud', False)}")
        if details.get('fraud_types'):
            print(f"   Fraud Types: {', '.join(details.get('fraud_types', []))}")
    
    print(f"\nDone: {done}")


def run_demo():
    """Run 40-step demo showing RL in action."""
    print("\n" + "="*80)
    print("🤖 CORP EXPENSE AUDIT - 40 STEP RL DEMONSTRATION")
    print("="*80)
    print("""
HOW RL IS USED HERE:
━━━━━━━━━━━━━━━━━━━━━━
1. OBSERVATION: Agent observes expense claims to audit
2. ACTION: Agent decides what to do (inspect, categorize, verify, approve/reject)
3. REWARD: Environment gives a REWARD signal
   - Positive rewards (+) for correct decisions
   - Negative rewards (-) for mistakes/inefficiency
4. LEARNING: Agent learns to maximize total reward
5. REPEAT: Continue for up to 40 steps

The goal is to reach high cumulative reward while auditing claims correctly!
    """)
    
    try:
        # Initialize agent
        agent = ExpenseAuditAgent(task_difficulty="easy", max_steps=40)
        print(f"Model: {agent.model}")
        print(f"API: {os.getenv('API_BASE_URL', 'https://api.openai.com/v1')}")
        
        # Reset environment
        initial_state = agent.env.reset()
        print(f"\n📊 INITIAL STATE:")
        print(f"   Total claims to audit: {initial_state['total_claims']}")
        print(f"   Max steps allowed: {initial_state['max_steps']}")
        print(f"   Pending claims: {len(initial_state['pending_claims'])}")
        
        done = False
        cumulative_reward = 0.0
        step_count = 0
        
        # Run up to 40 steps
        for step_num in range(1, 41):
            if done:
                print(f"\n✅ Task completed before step 40!")
                break
            
            # Get action from agent (LLM decides what to do)
            action = agent._get_agent_action(initial_state if step_num == 1 else None)
            
            if not action:
                action = {"action_type": "export_final_report", "action_data": {}}
            
            # Execute action in environment (get RL reward)
            state, reward, done, info = agent.env.step(action)
            cumulative_reward += reward
            step_count = step_num
            
            # Display step with RL reward explanation
            action_type = action.get("action_type", "unknown")
            action_data = action.get("action_data", {})
            
            print_step_demo(
                step_num=step_num,
                action_type=action_type,
                action_data=action_data,
                reward=reward,
                cumulative_reward=cumulative_reward,
                done=done,
                info=info
            )
            
            if done:
                break
            
            # Brief pause for readability
            import time
            time.sleep(0.5)
        
        # Summary
        print(f"\n{'='*80}")
        print(f"📈 FINAL RL METRICS AFTER {step_count} STEPS:")
        print(f"{'='*80}")
        print(f"Total Cumulative Reward: {cumulative_reward:.4f}")
        print(f"Average Reward per Step: {cumulative_reward/step_count:.4f}")
        print(f"Claims Processed: {len(agent.completed_claims)}")
        print(f"All Rewards: {[f'{r:.2f}' for r in agent.rewards]}")
        
        # Run grader to see final score
        if agent.task_difficulty == "easy":
            from graders import run_easy_grader
            metrics = run_easy_grader(agent.env)
        else:
            metrics = None
        
        if metrics:
            print(f"\n🎓 GRADING RESULTS:")
            print(f"   Final Score: {metrics.final_score:.4f}")
            print(f"   Audit Accuracy: {metrics.audit_accuracy:.2%}")
            print(f"   Efficiency Score: {metrics.efficiency_score:.2%}")
        
        print(f"\n{'='*80}")
        print("✨ Demo Complete - This shows how RL guides the model's decisions!")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_demo()
