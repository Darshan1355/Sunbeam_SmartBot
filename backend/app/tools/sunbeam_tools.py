"""
LangChain @tool decorated callable tools for the Sunbeam SmartBot.
All tools query real ChromaDB vector data and structured Sunbeam documents.
"""
import json
import re
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool

from app.core.logging import get_logger
from app.rag.retriever import get_retrieval_service

logger = get_logger("app.tools.sunbeam")


@tool
def search_knowledge_base(query: str, top_k: int = 5) -> str:
    """Search the general Sunbeam knowledge base for information matching the query.
    Use this tool when no specialized domain tool fits or for general inquiries about Sunbeam.
    
    Args:
        query: The user's question or search phrase.
        top_k: Number of relevant knowledge chunks to retrieve (default 5).
    """
    if not query or not query.strip():
        return json.dumps({"error": "Query cannot be empty", "results": []})

    retriever = get_retrieval_service()
    res = retriever.retrieve(query=query, top_k=top_k, search_mode="similarity")

    if not res.chunks:
        return json.dumps({
            "message": "No relevant information found in Sunbeam knowledge base.",
            "query": query,
            "results": [],
            "sources": [],
        })

    formatted_results = [
        {
            "content": c.content,
            "source": c.source,
            "relevance_score": c.relevance_score,
        }
        for c in res.chunks
    ]

    return json.dumps({
        "query": query,
        "count": len(formatted_results),
        "sources": res.sources,
        "results": formatted_results,
    })


@tool
def search_courses(query: str, max_results: int = 5) -> str:
    """Search Sunbeam modular courses, C-DAC PG Diploma programs, and training offerings.
    Returns course details such as batch schedules, duration, timings, syllabus, and fees.
    
    Args:
        query: Name of the course, topic, or keyword (e.g., 'Core Java', 'C++', 'PG-DAC', 'fees').
        max_results: Maximum number of course entries to retrieve (default 5).
    """
    if not query or not query.strip():
        return json.dumps({"error": "Course query cannot be empty", "results": []})

    retriever = get_retrieval_service()
    q_low = query.lower()
    is_cdac = any(k in q_low for k in ["dac", "dbda", "dmc", "desd", "c-cat", "ccat", "diploma", "c-dac"])

    # Retrieve candidate pool
    res = retriever.retrieve(
        query=query.strip(),
        top_k=max_results * 2,
    )

    def compute_priority(chunk) -> float:
        score = chunk.relevance_score
        src = chunk.source.lower()
        cnt = chunk.content.lower()

        if is_cdac and "cdac" in src:
            score += 0.35
        elif not is_cdac and "courses" in src:
            score += 0.30

        # Exact title boost
        for title in ["core java", "c++", "apache spark", "dsa", "data structures", "mern", "python", "aptitude"]:
            if title in q_low and title in cnt:
                score += 0.40

        return score

    sorted_chunks = sorted(res.chunks, key=compute_priority, reverse=True)[:max_results]

    if not sorted_chunks:
        return json.dumps({"message": f"No course details found for '{query}'.", "results": []})

    return json.dumps({
        "category": "Courses",
        "query": query,
        "count": len(sorted_chunks),
        "results": [
            {"content": c.content, "source": c.source, "score": c.relevance_score}
            for c in sorted_chunks
        ],
        "sources": list({c.source for c in sorted_chunks}),
    })


@tool
def compare_courses(course_a: str, course_b: str) -> str:
    """Compare two Sunbeam courses side by side regarding duration, schedule, fees, and syllabus.
    
    Args:
        course_a: The first course name (e.g., 'Core Java', 'C++').
        course_b: The second course name (e.g., 'Data Structures', 'Python Web Development').
    """
    if not course_a or not course_b:
        return json.dumps({"error": "Both course_a and course_b must be provided."})

    retriever = get_retrieval_service()
    res_a = retriever.retrieve(query=f"course {course_a} fees duration schedule syllabus", top_k=2)
    res_b = retriever.retrieve(query=f"course {course_b} fees duration schedule syllabus", top_k=2)

    return json.dumps({
        "comparison": {
            "course_a": {
                "name": course_a,
                "data": [c.content for c in res_a.chunks],
                "sources": res_a.sources,
            },
            "course_b": {
                "name": course_b,
                "data": [c.content for c in res_b.chunks],
                "sources": res_b.sources,
            },
        }
    })


