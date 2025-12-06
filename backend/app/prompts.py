"""
Centralized prompts for AI interactions.
All system prompts and prompt templates should be defined here.
"""
from typing import List, Dict, Optional

# =============================================================================
# Session Title Generation
# =============================================================================

SESSION_TITLE_SYSTEM_PROMPT = """You are a helpful assistant that generates concise, descriptive titles for chat sessions."""

SESSION_TITLE_USER_PROMPT = """Generate a concise, descriptive title (maximum 50 characters) for a chat session based on this user message. 
The title should be a short phrase that captures the main topic or question. 
Do not include quotes, colons, or special formatting. Just return the title text.

User message: {message}

Title:"""

# =============================================================================
# Chat Completion (for future use)
# =============================================================================

DEFAULT_SYSTEM_PROMPT = """You are a helpful, harmless, and honest AI assistant. You provide clear, accurate, and helpful responses to user queries."""


# =============================================================================
# Agent Tool Selection
# =============================================================================

TOOL_SELECTION_SYSTEM_PROMPT = """You are an intelligent agent that decides which tools to use to answer user queries.

Your job is to:
1. Analyze the user's query
2. Determine which tools (if any) are needed to answer it
3. Decide the order/sequence in which tools should be called
4. Extract the necessary arguments for each tool

You must respond with a valid JSON object containing a list of tools to call.
If no tools are needed, return an empty list.
If multiple tools are needed, specify the sequence order (0, 1, 2, etc.).

Response format:
{
  "tools": [
    {
      "tool_name": "get_weather",
      "arguments": {
        "location": "New York",
        "units": "metric"
      },
      "sequence": 0
    }
  ]
}

Important:
- Only return valid JSON
- Tool names must match exactly with available tools
- Arguments must match the tool's parameter schema
- Sequence determines execution order (lower numbers first)
- If no tools are needed, return {"tools": []}"""


def get_tool_selection_prompt(
    user_query: str,
    available_tools: list,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Generate prompt for tool selection agent.
    
    Args:
        user_query: The user's current query
        available_tools: List of tool info dicts with name, description, parameters
        conversation_history: Optional conversation history for context
    
    Returns:
        Formatted prompt string
    """
    # Format available tools
    tools_text = ""
    for i, tool in enumerate(available_tools, 1):
        tools_text += f"\n{i}. {tool['name']}\n"
        tools_text += f"   Description: {tool['description']}\n"
        
        # Format parameters
        params = tool.get('parameters', {})
        if params and 'properties' in params:
            tools_text += "   Parameters:\n"
            for param_name, param_info in params['properties'].items():
                param_type = param_info.get('type', 'string')
                param_desc = param_info.get('description', '')
                required = param_name in params.get('required', [])
                req_text = " (required)" if required else " (optional)"
                tools_text += f"     - {param_name} ({param_type}){req_text}: {param_desc}\n"
        tools_text += "\n"
    
    # Add conversation context if available
    context_text = ""
    if conversation_history:
        context_text = "\n\nConversation History:\n"
        for msg in conversation_history[-3:]:  # Last 3 messages for context
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:200]  # Truncate long messages
            context_text += f"{role}: {content}\n"
    
    prompt = f"""User Query: {user_query}
{context_text}

Available Tools:
{tools_text}

Analyze the user's query and determine which tools (if any) should be called to answer it.
Consider:
- Does the query require external data or actions?
- Which tools are relevant?
- What order should tools be called in (if multiple)?
- What arguments does each tool need?

Return your decision as JSON in this format:
{{
  "tools": [
    {{
      "tool_name": "tool_name_here",
      "arguments": {{"param": "value"}},
      "sequence": 0
    }}
  ]
}}

If no tools are needed, return: {{"tools": []}}

Response (JSON only):"""
    
    return prompt


# =============================================================================
# Helper Functions
# =============================================================================

def get_session_title_prompt(message: str) -> str:
    """Get the formatted prompt for generating a session title."""
    return SESSION_TITLE_USER_PROMPT.format(message=message)
