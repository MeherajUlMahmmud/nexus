"""
Tool system for AI function calling.
"""
from app.tools.base import BaseTool, ToolRegistry
from app.tools.weather import WeatherTool
from app.tools.calculator import CalculatorTool
from app.tools.file_creation import FileCreationTool
from app.tools.web_search import WebSearchTool

# Initialize tool registry
tool_registry = ToolRegistry()

# Register all available tools
tool_registry.register(WeatherTool())
tool_registry.register(CalculatorTool())
tool_registry.register(FileCreationTool())
tool_registry.register(WebSearchTool())

__all__ = ["BaseTool", "ToolRegistry", "tool_registry", "WeatherTool", "CalculatorTool", "FileCreationTool", "WebSearchTool"]

