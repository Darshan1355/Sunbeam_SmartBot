"""
Centralized Tool Registry for Sunbeam SmartBot.
Manages tool discovery, metadata inspection, execution logging,
and duplicate invocation caching.
"""
import time
from typing import Any, Callable, Dict, List, Optional
from langchain_core.tools import BaseTool

from app.core.logging import get_logger
from app.schemas.tools import ToolExecutionLog, ToolInfo
from app.tools.sunbeam_tools import (
    check_eligibility,
    compare_courses,
    fetch_sunbeam_website,
    multi_document_search,
    search_conversation_context,
    search_courses,
    search_faqs,
    search_internships,
    search_knowledge_base,
    search_website_info,
    summarize_document,
)

logger = get_logger("app.tools.registry")


class ToolRegistry:
    """
    Central repository for all available LangChain tools with execution logging
    and duplicate invocation prevention.
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._categories: Dict[str, str] = {}
        self._execution_logs: List[ToolExecutionLog] = []
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register the 10 core Sunbeam tools with their architectural categories."""
        defaults = [
            (search_knowledge_base, "retrieval"),
            (search_courses, "courses"),
            (compare_courses, "comparison"),
            (search_internships, "internships"),
            (search_website_info, "institutional"),
            (summarize_document, "utility"),
            (check_eligibility, "admissions"),
            (search_faqs, "support"),
            (multi_document_search, "retrieval"),
            (search_conversation_context, "context"),
            (fetch_sunbeam_website, "live_web"),
        ]

        for tool_obj, category in defaults:
            self.register(tool_obj, category=category)

    def register(self, tool_obj: BaseTool, category: str = "general") -> None:
        """Register a LangChain BaseTool."""
        self._tools[tool_obj.name] = tool_obj
        self._categories[tool_obj.name] = category
        logger.debug(f"Registered tool: '{tool_obj.name}' in category '{category}'")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Fetch tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        """Returns all registered LangChain BaseTool objects for agent binding."""
        return list(self._tools.values())

    def get_tool_infos(self) -> List[ToolInfo]:
        """Returns structured metadata for all registered tools."""
        infos = []
        for name, tool_obj in self._tools.items():
            parameters = {}
            if hasattr(tool_obj, "args_schema") and tool_obj.args_schema:
                try:
                    parameters = tool_obj.args_schema.model_json_schema()
                except Exception:
                    parameters = {}

            infos.append(
                ToolInfo(
                    name=name,
                    description=tool_obj.description.strip(),
                    category=self._categories.get(name, "general"),
                    is_available=True,
                    parameters=parameters,
                )
            )
        return infos

    def execute_tool(
        self,
        name: str,
        input_args: Dict[str, Any],
        call_cache: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Executes a registered tool with latency tracking, duplicate prevention,
        and structured execution logging.
        """
        tool_obj = self.get_tool(name)
        if not tool_obj:
            raise ValueError(f"Tool '{name}' is not registered.")

        # Duplicate call memoization
        cache_key = f"{name}:{sorted(input_args.items())}"
        if call_cache is not None and cache_key in call_cache:
            logger.info(f"Returning cached result for duplicate tool call: {name}")
            return call_cache[cache_key]

        start_time = time.perf_counter()
        status = "success"
        output = None

        try:
            logger.info(f"Executing tool: {name} with args: {input_args}")
            output = tool_obj.invoke(input_args)
            if call_cache is not None:
                call_cache[cache_key] = output
            return output
        except Exception as e:
            status = "error"
            output = f"Tool execution failed: {str(e)}"
            logger.error(f"Error executing {name}: {str(e)}")
            return output
        finally:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            preview = str(output)[:150] if output else "None"
            log_entry = ToolExecutionLog(
                tool_name=name,
                input_args=input_args,
                output_preview=preview,
                latency_ms=latency_ms,
                status=status,
            )
            self._execution_logs.append(log_entry)

    def get_execution_logs(self) -> List[ToolExecutionLog]:
        """Returns recent tool execution logs."""
        return self._execution_logs[-50:]


_tool_registry_instance: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Singleton accessor for ToolRegistry."""
    global _tool_registry_instance
    if _tool_registry_instance is None:
        _tool_registry_instance = ToolRegistry()
    return _tool_registry_instance
