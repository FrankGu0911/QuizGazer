# QuizGazer

**QuizGazer** 是一款智能桌面应用，旨在帮助您快速解答截图中的问题。无论您是在进行在线测验、观看课程视频，还是浏览包含问题的文档，QuizGazer 都能通过先进的AI技术，从图片中识别问题并迅速提供答案，成为您学习和工作中的得力助手。

## 核心功能

*   **智能截图识题**: 只需一键点击，即可截取屏幕任意区域，应用将自动调用视觉语言模型（VLM）识别并提取图片中的问题文本。
*   **AI快速问答**: 利用强大的大型语言模型（LLM），根据识别出的问题迅速生成准确、简洁的答案。
*   **可编辑问题**: 如果自动识别的题目不准确，您可以在界面上轻松编辑和修正，然后重新获取答案。
*   **简洁的浮动窗口**:
    *   **紧凑模式**: 默认以一个不打扰视线的紧凑图标形式存在。
    *   **扩展视图**: 截图后自动展开，清晰展示问题和答案。
    *   **一键复制**: 方便地将答案复制到剪贴板。
*   **窗口置顶与拖动**: 可将窗口“钉”在屏幕最顶层，并随意拖动到任何位置，方便对照使用。
*   **灵活的模型配置**: 支持通过 `config.ini` 文件自定义配置AI模型，您可以根据需求更换不同的AI服务。

## 安装与配置

**1. 克隆项目**

```bash
git clone https://github.com/your-username/QuizGazer.git
cd QuizGazer
```

**2. 创建虚拟环境** (推荐)

```bash
# 使用uv
uv sync

# 使用conda
conda create -n quizgazer python=3.10
conda activate quizgazer
pip install -r requirements.txt
```

**3. 配置AI模型**

为了让应用能够正常使用AI服务，您需要配置API密钥和模型信息。

*   首先，将 `config.ini.example` 文件复制一份并重命名为 `config.ini`。
*   然后，用您自己的信息填充 `config.ini` 文件。您需要分别为视觉语言模型（VLM）和大型语言模型（LLM）提供配置。

```ini
[vlm]
# 用于从图像中识别问题的模型
model_name = "gpt-4-vision-preview"
api_key = "sk-YOUR_OPENAI_API_KEY"
base_url = "https://api.openai.com/v1"

[llm]
# 用于回答问题的模型
model_name = "gpt-3.5-turbo"
api_key = "sk-YOUR_OPENAI_API_KEY"
base_url = "https://api.openai.com/v1"
```

> **注意**: `base_url` 可以根据您使用的代理或服务提供商进行修改。

## 如何运行

完成安装和配置后，在项目根目录下运行以下命令即可启动应用：

```bash
python main.py```

应用启动后，会以一个紧凑的浮动窗口形式出现在屏幕上。

## 如何使用

1.  **启动与界面**
    *   应用启动后，您会看到一个包含三个按钮的紧凑窗口：
        *   **📸 (截图)**: 点击开始截图。
        *   **📌 (置顶)**: 点击可将窗口固定在屏幕最顶层或取消置顶。绿色表示已置顶。
        *   **✕ (退出)**: 关闭应用。

2.  **截图识题**
    *   点击 **📸** 按钮，应用窗口会暂时隐藏。
    *   按住鼠标左键并拖动，选择您想识别问题的屏幕区域。
    *   松开鼠标后，应用窗口会自动展开，并显示从截图中识别出的问题。

3.  **获取与编辑答案**
    *   截图完成后，应用会自动将识别出的问题发送给AI，并在下方显示答案。
    *   如果问题识别有误，您可以直接在“Question (editable)”输入框中进行修改。
    *   点击 **Get New Answer** 按钮，可以根据修改后的问题重新获取答案。

4.  **管理窗口**
    *   点击 **Copy Answer** 按钮，可一键复制答案到剪贴板。
    *   点击 **Back** 按钮，窗口将收起，返回到紧凑的图标模式。
    *   点击 **Exit** 按钮，可随时退出应用。
    *   您可以按住窗口的任意空白区域拖动它到屏幕的任何位置。

## 技术栈

*   **GUI框架**: [PySide6](https://www.qt.io/qt-for-python) - 用于构建桌面应用的用户界面。
*   **AI集成**: [LangChain](https://python.langchain.com/) - 简化了与大型语言模型（LLM）和视觉语言模型（VLM）的交互。
*   **截图功能**: [mss](https://python-mss.readthedocs.io/) - 一个快速、跨平台的屏幕截图库。
*   **图像处理**: [Pillow](https://python-pillow.org/) - 用于处理图像数据。
*   **模型提供商**: [OpenAI](https://openai.com/) - 默认配置使用其GPT系列模型，但可通过 `config.ini` 灵活更换。