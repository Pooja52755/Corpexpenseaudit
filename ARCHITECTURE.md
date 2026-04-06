# Project Architecture & Data Flow

## System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                  CorpExpenseAudit System Architecture                    │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐                                                      │
│  │   models.py  │  Data Classes                                        │
│  ├──────────────┤  ├─ ClaimCategory (Enum)                            │
│  │              │  ├─ ExpenseClaim (Pydantic)                         │
│  │ Validates    │  ├─ AuditState (Pydantic)                          │
│  │ all data     │  ├─ GraderMetrics (Pydantic)                       │
│  │ structures   │  └─ FraudType (Enum)                               │
│  └──────────────┘                                                      │
│       │                                                                │
│       ▼                                                                │
│  ┌──────────────────────────────────────────────────────────┐         │
│  │           environment.py                                 │         │
│  ├──────────────────────────────────────────────────────────┤         │
│  │  CorpExpenseAudit(OpenEnv)                              │         │
│  │                                                          │         │
│  │  reset() ─────────────► Load claims, init state        │         │
│  │                        Return: state (dict)            │         │
│  │                                                          │         │
│  │  step(action) ───────► Execute action                  │         │
│  │                        Calculate reward                │         │
│  │                        Update state                    │         │
│  │                        Return: (state, reward, done, info)        │         │
│  │                                                          │         │
│  │  state_dict() ───────► Convert AuditState to dict      │         │
│  │                        (for LLM input)                 │         │
│  │                                                          │         │
│  │  _calculate_reward() ► Reward function logic           │         │
│  │                        +0.30 fraud detection           │         │
│  │                        -0.40 approve fraudulent        │         │
│  └──────────────────────────────────────────────────────────┘         │
│       │                                                                │
│       ▼                                                                │
│  ┌──────────────────────────────────────────────────────────┐         │
│  │        inference.py                                      │         │
│  ├──────────────────────────────────────────────────────────┤         │
│  │  ExpenseAuditAgent                                      │         │
│  │                                                          │         │
│  │  For each difficulty (easy, medium, hard):             │         │
│  │  ┌─────────────────────────────────────┐               │         │
│  │  │  run_audit() Loop:                  │               │         │
│  │  │  ┌───────────────────────────────┐  │               │         │
│  │  │  │ 1. Get state_dict()           │  │               │         │
│  │  │  │    (from environment)         │  │               │         │
│  │  │  └───────────────────────────────┘  │               │         │
│  │  │           │                          │               │         │
│  │  │           ▼                          │               │         │
│  │  │  ┌───────────────────────────────┐  │               │         │
│  │  │  │ 2. Call LLM (Groq)            │  │               │         │
│  │  │  │    - Ultra-minimal prompt     │  │               │         │
│  │  │  │    - Return: JSON action      │  │               │         │
│  │  │  └───────────────────────────────┘  │               │         │
│  │  │           │                          │               │         │
│  │  │           ▼                          │               │         │
│  │  │  ┌───────────────────────────────┐  │               │         │
│  │  │  │ 3. Execute action             │  │               │         │
│  │  │  │    - env.step(action)         │  │               │         │
│  │  │  │    - Get: (state, R, done)    │  │               │         │
│  │  │  └───────────────────────────────┘  │               │         │
│  │  │           │                          │               │         │
│  │  │           ▼                          │               │         │
│  │  │  ┌───────────────────────────────┐  │               │         │
│  │  │  │ 4. Print progress             │  │               │         │
│  │  │  │    - Step X/50                │  │               │         │
│  │  │  │    - Reward: +0.15            │  │               │         │
│  │  │  │    - Cumulative: +0.45        │  │               │         │
│  │  │  └───────────────────────────────┘  │               │         │
│  │  │           │                          │               │         │
│  │  │           ▼                          │               │         │
│  │  │  ┌───────────────────────────────┐  │               │         │
│  │  │  │ 5. Check if done?             │  │               │         │
│  │  │  │    - done=True ? Exit loop    │  │               │         │
│  │  │  │    - done=False ? Continue    │  │               │         │
│  │  │  └───────────────────────────────┘  │               │         │
│  │  └─────────────────────────────────────┘               │         │
│  │                                                          │         │
│  │  After loop:                                            │         │
│  │  - env.state contains all decisions                     │         │
│  │  - Results: {"easy": result1, "medium": result2, ...}  │         │
│  │                                                          │         │
│  └──────────────────────────────────────────────────────────┘         │
│       │                                                                │
│       ▼                                                                │
│  ┌──────────────────────────────────────────────────────────┐         │
│  │            graders.py                                    │         │
│  ├──────────────────────────────────────────────────────────┤         │
│  │  Evaluation Functions:                                  │         │
│  │                                                          │         │
│  │  run_easy_grader(env)                                   │         │
│  │  ├─ Extract decisions from env.state                    │         │
│  │  ├─ Compare to ground truth (claims.is_fraud)          │         │
│  │  ├─ Calculate metrics                                   │         │
│  │  └─ Return: GraderMetrics                              │         │
│  │                                                          │         │
│  │  Metrics Calculated:                                    │         │
│  │  ├─ Categorization Accuracy                            │         │
│  │  ├─ Fraud Detection Rate                               │         │
│  │  ├─ False Positive Rate                                │         │
│  │  ├─ GST Accuracy                                        │         │
│  │  ├─ Approval Accuracy                                  │         │
│  │  └─ Final Score (0-1.0, weighted average)             │         │
│  │                                                          │         │
│  └──────────────────────────────────────────────────────────┘         │
│       │                                                                │
│       ▼                                                                │
│  ┌──────────────────────────────────────────────────────────┐         │
│  │            OUTPUT (stdout)                               │         │
│  ├──────────────────────────────────────────────────────────┤         │
│  │  EASY Task:                                             │         │
│  │    Final Score: 0.3000 / 1.0000                         │         │
│  │    Categorization: 3/9 (33%)                            │         │
│  │    Fraud Detection: 0/0 (N/A)                           │         │
│  │    ...                                                   │         │
│  │                                                          │         │
│  │  MEDIUM Task:                                           │         │
│  │    Final Score: 0.0000 / 1.0000                         │         │
│  │    ...                                                   │         │
│  │                                                          │         │
│  │  HARD Task:                                             │         │
│  │    Final Score: 0.0225 / 1.0000                         │         │
│  │    ...                                                   │         │
│  │                                                          │         │
│  │  FINAL SUMMARY:                                         │         │
│  │    Average Score: 0.1075                                │         │
│  │                                                          │         │
│  └──────────────────────────────────────────────────────────┘         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
                    ┌─────────────────────┐
                    │  Expense Claims     │
                    │   (JSON Data)       │
                    │   - 9 easy          │
                    │   - 15 medium       │
                    │   - 20 hard         │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────────────────┐
                    │  environment.reset()            │
                    │  Load claims into state         │
                    │  pending_claims = [id1, id2...] │
                    │  reviewed_decisions = {}        │
                    └──────────┬──────────────────────┘
                               │
                               ▼
    ┌──────────────────────────────────────────────────────┐
    │  AGENT LOOP (Step 1 to 50)                           │
    │                                                       │
    │  ┌────────────────────────────────────────────────┐  │
    │  │ Step N:                                        │  │
    │  │                                                 │  │
    │  │ 1. state_dict() = {                            │  │
    │  │      "current_step": N,                        │  │
    │  │      "pending_claims": [claim_ids],           │  │
    │  │      "reviewed_count": X,                      │  │
    │  │      "total_reward": Y.YYYY,                  │  │
    │  │      "claims_summary": [...]                  │  │
    │  │    }                                            │  │
    │  │                                                 │  │
    │  │ 2. LLM_INPUT = f"""                            │  │
    │  │      Step {N}/50                               │  │
    │  │      Pending: {len(pending)}                   │  │
    │  │      Act on: {claim_id}                        │  │
    │  │    """                                          │  │
    │  │                                                 │  │
    │  │ 3. LLM_OUTPUT = groq_api.chat(                 │  │
    │  │      model="llama-3.1-8b-instant",             │  │
    │  │      messages=[system_prompt, user_message]    │  │
    │  │    )                                            │  │
    │  │   # Output: '{"action_type":"inspect_claim"..} │  │
    │  │                                                 │  │
    │  │ 4. action = json.loads(LLM_OUTPUT)             │  │
    │  │   # {                                           │  │
    │  │   #   "action_type": "categorize_claim",       │  │
    │  │   #   "action_data": {                         │  │
    │  │   #     "claim_id": "abc123",                  │  │
    │  │   #     "category": "travel",                  │  │
    │  │   #     "confidence": 0.85                     │  │
    │  │   #   },                                        │  │
    │  │   #   "reasoning": "..."                       │  │
    │  │   # }                                           │  │
    │  │                                                 │  │
    │  │ 5. state, reward, done, info = env.step(action)        │  │
    │  │   Returns:                                      │  │
    │  │   - state: Updated AuditState                  │  │
    │  │   - reward: Float (+0.15 for good, -0.40 bad) │  │
    │  │   - done: Boolean (audit complete?)           │  │
    │  │   - info: {"error": "...", ...}               │  │
    │  │                                                 │  │
    │  │ 6. Update totals:                              │  │
    │  │   cumulative_reward += reward                  │  │
    │  │   step_count += 1                              │  │
    │  │                                                 │  │
    │  │ 7. If done=True, break loop                    │  │
    │  │                                                 │  │
    │  └────────────────────────────────────────────────┘  │
    │   Continue until: done=True OR step_count >= 50      │
    └──────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────────────────┐
                    │  env.state contains:             │
                    │  ├─ categorizations             │
                    │  ├─ fraud_flags                 │
                    │  ├─ approvals                   │
                    │  ├─ rejections                  │
                    │  └─ final_accuracy              │
                    └──────────┬──────────────────────┘
                               │
                               ▼
                    ┌─────────────────────────────────┐
                    │  run_easy_grader(env)           │
                    │  ├─ Compare decisions to truth  │
                    │  ├─ Count correct/incorrect     │
                    │  ├─ Calculate percentages       │
                    │  └─ Return GraderMetrics        │
                    └──────────┬──────────────────────┘
                               │
                               ▼
                    ┌─────────────────────────────────┐
                    │  Final Output:                   │
                    │  {                               │
                    │    "final_score": 0.30,         │
                    │    "categorization_acc": 0.33,  │
                    │    "fraud_detection": 0.0,      │
                    │    "gst_accuracy": 0.0,         │
                    │    "efficiency": 0.825          │
                    │  }                               │
                    └─────────────────────────────────┘
