# SummarizeIt — AI Document Analyzer

SummarizeIt is a stateless, file-based AI web platform that allows you to upload text or PDF documents, instantly read AI-generated summaries, and run interactive RAG (Retrieval-Augmented Generation) Q&A against them. Best of all, it dynamically blends document context with **Live Web Search** using DuckDuckGo to provide answers enriched by out-of-document facts.

## Features
- 🚀 **Lightning Fast RAG:** Powered by Groq APIs and local sentence-transformers (No external vector DBs).
- 🔑 **Bring Your Own API Key (BYOK):** End users insert their own LLM API Key the moment they arrive. 
- 🔒 **Local Authentication:** Self-hosted user account persistence (powered by SQLite and JWTs) storing cross-session query history without relying on Firebase.
- 🌐 **Web Context Blending:** Toggle pure web search or doc-based web blending for rich contextual LLM replies.

## Architecture

* **Frontend:** React + Vite, styled purely with custom glassmorphic CSS implementations.
* **Backend:** FastAPI (Python), handling stateless API calls, in-memory FAISS indices per upload. Contains a local SQLite layer attached automatically via `lifespan` hook serving isolated User Sessions.

## Startup (Local Development)

### Backend Services
Navigate to `backend/` and install requirements:
```bash
python3 -m pip install -r requirements.txt
```
Run the FastAPI service (will create local `data.db` automatically):
```bash
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend UI
Navigate to `frontend/`:
```bash
npm install
npm run dev
```

## Production Deployment
Make sure to inject `VITE_API_URL` connecting to wherever you host your backend Python container.
Backend requires no database set up assuming a persistent volume exists targeting `backend/data.db`.
