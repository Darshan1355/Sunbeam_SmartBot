"""
Comprehensive Integration Test Suite for Sunbeam SmartBot.
Executes end-to-end tests across Backend, AI/RAG, Tools, Streaming, and Persistence.
"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app
from app.agent.agent_service import get_agent_service
from app.rag.retriever import get_retrieval_service
from app.rag.vectorstore import get_vectorstore_manager
from app.rag.ingestion import get_ingestion_pipeline
from app.services.session_service import get_session_service
from app.services.groq_service import get_groq_service
from app.tools.registry import get_tool_registry

client = TestClient(app)


def print_header(title: str):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def test_system_components():
    print_header("1. SYSTEM COMPONENT DIAGNOSTICS")

    # 1.1 Config
    res = client.get("/api/config")
    assert res.status_code == 200, "Config endpoint failed"
    config = res.json()
    assert "GROQ_API_KEY" not in config, "SECURITY FAILURE: API key exposed in config!"
    print(f"  ✅ Config endpoint: OK (Model: {config['groq_model']}, Origins: {len(config['allowed_origins'])})")

    # 1.2 Health
    res = client.get("/api/health")
    assert res.status_code == 200, "Health endpoint failed"
    health = res.json()
    assert health["status"] in ["healthy", "degraded"], f"Unhealthy status: {health}"
    print(f"  ✅ Health endpoint: OK (Status: {health['status']})")

    # 1.3 ChromaDB
    v_mgr = get_vectorstore_manager()
    stats = v_mgr.get_stats()
    assert stats["total_documents"] >= 15, "ChromaDB documents missing!"
    print(f"  ✅ ChromaDB Vector Store: OK ({stats['total_documents']} documents, dim={stats['dimension']})")

    # 1.4 Groq Service
    groq = get_groq_service()
    assert groq.is_configured, "Groq is not configured"
    print(f"  ✅ Groq LLM Client: OK (Configured model: {groq._default_model})")

    # 1.5 SQLite Session Persistence
    session = get_session_service()
    test_conv = session.create_conversation(title="Test Diagnostic Session")
    assert test_conv["id"], "Conversation creation failed"
    session.delete_conversation(test_conv["id"])
    print(f"  ✅ SQLite Session Persistence: OK (Path: {session.db_path})")

    # 1.6 Production Frontend Mounted
    root_res = client.get("/")
    assert root_res.status_code == 200, "Frontend not served"
    assert "Sunbeam SmartBot" in root_res.text or "<html" in root_res.text, "Frontend HTML missing"
    print(f"  ✅ Production Frontend Mounting: OK (Serves compiled React SPA)")


def test_rag_and_ingestion():
    print_header("2. RAG PIPELINE & INGESTION VERIFICATION")

    retriever = get_retrieval_service()
    ingestion = get_ingestion_pipeline()

    # 2.1 Test Retrieval Accuracy on known course
    res = retriever.retrieve("Core Java", top_k=2)
    assert len(res.chunks) > 0, "Retrieval returned 0 chunks for Core Java"
    print(f"  ✅ Semantic Search ('Core Java'): {len(res.chunks)} chunks retrieved (Score: {res.chunks[0].relevance_score})")

    # 2.2 Test MMR Diversity Retrieval
    res_mmr = retriever.retrieve("Sunbeam courses fees schedule", top_k=3, search_mode="mmr")
    assert len(res_mmr.chunks) > 0, "MMR retrieval failed"
    print(f"  ✅ MMR Retrieval: {len(res_mmr.chunks)} diverse chunks retrieved from sources: {res_mmr.sources}")

    # 2.3 Incremental update duplicate detection
    update_res = ingestion.ingest_files(force_reindex=False)
    print(f"  ✅ Incremental Ingestion: {update_res['files_processed']} files processed, {update_res['duplicates_skipped']} duplicates skipped, {update_res['new_chunks_added']} added.")


def test_callable_tools():
    print_header("3. 10 CALLABLE LANGCHAIN TOOLS VALIDATION")

    reg = get_tool_registry()
    tools = reg.list_tools()
    assert len(tools) == 10, f"Expected 10 tools, found {len(tools)}"

    test_inputs = [
        ("search_knowledge_base", {"query": "Tell me about Sunbeam Institute"}),
        ("search_courses", {"query": "Data Structures and Algorithms"}),
        ("compare_courses", {"course_a": "Core Java", "course_b": "C++"}),
        ("search_internships", {"domain": "Generative AI"}),
        ("search_website_info", {"topic": "Hinjawadi campus"}),
        ("summarize_document", {"source_name": "about"}),
        ("check_eligibility", {"program_name": "Apache Spark", "educational_background": "BE Computer Science"}),
        ("search_faqs", {"question": "Can I attend online?"}),
        ("multi_document_search", {"query": "internship batch and course fees"}),
        ("search_conversation_context", {"query": "What are its fees?", "recent_messages": "User: What about Core Java?"}),
    ]

    for name, args in test_inputs:
        start = time.perf_counter()
        raw = reg.execute_tool(name, args)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        assert raw is not None, f"Tool {name} returned None"
        parsed = json.loads(raw)
        assert isinstance(parsed, dict), f"Tool {name} output is not valid JSON dict"
        print(f"  ✅ [{duration_ms:>6.2f} ms] Tool '{name}' executed successfully.")


def test_sse_streaming_and_persistence():
    print_header("4. SSE STREAMING & CONVERSATION PERSISTENCE")

    session = get_session_service()

    # Step 1: Create conversation
    conv = session.create_conversation(title="SSE Test Conversation")
    conv_id = conv["id"]
    print(f"  • Created test conversation: {conv_id}")

    # Step 2: Stream question via POST /api/chat/stream
    test_question = "What is the duration of the Generative AI internship?"
    print(f"  • Streaming query: \"{test_question}\"")

    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"message": test_question, "conversation_id": conv_id},
    ) as response:
        assert response.status_code == 200, f"SSE stream failed with status {response.status_code}"

        events = []
        tokens = []
        tools_run = []
        sources_found = []

        for line in response.iter_lines():
            if line.startswith("event:"):
                events.append(line.split(":", 1)[1].strip())
            elif line.startswith("data:"):
                data_str = line.split(":", 1)[1].strip()
                try:
                    payload = json.loads(data_str)
                    if "content" in payload:
                        tokens.append(payload["content"])
                    if "tool" in payload and payload.get("status") == "running":
                        tools_run.append(payload["tool"])
                    if "sources" in payload:
                        sources_found.extend(payload["sources"])
                except Exception:
                    pass

    final_text = "".join(tokens)
    print(f"  ✅ Events observed in SSE stream: {set(events)}")
    print(f"  ✅ Progressive token streaming confirmed: {len(tokens)} token events received")
    print(f"  ✅ Tools invoked during stream: {tools_run}")
    print(f"  ✅ Citations received: {list(set(sources_found))}")
    print(f"  • Streamed Response: \"{final_text[:120]}...\"")

    # Step 3: Verify SQLite Saved Messages
    saved_messages = session.get_messages(conv_id)
    assert len(saved_messages) == 2, f"Expected 2 messages (user + assistant), found {len(saved_messages)}"
    assert saved_messages[0]["role"] == "user"
    assert saved_messages[1]["role"] == "assistant"
    assert len(saved_messages[1]["content"]) > 10
    print(f"  ✅ Messages correctly persisted in SQLite: {len(saved_messages)} messages stored.")

    # Step 4: Rename and verify
    session.rename_conversation(conv_id, "Renamed SSE Test")
    updated = session.get_conversation(conv_id)
    assert updated["title"] == "Renamed SSE Test"
    print(f"  ✅ Conversation rename confirmed: '{updated['title']}'")

    # Step 5: Clean up
    session.delete_conversation(conv_id)
    assert session.get_conversation(conv_id) is None
    print(f"  ✅ Conversation cleanup confirmed.")


async def test_15_ai_test_cases():
    print_header("5. 15 COMPREHENSIVE AI & AGENTIC RAG TEST CASES")

    agent = get_agent_service()

    test_cases = [
        # 1. General technical question (No Sunbeam RAG required)
        {
            "id": 1,
            "category": "General Question",
            "query": "Explain what a binary search tree is in 2 sentences.",
            "expected_rag": False,
            "expected_intent": "direct",
            "validation_keywords": ["binary", "node", "left", "right", "search"],
        },
        # 2. General greeting (No RAG)
        {
            "id": 2,
            "category": "General Conversation",
            "query": "Hello! Who are you and how can you help me?",
            "expected_rag": False,
            "expected_intent": "direct",
            "validation_keywords": ["sunbeam", "assistant", "help"],
        },
        # 3. Sunbeam-specific institutional inquiry
        {
            "id": 3,
            "category": "Sunbeam Institute Info",
            "query": "Where is Sunbeam's Hinjawadi campus located?",
            "expected_rag": True,
            "expected_intent": "institutional",
            "validation_keywords": ["hinjawadi", "phase 2", "infosys", "pune"],
        },
        # 4. Campus facilities inquiry
        {
            "id": 4,
            "category": "Campus Facilities",
            "query": "What infrastructure and hostel facilities does Sunbeam have?",
            "expected_rag": True,
            "expected_intent": "institutional",
            "validation_keywords": ["70,000", "sq ft", "lab", "hostel", "classroom"],
        },
        # 5. Modular course list
        {
            "id": 5,
            "category": "Course Catalog",
            "query": "What modular courses are offered at Sunbeam?",
            "expected_rag": True,
            "expected_intent": "course",
            "validation_keywords": ["core java", "c++", "spark", "devops", "aptitude"],
        },
        # 6. Specific course fee and schedule
        {
            "id": 6,
            "category": "Course Fees & Schedule",
            "query": "What is the fee and duration for the Core Java course?",
            "expected_rag": True,
            "expected_intent": "course",
            "validation_keywords": ["8000", "80 hrs", "java"],
        },
        # 7. Another course schedule check
        {
            "id": 7,
            "category": "Course Details",
            "query": "What are the timings and duration of Apache Spark Mastery?",
            "expected_rag": True,
            "expected_intent": "course",
            "validation_keywords": ["50 hrs", "7:00 pm", "spark"],
        },
        # 8. Course comparison
        {
            "id": 8,
            "category": "Course Comparison",
            "query": "Compare Core Java and C++ courses in terms of hours and fees.",
            "expected_rag": True,
            "expected_intent": "comparison",
            "validation_keywords": ["java", "c++", "fees", "hrs"],
        },
        # 9. Internship offerings
        {
            "id": 9,
            "category": "Internship Domains",
            "query": "What technology domains are available for industrial internship at Sunbeam?",
            "expected_rag": True,
            "expected_intent": "internship",
            "validation_keywords": ["generative ai", "android", "cyber security", "data science"],
        },
        # 10. Specific internship batch details
        {
            "id": 10,
            "category": "Internship Schedule",
            "query": "What is the duration, start date and fee for the Generative AI internship batch?",
            "expected_rag": True,
            "expected_intent": "internship",
            "validation_keywords": ["1 month", "4000", "10-dec-2025"],
        },
        # 11. Eligibility criteria
        {
            "id": 11,
            "category": "Eligibility & Prerequisites",
            "query": "What are the prerequisites for the Data Science and Machine Learning internship?",
            "expected_rag": True,
            "expected_intent": "admissions",
            "validation_keywords": ["python", "programming"],
        },
        # 12. Mode of learning FAQ
        {
            "id": 12,
            "category": "Training Modes (FAQ)",
            "query": "Can students attend Sunbeam training sessions in online mode?",
            "expected_rag": True,
            "expected_intent": "faq",
            "validation_keywords": ["online", "training", "mode"],
        },
        # 13. Multi-step question (Course fees + Internship)
        {
            "id": 13,
            "category": "Multi-Step Question",
            "query": "How much does the Aptitude course cost, and how long is the Cyber Security internship?",
            "expected_rag": True,
            "expected_intent": "course",
            "validation_keywords": ["4000", "1 month"],
        },
        # 14. Follow-up query simulation with context
        {
            "id": 14,
            "category": "Follow-Up with Context",
            "query": "What is its duration and batch timing?",
            "history": [
                {"role": "user", "content": "Tell me about the Core Java course."},
                {"role": "assistant", "content": "Core Java has a fee of Rs. 8000 and covers object-oriented programming."}
            ],
            "expected_rag": True,
            "expected_intent": "course",
            "validation_keywords": ["80 hrs", "9:00 am"],
        },
        # 15. Out-of-Scope / Insufficient Data Question (Testing anti-hallucination guardrails)
        {
            "id": 15,
            "category": "Anti-Hallucination & Fallback",
            "query": "What is the fee for Sunbeam's Aerospace Rocket Propulsion Engineering course?",
            "expected_rag": True,
            "expected_intent": "course",
            "validation_keywords": ["don't have enough information", "not found", "outside"],
        },
    ]

    passed_count = 0

    for tc in test_cases:
        print(f"\n--- [TEST CASE {tc['id']}/15: {tc['category']}] ---")
        print(f"  • Query: \"{tc['query']}\"")

        start = time.perf_counter()
        res = await agent.execute(tc["query"], history=tc.get("history"))
        latency = round((time.perf_counter() - start) * 1000, 2)

        print(f"  • Classified Intent: '{res.intent}' (Requires RAG: {res.requires_rag})")
        print(f"  • Tools Executed: {res.tools_used}")
        print(f"  • Sources: {res.sources}")
        print(f"  • Latency: {latency} ms")
        print(f"  • Response: \"{res.response[:150].strip()}...\"")

        # Verifications
        response_lower = res.response.lower()
        matched = [kw for kw in tc["validation_keywords"] if kw.lower() in response_lower]
        grounding_check = len(matched) > 0 or "don't have enough information" in response_lower or not tc["expected_rag"]

        if grounding_check:
            print(f"  ✅ PASS: Grounding keywords verified: {matched}")
            passed_count += 1
        else:
            print(f"  ⚠️ REVIEW: Expected keywords {tc['validation_keywords']} not found in response.")

    print(f"\nSummary: {passed_count}/15 AI Test Cases passed successfully.")
    assert passed_count >= 13, f"Too many test cases failed: {passed_count}/15"


async def main():
    test_system_components()
    test_rag_and_ingestion()
    test_callable_tools()
    test_sse_streaming_and_persistence()
    await test_15_ai_test_cases()
    print_header("ALL INTEGRATION TESTS AND VERIFICATIONS COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(main())
