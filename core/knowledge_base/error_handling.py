"""
Comprehensive error handling for knowledge base operations.
"""

import logging
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Type, Union
from enum import Enum
from dataclasses import dataclass
from functools import wraps


class ErrorCategory(Enum):
    """Categories of errors that can occur in the knowledge base system."""
    
    # API related errors
    API_CONNECTION = "api_connection"
    API_AUTHENTICATION = "api_authentication"
    API_RATE_LIMIT = "api_rate_limit"
    API_TIMEOUT = "api_timeout"
    API_INVALID_RESPONSE = "api_invalid_response"
    
    # Database related errors
    DATABASE_CONNECTION = "database_connection"
    DATABASE_QUERY = "database_query"
    DATABASE_CORRUPTION = "database_corruption"
    
    # File system errors
    FILE_NOT_FOUND = "file_not_found"
    FILE_PERMISSION = "file_permission"
    FILE_FORMAT = "file_format"
    FILE_SIZE_LIMIT = "file_size_limit"
    
    # Processing errors
    PROCESSING_TIMEOUT = "processing_timeout"
    PROCESSING_MEMORY = "processing_memory"
    PROCESSING_FORMAT = "processing_format"
    
    # Configuration errors
    CONFIG_MISSING = "config_missing"
    CONFIG_INVALID = "config_invalid"
    
    # General errors
    VALIDATION = "validation"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Information about an error occurrence."""
    
    category: ErrorCategory
    message: str
    details: Optional[str] = None
    recoverable: bool = True
    retry_after: Optional[float] = None
    user_message: Optional[str] = None
    technical_details: Optional[Dict[str, Any]] = None


class KnowledgeBaseError(Exception):
    """Base exception for knowledge base operations."""
    
    def __init__(self, error_info: ErrorInfo, original_exception: Optional[Exception] = None):
        self.error_info = error_info
        self.original_exception = original_exception
        super().__init__(error_info.message)


class APIError(KnowledgeBaseError):
    """Exception for API-related errors."""
    pass


class DatabaseError(KnowledgeBaseError):
    """Exception for database-related errors."""
    pass


class FileError(KnowledgeBaseError):
    """Exception for file-related errors."""
    pass


class ProcessingError(KnowledgeBaseError):
    """Exception for processing-related errors."""
    pass


class ConfigurationError(KnowledgeBaseError):
    """Exception for configuration-related errors."""
    pass


class ValidationError(KnowledgeBaseError):
    """Exception for validation errors."""
    pass


class RetryConfig:
    """Configuration for retry mechanisms."""
    
    def __init__(self, 
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class ErrorHandler:
    """Centralized error handling for knowledge base operations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._error_patterns = self._initialize_error_patterns()
        self._retry_configs = self._initialize_retry_configs()
    
    def _initialize_error_patterns(self) -> Dict[str, ErrorInfo]:
        """Initialize common error patterns and their handling information."""
        return {
            # API Errors
            "connection_error": ErrorInfo(
                category=ErrorCategory.API_CONNECTION,
                message="API connection failed",
                recoverable=True,
                retry_after=5.0,
                user_message="网络连接失败，请检查网络连接后重试"
            ),
            "authentication_error": ErrorInfo(
                category=ErrorCategory.API_AUTHENTICATION,
                message="API authentication failed",
                recoverable=False,
                user_message="API认证失败，请检查API密钥配置"
            ),
            "rate_limit_error": ErrorInfo(
                category=ErrorCategory.API_RATE_LIMIT,
                message="API rate limit exceeded",
                recoverable=True,
                retry_after=60.0,
                user_message="API调用频率超限，请稍后重试"
            ),
            "timeout_error": ErrorInfo(
                category=ErrorCategory.API_TIMEOUT,
                message="API request timeout",
                recoverable=True,
                retry_after=10.0,
                user_message="请求超时，请重试"
            ),
            
            # Database Errors
            "database_connection_error": ErrorInfo(
                category=ErrorCategory.DATABASE_CONNECTION,
                message="Database connection failed",
                recoverable=True,
                retry_after=5.0,
                user_message="数据库连接失败，请检查数据库配置"
            ),
            "database_query_error": ErrorInfo(
                category=ErrorCategory.DATABASE_QUERY,
                message="Database query failed",
                recoverable=True,
                retry_after=2.0,
                user_message="数据库查询失败，请重试"
            ),
            
            # File Errors
            "file_not_found": ErrorInfo(
                category=ErrorCategory.FILE_NOT_FOUND,
                message="File not found",
                recoverable=False,
                user_message="文件未找到，请检查文件路径"
            ),
            "file_permission_error": ErrorInfo(
                category=ErrorCategory.FILE_PERMISSION,
                message="File permission denied",
                recoverable=False,
                user_message="文件访问权限不足，请检查文件权限"
            ),
            "file_format_error": ErrorInfo(
                category=ErrorCategory.FILE_FORMAT,
                message="Invalid file format",
                recoverable=False,
                user_message="文件格式不支持，请使用支持的文件格式"
            ),
            "file_size_error": ErrorInfo(
                category=ErrorCategory.FILE_SIZE_LIMIT,
                message="File size exceeds limit",
                recoverable=False,
                user_message="文件大小超过限制，请使用较小的文件"
            ),
            
            # Processing Errors
            "processing_timeout": ErrorInfo(
                category=ErrorCategory.PROCESSING_TIMEOUT,
                message="Processing timeout",
                recoverable=True,
                retry_after=30.0,
                user_message="处理超时，请重试或使用较小的文件"
            ),
            "memory_error": ErrorInfo(
                category=ErrorCategory.PROCESSING_MEMORY,
                message="Insufficient memory for processing",
                recoverable=True,
                retry_after=60.0,
                user_message="内存不足，请稍后重试或使用较小的文件"
            ),
            
            # Configuration Errors
            "config_missing": ErrorInfo(
                category=ErrorCategory.CONFIG_MISSING,
                message="Required configuration missing",
                recoverable=False,
                user_message="配置缺失，请检查配置文件"
            ),
            "config_invalid": ErrorInfo(
                category=ErrorCategory.CONFIG_INVALID,
                message="Invalid configuration",
                recoverable=False,
                user_message="配置无效，请检查配置设置"
            )
        }
    
    def _initialize_retry_configs(self) -> Dict[ErrorCategory, RetryConfig]:
        """Initialize retry configurations for different error categories."""
        return {
            ErrorCategory.API_CONNECTION: RetryConfig(max_attempts=3, base_delay=2.0),
            ErrorCategory.API_TIMEOUT: RetryConfig(max_attempts=2, base_delay=5.0),
            ErrorCategory.API_RATE_LIMIT: RetryConfig(max_attempts=2, base_delay=60.0, exponential_base=1.0),
            ErrorCategory.DATABASE_CONNECTION: RetryConfig(max_attempts=3, base_delay=1.0),
            ErrorCategory.DATABASE_QUERY: RetryConfig(max_attempts=2, base_delay=1.0),
            ErrorCategory.PROCESSING_TIMEOUT: RetryConfig(max_attempts=2, base_delay=10.0),
            ErrorCategory.PROCESSING_MEMORY: RetryConfig(max_attempts=1, base_delay=30.0)
        }
    
    def classify_error(self, exception: Exception) -> ErrorInfo:
        """
        Classify an exception and return appropriate error information.
        
        Args:
            exception: The exception to classify
            
        Returns:
            ErrorInfo object with classification and handling information
        """
        exception_str = str(exception).lower()
        exception_type = type(exception).__name__.lower()
        
        # Check for specific error patterns (order matters!)
        
        # Check database errors first (before general connection errors)
        if ("database" in exception_str or "sqlite" in exception_str or "chroma" in exception_str or
              "db" in exception_str):
            if "connection" in exception_str:
                return self._error_patterns["database_connection_error"]
            else:
                return self._error_patterns["database_query_error"]
        
        # Check authentication errors
        elif "authentication" in exception_str or "unauthorized" in exception_str or "401" in exception_str:
            return self._error_patterns["authentication_error"]
        
        # Check rate limit errors
        elif "rate limit" in exception_str or "429" in exception_str:
            return self._error_patterns["rate_limit_error"]
        
        # Check timeout errors
        elif "timeout" in exception_str or "timeouterror" in exception_type:
            return self._error_patterns["timeout_error"]
        
        # Check general connection errors
        elif ("connection" in exception_str or "network" in exception_str or 
            "connectionerror" in exception_type or "networkerror" in exception_type):
            return self._error_patterns["connection_error"]
        
        # Check file errors
        elif ("file not found" in exception_str or "no such file" in exception_str or 
              "filenotfounderror" in exception_type):
            return self._error_patterns["file_not_found"]
        
        elif ("permission" in exception_str or "access denied" in exception_str or 
              "permissionerror" in exception_type):
            return self._error_patterns["file_permission_error"]
        
        # Check memory errors
        elif "memory" in exception_str or "memoryerror" in exception_type:
            return self._error_patterns["memory_error"]
        
        # Check configuration errors
        elif "config" in exception_str:
            if "missing" in exception_str or "not found" in exception_str:
                return self._error_patterns["config_missing"]
            else:
                return self._error_patterns["config_invalid"]
        
        # Default classification
        return ErrorInfo(
            category=ErrorCategory.UNKNOWN,
            message=f"Unknown error: {str(exception)}",
            recoverable=True,
            user_message="发生未知错误，请重试"
        )
    
    def handle_error(self, exception: Exception, context: str = "") -> ErrorInfo:
        """
        Handle an exception and return error information.
        
        Args:
            exception: The exception to handle
            context: Additional context about where the error occurred
            
        Returns:
            ErrorInfo object with handling information
        """
        error_info = self.classify_error(exception)
        
        # Log the error
        log_message = f"Error in {context}: {error_info.message}"
        if error_info.details:
            log_message += f" - {error_info.details}"
        
        if error_info.category in [ErrorCategory.CONFIG_MISSING, ErrorCategory.CONFIG_INVALID]:
            self.logger.error(log_message)
        elif error_info.recoverable:
            self.logger.warning(log_message)
        else:
            self.logger.error(log_message)
        
        # Log technical details for debugging
        self.logger.debug(f"Exception details: {traceback.format_exc()}")
        
        return error_info
    
    def should_retry(self, error_info: ErrorInfo, attempt: int) -> bool:
        """
        Determine if an operation should be retried based on error information.
        
        Args:
            error_info: Information about the error
            attempt: Current attempt number (1-based)
            
        Returns:
            True if the operation should be retried
        """
        if not error_info.recoverable:
            return False
        
        retry_config = self._retry_configs.get(error_info.category)
        if not retry_config:
            return attempt < 2  # Default: retry once
        
        return attempt < retry_config.max_attempts
    
    def get_retry_delay(self, error_info: ErrorInfo, attempt: int) -> float:
        """
        Calculate the delay before retrying an operation.
        
        Args:
            error_info: Information about the error
            attempt: Current attempt number (1-based)
            
        Returns:
            Delay in seconds before retrying
        """
        if error_info.retry_after:
            return error_info.retry_after
        
        retry_config = self._retry_configs.get(error_info.category)
        if not retry_config:
            return 1.0  # Default delay
        
        # Calculate exponential backoff
        delay = retry_config.base_delay * (retry_config.exponential_base ** (attempt - 1))
        delay = min(delay, retry_config.max_delay)
        
        # Add jitter to prevent thundering herd
        if retry_config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)
        
        return delay


