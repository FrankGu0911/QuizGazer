# 知识库RAG系统开发者指南

本指南面向希望扩展或自定义知识库RAG系统的开发者，提供了系统架构、API参考和扩展开发的详细信息。

## 系统架构

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户界面层                            │
├─────────────────────────────────────────────────────────────┤
│  Web UI  │  Desktop UI  │  CLI  │  REST API  │  Python API  │
├─────────────────────────────────────────────────────────────┤
│                        业务逻辑层                            │
├─────────────────────────────────────────────────────────────┤
│  RAG Pipeline  │  Knowledge Manager  │  Document Processor  │
├─────────────────────────────────────────────────────────────┤
│                        服务层                               │
├─────────────────────────────────────────────────────────────┤
│  Vector Store  │  Task Manager  │  Cache Manager  │  Monitor │
├─────────────────────────────────────────────────────────────┤
│                        数据层                               │
├─────────────────────────────────────────────────────────────┤
│    ChromaDB    │   File System   │    Configuration        │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件

### KnowledgeBaseManager

主要的知识库管理器，负责协调所有组件。

```python
class KnowledgeBaseManager:
    def __init__(self, storage_path: str = None, chromadb_config: ChromaDBConfig = None):
        pass
    
    def create_collection(self, name: str, description: str = "") -> Collection:
        pass
    
    def search_knowledge(self, query: str, collection_ids: List[str] = None, 
                        top_k: int = 10) -> List[KnowledgeFragment]:
        pass
```

## 扩展开发

### 自定义文档处理器

```python
from core.knowledge_base.document_processor import DocumentProcessor

class CustomDocumentProcessor(DocumentProcessor):
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        super().__init__(chunk_size, chunk_overlap)
        self.processors['.xml'] = self._process_xml
    
    def _process_xml(self, file_path: str) -> str:
        # 实现XML处理逻辑
        pass
```

## 测试指南

### 单元测试

```python
import unittest
from core.knowledge_base.manager import KnowledgeBaseManager

class TestKnowledgeBaseManager(unittest.TestCase):
    def setUp(self):
        self.kb_manager = KnowledgeBaseManager()
    
    def test_create_collection(self):
        collection = self.kb_manager.create_collection("测试集合")
        self.assertIsNotNone(collection)
```

## 部署指南

### Docker部署

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "api.server"]
```

---

*本开发者指南提供了知识库RAG系统的技术文档，帮助开发者进行扩展开发。*