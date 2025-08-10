"""
Test error handling functionality.
"""

import sys
import os
import time
from unittest.mock import Mock, patch

sys.path.append(os.path.dirname(__file__))

from error_handling import (
    ErrorHandler, ErrorCategory, ErrorInfo, KnowledgeBaseError,
    APIError, DatabaseError, FileError, ProcessingError,
    with_error_handling, with_retry, get_user_friendly_message
)


def test_error_classification():
    """Test error classification functionality."""
    print("Testing Error Classification...")
    print("=" * 50)
    
    error_handler = ErrorHandler()
    
    # Test 1: Connection errors
    print("\n1. Testing connection error classification:")
    
    connection_error = ConnectionError("Failed to connect to API")
    error_info = error_handler.classify_error(connection_error)
    
    print(f"   Error category: {error_info.category}")
    print(f"   Recoverable: {error_info.recoverable}")
    print(f"   User message: {error_info.user_message}")
    
    assert error_info.category == ErrorCategory.API_CONNECTION
    assert error_info.recoverable == True
    print("   ✓ Connection error classified correctly")
    
    # Test 2: Authentication errors
    print("\n2. Testing authentication error classification:")
    
    auth_error = Exception("401 Unauthorized: Invalid API key")
    error_info = error_handler.classify_error(auth_error)
    
    print(f"   Error category: {error_info.category}")
    print(f"   Recoverable: {error_info.recoverable}")
    print(f"   User message: {error_info.user_message}")
    
    assert error_info.category == ErrorCategory.API_AUTHENTICATION
    assert error_info.recoverable == False
    print("   ✓ Authentication error classified correctly")
    
    # Test 3: File not found errors
    print("\n3. Testing file not found error classification:")
    
    file_error = FileNotFoundError("No such file or directory: 'test.pdf'")
    error_info = error_handler.classify_error(file_error)
    
    print(f"   Error category: {error_info.category}")
    print(f"   Recoverable: {error_info.recoverable}")
    print(f"   User message: {error_info.user_message}")
    
    assert error_info.category == ErrorCategory.FILE_NOT_FOUND
    assert error_info.recoverable == False
    print("   ✓ File not found error classified correctly")
    
    # Test 4: Memory errors
    print("\n4. Testing memory error classification:")
    
    memory_error = MemoryError("Unable to allocate memory")
    error_info = error_handler.classify_error(memory_error)
    
    print(f"   Error category: {error_info.category}")
    print(f"   Recoverable: {error_info.recoverable}")
    print(f"   User message: {error_info.user_message}")
    
    assert error_info.category == ErrorCategory.PROCESSING_MEMORY
    assert error_info.recoverable == True
    print("   ✓ Memory error classified correctly")
    
    print("\n" + "=" * 50)
    print("✓ Error classification tests completed!")


def test_retry_logic():
    """Test retry logic functionality."""
    print("\nTesting Retry Logic...")
    print("=" * 50)
    
    error_handler = ErrorHandler()
    
    # Test 1: Retry decision for recoverable errors
    print("\n1. Testing retry decisions:")
    
    connection_error_info = ErrorInfo(
        category=ErrorCategory.API_CONNECTION,
        message="Connection failed",
        recoverable=True
    )
    
    # Should retry on first attempt
    should_retry_1 = error_handler.should_retry(connection_error_info, 1)
    print(f"   Should retry attempt 1: {should_retry_1}")
    assert should_retry_1 == True
    
    # Should retry on second attempt
    should_retry_2 = error_handler.should_retry(connection_error_info, 2)
    print(f"   Should retry attempt 2: {should_retry_2}")
    assert should_retry_2 == True
    
    # Should not retry on fourth attempt (max is 3)
    should_retry_4 = error_handler.should_retry(connection_error_info, 4)
    print(f"   Should retry attempt 4: {should_retry_4}")
    assert should_retry_4 == False
    
    print("   ✓ Retry decisions working correctly")
    
    # Test 2: No retry for non-recoverable errors
    print("\n2. Testing non-recoverable error retry:")
    
    auth_error_info = ErrorInfo(
        category=ErrorCategory.API_AUTHENTICATION,
        message="Authentication failed",
        recoverable=False
    )
    
    should_retry = error_handler.should_retry(auth_error_info, 1)
    print(f"   Should retry non-recoverable error: {should_retry}")
    assert should_retry == False
    print("   ✓ Non-recoverable errors not retried")
    
    # Test 3: Retry delay calculation
    print("\n3. Testing retry delay calculation:")
    
    delay_1 = error_handler.get_retry_delay(connection_error_info, 1)
    delay_2 = error_handler.get_retry_delay(connection_error_info, 2)
    delay_3 = error_handler.get_retry_delay(connection_error_info, 3)
    
    print(f"   Delay for attempt 1: {delay_1:.2f}s")
    print(f"   Delay for attempt 2: {delay_2:.2f}s")
    print(f"   Delay for attempt 3: {delay_3:.2f}s")
    
    # Delays should increase (exponential backoff)
    assert delay_2 > delay_1
    assert delay_3 > delay_2
    print("   ✓ Exponential backoff working correctly")
    
    print("\n" + "=" * 50)
    print("✓ Retry logic tests completed!")


