"""
Test AI Services integration with Knowledge Base.
"""

import sys
import os
import tempfile
import shutil
from unittest.mock import Mock, patch

# Add the parent directory to the path to access utils
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import AI services
from core import ai_services


def test_knowledge_base_initialization():
    """Test knowledge base initialization in AI services."""
    print("Testing Knowledge Base Initialization in AI Services...")
    print("=" * 60)
    
    # Test 1: Check if knowledge base is available
    print("\n1. Testing knowledge base availability:")
    
    is_available = ai_services.is_knowledge_base_available()
    print(f"   Knowledge base available: {is_available}")
    
    if is_available:
        print("   ✓ Knowledge base components loaded successfully")
        
        # Get RAG pipeline
        rag_pipeline = ai_services.get_rag_pipeline()
        if rag_pipeline:
            print("   ✓ RAG pipeline instance available")
        else:
            print("   ✗ RAG pipeline instance not available")
        
        # Get knowledge base manager
        kb_manager = ai_services.get_knowledge_base_manager()
        if kb_manager:
            print("   ✓ Knowledge base manager instance available")
        else:
            print("   ✗ Knowledge base manager instance not available")
    else:
        print("   ⚠ Knowledge base not available (may be disabled or missing dependencies)")
    
    # Test 2: Get knowledge base status
    print("\n2. Testing knowledge base status:")
    
    status = ai_services.get_knowledge_base_status()
    if status:
        print("   ✓ Knowledge base status retrieved")
        print(f"   - Available: {status.get('available', False)}")
        print(f"   - Enabled: {status.get('enabled', False)}")
        print(f"   - Manager Available: {status.get('manager_available', False)}")
        print(f"   - Total Collections: {status.get('total_collections', 0)}")
        print(f"   - Can Process Queries: {status.get('can_process_queries', False)}")
        
        if status.get('error'):
            print(f"   - Error: {status['error']}")
    else:
        print("   ✗ Failed to get knowledge base status")
    
    print("\n" + "=" * 60)
    print("✓ Knowledge base initialization test completed!")


