"""
API endpoint tests for FastAPI RAG system
"""

import json
from unittest.mock import Mock

import pytest
from fastapi import status


@pytest.mark.api
class TestQueryEndpoint:
    """Test /api/query endpoint"""

    def test_query_endpoint_success(self, test_client):
        """Test successful query processing"""
        response = test_client.post("/api/query", json={"query": "What is MCP?"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Verify response content
        assert data["answer"] == "This is a test response about MCP concepts."
        assert len(data["sources"]) == 1
        assert data["sources"][0]["title"] == "MCP Course"
        assert data["session_id"] == "test-session-123"

    def test_query_endpoint_with_session_id(self, test_client):
        """Test query processing with provided session ID"""
        response = test_client.post(
            "/api/query",
            json={"query": "What is MCP?", "session_id": "existing-session-456"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == "existing-session-456"

    def test_query_endpoint_empty_query(self, test_client):
        """Test query endpoint with empty query"""
        response = test_client.post("/api/query", json={"query": ""})

        # Should still process (RAG system handles empty queries)
        assert response.status_code == status.HTTP_200_OK

    def test_query_endpoint_missing_query(self, test_client):
        """Test query endpoint with missing query field"""
        response = test_client.post("/api/query", json={})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_query_endpoint_invalid_json(self, test_client):
        """Test query endpoint with invalid JSON"""
        response = test_client.post("/api/query", data="invalid json")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_query_endpoint_rag_system_error(self, test_app, mock_rag_system_for_api):
        """Test query endpoint when RAG system raises exception"""
        # Mock RAG system to raise exception
        mock_rag_system_for_api.query.side_effect = Exception("RAG system error")
        test_app.state.rag_system = mock_rag_system_for_api

        from fastapi.testclient import TestClient

        client = TestClient(test_app)

        response = client.post("/api/query", json={"query": "What is MCP?"})

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "RAG system error" in response.json()["detail"]


@pytest.mark.api
class TestCoursesEndpoint:
    """Test /api/courses endpoint"""

    def test_courses_endpoint_success(self, test_client):
        """Test successful course statistics retrieval"""
        response = test_client.get("/api/courses")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "total_courses" in data
        assert "course_titles" in data

        # Verify response content
        assert data["total_courses"] == 2
        assert len(data["course_titles"]) == 2
        assert "MCP: Build Rich-Context AI Apps" in data["course_titles"]
        assert "Introduction to RAG Systems" in data["course_titles"]

    def test_courses_endpoint_rag_system_error(self, test_app, mock_rag_system_for_api):
        """Test courses endpoint when RAG system raises exception"""
        # Mock RAG system to raise exception
        mock_rag_system_for_api.get_course_analytics.side_effect = Exception(
            "Analytics error"
        )
        test_app.state.rag_system = mock_rag_system_for_api

        from fastapi.testclient import TestClient

        client = TestClient(test_app)

        response = client.get("/api/courses")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Analytics error" in response.json()["detail"]


@pytest.mark.api
class TestSessionEndpoint:
    """Test /api/session/{session_id} endpoint"""

    def test_clear_session_success(self, test_client):
        """Test successful session clearing"""
        session_id = "test-session-to-clear"

        response = test_client.delete(f"/api/session/{session_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "status" in data
        assert "message" in data

        # Verify response content
        assert data["status"] == "success"
        assert session_id in data["message"]

    def test_clear_session_rag_system_error(self, test_app, mock_rag_system_for_api):
        """Test session clearing when RAG system raises exception"""
        session_id = "problematic-session"

        # Mock session manager to raise exception
        mock_rag_system_for_api.session_manager.clear_session.side_effect = Exception(
            "Session error"
        )
        test_app.state.rag_system = mock_rag_system_for_api

        from fastapi.testclient import TestClient

        client = TestClient(test_app)

        response = client.delete(f"/api/session/{session_id}")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Session error" in response.json()["detail"]

    def test_clear_session_empty_id(self, test_client):
        """Test session clearing with empty session ID"""
        response = test_client.delete("/api/session/")

        # Should return 404 or 405 depending on route matching
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        ]


@pytest.mark.api
class TestRootEndpoint:
    """Test root endpoint"""

    def test_root_endpoint(self, test_client):
        """Test root endpoint returns expected message"""
        response = test_client.get("/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "RAG System API"


@pytest.mark.api
class TestResponseModels:
    """Test API response model validation"""

    def test_query_response_model(self, test_client):
        """Test that query response matches expected model"""
        response = test_client.post("/api/query", json={"query": "What is MCP?"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify all required fields are present and correct types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

        # Verify sources have expected structure
        for source in data["sources"]:
            assert isinstance(source, dict)
            # Sources can be strings or dicts according to the model

    def test_course_stats_response_model(self, test_client):
        """Test that course stats response matches expected model"""
        response = test_client.get("/api/courses")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify all required fields are present and correct types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

        # Verify course titles are strings
        for title in data["course_titles"]:
            assert isinstance(title, str)


@pytest.mark.api
class TestCORSMiddleware:
    """Test CORS middleware functionality"""

    def test_cors_preflight_request(self, test_client):
        """Test CORS preflight request handling"""
        response = test_client.options(
            "/api/query",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        assert response.status_code == status.HTTP_200_OK

        # Check CORS headers are present
        headers = response.headers
        assert "access-control-allow-origin" in headers
        assert "access-control-allow-methods" in headers
        assert "access-control-allow-headers" in headers

    def test_cors_actual_request(self, test_client):
        """Test CORS headers on actual request"""
        response = test_client.post(
            "/api/query",
            json={"query": "What is MCP?"},
            headers={"Origin": "http://localhost:3000"},
        )

        assert response.status_code == status.HTTP_200_OK

        # Check CORS headers are present
        headers = response.headers
        assert "access-control-allow-origin" in headers


@pytest.mark.api
@pytest.mark.slow
class TestEndpointIntegration:
    """Test integration between different endpoints"""

    def test_query_and_session_integration(self, test_client):
        """Test query creation and session management"""
        # First, make a query to get a session
        query_response = test_client.post("/api/query", json={"query": "What is MCP?"})

        assert query_response.status_code == status.HTTP_200_OK
        session_id = query_response.json()["session_id"]

        # Then, clear the session
        clear_response = test_client.delete(f"/api/session/{session_id}")

        assert clear_response.status_code == status.HTTP_200_OK
        assert session_id in clear_response.json()["message"]

    def test_multiple_concurrent_queries(self, test_client):
        """Test handling multiple concurrent queries"""
        queries = [
            {"query": "What is MCP?"},
            {"query": "What are RAG systems?"},
            {"query": "How do vector databases work?"},
        ]

        responses = []
        for query in queries:
            response = test_client.post("/api/query", json=query)
            responses.append(response)

        # All requests should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "answer" in data
            assert "sources" in data
            assert "session_id" in data


@pytest.mark.api
class TestErrorHandling:
    """Test comprehensive error handling"""

    def test_endpoint_without_rag_system(self, test_app):
        """Test endpoints when RAG system is not initialized"""
        from fastapi.testclient import TestClient

        # Create client without attaching RAG system to app.state
        client = TestClient(test_app)

        # Test query endpoint
        response = client.post("/api/query", json={"query": "test"})
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "RAG system not initialized" in response.json()["detail"]

        # Test courses endpoint
        response = client.get("/api/courses")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "RAG system not initialized" in response.json()["detail"]

        # Test session endpoint
        response = client.delete("/api/session/test-session")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "RAG system not initialized" in response.json()["detail"]

    def test_malformed_requests(self, test_client):
        """Test handling of various malformed requests"""
        # Test with invalid HTTP method
        response = test_client.patch("/api/query", json={"query": "test"})
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # Test non-existent endpoint
        response = test_client.get("/api/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND
