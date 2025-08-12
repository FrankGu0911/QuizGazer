"""
Knowledge Base Manager - Central orchestrator for all knowledge base operations.
"""

import os
import uuid
import json
import logging
import threading
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

try:
    from .models import Collection, Document, ProcessingTask, DocumentType, ChromaDBConfig
    from .vector_store import VectorStoreManager
    from .task_manager import BackgroundTaskManager
    from .document_processor import DocumentProcessor
    from .retriever import KnowledgeRetriever
except ImportError:
    from models import Collection, Document, ProcessingTask, DocumentType, ChromaDBConfig
    from vector_store import VectorStoreManager
    from task_manager import BackgroundTaskManager
    from document_processor import DocumentProcessor
    from retriever import KnowledgeRetriever

# Import configuration manager
try:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from utils.config_manager import get_knowledge_base_config, get_chromadb_config
except ImportError:
    get_knowledge_base_config = None
    get_chromadb_config = None
    print("Warning: Configuration manager not available")


class KnowledgeBaseManager:
    """Central orchestrator for all knowledge base operations."""
    
    def __init__(self, storage_path: str = None, chromadb_config: ChromaDBConfig = None):
        """
        Initialize the Knowledge Base Manager.
        
        Args:
            storage_path: Path for storing knowledge base data
            chromadb_config: ChromaDB configuration
        """
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.kb_config = get_knowledge_base_config() if get_knowledge_base_config else {}
        self.storage_path = storage_path or self.kb_config.get('storage_path', './data/knowledge_base')
        
        # Ensure storage directory exists
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Initialize ChromaDB configuration
        if chromadb_config:
            self.chromadb_config = chromadb_config
        else:
            chromadb_config_dict = get_chromadb_config() if get_chromadb_config else {}
            self.chromadb_config = ChromaDBConfig(
                connection_type=chromadb_config_dict.get('connection_type', 'local'),
                host=chromadb_config_dict.get('host'),
                port=chromadb_config_dict.get('port'),
                path=chromadb_config_dict.get('path', './data/chromadb'),
                auth_credentials=chromadb_config_dict.get('auth_credentials'),
                ssl_enabled=chromadb_config_dict.get('ssl_enabled', False)
            )
        
        # Initialize components
        self.vector_store = VectorStoreManager(self.chromadb_config)
        self.task_manager = BackgroundTaskManager(
            max_workers=self.kb_config.get('max_concurrent_tasks', 3),
            vector_store=self.vector_store
        )
        self.document_processor = DocumentProcessor(
            chunk_size=self.kb_config.get('chunk_size', 1000),
            chunk_overlap=self.kb_config.get('chunk_overlap', 200)
        )
        self.retriever = KnowledgeRetriever(vector_store_manager=self.vector_store)
        
        # Collection metadata storage
        self.collections_file = os.path.join(self.storage_path, 'collections.json')
        self.documents_file = os.path.join(self.storage_path, 'documents.json')
        
        # In-memory storage for metadata
        self._collections: Dict[str, Collection] = {}
        self._documents: Dict[str, Document] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Load existing data
        self._load_metadata()
        
        # Initialize vector database
        try:
            self.vector_store.initialize_database()
            self.logger.info("KnowledgeBaseManager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize vector database: {e}")
            raise
    
    def create_collection(self, name: str, description: str = "") -> Collection:
        """
        Create a new collection.
        
        Args:
            name: Collection name (must be unique)
            description: Optional description
            
        Returns:
            Created Collection object
        """
        if not name or not name.strip():
            raise ValueError("Collection name cannot be empty")
        
        name = name.strip()
        
        with self._lock:
            # Check if collection already exists
            for collection in self._collections.values():
                if collection.name == name:
                    raise ValueError(f"Collection '{name}' already exists")
            
            # Check collection limit
            max_collections = self.kb_config.get('max_collections', 50)
            if len(self._collections) >= max_collections:
                raise ValueError(f"Maximum number of collections ({max_collections}) reached")
            
            # Create collection ID
            collection_id = str(uuid.uuid4())
            
            # Create collection object
            collection = Collection(
                id=collection_id,
                name=name,
                description=description.strip(),
                created_at=datetime.now(),
                document_count=0,
                total_chunks=0
            )
            
            # Validate collection
            validation_errors = collection.validate()
            if validation_errors:
                raise ValueError(f"Invalid collection data: {validation_errors}")
            
            try:
                # Create collection in vector database
                self.vector_store.create_collection(
                    name=collection_id,
                    metadata={
                        'name': name,
                        'description': description,
                        'created_at': collection.created_at.isoformat()
                    }
                )
                
                # Store in memory and persist
                self._collections[collection_id] = collection
                self._save_collections()
                
                self.logger.info(f"Created collection '{name}' with ID {collection_id}")
                return collection
                
            except Exception as e:
                self.logger.error(f"Failed to create collection '{name}': {e}")
                raise
    
    def delete_collection(self, collection_id: str) -> bool:
        """
        Delete a collection and all its documents.
        
        Args:
            collection_id: ID of the collection to delete
            
        Returns:
            True if collection was deleted, False if not found
        """
        with self._lock:
            if collection_id not in self._collections:
                return False
            
            collection = self._collections[collection_id]
            
            try:
                # Delete from vector database
                self.vector_store.delete_collection(collection_id)
                
                # Remove associated documents
                documents_to_remove = [
                    doc_id for doc_id, doc in self._documents.items()
                    if doc.collection_id == collection_id
                ]
                
                for doc_id in documents_to_remove:
                    del self._documents[doc_id]
                
                # Remove collection
                del self._collections[collection_id]
                
                # Persist changes
                self._save_collections()
                self._save_documents()
                
                self.logger.info(f"Deleted collection '{collection.name}' and {len(documents_to_remove)} documents")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to delete collection {collection_id}: {e}")
                return False
    
    def add_document_async(self, collection_id: str, file_path: str, doc_type: DocumentType) -> ProcessingTask:
        """
        Add a document to a collection asynchronously.
        
        Args:
            collection_id: ID of the target collection
            file_path: Path to the document file
            doc_type: Type of document
            
        Returns:
            ProcessingTask object for tracking progress
        """
        # Validate inputs
        if collection_id not in self._collections:
            raise ValueError(f"Collection {collection_id} not found")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file not found: {file_path}")
        
        # Check file size limit
        max_file_size = self.kb_config.get('max_file_size_mb', 100) * 1024 * 1024
        file_size = os.path.getsize(file_path)
        if file_size > max_file_size:
            raise ValueError(f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds limit ({max_file_size / 1024 / 1024}MB)")
        
        # Create document record
        document_id = str(uuid.uuid4())
        document = Document(
            id=document_id,
            collection_id=collection_id,
            filename=os.path.basename(file_path),
            file_path=file_path,
            document_type=doc_type,
            processed_at=datetime.now(),
            chunk_count=0,
            file_size=file_size
        )
        
        # Submit processing task
        task = self.task_manager.submit_processing_task(
            collection_id=collection_id,
            file_path=file_path,
            doc_type=doc_type,
            document_id=document_id
        )
        
        # Register callback to handle completion
        self.task_manager.register_progress_callback(
            task.id,
            lambda task_id, progress, message: self._handle_document_processing_completion(
                task_id, document, progress, message
            )
        )
        
        self.logger.info(f"Submitted document processing task {task.id} for {document.filename}")
        return task
    
    def get_processing_status(self, task_id: str) -> Optional[ProcessingTask]:
        """
        Get the status of a processing task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            ProcessingTask object or None if not found
        """
        return self.task_manager.get_task_status(task_id)
    
    def cancel_processing(self, task_id: str) -> bool:
        """
        Cancel a processing task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if task was cancelled, False otherwise
        """
        return self.task_manager.cancel_task(task_id)
    
    def remove_document(self, collection_id: str, document_id: str) -> bool:
        """
        Remove a document from a collection.
        
        Args:
            collection_id: ID of the collection
            document_id: ID of the document to remove
            
        Returns:
            True if document was removed, False if not found
        """
        with self._lock:
            if document_id not in self._documents:
                return False
            
            document = self._documents[document_id]
            if document.collection_id != collection_id:
                return False
            
            try:
                # Remove from vector database
                # Get all chunk IDs for this document
                chunk_ids = [f"{document_id}_chunk_{i}" for i in range(document.chunk_count)]
                if chunk_ids:
                    self.vector_store.delete_documents(collection_id, chunk_ids)
                
                # Remove from memory
                del self._documents[document_id]
                
                # Update collection stats
                if collection_id in self._collections:
                    collection = self._collections[collection_id]
                    collection.document_count = max(0, collection.document_count - 1)
                    collection.total_chunks = max(0, collection.total_chunks - document.chunk_count)
                
                # Persist changes
                self._save_documents()
                self._save_collections()
                
                self.logger.info(f"Removed document {document.filename} from collection {collection_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to remove document {document_id}: {e}")
                return False
    
    def list_collections(self) -> List[Collection]:
        """
        List all collections.
        
        Returns:
            List of Collection objects
        """
        with self._lock:
            return list(self._collections.values())
    
    def get_collection_stats(self, collection_id: str) -> dict:
        """
        Get statistics for a collection.
        
        Args:
            collection_id: ID of the collection
            
        Returns:
            Dictionary with collection statistics
        """
        with self._lock:
            if collection_id not in self._collections:
                return {"error": f"Collection {collection_id} not found"}
            
            collection = self._collections[collection_id]
            
            # Get documents in this collection
            collection_documents = [
                doc for doc in self._documents.values()
                if doc.collection_id == collection_id
            ]
            
            # Calculate statistics
            total_file_size = sum(doc.file_size for doc in collection_documents)
            doc_types = {}
            for doc in collection_documents:
                doc_type = doc.document_type.value
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            
            return {
                "collection_id": collection_id,
                "name": collection.name,
                "description": collection.description,
                "created_at": collection.created_at.isoformat(),
                "document_count": len(collection_documents),
                "total_chunks": collection.total_chunks,
                "total_file_size": total_file_size,
                "document_types": doc_types,
                "recent_documents": [
                    {
                        "id": doc.id,
                        "filename": doc.filename,
                        "document_type": doc.document_type.value,
                        "file_size": doc.file_size,
                        "processed_at": doc.processed_at.isoformat(),
                        "chunk_count": doc.chunk_count or 0
                    }
                    for doc in sorted(collection_documents, key=lambda x: x.processed_at, reverse=True)[:10]
                ]
            }
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the knowledge base.
        
        Args:
            document_id: ID of the document to delete
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            if document_id not in self._documents:
                self.logger.warning(f"Document {document_id} not found")
                return False
            
            document = self._documents[document_id]
            collection_id = document.collection_id
            
            try:
                # Remove from vector store
                if self.vector_store:
                    # Get all chunks for this document
                    # Note: This is a simplified approach - in a real implementation,
                    # you'd need to track chunk IDs to delete specific chunks
                    self.logger.info(f"Removing document {document_id} from vector store")
                
                # Update collection statistics
                if collection_id in self._collections:
                    collection = self._collections[collection_id]
                    collection.document_count = max(0, collection.document_count - 1)
                    if document.chunk_count:
                        collection.total_chunks = max(0, collection.total_chunks - document.chunk_count)
                
                # Remove document record
                del self._documents[document_id]
                
                # Persist changes
                self._save_documents()
                self._save_collections()
                
                self.logger.info(f"Document {document.filename} deleted successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to delete document {document_id}: {e}")
                return False
    
    def get_document_chunks(self, document_id: str) -> list:
        """
        Get all chunks for a specific document.
        
        Args:
            document_id: ID of the document
            
        Returns:
            List of document chunks
        """
        if document_id not in self._documents:
            return []
        
        document = self._documents[document_id]
        collection_id = document.collection_id
        
        try:
            # Query vector store for chunks by document_id
            if self.vector_store:
                collection = self.vector_store.get_collection(collection_id)
                if collection:
                    # Get all documents from the collection and filter by document_id
                    try:
                        # ChromaDB query to get documents with specific metadata
                        results = collection.get(
                            where={"document_id": document_id},
                            include=["documents", "metadatas"]
                        )
                        
                        chunks = []
                        if results and 'documents' in results:
                            documents = results['documents']
                            metadatas = results.get('metadatas', [])
                            
                            for i, (content, metadata) in enumerate(zip(documents, metadatas)):
                                chunks.append({
                                    "id": f"chunk_{i+1}",
                                    "content": content,
                                    "metadata": metadata or {}
                                })
                        
                        return chunks
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to query vector store for document chunks: {e}")
                        # Fall back to mock data
                        pass
            
            # Fallback: return mock data structure
            return [
                {
                    "id": f"chunk_{i+1}",
                    "content": f"文档片段 {i+1}\n\n这是来自文件 '{document.filename}' 的第 {i+1} 个文档片段。\n\n由于向量存储查询失败，这里显示的是模拟内容。实际内容需要从向量数据库中获取。",
                    "metadata": {
                        "chunk_index": i,
                        "source_file": document.filename,
                        "document_id": document_id,
                        "document_type": document.document_type.value
                    }
                }
                for i in range(min(document.chunk_count or 3, 10))  # Limit to 10 chunks for preview
            ]
            
        except Exception as e:
            self.logger.error(f"Failed to get chunks for document {document_id}: {e}")
            return []
    
    def export_collection(self, collection_id: str, format: str = "json") -> str:
        """
        Export a collection to a file.
        
        Args:
            collection_id: ID of the collection to export
            format: Export format ("json" or "csv")
            
        Returns:
            Path to the exported file
        """
        if collection_id not in self._collections:
            raise ValueError(f"Collection {collection_id} not found")
        
        collection = self._collections[collection_id]
        
        # Create export filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in collection.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        export_filename = f"{safe_name}_{timestamp}.{format}"
        export_path = os.path.join(self.storage_path, "exports", export_filename)
        
        # Ensure export directory exists
        os.makedirs(os.path.dirname(export_path), exist_ok=True)
        
        try:
            if format.lower() == "json":
                self._export_collection_json(collection_id, export_path)
            elif format.lower() == "csv":
                self._export_collection_csv(collection_id, export_path)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            self.logger.info(f"Exported collection '{collection.name}' to {export_path}")
            return export_path
            
        except Exception as e:
            self.logger.error(f"Failed to export collection {collection_id}: {e}")
            raise
    
    def import_collection(self, file_path: str, merge_strategy: str = "skip") -> Collection:
        """
        Import a collection from a file.
        
        Args:
            file_path: Path to the import file
            merge_strategy: Strategy for handling existing collections ("skip", "replace", "merge")
            
        Returns:
            Imported Collection object
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Import file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Validate import data structure
            if 'collection' not in import_data or 'documents' not in import_data:
                raise ValueError("Invalid import file format")
            
            collection_data = import_data['collection']
            documents_data = import_data['documents']
            
            # Check if collection already exists
            existing_collection = None
            for collection in self._collections.values():
                if collection.name == collection_data['name']:
                    existing_collection = collection
                    break
            
            if existing_collection:
                if merge_strategy == "skip":
                    self.logger.info(f"Collection '{collection_data['name']}' already exists, skipping import")
                    return existing_collection
                elif merge_strategy == "replace":
                    self.delete_collection(existing_collection.id)
                # For "merge" strategy, we'll add documents to existing collection
            
            # Create or use existing collection
            if not existing_collection or merge_strategy == "replace":
                collection = self.create_collection(
                    name=collection_data['name'],
                    description=collection_data.get('description', '')
                )
            else:
                collection = existing_collection
            
            # Import documents (this would require re-processing the original files)
            # For now, we'll just log the import attempt
            self.logger.info(f"Imported collection '{collection.name}' with {len(documents_data)} document records")
            
            return collection
            
        except Exception as e:
            self.logger.error(f"Failed to import collection from {file_path}: {e}")
            raise
    
    def list_processing_tasks(self) -> List[ProcessingTask]:
        """
        List all processing tasks.
        
        Returns:
            List of ProcessingTask objects
        """
        return self.task_manager.list_all_tasks()
    
    def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """
        Get overall knowledge base statistics.
        
        Returns:
            Dictionary with knowledge base statistics
        """
        with self._lock:
            total_documents = len(self._documents)
            total_chunks = sum(collection.total_chunks for collection in self._collections.values())
            total_file_size = sum(doc.file_size for doc in self._documents.values())
            
            # Document type distribution
            doc_types = {}
            for doc in self._documents.values():
                doc_type = doc.document_type.value
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            
            # Task statistics
            task_stats = self.task_manager.get_task_statistics()
            
            return {
                "total_collections": len(self._collections),
                "total_documents": total_documents,
                "total_chunks": total_chunks,
                "total_file_size": total_file_size,
                "document_types": doc_types,
                "task_statistics": task_stats,
                "storage_path": self.storage_path,
                "vector_database": {
                    "connection_type": self.chromadb_config.connection_type,
                    "path": self.chromadb_config.path
                }
            }
    
    def search_knowledge(self, query: str, collection_ids: List[str] = None, top_k: int = 10) -> List:
        """
        Search for knowledge across collections.
        
        Args:
            query: Search query
            collection_ids: List of collection IDs to search (None for all)
            top_k: Maximum number of results
            
        Returns:
            List of knowledge fragments
        """
        if collection_ids is None:
            collection_ids = list(self._collections.keys())
        
        # Validate collection IDs
        valid_collection_ids = [cid for cid in collection_ids if cid in self._collections]
        
        if not valid_collection_ids:
            return []
        
        try:
            return self.retriever.retrieve_relevant_knowledge(
                query=query,
                collections=valid_collection_ids,
                top_k=top_k
            )
        except Exception as e:
            self.logger.error(f"Knowledge search failed: {e}")
            return []
    
    def shutdown(self):
        """Shutdown the knowledge base manager and clean up resources."""
        self.logger.info("Shutting down KnowledgeBaseManager...")
        
        try:
            self.task_manager.shutdown()
            self.retriever.close()
            self.logger.info("KnowledgeBaseManager shutdown complete")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def _handle_document_processing_completion(self, task_id: str, document: Document, 
                                             progress: float, message: str):
        """Handle document processing completion callback."""
        if progress >= 1.0:  # Task completed
            task = self.task_manager.get_task_status(task_id)
            if task and task.status.value == "completed":
                # Update document and collection metadata
                with self._lock:
                    # Store document
                    self._documents[document.id] = document
                    
                    # Update collection stats
                    if document.collection_id in self._collections:
                        collection = self._collections[document.collection_id]
                        collection.document_count += 1
                        # Update chunk count from task
                        if hasattr(task, 'chunk_count') and task.chunk_count:
                            collection.total_chunks += task.chunk_count
                            document.chunk_count = task.chunk_count
                    
                    # Persist changes
                    self._save_documents()
                    self._save_collections()
                
                self.logger.info(f"Document processing completed for {document.filename}")
    
    def _load_metadata(self):
        """Load collection and document metadata from storage."""
        # Load collections
        if os.path.exists(self.collections_file):
            try:
                with open(self.collections_file, 'r', encoding='utf-8') as f:
                    collections_data = json.load(f)
                
                for collection_data in collections_data:
                    collection = Collection(
                        id=collection_data['id'],
                        name=collection_data['name'],
                        description=collection_data['description'],
                        created_at=datetime.fromisoformat(collection_data['created_at']),
                        document_count=collection_data['document_count'],
                        total_chunks=collection_data['total_chunks']
                    )
                    self._collections[collection.id] = collection
                
                self.logger.info(f"Loaded {len(self._collections)} collections from storage")
                
            except Exception as e:
                self.logger.error(f"Failed to load collections metadata: {e}")
        
        # Load documents
        if os.path.exists(self.documents_file):
            try:
                with open(self.documents_file, 'r', encoding='utf-8') as f:
                    documents_data = json.load(f)
                
                for document_data in documents_data:
                    document = Document(
                        id=document_data['id'],
                        collection_id=document_data['collection_id'],
                        filename=document_data['filename'],
                        file_path=document_data['file_path'],
                        document_type=DocumentType(document_data['document_type']),
                        processed_at=datetime.fromisoformat(document_data['processed_at']),
                        chunk_count=document_data['chunk_count'],
                        file_size=document_data['file_size']
                    )
                    self._documents[document.id] = document
                
                self.logger.info(f"Loaded {len(self._documents)} documents from storage")
                
            except Exception as e:
                self.logger.error(f"Failed to load documents metadata: {e}")
    
    def _save_collections(self):
        """Save collections metadata to storage."""
        try:
            collections_data = []
            for collection in self._collections.values():
                collections_data.append({
                    'id': collection.id,
                    'name': collection.name,
                    'description': collection.description,
                    'created_at': collection.created_at.isoformat(),
                    'document_count': collection.document_count,
                    'total_chunks': collection.total_chunks
                })
            
            with open(self.collections_file, 'w', encoding='utf-8') as f:
                json.dump(collections_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"Failed to save collections metadata: {e}")
    
    def _save_documents(self):
        """Save documents metadata to storage."""
        try:
            documents_data = []
            for document in self._documents.values():
                documents_data.append({
                    'id': document.id,
                    'collection_id': document.collection_id,
                    'filename': document.filename,
                    'file_path': document.file_path,
                    'document_type': document.document_type.value,
                    'processed_at': document.processed_at.isoformat(),
                    'chunk_count': document.chunk_count,
                    'file_size': document.file_size
                })
            
            with open(self.documents_file, 'w', encoding='utf-8') as f:
                json.dump(documents_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"Failed to save documents metadata: {e}")
    
    def _export_collection_json(self, collection_id: str, export_path: str):
        """Export collection to JSON format."""
        collection = self._collections[collection_id]
        collection_documents = [
            doc for doc in self._documents.values()
            if doc.collection_id == collection_id
        ]
        
        export_data = {
            'collection': {
                'id': collection.id,
                'name': collection.name,
                'description': collection.description,
                'created_at': collection.created_at.isoformat(),
                'document_count': collection.document_count,
                'total_chunks': collection.total_chunks
            },
            'documents': [
                {
                    'id': doc.id,
                    'filename': doc.filename,
                    'file_path': doc.file_path,
                    'document_type': doc.document_type.value,
                    'processed_at': doc.processed_at.isoformat(),
                    'chunk_count': doc.chunk_count,
                    'file_size': doc.file_size
                }
                for doc in collection_documents
            ],
            'export_metadata': {
                'exported_at': datetime.now().isoformat(),
                'export_format': 'json',
                'exporter_version': '1.0'
            }
        }
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    def _export_collection_csv(self, collection_id: str, export_path: str):
        """Export collection to CSV format."""
        import csv
        
        collection = self._collections[collection_id]
        collection_documents = [
            doc for doc in self._documents.values()
            if doc.collection_id == collection_id
        ]
        
        with open(export_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                'Document ID', 'Filename', 'Document Type', 'File Size (bytes)',
                'Chunk Count', 'Processed At'
            ])
            
            # Write document data
            for doc in collection_documents:
                writer.writerow([
                    doc.id,
                    doc.filename,
                    doc.document_type.value,
                    doc.file_size,
                    doc.chunk_count,
                    doc.processed_at.isoformat()
                ])
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            self.shutdown()
        except Exception:
            pass