"""
Base tool interface and registry for function calling.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Abstract base class for all tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (must match function name for Groq)."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for the AI model."""
        pass

    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON Schema for tool parameters."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """
        Execute the tool with given parameters.

        Returns:
            str: Formatted result string for the AI to present to user
        """
        pass

    def format(self) -> Dict[str, Any]:
        """Convert tool to Groq function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema
            }
        }


class ToolRegistry:
    """Registry for managing available tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        if not isinstance(tool, BaseTool):
            raise ValueError(
                f"Tool must be an instance of BaseTool, got {type(tool)}")

        if tool.name in self._tools:
            logger.warning(
                f"Tool {tool.name} is already registered, overwriting...")

        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_all(self) -> List[BaseTool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_tool_list(self, tool_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get tools in Groq function calling format.

        Args:
            tool_names: Optional list of tool names to filter. If None, returns all tools.

        Returns:
            List of tools in Groq function calling format
        """
        if tool_names is None:
            return [tool.format() for tool in self._tools.values()]

        # Tool list by name
        tool_list = []
        for name in tool_names:
            tool = self._tools.get(name)
            if tool:
                tool_list.append(tool.format())
            else:
                logger.warning(
                    f"Tool '{name}' not found in registry, skipping")

        return tool_list

    def get_available_tool_names(self) -> List[str]:
        """Get list of all available tool names."""
        return list(self._tools.keys())

    async def execute_tool(self, name: str, arguments: Dict[str, Any],
                           request_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Execute a tool by name with given arguments.

        Args:
            name: Tool name
            arguments: Tool arguments (will be passed as **kwargs to execute)
            request_context: Optional request context (e.g., IP address, user info)

        Returns:
            str: Tool execution result
        """
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")

        # Merge request context into arguments if tool needs it
        if request_context:
            arguments = {**arguments, **request_context}

        try:
            logger.info(f"Executing tool: {name} with arguments: {arguments}")
            result = await tool.execute(**arguments)
            return result
        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            raise
