import base64
import httpx
import os,time,logging
import json
from google.genai import Client, types
from langchain_openai import ChatOpenAI
from langchain.schema.messages import HumanMessage, SystemMessage
from utils.config_manager import get_model_config

# Import knowledge base components
try:
    from core.knowledge_base.rag_pipeline import RAGPipeline
    from core.knowledge_base.manager import KnowledgeBaseManager
    from core.knowledge_base.models import ChromaDBConfig
    from utils.config_manager import get_knowledge_base_config, get_chromadb_config
    KNOWLEDGE_BASE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Knowledge base components not available: {e}")
    RAGPipeline = None
    KnowledgeBaseManager = None
    ChromaDBConfig = None
    get_knowledge_base_config = None
    get_chromadb_config = None
    KNOWLEDGE_BASE_AVAILABLE = False

# Global RAG pipeline instance
_rag_pipeline = None
_knowledge_base_manager = None

def initialize_knowledge_base():
    """Initialize the knowledge base and RAG pipeline."""
    global _rag_pipeline, _knowledge_base_manager
    
    if not KNOWLEDGE_BASE_AVAILABLE:
        logging.warning("Knowledge base components not available, skipping initialization")
        return False
    
    try:
        # Load configuration
        kb_config = get_knowledge_base_config() if get_knowledge_base_config else {}
        chromadb_config_dict = get_chromadb_config() if get_chromadb_config else {}
        
        # Note: We initialize the knowledge base components even if disabled in config
        # This allows users to enable it through the UI later
        # The enabled state will be handled by the RAG pipeline itself
        
        # Create ChromaDB configuration
        chromadb_config = ChromaDBConfig(
            connection_type=chromadb_config_dict.get('connection_type', 'local'),
            host=chromadb_config_dict.get('host'),
            port=chromadb_config_dict.get('port'),
            path=chromadb_config_dict.get('path', './data/chromadb'),
            auth_credentials=chromadb_config_dict.get('auth_credentials'),
            ssl_enabled=chromadb_config_dict.get('ssl_enabled', False)
        )
        
        # Initialize knowledge base manager
        storage_path = kb_config.get('storage_path', './data/knowledge_base')
        _knowledge_base_manager = KnowledgeBaseManager(
            storage_path=storage_path,
            chromadb_config=chromadb_config
        )
        
        # Initialize embedding service
        from core.knowledge_base.embedding_service import initialize_embedding_service
        embedding_initialized = initialize_embedding_service()
        if not embedding_initialized:
            logging.warning("Embedding service initialization failed, but continuing...")
        
        # Initialize RAG pipeline with LLM service integration
        _rag_pipeline = RAGPipeline(
            knowledge_base_manager=_knowledge_base_manager,
            llm_service=_get_llm_response_for_rag
        )
        
        logging.info("Knowledge base and RAG pipeline initialized successfully")
        return True
        
    except Exception as e:
        logging.error(f"Failed to initialize knowledge base: {e}")
        return False

def get_rag_pipeline():
    """Get the global RAG pipeline instance."""
    return _rag_pipeline

def get_knowledge_base_manager():
    """Get the global knowledge base manager instance."""
    return _knowledge_base_manager

def is_knowledge_base_available():
    """Check if knowledge base is available and initialized."""
    return KNOWLEDGE_BASE_AVAILABLE and _rag_pipeline is not None

def _get_llm_response_for_rag(prompt: str) -> str:
    """
    Internal function to get LLM response for RAG pipeline.
    This wraps the existing get_answer_from_text function.
    
    IMPORTANT: use_knowledge_base=False to prevent recursive calls!
    """
    try:
        print("🔄 [AI服务] RAG管道调用LLM服务（禁用知识库以防递归）")
        return get_answer_from_text(prompt, force_search=False, use_knowledge_base=False)
    except Exception as e:
        print(f"❌ [AI服务] RAG的LLM调用失败: {e}")
        logging.error(f"Error getting LLM response for RAG: {e}")
        return f"抱歉，处理您的问题时出现错误：{str(e)}"

