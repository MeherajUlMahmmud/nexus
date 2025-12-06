"""
Centralized prompts for AI interactions.
All system prompts and prompt templates should be defined here.
"""

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
# Helper Functions
# =============================================================================

def get_session_title_prompt(message: str) -> str:
    """Get the formatted prompt for generating a session title."""
    return SESSION_TITLE_USER_PROMPT.format(message=message)
