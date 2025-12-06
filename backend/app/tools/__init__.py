"""
Tool system for AI function calling.
"""
from app.tools.base import BaseTool, ToolRegistry
from app.tools.weather import WeatherTool
from app.tools.calculator import CalculatorTool
from app.tools.file_creation import FileCreationTool

# Initialize tool registry
tool_registry = ToolRegistry()

# Register all available tools
tool_registry.register(WeatherTool())
tool_registry.register(CalculatorTool())
tool_registry.register(FileCreationTool())

__all__ = ["BaseTool", "ToolRegistry", "tool_registry", "WeatherTool", "CalculatorTool", "FileCreationTool"]