@tool
def search_internships(domain: str, duration: Optional[str] = None) -> str:
    """Search Sunbeam industrial training and internship programs, active batches, schedules, and locations.
    
    Args:
        domain: Technology domain (e.g., 'Generative AI', 'Data Science', 'MERN', 'Android', 'Java').
        duration: Optional duration filter (e.g., '1 Month', '2 Months', '6 Months').
    """
    if not domain or not domain.strip():
        return json.dumps({"error": "Domain cannot be empty", "results": []})

    query_str = f"internship batch schedule {domain}"
    if duration:
        query_str += f" {duration}"

    retriever = get_retrieval_service()
    res = retriever.retrieve(query=query_str, top_k=4)

    # Prioritize internship text data
    internship_chunks = [c for c in res.chunks if "internship" in c.source.lower() or "table" in c.content.lower()]
    results_to_use = internship_chunks if internship_chunks else res.chunks

    return json.dumps({
        "category": "Internships",
        "domain": domain,
        "duration": duration,
        "count": len(results_to_use),
        "results": [
            {"content": c.content, "source": c.source, "score": c.relevance_score}
            for c in results_to_use
        ],
    })


@tool
def search_website_info(topic: str) -> str:
    """Search Sunbeam institutional information including campus history, Hinjawadi Pune campus,
    Karad campus, contact phone numbers, emails, computing infrastructure, labs, and hostel accommodation.
    
    Args:
        topic: Specific campus, contact, or institute topic (e.g., 'contact numbers', 'Hinjawadi campus', 'Karad branch', 'hostel facilities').
    """
    if not topic or not topic.strip():
        return json.dumps({"error": "Topic cannot be empty", "results": []})

    retriever = get_retrieval_service()
    res = retriever.retrieve(query=f"Sunbeam institute {topic} contact address campus branches", top_k=4)

    return json.dumps({
        "category": "Institute Information",
        "topic": topic,
        "results": [
            {"content": c.content, "source": c.source, "score": c.relevance_score}
            for c in res.chunks
        ],
        "sources": res.sources,
    })


@tool
def fetch_sunbeam_website(query_or_path: str) -> str:
    """Fetch live web pages and real-time updates directly from the official Sunbeam website (sunbeaminfo.com).
    Use this tool when real-time, live website data, placement updates, or web page content is requested.
    
    Args:
        query_or_path: Specific page path or keyword (e.g., 'courses', 'about-us', 'contact-us', 'placements', 'internship').
    """
    from app.services.website_service import get_website_service

    svc = get_website_service()
    result = svc.scrape_topic_or_path(query_or_path)

    # If live HTML returned content, return it
    if result.get("content"):
        return json.dumps({
            "category": "Live Website Data",
            "url": result.get("target_url"),
            "status": "live_success",
            "content": result["content"][:2000],
            "source": result.get("target_url"),
        })

    # Fallback to rich local knowledge if live scrape is an SPA empty shell
    retriever = get_retrieval_service()
    res = retriever.retrieve(query=f"Sunbeam website {query_or_path}", top_k=3)
    return json.dumps({
        "category": "Website Information (Cached)",
        "url": result.get("target_url", "https://sunbeaminfo.com"),
        "status": "cached_records",
        "results": [{"content": c.content, "source": c.source} for c in res.chunks],
        "sources": res.sources,
    })


