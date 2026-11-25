"""
Agent state definition for LangGraph workflow.
"""
from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict):
    """
    State passed through nodes of the Sunbeam SmartBot Agentic RAG graph.
    """
    # Inputs
    query: str
    history: List[Dict[str, str]]

    # Intent & Routing
    intent: str  # 'direct', 'course', 'internship', 'comparison', 'institutional', 'admissions', 'faq', 'general_rag'
    requires_rag: bool
    rewritten_query: str
    selected_tools: List[str]

    # Tool Execution & Results
    tool_results: Dict[str, Any]
    tool_activity: List[Dict[str, Any]]  # Public metadata: tool_name, status, latency_ms, preview
    retrieved_context: List[str]
    sources: List[str]

    # Evaluation & Self-Correction
    retrieval_relevance: float  # 0.0 - 1.0
    relevance_reason: str
    retry_count: int
    max_retries: int

    # Final Output
    final_answer: str
