# CorpExpenseAudit - Enterprise Expense Claim Auditing OpenEnv

An AI-powered enterprise expense claim auditing system where agents learn to detect fraud, verify GST compliance, and enforce expense policies. Built on real-world Indian business processes.

## 🎯 Motivation & Problem Statement

**Why This Matters:**
- Indian companies lose **₹2B+ annually** to fraudulent expense claims
- Manual auditing of 1000s of claims is time-consuming and error-prone
- GST compliance violations result in significant tax penalties
- Policy violations damage company culture and trust

**What This Environment Tests:**
- Can an AI agent learn to audit expense claims like a senior finance professional?
- Can it detect sophisticated fraud patterns (duplicates, inflated amounts, fake invoices)?
- Can it verify GST compliance correctly (critical for Indian companies)?
- Can it balance thoroughness with efficiency (not reject too many valid claims)?

## 📋 Environment Description

**CorpExpenseAudit** is a Gym-style OpenEnv environment where AI agents act as senior auditors reviewing employee expense claims. Each claim contains multiple data points (amount, category, merchant, date, GST status) and the agent must decide whether to approve, reject, or flag it for fraud.

### Core Concepts

| Concept | Description |
|---------|-------------|
| **Claim** | Employee expense submission with details (amount, merchant, date, category) |
| **Ground Truth** | Pre-determined labels (correct category, fraud status, GST validity, policy compliance) |
| **Audit** | Agent processes all claims, makes decisions, accumulates rewards |
| **Task** | Collection of claims at specific difficulty (easy/medium/hard) |
| **Episode** | One complete audit (reset → step → step → ... → done) |

## 📁 Project Structure

```
CorpExpenseAudit/
├── models.py              # Pydantic models (ExpenseClaim, AuditState, OpenEnv types)
├── environment.py         # Main CorpExpenseAudit environment class
├── graders.py             # Deterministic graders (easy/medium/hard)
├── inference.py           # Agent inference loop with LLM + OpenEnv API support
├── api.py                 # FastAPI wrapper for remote OpenEnv access
├── openenv.yaml           # OpenEnv formal specification
├── requirements.txt       # Dependencies
├── .env.example           # Configuration template
├── Dockerfile             # Docker build for deployment
└── README.md              # This file
```

---

## 🎮 Action Space

Agents can execute 8 different actions. Each action has specific preconditions and returns immediate feedback.

### Available Actions

```python
# 1. INSPECT_CLAIM
{
  "action_type": "inspect_claim",
  "action_data": {
    "claim_id": str  # Claim to inspect
  }
}
# Effect: Reveals full claim details (amount, merchant, date, description, GST status)
# Reward: 0.0 (information gathering)
# Stage: 1 of 4 in claim workflow

# 2. CATEGORIZE_CLAIM
{
  "action_type": "categorize_claim",
  "action_data": {
    "claim_id": str,
    "category": str,  # travel, meals, accommodation, equipment, entertainment, misc, office_supplies
    "confidence": float  # 0.0-1.0
  }
}
# Effect: Assigns category based on description
# Reward: +0.15 if correct, -0.08 if wrong
# Stage: 2 of 4 in claim workflow

# 3. VERIFY_GST
{
  "action_type": "verify_gst",
  "action_data": {
    "claim_id": str  # Claim to verify
  }
}
# Effect: Checks GST invoice validity (compliant, non_compliant, not_applicable, unverifiable)
# Reward: +0.20 if compliant verified, +0.15 if non-compliance detected
# Stage: 3 of 4 in claim workflow

# 4. APPROVE_CLAIM
{
  "action_type": "approve_claim",
  "action_data": {
    "claim_id": str,
    "approved_amount": float  # Amount to reimburse
  }
}
# Effect: Approves claim for payment
# Reward: +0.25 if valid, -0.40 if fraudulent (WORST PENALTY!)
# Stage: 4 of 4 in claim workflow

# 5. REJECT_CLAIM
{
  "action_type": "reject_claim",
  "action_data": {
    "claim_id": str,
    "reason": str  # duplicate_claim, policy_violation, fraud_detected, insufficient_docs
  }
}
# Effect: Rejects claim
# Reward: +0.30 if correctly rejects fraud, +0.20 if policy violation, -0.20 if valid claim
# Stage: 4 of 4 in claim workflow

# 6. FLAG_FRAUD
{
  "action_type": "flag_fraud",
  "action_data": {
    "claim_id": str  # Claim to investigate
  }
}
# Effect: Escalates to fraud investigation team
# Reward: +0.30 if actual fraud, -0.25 if false positive
# Stage: 4 of 4 in claim workflow

# 7. REQUEST_MORE_INFO
{
  "action_type": "request_more_info",
  "action_data": {
    "claim_id": str,
    "info_needed": str  # receipt, invoice, documentation, clarification
  }
}
# Effect: Requests additional documentation from employee
# Reward: 0.0 (neutral action for uncertain cases)
# Stage: 4 of 4 in claim workflow

# 8. EXPORT_FINAL_REPORT
{
  "action_type": "export_final_report",
  "action_data": {}
}
# Effect: Completes audit and generates report
# Reward: +0.5 × final_accuracy bonus
# Precondition: All pending_claims must be processed
```

