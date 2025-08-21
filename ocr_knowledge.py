import mss
import base64
import requests
import json

# --- 配置信息 ---
# SiliconFlow API 的密钥
API_KEY = "sk-qanjubrwcwlmqlgsdhplcngahidxbhbfcmclflkfzduakksv"
# API 的基础 URL
BASE_URL = "https://api.siliconflow.cn/v1"
# 使用的模型名称
MODEL_NAME = "Pro/Qwen/Qwen2.5-VL-7B-Instruct"
# 要进行截图的屏幕编号 (1 代表主屏幕, 2 代表第二个屏幕, etc.)
SCREEN_NUMBER = 2
# 保存知识的 Markdown 文件名
KNOWLEDGE_FILE = "knowledge.md"

def capture_and_process_screen(screen_number: int):
    """
    对指定的屏幕进行截图, 调用VLM进行OCR和排版, 并将结果追加到文件中。
    """
    try:
        with mss.mss() as sct:
            # 检查屏幕数量是否有效
            if len(sct.monitors) < screen_number:
                print(f"错误: 找不到屏幕 {screen_number}。系统共有 {len(sct.monitors)} 个屏幕。")
                print("可用的屏幕信息:", sct.monitors)
                return

            # 获取指定屏幕的信息 (索引从0开始, 所以 screen_number - 1)
            monitor = sct.monitors[screen_number]

            # 截取指定屏幕
            sct_img = sct.grab(monitor)
            
            # 将 RGBA 图像转换为 RGB
            # VLM 模型通常需要 RGB 格式
            raw_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)

            print(f"已成功截取屏幕 {screen_number} 的图像。")

            # 将图像字节流编码为 Base64 字符串
            base64_image = base64.b64encode(raw_bytes).decode('utf-8')
            print("图像已成功编码为 Base64。")

            # --- 调用 VLM API ---
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": MODEL_NAME,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": '''
                                你是一位知识管理专家，任务是分析这张图片/文档页面的内容，并将其提炼、整合成一篇结构清晰、重点突出的Markdown格式知识笔记。

请遵循以下原则：

1.  **识别主题与层级**：
    * 首先，识别并提取内容的主要标题或核心主题，作为一级标题（#）。如果图片没有明确标题，请根据内容自行总结一个。
    * 其次，梳理出文中的关键定义、核心观点、主要步骤或数据。使用二级标题（##）、列表（-）、粗体（**）等方式来清晰地展示信息的层级结构。

2.  **保留关键细节**：在保持简洁的同时，确保重要的细节、例子或数据被完整记录下来。

3.  **忽略无关元素**：请自动忽略页码、页眉、页脚、水印、logo等与知识内容无关的装饰性或导航性元素。

请直接输出整理好的Markdown文本。'''
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 4096, # 您可以根据需要调整最大输出长度
                "temperature": 0.3 # 您可以根据需要调整创造性
            }
            
            print("正在向 VLM 发送请求...")
            response = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload)

            # 检查请求是否成功
            response.raise_for_status() 

            print("已成功收到 VLM 的响应。")
            response_data = response.json()
            
            # 提取模型生成的文本内容
            generated_text = response_data['choices'][0]['message']['content']
            
            # 简单的后处理：去除可能存在的前后引号
            if generated_text.startswith('"') and generated_text.endswith('"'):
                generated_text = generated_text[1:-1]
            if generated_text.startswith("'") and generated_text.endswith("'"):
                generated_text = generated_text[1:-1]
            generated_text =  generated_text.replace("```markdown", "")
            generated_text =  generated_text.replace("```", "")
            
                
            # --- 将结果追加到 Markdown 文件 ---
            with open(KNOWLEDGE_FILE, "a", encoding="utf-8") as f:
                # f.write("\n\n---\n\n") # 添加分割线以区分每次的记录
                f.write(generated_text)
            
            print(f"已成功将知识文本追加到 {KNOWLEDGE_FILE}。")
            # print("\n--- VLM 生成的内容 ---\n")
            # print(generated_text)


    except mss.exception.ScreenShotError as e:
        print(f"截图失败: {e}")
    except requests.exceptions.RequestException as e:
        print(f"API 请求失败: {e}")
        # 打印更详细的错误信息
        if 'response' in locals() and hasattr(response, 'text'):
            print("API 响应内容:", response.text)
    except (KeyError, IndexError) as e:
        print(f"解析API响应失败: {e}")
        print("收到的原始响应数据:", response_data)
    except Exception as e:
        print(f"发生未知错误: {e}")

if __name__ == "__main__":
    capture_and_process_screen(SCREEN_NUMBER)