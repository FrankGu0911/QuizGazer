import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from urllib.parse import urlparse

# 导入原生 Gemini 工具所需的库
try:
    from google.ai.generativelanguage_v1beta.types import Tool as GenAITool
except ImportError:
    print("错误: 无法导入 GenAITool。")
    print("请确保您已安装 google-generativeai 库: pip install google-generativeai")
    exit(1)

# --- 配置信息 ---
# 您的 API Key
API_KEY = "AIzaSyDqmhWrMiyV8MdBvpOEPAxtATe2TXf2O5E" 

# 您想使用的模型名称
# 注意: Google 官方目前没有 'gemini-2.5-flash' 模型。
# 为避免上游API报错，建议使用 'gemini-1.5-flash' 或 'gemini-pro'。
# 您的代理可能会处理这个命名，但使用官方名称更保险。
MODEL_NAME = "gemini-2.5-flash" # 使用 1.5 Pro，因为它对工具调用支持得很好

# 您的 gemini-balance 服务器地址
BASE_URL_NATIVE = "https://generativelanguage.googleapis.com/v1beta"

# --- 脚本主体 ---
print("✅ 路径检查成功 (200 OK)，现在进行最终的原生工具调用测试...")

# 从 URL 中解析出 api_endpoint
api_endpoint = urlparse(BASE_URL_NATIVE).netloc
print(f"将要连接的 Endpoint: {api_endpoint}")
print(f"将要使用的模型: {MODEL_NAME}")

try:
    # 1. 初始化 ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=API_KEY,
        client_options={"api_endpoint": api_endpoint},
        # convert_system_message_to_human=True # 如果遇到system message问题可以取消注释
    )

    # 2. 准备调用原生 Google 搜索工具
    print("\n⏳ 正在发送请求，要求模型使用 [Google Search] 工具...")
    
    # 构造带有工具的调用请求
    resp = llm.invoke(
        "When is the next total solar eclipse in US?", 
        tools=[GenAITool(google_search={})], 
    )

    # 3. 打印结果
    print("\n✅ 请求成功！")
    print("-" * 40)
    print("模型最终回答:")
    print(resp.content)
    print("-" * 40)
    
    # 检查并打印模型实际的工具调用过程
    if resp.tool_calls:
        print("\n🛠️ 模型在后台执行了以下工具调用：")
        for tool_call in resp.tool_calls:
            print(f"  - 函数名称: {tool_call['name']}")
            print(f"    函数参数: {tool_call['args']}")
    else:
        print("\nℹ️ 模型没有执行工具调用，可能是基于内部知识直接回答。")


except Exception as e:
    print(f"\n❌ 调用失败！错误信息如下：")
    print("-" * 40)
    print(e)
    print("-" * 40)
    print("\n🔍 如果仍然失败，请检查：")
    print("  1. 您使用的模型名称 (`{MODEL_NAME}`) 是否被您的代理和上游 Google API 支持。")
    print("  2. API Key 是否有调用该模型的权限。")
    print("  3. 查看 `gemini-balance` 的后台日志获取详细错误。")