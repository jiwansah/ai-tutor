AI Tutor — Broad Overview Design
A complete, consolidated design covering every layer — from student input to dashboards.

1. What We Are Building
A personalized, curriculum-grounded AI tutor for Classes 1–12 that:

    Understands the student (mastery, misconceptions, pace)
    Understands the curriculum (board, class, subject, chapter, concept)
    Teaches adaptively (diagnose → plan → teach → check → adapt)
    Grounds every answer in the textbook (RAG)
    Tracks progress over time (knowledge tracing)
    Supports multiple modes (Teacher, Socratic, Practice, Exam, Revision…)
    Is safe for children (first-class safety layer)
    Not a chatbot. A tutoring system.


2. The 7 Pillars

┌─────────────────────────────────────────────────────────────┐
│                     AI TUTOR PLATFORM                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   1. CURRICULUM INTELLIGENCE                                 │
│      Board → Class → Subject → Chapter → Section → Concept   │
│                                                              │
│   2. KNOWLEDGE BASE (RAG)                                    │
│      Textbook chunks · Embeddings · Citations                │
│                                                              │
│   3. STUDENT MODEL                                           │
│      Mastery · Misconceptions · Style · History              │
│                                                              │
│   4. TUTOR AGENT (Orchestrator)                              │
│      Diagnose → Plan → Teach → Check → Adapt                 │
│                                                              │
│   5. TUTOR SERVICES                                          │
│      Explain · Hint · Practice · Evaluate · Track            │
│                                                              │
│   6. LEARNING ENGINE                                         │
│      Knowledge Tracing · Spaced Repetition · Recommendations │
│                                                              │
│   7. SAFETY & GOVERNANCE                                     │
│      Input/Output Safety · Privacy · Audit · Dashboards      │
│                                                              │
└─────────────────────────────────────────────────────────────┘

3. Broad Architecture

┌──────────────────────────────────────────────────────────────┐
│                      STUDENT TOUCHPOINTS                      │
│         Web · Mobile · Voice · Image Upload · Offline         │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                        SAFETY LAYER                           │
│   Input Filter → Age Check → PII Redaction → Content Mod      │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    TUTOR ORCHESTRATOR                         │
│                                                               │
│   State Machine:                                              │
│   DIAGNOSE → PLAN → TEACH → CHECK → ADAPT → UPDATE           │
│                                                               │
│   Modes: Teacher · Socratic · Practice · Exam ·              │
│          Revision · Doubt · Quiz · Homework                   │
└──┬──────────┬──────────┬──────────┬──────────┬───────────────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
┌───────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Curri- │ │Know-   │ │Student │ │Concept │ │Tools   │
│culum  │ │ledge   │ │Model   │ │Graph   │ │Layer   │
│DB     │ │Base    │ │        │ │        │ │        │
│       │ │(RAG)   │ │        │ │        │ │SymPy   │
│Board  │ │        │ │Mastery │ │Prereq  │ │OCR     │
│Class  │ │Chunks  │ │Miscon- │ │Objec-  │ │Calc    │
│Subject│ │Embed   │ │ceptions│ │tives   │ │Code    │
│Chapter│ │Cite    │ │Style   │ │Miscon- │ │        │
│Section│ │        │ │History │ │ceptions│ │        │
└───────┘ └────────┘ └────────┘ └────────┘ └────────┘
   │          │          │          │          │
   └──────────┴──────────┴──────────┴──────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                     TUTOR SERVICES                            │
│   Explain · Ask · Practice · Evaluate · Hint · Track         │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                   LEARNING ENGINE                             │
│   Knowledge Tracing (BKT) · Spaced Repetition (FSRS)         │
│   Misconception Detection · Recommendation · Difficulty Cal   │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                      PROGRESS DB                              │
│   Skills · Attempts · Weak Areas · Mastery · Conversations    │
└───────────────────────────┬──────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Parent     │   │   Teacher    │   │    Admin     │
│  Dashboard   │   │  Dashboard   │   │  Dashboard   │
└──────────────┘   └──────────────┘   └──────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                     OUTPUT SAFETY                             │
│   Age Filter → Boundary Check → Audit Log                    │
└──────────────────────────────────────────────────────────────┘


4. Core Data Model
Curriculum (structured)
Board → Class → Subject → Book → Chapter → Section → Chunk

Concept Graph (pedagogical)
Concept
  ├── prerequisites[]
  ├── learning_objectives[]
  ├── misconceptions[]
  ├── examples[]
  └── exercises[]


