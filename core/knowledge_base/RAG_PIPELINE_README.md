# RAG Pipeline Integration

## Overview

The RAG (Retrieval-Augmented Generation) Pipeline is the core component that integrates knowledge retrieval with language model generation in the QuizGazer knowledge base system. It orchestrates the complete workflow from query processing to enhanced response generation.

## Key Features

### 🔄 Complete RAG Workflow
- **Query Processing**: Handles user queries with intelligent routing
- **Knowledge Retrieval**: Searches relevant knowledge fragments from selected collections
- **Context Building**: Formats retrieved knowledge into coherent context
- **Enhanced Generation**: Integrates knowledge context with LLM prompts
- **Fallback Handling**: Graceful degradation when knowledge base is unavailable

### 🎛️ Flexible Control
- **Collection Selection**: Choose which knowledge collections to search
- **Enable/Disable Toggle**: Turn knowledge base functionality on/off
- **Fallback Mode**: Temporarily disable knowledge retrieval
- **Relevance Filtering**: Filter knowledge fragments by relevance score

### 📊 Comprehensive Status Monitoring
- **Pipeline Status**: Monitor enabled state and component availability
- **Knowledge Base Stats**: Track collections, documents, and chunks
- **Query Statistics**: Monitor usage patterns and performance
- **Error Handling**: Robust error recovery with detailed logging

## Architecture

```
User Query
    ↓
RAG Pipeline
    ↓
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Knowledge       │    │ Context          │    │ Enhanced        │
│ Retrieval       │ -> │ Building         │ -> │ Generation      │
│                 │    │                  │    │                 │
│ • Search KB     │    │ • Format Context │    │ • Build Prompt  │
│ • Filter by     │    │ • Truncate if    │    │ • Call LLM      │
│   relevance     │    │   too long       │    │ • Return Result │
│ • Rank results  │    │ • Add metadata   │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Core Components

### RAGPipeline Class

The main orchestrator class that manages the complete RAG workflow.

#### Key Methods

```python
# Core Processing
process_query_with_knowledge(query: str, selected_collections: List[str] = None) -> str
build_enhanced_prompt(original_query: str, knowledge_context: str) -> str

# Collection Management
set_selected_collections(collection_ids: List[str])
get_selected_collections() -> List[str]

# Control Methods
enable_knowledge_base()
disable_knowledge_base()
enable_fallback_mode()
disable_fallback_mode()

# Status and Monitoring
get_knowledge_base_status() -> Dict[str, Any]
get_pipeline_statistics() -> Dict[str, Any]
should_use_knowledge_base() -> bool

# Preview and Testing
search_knowledge_preview(query: str, collections: List[str] = None, top_k: int = 3) -> List[Dict]
```

## Configuration

### Pipeline Settings

```python
# RAG Configuration
max_context_length = 4000          # Maximum characters for knowledge context
min_relevance_score = 0.3          # Minimum relevance score for fragments
max_knowledge_fragments = 5        # Maximum number of fragments to include
```

### Dependencies

- **KnowledgeBaseManager**: For knowledge retrieval operations
- **LLM Service**: For generating enhanced responses
- **Configuration Manager**: For loading settings

## Usage Examples

### Basic Usage

```python
from rag_pipeline import RAGPipeline
from manager import KnowledgeBaseManager

# Initialize components
kb_manager = KnowledgeBaseManager(storage_path="./data/kb")
llm_service = lambda prompt: your_llm_service(prompt)

# Create RAG pipeline
rag_pipeline = RAGPipeline(
    knowledge_base_manager=kb_manager,
    llm_service=llm_service
)

# Enable and configure
rag_pipeline.enable_knowledge_base()
rag_pipeline.set_selected_collections(["collection_1", "collection_2"])

# Process queries
response = rag_pipeline.process_query_with_knowledge("What is AI?")
print(response)
```

### Advanced Usage

```python
# Check status before processing
status = rag_pipeline.get_knowledge_base_status()
if status['can_process_queries']:
    # Preview knowledge before generating response
    preview = rag_pipeline.search_knowledge_preview(
        query="Machine learning types",
        collections=["ml_collection"],
        top_k=3
    )
    
    print(f"Found {len(preview)} relevant fragments:")
    for fragment in preview:
        print(f"- {fragment['source_document']} (score: {fragment['relevance_score']})")
    
    # Process the query
    response = rag_pipeline.process_query_with_knowledge(
        query="Machine learning types",
        selected_collections=["ml_collection"]
    )
    print(f"Response: {response}")
