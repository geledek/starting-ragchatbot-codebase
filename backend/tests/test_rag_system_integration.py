"""
Integration tests for RAG system end-to-end functionality
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from rag_system import RAGSystem
from session_manager import SessionManager
from vector_store import SearchResults


class TestRAGSystemIntegration:
    """Test end-to-end RAG system functionality"""

    @pytest.fixture
    def mock_rag_system(self, mock_config):
        """Create RAG system with mocked components"""
        with (
            patch("rag_system.VectorStore") as mock_vector_store_class,
            patch("rag_system.AIGenerator") as mock_ai_generator_class,
            patch("rag_system.SessionManager") as mock_session_manager_class,
            patch("rag_system.DocumentProcessor") as mock_doc_processor_class,
        ):

            # Create mock instances
            mock_vector_store = Mock()
            mock_ai_generator = Mock()
            mock_session_manager = Mock()
            mock_doc_processor = Mock()

            # Configure mock classes to return mock instances
            mock_vector_store_class.return_value = mock_vector_store
            mock_ai_generator_class.return_value = mock_ai_generator
            mock_session_manager_class.return_value = mock_session_manager
            mock_doc_processor_class.return_value = mock_doc_processor

            # Create RAG system
            rag_system = RAGSystem(mock_config)

            # Store references to mocks for test access
            rag_system._mock_vector_store = mock_vector_store
            rag_system._mock_ai_generator = mock_ai_generator
            rag_system._mock_session_manager = mock_session_manager
            rag_system._mock_doc_processor = mock_doc_processor

            return rag_system

    def test_content_query_workflow(self, mock_rag_system):
        """Test complete workflow for content-related questions"""
        # Setup mocks
        mock_rag_system._mock_session_manager.get_conversation_history.return_value = (
            None
        )
        mock_rag_system._mock_ai_generator.generate_response.return_value = "MCP is a Model Context Protocol that enables rich context sharing between AI models."

        # Mock tool manager to simulate successful search
        mock_rag_system.tool_manager.get_last_sources = Mock(
            return_value=[
                {
                    "display": "MCP Course - Lesson 1",
                    "link": "https://example.com/mcp/lesson-1",
                }
            ]
        )
        mock_rag_system.tool_manager.reset_sources = Mock()
        mock_rag_system.tool_manager.get_tool_definitions = Mock(
            return_value=[
                {
                    "name": "search_course_content",
                    "description": "Search course materials",
                }
            ]
        )

        # Execute query
        response, sources = mock_rag_system.query("What is MCP?")

        # Verify workflow
        mock_rag_system._mock_ai_generator.generate_response.assert_called_once()
        call_args = mock_rag_system._mock_ai_generator.generate_response.call_args

        # Check that query was formatted correctly (using keyword argument)
        assert (
            call_args[1]["query"]
            == "Answer this question about course materials: What is MCP?"
        )

        # Check that tools were provided
        assert call_args[1]["tools"] is not None
        assert call_args[1]["tool_manager"] == mock_rag_system.tool_manager

        # Check response and sources
        assert (
            response
            == "MCP is a Model Context Protocol that enables rich context sharing between AI models."
        )
        assert len(sources) == 1
        assert sources[0]["display"] == "MCP Course - Lesson 1"

        # Verify sources were reset after retrieval
        mock_rag_system.tool_manager.reset_sources.assert_called_once()

    def test_outline_query_workflow(self, mock_rag_system):
        """Test complete workflow for course outline questions"""
        # Mock AI response for outline query
        outline_response = """**Course:** [MCP: Build Rich-Context AI Apps with Anthropic](https://example.com/mcp-course)
**Instructor:** John Smith
**Total Lessons:** 3

**Course Outline:**
1. [Introduction to MCP](https://example.com/mcp-course/lesson-1)
2. [Building Your First MCP Server](https://example.com/mcp-course/lesson-2)
3. [Advanced MCP Patterns](https://example.com/mcp-course/lesson-3)"""

        mock_rag_system._mock_ai_generator.generate_response.return_value = (
            outline_response
        )
        mock_rag_system.tool_manager.get_last_sources = Mock(return_value=[])

        response, sources = mock_rag_system.query(
            "What is the outline of the MCP course?"
        )

        # Verify AI generator was called with formatted outline query
        call_args = mock_rag_system._mock_ai_generator.generate_response.call_args
        assert (
            call_args[1]["query"]
            == "Answer this question about course materials: What is the outline of the MCP course?"
        )

        # Verify response contains outline structure
        assert "**Course:**" in response
        assert "**Instructor:**" in response
        assert "**Total Lessons:**" in response
        assert "**Course Outline:**" in response
        assert "[MCP: Build Rich-Context AI Apps with Anthropic]" in response

    def test_session_management(self, mock_rag_system):
        """Test conversation history and session management"""
        session_id = "test_session_123"
        history = "User: Previous question\nAssistant: Previous answer"

        # Mock session manager
        mock_rag_system._mock_session_manager.get_conversation_history.return_value = (
            history
        )
        mock_rag_system._mock_ai_generator.generate_response.return_value = (
            "Follow-up response"
        )

        response, sources = mock_rag_system.query(
            "Follow-up question", session_id=session_id
        )

        # Verify session history was retrieved
        mock_rag_system._mock_session_manager.get_conversation_history.assert_called_once_with(
            session_id
        )

        # Verify history was passed to AI generator
        call_args = mock_rag_system._mock_ai_generator.generate_response.call_args
        assert call_args[1]["conversation_history"] == history

        # Verify conversation was updated with original query (not formatted prompt)
        mock_rag_system._mock_session_manager.add_exchange.assert_called_once_with(
            session_id,
            "Follow-up question",  # Original user query, not formatted prompt
            "Follow-up response",
        )

    def test_query_without_session(self, mock_rag_system):
        """Test query processing without session ID"""
        mock_rag_system._mock_ai_generator.generate_response.return_value = (
            "Response without session"
        )

        response, sources = mock_rag_system.query("Test question")  # No session_id

        # Verify no session operations were called
        mock_rag_system._mock_session_manager.get_conversation_history.assert_not_called()
        mock_rag_system._mock_session_manager.add_exchange.assert_not_called()

        # Verify AI generator was called without history
        call_args = mock_rag_system._mock_ai_generator.generate_response.call_args
        assert call_args[1]["conversation_history"] is None

    def test_error_handling_in_query(self, mock_rag_system):
        """Test error handling during query processing"""
        # Mock AI generator to raise exception
        mock_rag_system._mock_ai_generator.generate_response.side_effect = Exception(
            "API Error"
        )

        # Query should handle error gracefully
        with pytest.raises(Exception) as exc_info:
            mock_rag_system.query("Test question")

        assert "API Error" in str(exc_info.value)

    def test_tool_integration(self, mock_rag_system):
        """Test that tools are properly integrated and available"""
        # Verify tools were registered during initialization
        assert len(mock_rag_system.tool_manager.tools) == 2
        assert "search_course_content" in mock_rag_system.tool_manager.tools
        assert "get_course_outline" in mock_rag_system.tool_manager.tools

        # Verify tool definitions are available
        definitions = mock_rag_system.tool_manager.get_tool_definitions()
        assert len(definitions) == 2

        tool_names = [def_["name"] for def_ in definitions]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names

    def test_source_tracking_workflow(self, mock_rag_system):
        """Test end-to-end source tracking"""
        # Mock sources from tool execution
        mock_sources = [
            {
                "display": "MCP Course - Lesson 1",
                "link": "https://example.com/lesson-1",
            },
            {
                "display": "RAG Systems - Lesson 2",
                "link": "https://example.com/rag/lesson-2",
            },
        ]

        mock_rag_system.tool_manager.get_last_sources = Mock(return_value=mock_sources)
        mock_rag_system.tool_manager.reset_sources = Mock()
        mock_rag_system._mock_ai_generator.generate_response.return_value = (
            "Test response"
        )

        response, sources = mock_rag_system.query("Test query")

        # Verify sources were retrieved and returned
        assert sources == mock_sources

        # Verify sources were reset after retrieval
        mock_rag_system.tool_manager.reset_sources.assert_called_once()

    def test_course_analytics(self, mock_rag_system):
        """Test course analytics functionality"""
        # Mock vector store analytics methods
        mock_rag_system._mock_vector_store.get_course_count.return_value = 3
        mock_rag_system._mock_vector_store.get_existing_course_titles.return_value = [
            "MCP: Build Rich-Context AI Apps with Anthropic",
            "Introduction to RAG Systems",
            "Building Chatbots with LLMs",
        ]

        analytics = mock_rag_system.get_course_analytics()

        # Verify analytics structure
        assert "total_courses" in analytics
        assert "course_titles" in analytics
        assert analytics["total_courses"] == 3
        assert len(analytics["course_titles"]) == 3


class TestRAGSystemDocumentProcessing:
    """Test document processing and vector store integration"""

    @pytest.fixture
    def mock_rag_system_with_processing(self, mock_config):
        """RAG system with document processing mocks"""
        with (
            patch("rag_system.VectorStore") as mock_vs,
            patch("rag_system.AIGenerator") as mock_ai,
            patch("rag_system.SessionManager") as mock_sm,
            patch("rag_system.DocumentProcessor") as mock_dp,
        ):

            mock_vector_store = Mock()
            mock_ai_generator = Mock()
            mock_session_manager = Mock()
            mock_doc_processor = Mock()

            mock_vs.return_value = mock_vector_store
            mock_ai.return_value = mock_ai_generator
            mock_sm.return_value = mock_session_manager
            mock_dp.return_value = mock_doc_processor

            rag_system = RAGSystem(mock_config)
            rag_system._mock_doc_processor = mock_doc_processor
            rag_system._mock_vector_store = mock_vector_store

            return rag_system

    def test_add_course_document(self, mock_rag_system_with_processing, sample_courses):
        """Test adding a single course document"""
        from models import Course, CourseChunk, Lesson

        # Create mock course and chunks
        mock_course = Course(
            title="Test Course",
            instructor="Test Instructor",
            course_link="https://example.com/test",
            lessons=[
                Lesson(
                    lesson_number=1,
                    title="Lesson 1",
                    lesson_link="https://example.com/lesson1",
                )
            ],
        )

        mock_chunks = [
            CourseChunk(
                course_title="Test Course",
                lesson_number=1,
                chunk_index=0,
                content="Test course content",
            )
        ]

        # Mock document processor
        mock_rag_system_with_processing._mock_doc_processor.process_course_document.return_value = (
            mock_course,
            mock_chunks,
        )

        course, chunk_count = mock_rag_system_with_processing.add_course_document(
            "/path/to/test.pdf"
        )

        # Verify document was processed
        mock_rag_system_with_processing._mock_doc_processor.process_course_document.assert_called_once_with(
            "/path/to/test.pdf"
        )

        # Verify metadata and content were added to vector store
        mock_rag_system_with_processing._mock_vector_store.add_course_metadata.assert_called_once_with(
            mock_course
        )
        mock_rag_system_with_processing._mock_vector_store.add_course_content.assert_called_once_with(
            mock_chunks
        )

        # Verify return values
        assert course.title == "Test Course"
        assert chunk_count == 1

    def test_add_course_document_error(self, mock_rag_system_with_processing):
        """Test error handling during document processing"""
        # Mock document processor to raise exception
        mock_rag_system_with_processing._mock_doc_processor.process_course_document.side_effect = Exception(
            "Processing error"
        )

        course, chunk_count = mock_rag_system_with_processing.add_course_document(
            "/path/to/bad.pdf"
        )

        # Should return None and 0 on error
        assert course is None
        assert chunk_count == 0

        # Vector store should not be called
        mock_rag_system_with_processing._mock_vector_store.add_course_metadata.assert_not_called()
        mock_rag_system_with_processing._mock_vector_store.add_course_content.assert_not_called()


class TestRAGSystemQueryTypes:
    """Test how RAG system handles different query types"""

    @pytest.fixture
    def rag_with_real_tools(self, mock_config):
        """RAG system with real tools but mocked vector store and AI"""
        with (
            patch("rag_system.VectorStore") as mock_vs,
            patch("rag_system.AIGenerator") as mock_ai,
            patch("rag_system.SessionManager") as mock_sm,
            patch("rag_system.DocumentProcessor") as mock_dp,
        ):

            # Create real vector store mock with proper methods
            mock_vector_store = Mock()
            mock_vector_store.search.return_value = SearchResults(
                documents=["Test content"],
                metadata=[{"course_title": "Test Course", "lesson_number": 1}],
                distances=[0.1],
            )
            mock_vector_store._resolve_course_name.return_value = "Test Course"
            mock_vector_store.get_lesson_link.return_value = (
                "https://example.com/lesson1"
            )

            # Mock course catalog for outline tool
            catalog_data = {
                "metadatas": [  # List of metadata dictionaries
                    {
                        "title": "Test Course",
                        "instructor": "Test Instructor",
                        "course_link": "https://example.com/course",
                        "lessons_json": json.dumps(
                            [
                                {
                                    "lesson_number": 1,
                                    "lesson_title": "Lesson 1",
                                    "lesson_link": "https://example.com/lesson1",
                                }
                            ]
                        ),
                        "lesson_count": 1,
                    }
                ]
            }
            mock_vector_store.course_catalog.get.return_value = catalog_data

            mock_vs.return_value = mock_vector_store
            mock_ai.return_value = Mock()
            mock_sm.return_value = Mock()
            mock_dp.return_value = Mock()

            rag_system = RAGSystem(mock_config)
            rag_system._mock_vector_store = mock_vector_store
            return rag_system

    def test_content_search_tool_execution(self, rag_with_real_tools):
        """Test that content search tool executes correctly"""
        search_tool = rag_with_real_tools.search_tool

        result = search_tool.execute("test query", course_name="Test Course")

        # Verify vector store search was called
        rag_with_real_tools._mock_vector_store.search.assert_called_once_with(
            query="test query", course_name="Test Course", lesson_number=None
        )

        # Verify result format
        assert "[Test Course - Lesson 1]" in result
        assert "Test content" in result

        # Verify sources were tracked
        assert len(search_tool.last_sources) == 1
        assert search_tool.last_sources[0]["display"] == "Test Course - Lesson 1"

    def test_outline_tool_execution(self, rag_with_real_tools):
        """Test that outline tool executes correctly"""
        outline_tool = rag_with_real_tools.outline_tool

        result = outline_tool.execute("Test Course")

        # Verify course resolution was called
        rag_with_real_tools._mock_vector_store._resolve_course_name.assert_called_once_with(
            "Test Course"
        )

        # Verify catalog was queried
        rag_with_real_tools._mock_vector_store.course_catalog.get.assert_called_once_with(
            ids=["Test Course"]
        )

        # Verify result format
        assert "**Course:** [Test Course](https://example.com/course)" in result
        assert "**Instructor:** Test Instructor" in result
        assert "**Total Lessons:** 1" in result
        assert "1. [Lesson 1](https://example.com/lesson1)" in result

    def test_tool_manager_integration(self, rag_with_real_tools):
        """Test tool manager correctly routes to tools"""
        tool_manager = rag_with_real_tools.tool_manager

        # Test content search execution
        search_result = tool_manager.execute_tool(
            "search_course_content", query="test", course_name="Test"
        )
        assert "[Test Course - Lesson 1]" in search_result

        # Test outline execution
        outline_result = tool_manager.execute_tool(
            "get_course_outline", course_name="Test Course"
        )
        assert "**Course:** [Test Course]" in outline_result

        # Test unknown tool
        error_result = tool_manager.execute_tool("unknown_tool", query="test")
        assert "Tool 'unknown_tool' not found" in error_result
