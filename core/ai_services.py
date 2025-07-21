import base64
import httpx
import os,time,logging
from google.genai import Client,types
from langchain_openai import ChatOpenAI
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
            system_instruction = f"You are a helpful assistant. Provide a concise and accurate answer to the user's question. Use the search tool if you need to find the latest information. 现在时间是{cur_time}。请注意**始终使用中文回答**。注意题目来源于OCR结果，可能会有识别错误，请注意甄别."
            if force_search:
                system_instruction += " 必须使用搜索工具寻找答案"
            content = question_text,
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
            system_prompt = "You are a helpful assistant. Provide a concise and accurate answer to the user's question.使用中文回答。"
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