def test_error_handling_decorator():
    """Test error handling decorator."""
    print("\nTesting Error Handling Decorator...")
    print("=" * 50)
    
    # Test 1: Function that raises an exception
    print("\n1. Testing decorator with exception:")
    
    @with_error_handling(context="test_function", raise_on_error=True)
    def failing_function():
        raise ConnectionError("Test connection error")
    
    try:
        failing_function()
        assert False, "Should have raised an exception"
    except APIError as e:
        print(f"   ✓ Caught APIError: {e.error_info.message}")
        print(f"   User message: {e.error_info.user_message}")
        assert e.error_info.category == ErrorCategory.API_CONNECTION
    
    # Test 2: Function that succeeds
    print("\n2. Testing decorator with successful function:")
    
    @with_error_handling(context="test_function")
    def successful_function():
        return "success"
    
    result = successful_function()
    print(f"   ✓ Function returned: {result}")
    assert result == "success"
    
    # Test 3: Return value on error
    print("\n3. Testing return value on error:")
    
    @with_error_handling(context="test_function", raise_on_error=False, return_on_error="error_occurred")
    def failing_function_no_raise():
        raise ValueError("Test error")
    
    result = failing_function_no_raise()
    print(f"   ✓ Function returned on error: {result}")
    assert result == "error_occurred"
    
    print("\n" + "=" * 50)
    print("✓ Error handling decorator tests completed!")


def test_retry_decorator():
    """Test retry decorator."""
    print("\nTesting Retry Decorator...")
    print("=" * 50)
    
    # Test 1: Function that fails then succeeds
    print("\n1. Testing retry with eventual success:")
    
    call_count = 0
    
    @with_retry(max_attempts=3, base_delay=0.1, context="test_retry")
    def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Temporary failure")
        return "success"
    
    start_time = time.time()
    result = flaky_function()
    end_time = time.time()
    
    print(f"   ✓ Function succeeded after {call_count} attempts")
    print(f"   Result: {result}")
    print(f"   Total time: {end_time - start_time:.2f}s")
    
    assert result == "success"
    assert call_count == 3
    
    # Test 2: Function that always fails
    print("\n2. Testing retry with permanent failure:")
    
    call_count = 0
    
    @with_retry(max_attempts=2, base_delay=0.1, context="test_retry")
    def always_failing_function():
        nonlocal call_count
        call_count += 1
        raise ValueError("Permanent failure")
    
    try:
        always_failing_function()
        assert False, "Should have raised an exception"
    except KnowledgeBaseError as e:
        print(f"   ✓ Function failed after {call_count} attempts")
        print(f"   Final error: {e.error_info.message}")
        assert call_count == 2
    
    print("\n" + "=" * 50)
    print("✓ Retry decorator tests completed!")