# Global error handler instance
_error_handler = ErrorHandler()


def with_error_handling(context: str = "", 
                       raise_on_error: bool = True,
                       return_on_error: Any = None):
    """
    Decorator for adding error handling to functions.
    
    Args:
        context: Context description for logging
        raise_on_error: Whether to raise KnowledgeBaseError on exceptions
        return_on_error: Value to return if an error occurs and raise_on_error is False
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except KnowledgeBaseError:
                # Re-raise knowledge base errors as-is
                raise
            except Exception as e:
                error_info = _error_handler.handle_error(e, context or func.__name__)
                
                if raise_on_error:
                    # Determine the appropriate exception type
                    if error_info.category in [ErrorCategory.API_CONNECTION, ErrorCategory.API_AUTHENTICATION, 
                                             ErrorCategory.API_RATE_LIMIT, ErrorCategory.API_TIMEOUT, 
                                             ErrorCategory.API_INVALID_RESPONSE]:
                        raise APIError(error_info, e)
                    elif error_info.category in [ErrorCategory.DATABASE_CONNECTION, ErrorCategory.DATABASE_QUERY, 
                                                ErrorCategory.DATABASE_CORRUPTION]:
                        raise DatabaseError(error_info, e)
                    elif error_info.category in [ErrorCategory.FILE_NOT_FOUND, ErrorCategory.FILE_PERMISSION, 
                                                ErrorCategory.FILE_FORMAT, ErrorCategory.FILE_SIZE_LIMIT]:
                        raise FileError(error_info, e)
                    elif error_info.category in [ErrorCategory.PROCESSING_TIMEOUT, ErrorCategory.PROCESSING_MEMORY, 
                                                ErrorCategory.PROCESSING_FORMAT]:
                        raise ProcessingError(error_info, e)
                    elif error_info.category in [ErrorCategory.CONFIG_MISSING, ErrorCategory.CONFIG_INVALID]:
                        raise ConfigurationError(error_info, e)
                    elif error_info.category == ErrorCategory.VALIDATION:
                        raise ValidationError(error_info, e)
                    else:
                        raise KnowledgeBaseError(error_info, e)
                else:
                    return return_on_error
        
        return wrapper
    return decorator


def with_retry(max_attempts: int = None, 
               base_delay: float = None,
               context: str = ""):
    """
    Decorator for adding retry logic to functions.
    
    Args:
        max_attempts: Maximum number of attempts (overrides error-specific config)
        base_delay: Base delay between attempts (overrides error-specific config)
        context: Context description for logging
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            last_error = None
            
            while True:
                try:
                    return func(*args, **kwargs)
                except KnowledgeBaseError as e:
                    last_error = e
                    error_info = e.error_info
                except Exception as e:
                    last_error = e
                    error_info = _error_handler.handle_error(e, context or func.__name__)
                
                # Check if we should retry
                if max_attempts and attempt >= max_attempts:
                    should_retry = False
                else:
                    should_retry = _error_handler.should_retry(error_info, attempt)
                
                if not should_retry:
                    if isinstance(last_error, KnowledgeBaseError):
                        raise last_error
                    else:
                        # Convert to appropriate KnowledgeBaseError
                        if error_info.category in [ErrorCategory.API_CONNECTION, ErrorCategory.API_AUTHENTICATION, 
                                                 ErrorCategory.API_RATE_LIMIT, ErrorCategory.API_TIMEOUT]:
                            raise APIError(error_info, last_error)
                        else:
                            raise KnowledgeBaseError(error_info, last_error)
                
                # Calculate delay
                if base_delay:
                    delay = base_delay * (2 ** (attempt - 1))
                else:
                    delay = _error_handler.get_retry_delay(error_info, attempt)
                
                _error_handler.logger.info(f"Retrying {func.__name__} in {delay:.1f}s (attempt {attempt + 1})")
                time.sleep(delay)
                attempt += 1
        
        return wrapper
    return decorator


