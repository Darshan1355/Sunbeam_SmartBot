from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class KnowledgeBaseStatsResponse(BaseModel):
    collection_name: str
    persist_directory: str
    total_documents: int
    dimension: int
    sources_breakdown: Dict[str, int] = Field(default_factory=dict)
    status: str


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query string")
    top_k: int = Field(default=4, ge=1, le=20, description="Number of results to retrieve")
    score_threshold: float = Field(default=0.2, ge=0.0, le=1.0, description="Minimum relevance score threshold")
    search_mode: Literal["similarity", "mmr"] = Field(
        default="similarity", description="Retrieval algorithm: similarity or mmr"
    )
    filter_source: Optional[str] = Field(default=None, description="Filter results by source filename")


class ChunkResultItem(BaseModel):
    content: str
    source: str
    relevance_score: float
    distance: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeSearchResponse(BaseModel):
    query: str
    total_results: int
    sources: List[str]
    results: List[ChunkResultItem]


class KnowledgeUpdateRequest(BaseModel):
    force_reindex: bool = Field(default=False, description="Whether to clear and reindex documents")
    file_paths: Optional[List[str]] = Field(default=None, description="Specific files to reindex")


class KnowledgeUpdateResponse(BaseModel):
    files_processed: int
    total_chunks_created: int
    new_chunks_added: int
    duplicates_skipped: int
    total_collection_count: int
