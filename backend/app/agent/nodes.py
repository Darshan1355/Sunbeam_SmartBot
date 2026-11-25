"""
LangGraph nodes implementing query understanding, tool invocation,
retrieval evaluation, query rewriting, and grounded response generation.
"""
import json
import re
import time
from typing import Any, Dict, List

from app.agent.prompts import (
    DIRECT_GENERATOR_SYSTEM_PROMPT,
    GROUNDED_GENERATOR_SYSTEM_PROMPT,
    GROUNDED_GENERATOR_USER_PROMPT,
    INTENT_ANALYZER_PROMPT,
    RELEVANCE_EVALUATOR_PROMPT,
)
from app.agent.state import AgentState
from app.core.logging import get_logger
from app.schemas.chat import ChatMessage
from app.services.groq_service import get_groq_service
from app.tools.registry import get_tool_registry

logger = get_logger("app.agent.nodes")


def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Helper to cleanly extract JSON payload from LLM responses with markdown or code fences."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


async def analyze_intent_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 1: Analyzes user query, classifies intent, decides if RAG is required,
    and identifies appropriate tools.
    """
    query = state["query"]
    history = state.get("history", [])
    logger.info(f"[Agent Node: Intent Analysis] Processing query: '{query}'")

    groq_service = get_groq_service()

    # Build prompt input including recent history
    history_summary = ""
    if history:
        history_summary = "Recent Conversation History:\n" + "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history[-3:]
        ) + "\n\n"

    user_prompt = f"{history_summary}User Question: {query}"

    try:
        completion = await groq_service.generate_chat(
            messages=[
                ChatMessage(role="system", content=INTENT_ANALYZER_PROMPT),
                ChatMessage(role="user", content=user_prompt),
            ],
            temperature=0.0,
            max_tokens=600,
        )

        parsed = extract_json_from_text(completion.content)
        requires_rag = bool(parsed.get("requires_rag", True))
        intent = parsed.get("intent", "general_rag")
        rewritten_query = parsed.get("rewritten_query", query)
        selected_tools = parsed.get("selected_tools", ["search_knowledge_base"])

    except Exception as e:
        logger.warning(f"LLM intent analysis fallback triggered: {str(e)}")
        # Rule-based fallback
        q_low = query.lower()
        if any(w in q_low for w in ["decorator", "write a program", "hello world", "explain python", "what is oop"]):
            requires_rag = False
            intent = "direct"
            rewritten_query = query
            selected_tools = []
        elif any(w in q_low for w in ["compare", "versus", " vs "]):
            requires_rag = True
            intent = "comparison"
            rewritten_query = query
            selected_tools = ["compare_courses", "search_courses"]
        elif any(w in q_low for w in ["intern", "industrial"]):
            requires_rag = True
            intent = "internship"
            rewritten_query = query
            selected_tools = ["search_internships"]
        elif any(w in q_low for w in ["course", "fee", "fees", "syllabus", "schedule", "duration"]):
            requires_rag = True
            intent = "course"
            rewritten_query = query
            selected_tools = ["search_courses"]
        elif any(w in q_low for w in ["campus", "hinjawadi", "hostel", "location", "facility"]):
            requires_rag = True
            intent = "institutional"
            rewritten_query = query
            selected_tools = ["search_website_info"]
        else:
            requires_rag = True
            intent = "general_rag"
            rewritten_query = query
            selected_tools = ["search_knowledge_base"]

    logger.info(f"Intent analyzed: intent='{intent}', requires_rag={requires_rag}, tools={selected_tools}")

    return {
        "intent": intent,
        "requires_rag": requires_rag,
        "rewritten_query": rewritten_query,
        "selected_tools": selected_tools,
    }


async def tool_execution_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 2: Executes selected tools dynamically and aggregates results.
    """
    selected_tools = state.get("selected_tools", [])
    query = state.get("rewritten_query", state["query"])
    logger.info(f"[Agent Node: Tool Execution] Invoking tools: {selected_tools}")

    registry = get_tool_registry()
    tool_results = dict(state.get("tool_results", {}))
    tool_activity = list(state.get("tool_activity", []))
    retrieved_context = list(state.get("retrieved_context", []))
    sources = set(state.get("sources", []))

    for tool_name in selected_tools:
        # Determine tool arguments
        args: Dict[str, Any] = {}
        if tool_name == "search_courses":
            args = {"query": query, "max_results": 5}
        elif tool_name == "compare_courses":
            # Extract two course names if possible
            words = query.split()
            c1, c2 = "Core Java", "C++"
            if "and" in query.lower():
                parts = query.lower().split("and")
                c1 = parts[0].replace("compare", "").strip()
                c2 = parts[1].strip()
            args = {"course_a": c1, "course_b": c2}
        elif tool_name == "search_internships":
            args = {"domain": query}
        elif tool_name == "search_website_info":
            args = {"topic": query}
        elif tool_name == "summarize_document":
            args = {"source_name": "about"}
        elif tool_name == "check_eligibility":
            args = {"program_name": query, "educational_background": "Any graduate"}
        elif tool_name == "search_faqs":
            args = {"question": query}
        elif tool_name == "multi_document_search":
            args = {"query": query}
        elif tool_name == "search_conversation_context":
            hist_str = "\n".join(f"{m.get('role')}: {m.get('content')}" for m in state.get("history", []))
            args = {"query": query, "recent_messages": hist_str}
        elif tool_name == "fetch_sunbeam_website":
            args = {"query_or_path": query}
        else:
            args = {"query": query, "top_k": 5}

        start_time = time.perf_counter()
        try:
            raw_output = registry.execute_tool(tool_name, args)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            tool_results[tool_name] = raw_output

            # Parse returned JSON
            parsed_data = {}
            try:
                parsed_data = json.loads(raw_output)
            except Exception:
                pass

            # Extract chunks and sources
            if "content" in parsed_data and parsed_data["content"]:
                retrieved_context.append(str(parsed_data["content"]))
                if "url" in parsed_data:
                    sources.add(parsed_data["url"])

            if "results" in parsed_data:
                for item in parsed_data["results"]:
                    if isinstance(item, dict) and "content" in item:
                        retrieved_context.append(item["content"])
                    if isinstance(item, dict) and "source" in item:
                        sources.add(item["source"])

            if "sources" in parsed_data:
                for s in parsed_data["sources"]:
                    sources.add(s)

            if "comparison" in parsed_data:
                comp = parsed_data["comparison"]
                for k, v in comp.items():
                    if isinstance(v, dict):
                        for c in v.get("data", []):
                            retrieved_context.append(c)
                        for s in v.get("sources", []):
                            sources.add(s)

            tool_activity.append({
                "tool": tool_name,
                "status": "success",
                "latency_ms": latency_ms,
                "summary": f"Retrieved {len(parsed_data.get('results', []))} relevant items",
            })

        except Exception as e:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Failed to execute tool {tool_name}: {str(e)}")
            tool_activity.append({
                "tool": tool_name,
                "status": "error",
                "latency_ms": latency_ms,
                "summary": str(e),
            })

    return {
        "tool_results": tool_results,
        "tool_activity": tool_activity,
        "retrieved_context": retrieved_context,
        "sources": sorted(list(sources)),
    }


