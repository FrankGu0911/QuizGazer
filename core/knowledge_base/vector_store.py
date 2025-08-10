"""
Vector Store Manager - Manages ChromaDB operations and vector storage.
"""

import os
import uuid
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.api.models.Collection import Collection as ChromaCollection
except ImportError:
    chromadb = None
    Settings = None
    ChromaCollection = None

try:
    from .models import DocumentChunk, SearchResult, ChromaDBConfig, ConnectionStatus, DatabaseInfo
except ImportError:
    from models import DocumentChunk, SearchResult, ChromaDBConfig, ConnectionStatus, DatabaseInfo


class VectorStoreManager:
    """Manages ChromaDB operations and vector storage with support for both local and remote deployments."""
    
    def __init__(self, connection_config: ChromaDBConfig):
        """Initialize the Vector Store Manager with connection configuration."""
        if chromadb is None:
            raise ImportError("ChromaDB is not installed. Please install it with: pip install chromadb")
        
        self.config = connection_config
        self.client = None
        self.logger = logging.getLogger(__name__)
        
        # Validate configuration
        config_errors = self.config.validate()
        if config_errors:
            raise ValueError(f"Invalid ChromaDB configuration: {config_errors}")
    
    def initialize_database(self) -> None:
        """Initialize the ChromaDB database."""
        try:
            if self.config.connection_type == "local":
                # Create local storage directory if it doesn't exist
                os.makedirs(self.config.path, exist_ok=True)
                
                # Initialize local ChromaDB client
                self.client = chromadb.PersistentClient(
                    path=self.config.path,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                self.logger.info(f"Initialized local ChromaDB at {self.config.path}")
                
            elif self.config.connection_type == "remote":
                # Initialize remote ChromaDB client
                settings = Settings(
                    anonymized_telemetry=False
                )
                
                self.client = chromadb.HttpClient(
                    host=self.config.host,
                    port=self.config.port,
                    ssl=self.config.ssl_enabled,
                    settings=settings
                )
                self.logger.info(f"Initialized remote ChromaDB at {self.config.host}:{self.config.port}")
            
            else:
                raise ValueError(f"Unsupported connection type: {self.config.connection_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def create_collection(self, name: str, metadata: dict = None) -> ChromaCollection:
        """Create a new collection in ChromaDB."""
        if not self.client:
            self.initialize_database()
        
        try:
            # Add default metadata
            collection_metadata = {
                "created_at": datetime.now().isoformat(),
                "description": metadata.get("description", "") if metadata else "",
                **(metadata or {})
            }
            
            collection = self.client.create_collection(
                name=name,
                metadata=collection_metadata
            )
            
            self.logger.info(f"Created collection: {name}")
            return collection
            
        except Exception as e:
            self.logger.error(f"Failed to create collection {name}: {e}")
            raise
    
    def get_collection(self, name: str) -> Optional[ChromaCollection]:
        """Get an existing collection by name."""
        if not self.client:
            self.initialize_database()
        
        try:
            return self.client.get_collection(name=name)
        except Exception as e:
            self.logger.warning(f"Collection {name} not found: {e}")
            return None
    
    def add_documents(self, collection_name: str, chunks: List[DocumentChunk], embeddings: List[List[float]]) -> None:
        """Add document chunks and their embeddings to a collection."""
        if not self.client:
            self.initialize_database()
        
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")
        
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                raise ValueError(f"Collection {collection_name} does not exist")
            
            # Prepare data for ChromaDB
            ids = [chunk.id for chunk in chunks]
            documents = [chunk.content for chunk in chunks]
            metadatas = []
            
            for chunk in chunks:
                chunk_metadata = {
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    **chunk.metadata
                }
                metadatas.append(chunk_metadata)
            
            # Add to collection
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            self.logger.info(f"Added {len(chunks)} chunks to collection {collection_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to add documents to collection {collection_name}: {e}")
            raise
    
    def search_similar(self, collection_names: List[str], query_embedding: List[float], top_k: int = 10) -> List[SearchResult]:
        """Search for similar documents across collections."""
        if not self.client:
            self.initialize_database()
        
        all_results = []
        
        try:
            for collection_name in collection_names:
                collection = self.get_collection(collection_name)
                if not collection:
                    self.logger.warning(f"Collection {collection_name} not found, skipping")
                    continue
                
                # Query the collection
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k
                )
                
                # Convert results to SearchResult objects
                if results['ids'] and results['ids'][0]:
                    for i, chunk_id in enumerate(results['ids'][0]):
                        search_result = SearchResult(
                            chunk_id=chunk_id,
                            content=results['documents'][0][i] if results['documents'] and results['documents'][0] else "",
                            distance=results['distances'][0][i] if results['distances'] and results['distances'][0] else 0.0,
                            metadata={
                                "collection_name": collection_name,
                                **(results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {})
                            }
                        )
                        all_results.append(search_result)
            
            # Sort by distance (lower is better) and return top_k
            all_results.sort(key=lambda x: x.distance)
            return all_results[:top_k]
            
        except Exception as e:
            self.logger.error(f"Failed to search collections {collection_names}: {e}")
            raise
    
    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection from ChromaDB."""
        if not self.client:
            self.initialize_database()
        
        try:
            self.client.delete_collection(name=collection_name)
            self.logger.info(f"Deleted collection: {collection_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete collection {collection_name}: {e}")
            return False
    
    def delete_documents(self, collection_name: str, document_ids: List[str]) -> bool:
        """Delete specific documents from a collection."""
        if not self.client:
            self.initialize_database()
        
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                raise ValueError(f"Collection {collection_name} does not exist")
            
            collection.delete(ids=document_ids)
            self.logger.info(f"Deleted {len(document_ids)} documents from collection {collection_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete documents from collection {collection_name}: {e}")
            return False
    
    def get_collection_stats(self, collection_name: str) -> dict:
        """Get statistics for a collection."""
        if not self.client:
            self.initialize_database()
        
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                return {"error": f"Collection {collection_name} not found"}
            
            # Get collection count
            count = collection.count()
            
            # Get collection metadata
            metadata = collection.metadata or {}
            
            return {
                "name": collection_name,
                "document_count": count,
                "metadata": metadata,
                "created_at": metadata.get("created_at", "Unknown")
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get stats for collection {collection_name}: {e}")
            return {"error": str(e)}
    
    def list_collections(self) -> List[str]:
        """List all collection names."""
        if not self.client:
            self.initialize_database()
        
        try:
            collections = self.client.list_collections()
            return [col.name for col in collections]
            
        except Exception as e:
            self.logger.error(f"Failed to list collections: {e}")
            return []
    
    def test_connection(self) -> ConnectionStatus:
        """Test the connection to ChromaDB."""
        try:
            if not self.client:
                self.initialize_database()
            
            # Try to list collections as a connection test
            collections = self.client.list_collections()
            
            return ConnectionStatus(
                is_connected=True,
                connection_type=self.config.connection_type,
                database_version=chromadb.__version__ if hasattr(chromadb, '__version__') else "Unknown",
                error_message=None
            )
            
        except Exception as e:
            return ConnectionStatus(
                is_connected=False,
                connection_type=self.config.connection_type,
                database_version="Unknown",
                error_message=str(e)
            )
    
    def get_database_info(self) -> DatabaseInfo:
        """Get information about the database."""
        if not self.client:
            self.initialize_database()
        
        try:
            collections = self.client.list_collections()
            total_collections = len(collections)
            total_documents = 0
            
            # Count total documents across all collections
            for collection in collections:
                try:
                    col = self.client.get_collection(collection.name)
                    total_documents += col.count()
                except Exception as e:
                    self.logger.warning(f"Failed to count documents in collection {collection.name}: {e}")
            
            # Estimate storage size (this is approximate)
            storage_size = "Unknown"
            if self.config.connection_type == "local" and self.config.path:
                try:
                    total_size = 0
                    for dirpath, dirnames, filenames in os.walk(self.config.path):
                        for filename in filenames:
                            filepath = os.path.join(dirpath, filename)
                            total_size += os.path.getsize(filepath)
                    storage_size = f"{total_size / (1024*1024):.2f} MB"
                except Exception as e:
                    self.logger.warning(f"Failed to calculate storage size: {e}")
            
            return DatabaseInfo(
                total_collections=total_collections,
                total_documents=total_documents,
                storage_size=storage_size,
                connection_info=self.config
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get database info: {e}")
            return DatabaseInfo(
                total_collections=0,
                total_documents=0,
                storage_size="Unknown",
                connection_info=self.config
            )