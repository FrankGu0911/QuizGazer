import base64
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

    chat = ChatOpenAI(
        model=vlm_config['model_name'],
        openai_api_key=vlm_config['api_key'],
        base_url=vlm_config['base_url']
    )

    try:
        response = chat.invoke(
            [
                SystemMessage(
                    content="You are an expert in analyzing images and extracting any questions present in them. Focus only on the question text itself. If there are multiple questions, return them all. If there is no question, return an empty string."
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

    chat = ChatOpenAI(
        model=llm_config['model_name'],
        openai_api_key=llm_config['api_key'],
        base_url=llm_config['base_url']
    )

    try:
        response = chat.invoke(
            [
                SystemMessage(content="You are a helpful assistant. Provide a concise and accurate answer to the user's question."),
                HumanMessage(content=question_text),
            ]
        )
        return response.content
    except Exception as e:
        return f"An error occurred while communicating with the LLM: {e}"