def _extract_longest_json(text):
    """
    从文本中提取最长的JSON结构，优先匹配[]数组，然后匹配{}对象

    Args:
        text (str): 包含JSON的文本

    Returns:
        str: 提取的JSON字符串，如果没有找到则返回None
    """
    def find_matching_bracket(text, start_pos, open_char, close_char):
        """找到匹配的括号位置"""
        count = 1
        pos = start_pos + 1
        while pos < len(text) and count > 0:
            if text[pos] == open_char:
                count += 1
            elif text[pos] == close_char:
                count -= 1
            pos += 1
        return pos - 1 if count == 0 else -1

    # 优先查找最长的[]数组
    longest_array = ""
    for i, char in enumerate(text):
        if char == '[':
            end_pos = find_matching_bracket(text, i, '[', ']')
            if end_pos != -1:
                candidate = text[i:end_pos + 1]
                if len(candidate) > len(longest_array):
                    longest_array = candidate

    if longest_array:
        return longest_array

    # 如果没有找到数组，查找最长的{}对象
    longest_object = ""
    for i, char in enumerate(text):
        if char == '{':
            end_pos = find_matching_bracket(text, i, '{', '}')
            if end_pos != -1:
                candidate = text[i:end_pos + 1]
                if len(candidate) > len(longest_object):
                    longest_object = candidate

    return longest_object if longest_object else None

def get_direct_answer_from_image(image_bytes, force_search=False):
    """
    直接从图像获取答案，适用于包含图形、函数图、几何图等视觉元素的题目
    使用多模态模型一步到位解答问题

    Args:
        image_bytes (bytes): The image data in bytes.
        force_search (bool): Whether to force the model to use search tools.

    Returns:
        str: The answer from the multimodal model, or an error message.
    """
    llm_config = get_model_config('llm')
    if not llm_config:
        return "Error: LLM configuration is missing or invalid."

    provider = llm_config.get('llm_provider', 'gemini')

    if provider == 'gemini':
        try:
            client_options = {
                "api_key": llm_config.get('google_api_key') or llm_config.get('api_key')
            }
            # 注意：对于原生 Google GenAI API，不需要设置 http_options
            client_options["http_options"] = {'base_url': llm_config.get('base_url',"https://generativelanguage.googleapis.com/v1beta/openai/")}

            genai_client = Client(**client_options)

            model_name = llm_config.get('model_name', 'gemini-2.5-flash')
            cur_time = time.strftime("%Y-%m-%d_%H-%M-%S")

            system_instruction = f"""你是一个专业的答题助手。现在时间是{cur_time}。请直接分析图片中的问题并给出答案。

对于选择题：
1. 首先直接给出答案：**答案：A** 或 **答案：A、C**（多选题）
2. 然后简明扼要说明理由，不要长篇大论

对于主观题：
直接给出准确的中文答案和解释

特别注意：
- 仔细观察图片中的所有视觉元素，包括图形、图表、函数图像、几何图形等
- 如果题目涉及图形分析，请基于图片中的视觉信息进行解答
- 必须使用中文回答
- 选择题必须明确指出选项字母
- 回答要准确、简洁"""

            if force_search:
                system_instruction += " 必须使用搜索工具寻找答案"

            # 检测图片格式
            def detect_image_mime_type(image_data):
                """检测图片的MIME类型"""
                if image_data.startswith(b'\x89PNG'):
                    return 'image/png'
                elif image_data.startswith(b'\xff\xd8\xff'):
                    return 'image/jpeg'
                elif image_data.startswith(b'GIF'):
                    return 'image/gif'
                elif image_data.startswith(b'RIFF') and b'WEBP' in image_data[:12]:
                    return 'image/webp'
                else:
                    return 'image/png'  # 默认使用PNG

            mime_type = detect_image_mime_type(image_bytes)

            # 使用正确的 Google GenAI API 格式构建内容
            content = [
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type,
                ),
                "请分析这张图片中的问题并给出答案。如果图片包含图形、图表或其他视觉元素，请基于这些视觉信息进行分析。"
            ]

            # 构建配置
            config_kwargs = {
                "system_instruction": system_instruction,
            }

            # 只有在需要搜索时才添加工具
            if force_search:
                config_kwargs["tools"] = [
                    types.Tool(
                        google_search=types.GoogleSearch()
                    )
                ]

            response = genai_client.models.generate_content(
                model=model_name,
                contents=content,
                config=types.GenerateContentConfig(**config_kwargs),
            )

            print(f"Response from Multimodal LLM: {response}")
            return response.text

        except Exception as e:
            return f"An error occurred while communicating with the Gemini API: {e}"

    else:
        # 对于非Gemini提供商，回退到两步走方案
        return "Error: Direct image answering is only supported with Gemini provider. Please use the two-step approach (extract question first, then answer)."

