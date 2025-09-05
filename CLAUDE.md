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

### Code Quality & Formatting
```bash
# Essential pre-commit checks (recommended)
./scripts/pre-commit-check.sh

# Format code (Black + isort)
./scripts/format.sh

# Check linting (flake8)
./scripts/lint.sh

# Run type checking (mypy)
./scripts/typecheck.sh

# Run comprehensive quality checks
./scripts/quality-check.sh

# Manual commands
uv run black backend/          # Format with Black
uv run isort backend/          # Sort imports
uv run flake8 backend/         # Lint code
uv run mypy backend/           # Type check
uv run pytest backend/tests/   # Run tests
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

## System Workflow Diagram

```
┌─────────────────┐    ┌────────────────────┐    ┌─────────────────────┐
│   User Query    │────│   RAG System      │────│   AI Generator      │
│                 │    │   (Orchestrator)   │    │   (Claude API)      │
└─────────────────┘    └────────────────────┘    └─────────────────────┘
                                │                            │
                                │                            │
                       ┌────────▼────────┐                  │
                       │  Tool Manager   │                  │
                       │                 │                  │
                       └─────────────────┘                  │
                                │                            │
                    ┌───────────┼───────────┐               │
                    │           │           │               │
            ┌───────▼──────┐    │    ┌──────▼──────────┐   │
            │Content Search│    │    │Course Outline   │   │
            │Tool          │    │    │Tool             │   │
            └──────────────┘    │    └─────────────────┘   │
                    │           │           │               │
                    └───────────┼───────────┘               │
                                │                            │
                       ┌────────▼────────┐                  │
                       │  Vector Store   │                  │
                       │   (ChromaDB)    │                  │
                       └─────────────────┘                  │
                                │                            │
                    ┌───────────┼───────────┐               │
                    │           │           │               │
            ┌───────▼──────┐    │    ┌──────▼──────────┐   │
            │Course Content│    │    │Course Catalog   │   │
            │Collection    │    │    │Collection       │   │
            │(Chunks)      │    │    │(Metadata)       │   │
            └──────────────┘    │    └─────────────────┘   │
                                │                            │
                                └────────────────────────────┘

Query Types & Tool Selection:
┌─────────────────────────────────────────────────────────────────┐
│  Query Type              →  Tool Used                           │
├─────────────────────────────────────────────────────────────────┤
│  "What's in course X?"   →  get_course_outline                 │
│  "Course outline"        →  get_course_outline                 │
│  "List lessons"          →  get_course_outline                 │
│                                                                 │
│  "Explain concept Y"     →  search_course_content              │
│  "How does Z work?"      →  search_course_content              │
│  "Details about topic"   →  search_course_content              │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Document Ingestion Flow
1. Documents are processed and chunked in `document_processor.py`
2. Course metadata stored in ChromaDB `course_catalog` collection
3. Content chunks stored in ChromaDB `course_content` collection
4. Both collections indexed with sentence embeddings

### Query Processing Flow
1. User query received by `rag_system.py`
2. Claude AI analyzes query type via `ai_generator.py`
3. **Tool Selection**:
   - **Outline queries** → `CourseOutlineTool` → `course_catalog` collection
   - **Content queries** → `CourseSearchTool` → `course_content` collection
4. Tool executes semantic search in appropriate ChromaDB collection
5. Results formatted and returned to Claude for response generation
6. Final response delivered to user with source links
7. Conversation history managed by `session_manager.py`

## Key Dependencies

- **FastAPI** - Web framework
- **ChromaDB** - Vector database
- **Anthropic** - Claude API client
- **sentence-transformers** - Text embeddings
- **uvicorn** - ASGI server
- always use uv to run the server do not use pip directly