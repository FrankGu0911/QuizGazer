# 示例文档集合

本目录包含了用于测试知识库RAG系统的各种类型示例文档。这些文档展示了系统支持的不同文档格式和内容类型。

## 文档类型

### 1. 技术文档 (Markdown)
- `ai_fundamentals.md` - 人工智能基础知识
- `machine_learning_guide.md` - 机器学习指南
- `api_documentation.md` - API文档示例

### 2. 问答库 (CSV)
- `faq_general.csv` - 常见问题解答
- `technical_qa.csv` - 技术问答对
- `troubleshooting_qa.csv` - 故障排除问答

### 3. 纯文本文档 (TXT)
- `company_policies.txt` - 公司政策文档
- `user_manual.txt` - 用户手册
- `release_notes.txt` - 版本发布说明

### 4. 结构化数据 (JSON)
- `product_catalog.json` - 产品目录
- `configuration_examples.json` - 配置示例

## 使用方法

### 1. 批量上传示例

```python
from core.knowledge_base.manager import KnowledgeBaseManager
from core.knowledge_base.models import DocumentType
import os

# 初始化管理器
kb_manager = KnowledgeBaseManager()

# 创建示例集合
collection = kb_manager.create_collection(
    name="示例文档集合",
    description="用于测试的示例文档"
)

# 定义文档映射
document_mapping = {
    "ai_fundamentals.md": DocumentType.KNOWLEDGE_DOCUMENT,
    "machine_learning_guide.md": DocumentType.KNOWLEDGE_DOCUMENT,
    "api_documentation.md": DocumentType.KNOWLEDGE_DOCUMENT,
    "faq_general.csv": DocumentType.QUESTION_BANK,
    "technical_qa.csv": DocumentType.QUESTION_BANK,
    "troubleshooting_qa.csv": DocumentType.QUESTION_BANK,
    "company_policies.txt": DocumentType.KNOWLEDGE_DOCUMENT,
    "user_manual.txt": DocumentType.KNOWLEDGE_DOCUMENT,
    "release_notes.txt": DocumentType.KNOWLEDGE_DOCUMENT
}

# 批量上传文档
sample_docs_path = "./docs/sample_documents"
documents = []

for filename, doc_type in document_mapping.items():
    file_path = os.path.join(sample_docs_path, filename)
    if os.path.exists(file_path):
        documents.append((file_path, doc_type))

# 使用优化管理器进行批量上传
from core.knowledge_base.optimized_manager import create_optimized_manager

optimized_manager = create_optimized_manager()
task_ids = optimized_manager.add_documents_batch(collection.id, documents)

print(f"已提交 {len(task_ids)} 个文档处理任务")
```

### 2. 测试搜索功能

```python
# 等待文档处理完成后进行搜索测试
import time

# 等待处理完成
print("等待文档处理完成...")
time.sleep(30)  # 根据文档大小调整等待时间

# 测试查询
test_queries = [
    "什么是人工智能？",
    "如何配置API？",
    "常见的错误有哪些？",
    "公司的休假政策是什么？",
    "最新版本有什么新功能？"
]

for query in test_queries:
    print(f"\n查询: {query}")
    results = optimized_manager.search_knowledge(
        query=query,
        collection_ids=[collection.id],
        top_k=3
    )
    
    for i, result in enumerate(results, 1):
        print(f"  {i}. 相关度: {result.relevance_score:.3f}")
        print(f"     内容: {result.content[:100]}...")
        print(f"     来源: {result.source_document}")
```

## 文档内容说明

### 技术文档特点
- 包含代码示例和技术概念
- 使用Markdown格式，支持代码高亮
- 包含层次化的标题结构
- 适合技术知识检索

### 问答库特点
- CSV格式，包含问题和答案列
- 支持分类和难度标记
- 适合FAQ和客服场景
- 可以直接用于问答匹配

### 纯文本特点
- 简单的文本格式
- 适合政策文档和说明书
- 内容结构相对简单
- 处理速度较快

## 测试场景

### 1. 基础功能测试
使用这些示例文档可以测试：
- 文档上传和处理
- 文本分块和向量化
- 基本搜索功能
- 结果排序和相关性

### 2. 性能测试
- 批量文档处理性能
- 并发搜索性能
- 内存使用情况
- 缓存效果

### 3. 准确性测试
- 搜索结果的相关性
- 不同文档类型的处理效果
- 中英文混合内容处理
- 专业术语识别

## 自定义示例文档

您可以根据自己的需求创建自定义示例文档：

### 1. Markdown文档模板

```markdown
# 文档标题

## 概述
简要描述文档内容...

## 主要内容

### 子章节1
详细内容...

### 子章节2
更多内容...

## 代码示例

```python
# 示例代码
def example_function():
    return "Hello, World!"
```

## 总结
文档总结...
```

### 2. CSV问答库模板

```csv
question,answer,category,difficulty
"问题1","答案1","分类1","初级"
"问题2","答案2","分类2","中级"
"问题3","答案3","分类3","高级"
```

### 3. 文本文档模板

```
文档标题
========

第一部分：基本信息
- 要点1
- 要点2
- 要点3

第二部分：详细说明
详细的文本内容...

第三部分：注意事项
重要的注意事项...
```

## 注意事项

1. **文件编码**：确保所有文档使用UTF-8编码
2. **文件大小**：单个文件不要超过配置的最大大小限制
3. **内容质量**：确保文档内容准确、完整
4. **格式规范**：遵循相应格式的标准规范
5. **版权问题**：确保有权使用文档内容

## 扩展建议

### 1. 多语言支持
- 添加英文版本的示例文档
- 测试多语言混合内容
- 验证跨语言搜索能力

### 2. 专业领域
- 创建特定领域的示例文档
- 测试专业术语的处理效果
- 验证领域知识的准确性

### 3. 多媒体内容
- 添加包含图片的文档
- 测试表格内容的处理
- 验证复杂格式的支持

---

*这些示例文档旨在帮助您快速了解和测试知识库RAG系统的功能。请根据实际需求调整和扩展文档内容。*