def get_question_from_image(image_bytes):
    """
    Sends an image to the configured VLM to extract a question.

    Args:
        image_bytes (bytes): The image data in bytes.

    Returns:
        str: The extracted question text, or an error message.
    """
    vlm_config = get_model_config('vlm')
    if not vlm_config:
        return "Error: VLM configuration is missing or invalid."

    # Encode the image in base64
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    # Set up httpx client with timeout and proxy if available
    client_kwargs = {"timeout": 30}
    if vlm_config.get('proxy'):
        client_kwargs['proxies'] = vlm_config['proxy']
    
    http_client = httpx.Client(**client_kwargs)

    chat = ChatOpenAI(
        model=vlm_config['model_name'],
        openai_api_key=vlm_config['api_key'],
        base_url=vlm_config['base_url'],
        http_client=http_client
    )

    try:
        response = chat.invoke(
            [
                SystemMessage(
                    content='''
以JSON数组格式提取图中所有问题。

每个对象必须包含`question_text`(字符串), `code_block`(字符串或`null`), `options`(字符串数组`[]`)以及`question_type`四个键。
`question_type`的判断规则如下：
- 如果问题文本包含“多选”等关键词，或明确提示可选多个答案，则为 "多选题"。
- 如果`options`数组为空，则为 "主观题"。
- 其他所有有选项的情况，默认为 "单选题"。

对于选项提取的重要规则：
1. 必须同时包含选项标识（如A、B、C、D）和选项内容
2. 格式应为："A. 选项内容" 或 "A、选项内容" 或 "A：选项内容" 等
3. 即使原题中选项标识和内容是分离的，也必须将它们合并为一个完整选项


示例:
```json
[
  {
    "question_text": "题目的主要文本",
    "code_block": "完整的代码内容",
    "options": ["A. 第一个选项内容", "B. 第二个选项内容", "C. 第三个选项内容", "D. 第四个选项内容"],
    "question_type": "单选题"
  }
]
````

你的回答必须只包含JSON数组，无任何额外文本。若图中无问题，则返回空数组`[]`。
                    '''
                ),
                HumanMessage(
                    content=[
                        {"type": "text", "text": "Extract the question from this image."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            },
                        },
                    ]
                ),
            ]
        )
        print(f"Response from VLM: {response}")

        # 验证返回的内容是否为有效的JSON
        response_content = response.content.strip()

        # 先尝试提取最长的JSON结构
        json_content = _extract_longest_json(response_content)
        if not json_content:
            return f"Error: No valid JSON structure found in VLM response: {response_content}"

        try:
            # 尝试解析提取的JSON
            parsed_json = json.loads(json_content)

            # 如果是空数组，直接返回
            if isinstance(parsed_json, list) and len(parsed_json) == 0:
                return "[]"

            # 如果解析成功且不为空，返回提取的JSON内容
            return json_content

        except json.JSONDecodeError:
            # 如果不是有效的JSON，返回错误信息
            return f"Error: VLM returned invalid JSON format: {response_content}"

    except Exception as e:
        return f"An error occurred while communicating with the VLM: {e}"


