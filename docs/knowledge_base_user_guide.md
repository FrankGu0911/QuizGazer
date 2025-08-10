# 知识库RAG系统用户指南

## 概述

知识库RAG（Retrieval-Augmented Generation）系统是一个强大的文档管理和智能问答系统，它可以帮助您：

- 上传和管理各种类型的文档
- 智能搜索和检索相关信息
- 与AI助手进行基于知识库的对话
- 组织和分类您的知识内容

## 快速开始

### 1. 系统要求

- Python 3.8 或更高版本
- 至少 4GB 可用内存
- 2GB 可用磁盘空间

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 基本配置

首次使用前，需要配置知识库设置：

```python
from utils.config_manager import save_knowledge_base_config, save_chromadb_config

# 知识库基本配置
kb_config = {
    "enabled": True,
    "storage_path": "./data/knowledge_base",
    "max_file_size_mb": 100,
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "max_collections": 50,
    "background_processing": True,
    "max_concurrent_tasks": 3
}

save_knowledge_base_config(kb_config)

# ChromaDB配置
chromadb_config = {
    "connection_type": "local",
    "path": "./data/chromadb"
}

save_chromadb_config(chromadb_config)
```

## 主要功能

### 1. 创建和管理集合

集合是组织文档的基本单位，类似于文件夹的概念。

```python
from core.knowledge_base.manager import KnowledgeBaseManager

# 初始化管理器
kb_manager = KnowledgeBaseManager()

# 创建新集合
collection = kb_manager.create_collection(
    name="技术文档",
    description="存储技术相关的文档和资料"
)

print(f"创建集合: {collection.name} (ID: {collection.id})")

# 列出所有集合
collections = kb_manager.list_collections()
for col in collections:
    print(f"- {col.name}: {col.document_count} 个文档")
```

### 2. 上传文档

系统支持多种文档格式：

- **Markdown文件** (.md)：技术文档、说明文件
- **文本文件** (.txt)：纯文本内容
- **CSV文件** (.csv)：问答对、结构化数据
- **PDF文件** (.pdf)：报告、论文等
- **Word文档** (.docx)：办公文档

```python
from core.knowledge_base.models import DocumentType

# 上传单个文档
task = kb_manager.add_document_async(
    collection_id=collection.id,
    file_path="./docs/技术手册.md",
    doc_type=DocumentType.KNOWLEDGE_DOCUMENT
)

print(f"文档上传任务ID: {task.id}")

# 检查处理状态
status = kb_manager.get_processing_status(task.id)
print(f"处理状态: {status.status.value}")

# 批量上传文档
documents = [
    ("./docs/API文档.md", DocumentType.KNOWLEDGE_DOCUMENT),
    ("./data/FAQ.csv", DocumentType.QUESTION_BANK),
    ("./manuals/用户手册.pdf", DocumentType.KNOWLEDGE_DOCUMENT)
]

# 使用优化管理器进行批量处理
from core.knowledge_base.optimized_manager import create_optimized_manager

optimized_manager = create_optimized_manager()
task_ids = optimized_manager.add_documents_batch(collection.id, documents)
print(f"批量上传任务: {len(task_ids)} 个文档")
```

### 3. 搜索知识

```python
# 基本搜索
results = kb_manager.search_knowledge(
    query="如何配置API密钥？",
    collection_ids=[collection.id],
    top_k=5
)

for i, result in enumerate(results, 1):
    print(f"{i}. 相关度: {result.relevance_score:.3f}")
    print(f"   内容: {result.content[:100]}...")
    print(f"   来源: {result.source_document}")
    print()

# 使用优化搜索（带缓存）
optimized_results = optimized_manager.search_knowledge(
    query="如何配置API密钥？",
    collection_ids=[collection.id],
    top_k=5,
    use_cache=True
)

# 批量搜索
queries = [
    "API配置方法",
    "错误处理机制",
    "性能优化建议"
]

bulk_results = optimized_manager.bulk_search(
    queries=queries,
    collection_ids=[collection.id],
    top_k=3
)

for query, results in bulk_results.items():
    print(f"查询: {query}")
    print(f"结果数量: {len(results)}")
```

