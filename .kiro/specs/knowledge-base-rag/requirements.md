# Requirements Document

## Introduction

This feature introduces a knowledge base functionality to the QuizGazer application using Retrieval-Augmented Generation (RAG). The system will allow users to upload documents (PDF, Markdown, CSV) to create personalized knowledge bases, which will be used to enhance the accuracy and relevance of AI-generated answers by providing context-specific information rather than relying solely on general knowledge.

## Requirements

### Requirement 1

**User Story:** As a QuizGazer user, I want to upload and manage documents in organized collections, so that I can categorize different types of materials and control how they're processed.

#### Acceptance Criteria

1. WHEN a user uploads a document THEN the system SHALL require them to specify whether it's a "knowledge document" or "question bank"
2. WHEN a user uploads a knowledge document (PDF/Markdown) THEN the system SHALL process it using recursive character splitting
3. WHEN a user uploads a question bank (CSV) THEN the system SHALL require a specific format with columns for question, options, and correct answer
4. WHEN a user uploads a question bank THEN the system SHALL validate the CSV format and reject files that don't match the required structure
5. WHEN a user uploads any document THEN the system SHALL allow them to either add it to an existing collection or create a new collection
6. WHEN a user views their knowledge base THEN the system SHALL display collections with their contained documents and metadata
7. WHEN a user deletes a document THEN the system SHALL remove all associated vector embeddings from that collection
8. WHEN a user deletes a collection THEN the system SHALL remove all documents and embeddings within that collection

### Requirement 2

**User Story:** As a QuizGazer user, I want to select which collections to use for answering questions, so that I can control which knowledge sources are consulted for different types of queries.

#### Acceptance Criteria

1. WHEN a user enables knowledge base mode THEN the system SHALL display a list of available collections for selection
2. WHEN a user selects one or more collections THEN the system SHALL only search within those selected collections for relevant information
3. WHEN no collections are selected THEN the system SHALL use all available collections by default
4. WHEN a user asks a question THEN the system SHALL convert the question to embeddings using the configured Embedding API
5. WHEN embeddings are generated THEN the system SHALL search only the selected collections in ChromaDB for similar content
6. WHEN similar content is found THEN the system SHALL use the Reranker API to rank and select the most relevant knowledge fragments
7. WHEN relevant fragments are selected THEN the system SHALL integrate them into the LLM prompt before generating the final answer
8. IF no relevant knowledge is found in selected collections THEN the system SHALL proceed with the original question without additional context

### Requirement 3

**User Story:** As a QuizGazer user, I want to configure the knowledge base settings (APIs, models), so that I can customize the system to work with my preferred AI services.

#### Acceptance Criteria

1. WHEN a user accesses knowledge base settings THEN the system SHALL provide configuration options for Embedding API endpoint and credentials
2. WHEN a user accesses knowledge base settings THEN the system SHALL provide configuration options for Reranker API endpoint and credentials
3. WHEN a user saves API configurations THEN the system SHALL validate the connections and display success/error status
4. WHEN APIs are configured THEN the system SHALL use these endpoints for embedding generation and reranking operations
5. IF API credentials are invalid THEN the system SHALL display clear error messages and prevent knowledge base operations

### Requirement 4

**User Story:** As a QuizGazer user, I want to enable or disable the knowledge base feature, so that I can choose when to use enhanced answers versus standard AI responses.

#### Acceptance Criteria

1. WHEN a user toggles the knowledge base feature ON THEN the system SHALL include knowledge retrieval in the question-answering process
2. WHEN a user toggles the knowledge base feature OFF THEN the system SHALL bypass knowledge retrieval and use only the standard LLM response
3. WHEN the knowledge base is enabled but no documents are uploaded THEN the system SHALL function normally without additional context
4. WHEN the knowledge base toggle state changes THEN the system SHALL persist this setting for future sessions
5. WHEN the knowledge base is disabled THEN the system SHALL clearly indicate this status in the UI

### Requirement 5

**User Story:** As a QuizGazer user, I want the system to handle different document types with appropriate processing strategies, so that both knowledge documents and question banks are optimally structured for retrieval.

#### Acceptance Criteria