```

---

## Decision Workflow (What Happens in Each Step)

```
Agent sees state:
├─ "I have 5 pending claims"
├─ "Current reward is +0.45"
├─ "Step 2/50"
└─ "Should I inspect, approve, flag, or categorize?"

                         │
                         ▼
Agent calls LLM:
├─ Prompt: "Step 2/50. 5 pending. Next claim: claim_123"
└─ LLM decides: "JSON: {action: 'categorize_claim', data: {...}}"

                         │
                         ▼
Action executed:
├─ Action: Categorize claim_123 as "travel"
├─ Environment checks: Is ground truth "travel"?
├─ Yes → Reward +0.15 ✓
└─ No → Reward -0.08 ✗

                         │
                         ▼
New state returned:
├─ "Now 4 pending claims (one reviewed)"
├─ "New reward: +0.45 + 0.15 = +0.60"
├─ "Step 2/50 completed"
└─ Next iteration starts...
```

---

## Reward Decision Tree

```
                    Agent takes action
                            │
                ┌───────────┼───────────┐
                │           │           │
                ▼           ▼           ▼
           Categorize    Flag Fraud   Approve Claim
           Expense       Concern      or Reject
                │           │           │
                ├─Good───────┼─────┬─────┤
                │            │     │     │
        True+0.15(claim    Fraud   Valid Fraudulent
         Pos)   detected)  ✓+0.30  ✓+0.25 ✗-0.40
        
        False -0.08    -0.25      -0.20
        Neg


        Legend:
        ✓ = Correct decision → Positive reward
        ✗ = Wrong decision → Negative reward
        ✗✗ = Worst action (approve fraud) → -0.40 (HEAVY PENALTY)
