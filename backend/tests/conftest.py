"""
Shared test fixtures and configuration for RAG system tests.
"""
import pytest
import json
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List

# Add parent directory to path so we can import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import for API testing
from fastapi.testclient import TestClient
from fastapi import FastAPI
import httpx

from vector_store import VectorStore, SearchResults
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from ai_generator import AIGenerator
from rag_system import RAGSystem
from models import Course, Lesson, CourseChunk

@pytest.fixture
def sample_courses():
    """Sample course data for testing"""
    return [
        {
            "title": "MCP: Build Rich-Context AI Apps with Anthropic",
            "instructor": "John Smith", 
            "course_link": "https://example.com/mcp-course",
            "lessons": [
                {
                    "lesson_number": 1,
                    "lesson_title": "Introduction to MCP",
                    "lesson_link": "https://example.com/mcp-course/lesson-1"
                },
                {
                    "lesson_number": 2,
                    "lesson_title": "Building Your First MCP Server",
                    "lesson_link": "https://example.com/mcp-course/lesson-2"
                },
                {
                    "lesson_number": 3,
                    "lesson_title": "Advanced MCP Patterns",
                    "lesson_link": "https://example.com/mcp-course/lesson-3"
                }
            ]
        },
        {
            "title": "Introduction to RAG Systems",
            "instructor": "Jane Doe",
            "course_link": "https://example.com/rag-course",
            "lessons": [
                {
                    "lesson_number": 1,
                    "lesson_title": "What is RAG?",
                    "lesson_link": "https://example.com/rag-course/lesson-1"
                },
                {
                    "lesson_number": 2,
                    "lesson_title": "Vector Databases",
                    "lesson_link": "https://example.com/rag-course/lesson-2"
                }
            ]
        }
    ]

@pytest.fixture
def sample_course_chunks():
    """Sample course content chunks for testing"""
    return [
        {
            "course_title": "MCP: Build Rich-Context AI Apps with Anthropic",
            "lesson_number": 1,
            "chunk_index": 0,
            "content": "MCP (Model Context Protocol) is a revolutionary approach to building AI applications. It allows for rich context sharing between different AI models and systems."
        },
        {
            "course_title": "MCP: Build Rich-Context AI Apps with Anthropic", 
            "lesson_number": 1,
            "chunk_index": 1,
            "content": "The key benefits of MCP include improved context retention, better model coordination, and enhanced application performance."
        },
        {
            "course_title": "MCP: Build Rich-Context AI Apps with Anthropic",
            "lesson_number": 2,
            "chunk_index": 2,
            "content": "To build your first MCP server, you need to understand the protocol specifications and implement the required interfaces."
        },
        {
            "course_title": "Introduction to RAG Systems",
            "lesson_number": 1,
            "chunk_index": 0,
            "content": "RAG (Retrieval-Augmented Generation) combines information retrieval with text generation to create more accurate and contextual AI responses."
        }
    ]

@pytest.fixture
def mock_chroma_search_results():
    """Mock ChromaDB search results"""
    return {
        'documents': [[
            "MCP (Model Context Protocol) is a revolutionary approach to building AI applications.",
            "The key benefits of MCP include improved context retention and better model coordination."
        ]],
        'metadatas': [[
            {
                'course_title': 'MCP: Build Rich-Context AI Apps with Anthropic',
                'lesson_number': 1,
                'chunk_index': 0
            },
            {
                'course_title': 'MCP: Build Rich-Context AI Apps with Anthropic', 
                'lesson_number': 1,
                'chunk_index': 1
            }
        ]],
        'distances': [[0.15, 0.23]]
    }

@pytest.fixture
def mock_chroma_catalog_results():
    """Mock ChromaDB course catalog results"""
    return {
        'documents': [["MCP: Build Rich-Context AI Apps with Anthropic"]],
        'metadatas': [ # List of metadata dictionaries
            {
                'title': 'MCP: Build Rich-Context AI Apps with Anthropic',
                'instructor': 'John Smith',
                'course_link': 'https://example.com/mcp-course',
                'lessons_json': json.dumps([
                    {
                        "lesson_number": 1,
                        "lesson_title": "Introduction to MCP",
                        "lesson_link": "https://example.com/mcp-course/lesson-1"
                    },
                    {
                        "lesson_number": 2,
                        "lesson_title": "Building Your First MCP Server", 
                        "lesson_link": "https://example.com/mcp-course/lesson-2"
                    }
                ]),
                'lesson_count': 2
            }
        ],
        'ids': [["MCP: Build Rich-Context AI Apps with Anthropic"]]
    }

