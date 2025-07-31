import base64
import httpx
import os,time,logging
import json
from google.genai import Client, types
from langchain_openai import ChatOpenAI
from langchain.schema.messages import HumanMessage, SystemMessage
from utils.config_manager import get_model_config

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


def get_answer_from_text(question_text, force_search=False):
    """
    Sends a question text to the configured LLM to get an answer.

    Args:
        question_text (str): The question to be answered.

    Returns:
        str: The answer from the LLM, or an error message.
    """
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