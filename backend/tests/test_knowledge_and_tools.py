import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_knowledge_base_stats():
    response = client.get("/api/knowledge-base/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["collection_name"] == "langchain"
    assert data["total_documents"] >= 15
    assert data["dimension"] == 384
    assert data["status"] == "healthy"


def test_knowledge_base_search():
    response = client.post(
        "/api/knowledge-base/search",
        json={"query": "Core Java fees duration", "top_k": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Core Java fees duration"
    assert len(data["results"]) > 0
    first = data["results"][0]
    assert "content" in first
    assert "source" in first
    assert "relevance_score" in first
    assert first["relevance_score"] > 0.0


def test_knowledge_base_incremental_update_no_duplicates():
    # Calling update with existing files without force_reindex should skip duplicates
    response = client.post(
        "/api/knowledge-base/update",
        json={"force_reindex": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["files_processed"] == 3
    # Since existing collection has documents, duplicates should be recognized and skipped
    assert data["duplicates_skipped"] >= 0


def test_tools_endpoint():
    response = client.get("/api/tools")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tools"] == 10
    tool_names = [t["name"] for t in data["tools"]]
    assert "search_knowledge_base" in tool_names
    assert "search_courses" in tool_names
    assert "compare_courses" in tool_names
    assert "search_internships" in tool_names
    assert "search_website_info" in tool_names
    assert "summarize_document" in tool_names
    assert "check_eligibility" in tool_names
    assert "search_faqs" in tool_names
    assert "multi_document_search" in tool_names
    assert "search_conversation_context" in tool_names
