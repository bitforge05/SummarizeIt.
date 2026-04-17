# SummarizeIt

An AI-powered document analysis platform. Upload a PDF or text file, get an instant AI summary, and chat with your document using Retrieval-Augmented Generation (RAG). Supports live web search as an optional context layer.

## Features

- **Document Upload** — Upload `.pdf` or `.txt` files and get an AI-generated summary instantly
- **RAG Chat** — Ask questions about your document; the AI retrieves the most relevant passages to answer accurately
- **Web Search Mode** — Toggle live web search (via DuckDuckGo) to blend real-time results with document context
- **User Accounts** — Username/password authentication with JWT sessions; all chats and sessions are saved per user
- **Session History** — Resume any past document session from the sidebar
- **Bring Your Own API Key** — Works with any Groq-compatible API key; keys are never stored on the server

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite |
| Styling | Vanilla CSS with glassmorphism |
| Backend | FastAPI (Python) |
| AI / LLM | Groq API (`llama-3.3-70b-versatile`) |
| Embeddings | `sentence-transformers` (local, no external API) |
| Vector Search | FAISS (in-memory per session) |
| Web Search | DuckDuckGo Search (no API key required) |
| Auth | bcrypt + JWT |
| Database | SQLite (auto-created on startup) |

## Project Structure

```
summarizeit/
├── backend/
│   ├── main.py          # FastAPI app, all routes
│   ├── processor.py     # RAG engine, web search, Groq calls
│   ├── auth.py          # bcrypt hashing, JWT tokens
│   ├── database.py      # SQLite setup and helpers
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.jsx      # Full React app (auth, upload, chat, history)
    │   └── index.css    # All styles
    └── index.html
```

## Local Development

### Backend

```bash
cd backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn main:app --reload --port 8000
```

The SQLite database (`data.db`) is created automatically on first run.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:5173` and connects to the backend at `http://localhost:8000` by default.

## Environment Variables

### Frontend (`.env`)
```
VITE_API_URL=https://your-backend-url.com
```
Without this, the frontend falls back to `http://localhost:8000`.

### Backend (`.env`)
```
JWT_SECRET=your_random_secret_here
```
If not set, defaults to a development secret (change this in production).

## Deployment

The frontend is a static Vite build — deploy to **Vercel**, Netlify, or any CDN.

The backend is a Python FastAPI app — deploy to **Railway**, **Render**, or any container host. Make sure to:

1. Set `JWT_SECRET` as an environment variable on your backend host
2. Set `VITE_API_URL` to your live backend URL on Vercel

### Vercel (Frontend)

Connect your GitHub repo on [vercel.com](https://vercel.com), set the root directory to `frontend`, and add `VITE_API_URL` in the environment variables settings.

## How It Works

1. **Upload** — The file is sent to the backend, which extracts text and builds a FAISS vector index using local sentence-transformer embeddings
2. **Summary** — The first 12,000 characters are sent to Groq to generate a structured summary
3. **Chat** — Each question is embedded and matched against the vector index to retrieve the 4 most relevant text chunks, which are injected as context into the Groq prompt along with your conversation history
4. **Web Search** — When enabled, DuckDuckGo fetches the top 5 results for your question and merges them with document context before the LLM call