### 4. 与AI助手对话

```python
from core.knowledge_base.rag_pipeline import RAGPipeline

# 初始化RAG管道
rag_pipeline = RAGPipeline(
    knowledge_base_manager=kb_manager,
    llm_service=your_llm_service  # 您的LLM服务
)

# 启用知识库
rag_pipeline.enable_knowledge_base()
rag_pipeline.set_selected_collections([collection.id])

# 进行基于知识库的对话
response = rag_pipeline.process_query_with_knowledge(
    "请解释一下API认证的最佳实践"
)

print("AI回答:", response)

# 检查知识库状态
status = rag_pipeline.get_knowledge_base_status()
print(f"知识库状态: {status}")
```

## 高级功能

### 1. 性能优化

使用优化管理器可以获得更好的性能：

```python
# 创建带缓存配置的优化管理器
cache_config = {
    'embedding_cache': {
        'max_size': 10000,
        'max_memory_mb': 500
    },
    'query_cache': {
        'max_size': 1000,
        'max_memory_mb': 100,
        'default_ttl': 3600
    },
    'connection_pool': {
        'max_connections': 10,
        'timeout': 30.0
    }
}

optimized_manager = create_optimized_manager(cache_config=cache_config)

# 获取性能洞察
insights = optimized_manager.get_performance_insights()
print("性能统计:", insights['performance_summary'])
print("缓存统计:", insights['cache_statistics'])

# 内存优化
optimized_manager.optimize_memory_usage()
```

### 2. 监控和诊断

```python
# 获取系统统计信息
stats = kb_manager.get_knowledge_base_stats()
print(f"总集合数: {stats['total_collections']}")
print(f"总文档数: {stats['total_documents']}")
print(f"总块数: {stats['total_chunks']}")

# 获取集合详细信息
collection_info = kb_manager.get_collection(collection.id)
print(f"集合 '{collection_info.name}':")
print(f"- 文档数量: {collection_info.document_count}")
print(f"- 创建时间: {collection_info.created_at}")
print(f"- 最后更新: {collection_info.updated_at}")

# 列出集合中的文档
documents = kb_manager.list_documents(collection.id)
for doc in documents:
    print(f"- {doc.filename} ({doc.doc_type.value})")
```

### 3. 错误处理

```python
from core.knowledge_base.error_handling import with_error_handling, KnowledgeBaseError

@with_error_handling
def safe_document_upload(file_path, collection_id):
    return kb_manager.add_document_async(collection_id, file_path, DocumentType.KNOWLEDGE_DOCUMENT)

try:
    task = safe_document_upload("./docs/example.md", collection.id)
    print(f"上传成功: {task.id}")
except KnowledgeBaseError as e:
    print(f"知识库错误: {e}")
    print(f"用户友好消息: {e.get_user_friendly_message()}")
except Exception as e:
    print(f"其他错误: {e}")
```

## 用户界面

### 1. 知识库面板

如果您使用的是带UI的版本，可以通过图形界面管理知识库：

```python
from PySide6.QtWidgets import QApplication
from ui.knowledge_base_panel import KnowledgeBasePanel

app = QApplication([])
panel = KnowledgeBasePanel()
panel.show()
app.exec()
```

### 2. 设置对话框

```python
from ui.knowledge_base_settings import KnowledgeBaseSettingsDialog

settings_dialog = KnowledgeBaseSettingsDialog()
if settings_dialog.exec():
    print("设置已保存")
```

## 最佳实践

### 1. 文档组织

- **按主题创建集合**：将相关文档放在同一个集合中
- **使用描述性名称**：为集合和文档使用清晰的名称
- **定期清理**：删除过时或重复的文档

### 2. 搜索优化

