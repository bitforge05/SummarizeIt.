import json
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from processor import rag_instance
from database import init_db, get_db
from auth import register_user, login_user, get_current_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the SQLite database tables on startup
    init_db()
    yield
    # No shutdown logic needed for SQLite


app = FastAPI(title="AI Document Analyzer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {".txt", ".pdf"}


# ── Models ────────────────────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    question: str
    web_search_enabled: bool = False
    history: Optional[list] = []

class WebSearchRequest(BaseModel):
    question: str
    history: Optional[list] = []

class SaveSessionRequest(BaseModel):
    id: str
    filename: str
    summary: str
    messages: list
    webSearch: bool = False


# ── Key validation helper ─────────────────────────────────────────────────────

def _require_api_key(x_api_key: Optional[str]) -> str:
    """Extract and validate the API key from the request header."""
    if not x_api_key or not x_api_key.strip():
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide your key via the X-Api-Key header.",
        )
    return x_api_key.strip()


# ── Auth Routes ───────────────────────────────────────────────────────────────

@app.post("/auth/register")
def register(req: AuthRequest):
    return register_user(req.username, req.password)

@app.post("/auth/login")
def login(req: AuthRequest):
    return login_user(req.username, req.password)


# ── Session Routes (SQLite) ───────────────────────────────────────────────────

@app.get("/sessions")
def get_sessions(user=Depends(get_current_user)):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM sessions WHERE user_id = ? ORDER BY updated_at DESC", 
        (user["sub"],)
    ).fetchall()
    db.close()
    
    sessions = []
    for r in rows:
        sessions.append({
            "id": r["id"],
            "filename": r["filename"],
            "summary": r["summary"],
            "messages": json.loads(r["messages"]),
            "updatedAt": r["updated_at"]
        })
    return sessions

@app.post("/sessions")
def save_session(req: SaveSessionRequest, user=Depends(get_current_user)):
    db = get_db()
    existing = db.execute("SELECT id FROM sessions WHERE id = ? AND user_id = ?", (req.id, user["sub"])).fetchone()
    
    messages_str = json.dumps(req.messages)
    if existing:
        db.execute(
            "UPDATE sessions SET filename = ?, summary = ?, messages = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (req.filename, req.summary, messages_str, req.id)
        )
    else:
        db.execute(
            "INSERT INTO sessions (id, user_id, filename, summary, messages) VALUES (?, ?, ?, ?, ?)",
            (req.id, user["sub"], req.filename, req.summary, messages_str)
        )
    db.commit()
    db.close()
    return {"status": "saved"}

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str, user=Depends(get_current_user)):
    db = get_db()
    db.execute("DELETE FROM sessions WHERE id = ? AND user_id = ?", (session_id, user["sub"]))
    db.commit()
    db.close()
    return {"status": "deleted"}


# ── Core App Routes ───────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "online", "message": "AI Document Analyzer is running 🚀"}

@app.post("/process-upload")
async def process_upload(
    file: UploadFile = File(...),
    x_api_key: Optional[str] = Header(default=None),
    user=Depends(get_current_user), # verify token
):
    """Upload a .txt or .pdf file and build the RAG index."""
    _require_api_key(x_api_key)

    import os
    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Please upload a .txt or .pdf file.",
        )

    try:
        data = await file.read()
        success, message = rag_instance.process_file(data, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {e}")

    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}

@app.get("/summary")
async def get_summary(
    x_api_key: Optional[str] = Header(default=None),
    user=Depends(get_current_user)
):
    api_key = _require_api_key(x_api_key)
    try:
        return {"summary": rag_instance.get_summary(api_key=api_key)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(
    request: ChatRequest,
    x_api_key: Optional[str] = Header(default=None),
    user=Depends(get_current_user)
):
    """
    Answer a question about the uploaded document.
    Optionally blends live web search results when web_search_enabled=True.
    """
    api_key = _require_api_key(x_api_key)
    try:
        answer = rag_instance.query(
            question=request.question,
            api_key=api_key,
            web_search_enabled=request.web_search_enabled,
            history=request.history,
        )
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/web-search")
async def standalone_web_search(
    request: WebSearchRequest,
    x_api_key: Optional[str] = Header(default=None),
    user=Depends(get_current_user)
):
    """
    Perform a pure web search (no document context) and answer via Groq.
    Useful when no document is uploaded but web search is enabled.
    """
    api_key = _require_api_key(x_api_key)
    try:
        answer = rag_instance.query(
            question=request.question,
            api_key=api_key,
            web_search_enabled=True,
            history=request.history,
        )
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
