# HomeworkPlus - Proof of Concept (POC) Workflow

## 1. Project Overview
HomeworkPlus is an advanced, AI-powered educational platform designed to provide interactive, multi-modal homework assistance. It goes beyond simple Q&A by integrating a robust "Photo-to-Answer" pipeline, voice tutoring, real-time collaborative whiteboards, and a comprehensive gamified learning experience.

## 2. Technical Stack
* **Frontend**: Angular 19, Angular Material, TailwindCSS, Three.js (for 3D learning maps), Fabric.js (for whiteboard collaboration)
* **Backend**: FastAPI, Python 3.12, SQLAlchemy Async
* **Data Layer**:
  * Relational Database: NeonDB (PostgreSQL Serverless)
  * Vector Database: ChromaDB (for RAG Knowledge Base)
  * Caching & Queue: Redis + Celery
* **AI & Machine Learning Ecosystem**:
  * Foundational Models: GPT-4o, Claude Sonnet
  * Orchestration: LangChain, LangGraph
  * Vision & OCR: OpenCV, EasyOCR, PaddleOCR
  * Speech: OpenAI Whisper STT + TTS

---

## 3. Core Workflow: The "Photo-to-Answer" Multi-Agent Pipeline

The centerpiece of this POC is a sophisticated orchestrator that routes tasks through specialized AI agents to process raw imagery into highly educational, step-by-step solutions.

### Pipeline Steps:
1. **User Input** (`POST /api/v1/ai/solve`): The student uploads a photo of their homework or problem set.
2. **Vision Pre-Processing (`VisionAgent`)**: 
   * Utilizes OpenCV to enhance image contrast, correct skew, and remove noise, optimizing the image for text extraction.
3. **Privacy Scrubbing**: 
   * Detects and redacts any Personally Identifiable Information (PII) from the image before sending data to external APIs.
4. **Text Extraction (`OCRAgent`)**: 
   * EasyOCR and PaddleOCR work in tandem to extract standard text layout from the image.
5. **Math & Symbol Detection (`MathAgent`)**: 
   * Identifies complex mathematical equations, graphs, or scientific symbols and reliably converts them into structured LaTeX formats.
6. **Question Classification & Retrieval (`RAGAgent`)**: 
   * The core question is classified by subject/topic.
   * ChromaDB is queried to retrieve relevant contextual data (e.g., textbook formulas, similar solved examples, syllabus context) to ground the LLM and prevent hallucinations.
7. **Educational Solution Generation (`TutorAgent`)**: 
   * Utilizing GPT-4o or Claude, the system ingests the extracted text, LaTeX, and RAG context.
   * Instead of just providing the final answer, the TutorAgent generates a structured, step-by-step explanation designed to teach the underlying concepts.
8. **Multi-Modal Output (`VoiceAgent`)**: 
   * The resulting solution is delivered via text and can be optionally converted into a natural-sounding audio explanation using OpenAI's TTS.

---

## 4. Real-Time Collaboration & Communication

* **Collaborative Whiteboard (`WS /ws/whiteboard/{room_id}`)**: Enables real-time, bidirectional drawing and equation solving using WebSockets, allowing students and human/AI tutors to interact on the same canvas simultaneously.
* **Continuous AI Chat (`WS /ws/chat/{session_id}`)**: Provides a persistent WebSocket connection for multi-turn follow-up questions, allowing the student to ask clarifying questions about the generated solution without losing context.

---

## 5. Gamification & Engagement Engine

To maximize student retention and motivation, the platform features a deeply integrated gamification system:
* **Experience Engine (XP)**: Users earn XP for interacting with the platform (solving questions, maintaining streaks).
* **Progression System**: Dynamic leveling from 1 to 100+ based on a predefined XP curve.
* **Achievements**: Unlockable badges (e.g., "First Steps", "Math Wizard", "Scholar") for reaching specific milestones.
* **Competitive Metrics**: Global and subject-specific leaderboards (`GET /api/v1/dashboard/leaderboard`) to encourage friendly competition.

---

## 6. Architecture & Scalability

* **Containerization**: The entire stack (Backend, Frontend, Redis, ChromaDB) is orchestrated via Docker Compose, ensuring environment parity across development and production.
* **Asynchronous Processing**: Heavy AI workloads (like OCR and complex LLM chains) are decoupled from the main API thread and managed by Celery workers, ensuring the FastAPI backend remains highly responsive.
