# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QuizGazer is an intelligent desktop application built with PySide6 that uses AI to extract questions from screenshots and provide intelligent answers. It features a RAG (Retrieval-Augmented Generation) knowledge base system for enhanced question answering.

## Development Commands

### Environment Setup
```bash
# Modern approach (recommended)
uv sync

# Traditional approach
pip install -r requirements.txt

# Create config file
cp config.ini.example config.ini
# Edit config.ini with your API keys
```

### Running the Application
```bash
python main.py
```

### Testing
```bash
# Run all tests
python tests/run_all_tests.py

# Run specific test categories
python tests/run_all_tests.py --unit-only
python tests/run_all_tests.py --integration-only
python tests/run_all_tests.py --performance-only
python tests/run_all_tests.py --no-ui
```

### Building Executable
```bash
pyinstaller main.spec
```

## Architecture Overview

### Core Components

**AI Services Layer** (`core/ai_services.py`):
- Integrates Vision Language Models (VLM) for question extraction from images
- Integrates Large Language Models (LLM) for answer generation
- Supports multiple AI providers via configurable endpoints

**Knowledge Base System** (`core/knowledge_base/`):
- `rag_pipeline.py` - RAG processing pipeline for context-aware answers
- `manager.py` - Knowledge base collection management
- `document_processor.py` - Document parsing (PDF, Markdown, CSV)
- `models.py` - Data models for knowledge base entities

**UI Layer** (`ui/`):
- `main_window.py` - Main application window with floating interface
- `knowledge_base_panel.py` - Knowledge base management interface
- `knowledge_base_settings.py` - Configuration UI for knowledge base

**Screenshot Handler** (`core/screenshot_handler.py`):
- Cross-platform screen capture using mss library
- Region selection and image processing

### Technology Stack

- **GUI**: PySide6 (Qt for Python)
- **AI Integration**: LangChain ecosystem with OpenAI, Google GenAI
- **Vector Database**: ChromaDB (local and remote support)
- **Document Processing**: pdfplumber, PyPDF2, pandas
- **Image Processing**: Pillow, mss
- **Package Management**: uv (modern) or pip (legacy)

## Configuration System

The application uses `config.ini` for all configuration:

```ini
[vlm]          # Vision Language Model settings
[llm]          # Language Model settings
[knowledge_base] # Knowledge Base configuration
[chromadb]     # Vector database configuration
[embedding_api] # Embedding service configuration
[reranker_api]  # Reranking service configuration
```

Key configuration aspects:
- API keys and model endpoints
- ChromaDB connection settings (local/remote)
- Document processing parameters
- Performance tuning settings

## Key Development Patterns

### AI Service Integration
- Use the AI services through `core/ai_services.py` abstraction
- Support multiple providers via configuration
- Handle timeouts and retry logic properly

### Knowledge Base Development
- Documents are processed through the RAG pipeline in `core/knowledge_base/rag_pipeline.py`
- Vector storage uses ChromaDB with configurable embeddings
- Support for multiple document types with unified processing

### UI Development
- Follow the existing PySide6 patterns in `ui/`
- Use the floating window design pattern
- Implement proper signal/slot connections
- Handle background processing with thread management

### Error Handling
- Comprehensive error handling throughout the codebase
- User-friendly error messages in the UI
- Graceful degradation for AI service failures

## Testing Strategy

- Unit tests for core knowledge base functionality
- Integration tests for AI service interactions
- UI tests for interface components
- Performance tests for document processing pipelines

## File Structure Notes

- `/data/` - Local storage for documents and vector database
- `/docs/` - Comprehensive documentation including developer guides
- `main.py` - Simple entry point that initializes and shows the main window
- `main.spec` - PyInstaller configuration with required hidden imports

## Development Tips

- Use `uv` for modern Python package management
- The application supports both local and remote ChromaDB instances
- All AI model configurations are externalized to `config.ini`
- The UI is designed as a floating window that can be minimized/maximized
- Document processing happens in background threads to maintain UI responsiveness