@pytest.fixture
def mock_vector_store(mock_chroma_search_results, mock_chroma_catalog_results):
    """Mock VectorStore with realistic behavior"""
    mock_store = Mock(spec=VectorStore)
    
    # Mock course_content collection
    mock_course_content = Mock()
    mock_course_content.query.return_value = mock_chroma_search_results
    mock_store.course_content = mock_course_content
    
    # Mock course_catalog collection  
    mock_course_catalog = Mock()
    mock_course_catalog.query.return_value = mock_chroma_catalog_results
    mock_course_catalog.get.return_value = mock_chroma_catalog_results
    mock_store.course_catalog = mock_course_catalog
    
    # Mock search method
    def mock_search(query, course_name=None, lesson_number=None, limit=None):
        return SearchResults.from_chroma(mock_chroma_search_results)
    mock_store.search = mock_search
    
    # Mock course resolution
    mock_store._resolve_course_name.return_value = "MCP: Build Rich-Context AI Apps with Anthropic"
    
    # Mock link methods
    mock_store.get_course_link.return_value = "https://example.com/mcp-course"
    mock_store.get_lesson_link.return_value = "https://example.com/mcp-course/lesson-1"
    
    return mock_store

@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response for tool calling"""
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = "This is a test response about MCP concepts."
    mock_response.stop_reason = "end_turn"
    return mock_response

@pytest.fixture
def mock_anthropic_tool_response():
    """Mock Anthropic API response with tool use"""
    mock_response = Mock()
    
    # Create mock tool use content
    tool_content = Mock()
    tool_content.type = "tool_use"
    tool_content.name = "search_course_content" 
    tool_content.id = "tool_123"
    tool_content.input = {"query": "MCP introduction", "course_name": "MCP"}
    
    mock_response.content = [tool_content]
    mock_response.stop_reason = "tool_use"
    
    return mock_response

@pytest.fixture
def course_search_tool(mock_vector_store):
    """CourseSearchTool instance with mock vector store"""
    return CourseSearchTool(mock_vector_store)

@pytest.fixture
def course_outline_tool(mock_vector_store):
    """CourseOutlineTool instance with mock vector store"""
    return CourseOutlineTool(mock_vector_store)

@pytest.fixture
def tool_manager(course_search_tool, course_outline_tool):
    """ToolManager with registered tools"""
    manager = ToolManager()
    manager.register_tool(course_search_tool)
    manager.register_tool(course_outline_tool)
    return manager

@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    mock_config = Mock()
    mock_config.ANTHROPIC_API_KEY = "test-api-key"
    mock_config.ANTHROPIC_MODEL = "claude-3-sonnet-20240229"
    mock_config.CHROMA_PATH = "test_chroma_db"
    mock_config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    mock_config.MAX_RESULTS = 5
    mock_config.MAX_HISTORY = 10
    mock_config.CHUNK_SIZE = 1000
    mock_config.CHUNK_OVERLAP = 200
    return mock_config

# API Testing Fixtures

@pytest.fixture
def mock_rag_system_for_api():
    """Mock RAG system for API testing"""
    mock_rag = Mock(spec=RAGSystem)
    
    # Mock query method
    mock_rag.query.return_value = (
        "This is a test response about MCP concepts.",
        [{"title": "MCP Course", "link": "https://example.com/mcp"}]
    )
    
    # Mock session manager
    mock_session_manager = Mock()
    mock_session_manager.create_session.return_value = "test-session-123"
    mock_session_manager.clear_session.return_value = None
    mock_rag.session_manager = mock_session_manager
    
    # Mock get_course_analytics method
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["MCP: Build Rich-Context AI Apps", "Introduction to RAG Systems"]
    }
    
    return mock_rag

@pytest.fixture
def test_app():
    """Create a test FastAPI app without static file mounting issues"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import List, Optional, Union, Dict, Any
    
    # Create test app
    app = FastAPI(title="Test RAG API")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Pydantic models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None
    
    class QueryResponse(BaseModel):
        answer: str
        sources: List[Union[str, Dict[str, Any]]]
        session_id: str
    
    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]
    
    # Test endpoints (will be patched with mock RAG system)
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            if not hasattr(app.state, 'rag_system'):
                raise HTTPException(status_code=500, detail="RAG system not initialized")
            
            rag_system = app.state.rag_system
            session_id = request.session_id or rag_system.session_manager.create_session()
            answer, sources = rag_system.query(request.query, session_id)
            
            return QueryResponse(
                answer=answer,
                sources=sources, 
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            if not hasattr(app.state, 'rag_system'):
                raise HTTPException(status_code=500, detail="RAG system not initialized")
                
            analytics = app.state.rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/api/session/{session_id}")
    async def clear_session(session_id: str):
        try:
            if not hasattr(app.state, 'rag_system'):
                raise HTTPException(status_code=500, detail="RAG system not initialized")
                
            app.state.rag_system.session_manager.clear_session(session_id)
            return {"status": "success", "message": f"Session {session_id} cleared"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/")
    async def root():
        return {"message": "RAG System API"}
    
    return app

@pytest.fixture
def test_client(test_app, mock_rag_system_for_api):
    """Test client with mocked RAG system"""
    test_app.state.rag_system = mock_rag_system_for_api
    return TestClient(test_app)

@pytest.fixture
async def async_test_client(test_app, mock_rag_system_for_api):
    """Async test client with mocked RAG system"""
    test_app.state.rag_system = mock_rag_system_for_api
    async with httpx.AsyncClient(app=test_app, base_url="http://test") as client:
        yield client


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks between tests"""
    yield
    # Any cleanup can go here if needed