# Sunbeam SmartBot

Sunbeam SmartBot is an Agentic RAG application with a FastAPI/LangGraph backend, a React/Vite frontend, and a Python CLI for scraping and indexing Sunbeam information. It uses ChromaDB for local vector storage and Groq for LLM inference.

## Project structure

```text
Sunbeam_SmartBot/
├── .vscode/
│   └── extensions.json        # Recommended VS Code extensions
├── backend/
│   ├── app/                   # FastAPI API, agent, tools, and RAG services
│   ├── data/                  # Local conversation database (not committed)
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── run.py
├── data/
│   ├── documents/             # Source text used by the RAG applications
│   └── chroma_db/             # Local vector database (not committed)
├── frontend/
│   ├── src/
│   ├── package.json
│   └── package-lock.json
├── src/sunbeam_smartbot/      # Python scraper, indexer, and CLI package
├── docker-compose.yml
├── render.yaml
├── .dockerignore
├── pyproject.toml
└── requirements.txt
```

## Setup

Requires Python 3.10 or newer, Node.js/npm, Google Chrome for scraping, and a Groq API key.

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -r backend\requirements.txt
npm ci --prefix frontend
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
if (-not (Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
```

Set `GROQ_API_KEY` in `.env` and/or `backend/.env`. The frontend can use its `.env.example` as a template if you need to set `VITE_API_BASE_URL`. Example files contain placeholders only; do not commit real credentials.

## Run locally

Start the backend from a terminal:

```powershell
Set-Location backend
python run.py
```

Start the frontend from another terminal:

```powershell
npm --prefix frontend run dev
```

The UI is served at `http://localhost:5173`; the API and OpenAPI docs are at `http://localhost:8000` and `http://localhost:8000/docs`.

The standalone Python chat CLI can be started from the project root. The root-level `rag_chatbot.py` remains as a compatibility launcher:

```powershell
python -m sunbeam_smartbot
# or
python rag_chatbot.py
```

## Ingest documents

The backend's incremental ingestion pipeline reads the files listed in `backend/app/rag/ingestion.py` from `data/documents/`.

The standalone index builder can also be run from the project root:

```powershell
python -m sunbeam_smartbot.app
```

This scrapes configured pages and replaces `data/chroma_db/`. **Back up the local database before running it if you need to preserve its current contents.**

## Tests and build

Run backend tests from the backend directory:

```powershell
Set-Location backend
python -m pytest
```

Build the frontend from the project root:

```powershell
npm --prefix frontend run build
```

To run the containerized backend with its built frontend:

```powershell
docker compose up --build
```

## GitHub and local files

Commit source, tests, documentation, `.env.example` files, `.vscode/extensions.json`, and `frontend/package-lock.json`. The `.gitignore` excludes local environment files, Python/Node dependencies, build output, SQLite files, and the Chroma database. The text files in `data/documents/` remain trackable.