def get_user_friendly_message(exception: Exception) -> str:
    """
    Get a user-friendly error message for an exception.
    
    Args:
        exception: The exception to get a message for
        
    Returns:
        User-friendly error message
    """
    if isinstance(exception, KnowledgeBaseError):
        return exception.error_info.user_message or exception.error_info.message
    else:
        error_info = _error_handler.classify_error(exception)
        return error_info.user_message or error_info.message


def log_error(exception: Exception, context: str = "", level: str = "error"):
    """
    Log an error with appropriate level and context.
    
    Args:
        exception: The exception to log
        context: Additional context
        level: Log level (debug, info, warning, error, critical)
    """
    error_info = _error_handler.handle_error(exception, context)
    # Error is already logged in handle_error, this is for additional logging if needed


def create_error_report(exception: Exception, context: str = "") -> Dict[str, Any]:
    """
    Create a detailed error report for debugging.
    
    Args:
        exception: The exception to report
        context: Additional context
        
    Returns:
        Dictionary with error report details
    """
    error_info = _error_handler.classify_error(exception)
    
    return {
        "timestamp": time.time(),
        "context": context,
        "error_category": error_info.category.value,
        "error_message": error_info.message,
        "user_message": error_info.user_message,
        "recoverable": error_info.recoverable,
        "retry_after": error_info.retry_after,
        "exception_type": type(exception).__name__,
        "exception_message": str(exception),
        "traceback": traceback.format_exc(),
        "technical_details": error_info.technical_details
    }