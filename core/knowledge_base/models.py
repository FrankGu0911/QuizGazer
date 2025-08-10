"""
Data models for the Knowledge Base module.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
import re
import os


class DocumentType(Enum):
    """Document type enumeration."""
    KNOWLEDGE_DOCUMENT = "knowledge"
    QUESTION_BANK = "question_bank"


class ProcessingStatus(Enum):
    """Processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Collection:
    """Collection data model."""
    id: str
    name: str
    description: str
    created_at: datetime
    document_count: int
    total_chunks: int
    
    def validate(self) -> Dict[str, str]:
        """Validate collection data."""
        errors = {}
        
        if not self.id or not self.id.strip():
            errors['id'] = "Collection ID cannot be empty"
        
        if not self.name or not self.name.strip():
            errors['name'] = "Collection name cannot be empty"
        elif len(self.name) > 100:
            errors['name'] = "Collection name cannot exceed 100 characters"
        elif not re.match(r'^[a-zA-Z0-9_\-\s]+$', self.name):
            errors['name'] = "Collection name contains invalid characters"
        
        if len(self.description) > 500:
            errors['description'] = "Description cannot exceed 500 characters"
        
        if self.document_count < 0:
            errors['document_count'] = "Document count cannot be negative"
        
        if self.total_chunks < 0:
            errors['total_chunks'] = "Total chunks cannot be negative"
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if collection data is valid."""
        return len(self.validate()) == 0


@dataclass
class Document:
    """Document data model."""
    id: str
    collection_id: str
    filename: str
    file_path: str
    document_type: DocumentType
    processed_at: datetime
    chunk_count: int
    file_size: int
    
    def validate(self) -> Dict[str, str]:
        """Validate document data."""
        errors = {}
        
        if not self.id or not self.id.strip():
            errors['id'] = "Document ID cannot be empty"
        
        if not self.collection_id or not self.collection_id.strip():
            errors['collection_id'] = "Collection ID cannot be empty"
        
        if not self.filename or not self.filename.strip():
            errors['filename'] = "Filename cannot be empty"
        elif len(self.filename) > 255:
            errors['filename'] = "Filename cannot exceed 255 characters"
        
        if not self.file_path or not self.file_path.strip():
            errors['file_path'] = "File path cannot be empty"
        
        if not isinstance(self.document_type, DocumentType):
            errors['document_type'] = "Invalid document type"
        
        if self.chunk_count < 0:
            errors['chunk_count'] = "Chunk count cannot be negative"
        
        if self.file_size < 0:
            errors['file_size'] = "File size cannot be negative"
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if document data is valid."""
        return len(self.validate()) == 0


@dataclass
class DocumentChunk:
    """Document chunk data model."""
    id: str
    document_id: str
    content: str
    metadata: Dict[str, Any]
    chunk_index: int
    
    def validate(self) -> Dict[str, str]:
        """Validate document chunk data."""
        errors = {}
        
        if not self.id or not self.id.strip():
            errors['id'] = "Chunk ID cannot be empty"
        
        if not self.document_id or not self.document_id.strip():
            errors['document_id'] = "Document ID cannot be empty"
        
        if not self.content or not self.content.strip():
            errors['content'] = "Chunk content cannot be empty"
        elif len(self.content) > 10000:
            errors['content'] = "Chunk content cannot exceed 10000 characters"
        
        if self.chunk_index < 0:
            errors['chunk_index'] = "Chunk index cannot be negative"
        
        if not isinstance(self.metadata, dict):
            errors['metadata'] = "Metadata must be a dictionary"
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if document chunk data is valid."""
        return len(self.validate()) == 0


@dataclass
class ProcessingTask:
    """Processing task data model."""
    id: str
    document_id: str
    collection_id: str
    filename: str
    status: ProcessingStatus
    progress: float  # 0.0 to 1.0
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    
    def validate(self) -> Dict[str, str]:
        """Validate processing task data."""
        errors = {}
        
        if not self.id or not self.id.strip():
            errors['id'] = "Task ID cannot be empty"
        
        if not self.document_id or not self.document_id.strip():
            errors['document_id'] = "Document ID cannot be empty"
        
        if not self.collection_id or not self.collection_id.strip():
            errors['collection_id'] = "Collection ID cannot be empty"
        
        if not self.filename or not self.filename.strip():
            errors['filename'] = "Filename cannot be empty"
        
        if not isinstance(self.status, ProcessingStatus):
            errors['status'] = "Invalid processing status"
        
        if not (0.0 <= self.progress <= 1.0):
            errors['progress'] = "Progress must be between 0.0 and 1.0"
        
        if self.started_at and self.started_at < self.created_at:
            errors['started_at'] = "Start time cannot be before creation time"
        
        if self.completed_at and self.started_at and self.completed_at < self.started_at:
            errors['completed_at'] = "Completion time cannot be before start time"
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if processing task data is valid."""
        return len(self.validate()) == 0


@dataclass
class ChromaDBConfig:
    """ChromaDB configuration data model."""
    connection_type: str  # "local" or "remote"
    host: Optional[str] = None
    port: Optional[int] = None
    path: Optional[str] = None  # for local storage
    auth_credentials: Optional[Dict[str, Any]] = None
    ssl_enabled: bool = False
    
    def validate(self) -> Dict[str, str]:
        """Validate ChromaDB configuration."""
        errors = {}
        
        if self.connection_type not in ['local', 'remote']:
            errors['connection_type'] = "Connection type must be 'local' or 'remote'"
        
        if self.connection_type == 'remote':
            if not self.host or not self.host.strip():
                errors['host'] = "Host is required for remote connections"
            if not self.port or not isinstance(self.port, int) or self.port <= 0:
                errors['port'] = "Valid port number is required for remote connections"
        
        if self.connection_type == 'local':
            if not self.path or not self.path.strip():
                errors['path'] = "Path is required for local connections"
        
        if self.port and (not isinstance(self.port, int) or self.port <= 0 or self.port > 65535):
            errors['port'] = "Port must be a valid integer between 1 and 65535"
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if ChromaDB configuration is valid."""
        return len(self.validate()) == 0


@dataclass
class ConnectionStatus:
    """Connection status data model."""
    is_connected: bool
    connection_type: str
    database_version: str
    error_message: Optional[str]


@dataclass
class DatabaseInfo:
    """Database information data model."""
    total_collections: int
    total_documents: int
    storage_size: str
    connection_info: ChromaDBConfig


@dataclass
class KnowledgeFragment:
    """Knowledge fragment data model."""
    content: str
    source_document: str
    collection_name: str
    relevance_score: float
    metadata: Dict[str, Any]


@dataclass
class SearchResult:
    """Search result data model."""
    chunk_id: str
    content: str
    distance: float
    metadata: Dict[str, Any]


@dataclass
class RankedResult:
    """Ranked result data model."""
    content: str
    relevance_score: float
    source_info: Dict[str, Any]