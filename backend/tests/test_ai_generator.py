"""
Tests for AIGenerator tool calling functionality
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from ai_generator import AIGenerator

class TestAIGenerator:
    """Test AIGenerator tool calling and response generation"""

    @pytest.fixture
    def ai_generator(self):
        """Create AIGenerator instance for testing"""
        return AIGenerator(api_key="test-key", model="claude-3-sonnet-20240229")

    @pytest.fixture 
    def mock_anthropic_client(self):
        """Mock Anthropic client"""
        with patch('anthropic.Anthropic') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            yield mock_client

    def test_generate_response_without_tools(self, ai_generator, mock_anthropic_client):
        """Test response generation without tools"""
        # Mock response from Anthropic
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "This is a general knowledge response."
        mock_response.stop_reason = "end_turn"
        
        ai_generator.client.messages.create = Mock(return_value=mock_response)
        
        result = ai_generator.generate_response("What is AI?")
        
        # Verify API was called correctly
        ai_generator.client.messages.create.assert_called_once()
        call_args = ai_generator.client.messages.create.call_args
        
        assert call_args[1]["messages"][0]["content"] == "What is AI?"
        assert "tools" not in call_args[1]
        assert result == "This is a general knowledge response."

    def test_generate_response_with_conversation_history(self, ai_generator, mock_anthropic_client):
        """Test response generation with conversation history"""
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Response with history context."
        mock_response.stop_reason = "end_turn"
        
        ai_generator.client.messages.create = Mock(return_value=mock_response)
        
        history = "User: Previous question\nAssistant: Previous answer"
        result = ai_generator.generate_response(
            "Follow up question", 
            conversation_history=history
        )
        
        # Verify system content includes history
        call_args = ai_generator.client.messages.create.call_args
        system_content = call_args[1]["system"]
        assert "Previous conversation:" in system_content
        assert history in system_content

    def test_generate_response_with_tools_no_tool_use(self, ai_generator, mock_anthropic_client):
        """Test response generation with tools available but no tool use"""
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Direct response without using tools."
        mock_response.stop_reason = "end_turn"
        
        ai_generator.client.messages.create = Mock(return_value=mock_response)
        
        tools = [{"name": "search_course_content", "description": "Search course materials"}]
        result = ai_generator.generate_response("What is AI?", tools=tools)
        
        # Verify tools were provided to API
        call_args = ai_generator.client.messages.create.call_args
        assert call_args[1]["tools"] == tools
        assert call_args[1]["tool_choice"] == {"type": "auto"}
        assert result == "Direct response without using tools."

    def test_generate_response_with_tool_use(self, ai_generator, mock_anthropic_client, tool_manager):
        """Test response generation that uses tools"""
        # Mock initial response with tool use
        initial_response = Mock()
        tool_content = Mock()
        tool_content.type = "tool_use"
        tool_content.name = "search_course_content"
        tool_content.id = "tool_123"
        tool_content.input = {"query": "MCP introduction"}
        
        initial_response.content = [tool_content]
        initial_response.stop_reason = "tool_use"
        
        # Mock final response after tool execution
        final_response = Mock()
        final_response.content = [Mock()]
        final_response.content[0].text = "Based on the course material, MCP stands for Model Context Protocol."
        
        # Setup mock client to return different responses for each call
        ai_generator.client.messages.create = Mock(side_effect=[initial_response, final_response])
        
        # Mock tool manager execution
        tool_manager.execute_tool = Mock(return_value="MCP course content from tool")
        
        tools = [{"name": "search_course_content", "description": "Search course materials"}]
        result = ai_generator.generate_response(
            "What is MCP?", 
            tools=tools, 
            tool_manager=tool_manager
        )
        
        # Verify initial API call included tools
        first_call = ai_generator.client.messages.create.call_args_list[0]
        assert first_call[1]["tools"] == tools
        
        # Verify tool was executed
        tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", 
            query="MCP introduction"
        )
        
        # Verify second API call included tool results
        second_call = ai_generator.client.messages.create.call_args_list[1]
        messages = second_call[1]["messages"]
        
        # Should have: original user message, assistant tool use, user tool result
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        
        # Check tool result format
        tool_results = messages[2]["content"]
        assert len(tool_results) == 1
        assert tool_results[0]["type"] == "tool_result"
        assert tool_results[0]["tool_use_id"] == "tool_123"
        assert tool_results[0]["content"] == "MCP course content from tool"
        
        assert result == "Based on the course material, MCP stands for Model Context Protocol."

    def test_multiple_tool_calls(self, ai_generator, mock_anthropic_client, tool_manager):
        """Test handling multiple tool calls in one response"""
        # Mock initial response with multiple tool uses
        initial_response = Mock()
        
        tool_content_1 = Mock()
        tool_content_1.type = "tool_use" 
        tool_content_1.name = "search_course_content"
        tool_content_1.id = "tool_123"
        tool_content_1.input = {"query": "MCP"}
        
        tool_content_2 = Mock()
        tool_content_2.type = "tool_use"
        tool_content_2.name = "get_course_outline" 
        tool_content_2.id = "tool_456"
        tool_content_2.input = {"course_name": "MCP"}
        
        initial_response.content = [tool_content_1, tool_content_2]
        initial_response.stop_reason = "tool_use"
        
        # Mock final response
        final_response = Mock()
        final_response.content = [Mock()]
        final_response.content[0].text = "Combined response from multiple tools."
        
        ai_generator.client.messages.create = Mock(side_effect=[initial_response, final_response])
        
        # Mock tool executions
        def mock_execute_tool(tool_name, **kwargs):
            if tool_name == "search_course_content":
                return "Search result content"
            elif tool_name == "get_course_outline":
                return "Course outline content"
            return "Unknown tool"
        
        tool_manager.execute_tool = Mock(side_effect=mock_execute_tool)
        
        tools = [
            {"name": "search_course_content", "description": "Search"},
            {"name": "get_course_outline", "description": "Get outline"}
        ]
        
        result = ai_generator.generate_response(
            "Tell me about MCP course", 
            tools=tools,
            tool_manager=tool_manager
        )
        
        # Verify both tools were executed
        assert tool_manager.execute_tool.call_count == 2
        tool_manager.execute_tool.assert_any_call("search_course_content", query="MCP")
        tool_manager.execute_tool.assert_any_call("get_course_outline", course_name="MCP")
        
        # Verify final message contains both tool results
        second_call = ai_generator.client.messages.create.call_args_list[1]
        tool_results = second_call[1]["messages"][2]["content"]
        assert len(tool_results) == 2
        
        # Check both tool results are present
        tool_ids = [tr["tool_use_id"] for tr in tool_results]
        assert "tool_123" in tool_ids
        assert "tool_456" in tool_ids

    def test_tool_execution_error_handling(self, ai_generator, mock_anthropic_client, tool_manager):
        """Test handling when tool execution fails"""
        # Mock initial response with tool use
        initial_response = Mock()
        tool_content = Mock()
        tool_content.type = "tool_use"
        tool_content.name = "search_course_content"
        tool_content.id = "tool_123"
        tool_content.input = {"query": "test"}
        
        initial_response.content = [tool_content]
        initial_response.stop_reason = "tool_use"
        
        # Mock final response
        final_response = Mock()
        final_response.content = [Mock()]
        final_response.content[0].text = "I apologize, but I encountered an error."
        
        ai_generator.client.messages.create = Mock(side_effect=[initial_response, final_response])
        
        # Mock tool manager to return error
        tool_manager.execute_tool = Mock(return_value="Tool execution failed: Database error")
        
        result = ai_generator.generate_response(
            "Search query", 
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager
        )
        
        # Verify tool error was passed to final API call
        second_call = ai_generator.client.messages.create.call_args_list[1]
        tool_results = second_call[1]["messages"][2]["content"]
        assert tool_results[0]["content"] == "Tool execution failed: Database error"

    def test_system_prompt_content(self, ai_generator, mock_anthropic_client):
        """Test that system prompt contains correct tool guidance"""
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Test response."
        mock_response.stop_reason = "end_turn"
        
        ai_generator.client.messages.create = Mock(return_value=mock_response)
        
        ai_generator.generate_response("Test query")
        
        # Check system prompt content
        call_args = ai_generator.client.messages.create.call_args
        system_content = call_args[1]["system"]
        
        # Verify key components of system prompt
        assert "search_course_content" in system_content
        assert "get_course_outline" in system_content
        assert "Course outline queries" in system_content
        assert "Content search queries" in system_content
        assert "One tool call per query maximum" in system_content

    def test_api_parameters(self, ai_generator, mock_anthropic_client):
        """Test that API parameters are correctly set"""
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Test response."
        mock_response.stop_reason = "end_turn"
        
        ai_generator.client.messages.create = Mock(return_value=mock_response)
        
        ai_generator.generate_response("Test query")
        
        call_args = ai_generator.client.messages.create.call_args
        params = call_args[1]
        
        # Verify base parameters
        assert params["model"] == "claude-3-sonnet-20240229"
        assert params["temperature"] == 0
        assert params["max_tokens"] == 800
        assert params["messages"][0]["role"] == "user"
        assert params["messages"][0]["content"] == "Test query"

    def test_tool_use_without_tool_manager(self, ai_generator, mock_anthropic_client):
        """Test tool use response when no tool manager is provided"""
        # Mock response with tool use but no tool manager
        tool_response = Mock()
        tool_content = Mock()
        tool_content.type = "tool_use"
        tool_content.name = "search_course_content"
        tool_content.id = "tool_123"
        
        tool_response.content = [tool_content]
        tool_response.stop_reason = "tool_use"
        
        ai_generator.client.messages.create = Mock(return_value=tool_response)
        
        # Should return graceful error message when no tool_manager
        result = ai_generator.generate_response(
            "Test query", 
            tools=[{"name": "search_course_content"}],
            tool_manager=None  # No tool manager
        )
        
        # Should return graceful error message
        assert result == "I apologize, but I'm unable to access the necessary tools to answer your question right now."

class TestAIGeneratorSystemPrompt:
    """Test system prompt functionality and tool selection guidance"""

    def test_system_prompt_structure(self):
        """Test that system prompt has required sections"""
        prompt = AIGenerator.SYSTEM_PROMPT
        
        # Check for required sections
        assert "Available Tools:" in prompt
        assert "search_course_content" in prompt
        assert "get_course_outline" in prompt
        assert "Tool Usage Guidelines:" in prompt
        assert "Response Protocol:" in prompt
        
        # Check for tool selection guidance
        assert "Course outline queries" in prompt
        assert "Content search queries" in prompt
        assert "One tool call per query maximum" in prompt

    def test_response_guidelines(self):
        """Test that response guidelines are present"""
        prompt = AIGenerator.SYSTEM_PROMPT
        
        assert "Brief, Concise and focused" in prompt
        assert "Educational" in prompt
        assert "Clear" in prompt
        assert "Example-supported" in prompt
        assert "No meta-commentary" in prompt