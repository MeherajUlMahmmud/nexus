"""
Agent-based tool orchestration system.
Uses LLM to decide which tools to call, independent of model's native function calling.
"""
import json
import logging
import re
from typing import List, Dict, Any, Optional
from app.services.groq import get_chat_completion
from app.tools import tool_registry
from app.prompts import (
    TOOL_SELECTION_SYSTEM_PROMPT,
    get_tool_selection_prompt,
    FILE_CONTENT_GENERATION_SYSTEM_PROMPT,
    get_file_content_generation_prompt,
    FILE_CONTENT_REFINEMENT_SYSTEM_PROMPT,
    get_file_content_refinement_prompt
)

logger = logging.getLogger(__name__)


class ToolDecision:
    """Represents a tool decision made by the agent."""

    def __init__(self, tool_name: str, arguments: Dict[str, Any], sequence: int = 0):
        self.tool_name = tool_name
        self.arguments = arguments
        self.sequence = sequence

    def __repr__(self):
        return f"ToolDecision(tool={self.tool_name}, sequence={self.sequence}, args={self.arguments})"


class ToolOrchestrator:
    """
    Agent that orchestrates tool calling using LLM decision-making.
    Works independently of model's native function calling support.
    """

    def __init__(self, model: str = "llama-3.1-8b-instant"):
        self.model = model

    async def decide_tools(
        self,
        user_query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[ToolDecision]:
        """
        Use LLM to decide which tools to call and in what order.

        Args:
            user_query: The user's query
            conversation_history: Previous messages for context

        Returns:
            List of ToolDecision objects in execution order
        """
        # Get available tools
        available_tools = tool_registry.get_available_tool_names()
        logger.debug(f"[TOOL_DECISION] Available tools: {available_tools}")

        if not available_tools:
            logger.info(
                "[TOOL_DECISION] No tools available in registry, skipping tool decision")
            return []

        # Get tool descriptions for the LLM
        tools_info = []
        for tool_name in available_tools:
            tool = tool_registry.get(tool_name)
            if tool:
                tools_info.append({
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters_schema
                })

        # Build prompt
        prompt = get_tool_selection_prompt(
            user_query=user_query,
            available_tools=tools_info,
            conversation_history=conversation_history
        )

        # Make LLM call to decide tools
        try:
            messages = [
                {"role": "system", "content": TOOL_SELECTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]

            logger.info(f"[TOOL_DECISION] Calling LLM for tool decision - model: {self.model}, query_length: {len(user_query)}, "
                        f"available_tools: {len(available_tools)}")

            response = await get_chat_completion(
                messages=messages,
                model=self.model,
                temperature=0.3,  # Lower temperature for more deterministic decisions
                max_tokens=500
            )

            content = response.get("content", "")
            logger.debug(
                f"[TOOL_DECISION] LLM response received - length: {len(content) if content else 0}")
            if not content:
                logger.warning(
                    "[TOOL_DECISION] Agent returned empty response, no tools will be called")
                return []

            # Parse JSON response
            try:
                # Try to extract JSON from the response (might have markdown code blocks)
                content = content.strip()

                # Extract JSON from markdown code blocks if present
                if "```" in content:
                    # Try multiple regex patterns to extract JSON from code blocks
                    json_match = None

                    # Pattern 1: ```json\n...\n```
                    json_match = re.search(
                        r'```json\s*\n(.*?)\n```', content, re.DOTALL)
                    if not json_match:
                        # Pattern 2: ```\n...\n```
                        json_match = re.search(
                            r'```\s*\n(.*?)\n```', content, re.DOTALL)
                    if not json_match:
                        # Pattern 3: More lenient - any ``` followed by content and closing ```
                        json_match = re.search(
                            r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)

                    if json_match:
                        content = json_match.group(1).strip()
                    else:
                        # Fallback: try to extract between first ``` and last ```
                        lines = content.split("\n")
                        json_start = None
                        json_end = None
                        for i, line in enumerate(lines):
                            stripped = line.strip()
                            if stripped.startswith("```") and json_start is None:
                                # Found opening code block
                                json_start = i + 1
                            elif stripped == "```" and json_start is not None:
                                # Found closing code block
                                json_end = i
                                break
                        if json_start is not None and json_end is not None:
                            content = "\n".join(
                                lines[json_start:json_end]).strip()
                        elif json_start is not None:
                            # No closing found, take everything after opening
                            content = "\n".join(lines[json_start:]).strip()

                decision_data = json.loads(content)

                # Parse tool decisions
                tool_decisions = []
                if isinstance(decision_data, dict) and "tools" in decision_data:
                    tools_list = decision_data["tools"]
                elif isinstance(decision_data, list):
                    tools_list = decision_data
                else:
                    logger.warning(
                        f"Unexpected decision format: {decision_data}")
                    return []

                for tool_data in tools_list:
                    if isinstance(tool_data, dict):
                        tool_name = tool_data.get(
                            "tool_name") or tool_data.get("name")
                        arguments = tool_data.get("arguments", {})
                        sequence = tool_data.get(
                            "sequence", len(tool_decisions))

                        if tool_name and tool_name in available_tools:
                            tool_decisions.append(ToolDecision(
                                tool_name=tool_name,
                                arguments=arguments or {},
                                sequence=sequence
                            ))
                        else:
                            logger.warning(
                                f"Invalid tool name in decision: {tool_name}")

                # Sort by sequence
                tool_decisions.sort(key=lambda x: x.sequence)

                logger.info(f"[TOOL_DECISION] Successfully parsed {len(tool_decisions)} tool decision(s): "
                            f"{[f'{td.tool_name}(seq={td.sequence})' for td in tool_decisions]}")
                return tool_decisions

            except json.JSONDecodeError as e:
                logger.error(
                    f"[TOOL_DECISION] Failed to parse agent response as JSON: {e}\nResponse: {content[:500]}")
                return []

        except Exception as e:
            logger.error(
                f"[TOOL_DECISION] Error in agent tool decision: {e}", exc_info=True)
            return []

    async def generate_file_content(
        self,
        user_query: str,
        filename: str,
        file_type: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        additional_context: Optional[str] = None
    ) -> str:
        """
        Generate file content using LLM with dedicated content generation prompt.

        Args:
            user_query: The user's original query
            filename: Name of the file to create
            file_type: Type of file (txt, md, etc.)
            conversation_history: Optional conversation history for context
            additional_context: Optional additional context or requirements

        Returns:
            Generated file content string
        """
        try:
            prompt = get_file_content_generation_prompt(
                user_query=user_query,
                filename=filename,
                file_type=file_type,
                conversation_history=conversation_history,
                additional_context=additional_context
            )

            messages = [
                {"role": "system", "content": FILE_CONTENT_GENERATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]

            logger.info(f"[FILE_CONTENT_GENERATION] Generating content for {filename}.{file_type} - "
                        f"model: {self.model}, query_length: {len(user_query)}")
            import time
            generation_start = time.time()

            response = await get_chat_completion(
                messages=messages,
                model=self.model,
                temperature=0.7,  # Higher temperature for more creative content
                max_tokens=4000  # Allow longer content generation
            )

            generation_time = time.time() - generation_start
            content = response.get("content", "").strip()

            logger.info(f"[FILE_CONTENT_GENERATION] Content generated in {generation_time:.2f}s - "
                        f"content_length: {len(content)}")

            if not content:
                logger.warning(
                    f"[FILE_CONTENT_GENERATION] Empty content generated for {filename}.{file_type}")
                return ""

            return content

        except Exception as e:
            logger.error(
                f"[FILE_CONTENT_GENERATION] Error generating file content: {e}", exc_info=True)
            return ""

    async def refine_file_content(
        self,
        original_content: str,
        user_feedback: str,
        filename: str,
        file_type: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Refine existing file content based on user feedback.

        Args:
            original_content: The current file content
            user_feedback: User's feedback or requested changes
            filename: Name of the file
            file_type: Type of file (txt, md, etc.)
            conversation_history: Optional conversation history for context

        Returns:
            Refined file content string
        """
        try:
            prompt = get_file_content_refinement_prompt(
                original_content=original_content,
                user_feedback=user_feedback,
                filename=filename,
                file_type=file_type,
                conversation_history=conversation_history
            )

            messages = [
                {"role": "system", "content": FILE_CONTENT_REFINEMENT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]

            logger.info(f"[FILE_CONTENT_REFINEMENT] Refining content for {filename}.{file_type} - "
                        f"model: {self.model}, original_length: {len(original_content)}")
            import time
            refinement_start = time.time()

            response = await get_chat_completion(
                messages=messages,
                model=self.model,
                temperature=0.7,
                max_tokens=4000
            )

            refinement_time = time.time() - refinement_start
            refined_content = response.get("content", "").strip()

            logger.info(f"[FILE_CONTENT_REFINEMENT] Content refined in {refinement_time:.2f}s - "
                        f"refined_length: {len(refined_content)}")

            if not refined_content:
                logger.warning(
                    f"[FILE_CONTENT_REFINEMENT] Empty refined content for {filename}.{file_type}, returning original")
                return original_content

            return refined_content

        except Exception as e:
            logger.error(
                f"[FILE_CONTENT_REFINEMENT] Error refining file content: {e}", exc_info=True)
            return original_content

    async def execute_tools(
        self,
        tool_decisions: List[ToolDecision],
        request_context: Optional[Dict[str, Any]] = None,
        user_query: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute tools programmatically in sequence.
        For file creation tools, generates content separately if not provided.

        Args:
            tool_decisions: List of ToolDecision objects to execute
            request_context: Optional context (e.g., IP address, session_id)
            user_query: Original user query (for file content generation)
            conversation_history: Conversation history (for file content generation)

        Returns:
            List of tool execution results
        """
        results = []
        import time

        logger.info(
            f"[TOOL_EXECUTION] Starting execution of {len(tool_decisions)} tool(s) in sequence")

        for idx, decision in enumerate(tool_decisions, 1):
            tool = tool_registry.get(decision.tool_name)
            if not tool:
                logger.error(
                    f"[TOOL_EXECUTION] Tool '{decision.tool_name}' not found in registry - sequence: {idx}/{len(tool_decisions)}")
                results.append({
                    "tool_name": decision.tool_name,
                    "success": False,
                    "result": f"Error: Tool '{decision.tool_name}' not found"
                })
                continue

            try:
                # Merge arguments with request context, but only include context params that tool accepts
                execute_kwargs = {**decision.arguments}
                if request_context:
                    # Get tool's parameter schema to check which parameters it accepts
                    tool_params = tool.parameters_schema.get("properties", {})
                    # Only add context parameters that are defined in the tool's schema
                    for key, value in request_context.items():
                        if key in tool_params:
                            execute_kwargs[key] = value
                        else:
                            logger.debug(
                                f"[TOOL_EXECUTION] Skipping context parameter '{key}' - not in tool schema for {decision.tool_name}")

                # Special handling for file creation: generate content if missing
                if decision.tool_name == "create_file":
                    content = execute_kwargs.get("content", "")
                    filename = execute_kwargs.get("filename", "untitled")
                    file_type = execute_kwargs.get("file_type", "txt")

                    # If content is missing or empty, generate it
                    if not content or content.strip() == "":
                        logger.info(f"[TOOL_EXECUTION] Content not provided for file creation, generating content - "
                                    f"filename: {filename}, file_type: {file_type}")

                        # Use user_query if available, otherwise use a generic prompt
                        generation_query = user_query or f"Create a {file_type} file named {filename}"

                        generated_content = await self.generate_file_content(
                            user_query=generation_query,
                            filename=filename,
                            file_type=file_type,
                            conversation_history=conversation_history
                        )

                        if generated_content:
                            execute_kwargs["content"] = generated_content
                            logger.info(
                                f"[TOOL_EXECUTION] Generated {len(generated_content)} characters of content for {filename}.{file_type}")
                        else:
                            logger.warning(
                                f"[TOOL_EXECUTION] Failed to generate content for {filename}.{file_type}, using empty content")
                            execute_kwargs["content"] = ""

                logger.info(f"[TOOL_EXECUTION] Executing tool {idx}/{len(tool_decisions)}: {decision.tool_name} "
                            f"with args: {execute_kwargs}")
                tool_start = time.time()

                # Execute tool
                tool_result = await tool.execute(**execute_kwargs)

                tool_time = time.time() - tool_start
                logger.info(f"[TOOL_EXECUTION] Tool {decision.tool_name} completed successfully in {tool_time:.2f}s - "
                            f"result_length: {len(tool_result) if tool_result else 0}")

                results.append({
                    "tool_name": decision.tool_name,
                    "success": True,
                    "result": tool_result,
                    "arguments": execute_kwargs,  # Include generated content in arguments
                    "execution_time": tool_time
                })

            except Exception as e:
                tool_time = time.time() - tool_start if 'tool_start' in locals() else 0
                error_msg = f"Error executing tool {decision.tool_name}: {str(e)}"
                logger.error(
                    f"[TOOL_EXECUTION] Tool {decision.tool_name} failed after {tool_time:.2f}s: {error_msg}", exc_info=True)
                results.append({
                    "tool_name": decision.tool_name,
                    "success": False,
                    "result": f"Error: {error_msg}",
                    "arguments": decision.arguments,
                    "execution_time": tool_time
                })

        successful = sum(1 for r in results if r.get("success", False))
        logger.info(f"[TOOL_EXECUTION] Completed execution of {len(tool_decisions)} tool(s) - "
                    f"successful: {successful}, failed: {len(tool_decisions) - successful}")
        return results

    async def format_response(
        self,
        user_query: str,
        tool_results: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Use LLM to format final response using tool results.

        Args:
            user_query: Original user query
            tool_results: Results from tool executions
            conversation_history: Previous messages for context

        Returns:
            Formatted response string
        """
        # Build prompt with tool results
        tool_results_text = ""
        for i, result in enumerate(tool_results, 1):
            tool_results_text += f"\n\nTool {i}: {result['tool_name']}\n"
            tool_results_text += f"Success: {result['success']}\n"
            tool_results_text += f"Result: {result['result']}\n"

        prompt = f"""The user asked: {user_query}

I executed the following tools and got these results:
{tool_results_text}

Please provide a helpful, natural response to the user's question based on the tool results. 
If any tools failed, mention that but still try to answer based on successful tool results.
Be conversational and don't just list the tool results - synthesize them into a natural answer."""

        try:
            messages = []

            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)

            # Add current query and tool results
            messages.append({"role": "user", "content": prompt})

            logger.info(f"[RESPONSE_FORMATTING] Calling LLM to format response - model: {self.model}, "
                        f"tool_results_count: {len(tool_results)}")
            import time
            formatting_start = time.time()

            response = await get_chat_completion(
                messages=messages,
                model=self.model,
                temperature=0.7
            )

            formatting_time = time.time() - formatting_start
            content = response.get("content", "")
            logger.debug(f"[RESPONSE_FORMATTING] LLM response received - length: {len(content) if content else 0}, "
                         f"time: {formatting_time:.2f}s")

            if not content:
                logger.warning(
                    "[RESPONSE_FORMATTING] LLM returned empty response, using fallback formatter")
                content = self._format_fallback_response(
                    user_query, tool_results)

            logger.info(f"[RESPONSE_FORMATTING] Response formatted successfully - length: {len(content)}, "
                        f"time: {formatting_time:.2f}s")
            return content

        except Exception as e:
            logger.error(
                f"[RESPONSE_FORMATTING] Error formatting response: {e}", exc_info=True)
            return self._format_fallback_response(user_query, tool_results)

    def _format_fallback_response(self, user_query: str, tool_results: List[Dict[str, Any]]) -> str:
        """Fallback response formatter if LLM fails."""
        if not tool_results:
            return "I couldn't process your request. Please try again."

        response_parts = []
        for result in tool_results:
            if result["success"]:
                response_parts.append(result["result"])
            else:
                response_parts.append(f"Error: {result['result']}")

        return "\n\n".join(response_parts)