async def retrieval_evaluator_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 3: Evaluates the relevance of the retrieved context.
    """
    context_list = state.get("retrieved_context", [])
    query = state.get("rewritten_query", state["query"])
    logger.info(f"[Agent Node: Retrieval Evaluator] Grading {len(context_list)} context items")

    if not context_list:
        return {
            "retrieval_relevance": 0.0,
            "relevance_reason": "No context was retrieved by tools.",
        }

    # Fast heuristic check based on keyword presence and chunk length
    sample_text = " ".join(context_list[:3]).lower()
    q_words = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 3]

    matched_keywords = sum(1 for w in q_words if w in sample_text)
    heuristic_score = min(1.0, 0.4 + (matched_keywords / max(1, len(q_words))) * 0.6)

    # If heuristic is sufficiently clear, use it; otherwise evaluate with LLM
    final_score = round(heuristic_score, 2)
    reason = f"Keyword matching relevance: {int(final_score * 100)}%"

    logger.info(f"Retrieval evaluated: score={final_score} (reason: {reason})")

    return {
        "retrieval_relevance": final_score,
        "relevance_reason": reason,
    }


async def query_rewriter_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 4: Reformulates the query and switches to broader fallback search if initial retrieval was weak.
    """
    current_retry = state.get("retry_count", 0) + 1
    original_query = state["query"]
    logger.info(f"[Agent Node: Query Rewriter] Retrying retrieval (attempt {current_retry})")

    # Broaden query with general Sunbeam terms
    broadened_query = f"Sunbeam {original_query} information"

    return {
        "retry_count": current_retry,
        "rewritten_query": broadened_query,
        "selected_tools": ["search_knowledge_base"],
    }


async def response_generator_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 5: Synthesizes final grounded response via Groq API.
    """
    groq_service = get_groq_service()
    query = state["query"]
    requires_rag = state.get("requires_rag", True)
    context_list = state.get("retrieved_context", [])

    logger.info(f"[Agent Node: Response Generator] Synthesizing final answer (requires_rag={requires_rag})")

    if not requires_rag:
        # Direct programming / conversational response
        completion = await groq_service.generate_chat(
            messages=[
                ChatMessage(role="system", content=DIRECT_GENERATOR_SYSTEM_PROMPT),
                ChatMessage(role="user", content=query),
            ],
            temperature=0.3,
            max_tokens=800,
        )
        return {
            "final_answer": completion.content,
            "sources": [],
        }

    # Grounded RAG answer
    compiled_context = "\n\n---\n\n".join(context_list[:5])
    if not compiled_context.strip():
        return {
            "final_answer": "I don't have enough information in the Sunbeam records to answer that question accurately.",
            "sources": [],
        }

    active_question = state.get("rewritten_query") or query
    user_prompt = GROUNDED_GENERATOR_USER_PROMPT.format(
        question=active_question,
        context=compiled_context,
    )

    completion = await groq_service.generate_chat(
        messages=[
            ChatMessage(role="system", content=GROUNDED_GENERATOR_SYSTEM_PROMPT),
            ChatMessage(role="user", content=user_prompt),
        ],
        temperature=0.1,  # Low temperature for strict adherence
        max_tokens=1000,
    )

    return {
        "final_answer": completion.content,
    }
