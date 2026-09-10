# TechQueue — Your AI-Powered Interview Coach

> An Interview Trainer Agent powered by **RAG (Retrieval-Augmented Generation)** on IBM watsonx Orchestrate.  
> Built with `ibm/granite-4-h-small` and the watsonx Orchestrate ADK.

---
## Problem Statement: 
<img width="785" height="476" alt="image" src="https://github.com/user-attachments/assets/901671e3-69ef-4fba-a54b-9e34730c5b05" />

---
## Overview

**TechQueue** prepares candidates for job interviews by generating tailored question sets and personalised preparation strategies based on their profile, experience level, and target job role.

It retrieves role-specific interview questions, industry expectations, behavioral scenarios, and HR guidelines from a curated knowledge base and uses RAG to deliver context-aware, up-to-date preparation advice.

### Key Features
- 🎯 **Personalised Prep Plans** — Full preparation plans generated from candidate profile via RAG
- 📋 **Tailored Question Sets** — Technical, behavioral, system design, and HR questions per role & level
- 🧠 **Answer Evaluation** — Multi-dimension scoring with strengths, gaps, and model answer outlines
- 📊 **Mock Interview Reports** — Final readiness assessment and action plan after a practice session
- 💬 **Conversational Coach** — Natural chat interface via watsonx Orchestrate

---
## Demo
<img width="1891" height="976" alt="image" src="https://github.com/user-attachments/assets/d9c1feee-cca4-48f6-bb76-337fdff7853f" />
<img width="1891" height="887" alt="image" src="https://github.com/user-attachments/assets/ad9ec937-2e8c-43e9-84d9-8f62d576a8e7" />


## Evaluation source
<img width="1702" height="920" alt="image" src="https://github.com/user-attachments/assets/5bf271a9-a52e-4df9-92dd-72707c1c4a50" />

---




## Architecture Diagram

```mermaid
graph TB
    User[👤 Candidate] -->|Chat| Agent[TechQueue Agent\nibm/granite-4-h-small]
    Agent -->|Invokes| PrepFlow[Interview Prep Flow\nRAG + LLM]
    Agent -->|Invokes| ProfileTool[build_candidate_profile]
    Agent -->|Invokes| QuestionTool[get_question_set_config]
    Agent -->|Invokes| EvalTool[evaluate_answer]
    Agent -->|Invokes| ReportTool[generate_mock_interview_report]
    PrepFlow -->|RAG Query| KB[(Interview\nKnowledge Base\nBuilt-in Milvus)]
    PrepFlow -->|LLM Generate| LLM[granite-4-h-small]
    KB -->|Retrieved Context| LLM
    LLM -->|Prep Plan| Agent
    Agent -->|Response| User

    style Agent fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style PrepFlow fill:#50C878,stroke:#2E7D4E,color:#fff
    style KB fill:#9B59B6,stroke:#7D3C98,color:#fff
    style LLM fill:#E67E22,stroke:#CA6F1E,color:#fff
    style ProfileTool fill:#F39C12,stroke:#D68910,color:#fff
    style QuestionTool fill:#F39C12,stroke:#D68910,color:#fff
    style EvalTool fill:#F39C12,stroke:#D68910,color:#fff
    style ReportTool fill:#F39C12,stroke:#D68910,color:#fff
```

---

## Interview Prep Flow Diagram

```mermaid
flowchart TD
    Start([▶ START]) --> Input[User Profile Input\nname · role · level · tech stack]
    Input --> ParseNode[parse_candidate_profile\nDerive focus areas & question types]
    ParseNode --> LLMNode[LLM Prompt Node\ngenerate_prep_plan\nibm/granite-4-h-small + RAG]
    LLMNode -->|Knowledge Base Query| KB[(Interview Knowledge Base\nRole Questions · STAR Guides\nSystem Design · HR Tips)]
    KB --> LLMNode
    LLMNode --> Output[InterviewPrepFlowOutput\nPrep Plan · Questions · Next Steps]
    Output --> End([⏹ END])

    style Start fill:#2ECC71,stroke:#27AE60,color:#fff
    style End fill:#E74C3C,stroke:#C0392B,color:#fff
    style ParseNode fill:#F39C12,stroke:#D68910,color:#fff
    style LLMNode fill:#3498DB,stroke:#2980B9,color:#fff
    style KB fill:#9B59B6,stroke:#7D3C98,color:#fff
    style Output fill:#1ABC9C,stroke:#17A589,color:#fff
```

---

## Answer Evaluation Flow

```mermaid
flowchart TD
    Start([▶ START]) --> Q[User provides: question + answer]
    Q --> Eval[evaluate_answer Tool\nScores 5 dimensions]
    Eval --> Scores[Clarity · Depth · Relevance\nExamples · Structure]
    Scores --> Grade[Overall Score 1–10\nLetter Grade A–F]
    Grade --> Feedback[Strengths & Improvements\nModel Answer Outline\nFollow-up Questions]
    Feedback --> End([⏹ END])

    style Start fill:#2ECC71,stroke:#27AE60,color:#fff
    style End fill:#E74C3C,stroke:#C0392B,color:#fff
    style Eval fill:#F39C12,stroke:#D68910,color:#fff
    style Grade fill:#3498DB,stroke:#2980B9,color:#fff
    style Feedback fill:#1ABC9C,stroke:#17A589,color:#fff
```