### Action Workflow per Claim

**Mandatory 4-stage workflow (must execute in order):**

1. `inspect_claim` → Get claim details
2. `categorize_claim` → Assign category
3. `verify_gst` → Verify GST compliance
4. `approve_claim` OR `reject_claim` OR `flag_fraud` → Make final decision

---

## 📊 Observation Space

Each observation contains full audit state and claim information.

### State Structure

```python
{
  # Task metadata
  "task_id": str,                    # Unique task identifier
  "task_difficulty": str,            # "easy", "medium", "hard"
  "current_step": int,               # Current step (1 to max_steps)
  "max_steps": int,                  # Step limit (40 for easy, 60 for medium, 80 for hard)
  
  # Audit progress
  "pending_claims": list[str],       # Claim IDs still to process
  "reviewed_count": int,             # Claims already reviewed
  "total_claims": int,               # Total claims in task (9/15/20)
  "audit_complete": bool,            # All claims processed?
  
  # Reward tracking
  "total_reward": float,             # Cumulative reward so far
  "current_reward": float,           # Reward from last step
  
  # Performance metrics
  "final_accuracy": float,           # Current score (0.0-1.0)
  "categorization_accuracy": int,    # Claims with correct category
  "fraud_detected": int,             # Fraudulent claims caught
  "false_positives": int,            # Valid claims flagged as fraud
  
  # Claim summaries
  "claims_summary": [
    {
      "claim_id": str,
      "employee_id": str,
      "amount": float,
      "category": str,
      "description": str,
      "merchant_name": str,
      "merchant_city": str,
      "date_of_expense": str,
      "has_gst_invoice": bool,
      "status": str,  # "pending", "inspected", "categorized", "decided"
    },
    ...
  ]
}
```

### When Inspecting a Claim - Extended Details

When `inspect_claim` is called, agent receives:

```python
{
  "claim_details": {
    "claim_id": str,
    "employee_id": str,
    "amount": float,
    "claimed_category": str,
    "description": str,              # Key: Read this for categorization!
    "merchant_name": str,
    "merchant_city": str,
    "date_of_expense": str,
    "mileage_claimed": float,        # For travel claims
    "has_gst_invoice": bool,
    "receipt_provided": bool,
    "notes": str,
  },
  "info": {
    "claim_details": {...}           # Full claim visible after inspect
  }
}
```

---

## 🎯 Task Descriptions

### Task 1: EASY (9 Claims, 40 Steps Maximum)

**Difficulty Justification:**
- Simple, straightforward domestic claims
- No sophisticated fraud patterns
- Clear categorization clues in descriptions
- All receipts/documentation present

**Example Claims:**
1. Cab fare to office - ₹1,500
2. Hotel in Mumbai - ₹8,500
3. Office stationery/pens - ₹2,000
4. Laptop charging cable - ₹1,200

**Expected Actions per Claim:** 5-6 steps
- 1 inspect + 1 categorize + 1 verify_gst + 1 approve/reject = ~4 steps
- Plus some redundant checks

**Expected Baseline Score:** 0.30-0.50
- Random categorization: ~0.33 (1/3 categories correct)
- Basic heuristics: ~0.40-0.50
- Optimized agent: 0.70+

**Key Learning Goals:**
- Master 7 expense categories
- Understand GST compliance basics
- Build simple decision logic

---

### Task 2: MEDIUM (15 Claims, 60 Steps Maximum)

