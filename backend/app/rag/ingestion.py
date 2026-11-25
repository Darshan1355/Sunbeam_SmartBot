"""
Document ingestion pipeline for loading, cleaning, chunking,
duplicate checking, and incrementally updating ChromaDB.
"""
import hashlib
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.logging import get_logger
from app.rag.vectorstore import ChromaVectorStoreManager, get_vectorstore_manager

logger = get_logger("app.rag.ingestion")


def clean_text(text: str) -> str:
    """Preprocess and normalize raw document text."""
    if not text:
        return ""
    # Normalize Windows CRLF to LF
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Clean up repetitive excessive blank lines
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    # Strip trailing and leading whitespace
    return text.strip()


def calculate_content_hash(text: str) -> str:
    """Calculates deterministic MD5 hash for duplicate detection."""
    return hashlib.md5(text.strip().encode("utf-8")).hexdigest()


class DocumentIngestionPipeline:
    """
    Handles robust incremental ingestion of Sunbeam text documents into ChromaDB.
    """

    DEFAULT_FILES = [
        "data/documents/sunbeam_about.txt",
        "data/documents/sunbeam_internship.txt",
        "data/documents/sunbeam_courses.txt",
        "data/documents/sunbeam_cdac_courses.txt",
        "data/documents/sunbeam_contact_branches.txt",
    ]

    def __init__(
        self,
        vectorstore_mgr: Optional[ChromaVectorStoreManager] = None,
        chunk_size: int = 700,
        chunk_overlap: int = 80,
    ):
        self.vectorstore_mgr = vectorstore_mgr or get_vectorstore_manager()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            separators=[
                "\n----------------------------------------------------------------------------------------------------\n",
                "\n====================================================================================================\n",
                "\nSECTION: ",
                "\nTABLE: ",
                "\n\n",
                "\n",
                " ",
            ],
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

    def resolve_file_path(self, relative_path: str) -> Optional[Path]:
        """Resolves a document path from the project or backend directory."""
        path = Path(relative_path)
        if path.is_file():
            return path.resolve()

        project_root = Path(__file__).resolve().parents[3]
        for root in (project_root, project_root / "backend"):
            candidate = (root / path).resolve()
            if candidate.is_file():
                return candidate

        return None

    def load_document(self, file_path_str: str) -> Optional[Document]:
        """Loads and cleans a single text document."""
        resolved = self.resolve_file_path(file_path_str)
        if not resolved:
            logger.warning(f"File not found: {file_path_str}")
            return None

        try:
            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                raw_content = f.read()

            cleaned = clean_text(raw_content)
            if not cleaned:
                logger.warning(f"File {file_path_str} is empty after cleaning")
                return None

            doc_type = "general"
            if "about" in file_path_str:
                doc_type = "about"
            elif "internship" in file_path_str:
                doc_type = "internship"
            elif "courses" in file_path_str:
                doc_type = "courses"

            return Document(
                page_content=cleaned,
                metadata={
                    "source": file_path_str,
                    "filename": resolved.name,
                    "doc_type": doc_type,
                    "file_size": len(cleaned),
                },
            )
        except Exception as e:
            logger.error(f"Error reading file {file_path_str}: {str(e)}")
            return None

    def get_existing_hashes(self) -> set:
        """Retrieves existing content hashes from Chroma collection to avoid duplicate embeddings."""
        try:
            col = self.vectorstore_mgr.get_collection()
            data = col.get(include=["metadatas", "documents"])
            hashes = set()
            for meta, doc in zip(data.get("metadatas", []), data.get("documents", [])):
                if meta and "content_hash" in meta:
                    hashes.add(meta["content_hash"])
                elif doc:
                    # Fallback compute hash on document text
                    hashes.add(calculate_content_hash(doc))
            return hashes
        except Exception as e:
            logger.warning(f"Could not retrieve existing hashes from ChromaDB: {str(e)}")
            return set()

    def ingest_files(
        self,
        file_paths: Optional[List[str]] = None,
        force_reindex: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes incremental ingestion of documents.
        Checks for duplicates and preserves existing embeddings.
        """
        target_files = file_paths or self.DEFAULT_FILES
        existing_hashes = set() if force_reindex else self.get_existing_hashes()

        total_loaded = 0
        total_chunks = 0
        added_chunks = 0
        skipped_duplicates = 0

        chunks_to_add: List[Document] = []
        ids_to_add: List[str] = []

        for f_path in target_files:
            doc = self.load_document(f_path)
            if not doc:
                continue
            total_loaded += 1

            if force_reindex:
                # Delete existing documents for this source if re-indexing
                self.vectorstore_mgr.delete_by_source(f_path)

            file_chunks = self.text_splitter.split_documents([doc])
            total_chunks += len(file_chunks)

            for idx, chunk in enumerate(file_chunks):
                content_hash = calculate_content_hash(chunk.page_content)

                if content_hash in existing_hashes:
                    skipped_duplicates += 1
                    continue

                # Enrich metadata
                chunk.metadata["chunk_index"] = idx
                chunk.metadata["content_hash"] = content_hash
                chunk.metadata["char_count"] = len(chunk.page_content)

                # Deterministic chunk ID
                clean_name = Path(f_path).stem
                chunk_id = f"{clean_name}_{idx}_{content_hash[:8]}"

                chunks_to_add.append(chunk)
                ids_to_add.append(chunk_id)
                existing_hashes.add(content_hash)
                added_chunks += 1

        if chunks_to_add:
            logger.info(f"Adding {len(chunks_to_add)} new chunks to ChromaDB...")
            self.vectorstore_mgr.add_documents(chunks_to_add, ids=ids_to_add)

        return {
            "files_processed": total_loaded,
            "total_chunks_created": total_chunks,
            "new_chunks_added": added_chunks,
            "duplicates_skipped": skipped_duplicates,
            "total_collection_count": self.vectorstore_mgr.get_stats().get("total_documents", 0),
        }


_ingestion_pipeline_instance: Optional[DocumentIngestionPipeline] = None


def get_ingestion_pipeline() -> DocumentIngestionPipeline:
    """Singleton provider for DocumentIngestionPipeline."""
    global _ingestion_pipeline_instance
    if _ingestion_pipeline_instance is None:
        _ingestion_pipeline_instance = DocumentIngestionPipeline()
    return _ingestion_pipeline_instance
