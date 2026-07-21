# HomeworkPlus 📚✨

> AI-powered homework assistance platform — Photo-to-Answer, Voice Tutor, Collaborative Whiteboard, 3D Learning Map

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Angular 19, Angular Material, TailwindCSS, Three.js, Fabric.js |
| **Backend** | FastAPI, Python 3.12, SQLAlchemy Async |
| **Database** | NeonDB (PostgreSQL Serverless) |
| **Vector DB** | ChromaDB (RAG Knowledge Base) |
| **Cache/Queue** | Redis + Celery |
| **AI/LLM** | GPT-4o, Claude Sonnet, LangChain, LangGraph |
| **OCR** | EasyOCR + PaddleOCR |
| **Vision** | OpenCV |
| **Voice** | OpenAI Whisper STT + TTS |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- Docker Desktop
- NeonDB account → [neon.tech](https://neon.tech)
- OpenAI API key → [platform.openai.com](https://platform.openai.com)

### 1. Clone & Configure

```bash
git clone <repo-url>
cd homeworkplus

# Copy and fill in environment variables
cp backend/.env.example backend/.env
# Edit backend/.env with your NeonDB URL, OpenAI key, etc.
```

### 2. Start with Docker Compose (Recommended)

```bash
# Start all services: backend, frontend, Redis, ChromaDB
docker-compose up -d

# View logs
docker-compose logs -f backend
```

Services:
- **Frontend**: http://localhost:4200
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ChromaDB**: http://localhost:8001

### 3. Manual Local Setup

#### Backend

```bash
cd backend
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start FastAPI dev server
uvicorn app.main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A app.workers.celery_app worker --loglevel=info
```

#### Frontend

```bash
cd frontend
npm install
npm run dev  # or: ng serve
# → http://localhost:4200
```

---

## 📁 Project Structure

```
homeworkplus/
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   │   ├── agents/          # 9 AI agents
│   │   │   │   ├── vision_agent.py
│   │   │   │   ├── ocr_agent.py
│   │   │   │   ├── math_agent.py
│   │   │   │   ├── tutor_agent.py
│   │   │   │   ├── rag_agent.py
│   │   │   │   ├── voice_agent.py
│   │   │   │   ├── translation_agent.py
│   │   │   │   ├── recommendation_agent.py
│   │   │   │   └── progress_agent.py
│   │   │   └── pipeline.py      # Photo-to-Answer orchestrator
│   │   ├── api/v1/              # REST endpoints
│   │   ├── auth/                # JWT security
│   │   ├── models/              # 16 SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic v2 schemas
│   │   ├── websocket/           # Real-time WS manager
│   │   ├── workers/             # Celery tasks
│   │   ├── database/            # NeonDB connection
│   │   ├── config.py            # Settings
│   │   └── main.py              # FastAPI app
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── pages/           # 8 pages
│       │   ├── services/        # Angular services
│       │   ├── components/      # Shared components
│       │   └── guards/          # Route guards
│       └── styles/
├── docker-compose.yml
└── Makefile
```

---

## 🤖 AI Pipeline — Photo to Answer

```
Student Uploads Image
      │
      ▼
OpenCV Enhancement (VisionAgent)
      │
      ▼
PII Detection
      │
      ▼
EasyOCR + PaddleOCR (OCRAgent)
      │
      ▼
Math Detection + LaTeX (MathAgent)
      │
      ▼
Question Classification
      │
      ▼
ChromaDB RAG Search (RAGAgent)
      │
      ▼
GPT-4o / Claude (TutorAgent)
      │
      ▼
Step-by-Step Answer
      │
      ▼
TTS Voice Output (VoiceAgent)
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login → JWT tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET | `/api/v1/auth/me` | Current user profile |
| POST | `/api/v1/ai/upload-image` | Upload homework image |
| POST | `/api/v1/ai/solve` | Run Photo-to-Answer pipeline |
| POST | `/api/v1/ai/ask` | Text question → AI answer |
| POST | `/api/v1/ai/chat` | Multi-turn AI chat |
| GET | `/api/v1/dashboard/stats` | User dashboard data |
| GET | `/api/v1/dashboard/leaderboard` | XP leaderboard |
| WS | `/ws/whiteboard/{room_id}` | Collaborative whiteboard |
| WS | `/ws/chat/{session_id}` | Real-time chat |

---

## 🎮 Gamification

- **XP System**: Earn XP for every question solved, lesson completed, and study session
- **Levels**: 1–100+ based on XP curve
- **Badges**: 8 achievement badges (First Steps, Math Wizard, On Fire 🔥, Scholar 📚, etc.)
- **Streaks**: Daily study streak with bonus XP
- **Leaderboard**: Weekly and all-time rankings per subject

---

## 🛠️ Makefile Commands

```bash
make dev          # Start local dev (backend + frontend)
make docker-up    # Start Docker Compose
make docker-down  # Stop all containers
make migrate      # Run Alembic migrations
make test         # Run backend tests
make lint         # Run ruff linter
```

---

## 📜 License

MIT License — built for educational purposes.