Student Model
Student
  ├── profile (class, board, language, style)
  ├── mastery{concept: score}
  ├── misconceptions[]
  ├── attempts[]
  ├── sessions[]
  └── review_schedule{}

5. Request Flow (one student, one question)

    1.  Student asks question (text / voice / image)
    2.  Safety layer: input check
    3.  Load student model
    4.  Query understanding: subject, chapter, concept
    5.  Diagnose: prerequisite check, misconception scan
    6.  Plan: choose teaching strategy
    7.  Retrieve: textbook + concept graph + misconceptions
    8.  Teach: generate explanation / hint / question
    9.  Tools: verify (SymPy / calculator / OCR)
    10. Check: evaluate student response
    11. Adapt: choose next action
    12. Update: mastery (BKT) + review (FSRS)
    13. Safety layer: output check
    14. Respond to student
    15. Log to Progress DB
    16. Update dashboards

6. The Tutoring Loop (core intelligence)
        ┌──────────────┐
        │   DIAGNOSE   │  What does the student know?
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │     PLAN     │  Hint? Example? Re-teach? Practice?
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │    TEACH     │  Multi-turn, Socratic, grounded
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │    CHECK     │  Verify + assess + misconception detect
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │    ADAPT     │  Easy/hard? Re-teach? Move on?
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │   UPDATE     │  Mastery, misconceptions, schedule
        └──────────────┘
               │
               └──► next session starts here

7. Tutor Modes
Mode	    Purpose	            Behavior
Teacher	    Explain concepts    Full explanation, examples
Socratic	Guide discovery	    Questions, no direct answers
Practice	Skill building	    Generates questions
Exam	    Test readiness	    Timed, no hints
Revision	Weak areas	        Focused on low mastery
Doubt	    Quick answers	    Direct, cited
Quiz	    Quick check	        5–10 min assessment
Homework	Assignment help	    Step-by-step walkthrough


8. Knowledge Tracing & Spaced Repetition
After every attempt:
  ┌─────────────────────────────────────────────┐
  │  BKT: update P(mastery | response)          │
  │  Misconception detector: classify error     │
  │  FSRS: schedule next review date            │
  │  Recommender: pick next concept             │
  └─────────────────────────────────────────────┘
Result: the tutor knows what to teach next, when to review, and how to teach it.

9. Safety Layer (children-first)
        Student Input
            ↓
        Input Safety: age check, PII redaction, unsafe content filter
            ↓
        Tutor Agent
            ↓
        Output Safety: age-appropriate language, boundary check
            ↓
        Audit Log
            ↓
        Student


10. Dashboards
Student
    Progress, mastery, streak, next topics
Parent
    Summary only (not full conversations)
    Strengths, weak areas, time spent, alerts
Teacher
    Class-level mastery heatmap
    Common misconceptions
    Flagged AI answers
    Content authoring + review
Admin
    Content pipeline
    Board/subject coverage
    System health, cost, usage

11. Tech Stack
Layer	        Choice
Backend	        Python FastAPI
Relational      DB	PostgreSQL
Vector DB	    pgvector / Qdrant
Embeddings	    BGE / E5 / OpenAI
LLM	            Tiered: small (routing) → medium (teaching) → large (rare)
Tools	        SymPy, Wolfram, Tesseract, Code Runner
Orchestration	LangGraph / LlamaIndex / custom
Queue	        Redis + Celery
Storage	        S3 / GCS
Frontend	    Next.js / Flutter
Voice	        Whisper + TTS
Auth	        JWT + RBAC


12. Build Phases
Phase	    Focus	                                        Deliverable
1 (M1–3)	Curriculum DB, RAG, basic tutor	                Grounded Q&A tutor
2 (M4–6)	Student model, BKT, misconceptions, evaluator	Adaptive tutor
3 (M7–9)	Modes, voice, image, spaced repetition	        Multi-modal tutor
4 (M10–12)	Dashboards, multi-board, authoring, offline	    Full platform


13. What Makes It a Tutor (Not a Chatbot)
Chatbot	            This AI Tutor
Waits for question	Diagnoses first
Gives answer	    Hints → steps → practice
Same for everyone	Personalized per student
Forgets	            Remembers mastery + misconceptions
No verification	    SymPy + LLM verifier
No prerequisites	Concept graph
No progression	    BKT + FSRS
One mode	        8+ modes
Student only	    Student + Parent + Teacher

