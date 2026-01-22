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

IMPORTANT: For the "create_file" tool:
- You should provide filename, file_type, and other metadata
- You can omit the "content" parameter or set it to an empty string - it will be generated separately based on the user's request
- If you do provide content, it will be used as-is, but separate content generation is preferred for better quality

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
# File Content Generation
# =============================================================================

FILE_CONTENT_GENERATION_SYSTEM_PROMPT = """You are a helpful assistant that generates high-quality file content based on user requests.

Your job is to:
1. Understand what the user wants in the file
2. Generate appropriate, well-structured content
3. Ensure the content is complete and useful
4. Format the content appropriately for the file type

For text files (.txt): Generate plain text content that is clear and readable.
For markdown files (.md): Generate properly formatted markdown with headers, lists, and other markdown syntax as appropriate.

Return only the file content itself - no explanations, no metadata, just the content that should be written to the file."""


def get_file_content_generation_prompt(
    user_query: str,
    filename: str,
    file_type: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    additional_context: Optional[str] = None
) -> str:
    """
    Generate prompt for file content generation.

    Args:
        user_query: The user's original query
        filename: Name of the file to create
        file_type: Type of file (txt, md, etc.)
        conversation_history: Optional conversation history for context
        additional_context: Optional additional context or requirements

    Returns:
        Formatted prompt string
    """
    context_text = ""
    if conversation_history:
        context_text = "\n\nConversation History (for context):\n"
        # Last 5 messages for better context
        for msg in conversation_history[-5:]:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:300]  # Truncate long messages
            context_text += f"{role}: {content}\n"

    additional_info = ""
    if additional_context:
        additional_info = f"\n\nAdditional Requirements/Context:\n{additional_context}\n"

    file_type_guidance = ""
    if file_type == "md":
        file_type_guidance = "\n\nNote: This is a Markdown file. Use proper markdown formatting:\n- Use # for headers\n- Use - or * for lists\n- Use ** for bold, * for italic\n- Use ``` for code blocks\n- Structure the content with appropriate sections"
    elif file_type == "txt":
        file_type_guidance = "\n\nNote: This is a plain text file. Use clear, readable formatting with line breaks and sections as appropriate."

    prompt = f"""The user wants to create a file named "{filename}.{file_type}".

User's Request: {user_query}
{context_text}{additional_info}

Generate the complete content that should be written to this file. The content should fulfill the user's request and be well-structured and useful.
{file_type_guidance}

Return only the file content - no explanations, no comments, just the content that should be written to the file.

File Content:"""

    return prompt


# =============================================================================
# File Content Refinement
# =============================================================================

FILE_CONTENT_REFINEMENT_SYSTEM_PROMPT = """You are a helpful assistant that refines and improves file content.

Your job is to:
1. Review the existing file content
2. Understand what improvements or changes are needed
3. Generate improved/refined content
4. Maintain the file type formatting (txt, md, etc.)

Return only the refined file content itself - no explanations, no metadata, just the improved content that should replace the original."""


def get_file_content_refinement_prompt(
    original_content: str,
    user_feedback: str,
    filename: str,
    file_type: str,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Generate prompt for file content refinement.

    Args:
        original_content: The current file content
        user_feedback: User's feedback or requested changes
        filename: Name of the file
        file_type: Type of file (txt, md, etc.)
        conversation_history: Optional conversation history for context

    Returns:
        Formatted prompt string
    """
    context_text = ""
    if conversation_history:
        context_text = "\n\nConversation History (for context):\n"
        for msg in conversation_history[-3:]:  # Last 3 messages for context
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:200]
            context_text += f"{role}: {content}\n"

    # Truncate original content if too long (keep first and last parts)
    content_preview = original_content
    if len(original_content) > 2000:
        content_preview = (
            original_content[:1000] +
            "\n\n[... content truncated ...]\n\n" +
            original_content[-1000:]
        )

    prompt = f"""The user wants to refine/improve the content of file "{filename}.{file_type}".

Current File Content:
{content_preview}

User's Feedback/Requested Changes: {user_feedback}
{context_text}

Generate the refined/improved content that addresses the user's feedback while maintaining the file's purpose and structure.
Keep the same file type formatting ({file_type}).

Return only the refined file content - no explanations, no comments, just the improved content that should replace the original.

Refined File Content:"""

    return prompt


# =============================================================================
# Helper Functions
# =============================================================================

def get_session_title_prompt(message: str) -> str:
    """Get the formatted prompt for generating a session title."""
    return SESSION_TITLE_USER_PROMPT.format(message=message)