**Difficulty Increase:**
- Mixed claim types (domestic + international)
- Basic fraud patterns (1-2 duplicates, slightly inflated amounts)
- Some missing GST documentation
- Policy edge cases (legitimate business vs personal)

**Example Claims:**
1. Flight to Singapore - ₹25,000 (has fraud: inflated 3x normal)
2. Duplicate hotel claim - ₹8,500 (submitted twice)
3. Personal groceries - ₹3,500 (policy violation)
4. Office supplies - ₹1,200 (legitimate)

**Expected Actions per Claim:** 6-7 steps
- More verification steps needed
- Some claims need additional info requests

**Expected Baseline Score:** 0.20-0.40
- Failing to detect some fraud patterns
- Occasional misclassifications
- Poor efficiency on edge cases

**Key Learning Goals:**
- Detect duplicate/inflated amount fraud patterns
- Handle missing GST documentation
- Distinguish business from personal expenses
- Improve decision confidence

---

### Task 3: HARD (20 Claims, 120 Steps Maximum)

**Difficulty Increase:**
- Sophisticated fraud patterns:
  - Serial duplicates (same claim 3+ times)
  - Fake GST invoices (invalid format/numbers)
  - Same-day round trips (suspicious travel)
  - Cross-referenced fraud (linked to other claims)
- International claims with complex tax implications
- Edge cases requiring careful reading

**Example Claims:**
1. Daily Uber rides (10 x ₹500) - Some are duplicates
2. Hotel booking chain (5 different hotels, 1 claimed twice)
3. Laptop purchase - ₹125,000 (fake GST invoice)
4. Meal expense - ₹50,000 (clearly personal, marked as team lunch)

**Expected Actions per Claim:** 7-8 steps
- Heavy verification needed
- Multiple false positives possible
- Complex decision logic required

**Expected Baseline Score:** 0.05-0.20
- Many fraud patterns missed
- High false positive rate (rejecting valid claims)
- Poor fraud detection rate

**Key Learning Goals:**
- Detect sophisticated fraud patterns
- Balance fraud detection vs false positives
- Manage step efficiency under pressure
- Aggregate information across claims

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.8+
- pip package manager

### Step 1: Clone & Install

```bash
# Clone repository
git clone https://github.com/Pooja52755/Corpexpenseaudit
cd Corpexpenseaudit

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure API Access

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

**Choose ONE API provider:**

**Option A: OpenAI (Recommended for quality)**
```bash
export OPENAI_API_KEY="sk-..."
export MODEL_NAME="gpt-4o-mini"
```

**Option B: Groq (Fastest & cheapest - free tier)**
```bash
export GROQ_API_KEY="gsk_..."
export API_BASE_URL="https://api.groq.com/openai/v1"
export MODEL_NAME="mixtral-8x7b-32768"
```

**Option C: Hugging Face (Good for open models)**
```bash
export HF_TOKEN="hf_..."
export API_BASE_URL="https://api-inference.huggingface.co/v1"
export MODEL_NAME="meta-llama/Llama-2-70b"
```

**Option D: Local Ollama (Privacy-first)**
```bash
# Start Ollama first: ollama serve
export API_BASE_URL="http://localhost:11434/v1"
export OPENAI_API_KEY="local"
export MODEL_NAME="llama2"
```

---

## 💻 Usage Instructions

### Local Mode (Direct Environment)

```bash
# Run inference on all 3 tasks
python inference.py

# Expected output:
# [START] task=easy env=CorpExpenseAudit model=gpt-4o-mini
# [STEP] step=1 action=inspect_claim(...) reward=0.00 done=false error=null
# [STEP] step=2 action=categorize_claim(...) reward=0.15 done=false error=null
# ...
# [END] success=true steps=25 score=0.72 rewards=0.15,0.15,0.02,...
```

### Docker Mode (Remote API)

```bash
# Terminal 1: Start API container
docker build -t corpexpenseaudit:latest .
docker run -p 7860:7860 corpexpenseaudit:latest

# Terminal 2: Run inference against Docker API
export ENVIRONMENT_BASE_URL="http://localhost:7860"
python inference.py

# Docker logs should show:
# POST /reset HTTP/1.1" 200
# POST /step/{session_id} HTTP/1.1" 200
# POST /step/{session_id} HTTP/1.1" 200
```

### Python API for Custom Agents

```python
from environment import CorpExpenseAudit
from graders import run_easy_grader

