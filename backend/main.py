from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from processor import rag_instance

app = FastAPI(title="AI Document Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {".txt", ".pdf"}


class ChatRequest(BaseModel):
    question: str


@app.get("/")
async def root():
    return {"status": "online", "message": "AI Document Analyzer is running 🚀"}


@app.post("/process-upload")
async def process_upload(file: UploadFile = File(...)):
    """Upload a .txt or .pdf file and build the RAG index."""
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
async def get_summary():
    try:
        return {"summary": rag_instance.get_summary()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        return {"answer": rag_instance.query(request.question)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