```

---

## File Dependency Graph

```
        requirements.txt
              │
    ┌─────────┼─────────┬─────────┐
    │         │         │         │
    ▼         ▼         ▼         ▼
  pydantic   openai  dotenv    pyyaml
    │         │         │         │
    └─────────┴─────────┴─────────┘
            │
            ▼
      models.py ◄─────────────┐
      (Data validation)       │
            │                 │
            ▼                 │
      environment.py          │
      (OpenEnv interface) ────┤
            │                 │
            ├─────────────────┘
            │
            ▼
      inference.py
      (Main agent loop)
            │
            ├────────────────┐
            │                │
            ▼                ▼
        graders.py        api.py
        (Metrics)    (REST endpoints)
            │              │
            └──────┬───────┘
                   │
                   ▼
            Print Results
```

---

## Token Usage Optimization

```
BEFORE Optimization:
┌────────────────────────────────────────────────┐
│ System Prompt (long instructions)  → 300 tokens │
│ State (full claims list)           → 800 tokens │
│ Conversation history (4 messages) → 900 tokens  │
├────────────────────────────────────────────────┤
│ TOTAL: ~2000 tokens per step                   │
│ × 50 steps = 100,000 tokens                    │
│ PROBLEM: Hits rate limit very fast!            │
└────────────────────────────────────────────────┘