# Create environment
env = CorpExpenseAudit(task_difficulty="easy")

# Initialize
state = env.reset()
print(f"Total claims: {state['total_claims']}")
print(f"Max steps: {state['max_steps']}")

# Run agent loop
done = False
step = 0
while not done and step < state['max_steps']:
    # Your agent decides action based on state
    claim_id = state['pending_claims'][0]
    action = {
        "action_type": "inspect_claim",
        "action_data": {"claim_id": claim_id}
    }
    
    state, reward, done, info = env.step(action)
    print(f"Step {step}: reward={reward:.2f}, claims_left={len(state['pending_claims'])}")
    step += 1

# Grade the audit
metrics = run_easy_grader(env)
print(f"Final Score: {metrics.final_score:.2f}")
print(f"Fraud Detection: {metrics.correctly_detected_fraud}/{metrics.total_fraudulent}")
```

---

## 📈 Baseline Scores & Expected Performance

### Scoring Formula

```python
final_score = (
    0.30 * categorization_accuracy +      # How often correct category
    0.40 * fraud_detection_rate +         # Fraudulent claims caught
    0.20 * gst_accuracy +                 # GST verifications correct
    0.10 * approval_accuracy -            # Valid claims approved
    fraud_approval_penalty                # Penalty for approving fraud
)

# Penalties:
# - Approving fraudulent claim: -0.40 per claim
# - False positive fraud flag: -0.25 per claim
# - Rejecting valid claim: -0.20 per claim
# - Wrong categorization: -0.08 per claim
```

### Baseline Performance (Random Agent)

| Task | Claims | Baseline | Why |
|------|--------|----------|-----|
| Easy (9 claims) | 9 | 0.35 | Random categorization = 1/7 correct |
| Medium (15 claims) | 15 | 0.25 | ~50% fraud missed, some false positives |
| Hard (20 claims) | 20 | 0.10 | Complex fraud patterns mostly missed |
| **Average** | 44 | **0.23** | Random agent fails >75% of audits |

### Expected Performance Milestones

| Milestone | Easy | Medium | Hard | Techniques |
|-----------|------|--------|------|-----------|
| **Naive** | 0.35 | 0.25 | 0.10 | Random decisions |
| **Heuristic** | 0.45 | 0.30 | 0.15 | Keyword matching in descriptions |
| **LLM (Few-shot)** | 0.65 | 0.45 | 0.30 | Chain-of-thought prompting |
| **LLM (Optimized)** | 0.75+ | 0.60+ | 0.50+ | Category expertise + fraud patterns + state memory |

### Competitive Scores (OpenEnv Hackathon Targets)

- **Easy**: Goal ≥ 0.70 (High accuracy on simple claims)
- **Medium**: Goal ≥ 0.60 AND fraud_detection ≥ 0.70 (Catches most fraud)
- **Hard**: Goal ≥ 0.75 AND fraud_detection ≥ 0.85 AND gst_accuracy ≥ 0.80 (Expert level)

## 🏗️ OpenEnv Formal Specification

See [openenv.yaml](openenv.yaml) for complete formal specification including:
- Environment metadata (name, version, author)
- Action interface with all 8 actions
- Observation schema  
- Reward structure
- API deployment configuration
- HF Spaces configuration

---

## 🚢 Deployment

### Docker Build & Run (Local Testing)

```bash
# Build image
docker build -t corpexpenseaudit:latest .

# Run container (local mode)
docker run -p 7860:7860 corpexpenseaudit:latest

# Run container with API override
docker run -e ENVIRONMENT_BASE_URL="http://api:7860" -p 7860:7860 corpexpenseaudit:latest
```

### Hugging Face Spaces Deployment

**Note:** HF Spaces with Docker runtime requires paid tier. Alternative: Use HF Spaces with Python runtime (no Docker fee).

1. Create Space on huggingface.co/spaces (Docker runtime)
2. Configure secrets:
   - `OPENAI_API_KEY` (or other LLM API key)
   - `API_BASE_URL`
   - `MODEL_NAME`
   - `ENVIRONMENT_BASE_URL` (optional, for remote API mode)
3. Push files to Space
4. HF will auto-build and deploy

Test endpoint:
```bash
curl https://YOUR_USERNAME-corpexpenseaudit.hf.space/health
# Expected: {"status": "healthy", "service": "CorpExpenseAudit", "version": "1.0.0"}
```

---

## 🔍 Troubleshooting

### ImportError: No module named 'openai'

```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Verify installation
python -c "from openai import OpenAI; print('✓ OpenAI installed')"
```

### API Connection Timeout

```bash
# Test API connectivity
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"