14. One-Line Summary
Safety → Orchestrator → (Curriculum + RAG + Student Model + Concept Graph + Tools) → Tutor Services → Learning Engine → Progress DB → Dashboards → Safety





1. Project Structure
ai-tutor/
├── docker-compose.yml
├── .env.example
├── README.md
│
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   │
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── deps.py
│   │   │
│   │   ├── core/
│   │   │   ├── security.py
│   │   │   ├── logging.py
│   │   │   ├── exceptions.py
│   │   │   ├── rate_limit.py
│   │   │   └── redis.py
│   │   │
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── models/
│   │   │       ├── user.py
│   │   │       ├── curriculum.py
│   │   │       ├── content.py
│   │   │       ├── student.py
│   │   │       ├── session.py
│   │   │       └── audit.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── auth.py
│   │   │   ├── curriculum.py
│   │   │   ├── tutor.py
│   │   │   └── student.py
│   │   │
│   │   ├── api/
│   │   │   ├── router.py
│   │   │   └── v1/
│   │   │       ├── auth.py
│   │   │       ├── curriculum.py
│   │   │       ├── tutor.py
│   │   │       ├── ingest.py
│   │   │       └── dashboard.py
│   │   │
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── curriculum_service.py
│   │   │   ├── ingest_service.py
│   │   │   ├── rag_service.py
│   │   │   ├── embedding_service.py
│   │   │   ├── llm_service.py
│   │   │   ├── safety_service.py
│   │   │   ├── diagnostic_service.py
│   │   │   ├── planner_service.py
│   │   │   ├── tutor_service.py
│   │   │   ├── evaluator_service.py
│   │   │   ├── knowledge_tracing.py
│   │   │   ├── spaced_repetition.py
│   │   │   └── misconception_service.py
│   │   ├── repositories/           # ← NEW: data access (all SQL)
│   │   ├── base.py
│   │   ├── user_repo.py
│   │   ├── curriculum_repo.py
│   │   ├── content_repo.py
│   │   ├── student_repo.py
│   │   ├── session_repo.py
│   │   └── audit_repo.py
│   │   ├── agents/
│   │   │   ├── orchestrator.py
│   │   │   ├── states.py
│   │   │   ├── diagnoser.py
│   │   │   ├── planner.py
│   │   │   ├── teacher.py
│   │   │   ├── evaluator.py
│   │   │   └── verifier.py
│   │   │
│   │   ├── tools/
│   │   │   ├── math_tool.py
│   │   │   ├── ocr_tool.py
│   │   │   └── code_tool.py
│   │   │
│   │   ├── prompts/
│   │   │   ├── system.py
│   │   │   ├── teacher.py
│   │   │   ├── socratic.py
│   │   │   └── evaluator.py
│   │   │
│   │   └── workers/
│   │       ├── celery_app.py
│   │       └── tasks.py
│   │
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_tutor.py
│       └── test_rag.py
│
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── Dockerfile
│   │
│   └── src/
│       ├── app/
│       │   ├── layout.tsx
│       │   ├── page.tsx
│       │   ├── (auth)/
│       │   │   ├── login/page.tsx
│       │   │   └── register/page.tsx
│       │   ├── (tutor)/
│       │   │   ├── layout.tsx
│       │   │   ├── dashboard/page.tsx
│       │   │   ├── tutor/page.tsx
│       │   │   ├── practice/page.tsx
│       │   │   └── progress/page.tsx
│       │   └── api/
│       │
│       ├── components/
│       │   ├── ui/
│       │   ├── tutor/
│       │   │   ├── ChatWindow.tsx
│       │   │   ├── MessageBubble.tsx
│       │   │   ├── StreamingText.tsx
│       │   │   ├── InputBar.tsx
│       │   │   ├── ModeSelector.tsx
│       │   │   ├── CitationCard.tsx
│       │   │   └── StepCard.tsx
│       │   └── curriculum/
│       │
│       ├── lib/
│       │   ├── api.ts
│       │   ├── auth.ts
│       │   ├── store.ts
│       │   └── utils.ts
│       │
│       ├── hooks/
│       │   ├── useTutor.ts
│       │   ├── useStreaming.ts
│       │   └── useAuth.ts
│       │
│       └── styles/
│           └── globals.css
│
└── infra/
    ├── nginx/
    │   └── nginx.conf
    ├── postgres/
    │   └── init.sql
    └── k8s/
        ├── backend.yaml
        ├── frontend.yaml
        └── worker.yaml