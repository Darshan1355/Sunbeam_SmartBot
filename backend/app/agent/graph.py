"""
LangGraph workflow orchestrating dynamic tool selection, multi-step retrieval,
evaluation, query rewriting, and grounded response generation.
"""
from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    analyze_intent_node,
    query_rewriter_node,
    response_generator_node,
    retrieval_evaluator_node,
    tool_execution_node,
)
from app.agent.state import AgentState
from app.core.logging import get_logger

logger = get_logger("app.agent.graph")


def route_after_intent(state: AgentState) -> str:
    """Conditional router deciding whether RAG tools are needed or direct generation."""
    if not state.get("requires_rag", True):
        logger.info("Routing -> direct response_generator (no RAG needed)")
        return "response_generator"
    logger.info("Routing -> tool_execution (RAG needed)")
    return "tool_execution"


def route_after_eval(state: AgentState) -> str:
    """Conditional router deciding whether retrieval was sufficient or needs query rewriting."""
    score = state.get("retrieval_relevance", 0.0)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 1)

    if score >= 0.35 or retry_count >= max_retries:
        logger.info(f"Routing -> response_generator (score: {score}, retries: {retry_count})")
        return "response_generator"

    logger.info(f"Routing -> query_rewriter for retry (score: {score} < 0.35)")
    return "query_rewriter"


def create_agent_graph():
    """Builds and compiles the Sunbeam Agentic RAG StateGraph."""
    workflow = StateGraph(AgentState)

    # 1. Register Nodes
    workflow.add_node("intent_analyzer", analyze_intent_node)
    workflow.add_node("tool_execution", tool_execution_node)
    workflow.add_node("retrieval_evaluator", retrieval_evaluator_node)
    workflow.add_node("query_rewriter", query_rewriter_node)
    workflow.add_node("response_generator", response_generator_node)

    # 2. Define Edges
    workflow.add_edge(START, "intent_analyzer")

    workflow.add_conditional_edges(
        "intent_analyzer",
        route_after_intent,
        {
            "response_generator": "response_generator",
            "tool_execution": "tool_execution",
        },
    )

    workflow.add_edge("tool_execution", "retrieval_evaluator")

    workflow.add_conditional_edges(
        "retrieval_evaluator",
        route_after_eval,
        {
            "response_generator": "response_generator",
            "query_rewriter": "query_rewriter",
        },
    )

    workflow.add_edge("query_rewriter", "tool_execution")
    workflow.add_edge("response_generator", END)

    app = workflow.compile()
    logger.info("LangGraph Agentic RAG workflow successfully compiled.")
    return app


_compiled_graph = None


def get_agent_graph():
    """Singleton provider for compiled LangGraph agent."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = create_agent_graph()
    return _compiled_graph
