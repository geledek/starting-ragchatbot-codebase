# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Retrieval-Augmented Generation (RAG) system for querying course materials. It's a full-stack Python application using FastAPI backend and vanilla JS frontend, with ChromaDB for vector storage and Anthropic's Claude for AI responses.

## Development Commands

### Running the Application
```bash
# Quick start (preferred)
./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000
```

### Package Management
```bash
# Install dependencies
uv sync

# Add new dependency
uv add <package-name>
```

### Development Server
- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Architecture

### Backend Structure (`backend/`)
- **app.py** - FastAPI main application with CORS, static file serving, and API endpoints
- **rag_system.py** - Main orchestrator coordinating all components
- **document_processor.py** - Handles document parsing and chunking
- **vector_store.py** - ChromaDB vector database operations
- **ai_generator.py** - Anthropic Claude API integration with tool support
- **search_tools.py** - Tool-based search system for RAG queries
- **session_manager.py** - Conversation history management
- **models.py** - Pydantic data models
- **config.py** - Configuration management with environment variables

### Frontend Structure (`frontend/`)
- **index.html** - Main web interface
- **script.js** - JavaScript application logic
- **style.css** - Application styling

### Key Design Patterns
- **Tool-based RAG**: Uses Claude's tool calling to search the vector database during generation
- **Session Management**: Maintains conversation context across queries
- **Modular Components**: Each core function (document processing, vector storage, AI generation) is separated
- **Configuration-driven**: All settings centralized in config.py with environment variable support

## Environment Setup

Required `.env` file in root:
```
ANTHROPIC_API_KEY=your_api_key_here
```

## Data Flow

1. Documents are processed and chunked in `document_processor.py`
2. Chunks are stored in ChromaDB via `vector_store.py`
3. User queries trigger tool-based search through `search_tools.py`
4. Claude generates responses using retrieved context via `ai_generator.py`
5. Conversation history is managed by `session_manager.py`

## Key Dependencies

- **FastAPI** - Web framework
- **ChromaDB** - Vector database
- **Anthropic** - Claude API client
- **sentence-transformers** - Text embeddings
- **uvicorn** - ASGI server
- always use uv to run the server do not use pip directly