def get_answer_from_text(question_text, force_search=False, use_knowledge_base=True):
    """
    Sends a question text to the configured LLM to get an answer.
    Optionally uses knowledge base for enhanced responses.

    Args:
        question_text (str): The question to be answered.
        force_search (bool): Whether to force search tools usage.
        use_knowledge_base (bool): Whether to use knowledge base for enhanced answers.

    Returns:
        str: The answer from the LLM, or an error message.
    """
    # Try to use knowledge base first if available and enabled
    print(f"🤖 [AI服务] get_answer_from_text 调用，use_knowledge_base={use_knowledge_base}")
    if use_knowledge_base and is_knowledge_base_available():
        print("🚀 [AI服务] 知识库可用，尝试使用RAG增强响应")
        try:
            rag_pipeline = get_rag_pipeline()
            if rag_pipeline and rag_pipeline.should_use_knowledge_base():
                print("✅ [AI服务] RAG管道可用且应该使用知识库")
                print("🔍 [AI服务] 调用RAG管道处理查询...")
                logging.info("Using knowledge base for enhanced response")
                enhanced_response = rag_pipeline.process_query_with_knowledge(question_text)
                if enhanced_response and not enhanced_response.startswith("抱歉"):
                    print("✅ [AI服务] RAG增强响应成功，返回结果")
                    print(f"📝 [AI服务] 响应长度: {len(enhanced_response)} 字符")
                    return enhanced_response
                else:
                    print("⚠️ [AI服务] RAG响应不满意，回退到标准LLM")
                    logging.info("Knowledge base response not satisfactory, falling back to standard LLM")
            else:
                print("❌ [AI服务] RAG管道不可用或不应使用知识库")
        except Exception as e:
            print(f"❌ [AI服务] 使用知识库时出错: {e}")
            logging.error(f"Error using knowledge base: {e}")
            logging.info("Falling back to standard LLM response")
    else:
        if not use_knowledge_base:
            print("🔒 [AI服务] 知识库使用被禁用")
        else:
            print("❌ [AI服务] 知识库不可用")
    
    # Standard LLM processing (original implementation)
    llm_config = get_model_config('llm')
    if not llm_config:
        return "Error: LLM configuration is missing or invalid."

    provider = llm_config.get('llm_provider', 'gemini')
    chat = None

    if provider == 'gemini':
        try:
            client_options = {
                "api_key": llm_config.get('google_api_key') or llm_config.get('api_key')
            }
            client_options["http_options"] = {'base_url': llm_config.get('base_url',"https://generativelanguage.googleapis.com/v1beta/openai/")}

            genai_client = Client(**client_options)
            
            model_name = llm_config.get('model_name', 'gemini-2.5-flash')
            # model = genai.GenerativeModel(model_name)
            cur_time = time.strftime("%Y-%m-%d_%H-%M-%S")
            system_instruction = f"""你是一个专业的答题助手。现在时间是{cur_time}。请按照以下格式回答问题：
            对于选择题：
            1. 首先直接给出答案：**答案：A** 或 **答案：A、C**（多选题）
            2. 然后简明扼要说明理由，不要长篇大论

            对于主观题：
            直接给出准确的中文答案和解释

            要求：
            - 必须使用中文回答
            - 选择题必须明确指出选项字母
            - 回答要准确、简洁
            - 注意题目可能来自OCR，存在识别错误，请合理判断"""
            if force_search:
                system_instruction += " 必须使用搜索工具寻找答案"
            content = question_text
            response = genai_client.models.generate_content(
                model=model_name,
                contents=content,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=[
                        types.Tool(
                            google_search=types.GoogleSearch()
                        )
                    ],
                    
                ),
            )
            
            print(f"Response from LLM: {response}")
            return response.text
        except Exception as e:
            return f"An error occurred while communicating with the Gemini API: {e}"

    else:
        # For other providers, use the existing ChatOpenAI setup.
        # Set up httpx client with timeout and proxy if available
        client_kwargs = {"timeout": 30}
        if llm_config.get('proxy'):
            client_kwargs['proxies'] = llm_config['proxy']
            
        http_client = httpx.Client(**client_kwargs)

        chat = ChatOpenAI(
            model=llm_config['model_name'],
            openai_api_key=llm_config['api_key'],
            base_url=llm_config['base_url'],
            http_client=http_client
        )
        try:
            system_prompt = "You are a helpful assistant. 你是一个中文助手。无论用户提问使用什么语言，你都必须始终使用中文回答所有问题。对于选择题（单选或多选），请先分析问题，然后明确指出正确答案的选项（如'答案是B'或'答案是A和C'）。之后再提供详细解释。Provide a concise and accurate answer to the user's question. 即使题目全是英文，你也必须用中文回答。"
            if force_search:
                logging.warning("OpenAI compatibility mode: force_search is not usable")
                # system_prompt += " 必须使用搜索工具寻找答案"
            response = chat.invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=question_text),
                ]
            )
            print(f"Response from LLM: {response}")
            return response.content
        except Exception as e:
            return f"An error occurred while communicating with the LLM: {e}"

# Knowledge Base Management Functions

