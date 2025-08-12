"""
Embedding Service - Handles text embedding generation using external APIs.
"""

import logging
import requests
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

try:
    from .cache_manager import EmbeddingCache
    from utils.config_manager import get_api_config
except ImportError:
    EmbeddingCache = None
    get_api_config = None


class EmbeddingService:
    """Service for generating text embeddings using external APIs."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the embedding service."""
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        if config:
            self.config = config
        elif get_api_config:
            try:
                self.config = get_api_config('embedding_api')
            except Exception as e:
                self.logger.warning(f"Failed to load embedding API config: {e}")
                self.config = None
        else:
            self.config = None
        
        # Initialize cache if available
        self.cache = EmbeddingCache() if EmbeddingCache else None
        
        # HTTP session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
        
        if self.config and self.config.get('api_key'):
            self.session.headers.update({
                'Authorization': f'Bearer {self.config["api_key"]}'
            })
    
    def is_available(self) -> bool:
        """Check if the embedding service is available."""
        return (self.config is not None and 
                self.config.get('endpoint') and 
                self.config.get('api_key') and 
                self.config.get('model'))
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text."""
        if not self.is_available():
            self.logger.error("Embedding service not available")
            return None
        
        # Check cache first
        if self.cache:
            cached_embedding = self.cache.get_embedding(text, self.config.get('model', 'default'))
            if cached_embedding:
                self.logger.debug("Using cached embedding")
                return cached_embedding
        
        try:
            # Prepare API request
            data = {
                'model': self.config['model'],
                'input': text
            }
            
            # Make API request
            self.logger.debug(f"Generating embedding for text: {text[:50]}...")
            response = self.session.post(
                self.config['endpoint'],
                json=data,
                timeout=self.config.get('timeout', 30)
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract embedding from response
            if 'data' in result and len(result['data']) > 0:
                embedding = result['data'][0].get('embedding', [])
                self.logger.debug(f"Generated embedding with {len(embedding)} dimensions")
                
                # Cache the embedding
                if self.cache and embedding:
                    self.cache.cache_embedding(text, embedding, self.config.get('model', 'default'))
                
                return embedding
            else:
                self.logger.error(f"Invalid embedding API response format: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Embedding API request failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 10, max_workers: int = 3) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts in batches."""
        if not texts:
            return []
        
        if not self.is_available():
            self.logger.error("Embedding service not available")
            return [None] * len(texts)
        
        embeddings = [None] * len(texts)
        
        # Process in batches to avoid overwhelming the API
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_indices = list(range(i, min(i + batch_size, len(texts))))
            
            self.logger.debug(f"Processing embedding batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
            
            # Use thread pool for concurrent requests within batch
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit tasks
                future_to_index = {
                    executor.submit(self.generate_embedding, text): (idx, text)
                    for idx, text in zip(batch_indices, batch_texts)
                }
                
                # Collect results
                for future in as_completed(future_to_index):
                    idx, text = future_to_index[future]
                    try:
                        embedding = future.result()
                        embeddings[idx] = embedding
                        if embedding is None:
                            self.logger.warning(f"Failed to generate embedding for text at index {idx}")
                    except Exception as e:
                        self.logger.error(f"Exception generating embedding for text at index {idx}: {e}")
                        embeddings[idx] = None
            
            # Add delay between batches to respect rate limits
            if i + batch_size < len(texts):
                time.sleep(0.5)
        
        successful_count = sum(1 for e in embeddings if e is not None)
        self.logger.info(f"Generated {successful_count}/{len(texts)} embeddings successfully")
        
        return embeddings
    
    def get_embedding_dimension(self) -> Optional[int]:
        """Get the dimension of embeddings from this service."""
        if not self.is_available():
            return None
        
        # Try to get dimension from a test embedding
        test_embedding = self.generate_embedding("test")
        return len(test_embedding) if test_embedding else None
    
    def close(self):
        """Close the HTTP session."""
        if self.session:
            self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Global embedding service instance
_embedding_service = None

def get_embedding_service() -> Optional[EmbeddingService]:
    """Get the global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service if _embedding_service.is_available() else None

def initialize_embedding_service(config: Optional[Dict[str, Any]] = None) -> bool:
    """Initialize the global embedding service."""
    global _embedding_service
    try:
        _embedding_service = EmbeddingService(config)
        return _embedding_service.is_available()
    except Exception as e:
        logging.error(f"Failed to initialize embedding service: {e}")
        return False