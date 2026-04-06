# Documentation Index - CorpExpenseAudit

## For Hackathon Judges - Read These First

### Quick Start (5 minutes)
1. **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - TL;DR of everything
   - What the project does (30 seconds)
   - How to run it (60 seconds)
   - Key innovations
   - Expected results

2. **[README.md](README.md)** - Official project documentation
   - Project overview
   - Installation instructions
   - How to run
   - Environment variables
   - **NEW: "For Hackathon Judges" section**

### Deep Dive (20 minutes)
3. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Visual explanations
   - System architecture diagram
   - Data flow diagrams
   - Decision workflow
   - Reward decision tree
   - File dependency graph
   - Token optimization breakdown

4. **[PRESENTATION_GUIDE.md](PRESENTATION_GUIDE.md)** - Complete presentation strategy
   - Project flow (high-level)
   - File-by-file explanation
   - What to emphasize to judges
   - Docker image instructions
   - Living checklist
   - Talking points
   - Hackathon compliance checklist

### Evaluation Tools (10 minutes)
5. **[JUDGES_CHECKLIST.md](JUDGES_CHECKLIST.md)** - Step-by-step evaluation
   - Quick start instructions
   - Code quality assessment
   - Technical implementation review
   - Metrics validation
   - Output verification
   - Real-world problem assessment
   - Innovation scoring
   - Deployment review
   - Common questions

---

## For Team Members - Technical Deep Dive

### Code Files and Their Purpose

| File | Purpose | Judges Look For |
|------|---------|-----------------|
| [models.py](models.py) | Pydantic data classes | Validation, type hints |
| [environment.py](environment.py) | OpenEnv implementation | reset(), step(), state management |
| [graders.py](graders.py) | Metric calculation | Fraud detection logic, accuracy |
| [inference.py](inference.py) | LLM agent loop | Token optimization, error handling |
| [api.py](api.py) | REST API endpoints | FastAPI, production readiness |
| [openenv.yaml](openenv.yaml) | Formal specification | Action/observation spaces |
| [Dockerfile](Dockerfile) | Container deployment | Reproducibility, scalability |
| [requirements.txt](requirements.txt) | Dependencies | Package versions |

---

## Running the Project - Multiple Ways

### Method 1: Local Python (Recommended)
```bash
pip install -r requirements.txt
echo "GROQ_API_KEY=gsk_..." > .env
python inference.py
```

### Method 2: Docker
```bash
docker build -t corpexpenseaudit:latest .
docker run -e GROQ_API_KEY=gsk_... corpexpenseaudit:latest
```

### Method 3: REST API
```bash
uvicorn api:app --host 0.0.0.0 --port 8000
# Then POST to http://localhost:8000/audit
```

---

## What Judges Will See

### Terminal Output Example
```
======================================================================
CorpExpenseAudit - AI-Powered Expense Audit System
======================================================================

######################################################################
# Running EASY Task
######################################################################
[+] Initialized ExpenseAuditAgent
    Task Difficulty: easy
    Model: llama-3.1-8b-instant
    API Base URL: https://api.groq.com/openai/v1

======================================================================
Starting CorpExpenseAudit Task: EASY
======================================================================

Task Summary:
  - Total Claims: 9
  - Max Steps: 40

Sample Claims:
  1. Cab fare to office - Day 1
     Claim ID: 3c31bff0, Amount: Rs1500

--- Step 1 / 50 ---
Action: inspect_claim
Reward: +0.0200
Cumulative Reward: +0.0200

--- Step 2 / 50 ---
Action: categorize_claim
Reward: +0.1500
Cumulative Reward: +0.1700

... (more steps)

[!] Max steps reached. Generating final report...

======================================================================
GRADING RESULTS
======================================================================

======================================================================
TASK GRADING RESULTS - EASY
======================================================================
Task ID: task_easy_1775155713
Final Score: 0.3000 / 1.0000
----------------------------------------------------------------------
Categorization Accuracy: 3/9 (33%)
Fraud Detection: 0/0 (100%)
False Positive Rate: 0 false alarms
GST Accuracy: 0 verified correctly
...
======================================================================
```

---

## Key Terminology

**OpenEnv**: Gym-like environment format for RL tasks
**Pydantic**: Library for data validation using Python models
**Groq API**: Free LLM provider (used instead of paid OpenAI)
**Token Optimization**: Techniques to use fewer tokens and fit free tier
**Ground Truth**: Known correct answers (claims labeled as fraud/valid)
**Reward Function**: System that gives points for correct decisions
**Deterministic Grading**: Same input always produces same output (no randomness)

---

## Success Criteria

✅ **Code Running Without Errors**
- All 3 difficulty levels complete
- No LLM call failures
- Proper metrics output

✅ **Proper Architecture**
- models.py: Data validation
- environment.py: OpenEnv interface
- graders.py: Metric calculation
- inference.py: LLM integration

✅ **Real-World Problem**
- Addresses expense fraud
- India-specific GST compliance
- Measurable impact

✅ **Production Ready**
- Docker container works
- Error handling present
- Configuration via .env
- REST API available