---

## Project Structure

```
techqueue_interview_coach/
├── __init__.py
├── main_flow.py                         # Flow test script
├── import-all.sh                        # CLI import script
├── README.md
├── tools/
│   ├── __init__.py
│   ├── profile_tools.py                 # build_candidate_profile, get_question_set_config
│   ├── evaluation_tools.py              # evaluate_answer, generate_mock_interview_report
│   └── interview_prep_flow.py           # Full interview prep flow (RAG + LLM)
├── agents/
│   └── techqueue_interview_coach.yaml   # Agent configuration
├── knowledge_base/
│   └── interview_knowledge_base.yaml    # Knowledge base spec
└── generated/
    └── interview_prep_flow.json         # Compiled flow spec (auto-generated)
```

---

## Tools Reference

| Tool | Type | Purpose |
|------|------|---------|
| `interview_prep_flow` | Flow | Full personalised prep plan via RAG + LLM |
| `build_candidate_profile` | Python | Profile analysis and focus area derivation |
| `get_question_set_config` | Python | Generate categorised question sets |
| `evaluate_answer` | Python | Multi-dimension answer scoring and feedback |
| `generate_mock_interview_report` | Python | Final readiness report card and action plan |

---

## Supported Roles & Levels

| Role Category | Experience Levels | Question Types |
|---------------|-------------------|----------------|
| Software Engineer | Entry / Mid / Senior | Technical · Behavioral · System Design · HR |
| Data Scientist / ML | Entry / Mid / Senior | Technical · Behavioral · Case Study · HR |
| Product Manager | Entry / Mid / Senior | Case Study · Situational · Behavioral · HR |
| DevOps / SRE / Cloud | Entry / Mid / Senior | Technical · System Design · Behavioral · HR |
| General / Other | Entry / Mid / Senior | Behavioral · HR |

---

## Setup & Usage

### Option A: Local Dev Mode (Offline with Ollama & granite3-moe:3b)
The fastest way to test TechQueue locally with zero cloud dependencies:

1. **Start Ollama**:
   ```bash
   ollama serve
   ```
   Ensure `granite3-moe:3b` is available:
   ```bash
   ollama list
   ```

2. **Launch Dev Server**:
   - Double-click `start_dev.bat` or run:
     ```cmd
     start_dev.bat
     ```
   - Open your browser to **`http://localhost:8181`**

---

### Option B: Deploy to watsonx Orchestrate

#### Prerequisites
- watsonx Orchestrate ADK installed
- Active environment configured (`orchestrate env activate`)

#### 1. Import Everything (Windows)
```cmd
import-all.bat
```
*(Or in PowerShell: `.\import-all.ps1`, or in Linux/macOS: `./import-all.sh`)*

#### 2. Start Chatting
```bash
orchestrate chat start
# Select: techqueue_interview_coach
```

#### 3. Test the Flow Programmatically
```cmd
python main_flow.py
```

---

## Sample Interactions

**Starting a session:**
> "I want to prepare for a Senior Backend Engineer interview. My name is Priya, I have 7 years of experience with Go and Kubernetes."

**Getting focused questions:**
> "Give me 5 system design questions for a mid-level Software Engineer."

**Evaluating a practice answer:**
> "Can you evaluate my answer to: 'Explain the CAP theorem'? My answer: [answer text]"

**Getting a readiness report:**
> "I finished 10 practice questions and averaged 7.5/10 for a mid-level SWE role. Give me a readiness report."

---

## Knowledge Base Documents

Upload the following documents to the knowledge base for full RAG coverage:

| Document | Content |
|----------|---------|
| `interview_questions_swe.txt` | Core DSA, concurrency, API design, SOLID, web security |
| `behavioral_interview_guide.txt` | STAR method guide, 4 key competencies, sample answers |
| `hr_interview_guidelines.txt` | HR screening questions, compensation, culture-fit |
| `system_design_prep.txt` | 5-step framework, CAP/PACELC theorems, scaling patterns |
| `data_science_interview_qa.txt` | ML theory, metrics (ROC/PR), A/B testing guardrails |
| `product_manager_interview_prep.txt` | CIRCLES method, RICE/MoSCoW, North Star metrics |

---

## Configuration

| Parameter | Value |
|-----------|-------|
| LLM Model | `ibm/granite-4-h-small` |
| Agent Style | `react_core` |
| Knowledge Base | Built-in Milvus (managed) |
| Embedding Model | `ibm/slate-125m-english-rtrvr-v2` |
| WatsonX URL | `https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29` |
| Project ID | `eca423cb-5689-4a9b-9279-0545246fde9c` |
