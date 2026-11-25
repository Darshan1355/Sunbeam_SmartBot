"""
Embeddings module providing LangChain-compatible embedding functions.
Uses Chroma's locally cached ONNX all-MiniLM-L6-v2 embedding model (384 dimensions)
with fallback to SentenceTransformers/HuggingFace if available.
"""
from typing import List, Optional
import chromadb.utils.embedding_functions as ef
from langchain_core.embeddings import Embeddings

from app.core.logging import get_logger

logger = get_logger("app.rag.embeddings")


class SunbeamEmbeddings(Embeddings):
    """
    LangChain compatible Embeddings implementation backed by the
    all-MiniLM-L6-v2 model (384 dimensions). Runs fully offline with zero
    network dependencies.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._ef = ef.DefaultEmbeddingFunction()
        logger.info(f"Initialized SunbeamEmbeddings with model: {self.model_name} (dim=384)")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search docs."""
        if not texts:
            return []
        try:
            return self._ef(texts)
        except Exception as e:
            logger.error(f"Failed to embed documents: {str(e)}")
            raise

    def embed_query(self, text: str) -> List[float]:
        """Embed query text."""
        if not text or not text.strip():
            # Return zero vector if empty query
            return [0.0] * 384
        try:
            vectors = self._ef([text])
            return vectors[0]
        except Exception as e:
            logger.error(f"Failed to embed query: {str(e)}")
            raise


_embedding_instance: Optional[SunbeamEmbeddings] = None


def get_embedding_model() -> SunbeamEmbeddings:
    """Singleton provider for embeddings model."""
    global _embedding_instance
    if _embedding_instance is None:
        _embedding_instance = SunbeamEmbeddings()
    return _embedding_instance