# For Groq:
curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"
```

### JSON Parsing Error in inference.py

- Model returned invalid JSON
- Try: `MODEL_NAME=gpt-3.5-turbo` (simpler model)
- Or: Reduce `MAX_TOKENS` setting
- Or: Switch to Groq (more reliable JSON)

### `'pending_claims' KeyError` in Remote Mode

- Docker API not returning Observation format properly
- Check: `docker logs <container_id>` for stack trace
- Restart container: `docker restart <container_id>`

### Docker Build Fails

```bash
# Clear Docker cache and rebuild
docker system prune -a
docker build --no-cache -t corpexpenseaudit:latest .
```

---

## 📚 Understanding the Reward System

### Dense Rewards (Per Action)

Each action has immediate reward:
```
+0.15 = Correct categorization (tight grading)
-0.08 = Wrong categorization (teaches constraint)
+0.20 = GST compliance verified
+0.25 = Valid claim approved (main goal)
-0.40 = Fraudulent claim approved (CRITICAL FAILURE)
+0.30 = Fraud correctly detected (high value)
-0.25 = False positive fraud (hurts employees)
-0.20 = Valid claim rejected (opportunity cost)
```

### Why These Values?

| Reward | Reason |
|--------|--------|
| -0.40 for fraud approval | Most costly error; direct company loss |
| +0.30 for fraud detection | High business value |
| +0.25 for valid approval | Core task; business enablement |
| -0.20 for valid rejection | Intermediary cost; opportunity loss |
| -0.08 for misclassification | Guides learning without harsh penalty |

---

## ✅ Running Full Validation

```bash
# 1. Test environment
python -c "
from environment import CorpExpenseAudit
env = CorpExpenseAudit('easy')
state = env.reset()
print(f'✓ Environment initialized: {state[\"total_claims\"]} claims')
"

# 2. Test graders
python -c "
from graders import run_easy_grader
from environment import CorpExpenseAudit
env = CorpExpenseAudit('easy')
env.reset()
# Run one step
action = {'action_type': 'export_final_report', 'action_data': {}}
env.step(action)
metrics = run_easy_grader(env)
print(f'✓ Grader works: Score = {metrics.final_score:.2f}')
"

# 3. Test YAML
python -c "
import yaml
with open('openenv.yaml') as f:
    spec = yaml.safe_load(f)
    print(f'✓ YAML valid: {spec[\"name\"]} v{spec[\"version\"]}')
"

# 4. Run full inference
python inference.py
```

---

## 📖 For Research & Benchmarking

### Citation

If you use CorpExpenseAudit in research, please cite:

```bibtex
@software{corpexpenseaudit2024,
  title={CorpExpenseAudit: Enterprise Expense Claim Auditing OpenEnv},
  author={Pooja},
  year={2024},
  url={https://github.com/Pooja52755/Corpexpenseaudit},
  note={OpenEnv Environment for Expense Audit RL}
}
```

### Benchmark Results

To compare agents, report:
- Task (easy/medium/hard)
- Model used (gpt-4o, mixtral, llama2, etc.)
- Final score
- Fraud detection rate
- GST accuracy
- Steps used

Example benchmark JSON:
```json
{
  "agent": "gpt-4o-mini",
  "task": "hard",
  "score": 0.68,
  "metrics": {
    "categorization_accuracy": 0.85,
    "fraud_detection_rate": 0.78,
    "gst_accuracy": 0.92,
    "approval_accuracy": 0.81
  },
  "steps_used": 67,
  "max_steps": 80
}
```

---

## 🤝 Contributing

contributions welcome! Areas:
- New fraud patterns for Hard task
- Additional expense categories
- Alternative LLM providers
- Performance optimizations
- Documentation improvements

---

## 📄 License

MIT License - See LICENSE file for details

---

## ✉️ Feedback & Issues

For bugs, feature requests, or questions:
- Open an issue on GitHub
- Contact: support@corpexpenseaudit.com

---

**Happy Auditing! 🎉**
