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
    
    def generate_embedding(self, text: str, max_retries: int = 3, retry_delay: float = 1.0) -> Optional[List[float]]:
        """
        Generate embedding for a single text with retry mechanism.
        
        Args:
            text: Text to generate embedding for
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Delay between retries in seconds (default: 1.0)
        
        Returns:
            Embedding vector or None if all attempts fail
        """
        if not self.is_available():
            self.logger.error("Embedding service not available")
            return None
        
        # Check cache first
        if self.cache:
            cached_embedding = self.cache.get_embedding(text, self.config.get('model', 'default'))
            if cached_embedding:
                self.logger.debug("Using cached embedding")
                return cached_embedding
        
        # Retry loop
        for attempt in range(max_retries):
            try:
                # Prepare API request
                data = {
                    'model': self.config['model'],
                    'input': text
                }
                
                # Make API request
                text_preview = text[:100] + "..." if len(text) > 100 else text
                if attempt > 0:
                    self.logger.info(f"Retry attempt {attempt + 1}/{max_retries} for text: {text_preview}")
                else:
                    self.logger.debug(f"Generating embedding for text: {text_preview}")
                
                request_start = time.time()
                response = self.session.post(
                    self.config['endpoint'],
                    json=data,
                    timeout=self.config.get('timeout', 30)
                )
                request_time = time.time() - request_start
                
                response.raise_for_status()
                result = response.json()
                
                # Extract embedding from response
                if 'data' in result and len(result['data']) > 0:
                    embedding = result['data'][0].get('embedding', [])
                    self.logger.debug(f"Generated embedding with {len(embedding)} dimensions in {request_time:.2f}s")
                    
                    # Cache the embedding
                    if self.cache and embedding:
                        self.cache.cache_embedding(text, embedding, self.config.get('model', 'default'))
                    
                    return embedding
                else:
                    self.logger.error(f"Invalid embedding API response format: {result}")
                    print(f"❌ [Embedding] API响应格式错误: {result}")
                    # Don't retry on invalid response format
                    return None
                    
            except requests.exceptions.Timeout as e:
                self.logger.warning(f"Embedding API request timeout (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"⏰ [Embedding] API请求超时 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print(f"   🔄 等待 {retry_delay}s 后重试...")
                    time.sleep(retry_delay)
                    continue
                return None
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Embedding API request failed (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"🌐 [Embedding] API请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print(f"   🔄 等待 {retry_delay}s 后重试...")
                    time.sleep(retry_delay)
                    continue
                return None
                
            except Exception as e:
                self.logger.error(f"Failed to generate embedding (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"❌ [Embedding] 生成向量失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print(f"   🔄 等待 {retry_delay}s 后重试...")
                    time.sleep(retry_delay)
                    continue
                return None
        
        # All retries exhausted
        self.logger.error(f"All {max_retries} retry attempts exhausted for embedding generation")
        print(f"❌ [Embedding] 所有 {max_retries} 次重试均失败")
        return None
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 10, max_workers: int = 3, progress_callback=None) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts in batches."""
        if not texts:
            return []
        
        if not self.is_available():
            self.logger.error("Embedding service not available")
            return [None] * len(texts)
        
        # Get retry settings from config
        max_retries = self.config.get('max_retries', 3)
        retry_delay = self.config.get('retry_delay', 1.0)
        
        print(f"🔤 [Embedding] 开始生成 {len(texts)} 个文本的向量")
        print(f"   - 批次大小: {batch_size}")
        print(f"   - 并发数: {max_workers}")
        print(f"   - 最大重试次数: {max_retries}")
        print(f"   - 重试延迟: {retry_delay}s")
        print(f"   - API端点: {self.config.get('endpoint', 'N/A')}")
        print(f"   - 模型: {self.config.get('model', 'N/A')}")
        
        embeddings = [None] * len(texts)
        total_batches = (len(texts) + batch_size - 1) // batch_size
        start_time = time.time()
        
        # Process in batches to avoid overwhelming the API
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_indices = list(range(i, min(i + batch_size, len(texts))))
            batch_num = i // batch_size + 1
            
            print(f"📦 [Embedding] 处理批次 {batch_num}/{total_batches} ({len(batch_texts)} 个文本)")
            batch_start_time = time.time()
            
            # Use thread pool for concurrent requests within batch
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit tasks with retry parameters
                future_to_index = {
                    executor.submit(self.generate_embedding, text, max_retries, retry_delay): (idx, text)
                    for idx, text in zip(batch_indices, batch_texts)
                }
                
                # Collect results
                batch_successful = 0
                batch_failed_indices = []
                for future in as_completed(future_to_index):
                    idx, text = future_to_index[future]
                    try:
                        embedding = future.result()
                        embeddings[idx] = embedding
                        if embedding is not None:
                            batch_successful += 1
                        else:
                            batch_failed_indices.append(idx)
                            print(f"   ⚠️ [Embedding] 索引 {idx} 生成失败（已重试）")
                            self.logger.warning(f"Failed to generate embedding for text at index {idx} after retries")
                    except Exception as e:
                        batch_failed_indices.append(idx)
                        print(f"   ❌ [Embedding] 索引 {idx} 异常: {e}")
                        self.logger.error(f"Exception generating embedding for text at index {idx}: {e}")
                        embeddings[idx] = None
            
            batch_time = time.time() - batch_start_time
            print(f"   ✅ [Embedding] 批次 {batch_num} 完成: {batch_successful}/{len(batch_texts)} 成功 (耗时: {batch_time:.2f}s)")
            
            # Show failed indices if any
            if batch_failed_indices:
                print(f"   ⚠️ [Embedding] 失败的索引: {batch_failed_indices}")
            
            # Call progress callback if provided
            if progress_callback:
                completed_count = min(i + batch_size, len(texts))
                progress_callback(completed_count, len(texts))
            
            # Add delay between batches to respect rate limits
            if i + batch_size < len(texts):
                delay = 0.2  # Reduce delay from 0.5s to 0.2s
                print(f"   ⏳ [Embedding] 等待 {delay}s 避免API限流...")
                time.sleep(delay)
        
        total_time = time.time() - start_time
        successful_count = sum(1 for e in embeddings if e is not None)
        print(f"🎉 [Embedding] 全部完成: {successful_count}/{len(texts)} 成功 (总耗时: {total_time:.2f}s)")
        
        if successful_count < len(texts):
            failed_count = len(texts) - successful_count
            print(f"⚠️ [Embedding] {failed_count} 个文本生成失败")
        
        self.logger.info(f"Generated {successful_count}/{len(texts)} embeddings successfully in {total_time:.2f}s")
        
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