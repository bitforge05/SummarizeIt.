# SummarizeIt

> Upload any `.txt` or `.pdf` document — get an instant AI summary and an interactive Q&A chat powered by **Groq (LLaMA 3.3 70B)** and a local RAG pipeline.

![AI Powered](https://img.shields.io/badge/AI-Powered-7c3aed?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-18-61dafb?style=for-the-badge&logo=react)

---

## Table of Contents

1. [What is SummarizeIt?](#1-what-is-summarizeIt)
2. [Features](#2-features)
3. [Project Structure](#3-project-structure)
4. [Prerequisites](#4-prerequisites)
5. [Setup and Installation](#5-setup-and-installation)
6. [Running the App](#6-running-the-app)
7. [API Reference](#7-api-reference)
8. [How It Works — System Architecture](#8-how-it-works--system-architecture)
9. [Core AI Concept: RAG](#9-core-ai-concept-rag)
10. [Backend Deep Dive](#10-backend-deep-dive)
11. [Frontend Deep Dive](#11-frontend-deep-dive)
12. [Every Library Explained](#12-every-library-explained)
13. [Step-by-Step Walkthroughs](#13-step-by-step-walkthroughs)
14. [Environment and Configuration](#14-environment-and-configuration)
15. [Troubleshooting](#15-troubleshooting)
16. [Glossary](#16-glossary)

---

## 1. What is SummarizeIt?

**SummarizeIt** is an AI-powered document analysis tool. You upload a `.txt` or `.pdf` file, and the app:

- **Reads** the entire document automatically
- **Summarizes** it into clear, structured bullet points using LLaMA 3.3 70B via Groq
- **Lets you chat** with the document — ask any question and get an answer pulled directly from the file

Think of it as having a conversation with your document.

---

## 2. Features

- 📄 **PDF & TXT support** — drop any text or PDF file
- 🧠 **AI Summary** — structured bullet-point summary generated instantly
- 💬 **Interactive Q&A** — the system retrieves only the relevant parts before answering (RAG)
- 🔒 **Fully local embeddings** — no third-party embedding API; runs on your machine
- ⚡ **Fast responses** — Groq's LPU hardware delivers answers in ~1–2 seconds

---

## 3. Project Structure

```
SummarizeIt/
├── backend/                 # Python / FastAPI server
│   ├── main.py              # API endpoints
│   ├── processor.py         # RAG pipeline (embeddings, FAISS, Groq)
│   ├── requirements.txt     # Python dependencies
│   └── start.sh             # Helper start script
│
├── frontend/                # React app (Vite)
│   ├── src/
│   │   ├── App.jsx          # Main UI component
│   │   ├── index.css        # Glassmorphism design system
│   │   └── main.jsx         # React entry point
│   ├── index.html
│   └── package.json
│
├── .gitignore
└── README.md                # This file
```

---

## 4. Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | 3.12 recommended |
| Node.js | 18+ | For the React frontend |
| Groq API Key | — | Free at https://console.groq.com/keys |

---

## 5. Setup and Installation

### Step 1 — Clone the repository

```bash
git clone https://github.com/bitforge05/SummarizeIt..git
cd SummarizeIt.
```

### Step 2 — Backend setup

```bash
cd backend
pip install -r requirements.txt
```

Create your `.env` file with your Groq API key:

```bash
# Create backend/.env manually and add:
echo "GROQ_API_KEY=gsk_your_key_here" > .env
```

**How to get a free Groq API key:**
1. Go to **https://console.groq.com/keys**
2. Sign in (Google login available)
3. Click **"Create API Key"**
4. Copy the key (starts with `gsk_`)
5. Paste it into `backend/.env`

> **Free tier:** ~14,400 requests/day — more than enough for personal use.

### Step 3 — Frontend setup

```bash
cd ../frontend
npm install
```

---

## 6. Running the App

Open **two terminal windows**.

### Terminal 1 — Start Backend

```bash
cd backend
python3 main.py
```

Expected output:
```
[Embeddings] Loading local model …
[Embeddings] Ready.

INFO:     Uvicorn running on http://0.0.0.0:8000
```

> The first run downloads the embedding model (~90 MB). Subsequent runs are instant.

### Terminal 2 — Start Frontend

```bash
cd frontend
npm run dev
```

Then open **http://localhost:5173** in your browser.

---

## 7. API Reference

Base URL: `http://localhost:8000`

---

### `GET /`

Health check.

```bash
curl http://localhost:8000/
```

**Response:**
```json
{ "status": "online", "message": "AI Document Analyzer is running 🚀" }
```

---

### `POST /process-upload`

Upload and index a document. **Must be called first before `/summary` or `/chat`.**

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | ✅ | A `.txt` or `.pdf` file |

```bash
curl -X POST http://localhost:8000/process-upload \
  -F "file=@my_document.pdf"
```

**Success (200):**
```json
{ "message": "Processed successfully (42 chunks, 33,851 characters)." }
```

**Error responses:**

| Code | Reason |
|------|--------|
| 400 | Unsupported file type |
| 400 | PDF has no extractable text |
| 400 | Text file is empty |
| 500 | Internal processing error |

---

### `GET /summary`

Generate an AI summary of the uploaded document.

```bash
curl http://localhost:8000/summary
```

**Response (200):**
```json
{
  "summary": "## Key Topics\n\n**Introduction**\n- The document covers...\n\n**Main Arguments**\n- ..."
}
```

---

### `POST /chat`

Ask a question about the document using RAG.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the key findings?"}'
```

**Request body:**
```json
{ "question": "What is the main conclusion?" }
```

**Response (200):**
```json
{ "answer": "Based on the document, the main conclusion is..." }
```

---

## 8. How It Works — System Architecture

```
+--------------------------------------------------------------+
|                      USER'S BROWSER                          |
|   React Frontend (Vite)  -- localhost:5173                   |
+--------------------+-----------------------------------------+
                     |  HTTP (fetch API)
                     v
+--------------------------------------------------------------+
|                  PYTHON BACKEND (FastAPI)                    |
|   localhost:8000                                             |
|                                                              |
|  File Parser --> Text Chunker --> Embedder (local)           |
|                                       |                      |
|                                  FAISS Index                 |
|                                  (Vector DB)                 |
|                                       |                      |
|                            Groq API (LLaMA 3.3 70B)          |
|                    Summary + Grounded Q&A answers            |
+--------------------------------------------------------------+
```

The frontend and backend are **completely separate** apps that communicate via HTTP REST calls.

---

## 9. Core AI Concept: RAG

**RAG (Retrieval-Augmented Generation)** is the core AI pattern powering this app.

### The problem

LLMs don't know your document. Sending the entire document to an LLM on every question is slow, expensive, and hits token limits.

### The solution: three phases

#### Phase 1 — Indexing (runs once on upload)

```
Document
  → Split into ~800-char overlapping chunks
  → Encode each chunk into a 384-dim embedding vector
  → Store all vectors in FAISS (vector database)
```

#### Phase 2 — Retrieval (runs on each question)

```
Question
  → Encode question into embedding vector
  → Search FAISS for top-4 most similar chunk vectors
  → Return those chunks (the relevant context)
```

#### Phase 3 — Generation (runs on each question)

```
Context chunks + Question
  → Prompt: "Answer using ONLY the context below. Context: [...]. Question: [...]"
  → Send to Groq LLaMA 3.3 70B
  → Get a grounded, accurate answer
```

This is **fast**, **cheap**, and produces answers grounded in your document rather than hallucinated ones.

---

## 10. Backend Deep Dive

### `backend/processor.py`

The brain of the app.

#### `ContentRAG` class

A Python class holding all state: extracted text, chunks, FAISS index. One singleton instance is shared across all requests.

```python
class ContentRAG:
    source_text  # full raw text of the uploaded document
    chunks       # list of 800-char text chunks
    index        # FAISS vector index
```

#### Key methods

| Method | What it does |
|--------|-------------|
| `process_file(data, filename)` | Detects file type, extracts text, calls `_build_rag()` |
| `_build_rag(text)` | Chunks → embeds → indexes the full pipeline |
| `chunk_text()` | Splits text into overlapping 800-char windows |
| `create_embeddings()` | Calls local `sentence-transformers` to convert chunks to vectors |
| `build_index()` | Creates FAISS `IndexFlatL2` and adds all vectors |
| `get_summary()` | Sends first 12,000 chars to Groq for summarization |
| `query(question)` | Embeds question → FAISS search → Groq answer |
| `call_groq()` | Groq API call with retry logic for rate limits |

### `backend/main.py`

The web server using **FastAPI**.

- Defines all four API endpoints
- Handles CORS so the frontend on port 5173 can talk to the backend on port 8000
- Validates file extensions before processing
- Reads file bytes directly in memory (no temp files written to disk)

---

## 11. Frontend Deep Dive

### `frontend/src/App.jsx`

A single React component managing all UI state.

#### State variables

| State | Type | Purpose |
|-------|------|---------|
| `uploadedFile` | File | The selected file object |
| `isProcessing` | boolean | True while uploading and summarizing |
| `isReady` | boolean | True once a document has been indexed |
| `summary` | string | The AI-generated summary text |
| `messages` | array | Chat history `[{role, text}]` |
| `input` | string | Current chat input value |
| `isThinking` | boolean | True while waiting for a chat response |

#### Key hooks used

**`useState`** — stores and updates all the values above

**`useRef`** — two uses:
- `fileInputRef` — programmatically clicks the hidden `<input type="file">` when the styled button is clicked
- `chatEndRef` — an invisible div at the bottom of the chat that gets scrolled into view

**`useEffect`** — auto-scrolls the chat to the bottom every time `messages` changes

### `frontend/src/index.css`

The entire visual design system:

- **CSS Custom Properties** on `:root` — a token system (`--accent`, `--bg`, `--border`, etc.) that keeps colors consistent
- **`body::before`** — CSS pseudo-element rendering the background gradient without extra HTML elements
- **`.glass-panel`** — the glassmorphism card effect using `backdrop-filter: blur(14px)` + semi-transparent background
- **`@keyframes spin`** — loading spinner animation

---

## 12. Every Library Explained

### Backend

| Library | Purpose |
|---------|---------|
| **FastAPI** | Python web framework — turns functions into HTTP endpoints |
| **uvicorn** | ASGI server — actually runs and serves the FastAPI app |
| **python-dotenv** | Reads `backend/.env` and loads variables into the environment |
| **groq** | Official Groq Python SDK — sends prompts to LLaMA 3.3 70B |
| **sentence-transformers** | Local ML model that converts text into embedding vectors. Model: `all-MiniLM-L6-v2`, produces 384-dim vectors. No API key needed. |
| **faiss-cpu** | Facebook AI Similarity Search — vector database for instant nearest-neighbor search |
| **numpy** | Numerical arrays — bridges sentence-transformers output to what FAISS expects |
| **pypdf** | Reads PDF files and extracts text from each page |
| **python-multipart** | Required by FastAPI to parse `multipart/form-data` file uploads |

### Frontend

| Library | Purpose |
|---------|---------|
| **React 18** | UI framework with component-based reactive state |
| **Vite** | Build tool + dev server with instant hot-module replacement |
| **lucide-react** | SVG icon components (Sparkles, Send, MessageSquare, etc.) |

### External APIs

| API | Model | Free Tier |
|-----|-------|-----------|
| **Groq** | LLaMA 3.3 70B Versatile | ~14,400 requests/day |

---

## 13. Step-by-Step Walkthroughs

### When you upload a file

```
1. User selects a file → React stores it in state
2. User clicks "Analyze" → handleProcess() runs
3. Frontend creates FormData and POSTs file to /process-upload
4. FastAPI reads bytes, detects extension
5. .pdf  → pypdf extracts text from all pages
   .txt  → bytes decoded as UTF-8
6. _build_rag(text) runs:
   a. chunk_text()        → splits into ~15-50 overlapping chunks
   b. create_embeddings() → each chunk → 384-dim vector via sentence-transformers
   c. build_index()       → all vectors stored in FAISS IndexFlatL2
7. Backend returns 200 OK
8. Frontend immediately GETs /summary
9. get_summary() sends first 12,000 chars to Groq
10. Groq returns structured bullet-point summary
11. Frontend renders summary, enables the chat input
```

### When you ask a question

```
1. User types question, presses Enter
2. User's message appears immediately in chat
3. Frontend POSTs {"question": "..."} to /chat
4. query() encodes question → 384-dim vector
5. FAISS searches all chunk vectors by L2 distance
6. Top-4 most similar chunks returned
7. Prompt built:
   "Answer ONLY using context below.
    Context: [chunk1][chunk2][chunk3][chunk4]
    Question: [user's question]"
8. Groq LLaMA 3.3 70B generates a grounded answer
9. Frontend appends answer to chat, auto-scrolls
```

---

## 14. Environment and Configuration

### Required file: `backend/.env`

This file is **not committed to Git** (it's in `.gitignore`). You must create it manually.

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

### How to get a free Groq API key

| Step | Action |
|------|--------|
| 1 | Go to **https://console.groq.com/keys** |
| 2 | Sign in with Google |
| 3 | Click **"Create API Key"** |
| 4 | Copy the key (starts with `gsk_`) |
| 5 | Paste into `backend/.env` |

> **Never share your `.env` file or commit it to GitHub.** Your API key gives billing access to your account.

---

## 15. Troubleshooting

| Problem | Fix |
|---------|-----|
| `GROQ_API_KEY is missing` | Create `backend/.env` with `GROQ_API_KEY=gsk_...` |
| `No module named 'sentence_transformers'` | Run `pip install -r requirements.txt` inside `backend/` |
| `No module named 'groq'` | Run `pip install groq` — make sure you use the same `python3` that runs `main.py` |
| Summary/chat returns 500 | Check terminal for the actual error; most often a missing API key |
| PDF shows no text | Your PDF may be image-only (scanned). Convert to `.txt` first. |
| Slow first startup | First run downloads the 90 MB embedding model. Subsequent starts are instant. |

---

## 16. Glossary

| Term | Plain English |
|------|--------------|
| **LLM** | Large Language Model — AI trained on massive text datasets that can read, write and reason (e.g. GPT-4, LLaMA 3) |
| **RAG** | Retrieval-Augmented Generation — first search a database for relevant context, then send that context to an LLM for a grounded answer |
| **Embedding** | A list of numbers representing the "meaning" of text. Similar meanings → similar numbers. |
| **Vector** | A list of numbers. E.g. `[0.12, -0.45, 0.87, ...]` — here 384 numbers per text chunk. |
| **FAISS** | Facebook AI Similarity Search — a vector database that finds the most similar vectors in milliseconds |
| **Chunking** | Splitting a long document into smaller overlapping pieces for individual embedding and retrieval |
| **Sliding Window** | The chunking method: each chunk overlaps the next by 150 chars so boundary context isn't lost |
| **FastAPI** | Python web framework — turns Python functions into HTTP API endpoints |
| **CORS** | Browser security rule requiring servers to explicitly allow requests from different ports/domains |
| **React** | JavaScript UI library — components re-render automatically when state changes |
| **useState** | React hook for storing and updating values inside a component |
| **useEffect** | React hook that runs code when specified values change |
| **useRef** | React hook for referencing DOM elements without causing re-renders |
| **FormData** | JS object for packaging file uploads in HTTP requests |
| **Glassmorphism** | Design style using frosted-glass cards: semi-transparent + blur |
| **Vite** | Fast frontend build tool with instant hot-module reload |
| **Token** | Unit an LLM processes — roughly one word or sub-word. APIs charge per token. |
| **Groq** | Company running LLMs on custom LPU chips for very fast inference |
| **LLaMA 3.3 70B** | Meta's open-source 70 billion parameter LLM used here for summarization and Q&A |
| **sentence-transformers** | Library with pre-trained models turning sentences into embeddings. `all-MiniLM-L6-v2` used here. |
| **pypdf** | Python library to read PDFs and extract text |
| **Singleton** | Design pattern where only one object instance exists — `rag_instance` is shared by all API requests |
| **IndexFlatL2** | FAISS index doing exact nearest-neighbor search using Euclidean (L2) distance |
| **dotenv** | Convention for storing secrets in a `.env` file kept out of version control |