AFTER Optimization:
┌────────────────────────────────────────────────┐
│ System Prompt (1 line)              → 20 tokens │
│ State (minimal needed)              → 50 tokens │
│ No conversation history             → 0 tokens  │
├────────────────────────────────────────────────┤
│ TOTAL: ~150 tokens per step                    │
│ × 50 steps = 7,500 tokens                      │
│ RESULT: Fits free tier! (6000 TPM limit/min)   │
└────────────────────────────────────────────────┘

Optimization Factor: 2000 / 150 = 13.3x reduction
```

---

## Environment State Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│  Initial State (after reset())                              │
├─────────────────────────────────────────────────────────────┤
│  {                                                           │
│    "task_id": "task_easy_123",                              │
│    "task_difficulty": "easy",                               │
│    "current_step": 0,                                       │
│    "max_steps": 40,                                         │
│    "pending_claims": [12 claim IDs],                        │
│    "reviewed_count": 0,                                     │
│    "total_claims": 9,                                       │
│    "total_reward": 0.0,                                     │
│    "audit_complete": False,                                 │
│    "categorizations": {},     ← Empty                       │
│    "fraud_flags": {},         ← Empty                       │
│    "approvals": {}            ← Empty                       │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
                           │
            (First action: categorize_claim)
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  After Step 1                                               │
├─────────────────────────────────────────────────────────────┤
│  {                                                           │
│    "task_id": "task_easy_123",                              │
│    "current_step": 1,         ← Incremented                 │
│    "pending_claims": [11 IDs], ← Reduced (1 reviewed)      │
│    "reviewed_count": 1,       ← Incremented                 │
│    "total_reward": +0.15,     ← Updated                    │
│    "categorizations": {       ← Updated                    │
│      "claim_abc": "travel"                                  │
│    },                                                       │
│    "audit_complete": False,                                 │
│    ...                                                       │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
                           │
            (Steps 2-40: More actions)
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  After All Steps (Step 40)                                  │
├─────────────────────────────────────────────────────────────┤
│  {                                                           │
│    "current_step": 40,                                      │
│    "pending_claims": [],      ← All reviewed or max steps   │
│    "reviewed_count": 9,       ← All reviewed                │
│    "total_reward": +2.45,     ← Accumulated                 │
│    "audit_complete": True,    ← Marked complete            │
│    "categorizations": {       ← All decisions recorded     │
│      "claim_abc": "travel",                                 │
│      "claim_def": "meals",                                  │
│      ...                                                    │
│    },                                                       │
│    "fraud_flags": {                                         │
│      "claim_xyz": "duplicate_claim"                         │
│    },                                                       │
│    "approvals": {                                           │
│      "claim_abc": 1500.0  ← Approved amount                │
│    }                                                        │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
                           │
                  (Grading: compare to truth)
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Grading Result                                             │
├─────────────────────────────────────────────────────────────┤
│  Accuracy: 7/9 categorizations correct = 77%               │
│  Fraud Detected: 1/2 frauds caught = 50%                   │
│  False Positives: 0 false flags = 0%                       │
│  Final Score: 0.35 / 1.0                                   │
└─────────────────────────────────────────────────────────────┘
```