def get_knowledge_base_status():
    """
    Get the current status of the knowledge base.
    
    Returns:
        dict: Knowledge base status information
    """
    if not is_knowledge_base_available():
        return {
            "available": False,
            "enabled": False,
            "error": "Knowledge base not initialized or not available"
        }
    
    try:
        rag_pipeline = get_rag_pipeline()
        return rag_pipeline.get_knowledge_base_status()
    except Exception as e:
        return {
            "available": False,
            "enabled": False,
            "error": str(e)
        }

def set_knowledge_base_collections(collection_ids):
    """
    Set the collections to use for knowledge base queries.
    
    Args:
        collection_ids (list): List of collection IDs to use
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not is_knowledge_base_available():
        return False
    
    try:
        rag_pipeline = get_rag_pipeline()
        rag_pipeline.set_selected_collections(collection_ids)
        return True
    except Exception as e:
        logging.error(f"Error setting knowledge base collections: {e}")
        return False

def get_knowledge_base_collections():
    """
    Get available knowledge base collections.
    
    Returns:
        list: List of available collections
    """
    if not is_knowledge_base_available():
        return []
    
    try:
        kb_manager = get_knowledge_base_manager()
        return kb_manager.list_collections()
    except Exception as e:
        logging.error(f"Error getting knowledge base collections: {e}")
        return []

def enable_knowledge_base():
    """
    Enable knowledge base functionality.
    
    Returns:
        bool: True if successful, False otherwise
    """
    print("🚀 [AI服务] 启用知识库功能...")
    
    if not is_knowledge_base_available():
        print("❌ [AI服务] 知识库不可用，无法启用")
        return False
    
    try:
        print("🔧 [AI服务] 获取RAG管道实例...")
        rag_pipeline = get_rag_pipeline()
        
        print("⚡ [AI服务] 调用RAG管道的启用知识库方法...")
        rag_pipeline.enable_knowledge_base()
        
        print("✅ [AI服务] 知识库功能启用成功")
        return True
    except Exception as e:
        print(f"❌ [AI服务] 启用知识库时发生错误: {e}")
        import traceback
        print(f"🔍 [AI服务] 错误详情: {traceback.format_exc()}")
        logging.error(f"Error enabling knowledge base: {e}")
        return False

def disable_knowledge_base():
    """
    Disable knowledge base functionality.
    
    Returns:
        bool: True if successful, False otherwise
    """
    print("🛑 [AI服务] 禁用知识库功能...")
    
    if not is_knowledge_base_available():
        print("❌ [AI服务] 知识库不可用，无法禁用")
        return False
    
    try:
        print("🔧 [AI服务] 获取RAG管道实例...")
        rag_pipeline = get_rag_pipeline()
        
        print("⚡ [AI服务] 调用RAG管道的禁用知识库方法...")
        rag_pipeline.disable_knowledge_base()
        
        print("✅ [AI服务] 知识库功能禁用成功")
        return True
    except Exception as e:
        print(f"❌ [AI服务] 禁用知识库时发生错误: {e}")
        import traceback
        print(f"🔍 [AI服务] 错误详情: {traceback.format_exc()}")
        logging.error(f"Error disabling knowledge base: {e}")
        return False

def search_knowledge_preview(query, collections=None, top_k=3):
    """
    Search knowledge base and return preview results.
    
    Args:
        query (str): Search query
        collections (list): Collections to search (None for all selected)
        top_k (int): Maximum number of results
        
    Returns:
        list: List of knowledge fragment previews
    """
    if not is_knowledge_base_available():
        return []
    
    try:
        rag_pipeline = get_rag_pipeline()
        return rag_pipeline.search_knowledge_preview(query, collections, top_k)
    except Exception as e:
        logging.error(f"Error searching knowledge base: {e}")
        return []

def get_knowledge_base_statistics():
    """
    Get knowledge base statistics.
    
    Returns:
        dict: Knowledge base statistics
    """
    if not is_knowledge_base_available():
        return {"error": "Knowledge base not available"}
    
    try:
        kb_manager = get_knowledge_base_manager()
        return kb_manager.get_knowledge_base_stats()
    except Exception as e:
        logging.error(f"Error getting knowledge base statistics: {e}")
        return {"error": str(e)}

# Initialize knowledge base on module import
try:
    initialize_knowledge_base()
except Exception as e:
    logging.error(f"Failed to initialize knowledge base on module import: {e}")