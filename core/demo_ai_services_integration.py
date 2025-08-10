"""
Demo script showing AI Services integration with Knowledge Base.
"""

import sys
import os

# Add the parent directory to the path to access utils
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import AI services
from core import ai_services


def demo_ai_services_integration():
    """Demonstrate AI services integration with knowledge base."""
    print("AI Services Integration with Knowledge Base Demo")
    print("=" * 60)
    
    # Check knowledge base availability
    print("\n1. Knowledge Base Status:")
    print("-" * 30)
    
    is_available = ai_services.is_knowledge_base_available()
    print(f"Knowledge Base Available: {is_available}")
    
    if is_available:
        status = ai_services.get_knowledge_base_status()
        print(f"Enabled: {status.get('enabled', False)}")
        print(f"Total Collections: {status.get('total_collections', 0)}")
        print(f"Total Documents: {status.get('total_documents', 0)}")
        print(f"Can Process Queries: {status.get('can_process_queries', False)}")
    else:
        print("Knowledge base is not available or not initialized.")
    
    # Demo questions
    print("\n2. Enhanced Question Answering Demo:")
    print("-" * 30)
    
    demo_questions = [
        "什么是人工智能？请详细解释。",
        "机器学习和深度学习有什么区别？",
        "请介绍一下自然语言处理的应用。"
    ]
    
    for i, question in enumerate(demo_questions, 1):
        print(f"\n问题 {i}: {question}")
        print("回答:")
        
        try:
            # Get enhanced answer with knowledge base
            answer = ai_services.get_answer_from_text(
                question, 
                force_search=False, 
                use_knowledge_base=True
            )
            
            # Display answer (truncated for demo)
            if len(answer) > 300:
                print(f"{answer[:300]}...")
                print(f"[回答已截断，完整长度: {len(answer)} 字符]")
            else:
                print(answer)
                
        except Exception as e:
            print(f"错误: {e}")
        
        print("-" * 50)
    
    # Demo knowledge base management
    print("\n3. Knowledge Base Management Demo:")
    print("-" * 30)
    
    # Get collections
    collections = ai_services.get_knowledge_base_collections()
    print(f"Available Collections: {len(collections)}")
    
    if collections:
        for collection in collections[:3]:  # Show first 3
            print(f"- {collection.name}: {collection.document_count} documents")
    else:
        print("No collections found. You can add documents to create collections.")
    
    # Get statistics
    stats = ai_services.get_knowledge_base_statistics()
    if 'error' not in stats:
        print(f"\nKnowledge Base Statistics:")
        print(f"- Total Collections: {stats.get('total_collections', 0)}")
        print(f"- Total Documents: {stats.get('total_documents', 0)}")
        print(f"- Total Chunks: {stats.get('total_chunks', 0)}")
        print(f"- Storage Path: {stats.get('storage_path', 'Unknown')}")
    else:
        print(f"Statistics Error: {stats.get('error')}")
    
    # Demo search preview
    print("\n4. Knowledge Search Preview Demo:")
    print("-" * 30)
    
    search_query = "人工智能的定义和应用"
    print(f"Search Query: {search_query}")
    
    preview_results = ai_services.search_knowledge_preview(
        query=search_query,
        collections=None,
        top_k=3
    )
    
    print(f"Found {len(preview_results)} relevant fragments:")
    for i, result in enumerate(preview_results, 1):
        print(f"{i}. Source: {result.get('source_document', 'Unknown')}")
        print(f"   Relevance: {result.get('relevance_score', 0):.3f}")
        print(f"   Preview: {result.get('content_preview', 'No preview')[:100]}...")
        print()
    
    if not preview_results:
        print("No relevant knowledge fragments found.")
        print("This is expected if no documents have been uploaded to the knowledge base.")
    
    print("\n" + "=" * 60)
    print("✓ AI Services Integration Demo Completed!")
    print("=" * 60)
    
    # Instructions for users
    print("\nNext Steps:")
    print("1. To use the knowledge base, upload documents through the UI")
    print("2. Create collections to organize your documents")
    print("3. Enable knowledge base in settings if disabled")
    print("4. Ask questions to get enhanced answers with your knowledge")


def demo_comparison():
    """Demo comparing responses with and without knowledge base."""
    print("\nComparison Demo: With vs Without Knowledge Base")
    print("=" * 60)
    
    test_question = "什么是深度学习？它有哪些主要特点？"
    print(f"Test Question: {test_question}")
    
    print("\n1. Response WITH Knowledge Base:")
    print("-" * 40)
    try:
        response_with_kb = ai_services.get_answer_from_text(
            test_question, 
            use_knowledge_base=True
        )
        print(response_with_kb[:400] + "..." if len(response_with_kb) > 400 else response_with_kb)
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n2. Response WITHOUT Knowledge Base:")
    print("-" * 40)
    try:
        response_without_kb = ai_services.get_answer_from_text(
            test_question, 
            use_knowledge_base=False
        )
        print(response_without_kb[:400] + "..." if len(response_without_kb) > 400 else response_without_kb)
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 60)
    print("✓ Comparison Demo Completed!")


def demo_error_scenarios():
    """Demo error handling scenarios."""
    print("\nError Handling Demo")
    print("=" * 60)
    
    print("\n1. Testing with empty question:")
    try:
        response = ai_services.get_answer_from_text("", use_knowledge_base=True)
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error handled: {e}")
    
    print("\n2. Testing knowledge base toggle:")
    
    # Disable knowledge base
    disable_result = ai_services.disable_knowledge_base()
    print(f"Disable KB result: {disable_result}")
    
    # Test with disabled KB
    response_disabled = ai_services.get_answer_from_text(
        "什么是AI？", 
        use_knowledge_base=True
    )
    print(f"Response with disabled KB: {response_disabled[:100]}...")
    
    # Re-enable knowledge base
    enable_result = ai_services.enable_knowledge_base()
    print(f"Enable KB result: {enable_result}")
    
    print("\n" + "=" * 60)
    print("✓ Error Handling Demo Completed!")


if __name__ == "__main__":
    try:
        demo_ai_services_integration()
        demo_comparison()
        demo_error_scenarios()
        
        print("\n🎉 All demos completed successfully! 🎉")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()