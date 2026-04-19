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

try:
    import certifi
    ssl._create_default_https_context = ssl.create_default_context
except Exception:
    pass

_embed_model = None

def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        print("[Embeddings] Loading local model …")
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        print("[Embeddings] Ready.")
    return _embed_model

GROQ_MODEL = "llama-3.3-70b-versatile"


def web_search(query: str, max_results: int = 5) -> list[dict]:
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return results
    except Exception as e:
        print(f"[WebSearch] Error: {e}")
        return []


def format_web_results(results: list[dict]) -> str:
    if not results:
        return "No web results found."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r.get('title', 'No title')}\n{r.get('body', '')}\nSource: {r.get('href', '')}")
    return "\n\n".join(lines)


def call_groq(prompt: str, api_key: str, system: str = "You are a helpful AI assistant.", retries: int = 2, history: list = None) -> str:
    if not api_key or not api_key.strip():
        raise ValueError("No API key provided. Please enter your key in the app.")

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


def extract_text_from_pdf(file_data: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_text_from_txt(file_data: bytes) -> str:
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return file_data.decode(enc)
        except UnicodeDecodeError:
            continue
    return file_data.decode("utf-8", errors="replace")


def chunk_text(text: str, size: int = 500, overlap: int = 100) -> List[str]:
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        chunks.append(" ".join(words[start: start + size]))
        start += size - overlap
    return chunks


class ContentRAG:
    def __init__(self):
        self.index = None
        self.chunks: List[str] = []
        self.source_text = ""
        self.filename = ""

    def _build_rag(self, text: str) -> Tuple[bool, str]:
        self.source_text = text
        self.chunks = chunk_text(text)
        if not self.chunks:
            return False, "Document has no usable text."
        embeddings = np.array(_get_embed_model().encode(self.chunks)).astype("float32")
        self.index = faiss.IndexFlatL2(embeddings.shape[1])
        self.index.add(embeddings)
        return True, f"Processed {len(self.chunks)} chunks from '{self.filename}'."

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
        doc_context = ""
        if self.index:
            q_emb = np.array(_get_embed_model().encode([question])).astype("float32")
            _, indices = self.index.search(q_emb, k=4)
            doc_context = "\n\n".join(
                self.chunks[i] for i in indices[0] if i < len(self.chunks)
            )
        elif not web_search_enabled:
            return "Please upload and process a document first."

        web_context = ""
        if web_search_enabled:
            print(f"[WebSearch] Searching for: {question}")
            results = web_search(question)
            web_context = format_web_results(results)

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
                "Answer the user's input using the document context below or by continuing "
                "the conversation based on the chat history. If the user asks a specific question "
                "about the document that isn't answered in the context, you may say it's not "
                "explicitly covered, but still try to respond helpfully to conversational inputs."
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


rag_instance = ContentRAG()