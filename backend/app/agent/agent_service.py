"""
Agent service providing a clean API interface to invoke the LangGraph Agentic RAG system.
"""
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.agent.graph import get_agent_graph
from app.agent.state import AgentState
from app.core.logging import get_logger

logger = get_logger("app.agent.service")


class AgentExecutionResult(BaseModel):
    query: str
    response: str
    intent: str
    requires_rag: bool
    sources: List[str]
    tools_used: List[str]
    tool_activity: List[Dict[str, Any]]
    execution_time_ms: float


class AgentService:
    """
    High-level facade for executing queries against the Sunbeam Agentic RAG graph.
    """

    def __init__(self):
        self.graph = get_agent_graph()

    async def execute(
        self,
        query: str,
        history: Optional[List[Dict[str, str]]] = None,
        max_retries: int = 1,
    ) -> AgentExecutionResult:
        """
        Executes query through the LangGraph agent.
        """
        if not query or not query.strip():
            return AgentExecutionResult(
                query=query,
                response="Please provide a valid question.",
                intent="direct",
                requires_rag=False,
                sources=[],
                tools_used=[],
                tool_activity=[],
                execution_time_ms=0.0,
            )

        start_time = time.perf_counter()
        initial_state: AgentState = {
            "query": query.strip(),
            "history": history or [],
            "intent": "general_rag",
            "requires_rag": True,
            "rewritten_query": query.strip(),
            "selected_tools": [],
            "tool_results": {},
            "tool_activity": [],
            "retrieved_context": [],
            "sources": [],
            "retrieval_relevance": 0.0,
            "relevance_reason": "",
            "retry_count": 0,
            "max_retries": max_retries,
            "final_answer": "",
        }

        logger.info(f"Invoking Agent Graph for query: '{query[:80]}'")
        final_state = await self.graph.ainvoke(initial_state)

        execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        tools_used = [act["tool"] for act in final_state.get("tool_activity", [])]

        return AgentExecutionResult(
            query=query,
            response=final_state.get("final_answer", ""),
            intent=final_state.get("intent", "general_rag"),
            requires_rag=final_state.get("requires_rag", True),
            sources=final_state.get("sources", []),
            tools_used=tools_used,
            tool_activity=final_state.get("tool_activity", []),
            execution_time_ms=execution_time_ms,
        )


_agent_service_instance: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    """Singleton accessor for AgentService."""
    global _agent_service_instance
    if _agent_service_instance is None:
        _agent_service_instance = AgentService()
    return _agent_service_instance
