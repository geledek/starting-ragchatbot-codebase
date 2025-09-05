from typing import Any, Dict, List, Optional

import anthropic


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive search tools for course information.

Available Tools:
1. **search_course_content**: For finding specific content within courses (lessons, topics, concepts)
2. **get_course_outline**: For retrieving complete course structure (title, instructor, lesson list with links)

Tool Usage Guidelines:
- **Course outline queries**: Use get_course_outline for questions asking about course structure, lesson lists, outlines, or "what's in this course"
- **Content search queries**: Use search_course_content for questions about specific topics, concepts, or detailed course material
- **Sequential tool calling**: You can make multiple tool calls across rounds to gather comprehensive information
- **Progressive reasoning**: Use results from previous tool calls to inform subsequent searches
- Synthesize results into accurate, fact-based responses
- If tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without tools
- **Course outline questions**: Use get_course_outline tool, then present the complete structure with course title, instructor, lesson count, and full lesson list with clickable links
- **Course content questions**: Use search_course_content tool, then answer based on found content
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the tool"

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
        max_tool_rounds: int = 2,
    ) -> str:
        """
        Generate AI response with sequential tool calling support.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            max_tool_rounds: Maximum number of tool calling rounds (default: 2)

        Returns:
            Generated response as string
        """

        # Build system content efficiently
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Initialize message history for sequential tool calling
        messages = [{"role": "user", "content": query}]

        # Sequential tool calling loop
        for _ in range(max_tool_rounds):
            # Prepare API call parameters
            api_params = {
                **self.base_params,
                "messages": messages.copy(),
                "system": system_content,
            }

            # Add tools if available
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = {"type": "auto"}

            try:
                # Get response from Claude
                response = self.client.messages.create(**api_params)

                # Add Claude's response to message history
                messages.append({"role": "assistant", "content": response.content})

                # Check if Claude wants to use tools
                if response.stop_reason == "tool_use":
                    if not tool_manager:
                        return "I apologize, but I'm unable to access the necessary tools to answer your question right now."

                    # Execute tool calls and add results
                    tool_results = self._execute_tool_calls(response, tool_manager)
                    if tool_results is None:  # Tool execution failed
                        return "I apologize, but I encountered an error while executing the requested tools."

                    messages.append({"role": "user", "content": tool_results})

                    # Continue to next round for follow-up reasoning
                    continue
                else:
                    # No tool use - Claude provided final answer
                    if response.content and len(response.content) > 0:
                        # Handle different content types
                        for content_block in response.content:
                            if hasattr(content_block, "text"):
                                return content_block.text
                        return "I apologize, but the AI response contained no text content."
                    else:
                        return (
                            "I apologize, but I received an empty response from the AI."
                        )

            except Exception as e:
                # Handle API errors gracefully
                return f"I apologize, but I encountered an error while processing your request: {str(e)}"

        # Max rounds reached - make final call without tools to get response
        # If the last message is from user (tool results), the API expects an assistant response
        if messages and messages[-1]["role"] == "user":
            final_params = {
                **self.base_params,
                "messages": messages,
                "system": system_content,
            }

            try:
                final_response = self.client.messages.create(**final_params)

                if final_response.content and len(final_response.content) > 0:
                    # Handle different content types
                    for content_block in final_response.content:
                        if hasattr(content_block, "text"):
                            return content_block.text
                    return "I apologize, but the AI response contained no text content."
                else:
                    return "I apologize, but I received an empty response from the AI."
            except Exception as e:
                return f"I apologize, but I encountered an error while generating the final response: {str(e)}"
        else:
            # Conversation ended with assistant message - shouldn't happen in our logic
            return "I apologize, but the conversation ended unexpectedly."

    def _execute_tool_calls(
        self, response, tool_manager
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Execute all tool calls in a response and return formatted results.

        Args:
            response: The response containing tool use requests
            tool_manager: Manager to execute tools

        Returns:
            List of tool results, or None if execution failed
        """
        tool_results = []

        for content_block in response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result,
                        }
                    )

                except Exception:
                    # Tool execution failed - return None to terminate sequence
                    return None

        return tool_results if tool_results else None