1. WHEN processing knowledge documents (PDF/Markdown) THEN the system SHALL use recursive character splitting to maintain semantic integrity
2. WHEN processing question bank CSV files THEN the system SHALL require columns named "question", "options", and "correct_answer"
3. WHEN processing question bank CSV files THEN the system SHALL treat each row as an independent knowledge unit combining question, options, and answer
4. WHEN storing document chunks THEN the system SHALL attach metadata including source file, document type, collection name, and chunk position
5. WHEN storing question bank entries THEN the system SHALL attach metadata including question ID, difficulty level (if provided), and topic category (if provided)
6. WHEN retrieving knowledge THEN the system SHALL include source metadata to enable traceability and citation
7. IF a document fails format validation THEN the system SHALL display specific error messages indicating required format corrections
8. IF a document fails to process THEN the system SHALL log the error and notify the user with specific failure details

### Requirement 6

**User Story:** As a QuizGazer user, I want to manage collections effectively, so that I can organize my knowledge base and control which materials are used for different scenarios.

#### Acceptance Criteria

1. WHEN a user creates a new collection THEN the system SHALL require a unique collection name and optional description
2. WHEN a user views collections THEN the system SHALL display collection name, description, document count, and creation date
3. WHEN a user renames a collection THEN the system SHALL update the collection metadata while preserving all contained documents
4. WHEN a user exports a collection THEN the system SHALL provide options to export as a backup file or individual documents
5. WHEN a user imports a collection THEN the system SHALL validate the format and merge or replace existing collections as specified
6. WHEN collections contain both knowledge documents and question banks THEN the system SHALL clearly indicate the mix of content types
7. WHEN a user searches within a collection THEN the system SHALL provide preview of matching content before full retrieval

### Requirement 7

**User Story:** As a QuizGazer user, I want large document processing to happen in the background with progress tracking, so that I can continue using the application while my documents are being processed.

#### Acceptance Criteria

1. WHEN a user uploads a large document (>5MB or >100 pages) THEN the system SHALL process it as an asynchronous background task
2. WHEN background processing starts THEN the system SHALL display a progress indicator showing processing status
3. WHEN document processing is in progress THEN the system SHALL allow users to continue using other features normally
4. WHEN document processing completes successfully THEN the system SHALL notify the user and make the document available for queries
5. WHEN document processing fails THEN the system SHALL notify the user with specific error details and suggested solutions
6. WHEN multiple documents are being processed THEN the system SHALL show progress for each document individually
7. WHEN a user closes the application during processing THEN the system SHALL resume processing when the application restarts

### Requirement 8

**User Story:** As a QuizGazer user, I want the system to extract text from image-based PDFs using OCR, so that I can use scanned documents and image-heavy materials in my knowledge base.

#### Acceptance Criteria

1. WHEN a user uploads a PDF document THEN the system SHALL detect if it contains primarily images or scanned content
2. WHEN an image-based PDF is detected THEN the system SHALL use the existing VLM (Visual Language Model) to perform OCR extraction
3. WHEN performing OCR on PDF pages THEN the system SHALL process each page as a separate image through the VLM
4. WHEN OCR text is extracted THEN the system SHALL combine it with any existing text content from the PDF
5. WHEN OCR processing is required THEN the system SHALL inform the user that additional processing time is needed
6. WHEN OCR fails on specific pages THEN the system SHALL log the failures but continue processing other pages
7. IF the VLM service is unavailable THEN the system SHALL skip OCR and process only the extractable text content with a warning to the user

### Requirement 9

**User Story:** As a system administrator, I want the knowledge base to use local storage and external APIs efficiently, so that the system remains performant and cost-effective.

#### Acceptance Criteria

1. WHEN the system initializes THEN it SHALL create or connect to a local ChromaDB instance for vector storage
2. WHEN generating embeddings THEN the system SHALL use external API calls to avoid local model deployment overhead
3. WHEN performing reranking THEN the system SHALL use external API calls compatible with vllm format (/v1/rerank endpoint)
4. WHEN the vector database grows large THEN the system SHALL maintain reasonable query performance through proper indexing
5. IF external APIs are unavailable THEN the system SHALL gracefully degrade to standard LLM responses without knowledge enhancement我需要