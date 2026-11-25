"""
Vectorstore module managing ChromaDB persistent vector database.
Preserves existing 'langchain' collection and embeddings.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.embeddings import get_embedding_model

logger = get_logger("app.rag.vectorstore")


class ChromaVectorStoreManager:
    """
    Manages persistent ChromaDB vector store operations.
    Supports similarity search, MMR, document filtering, and collection statistics.
    """

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: str = "langchain",
    ):
        settings = get_settings()
        raw_dir = persist_directory or settings.CHROMA_PERSIST_DIR

        resolved_path = Path(raw_dir)
        if not resolved_path.is_absolute():
            project_root = Path(__file__).resolve().parents[3]
            backend_root = project_root / "backend"
            project_candidate = (project_root / resolved_path).resolve()
            backend_candidate = (backend_root / resolved_path).resolve()
            resolved_path = (
                project_candidate if project_candidate.exists() else backend_candidate
            )

        self.persist_directory = str(resolved_path)
        self.collection_name = collection_name
        self.embedding_model = get_embedding_model()

        logger.info(f"Connecting to ChromaDB at: {self.persist_directory} [Collection: {self.collection_name}]")

        self._client = chromadb.PersistentClient(path=self.persist_directory)
        self._vector_store = Chroma(
            client=self._client,
            collection_name=self.collection_name,
            embedding_function=self.embedding_model,
        )

    @property
    def vector_store(self) -> Chroma:
        return self._vector_store

    def get_collection(self):
        """Returns the underlying raw chromadb collection."""
        return self._client.get_collection(
            name=self.collection_name,
            embedding_function=self.embedding_model._ef,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Returns diagnostic statistics for the vector database."""
        try:
            col = self.get_collection()
            count = col.count()
            data = col.get(include=["metadatas"])
            sources = {}
            for meta in data.get("metadatas", []):
                if meta and "source" in meta:
                    src = meta["source"]
                    sources[src] = sources.get(src, 0) + 1

            return {
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory,
                "total_documents": count,
                "sources_breakdown": sources,
                "dimension": 384,
                "status": "healthy" if count > 0 else "empty",
            }
        except Exception as e:
            logger.error(f"Failed to fetch ChromaDB stats: {str(e)}")
            return {
                "collection_name": self.collection_name,
                "error": str(e),
                "total_documents": 0,
                "status": "unhealthy",
            }

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """Perform standard semantic similarity search."""
        if not query or not query.strip():
            return []
        try:
            return self._vector_store.similarity_search(query, k=k, filter=filter)
        except Exception as e:
            logger.error(f"Similarity search error: {str(e)}")
            return []

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Document, float]]:
        """Perform similarity search with distance scores."""
        if not query or not query.strip():
            return []
        try:
            return self._vector_store.similarity_search_with_score(query, k=k, filter=filter)
        except Exception as e:
            logger.error(f"Similarity search with score error: {str(e)}")
            return []

    def mmr_search(
        self,
        query: str,
        k: int = 4,
        fetch_k: int = 20,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """Perform Maximal Marginal Relevance search for high diversity."""
        if not query or not query.strip():
            return []
        try:
            return self._vector_store.max_marginal_relevance_search(
                query, k=k, fetch_k=fetch_k, filter=filter
            )
        except Exception as e:
            logger.error(f"MMR search error: {str(e)}")
            return []

    def add_documents(self, documents: List[Document], ids: Optional[List[str]] = None) -> List[str]:
        """Add documents to ChromaDB."""
        if not documents:
            return []
        try:
            doc_ids = self._vector_store.add_documents(documents=documents, ids=ids)
            logger.info(f"Successfully added {len(doc_ids)} documents to ChromaDB")
            return doc_ids
        except Exception as e:
            logger.error(f"Failed to add documents to ChromaDB: {str(e)}")
            raise

    def delete_by_ids(self, ids: List[str]) -> None:
        """Deletes documents by their unique Chroma IDs."""
        if not ids:
            return
        try:
            self._vector_store.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents from ChromaDB")
        except Exception as e:
            logger.error(f"Failed to delete documents by IDs: {str(e)}")
            raise

    def delete_by_source(self, source_path: str) -> int:
        """Deletes all chunks associated with a specific source file."""
        try:
            col = self.get_collection()
            results = col.get(where={"source": source_path})
            ids_to_delete = results.get("ids", [])
            if ids_to_delete:
                col.delete(ids=ids_to_delete)
                logger.info(f"Deleted {len(ids_to_delete)} chunks matching source '{source_path}'")
            return len(ids_to_delete)
        except Exception as e:
            logger.error(f"Failed to delete documents by source '{source_path}': {str(e)}")
            raise


_vector_store_manager: Optional[ChromaVectorStoreManager] = None


def get_vectorstore_manager() -> ChromaVectorStoreManager:
    """Singleton accessor for ChromaVectorStoreManager."""
    global _vector_store_manager
    if _vector_store_manager is None:
        _vector_store_manager = ChromaVectorStoreManager()
    return _vector_store_manager
