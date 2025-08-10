# QuizGazer 知识库功能实现方案

## 1. 改进目的

当前 QuizGazer 应用的核心功能是利用视觉语言模型（VLM）从截图中识别问题，并由大语言模型（LLM）提供解答。为了进一步提升应用的专业性和回答的准确性，本项目旨在引入一个外部知识库功能。

主要目标如下：

*   **提升回答准确性**：通过引入与用户提供的文档（如复习资料、专业题库）相关的知识，使 LLM 的回答不再仅仅依赖其通用知识，而是基于特定的、可信的知识源。
*   **增强个性化**：允许用户根据自己的学习或工作内容，构建专属知识库，使应用成为一个个性化的学习和查询工具。
*   **扩展应用场景**：从一个通用的截图问答工具，扩展为一个能够深入特定领域的智能助手，例如用于备考、查询内部技术文档等。

该功能将通过实现一个**检索增强生成（Retrieval-Augmented Generation, RAG）**流程来完成。

## 2. 总体设计

我们将引入一个新的“知识库管理”模块，并改造现有的 AI 服务流程。主要分为两大块：

1.  **知识库构建与管理（离线过程）**：负责将用户上传的非结构化或结构化文档（如 PDF, Markdown, CSV）处理成结构化的向量数据，并存入本地向量数据库。
2.  **检索与生成流程（在线过程）**：在用户提问时，先从知识库中检索相关信息，然后将这些信息与原始问题一起整合，形成一个新的、更丰富的提示词（Prompt），最后交给大语言模型（LLM）生成最终答案。

### 2.1 架构设计图

```mermaid
graph TD
    subgraph Knowledge Base Management (Offline Process)
        A[1. 用户文档源 (PDF, MD, CSV)] --> B{2. 文档加载与切分};
        B --> C{3. 文本嵌入 (Embedding API)};
        C --> D[(4. 本地向量数据库 - ChromaDB)];
    end

    subgraph RAG Inference (Online Process)
        E[用户问题] --> F{3. 文本嵌入 (Embedding API)};
        F --> G{5. 向量检索};
        D --> G;
        G --> H{6. 重排序 (Reranker API)};
        H --> I{7. 提示词工程};
        E --> I;
        I --> J{8. LLM 生成答案};
        J --> K[最终答案];
    end
```

### 2.2 核心挑战与对策

*   **模型部署**：为了降低本地资源消耗和维护成本，**Embedding** 和 **Reranker** 模型将通过调用外部 API（兼容 OpenAI 格式）的方式实现。
*   **混合文档处理**：
    *   **长篇资料 (PDF/MD)**: 采用“递归字符切分”策略，保证知识的语义完整性。
    *   **题库 (CSV/JSON)**: 采用“按行处理”策略，将每个问答对作为一个独立的知识单元。
    *   **元数据 (Metadata)**: 在存入向量数据库时，为每个数据块附加源文件、文档类型等元数据，便于后续过滤和追溯。

## 3. 技术选型

*   **向量数据库**: **ChromaDB** (本地存储，轻量易用)。
*   **编排框架**: **LangChain** (简化文档处理、切分和与向量数据库的交互)。
*   **Embedding API**: 兼容 OpenAI 的 API 服务 (如 Zhipu AI, Moonshot, or OpenAI)。
*   **Reranker API**: 兼容vllm格式的 API 服务，/v1/rerank为路径的。

## 4. 项目结构变更

将在 `core` 目录下新增 `knowledge_base` 模块，用于封装所有与知识库相关的功能。

```
QuizGazer/
└── core/
    ├── ...
    └── knowledge_base/
        ├── __init__.py
        ├── document_processor.py  # 文档加载与切分
        ├── manager.py             # 知识库管理 (创建、索引)
        └── retriever.py           # 知识检索 (查询、rerank)
```

## 5. 实施步骤

1.  **[已完成]** **规划与设计**：确定 RAG 方案，并根据 API 和混合文档需求进行调整。
2.  **配置更新**：修改 `config.ini.example` 和 `utils/config_manager.py` 以支持知识库、Embedding 和 Reranker 的 API 配置。
3.  **文档处理模块**：创建 `core/knowledge_base` 模块，并实现 `document_processor.py`，用于加载和处理不同类型的文档。
4.  **知识库管理模块**：实现 `manager.py`，负责调用 Embedding API 将处理后的文档块向量化并存入 ChromaDB。
5.  **知识检索模块**：实现 `retriever.py`，负责查询向量数据库、调用 Reranker API 并返回最相关的知识片段。
6.  **整合 RAG 流程**：修改 `core/ai_services.py`，在 LLM 请求前插入知识检索和提示词构建的步骤。
7.  **UI 开发**：在 `ui/main_window.py` 中添加知识库管理的 UI 界面（如上传文件、创建知识库）和功能开关。

此方案旨在以模块化、可扩展的方式为 QuizGazer 应用增加强大的知识库功能，从而显著提升其核心价值。