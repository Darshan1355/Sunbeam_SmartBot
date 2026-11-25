"""
Retriever service for semantic document retrieval with scoring,
threshold filtering, source citation, and metadata enhancement.
"""
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.rag.vectorstore import ChromaVectorStoreManager, get_vectorstore_manager

logger = get_logger("app.rag.retriever")


class RetrievedChunk(BaseModel):
    """Structured representation of a retrieved document chunk."""

    content: str
    source: str
    chunk_index: Optional[int] = None
    distance: float
    relevance_score: float = Field(
        ..., description="Normalized similarity score in range [0.0, 1.0], where 1.0 is highest"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    """Aggregate result from retrieval operation."""

    query: str
    total_chunks: int
    chunks: List[RetrievedChunk]
    sources: List[str]
    context_text: str


class RetrievalService:
    """
    High-level retrieval service providing semantic search, MMR retrieval,
    score normalization, and metadata filtering.
    """

    def __init__(self, vectorstore_mgr: Optional[ChromaVectorStoreManager] = None):
        self.vectorstore_mgr = vectorstore_mgr or get_vectorstore_manager()

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        score_threshold: float = 0.25,
        search_mode: str = "similarity",  # 'similarity' or 'mmr'
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> RetrievalResult:
        """
        Executes document retrieval with scoring and source extraction.

        Distance in Chroma (L2 space): smaller = more similar.
        Normalized score = 1.0 / (1.0 + distance).
        """
        if not query or not query.strip():
            return RetrievalResult(
                query=query,
                total_chunks=0,
                chunks=[],
                sources=[],
                context_text="",
            )

        logger.info(f"Retrieving for query: '{query[:80]}' (top_k={top_k}, mode={search_mode})")

        raw_results = []
        fetch_k = max(top_k * 3, 15)
        if search_mode == "mmr":
            # MMR search
            docs = self.vectorstore_mgr.mmr_search(
                query=query,
                k=top_k,
                fetch_k=max(30, fetch_k),
                filter=filter_metadata,
            )
            for doc in docs:
                raw_results.append((doc, 0.5))
        else:
            # Similarity with scores using expanded candidate pool for hybrid ranking
            raw_results = self.vectorstore_mgr.similarity_search_with_score(
                query=query,
                k=fetch_k,
                filter=filter_metadata,
            )

        retrieved_chunks: List[RetrievedChunk] = []
        sources_set = set()

        # Extract meaningful terms from query for keyword boosting
        query_words = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 2]
        stopwords = {"what", "which", "where", "when", "does", "have", "with", "from", "about", "tell", "show", "give", "sunbeam", "institute", "information"}
        keywords = [w for w in query_words if w not in stopwords]

        for doc, distance in raw_results:
            # Normalized relevance score: 1.0 / (1.0 + distance)
            relevance = round(1.0 / (1.0 + max(0.0, distance)), 4)
            
            # Hybrid boost: reward exact keyword presence in chunk text
            if keywords:
                content_lower = doc.page_content.lower()
                matches = sum(1 for kw in keywords if kw in content_lower)
                boost = (matches / len(keywords)) * 0.25
                relevance = min(1.0, round(relevance + boost, 4))

            if relevance < score_threshold and search_mode != "mmr":
                continue

            src = doc.metadata.get("source", "unknown")
            sources_set.add(src)

            retrieved_chunks.append(
                RetrievedChunk(
                    content=doc.page_content.strip(),
                    source=src,
                    chunk_index=doc.metadata.get("chunk_index"),
                    distance=round(distance, 4),
                    relevance_score=relevance,
                    metadata=doc.metadata,
                )
            )

        # Sort by boosted relevance score descending and take top_k
        retrieved_chunks.sort(key=lambda x: x.relevance_score, reverse=True)
        retrieved_chunks = retrieved_chunks[:top_k]

        context_parts = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            context_parts.append(f"[Source {i}: {chunk.source}]\n{chunk.content}")
        context_text = "\n\n---\n\n".join(context_parts)

        return RetrievalResult(
            query=query,
            total_chunks=len(retrieved_chunks),
            chunks=retrieved_chunks,
            sources=sorted(list(sources_set)),
            context_text=context_text,
        )


_retrieval_service_instance: Optional[RetrievalService] = None


def get_retrieval_service() -> RetrievalService:
    """Singleton provider for RetrievalService."""
    global _retrieval_service_instance
    if _retrieval_service_instance is None:
        _retrieval_service_instance = RetrievalService()
    return _retrieval_service_instance
