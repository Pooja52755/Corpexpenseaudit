# How RL (Reinforcement Learning) is Used in CorpExpenseAudit

## Quick Overview

Your system uses **reward signals** (RL) to guide the LLM agent toward making correct auditing decisions. Here's how:

```
Agent Observes Claims → Agent Takes Action → Environment Gives REWARD → Agent Learns Pattern
                                                      ↓
                                              Positive: Continue this strategy
                                              Negative: Avoid this approach
```

---

## The RL Loop (40 Steps Example)

### Step-by-Step Breakdown

#### **STEP 1-3: INSPECTION (Gathering Information)**
```
Agent: "I'll inspect claim ABC123 to understand what was claimed"
Environment: "✓ REWARD: +0.10"
→ Message: "Good! Information gathering is correct first step"
```
- **Why positive?** Inspecting claims gives the agent ground truth to make better decisions
- **RL Signal:** Encourages the policy to inspect claims systematically

#### **STEP 4-6: CATEGORIZATION (Classify Expense Type)**
```
Agent: "This claim (meals) should be categorized as MEALS with 92% confidence"
Environment: "✓ REWARD: +0.15" (if correct category)
             "✗ REWARD: -0.10" (if wrong category)
→ Message: "Great catch! You correctly identified the category"
```
- **Why reward varies?** Correct categorization gets positive reward; incorrect gets penalty
- **RL Signal:** Agent learns which features indicate which category

#### **STEP 7-9: GST VERIFICATION (Check Compliance)**
```
Agent: "Verifying GST invoice validity for claim..."
Environment: "REWARD: +0.20" (if correct assessment)
```
- **Why important?** GST compliance is legally critical
- **RL Signal:** High positive reward for getting it right; encourages thoroughness

#### **STEP 10-15: FRAUD DETECTION (Identify Red Flags)**
```
Agent: "Flagging claim as FRAUD - identical claim submitted 3x"
Environment Options:
  ✓ REWARD: +0.50 (Actually fraudulent) → "Excellent fraud detection!"
  ✗ REWARD: -0.30 (False positive) → "This damaged trust unfairly"
```
- **Why huge difference?** Fraud detection is critical; false accusations are expensive
- **RL Signal:** Heavily rewards correct fraud detection; heavily penalizes false positives

#### **STEP 16-20: DECISION MAKING (Approve/Reject/Request Info)**
```
Agent: "APPROVE claim XYZ - valid, compliant, not fraudulent"
Environment: "✓ REWARD: +0.25" (if decision is optimal)

OR

Agent: "REJECT claim for missing documentation"
Environment: "✓ REWARD: +0.20" (if justified and correct)
```
- **Why different rewards?** Each decision path has different risk/benefit profiles
- **RL Signal:** Guides agent toward optimal audit outcomes

#### **STEP 21-38: REPETITION & PATTERN LEARNING**
```
Processing multiple claims... Agent sees repeated patterns:
  "When I see: merchant in high-risk category + large amount + no invoice
   → I should FLAG AND REJECT"

Rewards reinforce this pattern:
  ✓ +0.35 reward when following this pattern correctly
  ✗ -0.25 reward when missing pattern
```
- **Pattern Learning:** RL accumulates experience; agent gets better
- **Cumulative Reward:** Increasing over steps = agent improving

#### **STEP 39-40: EXPORT & FINALIZE**
```
Agent: "All claims reviewed. EXPORT_FINAL_REPORT"
Environment: Runs grading metrics
  Final Accuracy: 92%
  Fraud Detection: 88%
  → REWARD: +1.50 (Task completion bonus)
```

---

## The Reward Structure (Why Each Action Gets Certain Rewards)

### **Positive Rewards** (+)
| Action | Normal | Optimal | Reason |
|--------|--------|---------|--------|
| Inspect Claim | +0.10 | +0.10 | Information gathering |
| Categorize (Correct) | +0.15 | +0.15 | Accuracy |
| Verify GST (Correct) | +0.20 | +0.25 | Compliance critical |
| Flag Fraud (True) | +0.50 | +0.60 | High value anti-fraud |
| Approve Valid Claim | +0.25 | +0.30 | Legitimate expense |
| Reject Invalid Claim | +0.30 | +0.35 | Prevents loss |
| Task Completion | +1.00 | +1.50 | Finalization bonus |