```

### Error Handling

```python
try:
    response = rag_pipeline.process_query_with_knowledge(query)
except Exception as e:
    # RAG pipeline has built-in error handling
    # This should rarely be needed as the pipeline
    # gracefully falls back to standard responses
    print(f"Unexpected error: {e}")
```

## Integration Points

### With AI Services

The RAG pipeline integrates with the existing AI services layer:

```python
# In ai_services.py
class AIServices:
    def __init__(self):
        self.rag_pipeline = RAGPipeline(
            knowledge_base_manager=self.kb_manager,
            llm_service=self.generate_response
        )
    
    def process_query(self, query: str) -> str:
        if self.rag_pipeline.should_use_knowledge_base():
            return self.rag_pipeline.process_query_with_knowledge(query)
        else:
            return self.generate_response(query)
```

### With UI Components

The pipeline provides status information for UI components:

```python
# In UI components
status = rag_pipeline.get_knowledge_base_status()
ui_elements.update({
    'kb_enabled': status['enabled'],
    'collections_available': status['total_collections'],
    'can_process': status['can_process_queries']
})
```

## Performance Considerations

### Context Length Management
- Automatically truncates long knowledge context to stay within limits
- Configurable `max_context_length` parameter
- Preserves most relevant information when truncating

### Relevance Filtering
- Filters knowledge fragments by minimum relevance score
- Prevents low-quality knowledge from affecting responses
- Configurable `min_relevance_score` parameter

### Fragment Limiting
- Limits number of knowledge fragments to prevent prompt bloat
- Configurable `max_knowledge_fragments` parameter
- Prioritizes highest-scoring fragments

## Error Handling and Fallbacks

### Graceful Degradation
1. **Knowledge Base Unavailable**: Falls back to standard LLM response
2. **No Relevant Knowledge**: Uses standard response with note
3. **API Failures**: Provides error-aware fallback responses
4. **Processing Errors**: Logs errors and continues with fallback

### Error Recovery
- Automatic retry mechanisms for transient failures
- Detailed error logging for debugging
- User-friendly error messages
- Maintains service availability during failures

## Testing

### Unit Tests
Run the comprehensive test suite:
```bash
python core/knowledge_base/test_rag_pipeline.py
```

### Demo Script
See the pipeline in action:
```bash
python core/knowledge_base/demo_rag_pipeline.py
```

### Test Coverage
- ✅ Pipeline initialization and configuration
- ✅ Collection management and selection
- ✅ Status monitoring and control methods
- ✅ Prompt building and context formatting
- ✅ Knowledge search and preview functionality
- ✅ Query processing with various scenarios
- ✅ Error handling and fallback mechanisms

## Monitoring and Debugging

### Status Information
```python
# Get comprehensive status
status = rag_pipeline.get_knowledge_base_status()
print(f"Enabled: {status['enabled']}")
print(f"Collections: {status['total_collections']}")
print(f"Documents: {status['total_documents']}")
print(f"Can Process: {status['can_process_queries']}")

# Get pipeline statistics
stats = rag_pipeline.get_pipeline_statistics()
print(f"Selected Collections: {stats['selected_collections_count']}")
print(f"Max Context Length: {stats['max_context_length']}")
```

### Logging
The pipeline uses Python's logging module with detailed debug information:
- Query processing steps
- Knowledge retrieval results
- Error conditions and recovery
- Performance metrics

## Future Enhancements

### Planned Features
- [ ] Query caching for improved performance
- [ ] Advanced relevance scoring algorithms
- [ ] Multi-language knowledge support
- [ ] Real-time knowledge base updates
- [ ] Advanced context compression techniques

### Extension Points
- Custom knowledge formatters
- Pluggable relevance scoring
- Custom fallback strategies
- Advanced prompt templates

## Requirements Satisfied

This RAG Pipeline implementation satisfies the following requirements from the specification:

- **Requirement 2.1**: Collection selection for query processing ✅
- **Requirement 2.7**: Fallback when no relevant knowledge found ✅
- **Requirement 4.1**: Knowledge base toggle functionality ✅
- **Requirement 4.2**: Bypass knowledge retrieval when disabled ✅

## Conclusion

The RAG Pipeline provides a robust, flexible, and well-tested foundation for integrating knowledge retrieval with language model generation. It handles edge cases gracefully, provides comprehensive monitoring capabilities, and maintains high availability through intelligent fallback mechanisms.