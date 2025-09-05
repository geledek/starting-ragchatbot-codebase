"""
Unit tests for CourseSearchTool and CourseOutlineTool in search_tools.py
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from search_tools import CourseOutlineTool, CourseSearchTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchTool:
    """Test CourseSearchTool.execute() method outputs"""

    def test_tool_definition(self, course_search_tool):
        """Test that tool definition is properly structured"""
        definition = course_search_tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["input_schema"]["type"] == "object"
        assert "query" in definition["input_schema"]["properties"]
        assert definition["input_schema"]["required"] == ["query"]

    def test_successful_search_with_results(
        self, course_search_tool, mock_chroma_search_results
    ):
        """Test successful content search returning results"""
        # Setup mock vector store to return search results
        mock_results = SearchResults.from_chroma(mock_chroma_search_results)
        course_search_tool.store.search = Mock(return_value=mock_results)

        result = course_search_tool.execute("MCP introduction")

        # Verify search was called
        course_search_tool.store.search.assert_called_once_with(
            query="MCP introduction", course_name=None, lesson_number=None
        )

        # Verify result format
        assert isinstance(result, str)
        assert "MCP: Build Rich-Context AI Apps with Anthropic" in result
        assert "MCP (Model Context Protocol)" in result
        assert len(course_search_tool.last_sources) == 2

    def test_search_with_course_filter(self, course_search_tool):
        """Test search with course name filter"""
        mock_results = SearchResults(
            documents=["Test content"],
            metadata=[{"course_title": "MCP Course", "lesson_number": 1}],
            distances=[0.1],
        )
        course_search_tool.store.search = Mock(return_value=mock_results)

        result = course_search_tool.execute("introduction", course_name="MCP")

        course_search_tool.store.search.assert_called_once_with(
            query="introduction", course_name="MCP", lesson_number=None
        )
        assert "MCP Course" in result

    def test_search_with_lesson_filter(self, course_search_tool):
        """Test search with lesson number filter"""
        mock_results = SearchResults(
            documents=["Lesson 2 content"],
            metadata=[{"course_title": "MCP Course", "lesson_number": 2}],
            distances=[0.1],
        )
        course_search_tool.store.search = Mock(return_value=mock_results)

        result = course_search_tool.execute("server", lesson_number=2)

        course_search_tool.store.search.assert_called_once_with(
            query="server", course_name=None, lesson_number=2
        )
        assert "Lesson 2" in result

    def test_empty_search_results(self, course_search_tool):
        """Test handling when no content is found"""
        empty_results = SearchResults(documents=[], metadata=[], distances=[])
        course_search_tool.store.search = Mock(return_value=empty_results)

        result = course_search_tool.execute("nonexistent topic")

        assert result == "No relevant content found."

    def test_empty_results_with_filters(self, course_search_tool):
        """Test empty results message includes filter information"""
        empty_results = SearchResults(documents=[], metadata=[], distances=[])
        course_search_tool.store.search = Mock(return_value=empty_results)

        result = course_search_tool.execute(
            "topic", course_name="Nonexistent", lesson_number=5
        )

        assert (
            "No relevant content found in course 'Nonexistent' in lesson 5." in result
        )

    def test_search_error_handling(self, course_search_tool):
        """Test handling of search errors"""
        error_results = SearchResults(
            documents=[], metadata=[], distances=[], error="Database connection failed"
        )
        course_search_tool.store.search = Mock(return_value=error_results)

        result = course_search_tool.execute("test query")

        assert result == "Database connection failed"

    def test_source_link_generation_with_lesson(self, course_search_tool):
        """Test source link generation for lesson-specific content"""
        mock_results = SearchResults(
            documents=["Test content"],
            metadata=[{"course_title": "MCP Course", "lesson_number": 1}],
            distances=[0.1],
        )
        course_search_tool.store.search = Mock(return_value=mock_results)
        course_search_tool.store.get_lesson_link = Mock(
            return_value="https://example.com/lesson-1"
        )

        result = course_search_tool.execute("test")

        # Check that lesson link was requested
        course_search_tool.store.get_lesson_link.assert_called_once_with(
            "MCP Course", 1
        )

        # Check that source was tracked
        assert len(course_search_tool.last_sources) == 1
        assert course_search_tool.last_sources[0]["display"] == "MCP Course - Lesson 1"
        assert (
            course_search_tool.last_sources[0]["link"] == "https://example.com/lesson-1"
        )

    def test_source_link_generation_course_only(self, course_search_tool):
        """Test source link generation for course-level content"""
        mock_results = SearchResults(
            documents=["Test content"],
            metadata=[{"course_title": "MCP Course"}],  # No lesson_number
            distances=[0.1],
        )
        course_search_tool.store.search = Mock(return_value=mock_results)
        course_search_tool.store.get_course_link = Mock(
            return_value="https://example.com/course"
        )

        result = course_search_tool.execute("test")

        # Check that course link was requested
        course_search_tool.store.get_course_link.assert_called_once_with("MCP Course")

        # Check that source was tracked
        assert len(course_search_tool.last_sources) == 1
        assert course_search_tool.last_sources[0]["display"] == "MCP Course"
        assert (
            course_search_tool.last_sources[0]["link"] == "https://example.com/course"
        )

    def test_result_formatting(self, course_search_tool):
        """Test proper formatting of search results"""
        mock_results = SearchResults(
            documents=["First chunk", "Second chunk"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2},
            ],
            distances=[0.1, 0.2],
        )
        course_search_tool.store.search = Mock(return_value=mock_results)

        result = course_search_tool.execute("test")

        # Check formatting structure
        lines = result.split("\n")
        assert "[Course A - Lesson 1]" in result
        assert "[Course B - Lesson 2]" in result
        assert "First chunk" in result
        assert "Second chunk" in result

        # Check that results are separated by double newlines
        assert "\n\n" in result


class TestCourseOutlineTool:
    """Test CourseOutlineTool.execute() method outputs"""

    def test_outline_tool_definition(self, course_outline_tool):
        """Test outline tool definition structure"""
        definition = course_outline_tool.get_tool_definition()

        assert definition["name"] == "get_course_outline"
        assert "description" in definition
        assert "course_name" in definition["input_schema"]["properties"]
        assert definition["input_schema"]["required"] == ["course_name"]

    def test_successful_outline_retrieval(
        self, course_outline_tool, mock_chroma_catalog_results
    ):
        """Test successful course outline retrieval"""
        # Mock course name resolution
        course_outline_tool.store._resolve_course_name = Mock(
            return_value="MCP: Build Rich-Context AI Apps with Anthropic"
        )

        # Mock catalog get method
        course_outline_tool.store.course_catalog.get = Mock(
            return_value=mock_chroma_catalog_results
        )

        result = course_outline_tool.execute("MCP")

        # Verify course resolution was called
        course_outline_tool.store._resolve_course_name.assert_called_once_with("MCP")

        # Verify catalog query was called
        course_outline_tool.store.course_catalog.get.assert_called_once_with(
            ids=["MCP: Build Rich-Context AI Apps with Anthropic"]
        )

        # Verify result format
        assert "**Course:** [MCP: Build Rich-Context AI Apps with Anthropic]" in result
        assert "**Instructor:** John Smith" in result
        assert "**Total Lessons:** 2" in result
        assert "1. [Introduction to MCP]" in result
        assert "2. [Building Your First MCP Server]" in result

    def test_course_not_found(self, course_outline_tool):
        """Test handling when course name cannot be resolved"""
        course_outline_tool.store._resolve_course_name = Mock(return_value=None)

        result = course_outline_tool.execute("Nonexistent Course")

        assert result == "No course found matching 'Nonexistent Course'"

    def test_metadata_not_found(self, course_outline_tool):
        """Test handling when course metadata is missing"""
        course_outline_tool.store._resolve_course_name = Mock(
            return_value="Test Course"
        )
        course_outline_tool.store.course_catalog.get = Mock(
            return_value={"metadatas": []}  # Empty metadata
        )

        result = course_outline_tool.execute("Test Course")

        assert "Course metadata not found for 'Test Course'" in result

    def test_outline_formatting_without_links(self, course_outline_tool):
        """Test outline formatting when course/lesson links are missing"""
        course_outline_tool.store._resolve_course_name = Mock(
            return_value="Test Course"
        )

        # Mock catalog data without links
        catalog_data = {
            "metadatas": [
                {
                    "title": "Test Course",
                    "instructor": "Test Instructor",
                    "course_link": None,  # No course link
                    "lessons_json": json.dumps(
                        [
                            {
                                "lesson_number": 1,
                                "lesson_title": "Lesson 1",
                                "lesson_link": None,  # No lesson link
                            }
                        ]
                    ),
                    "lesson_count": 1,
                }
            ]
        }
        course_outline_tool.store.course_catalog.get = Mock(return_value=catalog_data)

        result = course_outline_tool.execute("Test Course")

        # Should show course and lesson without links
        assert "**Course:** Test Course" in result  # No link brackets
        assert "1. Lesson 1" in result  # No link brackets

    def test_json_parsing_error(self, course_outline_tool):
        """Test handling of malformed JSON in lessons data"""
        course_outline_tool.store._resolve_course_name = Mock(
            return_value="Test Course"
        )

        catalog_data = {
            "metadatas": [
                {
                    "title": "Test Course",
                    "instructor": "Test Instructor",
                    "course_link": None,
                    "lessons_json": "invalid json{",  # Malformed JSON
                    "lesson_count": 1,
                }
            ]
        }
        course_outline_tool.store.course_catalog.get = Mock(return_value=catalog_data)

        result = course_outline_tool.execute("Test Course")

        assert "Error parsing lesson data for course 'Test Course'" in result

    def test_outline_exception_handling(self, course_outline_tool):
        """Test handling of unexpected exceptions"""
        course_outline_tool.store._resolve_course_name = Mock(
            return_value="Test Course"
        )
        course_outline_tool.store.course_catalog.get = Mock(
            side_effect=Exception("Database error")
        )

        result = course_outline_tool.execute("Test Course")

        assert "Error retrieving course outline: Database error" in result


class TestToolManager:
    """Test ToolManager functionality"""

    def test_tool_registration(self, tool_manager):
        """Test that tools are properly registered"""
        definitions = tool_manager.get_tool_definitions()

        assert len(definitions) == 2
        tool_names = [def_["name"] for def_ in definitions]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names

    def test_tool_execution(self, tool_manager):
        """Test tool execution through manager"""
        # Mock the search tool's execute method
        search_tool = tool_manager.tools["search_course_content"]
        search_tool.execute = Mock(return_value="Test search result")

        result = tool_manager.execute_tool("search_course_content", query="test query")

        assert result == "Test search result"
        search_tool.execute.assert_called_once_with(query="test query")

    def test_tool_not_found(self, tool_manager):
        """Test handling of unknown tool names"""
        result = tool_manager.execute_tool("nonexistent_tool", query="test")

        assert result == "Tool 'nonexistent_tool' not found"

    def test_source_tracking(self, tool_manager):
        """Test source tracking across tools"""
        # Mock search tool with sources
        search_tool = tool_manager.tools["search_course_content"]
        search_tool.last_sources = [{"display": "Test Course", "link": "test-link"}]

        sources = tool_manager.get_last_sources()

        assert len(sources) == 1
        assert sources[0]["display"] == "Test Course"
        assert sources[0]["link"] == "test-link"

    def test_source_reset(self, tool_manager):
        """Test source reset functionality"""
        # Set sources on search tool
        search_tool = tool_manager.tools["search_course_content"]
        search_tool.last_sources = [{"display": "Test", "link": "test"}]

        # Reset sources
        tool_manager.reset_sources()

        # Verify sources are cleared
        sources = tool_manager.get_last_sources()
        assert len(sources) == 0
