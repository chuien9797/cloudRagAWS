import re
import nltk
from nltk.tokenize import sent_tokenize
from sentence_transformers import SentenceTransformer, CrossEncoder
import chromadb
from rank_bm25 import BM25Okapi
import logging

logger = logging.getLogger(__name__)


nltk.download("punkt",     quiet=True)
nltk.download("punkt_tab", quiet=True)


# MODELS
embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
reranker        = CrossEncoder("cross-encoder/ms-marco-MiniLM-L6-v2")



client     = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="rag_docs")


def chunk_text(text: str, max_tokens: int = 200) -> list[str]:
    try:
        sentences = sent_tokenize(text)
    except Exception:
        sentences = text.split(". ")

    chunks      = []
    current     = []
    current_len = 0

    for s in sentences:
        s_len = len(s.split())
        if current_len + s_len > max_tokens:
            if current:
                chunks.append(" ".join(current))
            current     = [s]
            current_len = s_len
        else:
            current.append(s)
            current_len += s_len

    if current:
        chunks.append(" ".join(current))

    return [c.strip() for c in chunks if c.strip()]



def is_valid_chunk(text: str) -> bool:
    if len(text.split()) < 8:
        return False
    alpha_ratio = sum(c.isalpha() for c in text) / max(len(text), 1)
    if alpha_ratio < 0.40:
        return False
    citation_count = len(re.findall(r'\[\d+\]', text))
    word_count     = len(text.split())
    if citation_count > 3 and (citation_count / max(word_count, 1)) > 0.05:
        return False
    if "arxiv preprint arxiv" in text.lower():
        return False
    bad = ["obj\n", "stream\n", "xref\n", "endobj"]
    t   = text.lower()
    if any(b in t for b in bad):
        return False
    return True



def add_document(doc_id: str, pages: list[dict], metadata: dict = None) -> int:
    """
    pages: list of {"text": str, "page_number": int | None}
    Returns total number of chunks added to ChromaDB.
    """
    if not pages:
        raise ValueError("No pages provided")

    added        = 0
    chunk_index  = 0   # global chunk counter across all pages

    for page in pages:
        page_text   = page.get("text", "")
        page_number = page.get("page_number")

        if not page_text.strip():
            continue

        chunks = chunk_text(page_text)

        for page_chunk_index, chunk in enumerate(chunks, start=1):
            if not is_valid_chunk(chunk):
                chunk_index += 1
                continue

            embedding = embedding_model.encode(chunk).tolist()

            collection.add(
                documents=[chunk],
                embeddings=[embedding],
                ids=[f"{doc_id}_{chunk_index}"],
                metadatas=[{
                    **(metadata or {}),
                    "doc_id":      doc_id,
                    "chunk_id":    chunk_index,
                    "page_number": page_number,
                    "paragraph_number": page_chunk_index,
                }]
            )
            added       += 1
            chunk_index += 1

    if added == 0:
        raise ValueError("All chunks were filtered out — check document quality")

    return added


# BM25
def bm25_search(query: str, pairs: list[tuple]) -> list[tuple]:
    if not pairs:
        return []
    docs      = [p[0] for p in pairs]
    tokenized = [d.split() for d in docs]
    bm25      = BM25Okapi(tokenized)
    scores    = bm25.get_scores(query.split())
    ranked    = sorted(zip(pairs, scores), key=lambda x: x[1], reverse=True)
    return [pair for pair, _ in ranked]



def hybrid_retrieve(query: str, top_k: int = 6, doc_id: str = None):
    total_docs = collection.count()
    if total_docs == 0:
        return [], [], []

    n_results       = min(top_k * 3, 20, total_docs)
    query_embedding = embedding_model.encode(query).tolist()
    where_filter    = {"doc_id": {"$eq": doc_id}} if doc_id else None

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter
        )
    except Exception as e:
        logger.error(f"ChromaDB query failed: {e}")
        return [], [], []

    raw_docs  = results["documents"][0] if results["documents"] else []
    raw_metas = results["metadatas"][0]  if results.get("metadatas") else []

    paired = [
        (doc, meta)
        for doc, meta in zip(raw_docs, raw_metas)
        if is_valid_chunk(doc)
    ]

    if not paired:
        return [], [], []

    paired = bm25_search(query, paired)

    seen, deduped = set(), []
    for doc, meta in paired:
        key = doc[:80]
        if key not in seen:
            seen.add(key)
            deduped.append((doc, meta))

    if deduped:
        docs_only = [p[0] for p in deduped]
        scores = reranker.predict([[query, d] for d in docs_only])
        ranked_pairs = sorted(zip(deduped, scores), key=lambda x: x[1], reverse=True)
        deduped = [pair for pair, _ in ranked_pairs]
        ranked_scores = [float(score) for _, score in ranked_pairs]
    else:
        ranked_scores = []

    final = deduped[:top_k]
    final_scores = ranked_scores[:top_k] if ranked_scores else [0.0] * len(final)
    return [p[0] for p in final], [p[1] for p in final], final_scores
