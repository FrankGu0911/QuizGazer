import base64
import httpx
import os
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from google.ai.generativelanguage_v1beta.types import Tool as GenAITool
from langchain.tools import Tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain.schema.messages import HumanMessage, SystemMessage
from utils.config_manager import get_model_config

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
示例:
```json
[
  {
    "question_text": "题目的主要文本",
    "code_block": "完整的代码内容",
    "options": ["选项A", "选项B"]
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
        return response.content
    except Exception as e:
        return f"An error occurred while communicating with the VLM: {e}"


def get_answer_from_text(question_text):
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
        proxy = llm_config.get('proxy')
        original_proxy = os.environ.get('https_proxy')
        if proxy:
            os.environ['https_proxy'] = proxy
            
        try:
            # 1. 初始化 ChatGoogleGenerativeAI 模型
            init_kwargs = {
                'model': llm_config.get('model_name', 'gemini-pro'), # 确保有默认模型
                'google_api_key': llm_config['api_key'],
                'timeout': 30,
            }
            chat = ChatGoogleGenerativeAI(**init_kwargs)

            # 2. 定义要使用的原生工具列表
            tools = [GenAITool(google_search={})]

            # 3. 直接调用模型
            messages = [
                SystemMessage(content="You are a helpful assistant. Provide a concise and accurate answer to the user's question. Use the search tool if you need to find the latest information.使用中文回答。注意题目来源于OCR结果，可能会有识别错误，请注意甄别"),
                HumanMessage(content=question_text)
            ]
            response = chat.invoke(messages, tools=tools)

            # 4. 直接从响应中获取内容
            return response.content
        
        except Exception as e:
            return f"An error occurred while communicating with the LLM: {e}"
        finally:
            # Restore original proxy setting after the call
            if proxy:
                if original_proxy:
                    os.environ['https_proxy'] = original_proxy
                elif 'https_proxy' in os.environ:
                    del os.environ['https_proxy']

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
            response = chat.invoke(
                [
                    SystemMessage(content="You are a helpful assistant. Provide a concise and accurate answer to the user's question.使用中文回答。"),
                    HumanMessage(content=question_text),
                ]
            )
            return response.content
        except Exception as e:
            return f"An error occurred while communicating with the LLM: {e}"