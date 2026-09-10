"""
TechQueue Interview Coach — Dev Mode Server (Ollama Edition)
=============================================================
100% offline. Uses Ollama (already running on :11434) as the LLM.
No API keys, no external network, no ADK, no packages needed.

Usage:
    python dev_server.py
    Open http://localhost:8181
"""

import http.server
import io
import json
import os
import re
import sys
import urllib.request
import urllib.error
from typing import Any

# ── Windows Console UTF-8 Safety ───────────────────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Auto-load .env ─────────────────────────────────────────────────────────────
def _load_env_file():
    candidates = [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.dirname(__file__), "..", ".env"),
        ".env",
    ]
    for c in candidates:
        if os.path.isfile(c):
            try:
                with open(c, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("\"'")
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

_load_env_file()

# ── Config ─────────────────────────────────────────────────────────────────────
OLLAMA_URL   = os.environ.get("OLLAMA_URL",   "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "granite3-moe:3b")
PORT         = int(os.environ.get("PORT", "8181"))

# ── Offline Knowledge Base Loader & Local RAG ──────────────────────────────────
KB_DOCS: dict[str, str] = {}

def _init_knowledge_base():
    kb_path = os.path.join(os.path.dirname(__file__), "knowledge_base")
    if os.path.isdir(kb_path):
        for f in os.listdir(kb_path):
            if f.endswith(".txt") or f.endswith(".md"):
                try:
                    with open(os.path.join(kb_path, f), "r", encoding="utf-8", errors="ignore") as fp:
                        KB_DOCS[f] = fp.read()
                except Exception:
                    pass

_init_knowledge_base()

def _search_knowledge_base(query: str, max_chars: int = 1500) -> str:
    """Retrieve the most relevant section from the local knowledge base files."""
    if not KB_DOCS:
        return ""
    q_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", query.lower()))
    # filter generic query words
    stop_words = {"give", "show", "tell", "what", "with", "from", "help", "please", "some", "want", "prep"}
    q_words = q_words - stop_words
    if not q_words:
        return ""

    best_score, best_snippet = 0, ""
    for doc_name, content in KB_DOCS.items():
        sections = re.split(r"\n(?=#{1,3}\s)", content)
        for sec in sections:
            sec_lower = sec.lower()
            sec_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", sec_lower))
            overlap = len(q_words & sec_words)
            first_line = sec_lower.split("\n", 1)[0]
            header_overlap = len(q_words & set(re.findall(r"\b[a-zA-Z]{3,}\b", first_line)))
            score = overlap + (header_overlap * 3)
            if score > best_score:
                best_score = score
                best_snippet = sec[:max_chars]

    if best_score >= 2:
        return f"\n\n[KNOWLEDGE BASE CONTEXT]\n{best_snippet.strip()}\n"
    return ""

# ── Tool: build_candidate_profile ─────────────────────────────────────────────
def build_candidate_profile(name, job_role, experience_level, tech_stack=None):
    level = experience_level.lower().strip()
    if level not in ("entry", "mid", "senior"): level = "mid"
    r = job_role.lower()
    focus, qtypes = [], ["behavioral", "hr"]
    if any(k in r for k in ("software", "engineer", "developer", "swe", "backend", "frontend", "fullstack")):
        focus += ["Data Structures & Algorithms", "System Design", "Code Quality"]
        qtypes += ["technical", "system_design"]
    if any(k in r for k in ("data", "scientist", "ml", "machine learning", "ai", "analyst")):
        focus += ["Statistics & ML Theory", "Model Evaluation", "Data Wrangling"]
        qtypes += ["technical", "case_study"]
    if any(k in r for k in ("product", "manager", "pm")):
        focus += ["Product Strategy", "Prioritisation", "Stakeholder Management"]
        qtypes += ["case_study", "situational"]
    if any(k in r for k in ("devops", "cloud", "sre", "platform", "infra")):
        focus += ["CI/CD Pipelines", "Cloud Architecture", "Incident Management"]
        qtypes += ["technical", "system_design"]
    if tech_stack: focus.append(f"Stack: {tech_stack}")
    if not focus: focus = ["Domain Knowledge", "Communication", "Problem Solving"]
    tips = {
        "entry": "Focus on core fundamentals and walk through your academic/project work step-by-step.",
        "mid":   "Prepare STAR-format stories from real projects; be ready to discuss trade-offs.",
        "senior":"Emphasise leadership, system design at scale, and how you drive engineering culture.",
    }
    return {
        "name": name, "job_role": job_role, "experience_level": level,
        "focus_areas": list(dict.fromkeys(focus)),
        "recommended_question_types": list(dict.fromkeys(qtypes)),
        "preparation_tip": tips[level],
    }

# ── Tool: get_question_set ─────────────────────────────────────────────────────
SEED_Q: dict[tuple, list] = {
    ("technical", "entry"): [
        "Explain the difference between a stack and a queue with a real use-case.",
        "What is Big-O notation? Give examples for O(1), O(n), and O(n log n).",
        "How does garbage collection work in Python or Java?",
        "Write a function to reverse a linked list. What is the time complexity?",
        "What is REST? How does it differ from GraphQL?",
    ],
    ("technical", "mid"): [
        "Design a rate limiter for a high-traffic public API.",
        "How would you optimise a slow SQL query running on 50 million rows?",
        "Explain eventual consistency vs. strong consistency with examples.",
        "What are the SOLID principles? Give a concrete code example for each.",
        "How do you handle distributed transactions without a two-phase commit?",
    ],
    ("technical", "senior"): [
        "How would you architect a real-time collaborative document editor?",
        "Describe your approach to database sharding for a 10× traffic increase.",
        "How do you ensure zero-downtime deployments for a mission-critical service?",
        "What trade-offs do you weigh when choosing microservices vs. a monolith?",
        "How do you design for observability in a large distributed system?",
    ],
    ("behavioral", "entry"): [
        "Tell me about a time you faced a challenging technical problem. How did you solve it?",
        "Describe a project you are most proud of and your specific role in its success.",
        "How do you handle constructive feedback from a code review?",
        "Give an example of when you had to learn a new technology quickly.",
        "How do you prioritise tasks when you have multiple competing deadlines?",
    ],
    ("behavioral", "mid"): [
        "Describe a time you disagreed with a technical decision. How did you handle it?",
        "Tell me about a project that failed. What did you learn, and what would you do differently?",
        "How have you mentored junior engineers? What impact did it have?",
        "Give an example of driving a cross-functional initiative end-to-end.",
        "Describe a time you had to balance technical debt against delivering new features.",
    ],
    ("behavioral", "senior"): [
        "Tell me about a time you changed the technical direction of an engineering team.",
        "How have you built engineering culture and quality standards across an organisation?",
        "Describe how you influenced a major architectural decision under time pressure.",
        "How do you handle an underperforming direct report?",
        "Give an example of driving a significant technical change across multiple teams.",
    ],
    ("system_design", "entry"): [
        "Design a URL shortener like bit.ly. What are the key components?",
        "How would you design a simple in-memory key-value store?",
        "Design a basic push notification system for a mobile app.",
        "Walk me through a design for a file upload and storage service.",
        "How would you design a simple real-time chat application?",
    ],
    ("system_design", "mid"): [
        "Design Twitter's trending topics feature at 10M daily active users.",
        "How would you design the backend for a ride-sharing platform like Uber?",
        "Design a distributed job scheduler with at-least-once execution guarantees.",
        "How would you build a scalable e-commerce checkout and payment system?",
        "Design a real-time leaderboard for a multiplayer gaming platform.",
    ],
    ("system_design", "senior"): [
        "Design a global CDN from scratch. How do you handle cache invalidation?",
        "How would you architect a multi-region active-active database system?",
        "Design a machine learning feature store for a Netflix-scale recommendation engine.",
        "How would you build a PCI-compliant payment processing platform?",
        "Design a fault-tolerant event streaming platform comparable to Apache Kafka.",
    ],
    ("case_study", "entry"): [
        "Walk me through how you would frame an A/B test for a new checkout button.",
        "How would you detect and handle missing or corrupted data in a customer dataset?",
        "Explain how you would validate a classification model before deploying it to production.",
        "How would you evaluate whether a recommendation model is genuinely improving user engagement?",
        "Walk me through the metrics you would track for a new mobile onboarding flow.",
    ],
    ("case_study", "mid"): [
        "You notice a 15% drop in conversion rate after a website redesign. How do you diagnose the root cause?",
        "Design an experiment to test a new search ranking algorithm without degrading user experience.",
        "How would you predict customer lifetime value (LTV) when transaction history is sparse?",
        "How would you handle significant class imbalance (e.g., 99.8% negative) in fraud detection?",
        "Explain your approach to feature engineering and model selection for churn prediction.",
    ],
    ("case_study", "senior"): [
        "Design an end-to-end machine learning pipeline for real-time fraud scoring with <50ms latency SLAs.",
        "How do you monitor and remediate concept drift and data distribution shifts in production ML models?",
        "How would you define and optimize the North Star metric and guardrail metrics for a two-sided marketplace?",
        "Architect a continuous model retraining and shadow-deployment pipeline on Kubernetes/Cloud.",
        "How do you prioritize data platform investments between self-serve BI and advanced predictive modeling?",
    ],
    ("situational", "entry"): [
        "A key stakeholder asks for a feature that contradicts the agreed sprint goal. How do you respond?",
        "You discover a critical bug right before release. What steps do you take immediately?",
        "How do you handle a situation where requirements for a task keep changing?",
        "Describe how you prioritize your daily work when multiple urgent requests come in.",
        "How do you communicate a delay in your deliverables to your team lead?",
    ],
    ("situational", "mid"): [
        "Engineering estimates 6 months for a high-priority customer request. How do you negotiate scope vs timeline?",
        "Two senior stakeholders have conflicting priorities for the next quarter. How do you align them?",
        "A feature you championed launched and underperformed expected metrics. What is your post-launch strategy?",
        "How do you resolve a heated technical debate between two engineers on your team?",
        "Describe a time you had to pivot product strategy based on sudden customer churn data.",
    ],
    ("situational", "senior"): [
        "Your flagship product's user growth has plateaued for two consecutive quarters. Outline your 90-day turnaround plan.",
        "How do you decide between building in-house vs buying a third-party SaaS solution for core infrastructure?",
        "How do you sunset a legacy product feature that 5% of enterprise customers still heavily rely on?",
        "Describe how you manage executive expectations when delivering bad news about a major initiative delay.",
        "How do you establish engineering excellence and SLA accountability across distributed global teams?",
    ],
    ("hr", "entry"): [
        "Why do you want to join our company specifically?",
        "Where do you see yourself in 3 years?",
        "What are your greatest strengths and one area you are actively improving?",
        "How do you maintain work-life balance during intense project phases?",
        "Why are you looking to transition from your current role?",
    ],
    ("hr", "mid"): [
        "What motivates you beyond compensation and title?",
        "How do you stay current with new technologies and industry trends?",
        "Describe your ideal team culture and working environment.",
        "How do you align your personal career goals with company objectives?",
        "How would you describe your leadership and collaboration style?",
    ],
    ("hr", "senior"): [
        "How do you build and retain high-performing engineering teams?",
        "What is your philosophy on technical hiring and interview design?",
        "How do you balance innovation and speed against system stability?",
        "How do you align engineering strategy with business goals and OKRs?",
        "What technical or cultural legacy do you want to leave at your next company?",
    ],
}

def get_question_set(job_role, experience_level, question_types, count=5):
    level = experience_level.lower().strip()
    if level not in ("entry", "mid", "senior"): level = "mid"
    diff  = {"entry": "easy", "mid": "medium", "senior": "hard"}.get(level, "medium")
    count = max(1, min(int(count), 10))
    out   = []
    for qt in question_types:
        key  = (qt.lower().replace(" ", "_"), level)
        bank = SEED_Q.get(key, SEED_Q.get((qt.lower().replace(" ", "_"), "mid"), []))
        for q in bank[:count]:
            out.append({"type": qt, "question": q, "difficulty": diff})
    return {"job_role": job_role, "level": level, "total": len(out),
            "questions": out, "est_minutes": len(out) * 4}

# ── Tool: evaluate_answer ──────────────────────────────────────────────────────
def evaluate_answer(question, answer, q_type, level):
    words   = len(answer.split())
    has_ex  = any(k in answer.lower() for k in (
        "for example", "for instance", "i worked", "we built", "such as", "i designed",
        "in my", "when i", "at my", "our team"))
    has_str = any(k in answer.lower() for k in (
        "first", "second", "third", "then", "finally", "additionally", "however", "because",
        "therefore", "situation", "task", "action", "result"))
    deep    = words > 80
    clarity = 4 if has_str else 3
    depth   = 4 if deep    else 2
    examples= 5 if has_ex  else 2
    struct  = 4 if has_str else 2
    overall = round(((clarity + depth + 3 + examples + struct) / 5) * 2)
    grade   = {10: "A", 9: "A", 8: "B", 7: "B", 6: "C", 5: "C", 4: "D", 3: "D"}.get(overall, "F")
    strengths, improvements = [], []
    if has_ex:  strengths.append("Good use of concrete examples to support the answer.")
    else:       improvements.append("Add a specific real example — use the STAR method for behavioral questions.")
    if has_str: strengths.append("Answer has a clear logical structure and flow.")
    else:       improvements.append("Structure your answer with signposts: first/then/finally or Situation→Task→Action→Result.")
    if deep:    strengths.append("Demonstrates solid depth and technical substance.")
    else:       improvements.append(f"Answer is too brief ({words} words). Aim for 100–200 words with specific detail.")
    outlines = {
        "technical":     "1. State the concept. 2. Explain the mechanism/algorithm. 3. Discuss complexity/trade-offs. 4. Give a real use-case.",
        "behavioral":    "STAR: Situation → Task → Action → Result. Quantify the outcome where possible.",
        "system_design": "1. Clarify requirements. 2. Estimate scale. 3. High-level components. 4. Deep-dive critical path. 5. Trade-offs & failure modes.",
        "hr":            "Be authentic, align with company values, and support every claim with a brief story.",
    }
    follow_ups = {
        "technical":     ["What is the time/space complexity?", "How would you scale this to 100× load?", "What edge cases haven't you handled?"],
        "behavioral":    ["What would you do differently today?", "What was the measurable business impact?", "How did that shape how you work now?"],
        "system_design": ["How does it handle a 10× traffic spike?", "What monitoring and alerting would you add?", "How would you migrate from the current system?"],
        "hr":            ["Can you give another example?", "How does that value align with our company mission?", "What does success look like in your first 90 days?"],
    }
    return {
        "question": question, "score": overall, "grade": grade,
        "strengths":  strengths  or ["Good attempt — keep practising!"],
        "improvements": improvements or ["Continue refining depth and delivery."],
        "model_outline": outlines.get(q_type.lower(), outlines["behavioral"]),
        "follow_ups": follow_ups.get(q_type.lower(), follow_ups["behavioral"]),
    }

# ── Ollama LLM call ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are TechQueue, an expert AI Interview Coach powered by IBM Granite and RAG. "
    "You help candidates prepare for job interviews by generating personalised prep plans, "
    "role-specific questions (technical, behavioral, system design, HR), and evaluating "
    "practice answers with detailed constructive feedback. "
    "Be encouraging, specific, and actionable. "
    "When tool output or knowledge base context is provided in the message, use it to structure your response clearly."
)

def call_ollama(messages: list) -> str:
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 1024}
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read())
        return body["message"]["content"]
    except urllib.error.URLError as e:
        return f"⚠️ Cannot reach Ollama at {OLLAMA_URL}. Make sure Ollama is running (`ollama serve`).\nError: {e}"
    except Exception as ex:
        return f"⚠️ LLM error: {ex}"

