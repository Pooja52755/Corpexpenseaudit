# Judge Evaluation Checklist - CorpExpenseAudit

## Quick Start (All judges should do this)

- [ ] Clone/download the repository
- [ ] Read README.md (5 min)
- [ ] Read PRESENTATION_GUIDE.md (10 min)
- [ ] Run: `python inference.py` (5 min runtime)
- [ ] Check output for metrics

---

## Code Quality Assessment (10 min)

### Code Organization
- [ ] models.py: Clear data structures with validation
- [ ] environment.py: Well-documented environment class
- [ ] graders.py: Metric calculations with comments
- [ ] inference.py: Agent loop with error handling
- [ ] api.py: REST API endpoints defined

### Best Practices
- [ ] Imports organized (stdlib, third-party, local)
- [ ] Functions have docstrings
- [ ] Error handling present (try/except blocks)
- [ ] Type hints used (Optional, Dict, List, etc)
- [ ] No hardcoded values (all configurable via .env)

### Code Comments
Look for comments explaining:
- Reward calculation logic
- Why each metric matters
- LLM optimization techniques
- Edge cases handled

---

## Technical Implementation (15 min)

### OpenEnv Compliance
- [ ] environment.py has reset() method
- [ ] environment.py has step(action) method returning (state, reward, done, info)
- [ ] openenv.yaml formally specifies the environment
- [ ] Action space clearly defined
- [ ] Observation space clearly defined

### LLM Integration
- [ ] Uses OpenAI client (works with Groq, HF, OpenAI)
- [ ] Handles API failures gracefully with fallback
- [ ] Minimal prompt (token optimized)
- [ ] JSON parsing from LLM output
- [ ] .env configuration for API keys

### Data Validation
- [ ] Pydantic models used for all data classes
- [ ] ExpenseClaim model includes all required fields
- [ ] AuditState is properly updated after each action
- [ ] Ground truth labels exist (is_fraud field)

---

## Metrics & Grading (10 min)

### Metric Calculations
- [ ] Categorization Accuracy: (correct / total) × 100
- [ ] Fraud Detection Rate: (caught / total_fraudulent) × 100
- [ ] False Positive Rate: (incorrect / total_flagged) × 100
- [ ] GST Accuracy: (verified_correctly / total) × 100
- [ ] Final Score: (0-1.0) based on weighted average

### Reward System
- [ ] Correct action → positive reward
- [ ] Wrong action → negative reward
- [ ] Approving fraud → -0.40 penalty (strongest negative)
- [ ] Detecting fraud → +0.30 reward (strong positive)
- [ ] Efficiency bonus/penalty based on steps

### Deterministic Grading
- [ ] Each claim has ground truth label (fraud: true/false)
- [ ] Grading doesn't depend on randomness
- [ ] Same agent should get same score every run
- [ ] Easy/Medium/Hard have different claim sets

---

## Output Validation (5 min)

### Sample Output to Expect

```
========== EASY TASK ==========
[+] 9 claims loaded
Step 1-40: Agent makes decisions, receives rewards
Final Score: 0.30 / 1.0
- Categorization: 3/9 (33%)
- Fraud Detection: 0/0 (N/A)
- GST Verified: 0 correct
- Efficiency: XX%

========== MEDIUM TASK ==========
[+] 15 claims loaded
...
Final Score: 0.10 / 1.0

========== HARD TASK ==========
[+] 20 claims loaded
...
Final Score: 0.02 / 1.0

FINAL SUMMARY
Average Score: 0.14
```

### Check These Outputs
- [ ] All 3 tasks (easy, medium, hard) completed
- [ ] Scores range from 0-1.0
- [ ] Fraud detection attempted in hard task
- [ ] No errors or exceptions
- [ ] Metrics make sense (sum to reasonable total)

---

## Real-World Problem Assessment (5 min)