- **使用具体的查询**：避免过于宽泛的搜索词
- **利用缓存**：对于频繁查询，启用缓存可以提高性能
- **批量处理**：对于多个查询，使用批量搜索功能

### 3. 性能优化

- **监控内存使用**：定期检查内存使用情况
- **合理设置缓存大小**：根据可用内存调整缓存配置
- **使用批量操作**：对于大量文档，使用批量上传功能

### 4. 错误处理

- **检查文件格式**：确保上传的文件格式受支持
- **监控处理状态**：异步操作需要检查完成状态
- **处理异常**：使用适当的错误处理机制

## 故障排除

### 常见问题

#### 1. 文档上传失败

**问题**: 文档上传后处理失败

**解决方案**:
- 检查文件格式是否支持
- 确认文件大小不超过限制
- 检查文件是否损坏
- 查看错误日志获取详细信息

```python
# 检查处理状态和错误信息
status = kb_manager.get_processing_status(task.id)
if status.status == ProcessingStatus.FAILED:
    print(f"处理失败: {status.error_message}")
```

#### 2. 搜索结果不准确

**问题**: 搜索返回不相关的结果

**解决方案**:
- 使用更具体的查询词
- 检查文档是否正确分块
- 调整chunk_size和chunk_overlap参数
- 确认搜索的集合是否正确

#### 3. 性能问题

**问题**: 系统响应缓慢

**解决方案**:
- 启用缓存功能
- 使用优化管理器
- 检查内存使用情况
- 考虑增加系统资源

```python
# 性能诊断
insights = optimized_manager.get_performance_insights()
issues = insights['performance_issues']
for issue in issues:
    print(f"性能问题: {issue['type']} - {issue.get('severity', 'unknown')}")
```

#### 4. 内存不足

**问题**: 系统内存使用过高

**解决方案**:
- 减少缓存大小
- 定期清理缓存
- 使用内存优化功能
- 分批处理大量文档

```python
# 内存优化
optimized_manager.optimize_memory_usage()
optimized_manager.clear_all_caches()
```

## 配置参考

### 知识库配置

```python
kb_config = {
    "enabled": True,                    # 是否启用知识库
    "storage_path": "./data/kb",        # 存储路径
    "max_file_size_mb": 100,           # 最大文件大小(MB)
    "chunk_size": 1000,                # 文档分块大小
    "chunk_overlap": 200,              # 分块重叠大小
    "max_collections": 50,             # 最大集合数
    "background_processing": True,      # 后台处理
    "max_concurrent_tasks": 3,         # 最大并发任务数
    "batch_size": 10,                  # 批处理大小
    "memory_threshold_mb": 1000,       # 内存阈值(MB)
    "cleanup_interval": 300            # 清理间隔(秒)
}
```

### ChromaDB配置

```python
chromadb_config = {
    "connection_type": "local",         # 连接类型: local/remote
    "path": "./data/chromadb",         # 本地路径
    "host": "localhost",               # 远程主机
    "port": 8000,                      # 远程端口
    "ssl_enabled": False,              # 是否启用SSL
    "auth_credentials": {              # 认证信息
        "username": "user",
        "password": "pass"
    }
}
```

### 缓存配置

```python
cache_config = {
    "embedding_cache": {
        "max_size": 10000,             # 最大条目数
        "max_memory_mb": 500           # 最大内存使用(MB)
    },
    "query_cache": {
        "max_size": 1000,              # 最大条目数
        "max_memory_mb": 100,          # 最大内存使用(MB)
        "default_ttl": 3600            # 默认过期时间(秒)
    },
    "connection_pool": {
        "max_connections": 10,         # 最大连接数
        "timeout": 30.0                # 连接超时(秒)
    }
}
```

## 支持和反馈

如果您在使用过程中遇到问题或有改进建议，请：

1. 查看本文档的故障排除部分
2. 检查系统日志获取详细错误信息
3. 联系技术支持团队

---

*本文档会持续更新，请关注最新版本。*