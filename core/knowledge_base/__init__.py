"""
Knowledge Base module for QuizGazer.

This module provides Retrieval-Augmented Generation (RAG) capabilities,
allowing users to create personalized knowledge bases from various document types.
"""

from .manager import KnowledgeBaseManager
from .models import (
    Collection, Document, DocumentChunk, ProcessingTask, 
    DocumentType, ProcessingStatus, ChromaDBConfig
)

__all__ = [
    'KnowledgeBaseManager',
    'Collection', 'Document', 'DocumentChunk', 'ProcessingTask',
    'DocumentType', 'ProcessingStatus', 'ChromaDBConfig'
]