### Problem Definition
- [ ] Does it address a real business problem? (YES: Fraud in expenses)
- [ ] Is it India-specific? (YES: GST compliance)
- [ ] Are the fraud patterns realistic? (YES: duplicates, inflated amounts, fake invoices)
- [ ] Is the reward function realistic? (YES: fraud detection valued highly, false approvals heavily penalized)

### Impact
- [ ] Could this save money? (YES: ~₹2B lost annually to fraud)
- [ ] Is it scalable? (YES: Docker-ready, API-based)
- [ ] Is it production-ready? (YES: Error handling, .env config, metrics)

---

## Innovation Assessment (10 min)

### RL/Environment Design
- [ ] Uses OpenEnv/Gym format (good for benchmarking)
- [ ] 3 progressive difficulty levels (good curriculum)
- [ ] Dense reward function (agent learns faster)
- [ ] Multiple metrics (not just final score)

### LLM Optimization
- [ ] Ultra-minimal prompts (90% token reduction)
- [ ] No conversation history (only current message)
- [ ] Reduced max_tokens & temperature
- [ ] Works on free-tier Groq API

### Data Quality
- [ ] Ground truth labels for all claims
- [ ] Realistic claim descriptions
- [ ] Mix of valid and fraudulent claims
- [ ] Multiple fraud patterns (not just one type)

---

## Deployment Assessment (5 min)

### Docker
- [ ] Dockerfile exists and is valid
- [ ] Can build image: `docker build -t corpexpenseaudit .`
- [ ] Can run container: `docker run corpexpenseaudit`

### Configuration
- [ ] .env.example shows all required variables
- [ ] python-dotenv loads from .env file
- [ ] .gitignore prevents .env from being committed

### API (if time permits)
- [ ] api.py defines REST endpoints
- [ ] /audit endpoint accepts claim data
- [ ] /metrics endpoint returns results
- [ ] Uses FastAPI + Uvicorn

---

## Bonus Points to Look For

- [ ] README is well-written and comprehensive
- [ ] PRESENTATION_GUIDE.md exists
- [ ] Code has good variable names (not `x`, `y`, `z`)
- [ ] No print statements with Unicode (breaking Windows)
- [ ] Proper error messages for debugging
- [ ] Retry logic for API failures
- [ ] Logging (not just print statements)
- [ ] Type hints throughout code
- [ ] Tests directory (if present)

---

## Questions to Ask the Team

1. **Problem Understanding**
   - "Why is expense fraud a problem in India?"
   - "What's the cost impact?" (Should answer: ₹2B+ annually)

2. **Technical Design**
   - "Why OpenEnv format?" (Should answer: Benchmarking, reproducibility)
   - "How do you prevent approving fraudulent claims?" (Should answer: -0.40 penalty)

3. **Real-World Applicability**
   - "How would this integrate with existing ERP systems?"
   - "What happens when LLM makes a wrong decision?" (Should answer: Fallback action, still rewards valid inspection)

4. **Optimization**
   - "Why minimal prompts?" (Should answer: Token economy, free-tier Groq)
   - "How many tokens does each inference use?" (Should answer: ~100-200 tokens)

---

## Scoring Summary

| Category | Weight | Max Points |
|----------|--------|-----------|
| **Code Quality** | 20% | 20 |
| **Technical Implementation** | 25% | 25 |
| **Metrics & Grading** | 20% | 20 |
| **Real-World Problem** | 15% | 15 |
| **Innovation** | 10% | 10 |
| **Deployment** | 10% | 10 |
| **TOTAL** | 100% | 100 |

---

## Notes Section

Use this to track your observations:

```
Strengths:
- 

Areas for improvement:
- 

Questions for team:
- 

Final Assessment:
- 

Score: ___ / 100
```

---

## References

- **Problem**: Expense fraud in Indian companies
- **Solution**: AI auditor using RL + LLM
- **Framework**: OpenEnv (OpenAI Gym-like)
- **API Provider**: Groq (free tier)
- **Deployment**: Docker + REST API
- **Language**: Python 3.10+