# ── HTML UI Template ───────────────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TechQueue — AI Interview Coach</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"Segoe UI",system-ui,sans-serif;background:#0f172a;color:#e2e8f0;height:100vh;display:flex;flex-direction:column;overflow:hidden}
header{background:linear-gradient(135deg,#1e40af 0%,#7c3aed 100%);padding:14px 24px;display:flex;align-items:center;gap:14px;box-shadow:0 2px 12px rgba(0,0,0,.5);flex-shrink:0}
.logo{width:40px;height:40px;background:#fff;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.3rem;flex-shrink:0}
.htext h1{font-size:1.25rem;font-weight:700;color:#fff;letter-spacing:-.3px}
.htext p{font-size:.75rem;color:#bfdbfe;margin-top:1px}
.badge{display:inline-block;background:#10b981;color:#fff;font-size:.6rem;padding:2px 7px;border-radius:999px;font-weight:700;margin-left:6px;vertical-align:middle}
.model-tag{display:inline-block;background:rgba(255,255,255,.15);color:#e0e7ff;font-size:.65rem;padding:2px 8px;border-radius:999px;margin-left:6px;vertical-align:middle}
#chat{flex:1;overflow-y:auto;padding:20px 24px;display:flex;flex-direction:column;gap:14px}
.msg{max-width:78%;padding:12px 16px;border-radius:14px;line-height:1.65;font-size:.875rem;white-space:pre-wrap;word-wrap:break-word}
.user{background:#1e40af;color:#dbeafe;align-self:flex-end;border-bottom-right-radius:4px}
.bot{background:#1e293b;color:#e2e8f0;align-self:flex-start;border:1px solid #334155;border-bottom-left-radius:4px}
.bot b{color:#7dd3fc}
.typing{display:flex;align-items:center;gap:8px;padding:10px 16px;background:#1e293b;border:1px solid #334155;border-radius:14px;border-bottom-left-radius:4px;align-self:flex-start;color:#94a3b8;font-size:.82rem}
.dot{width:7px;height:7px;border-radius:50%;background:#6366f1;animation:blink 1.2s ease-in-out infinite}
.dot:nth-child(2){animation-delay:.2s}.dot:nth-child(3){animation-delay:.4s}
@keyframes blink{0%,80%,100%{opacity:.3}40%{opacity:1}}
.chips{display:flex;flex-wrap:wrap;gap:8px;padding:8px 24px;flex-shrink:0}
.chip{background:#1e293b;border:1px solid #475569;color:#94a3b8;padding:7px 14px;border-radius:999px;font-size:.76rem;cursor:pointer;transition:all .15s;user-select:none}
.chip:hover{background:#334155;color:#e2e8f0;border-color:#6366f1}
#form{display:flex;gap:10px;padding:14px 20px;background:#1e293b;border-top:1px solid #334155;flex-shrink:0}
#inp{flex:1;background:#0f172a;border:1px solid #475569;color:#e2e8f0;padding:10px 18px;border-radius:24px;font-size:.875rem;outline:none;resize:none;font-family:inherit}
#inp:focus{border-color:#6366f1}
#send{background:#6366f1;color:#fff;border:none;padding:10px 22px;border-radius:24px;cursor:pointer;font-size:.875rem;font-weight:600;transition:background .15s;flex-shrink:0}
#send:hover{background:#4f46e5}
#send:disabled{background:#475569;cursor:default}
</style>
</head>
<body>
<header>
  <div class="logo">🎯</div>
  <div class="htext">
    <h1>TechQueue<span class="badge">DEV</span><span class="model-tag">__MODEL_TAG__ · Ollama</span></h1>
    <p>AI-Powered Interview Coach · Offline · IBM watsonx Orchestrate Ready</p>
  </div>
</header>
<div id="chat">
  <div class="msg bot"><b>TechQueue</b> — AI Interview Coach

Welcome! I'm here to help you land your dream job. Tell me about yourself and I'll create a personalised prep plan.

Share your:
  • <b>Name</b>
  • <b>Target job role</b> (e.g. Software Engineer, Data Scientist, Product Manager)
  • <b>Experience level</b> (entry / mid / senior)
  • <b>Tech stack</b> (optional)

I'll generate tailored interview questions, evaluate your practice answers, and build you a full preparation strategy.</div>
</div>
<div class="chips">
  <div class="chip" onclick="fill('My name is Alex. I am a mid-level Software Engineer with Python and React. Help me prepare.')">👤 Start Prep (SWE)</div>
  <div class="chip" onclick="fill('Give me 5 system design interview questions for a senior backend engineer.')">🏗️ System Design Qs</div>
  <div class="chip" onclick="fill('Give me 5 behavioral interview questions for an entry-level data scientist.')">🧠 Behavioral Qs</div>
  <div class="chip" onclick="fill('Evaluate my answer. Question: What is the CAP theorem? My answer: The CAP theorem states a distributed system can only guarantee two of three properties at once: Consistency, Availability, and Partition Tolerance. For example, during a network partition you must choose between AP (serve possibly stale data) or CP (reject requests to stay consistent). This is why Cassandra is AP while HBase is CP.')">✅ Evaluate My Answer</div>
  <div class="chip" onclick="fill('I finished 10 practice questions and my average score was 7 out of 10. I am targeting a mid-level Software Engineer role. Give me a readiness report and action plan.')">📊 Readiness Report</div>
</div>
<form id="form" onsubmit="return false">
  <textarea id="inp" rows="1" placeholder="Type your message… (Enter to send, Shift+Enter for new line)"></textarea>
  <button id="send" onclick="send()">Send</button>
</form>
<script>
const chat = document.getElementById('chat');
const inp  = document.getElementById('inp');
const btn  = document.getElementById('send');
let history = [];

function fill(t){ inp.value = t; inp.focus(); inp.style.height='auto'; inp.style.height=inp.scrollHeight+'px'; }

function addMsg(role, text){
  const d = document.createElement('div');
  d.className = 'msg ' + (role==='user'?'user':'bot');
  d.textContent = text;
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
  return d;
}

function addTyping(){
  const d = document.createElement('div');
  d.className = 'typing';
  d.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span><span style="margin-left:4px">TechQueue is thinking…</span>';
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
  return d;
}

async function send(){
  const text = inp.value.trim();
  if(!text || btn.disabled) return;
  inp.value = ''; inp.style.height = 'auto';
  addMsg('user', text);
  history.push({role:'user', content: text});
  const t = addTyping();
  btn.disabled = true;
  try {
    const r = await fetch('/api/chat', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({messages: history})
    });
    const data = await r.json();
    chat.removeChild(t);
    const reply = data.reply || '[No response received]';
    addMsg('bot', reply);
    history.push({role:'assistant', content: reply});
  } catch(e) {
    chat.removeChild(t);
    addMsg('bot', 'Connection error: ' + e.message);
  }
  btn.disabled = false;
  inp.focus();
}

inp.addEventListener('keydown', e => {
  if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); send(); }
});
inp.addEventListener('input', function(){
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 120) + 'px';
});
</script>
</body>
</html>"""

# ── Tool enrichment helpers ─────────────────────────────────────────────────────
def _detect_and_enrich(user_text: str) -> str:
    low = user_text.lower()

    # ── Profile / prep plan ──
    if any(k in low for k in ("my name is", "help me prepare", "i am a", "i'm a", "prep for", "preparing for", "start prep")):
        name_m  = re.search(r"(?:my name is|i am|i'm|name[:\s]+)\s*([a-zA-Z]+)", low)
        level_m = re.search(r"\b(entry|mid|senior|junior|lead|principal|experienced)\b", low)
        role_m  = re.search(
            r"(software engineer|data scientist|data analyst|product manager|devops|sre|"
            r"backend engineer|frontend engineer|fullstack|ml engineer|machine learning engineer|"
            r"cloud engineer|platform engineer|qa engineer)", low)
        stack_m = re.search(
            r"(?:with|using|stack[:\s]+)([a-zA-Z0-9 ,+#.]+?)(?:\.|$|and i)", low)
        name  = name_m.group(1).title() if name_m else "Candidate"
        role  = role_m.group(1).title()  if role_m  else "Software Engineer"
        level = level_m.group(1)         if level_m else "mid"
        if level in ("junior", "lead", "principal"):
            level = "entry" if level == "junior" else "senior"
        if level == "experienced": level = "mid"
        stack = stack_m.group(1).strip() if stack_m else None
        p = build_candidate_profile(name, role, level, stack)
        qs = get_question_set(role, level, p["recommended_question_types"], 3)
        kb_context = _search_knowledge_base(f"{role} interview questions preparation")
        return (
            f"\n\n[PROFILE ANALYSIS]\n{json.dumps(p, indent=2)}"
            f"\n\n[STARTER QUESTION SET — {len(qs['questions'])} questions]\n{json.dumps(qs['questions'], indent=2)}"
            f"{kb_context}"
            f"\n\nUse this data to build a warm, personalised interview prep plan. "
            f"Present focus areas, recommended question categories, the starter questions grouped by type, "
            f"and specific preparation tips tailored to a {level}-level {role}."
        )

    # ── Question set ──
    if (any(k in low for k in ("give me", "list", "generate", "show me", "provide", "need")) and "question" in low) or "practice questions" in low:
        level_m = re.search(r"\b(entry|mid|senior|junior)\b", low)
        role_m  = re.search(
            r"(software engineer|data scientist|data analyst|product manager|devops|sre|"
            r"backend|frontend|fullstack|ml engineer|machine learning|cloud|platform|qa)", low)
        types_m = re.findall(r"(technical|behavioral|system design|system_design|hr|case study|case_study|situational)", low)
        count_m = re.search(r"\b(\d+)\s+question", low)
        level  = (level_m.group(1) if level_m else "mid").replace("junior", "entry")
        role   = role_m.group(1).title() if role_m else "Software Engineer"
        qtypes = [t.replace(" ", "_") for t in types_m] if types_m else ["technical", "behavioral", "hr"]
        count  = int(count_m.group(1)) if count_m else 5
        qs = get_question_set(role, level, qtypes, count)
        kb_context = _search_knowledge_base(f"{role} {' '.join(qtypes)}")
        return (
            f"\n\n[QUESTION SET — {qs['total']} questions for {level} {role}]\n"
            f"{json.dumps(qs['questions'], indent=2)}"
            f"{kb_context}"
            f"\n\nPresent these questions clearly, grouped by type, with the difficulty label. "
            f"Add a brief tip for how to approach each category."
        )

    # ── Answer evaluation ──
    if any(k in low for k in ("evaluate", "score my", "assess my", "my answer", "how did i do", "rate my")):
        q_m = re.search(r"question[:\s—–-]+(.+?)(?:my answer|answer[:\s—–-])", low, re.DOTALL)
        a_m = re.search(r"(?:my answer[:\s—–-]|answer[:\s—–-])(.+)", low, re.DOTALL)
        question = q_m.group(1).strip() if q_m else "Interview question"
        answer   = a_m.group(1).strip() if a_m else user_text
        type_m   = re.search(r"(technical|behavioral|system design|system_design|hr|case study|situational)", low)
        level_m  = re.search(r"\b(entry|mid|senior)\b", low)
        qtype    = (type_m.group(1).replace(" ", "_") if type_m else "technical")
        level    = level_m.group(1) if level_m else "mid"
        ev = evaluate_answer(question, answer, qtype, level)
        kb_context = _search_knowledge_base(f"{question} {qtype} model answer")
        return (
            f"\n\n[ANSWER EVALUATION]\n{json.dumps(ev, indent=2)}"
            f"{kb_context}"
            f"\n\nPresent this evaluation in a clear format: "
            f"Score and grade first, then Strengths, then Areas to Improve, "
            f"then Model Answer Outline, then Follow-up Questions an interviewer might ask."
        )

    # ── Readiness report ──
    if any(k in low for k in ("readiness", "report", "how ready", "am i ready", "report card", "action plan")):
        score_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:out of|/)\s*10", low)
        level_m = re.search(r"\b(entry|mid|senior)\b", low)
        role_m  = re.search(
            r"(software engineer|data scientist|product manager|devops|backend|frontend|sre)", low)
        score  = float(score_m.group(1)) if score_m else 6.5
        level  = level_m.group(1) if level_m else "mid"
        role   = role_m.group(1).title() if role_m else "Software Engineer"
        readiness = ("Strong" if score>=8.5 else "Ready" if score>=7 else "Needs Work" if score>=5.5 else "Not Ready")
        tips_map = {
            "entry": "Focus on DSA fundamentals, practice explaining concepts aloud, and prepare 3 project stories.",
            "mid":   "Write 5 STAR stories, study system design basics, and research the target company's stack.",
            "senior":"Prepare leadership examples, system design at scale, and how you've driven org-wide change.",
        }
        gaps = []
        if score < 7:   gaps.append("Answer depth and technical specificity")
        if score < 6.5: gaps.append("Structured storytelling for behavioral questions")
        if score < 8:   gaps.append("System design breadth")
        if not gaps:    gaps = ["Minor polish on delivery and conciseness"]
        report = {
            "job_role": role, "level": level, "score": score,
            "readiness": readiness, "key_gaps": gaps,
            "action_plan": [
                tips_map[level],
                "Complete 2 more full mock interview sessions.",
                "Record yourself answering questions to review pacing.",
                "Research the target company's tech stack and culture.",
            ],
            "resources": [
                "LeetCode — DSA practice: https://leetcode.com",
                "System Design Primer: https://github.com/donnemartin/system-design-primer",
                "STAR Method Guide: https://www.themuse.com/advice/star-interview-method",
            ],
        }
        return (
            f"\n\n[READINESS REPORT]\n{json.dumps(report, indent=2)}"
            f"\n\nPresent this as a final mock interview report card: "
            f"overall readiness badge, score, strengths summary, key gaps, "
            f"concrete action plan, and a motivational closing message."
        )

    # ── General knowledge query fallback ──
    kb_context = _search_knowledge_base(user_text)
    if kb_context:
        return kb_context

    return ""

# ── HTTP Request Handler ────────────────────────────────────────────────────────
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  [{self.log_date_time_string()}] {fmt % args}")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            rendered_html = HTML.replace("__MODEL_TAG__", OLLAMA_MODEL)
            body = rendered_html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_response(404); self.end_headers(); return

        length   = int(self.headers.get("Content-Length", 0))
        data     = json.loads(self.rfile.read(length))
        user_msgs = data.get("messages", [])

        # Build messages with system prompt
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in user_msgs[:-1]:
            messages.append(m)

        # Enrich the last user message with local tool output & RAG context
        if user_msgs:
            last_text = user_msgs[-1]["content"]
            enrichment = _detect_and_enrich(last_text)
            messages.append({
                "role": "user",
                "content": last_text + enrichment
            })

        reply = call_ollama(messages)

        body = json.dumps({"reply": reply}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

# ── Entry point ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 56)
    print("  TechQueue Interview Coach  [DEV · OLLAMA]")
    print("=" * 56)
    print(f"  LLM    : {OLLAMA_MODEL} via Ollama")
    print(f"  Ollama : {OLLAMA_URL}")
    print(f"  UI     : http://localhost:{PORT}")
    print(f"  KB Docs: {len(KB_DOCS)} files loaded")
    print("=" * 56)
    print(f"  Open  http://localhost:{PORT}  in your browser")
    print("  Press Ctrl+C to stop")
    print("=" * 56)
    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
