import os
import io
import ssl
import time
import uuid
import tempfile
from typing import List, Optional, Tuple

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ── Fix SSL certs for Python 3.12 on macOS ───────────────────────────────────
try:
    import certifi
    ssl._create_default_https_context = ssl.create_default_context
except Exception:
    pass

# ── Local embedding model ─────────────────────────────────────────────────────
print("[Embeddings] Loading local model …")
_embed_model = SentenceTransformer("all-MiniLM-L6-v2")
print("[Embeddings] Ready.\n")

# ── Groq client (lazy) ────────────────────────────────────────────────────────
_groq_client = None

def _get_groq() -> Groq:
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is missing. "
                "Add GROQ_API_KEY=your_key to backend/.env  (get one free at https://console.groq.com/keys)"
            )
        _groq_client = Groq(api_key=api_key)
    return _groq_client

GROQ_MODEL = "llama-3.3-70b-versatile"


# ─────────────────────────────────────────────────────────────────────────────
# Helper: call Groq with retry on transient errors
# ─────────────────────────────────────────────────────────────────────────────

def call_groq(prompt: str, system: str = "You are a helpful AI assistant.", retries: int = 2) -> str:
    client = _get_groq()
    for attempt in range(retries + 1):
        try:
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=4096,
            )
            return resp.choices[0].message.content
        except Exception as e:
            err = str(e)
            if attempt < retries and ("rate" in err.lower() or "429" in err):
                wait = 5 * (attempt + 1)
                print(f"[Groq] Rate limited. Retrying in {wait}s …")
                time.sleep(wait)
            else:
                raise


# ─────────────────────────────────────────────────────────────────────────────
# Helpers: file reading
# ─────────────────────────────────────────────────────────────────────────────

def extract_text_from_pdf(data: bytes) -> str:
    """Extract all text from a PDF byte stream."""
    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages).strip()

def extract_text_from_txt(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore").strip()


# ─────────────────────────────────────────────────────────────────────────────
# Main RAG class
# ─────────────────────────────────────────────────────────────────────────────

class ContentRAG:
    def __init__(self):
        self.source_text: str = ""
        self.chunks: List[str] = []
        self.index = None
        self.filename: str = ""

    # ── Text pipeline ─────────────────────────────────────────────────────────

    def chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if chunk.strip():
                chunks.append(chunk)
        return chunks

    def create_embeddings(self, chunks: List[str]) -> Optional[np.ndarray]:
        if not chunks:
            return None
        return np.array(_embed_model.encode(chunks, show_progress_bar=False)).astype("float32")

    def build_index(self, embeddings: np.ndarray):
        index = faiss.IndexFlatL2(embeddings.shape[1])
        index.add(embeddings)
        return index

    def _build_rag(self, text: str) -> Tuple[bool, str]:
        self.source_text = text
        self.chunks = self.chunk_text(text)
        if not self.chunks:
            return False, "No usable content found in the file."
        embeddings = self.create_embeddings(self.chunks)
        if embeddings is None:
            return False, "Failed to create embeddings."
        self.index = self.build_index(embeddings)
        return True, f"Processed successfully ({len(self.chunks)} chunks, {len(text):,} characters)."

    # ── Entry point ───────────────────────────────────────────────────────────

    def process_file(self, file_data: bytes, filename: str) -> Tuple[bool, str]:
        ext = os.path.splitext(filename)[-1].lower()
        self.filename = filename

        if ext == ".pdf":
            try:
                text = extract_text_from_pdf(file_data)
            except Exception as e:
                return False, f"Could not read PDF: {e}"
            if not text:
                return False, "PDF has no extractable text (it may be scanned image-only)."

        elif ext == ".txt":
            text = extract_text_from_txt(file_data)
            if not text:
                return False, "The text file is empty."

        else:
            return False, f"Unsupported file type '{ext}'. Please upload a .txt or .pdf file."

        print(f"[Process] '{filename}' → {len(text):,} characters extracted.")
        return self._build_rag(text)

    # ── AI features ───────────────────────────────────────────────────────────

    def get_summary(self) -> str:
        if not self.source_text:
            return "No content loaded. Please upload a file first."
        excerpt = self.source_text[:12000]
        prompt = (
            "Summarize the following document clearly and concisely.\n"
            "- Use bullet points grouped under short headings\n"
            "- Highlight key insights and takeaways\n"
            "- Be thorough but easy to read\n\n"
            f"Document content:\n{excerpt}"
        )
        return call_groq(prompt, system="You are an expert document summarizer. Provide clear, structured summaries.")

    def query(self, question: str) -> str:
        if not self.index:
            return "Please upload and process a document first."

        q_emb = np.array(_embed_model.encode([question])).astype("float32")
        _, indices = self.index.search(q_emb, k=4)
        context = "\n\n".join(
            self.chunks[i] for i in indices[0] if i < len(self.chunks)
        )
        prompt = (
            "Answer the question using ONLY the document context below.\n"
            'If the answer is not in the context, say: "This is not covered in the document."\n\n'
            f"Context:\n{context}\n\n"
            f"Question: {question}"
        )
        return call_groq(prompt, system="You are a precise Q&A assistant. Answer based only on the provided context.")


# Singleton
rag_instance = ContentRAG()