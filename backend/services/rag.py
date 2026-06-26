"""
services/rag.py — ChromaDB RAG service.

Stores syllabus content and GATE PYQs as embeddings.
Agents retrieve relevant context before generating questions.
"""
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from backend.config import CHROMA_PATH

_embed_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

_client = chromadb.PersistentClient(path=CHROMA_PATH)

# Two collections: syllabus topics and GATE previous year questions
syllabus_col  = _client.get_or_create_collection("syllabus",  embedding_function=_embed_fn)
gate_pyq_col  = _client.get_or_create_collection("gate_pyq",  embedding_function=_embed_fn)


def add_syllabus(topic_id: str, topic: str, content: str, subject: str, unit: int):
    """Ingest a syllabus topic into the vector store."""
    syllabus_col.upsert(
        ids=[topic_id],
        documents=[content],
        metadatas=[{"topic": topic, "subject": subject, "unit": unit}],
    )


def add_gate_pyq(qid: str, question: str, answer: str, subject: str, year: int):
    """Ingest a GATE previous year question."""
    gate_pyq_col.upsert(
        ids=[qid],
        documents=[f"Q: {question}\nA: {answer}"],
        metadatas=[{"subject": subject, "year": year}],
    )


def get_syllabus_context(topic: str, top_k: int = 4) -> str:
    """Retrieve the most relevant syllabus chunks for a topic."""
    results = syllabus_col.query(query_texts=[topic], n_results=top_k)
    docs = results.get("documents", [[]])[0]
    return "\n\n".join(docs) if docs else ""


def get_gate_examples(topic: str, top_k: int = 3) -> str:
    """Retrieve similar GATE questions for reference patterns."""
    results = gate_pyq_col.query(query_texts=[topic], n_results=top_k)
    docs = results.get("documents", [[]])[0]
    return "\n\n".join(docs) if docs else ""
