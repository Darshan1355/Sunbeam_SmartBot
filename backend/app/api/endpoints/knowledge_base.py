"""
Endpoints for knowledge base status, semantic search, and document ingestion.
"""
from fastapi import APIRouter, Depends, status
from starlette.concurrency import run_in_threadpool

from app.rag.ingestion import DocumentIngestionPipeline, get_ingestion_pipeline
from app.rag.retriever import RetrievalService, get_retrieval_service
from app.rag.vectorstore import ChromaVectorStoreManager, get_vectorstore_manager
from app.schemas.knowledge import (
    ChunkResultItem,
    KnowledgeBaseStatsResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeUpdateRequest,
    KnowledgeUpdateResponse,
)

router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base & RAG"])


@router.get(
    "/stats",
    response_model=KnowledgeBaseStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Knowledge Base Statistics",
    description="Returns persistent ChromaDB collection size, document breakdown, and embedding dimension.",
)
async def get_knowledge_base_stats(
    vector_mgr: ChromaVectorStoreManager = Depends(get_vectorstore_manager),
) -> KnowledgeBaseStatsResponse:
    stats = await run_in_threadpool(vector_mgr.get_stats)
    return KnowledgeBaseStatsResponse(
        collection_name=stats.get("collection_name", "langchain"),
        persist_directory=stats.get("persist_directory", ""),
        total_documents=stats.get("total_documents", 0),
        dimension=stats.get("dimension", 384),
        sources_breakdown=stats.get("sources_breakdown", {}),
        status=stats.get("status", "healthy"),
    )


@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic Search Knowledge Base",
    description="Executes semantic similarity or MMR search against indexed Sunbeam documents.",
)
async def search_knowledge_base_endpoint(
    req: KnowledgeSearchRequest,
    retriever: RetrievalService = Depends(get_retrieval_service),
) -> KnowledgeSearchResponse:
    filter_meta = {"source": req.filter_source} if req.filter_source else None

    result = await run_in_threadpool(
        retriever.retrieve,
        query=req.query,
        top_k=req.top_k,
        score_threshold=req.score_threshold,
        search_mode=req.search_mode,
        filter_metadata=filter_meta,
    )

    items = [
        ChunkResultItem(
            content=c.content,
            source=c.source,
            relevance_score=c.relevance_score,
            distance=c.distance,
            metadata=c.metadata,
        )
        for c in result.chunks
    ]

    return KnowledgeSearchResponse(
        query=req.query,
        total_results=len(items),
        sources=result.sources,
        results=items,
    )


@router.post(
    "/update",
    response_model=KnowledgeUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Incremental Knowledge Base Ingestion",
    description="Loads, chunks, and incrementally updates ChromaDB with duplicate detection.",
)
async def update_knowledge_base(
    req: KnowledgeUpdateRequest,
    ingestion: DocumentIngestionPipeline = Depends(get_ingestion_pipeline),
) -> KnowledgeUpdateResponse:
    result = await run_in_threadpool(
        ingestion.ingest_files,
        file_paths=req.file_paths,
        force_reindex=req.force_reindex,
    )

    return KnowledgeUpdateResponse(
        files_processed=result["files_processed"],
        total_chunks_created=result["total_chunks_created"],
        new_chunks_added=result["new_chunks_added"],
        duplicates_skipped=result["duplicates_skipped"],
        total_collection_count=result["total_collection_count"],
    )