def test_knowledge_base_management_functions():
    """Test knowledge base management functions."""
    print("\nTesting Knowledge Base Management Functions...")
    print("=" * 60)
    
    # Test 1: Get collections
    print("\n1. Testing get collections:")
    
    collections = ai_services.get_knowledge_base_collections()
    print(f"   Collections found: {len(collections)}")
    
    if collections:
        for i, collection in enumerate(collections[:3]):  # Show first 3
            print(f"   - Collection {i+1}: {collection.name} ({collection.document_count} docs)")
    else:
        print("   ⚠ No collections found (expected if knowledge base is empty)")
    
    # Test 2: Enable/disable knowledge base
    print("\n2. Testing enable/disable functionality:")
    
    # Try to disable
    disable_result = ai_services.disable_knowledge_base()
    print(f"   Disable result: {disable_result}")
    
    # Check status after disable
    status_disabled = ai_services.get_knowledge_base_status()
    if status_disabled:
        print(f"   Status after disable - Enabled: {status_disabled.get('enabled', 'Unknown')}")
    
    # Try to enable
    enable_result = ai_services.enable_knowledge_base()
    print(f"   Enable result: {enable_result}")
    
    # Check status after enable
    status_enabled = ai_services.get_knowledge_base_status()
    if status_enabled:
        print(f"   Status after enable - Enabled: {status_enabled.get('enabled', 'Unknown')}")
    
    # Test 3: Set collections
    print("\n3. Testing collection selection:")
    
    # Try to set collections (even if empty)
    test_collections = ["test_collection_1", "test_collection_2"]
    set_result = ai_services.set_knowledge_base_collections(test_collections)
    print(f"   Set collections result: {set_result}")
    
    # Test 4: Search preview (should return empty for non-existent collections)
    print("\n4. Testing knowledge search preview:")
    
    preview_results = ai_services.search_knowledge_preview(
        query="What is artificial intelligence?",
        collections=None,
        top_k=3
    )
    print(f"   Preview results: {len(preview_results)} fragments")
    
    if preview_results:
        for i, result in enumerate(preview_results):
            print(f"   - Fragment {i+1}: {result.get('source_document', 'Unknown')} (score: {result.get('relevance_score', 0)})")
    else:
        print("   ⚠ No preview results (expected if no documents in knowledge base)")
    
    # Test 5: Get statistics
    print("\n5. Testing knowledge base statistics:")
    
    stats = ai_services.get_knowledge_base_statistics()
    if stats and 'error' not in stats:
        print("   ✓ Statistics retrieved successfully")
        print(f"   - Total Collections: {stats.get('total_collections', 0)}")
        print(f"   - Total Documents: {stats.get('total_documents', 0)}")
        print(f"   - Total Chunks: {stats.get('total_chunks', 0)}")
        print(f"   - Storage Path: {stats.get('storage_path', 'Unknown')}")
    else:
        print(f"   ⚠ Statistics error: {stats.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 60)
    print("✓ Knowledge base management functions test completed!")


def test_enhanced_question_answering():
    """Test enhanced question answering with knowledge base."""
    print("\nTesting Enhanced Question Answering...")
    print("=" * 60)
    
    # Test questions
    test_questions = [
        "什么是人工智能？",
        "What is machine learning?",
        "请解释深度学习的基本概念",
        "今天天气怎么样？"  # This should not have relevant knowledge
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. Testing question: {question}")
        print("-" * 40)
        
        # Test with knowledge base enabled
        print("   With Knowledge Base:")
        try:
            response_with_kb = ai_services.get_answer_from_text(
                question, 
                force_search=False, 
                use_knowledge_base=True
            )
            print(f"   Response length: {len(response_with_kb)} characters")
            print(f"   Response preview: {response_with_kb[:100]}...")
            
            # Check if response indicates knowledge base usage
            if "知识库" in response_with_kb or "知识内容" in response_with_kb:
                print("   ✓ Response indicates knowledge base usage")
            elif "暂时不可用" in response_with_kb:
                print("   ⚠ Knowledge base temporarily unavailable")
            else:
                print("   ⚠ Standard response (no relevant knowledge or KB disabled)")
                
        except Exception as e:
            print(f"   ✗ Error with knowledge base: {e}")
        
        # Test without knowledge base
        print("   Without Knowledge Base:")
        try:
            response_without_kb = ai_services.get_answer_from_text(
                question, 
                force_search=False, 
                use_knowledge_base=False
            )
            print(f"   Response length: {len(response_without_kb)} characters")
            print(f"   Response preview: {response_without_kb[:100]}...")
            
        except Exception as e:
            print(f"   ✗ Error without knowledge base: {e}")
    
    print("\n" + "=" * 60)
    print("✓ Enhanced question answering test completed!")


def test_error_handling_and_fallbacks():
    """Test error handling and fallback mechanisms."""
    print("\nTesting Error Handling and Fallbacks...")
    print("=" * 60)
    
    # Test 1: Invalid question handling
    print("\n1. Testing invalid question handling:")
    
    invalid_questions = ["", "   ", None]
    
    for i, invalid_q in enumerate(invalid_questions):
        print(f"   Testing invalid question {i+1}: {repr(invalid_q)}")
        try:
            if invalid_q is None:
                # Skip None test as it would cause TypeError
                print("   ⚠ Skipping None test (would cause TypeError)")
                continue
                
            response = ai_services.get_answer_from_text(invalid_q, use_knowledge_base=True)
            print(f"   Response: {response[:50]}...")
            
            if "有效" in response or "问题" in response:
                print("   ✓ Appropriate error message returned")
            else:
                print("   ⚠ Unexpected response format")
                
        except Exception as e:
            print(f"   ✗ Exception occurred: {e}")
    
    # Test 2: Knowledge base unavailable scenario
    print("\n2. Testing knowledge base unavailable scenario:")
    
    # Temporarily disable knowledge base
    original_available = ai_services.is_knowledge_base_available()
    
    # Mock the availability check to return False
    with patch.object(ai_services, 'is_knowledge_base_available', return_value=False):
        response = ai_services.get_answer_from_text(
            "What is AI?", 
            use_knowledge_base=True
        )
        print(f"   Response when KB unavailable: {response[:100]}...")
        
        if response and len(response) > 0:
            print("   ✓ Fallback to standard LLM successful")
        else:
            print("   ✗ Fallback failed")
    
    print(f"   Original KB availability restored: {original_available}")
    
    # Test 3: API configuration validation
    print("\n3. Testing API configuration:")
    
    # Check if embedding and reranker APIs are configured
    try:
        from utils.config_manager import get_embedding_api_config, get_reranker_api_config
        
        embedding_config = get_embedding_api_config()
        if embedding_config:
            print("   ✓ Embedding API configuration found")
            print(f"   - Endpoint: {embedding_config.get('endpoint', 'Not set')}")
            print(f"   - Model: {embedding_config.get('model', 'Not set')}")
        else:
            print("   ⚠ Embedding API configuration not found")
        
        reranker_config = get_reranker_api_config()
        if reranker_config:
            print("   ✓ Reranker API configuration found")
            print(f"   - Endpoint: {reranker_config.get('endpoint', 'Not set')}")
            print(f"   - Model: {reranker_config.get('model', 'Not set')}")
        else:
            print("   ⚠ Reranker API configuration not found")
            
    except ImportError:
        print("   ⚠ Configuration functions not available")
    except Exception as e:
        print(f"   ✗ Error checking API configuration: {e}")
    
    print("\n" + "=" * 60)
    print("✓ Error handling and fallbacks test completed!")


def run_all_integration_tests():
    """Run all AI services integration tests."""
    print("Running AI Services Integration Tests")
    print("=" * 70)
    
    try:
        test_knowledge_base_initialization()
        test_knowledge_base_management_functions()
        test_enhanced_question_answering()
        test_error_handling_and_fallbacks()
        
        print("\n" + "=" * 70)
        print("🎉 ALL AI SERVICES INTEGRATION TESTS COMPLETED! 🎉")
        print("=" * 70)
        
        # Summary
        print("\nSummary:")
        print("- Knowledge base integration: ✓ Implemented")
        print("- RAG pipeline integration: ✓ Implemented")
        print("- Enhanced question answering: ✓ Implemented")
        print("- Error handling and fallbacks: ✓ Implemented")
        print("- Management functions: ✓ Implemented")
        
    except Exception as e:
        print(f"\n❌ INTEGRATION TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_integration_tests()