def test_user_friendly_messages():
    """Test user-friendly error messages."""
    print("\nTesting User-Friendly Messages...")
    print("=" * 50)
    
    # Test 1: KnowledgeBaseError with user message
    print("\n1. Testing KnowledgeBaseError message:")
    
    error_info = ErrorInfo(
        category=ErrorCategory.API_CONNECTION,
        message="Connection failed",
        user_message="网络连接失败，请检查网络连接后重试"
    )
    kb_error = KnowledgeBaseError(error_info)
    
    user_message = get_user_friendly_message(kb_error)
    print(f"   User message: {user_message}")
    assert user_message == "网络连接失败，请检查网络连接后重试"
    print("   ✓ KnowledgeBaseError user message correct")
    
    # Test 2: Regular exception
    print("\n2. Testing regular exception message:")
    
    regular_error = ConnectionError("Failed to connect")
    user_message = get_user_friendly_message(regular_error)
    print(f"   User message: {user_message}")
    assert "网络连接失败" in user_message
    print("   ✓ Regular exception user message correct")
    
    # Test 3: File not found error
    print("\n3. Testing file error message:")
    
    file_error = FileNotFoundError("test.pdf not found")
    user_message = get_user_friendly_message(file_error)
    print(f"   User message: {user_message}")
    assert "文件未找到" in user_message
    print("   ✓ File error user message correct")
    
    print("\n" + "=" * 50)
    print("✓ User-friendly message tests completed!")


def test_error_scenarios():
    """Test various error scenarios."""
    print("\nTesting Error Scenarios...")
    print("=" * 50)
    
    # Test 1: API timeout scenario
    print("\n1. Testing API timeout scenario:")
    
    @with_error_handling(context="api_call")
    def api_timeout_function():
        raise TimeoutError("Request timeout after 30 seconds")
    
    try:
        api_timeout_function()
    except APIError as e:
        print(f"   ✓ API timeout handled: {e.error_info.user_message}")
        assert e.error_info.category == ErrorCategory.API_TIMEOUT
    
    # Test 2: Database connection scenario
    print("\n2. Testing database connection scenario:")
    
    @with_error_handling(context="database_operation")
    def database_error_function():
        raise Exception("ChromaDB connection failed")
    
    try:
        database_error_function()
    except DatabaseError as e:
        print(f"   ✓ Database error handled: {e.error_info.user_message}")
        assert e.error_info.category == ErrorCategory.DATABASE_CONNECTION
    
    # Test 3: File permission scenario
    print("\n3. Testing file permission scenario:")
    
    @with_error_handling(context="file_operation")
    def file_permission_function():
        raise PermissionError("Permission denied: /protected/file.pdf")
    
    try:
        file_permission_function()
    except FileError as e:
        print(f"   ✓ File permission error handled: {e.error_info.user_message}")
        assert e.error_info.category == ErrorCategory.FILE_PERMISSION
    
    # Test 4: Configuration error scenario
    print("\n4. Testing configuration error scenario:")
    
    @with_error_handling(context="config_loading")
    def config_error_function():
        raise Exception("Required configuration missing: api_key")
    
    try:
        config_error_function()
    except KnowledgeBaseError as e:
        print(f"   ✓ Configuration error handled: {e.error_info.user_message}")
        # Should be classified as config missing
        assert e.error_info.category == ErrorCategory.CONFIG_MISSING
    
    print("\n" + "=" * 50)
    print("✓ Error scenario tests completed!")


def run_all_tests():
    """Run all error handling tests."""
    print("Running All Error Handling Tests")
    print("=" * 70)
    
    try:
        test_error_classification()
        test_retry_logic()
        test_error_handling_decorator()
        test_retry_decorator()
        test_user_friendly_messages()
        test_error_scenarios()
        
        print("\n" + "=" * 70)
        print("🎉 ALL ERROR HANDLING TESTS COMPLETED SUCCESSFULLY! 🎉")
        print("=" * 70)
        
        print("\nSummary:")
        print("- Error classification: ✓ Working")
        print("- Retry logic: ✓ Working")
        print("- Error handling decorator: ✓ Working")
        print("- Retry decorator: ✓ Working")
        print("- User-friendly messages: ✓ Working")
        print("- Error scenarios: ✓ Working")
        
    except Exception as e:
        print(f"\n❌ ERROR HANDLING TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()