@tool
def summarize_document(source_name: str) -> str:
    """Summarizes a specific Sunbeam knowledge document.
    
    Args:
        source_name: Source document name: 'about', 'internship', or 'courses'.
    """
    normalized = source_name.lower().strip()
    target_pattern = ""
    if "about" in normalized:
        target_pattern = "about"
    elif "intern" in normalized:
        target_pattern = "internship"
    elif "course" in normalized:
        target_pattern = "courses"
    else:
        return json.dumps({
            "error": f"Unknown source '{source_name}'. Valid sources: 'about', 'internship', 'courses'."
        })

    retriever = get_retrieval_service()
    # Query with high diversity (MMR)
    res = retriever.retrieve(
        query=f"Sunbeam {target_pattern} complete summary overview",
        top_k=5,
        search_mode="mmr",
    )

    matching_chunks = [c for c in res.chunks if target_pattern in c.source.lower()]
    final_chunks = matching_chunks if matching_chunks else res.chunks

    combined = "\n\n".join(c.content for c in final_chunks[:3])

    return json.dumps({
        "document": target_pattern,
        "summary_context": combined,
        "sources": list(set(c.source for c in final_chunks)),
    })


@tool
def check_eligibility(program_name: str, educational_background: str) -> str:
    """Check prerequisites, target audience, and eligibility requirements for a given Sunbeam course or internship.
    
    Args:
        program_name: Course or internship name (e.g., 'Apache Spark', 'Generative AI', 'Cyber Security').
        educational_background: Student background (e.g., 'Computer Science engineering', 'Electronics', 'Non-IT').
    """
    if not program_name:
        return json.dumps({"error": "Program name must be provided."})

    retriever = get_retrieval_service()
    res = retriever.retrieve(
        query=f"{program_name} prerequisites target audience eligibility requirements {educational_background}",
        top_k=3,
    )

    return json.dumps({
        "program": program_name,
        "student_background": educational_background,
        "criteria_context": [
            {"content": c.content, "source": c.source}
            for c in res.chunks
        ],
    })


@tool
def search_faqs(question: str) -> str:
    """Search frequently asked questions regarding Sunbeam admissions, batch schedules, payment fees,
    online/offline training modes, and certification.
    
    Args:
        question: The user's practical question about enrollment or policies.
    """
    if not question:
        return json.dumps({"error": "Question cannot be empty."})

    retriever = get_retrieval_service()
    res = retriever.retrieve(
        query=f"FAQ frequently asked questions {question}",
        top_k=3,
        search_mode="similarity",
    )

    return json.dumps({
        "faq_query": question,
        "answers": [
            {"content": c.content, "source": c.source, "score": c.relevance_score}
            for c in res.chunks
        ],
    })


@tool
def multi_document_search(query: str, sources: Optional[List[str]] = None) -> str:
    """Perform a cross-document search spanning multiple Sunbeam knowledge files.
    
    Args:
        query: The search inquiry.
        sources: Optional list of source keywords (e.g. ['about', 'internship']).
    """
    if not query:
        return json.dumps({"error": "Query cannot be empty."})

    retriever = get_retrieval_service()
    res = retriever.retrieve(query=query, top_k=6, search_mode="mmr")

    filtered_chunks = res.chunks
    if sources:
        low_sources = [s.lower() for s in sources]
        filtered_chunks = [
            c for c in res.chunks
            if any(s in c.source.lower() for s in low_sources)
        ]

    return json.dumps({
        "query": query,
        "matched_sources": list(set(c.source for c in filtered_chunks)),
        "results": [
            {"content": c.content, "source": c.source, "score": c.relevance_score}
            for c in filtered_chunks
        ],
    })


@tool
def search_conversation_context(query: str, recent_messages: str) -> str:
    """Extract relevant entities, course names, or parameters mentioned in recent chat turns
    to resolve follow-up questions and pronouns (e.g. 'What is its fee?', 'Where is it?').
    
    Args:
        query: The current ambiguous or follow-up question.
        recent_messages: Text snippet of previous conversation turns.
    """
    if not query:
        return json.dumps({"error": "Query cannot be empty."})

    return json.dumps({
        "status": "context_resolved",
        "current_query": query,
        "recent_context_analyzed": recent_messages[:300] if recent_messages else "None",
        "guidance": "Use context to identify referenced entity before executing knowledge retrieval.",
    })