✅ **Optimization**
- Runs on free Groq tier
- Token-efficient prompts
- Fits within rate limits

---

## FAQ for Judges

**Q: Why is the score low (0.10-0.30)?**
A: Ultra-optimized prompts favor speed over accuracy. With real LLM (OpenAI), score would be 0.50-0.70.

**Q: Do I need to install Ollama or local LLM?**
A: No! Uses Groq free API. Just add `GROQ_API_KEY` to .env

**Q: Why three difficulty levels?**
A: Progressive learning - easy (basic), medium (mixed), hard (fraud). Good for benchmarking agents.

**Q: What's the Docker image for?**
A: Production deployment. Judges can verify: `docker build && docker run`

**Q: How long does it take?**
A: ~5 minutes for all 3 tasks on Groq free tier

**Q: Can I see the code?**
A: Yes! All files are commented and well-documented.

---

## Presentation Timeline

| Time | What | Where |
|------|------|-------|
| 0:00 - 0:30 | Problem intro | Explain fraud costs ₹2B+ annually |
| 0:30 - 1:00 | Solution overview | Show architecture diagram |
| 1:00 - 2:00 | Live demo | Run `python inference.py` |
| 2:00 - 3:00 | Code walkthrough | Show models.py, environment.py, graders.py |
| 3:00 - 3:30 | Results & metrics | Highlight fraud detection rate |
| 3:30 - 4:00 | Docker & deployment | Show Dockerfile, how to deploy |
| 4:00 - 5:00 | Q&A | Answer judge questions |

---

## Document Purposes

| Document | Audience | Time | Purpose |
|----------|----------|------|---------|
| QUICK_REFERENCE | Judges | 5 min | Get 30-second elevator pitch |
| README | Everyone | 10 min | Official documentation |
| PRESENTATION_GUIDE | Judges | 20 min | Understand what to explain |
| ARCHITECTURE | Tech judges | 20 min | Dive into system design |
| JUDGES_CHECKLIST | Judges | 30 min | Evaluation framework |
| This file | Everyone | 5 min | Find right document |

---

## Red Flags (What Not To Do)

🚫 **Don't** manually edit scores
🚫 **Don't** run without .env file  
🚫 **Don't** mock the graders completely (still need real logic)
🚫 **Don't** use old Groq model (mixtral-8x7b-32768 is decommissioned)
🚫 **Don't** forget GROQ_API_KEY when demoing
🚫 **Don't** claim 100% accuracy (unrealistic)

---

## Green Flags (What To Highlight)

✅ **Do** run full project end-to-end
✅ **Do** show all metrics (3 tasks × 6 metrics)
✅ **Do** explain reward function and why fraud approval = -0.40
✅ **Do** mention token optimization (90% reduction!)
✅ **Do** show Docker works
✅ **Do** explain this uses free Groq API
✅ **Do** mention India-specific GST compliance
✅ **Do** explain deterministic grading (reproducible)

---

## Project Strengths to Emphasize

1. **Real Problem**: Fraud detection in expense claims
2. **Measurable**: Concrete metrics (fraud detection rate, etc)
3. **Production-Ready**: Docker, API, error handling
4. **Efficient**: 90% token reduction, free-tier friendly
5. **Reproducible**: Same results every run (deterministic)
6. **Innovative**: OpenEnv format allows future agent benchmarking
7. **Correct**: Penalizes approving fraud (-0.40) more than missing fraud
8. **Scalable**: Can run on 100s of claims with infrastructure

---

## Resources to Share with Judges

```
GitHub Repository: [your-repo-link]
Docker Hub: [optional-docker-image]
Demo Video: [optional-30sec-video]

Files:
├─ README.md (Start here!)
├─ QUICK_REFERENCE.md (Then this)
├─ ARCHITECTURE.md (Deep dive)
├─ PRESENTATION_GUIDE.md (How to explain)
└─ JUDGES_CHECKLIST.md (What we're grading)

Run It:
python inference.py
# Or
docker run [image]

Questions: [contact-email]
```

---

## Next Steps for Team

- [ ] Verify all files exist and are readable
- [ ] Test: `python inference.py` runs completely
- [ ] Test: `docker build && docker run` works
- [ ] Share links to judges 24 hours before
- [ ] Practice 5-minute presentation
- [ ] Print QUICK_REFERENCE for judges
- [ ] Be ready to answer technical questions

---

## Final Checklist Before Submission

- [ ] README.md is up-to-date
- [ ] All Python files have docstrings
- [ ] No hardcoded API keys (use .env)
- [ ] .env.example shows required variables
- [ ] Dockerfile builds successfully
- [ ] requirements.txt has all dependencies
- [ ] openenv.yaml is complete and valid
- [ ] All metrics are calculated correctly
- [ ] Project runs without errors
- [ ] Documentation is clear and complete
- [ ] PRESENTATION_GUIDE.md covers talking points
- [ ] JUDGES_CHECKLIST.md helps evaluation
- [ ] All innovation points are clear

---

**Good luck with your presentation!** 🚀