### **Negative Rewards** (-)
| Action | Penalty | Reason |
|--------|---------|--------|
| Categorize (Wrong) | -0.10 | Misclassification |
| Flag Non-Fraud as Fraud | -0.30 | False accusation (expensive) |
| Approve Fraudulent Claim | -0.50 | Major miss (biggest penalty) |
| Inefficient Step | -0.05 | Over-using steps |
| Invalid Action | -0.05 to -0.10 | Errors |

---

## How RL Guides Learning Over 40 Steps

### **Early Steps (1-5): Exploration**
- Agent tries different approaches
- Gets mixed rewards
- Learns what information matters

### **Middle Steps (6-25): Pattern Recognition**
- Agent recognizes patterns: "Claims with pattern X are usually fraudulent"
- Reward signals reinforce correct patterns
- Cumulative reward starts increasing steadily

### **Late Steps (26-40): Optimization**
- Agent focuses on high-reward actions
- Skips low-confidence decisions
- Maximizes efficient claim processing
- Final export completes task

### **Cumulative Effect**
```
Step 1:  Cumulative Reward =  +0.10
Step 5:  Cumulative Reward =  +0.65 (5 inspections)
Step 10: Cumulative Reward =  +2.15 (inspections + categorization)
Step 20: Cumulative Reward =  +5.45 (pattern learning pays off)
Step 30: Cumulative Reward =  +8.90 (optimization phase)
Step 40: Cumulative Reward = +12.50 (task complete + bonus)
```

---

## The Mathematical Model Behind RL

### **Policy Gradient Insight**
```python
# Reward signal updates agent's policy:
if reward > 0:
    # Increase probability of this action in similar situations
    policy[state][action] *= (1 + reward)
else:
    # Decrease probability of this action
    policy[state][action] *= (1 - abs(reward))
```

### **Cumulative/Total Return**
```python
G_t = sum of all future rewards from step t onwards
    = r_t + γ*r_{t+1} + γ²*r_{t+2} + ...
    
Where γ (gamma) = discount factor (usually 0.99)
      = value of future rewards vs immediate reward
```

In your system: Early good decisions compound through future steps!

---

## Why This RL Approach Works for Auditing

### **1. Safety (Low False Positives)**
Large penalty (-0.30 to -0.50) for false fraud accusations teaches agent to be confident before flagging

### **2. Accuracy (High True Positives)**
Large reward (+0.50 to +0.60) for correct fraud detection teaches thorough investigation

### **3. Efficiency (Time Bound)**
Penalty for wasting steps (-0.05) encourages quick decisions while maintaining accuracy

### **4. Compliance (Critical Paths)**
Higher rewards (0.20-0.25) for GST/policy verification ensures these non-negotiable tasks are done

### **5. Adaptation**
Agent learns most rewarding sequence of actions and increases probability of that sequence

---

## Seeing It In Action: Run the Demo

```bash
python demo_40_steps.py
```

This will show you:
- ✅ Real agent actions
- 📊 Real reward signals
- 📈 Cumulative learning curve
- 🎯 How rewards guide decisions over 40 steps

---

## Key Metrics to Watch

After 40 steps, evaluate:

| Metric | Meaning |
|--------|---------|
| **Cumulative Reward** | Total learning - should increase smoothly |
| **Avg Reward/Step** | Efficiency - should be positive |
| **Fraud Detection Accuracy** | Correct fraud catches |
| **False Positive Rate** | Wrong fraud flags (should be low) |
| **Steps Used** | Efficiency - use fewer steps to get high score |

---

## Summary

Your RL system works like this:

1. **Agent observes** a claim (state)
2. **Agent decides** action (inspect, categorize, verify, decide)
3. **Environment returns** reward signal indicating decision quality
4. **Agent learns** to maximize future rewards by adjusting behavior
5. **Over 40 steps** = accumulates experience and improves decisions
6. **Final score** = sum of all reward signals + grading accuracy check

The rewards are **designed** to:
- ✅ Encourage correct auditing
- ✅ Penalize mistakes proportionally 
- ✅ Force compliance with critical checks
- ✅ Improve efficiency over time

This is exactly how RL works in practice! 🎯
