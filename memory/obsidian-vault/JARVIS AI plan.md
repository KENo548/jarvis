**JARVIS AI Command Center**

**Minimum Working System — Build Specification v4.0 (Lean + Complete)**

GitHub: [https://github.com/KENo548/AGENCY-OP.B-](https://github.com/KENo548/AGENCY-OP.B-) | Branch: main

---

**🧠 HOW TO USE THIS**

Paste this into a new session and say:

**“Read this fully. You are my JARVIS build assistant. Continue from CURRENT BUILD STATE and guide me step-by-step.”**

---

**🔴 CURRENT BUILD STATE**

- Phase: **Phase 1–2 (Local Build)**
- Focus: **Control Layer + WF-01**
- Next Step: **Spin up local environment (Docker)**

👉 Ignore Phase 3 until Phase 1 works end-to-end.

---

**1.** **🎯 PURPOSE**

JARVIS is a personal AI command system that:

- Understands natural language
- Routes tasks to specialist agents (150+)
- Executes via workflows
- Logs all actions
- Improves using performance data

👉 Not a chatbot.  
👉 A controlled execution system.

---

**2.** **🏗️ CORE ARCHITECTURE**

|**Layer**|**Tool**|**Role**|
|---|---|---|
|Interface|Open WebUI (local)|Command center|
|Brain|Gemini 3.1 Pro|Intent → JSON|
|Control Layer|Supabase Edge Function|Validation + rules|
|Execution|n8n (local Docker)|Workflows|
|Memory|Supabase|Logs + data|

---

**3.** **🔁 CORE EXECUTION FLOW (NON-NEGOTIABLE)**

User Input (Open WebUI)  
    ↓  
Gemini → structured JSON  
    ↓  
Control Layer (Supabase)  
    - Validate JSON  
    - Check confidence  
    - Check idempotency  
    - Enforce rules  
    ↓  
n8n Webhook  
    ↓  
Workflow Execution  
    ↓  
Supabase (task_log)

---

**4.** **⚖️ NON-NEGOTIABLE RULES**

1. No execution without Control Layer
2. Every action must be logged
3. No silent failures
4. Idempotency required (no duplicates)
5. Bulk actions (>3) require confirmation
6. Event-driven only (no always-on agents)

---

**5.** **📦 JSON CONTRACT (SYSTEM BACKBONE)**

{  
  "request_id": "uuid",  
  "intent": "string",  
  "agents": ["string"],  
  "action_type": "string",  
  "execution_required": true,  
  "confidence": 0.0,  
  "bulk": false,  
  "parameters": {}  
}

---

**6.** **🛡️ CONTROL LAYER (EDGE FUNCTION)**

**Location:** Supabase Edge Function  
**Role:** Global gatekeeper BEFORE n8n

**Validation Order:**

1. JSON valid? → retry once with fix prompt
2. Required fields present? → block
3. Confidence ≥ 0.75? → else stop
4. Duplicate request_id? → skip
5. Bulk? → require confirmation

✅ If all pass → send to n8n webhook  
❌ Else → block + log + notify

---

**7.** **🗄️ MINIMUM DATABASE SETUP**

Only create these initially:

**task_log**

- request_id
- status
- error
- timestamp

**system_rules**

- max_daily_actions
- confidence_threshold

👉 Add analytics tables later (Phase 2+)

---

**8.** **⚙️ N8N DESIGN (SIMPLE + CONTROLLED)**

Start with ONE workflow:

**WF-01:**

- Trigger: Webhook
- Action: simple task (e.g., generate content text)
- End: write to task_log

**Rules:**

- Always log result
- Always include error handler
- No complex chaining yet

---

**9.** **🧠 GEMINI SYSTEM BEHAVIOR**

- Returns JSON when execution is needed
- Asks for clarification if confidence < 0.75
- Flags bulk actions
- Routes to correct agents

👉 Do NOT rely on it for enforcement → Control Layer handles that

---

**10.** **🧪 MINIMUM SUCCESS CRITERIA**

System is “working” ONLY if:

- 5 different commands → valid JSON
- All pass Control Layer
- All trigger n8n
- All create Supabase entries
- Duplicate request is blocked
- Bulk request is flagged

👉 If this works → you have a real system

---

**11.** **🚀 BUILD CHECKLIST (DO IN ORDER)**

**Phase 0 — Setup**

- Create Supabase project
- Create task_log + system_rules
- Get Gemini API key

**Phase 1 — Local Stack**

- Install Docker
- Run Open WebUI locally
- Run n8n locally
- Connect Gemini API

**Phase 2 — Control Layer**

- Create Edge Function
- Implement validation logic
- Test retry + blocking

**Phase 2 — First Workflow**

- Create WF-01 in n8n
- Connect webhook
- Run full pipeline test

---

**12.** **🔮 PHASE 2+ (ONLY AFTER SUCCESS)**

Add ONLY after Phase 1 works:

- Distribution workflows (posting)
- Analytics tables
- Feedback loop (6h / 24h / 72h)
- Precomputed insights
- Multi-workflow system

---

**13.** **🌐 PHASE 3 (PRODUCTION)**

- Move to VPS / cloud hosting
- Add API gateway
- Replace full context with RAG
- Build dashboard

---

**🧠 FINAL RULE**

**A working system > a perfect design**

---

**:::**

# JARVIS AI Command Center
**Minimum Working System — Build Specification v3.0 (Updated & Aligned)**

*GitHub: https://github.com/KENo548/AGENCY-OP.B- | Branch: main | v3.0*

## How To Use This Document
Paste this entire document into a new Claude 3.5 Sonnet (or Gemini) session. Then say exactly:

> **Resume Phrase — Copy This Exactly**
> "Read this document fully. You are my JARVIS build assistant. We are building the Minimum Working System defined in Section 3. Walk me through the next unchecked step in the build checklist."

The AI will immediately know your full architecture, build status, and exact next action.

---

## CURRENT BUILD STATE
**Phase:** Phase 1 & 2 (Local Development Pipeline)
**Focus:** Control Layer + WF-01
**Next Step:** Environment Setup (Local Docker n8n + Open WebUI)

*Ignore Phase 3 (VPS Hosting, Analytics, Distribution) until Phase 1 and 2 are 100% complete and working locally.*

---

## 1. Purpose
JARVIS is a personal AI command center that:
*   Understands user intent from natural language.
*   Routes tasks to the correct specialist agent from a 150+ agent directory.
*   Executes real-world actions via automation workflows.
*   Logs every action and learns from results over time.

It is an orchestrated system with a brain, hands, memory, and a feedback loop. **It only becomes a money-making JARVIS once execution, iteration, and distribution workflows are validated.**

---

## 2. System Architecture & The Phased Reality Check
*Rule: Self-hosting everything is for development (Phase 1-2). A JARVIS tied to a laptop dies when it closes. Production requires independent 24/7 hosting.*

| Layer | Tool | Purpose |
| :--- | :--- | :--- |
| **Interface** | Open WebUI / LibreChat | Chat window command center. **(Phase 1: Local Docker to avoid sleep limits on Hugging Face)** |
| **Brain** | Gemini 3.1 Pro API | Understands intent, returns structured JSON. **(Must use Context Caching to prevent massive latency from loading 150 agents. Long-term: RAG needed)**. |
| **Control Layer** | Supabase Edge Function | Validates JSON, enforces rules, checks idempotency — blocks unsafe actions BEFORE hitting n8n. |
| **Execution** | n8n | Runs event-driven commands. **(Phase 1: Local Docker for unlimited free executions. N8n Cloud pricing destroys free scale).** |
| **State / Memory** | Supabase (Postgres) | Logs every action to `task_log`, tracks analytics. |
| **Feedback Loop** | n8n scheduled trigger | Pulls analytics at 6h/24h/72h to form insights. |

### Core Flow (Non-Negotiable)
1. User types command in Open WebUI.
2. Gemini 3.1 Pro processes intent → returns structured JSON.
3. Control Layer validates JSON (structure + confidence + limits + idempotency). *(Blocked here if invalid — retry/notify).*
4. n8n workflow triggered via webhook.
5. Workflow executes real-world action.
6. Result written back to Supabase `task_log`.

---

## 3. Non-Negotiable System Rules
*(Enforced by Control Layer, cannot be overridden by conversational AI).*
1. **Structured JSON:** Gemini must return valid JSON. Control Layer enforces schema.
2. **No Execution Without Control:** n8n never fires directly from Gemini.
3. **Every Action Logged:** Every execution writes a row to `task_log` (success or fail).
4. **No Silent Failures:** Log error, notify user, stop.
5. **Idempotency:** Control layer drops duplicate `request_id` inputs.
6. **Bulk Action Limit:** Actions >3 items require user confirmation.

---

## 4. The JSON Contract
Every response to execution tasks MUST conform to this:
```json
{
  "request_id": "uuid-generated-at-input",
  "intent": "create_instagram_reels",
  "agents": ["@agency-carousel-growth-engine"],
  "action_type": "content_creation",
  "execution_required": true,
  "confidence": 0.91,
  "bulk": false,
  "parameters": {
    "count": 5,
    "topic": "AI tools"
  }
}
```

---

## 5. Control Layer — Full Specification (Supabase Edge Function)
It is NOT inside n8n. It sits before n8n to act as the global rule enforcer.
*   **If valid JSON:** HTTP POST to n8n webhook.
*   **If invalid (First string):** Send self-healing retry prompt back to Gemini.
*   **If invalid (Second try):** Block, log error, notify user.

---

## 6. Build Checklist — Minimum Working System
Do not skip ahead.

### Phase 0 — Foundations
- [ ] Create Supabase project (free tier).
- [ ] Create `task_log` table (id, request_id, agent_used, status, error, timestamp).
- [ ] Create `system_rules` table (limits, thresholds).
- [ ] Get Gemini 3.1 Pro API key from Google AI Studio.

### Phase 1 — Local Environment (The Fix)
- [ ] Install Docker on local machine.
- [ ] Spin up Open WebUI locally via Docker.
- [ ] Spin up n8n locally via Docker.
- [ ] Connect Gemini API key in Open WebUI.
- [ ] Paste entire Agent Directory into System Prompt (ensure Context Caching is active if possible).

### Phase 2 — The Control Layer Pipeline
- [ ] Create Supabase Edge Function: `jarvis-control-layer`.
- [ ] Implement validation checklist (JSON, Confidence >0.75, Idempotency).
- [ ] Test JSON fallback retry loop.

### Phase 3+ — Reliability (Future Roadmap)
- [ ] Implement Distribution Workflows (Posting to IG/YT).
- [ ] Migrate local Docker instances to Cloud VPS or robust serverless environments to allow laptop-free execution.
- [ ] Migrate full-context loading to RAG/Vector selective loading.
