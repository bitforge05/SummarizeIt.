import os
import io
import ssl
import time
from typing import List, Optional, Tuple

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
from groq import Groq

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

GROQ_MODEL = "llama-3.3-70b-versatile"


# ─────────────────────────────────────────────────────────────────────────────
# Web search (DuckDuckGo — no API key required)
# ─────────────────────────────────────────────────────────────────────────────

def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web using DuckDuckGo and return a list of results.
    Each result has keys: title, body, href.
    Returns an empty list on any error so callers can degrade gracefully.
    """
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return results
    except Exception as e:
        print(f"[WebSearch] Error: {e}")
        return []


def format_web_results(results: list[dict]) -> str:
    """Format DuckDuckGo results into a readable context string for Groq."""
    if not results:
        return "No web results found."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r.get('title', 'No title')}\n{r.get('body', '')}\nSource: {r.get('href', '')}")
    return "\n\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Groq helper — creates a fresh client per call (no server-side key storage)
# ─────────────────────────────────────────────────────────────────────────────

def call_groq(prompt: str, api_key: str, system: str = "You are a helpful AI assistant.", retries: int = 2, history: list = None) -> str:
    """
    Call the Groq API using the user-supplied api_key.
    A fresh client is created each call so the key is never cached server-side.
    """
    if not api_key or not api_key.strip():
        raise ValueError("No Groq API key provided. Please enter your key in the app.")

    client = Groq(api_key=api_key.strip())

    msgs = [{"role": "system", "content": system}]
    if history:
        for m in history:
            msgs.append({"role": m.get("role", "user"), "content": m.get("content", "")})
    msgs.append({"role": "user", "content": prompt})

    for attempt in range(retries + 1):
        try:
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=msgs,
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
# File reading helpers
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

    # ── Text pipeline ──────────────────────────────────────────────────────────

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
        idx = faiss.IndexFlatL2(embeddings.shape[1])
        idx.add(embeddings)
        return idx

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

    # ── Entry point ────────────────────────────────────────────────────────────

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

    # ── AI features ────────────────────────────────────────────────────────────

    def get_summary(self, api_key: str) -> str:
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
        return call_groq(
            prompt, api_key=api_key,
            system="You are an expert document summarizer. Provide clear, structured summaries."
        )

    def query(self, question: str, api_key: str, web_search_enabled: bool = False, history: list = None) -> str:
        """
        Answer a question using the document RAG index and chat history.
        If web_search_enabled is True, also fetch live web results and blend them
        into the context before asking Groq.
        """
        # ── Fetch document context ─────────────────────────────────────────────
        doc_context = ""
        if self.index:
            q_emb = np.array(_embed_model.encode([question])).astype("float32")
            _, indices = self.index.search(q_emb, k=4)
            doc_context = "\n\n".join(
                self.chunks[i] for i in indices[0] if i < len(self.chunks)
            )
        elif not web_search_enabled:
            return "Please upload and process a document first."

        # ── Optionally fetch web context ───────────────────────────────────────
        web_context = ""
        if web_search_enabled:
            print(f"[WebSearch] Searching for: {question}")
            results = web_search(question)
            web_context = format_web_results(results)

        # ── Build combined prompt ──────────────────────────────────────────────
        sections = []
        if doc_context:
            sections.append(f"## Document Context\n{doc_context}")
        if web_context:
            sections.append(f"## Live Web Results\n{web_context}")

        context_block = "\n\n".join(sections)
        has_doc = bool(self.index)
        has_web = bool(web_search_enabled)

        if has_doc and has_web:
            instructions = (
                "You have two sources of context: excerpts from an uploaded document, "
                "and live web search results. Use both to give a comprehensive answer. "
                "Clearly indicate when information comes from the web vs. the document."
            )
        elif has_web:
            instructions = (
                "Answer based on the live web search results below. "
                "Cite sources where relevant."
            )
        else:
            instructions = (
                "Answer the user's input using the document context below or by continuing the conversation based on the chat history. "
                "If the user asks a specific question about the document that isn't answered in the context, you may say it's not explicitly covered, "
                "but still try to respond helpfully to conversational inputs."
            )

        prompt = (
            f"{instructions}\n\n"
            f"{context_block}\n\n"
            f"Question: {question}"
        )

        return call_groq(
            prompt, api_key=api_key,
            system="You are a precise, helpful assistant. Answer based on the provided context.",
            history=history
        )


# Singleton
rag_instance = ContentRAG()