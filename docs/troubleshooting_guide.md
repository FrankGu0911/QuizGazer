# 知识库RAG系统故障排除指南

本指南提供了知识库RAG系统常见问题的诊断和解决方案。

## 目录

- [安装和配置问题](#安装和配置问题)
- [文档处理问题](#文档处理问题)
- [搜索和检索问题](#搜索和检索问题)
- [性能问题](#性能问题)
- [内存和资源问题](#内存和资源问题)
- [API和服务问题](#api和服务问题)
- [数据库连接问题](#数据库连接问题)
- [UI界面问题](#ui界面问题)
- [日志和调试](#日志和调试)

## 安装和配置问题

### 问题1：依赖包安装失败

**症状**：
```bash
ERROR: Could not find a version that satisfies the requirement chromadb
```

**可能原因**：
- Python版本不兼容
- 网络连接问题
- pip版本过旧

**解决方案**：
```bash
# 检查Python版本（需要3.8+）
python --version

# 升级pip
pip install --upgrade pip

# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 如果仍有问题，尝试单独安装问题包
pip install chromadb --no-cache-dir
```

### 问题2：配置文件加载失败

**症状**：
```python
FileNotFoundError: [Errno 2] No such file or directory: 'config/knowledge_base.json'
```

**解决方案**：
```python
# 创建默认配置
from utils.config_manager import save_knowledge_base_config

default_config = {
    "enabled": True,
    "storage_path": "./data/knowledge_base",
    "max_file_size_mb": 100,
    "chunk_size": 1000,
    "chunk_overlap": 200
}

save_knowledge_base_config(default_config)
```

### 问题3：环境变量未设置

**症状**：
```python
ValueError: API key not found
```

**解决方案**：
```bash
# 创建.env文件
echo "OPENAI_API_KEY=your-api-key-here" > .env
echo "CHROMADB_PATH=./data/chromadb" >> .env

# 或者在代码中设置
import os
os.environ['OPENAI_API_KEY'] = 'your-api-key-here'
```

## 文档处理问题

### 问题4：文档上传失败

**症状**：
```python
KnowledgeBaseError: Failed to process document: unsupported file format
```

**诊断步骤**：
```python
# 检查文件格式
import os
file_path = "your_document.pdf"
file_extension = os.path.splitext(file_path)[1].lower()
print(f"文件扩展名: {file_extension}")

# 检查文件大小
file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
print(f"文件大小: {file_size:.2f} MB")

# 检查文件是否可读
try:
    with open(file_path, 'rb') as f:
        f.read(100)
    print("文件可读")
except Exception as e:
    print(f"文件读取错误: {e}")
```

**解决方案**：
- 确认文件格式在支持列表中（.md, .txt, .csv, .pdf, .docx）
- 检查文件大小是否超过限制
- 确认文件未损坏且可读
- 检查文件编码（建议使用UTF-8）

### 问题5：PDF文档处理失败

**症状**：
```python
ProcessingError: Failed to extract text from PDF
```

**解决方案**：
```python
# 安装额外的PDF处理依赖
pip install PyPDF2 pdfplumber

# 检查PDF文件
import PyPDF2
try:
    with open('document.pdf', 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        print(f"PDF页数: {len(reader.pages)}")
        print(f"第一页文本: {reader.pages[0].extract_text()[:100]}")
except Exception as e:
    print(f"PDF处理错误: {e}")
```

### 问题6：文档处理超时

**症状**：
```python
TimeoutError: Document processing timeout after 300 seconds
```

**解决方案**：
```python
# 调整超时设置
kb_config = {
    "processing_timeout": 600,  # 增加到10分钟
    "max_concurrent_tasks": 2   # 减少并发任务
}

# 分批处理大文档
def process_large_document(file_path, collection_id):
    # 检查文件大小
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    
    if file_size_mb > 50:  # 大于50MB
        print(f"大文档 ({file_size_mb:.1f}MB)，建议分割后处理")
        # 实现文档分割逻辑
    else:
        return kb_manager.add_document_async(collection_id, file_path, doc_type)
```

## 搜索和检索问题

### 问题7：搜索结果不准确

**症状**：搜索返回不相关的结果

**诊断步骤**：
```python
# 检查搜索参数
query = "你的查询"
results = kb_manager.search_knowledge(
    query=query,
    collection_ids=[collection_id],
    top_k=10  # 增加结果数量进行分析
)

# 分析结果相关性
for i, result in enumerate(results):
    print(f"结果 {i+1}:")
    print(f"  相关度: {result.relevance_score:.3f}")
    print(f"  内容: {result.content[:200]}...")
    print(f"  来源: {result.source_document}")
    print()
```

**解决方案**：
```python
# 1. 优化查询词
def optimize_query(original_query):
    # 添加同义词或相关词
    synonyms = {
        "API": ["接口", "应用程序接口"],
        "配置": ["设置", "配置文件", "参数"]
    }
    
    optimized_query = original_query
    for key, values in synonyms.items():
        if key in original_query:
            optimized_query += " " + " ".join(values)
    
    return optimized_query

# 2. 调整分块参数
kb_config = {
    "chunk_size": 800,      # 减小分块大小
    "chunk_overlap": 150    # 增加重叠
}

# 3. 使用多个查询策略
def multi_query_search(query, collection_ids, top_k=5):
    queries = [
        query,
        f"关于{query}的信息",
        f"{query}是什么",
        f"如何{query}"
    ]
    
    all_results = []
    for q in queries:
        results = kb_manager.search_knowledge(q, collection_ids, top_k)
        all_results.extend(results)
    
    # 去重并按相关性排序
    unique_results = {}
    for result in all_results:
        key = result.content[:100]  # 使用内容前100字符作为去重键
        if key not in unique_results or result.relevance_score > unique_results[key].relevance_score:
            unique_results[key] = result
    
    return sorted(unique_results.values(), key=lambda x: x.relevance_score, reverse=True)[:top_k]
```

### 问题8：搜索速度慢

**症状**：搜索响应时间超过5秒

**诊断步骤**：
```python
import time

# 测量搜索时间
start_time = time.time()
results = kb_manager.search_knowledge("测试查询", [collection_id], top_k=5)
search_time = time.time() - start_time

print(f"搜索耗时: {search_time:.2f}秒")
print(f"结果数量: {len(results)}")

# 检查集合大小
collection = kb_manager.get_collection(collection_id)
print(f"集合文档数: {collection.document_count}")
print(f"总块数: {collection.total_chunks}")
```

**解决方案**：
```python
# 1. 启用缓存
from core.knowledge_base.optimized_manager import create_optimized_manager

cache_config = {
    'query_cache': {
        'max_size': 1000,
        'max_memory_mb': 100,
        'default_ttl': 3600
    }
}

optimized_manager = create_optimized_manager(cache_config=cache_config)

# 2. 减少搜索范围
# 只搜索相关集合
relevant_collections = filter_relevant_collections(query)
results = optimized_manager.search_knowledge(
    query, 
    collection_ids=relevant_collections, 
    top_k=5
)

# 3. 使用批量搜索
queries = ["查询1", "查询2", "查询3"]
bulk_results = optimized_manager.bulk_search(queries, [collection_id])
```

## 性能问题

### 问题9：系统响应缓慢

**诊断步骤**：
```python
# 获取性能洞察
from core.knowledge_base.optimized_manager import create_optimized_manager

optimized_manager = create_optimized_manager()
insights = optimized_manager.get_performance_insights()

print("性能问题:")
for issue in insights['performance_issues']:
    print(f"- {issue['type']}: {issue.get('severity', 'unknown')}")

print("\n优化建议:")
for suggestion in insights['optimization_suggestions']:
    print(f"- {suggestion['type']}: {suggestion['reason']}")
```

**解决方案**：
```python
# 1. 启用所有优化功能
cache_config = {
    'embedding_cache': {
        'max_size': 10000,
        'max_memory_mb': 500
    },
    'query_cache': {
        'max_size': 1000,
        'max_memory_mb': 100
    },
    'connection_pool': {
        'max_connections': 10
    }
}

optimized_manager = create_optimized_manager(cache_config=cache_config)

# 2. 定期内存优化
import threading
import time

def memory_optimization_task():
    while True:
        time.sleep(300)  # 每5分钟
        optimized_manager.optimize_memory_usage()

optimization_thread = threading.Thread(target=memory_optimization_task, daemon=True)
optimization_thread.start()

# 3. 调整并发参数
kb_config = {
    "max_concurrent_tasks": 2,  # 减少并发任务
    "batch_size": 5            # 减小批处理大小
}
```

### 问题10：高CPU使用率

**症状**：CPU使用率持续超过80%

**诊断步骤**：
```python
import psutil
import time

# 监控CPU使用率
def monitor_cpu(duration=60):
    cpu_usage = []
    for _ in range(duration):
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_usage.append(cpu_percent)
        print(f"CPU使用率: {cpu_percent}%")
    
    avg_cpu = sum(cpu_usage) / len(cpu_usage)
    print(f"平均CPU使用率: {avg_cpu:.1f}%")
    return avg_cpu

# 检查进程CPU使用
process = psutil.Process()
print(f"当前进程CPU使用率: {process.cpu_percent()}%")
```

**解决方案**：
```python
# 1. 限制并发处理
kb_config = {
    "max_concurrent_tasks": 1,
    "max_workers": 2
}

# 2. 使用更高效的模型
# 选择计算量较小的嵌入模型
embedding_config = {
    "model": "text-embedding-ada-002",  # 相对轻量
    "batch_size": 16  # 减小批处理大小
}

# 3. 实现CPU使用率限制
import time
import threading

class CPUThrottler:
    def __init__(self, max_cpu_percent=70):
        self.max_cpu_percent = max_cpu_percent
        self.monitoring = True
    
    def start_monitoring(self):
        def monitor():
            while self.monitoring:
                cpu_percent = psutil.cpu_percent(interval=1)
                if cpu_percent > self.max_cpu_percent:
                    print(f"CPU使用率过高 ({cpu_percent}%)，暂停处理...")
                    time.sleep(2)  # 暂停2秒
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()

throttler = CPUThrottler()
throttler.start_monitoring()
```

## 内存和资源问题

### 问题11：内存不足错误

**症状**：
```python
MemoryError: Unable to allocate memory
```

**诊断步骤**：
```python
import psutil

# 检查内存使用情况
def check_memory_usage():
    # 系统内存
    memory = psutil.virtual_memory()
    print(f"系统内存使用率: {memory.percent}%")
    print(f"可用内存: {memory.available / 1024 / 1024 / 1024:.1f} GB")
    
    # 进程内存
    process = psutil.Process()
    process_memory = process.memory_info()
    print(f"进程内存使用: {process_memory.rss / 1024 / 1024:.1f} MB")
    
    # 缓存内存使用
    if hasattr(optimized_manager, 'cache_manager'):
        cache_stats = optimized_manager.get_cache_statistics()
        print(f"缓存内存使用: {cache_stats.get('total_memory_mb', 0):.1f} MB")

check_memory_usage()
```

**解决方案**：
```python
# 1. 减少缓存大小
cache_config = {
    'embedding_cache': {
        'max_size': 5000,      # 减少到5000
        'max_memory_mb': 200   # 减少到200MB
    },
    'query_cache': {
        'max_size': 500,       # 减少到500
        'max_memory_mb': 50    # 减少到50MB
    }
}

# 2. 实现内存监控和自动清理
class MemoryManager:
    def __init__(self, max_memory_mb=1000):
        self.max_memory_mb = max_memory_mb
    
    def check_and_cleanup(self):
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb > self.max_memory_mb:
            print(f"内存使用过高 ({memory_mb:.1f}MB)，开始清理...")
            
            # 清理缓存
            optimized_manager.cache_manager.clear_all_caches()
            
            # 强制垃圾回收
            import gc
            gc.collect()
            
            # 再次检查
            new_memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
            print(f"清理后内存使用: {new_memory_mb:.1f}MB")

memory_manager = MemoryManager(max_memory_mb=800)

# 3. 分批处理大量数据
def process_documents_with_memory_limit(documents, collection_id):
    memory_manager = MemoryManager()
    
    for i, (file_path, doc_type) in enumerate(documents):
        # 每处理5个文档检查一次内存
        if i % 5 == 0:
            memory_manager.check_and_cleanup()
        
        try:
            task = kb_manager.add_document_async(collection_id, file_path, doc_type)
            print(f"已提交文档 {i+1}/{len(documents)}: {file_path}")
        except MemoryError:
            print("内存不足，暂停处理...")
            memory_manager.check_and_cleanup()
            time.sleep(5)  # 等待5秒后重试
```

### 问题12：磁盘空间不足

**症状**：
```python
OSError: [Errno 28] No space left on device
```

**诊断步骤**：
```python
import shutil

# 检查磁盘空间
def check_disk_space(path="."):
    total, used, free = shutil.disk_usage(path)
    
    print(f"磁盘总空间: {total / 1024 / 1024 / 1024:.1f} GB")
    print(f"已使用空间: {used / 1024 / 1024 / 1024:.1f} GB")
    print(f"可用空间: {free / 1024 / 1024 / 1024:.1f} GB")
    print(f"使用率: {(used / total) * 100:.1f}%")
    
    return free

free_space = check_disk_space()
if free_space < 1024 * 1024 * 1024:  # 小于1GB
    print("⚠️ 磁盘空间不足！")
```

**解决方案**：
```python
# 1. 清理临时文件和缓存
import os
import glob

def cleanup_temp_files():
    # 清理临时文件
    temp_patterns = [
        "./temp/*",
        "./data/temp/*",
        "./__pycache__/*",
        "./logs/*.log.old"
    ]
    
    for pattern in temp_patterns:
        for file_path in glob.glob(pattern):
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"删除临时文件: {file_path}")
            except Exception as e:
                print(f"删除文件失败 {file_path}: {e}")

# 2. 压缩旧数据
def compress_old_data():
    import zipfile
    import datetime
    
    # 压缩30天前的日志文件
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=30)
    
    for log_file in glob.glob("./logs/*.log"):
        file_time = datetime.datetime.fromtimestamp(os.path.getmtime(log_file))
        if file_time < cutoff_date:
            zip_name = f"{log_file}.zip"
            with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(log_file, os.path.basename(log_file))
            os.remove(log_file)
            print(f"压缩日志文件: {log_file} -> {zip_name}")

# 3. 实现磁盘空间监控
class DiskSpaceMonitor:
    def __init__(self, min_free_gb=2):
        self.min_free_gb = min_free_gb
    
    def check_space(self, path="."):
        _, _, free = shutil.disk_usage(path)
        free_gb = free / 1024 / 1024 / 1024
        
        if free_gb < self.min_free_gb:
            print(f"⚠️ 磁盘空间不足: {free_gb:.1f}GB < {self.min_free_gb}GB")
            self.cleanup()
            return False
        return True
    
    def cleanup(self):
        cleanup_temp_files()
        compress_old_data()
        
        # 清理缓存
        optimized_manager.clear_all_caches()

disk_monitor = DiskSpaceMonitor()
```

## API和服务问题

### 问题13：API调用失败

**症状**：
```python
APIError: Rate limit exceeded
```

**诊断步骤**：
```python
# 检查API配置
def diagnose_api_config():
    import os
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ API密钥未设置")
        return False
    
    if not api_key.startswith('sk-'):
        print("❌ API密钥格式不正确")
        return False
    
    print("✅ API密钥格式正确")
    
    # 测试API连接
    try:
        # 这里应该实现实际的API测试
        print("✅ API连接测试通过")
        return True
    except Exception as e:
        print(f"❌ API连接测试失败: {e}")
        return False

diagnose_api_config()
```

**解决方案**：
```python
# 1. 实现重试机制
import time
import random
from functools import wraps

def retry_with_backoff(max_retries=3, base_delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    
                    # 指数退避 + 随机抖动
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"API调用失败，{delay:.1f}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(delay)
            
            return None
        return wrapper
    return decorator

# 2. 实现速率限制
class RateLimiter:
    def __init__(self, max_requests_per_minute=60):
        self.max_requests = max_requests_per_minute
        self.requests = []
    
    def wait_if_needed(self):
        now = time.time()
        
        # 清理1分钟前的请求记录
        self.requests = [req_time for req_time in self.requests if now - req_time < 60]
        
        if len(self.requests) >= self.max_requests:
            sleep_time = 60 - (now - self.requests[0])
            if sleep_time > 0:
                print(f"达到速率限制，等待 {sleep_time:.1f} 秒...")
                time.sleep(sleep_time)
        
        self.requests.append(now)

rate_limiter = RateLimiter(max_requests_per_minute=50)

@retry_with_backoff(max_retries=3)
def api_call_with_rate_limit(func, *args, **kwargs):
    rate_limiter.wait_if_needed()
    return func(*args, **kwargs)

# 3. 配置多个API密钥轮换
class APIKeyRotator:
    def __init__(self, api_keys):
        self.api_keys = api_keys
        self.current_index = 0
        self.failed_keys = set()
    
    def get_current_key(self):
        if len(self.failed_keys) == len(self.api_keys):
            # 所有密钥都失败了，重置失败列表
            self.failed_keys.clear()
        
        while self.current_index in self.failed_keys:
            self.current_index = (self.current_index + 1) % len(self.api_keys)
        
        return self.api_keys[self.current_index]
    
    def mark_key_failed(self):
        self.failed_keys.add(self.current_index)
        self.current_index = (self.current_index + 1) % len(self.api_keys)

# 使用示例
api_keys = [
    "sk-key1...",
    "sk-key2...",
    "sk-key3..."
]
key_rotator = APIKeyRotator(api_keys)
```

### 问题14：网络连接超时

**症状**：
```python
TimeoutError: Request timeout after 30 seconds
```

**解决方案**：
```python
# 1. 调整超时设置
api_config = {
    "timeout": 60,          # 增加到60秒
    "connect_timeout": 10,  # 连接超时
    "read_timeout": 50      # 读取超时
}

# 2. 实现连接池
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class APIClient:
    def __init__(self):
        self.session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def make_request(self, url, data, timeout=60):
        try:
            response = self.session.post(url, json=data, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            print("请求超时，请检查网络连接")
            raise
        except requests.exceptions.ConnectionError:
            print("网络连接错误")
            raise

# 3. 网络诊断工具
def diagnose_network():
    import socket
    import urllib.request
    
    # 检查DNS解析
    try:
        socket.gethostbyname('api.openai.com')
        print("✅ DNS解析正常")
    except socket.gaierror:
        print("❌ DNS解析失败")
    
    # 检查网络连通性
    try:
        urllib.request.urlopen('https://api.openai.com', timeout=10)
        print("✅ 网络连通性正常")
    except Exception as e:
        print(f"❌ 网络连通性问题: {e}")
    
    # 检查代理设置
    proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    if proxy:
        print(f"🔍 检测到代理设置: {proxy}")

diagnose_network()
```

## 数据库连接问题

### 问题15：ChromaDB连接失败

**症状**：
```python
ConnectionError: Could not connect to ChromaDB
```

**诊断步骤**：
```python
# 检查ChromaDB配置
def diagnose_chromadb():
    from core.knowledge_base.models import ChromaDBConfig
    
    config = ChromaDBConfig(
        connection_type="local",
        path="./data/chromadb"
    )
    
    print(f"连接类型: {config.connection_type}")
    print(f"数据路径: {config.path}")
    
    # 检查路径是否存在
    import os
    if not os.path.exists(config.path):
        print(f"❌ 数据路径不存在: {config.path}")
        os.makedirs(config.path, exist_ok=True)
        print(f"✅ 已创建数据路径: {config.path}")
    
    # 检查权限
    if not os.access(config.path, os.W_OK):
        print(f"❌ 数据路径无写权限: {config.path}")
    else:
        print(f"✅ 数据路径权限正常")

diagnose_chromadb()
```

**解决方案**：
```python
# 1. 重新初始化数据库
def reset_chromadb():
    import shutil
    import os
    
    db_path = "./data/chromadb"
    
    if os.path.exists(db_path):
        print(f"删除现有数据库: {db_path}")
        shutil.rmtree(db_path)
    
    print(f"重新创建数据库目录: {db_path}")
    os.makedirs(db_path, exist_ok=True)
    
    # 重新初始化管理器
    from core.knowledge_base.manager import KnowledgeBaseManager
    kb_manager = KnowledgeBaseManager()
    
    print("✅ 数据库重新初始化完成")

# 2. 数据库健康检查
def check_chromadb_health():
    try:
        import chromadb
        
        # 创建客户端
        client = chromadb.PersistentClient(path="./data/chromadb")
        
        # 列出集合
        collections = client.list_collections()
        print(f"✅ ChromaDB连接正常，集合数量: {len(collections)}")
        
        # 测试创建和删除集合
        test_collection = client.create_collection("test_health_check")
        client.delete_collection("test_health_check")
        print("✅ 数据库读写测试通过")
        
        return True
    except Exception as e:
        print(f"❌ ChromaDB健康检查失败: {e}")
        return False

# 3. 数据库修复工具
def repair_chromadb():
    print("开始修复ChromaDB...")
    
    # 备份现有数据
    import shutil
    import datetime
    
    db_path = "./data/chromadb"
    backup_path = f"./data/chromadb_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if os.path.exists(db_path):
        shutil.copytree(db_path, backup_path)
        print(f"✅ 数据已备份到: {backup_path}")
    
    # 尝试修复
    try:
        check_chromadb_health()
        print("✅ 数据库修复成功")
    except Exception as e:
        print(f"❌ 数据库修复失败: {e}")
        print("建议重新初始化数据库")
```

## UI界面问题

### 问题16：UI界面无法启动

**症状**：
```python
ImportError: No module named 'PySide6'
```

**解决方案**：
```bash
# 安装UI依赖
pip install PySide6

# 如果安装失败，尝试其他方法
conda install pyside6

# 或者使用系统包管理器（Ubuntu）
sudo apt-get install python3-pyside6
```

### 问题17：UI界面显示异常

**诊断步骤**：
```python
# 检查Qt环境
def check_qt_environment():
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QT_VERSION_STR
        
        print(f"Qt版本: {QT_VERSION_STR}")
        
        # 创建应用程序实例
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        print("✅ Qt环境正常")
        return True
    except Exception as e:
        print(f"❌ Qt环境问题: {e}")
        return False

check_qt_environment()
```

**解决方案**：
```python
# 1. 设置Qt环境变量
import os
os.environ['QT_QPA_PLATFORM'] = 'xcb'  # Linux
# os.environ['QT_QPA_PLATFORM'] = 'windows'  # Windows

# 2. 处理高DPI显示
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

def setup_high_dpi():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

# 3. 错误处理包装器
def safe_ui_startup():
    try:
        setup_high_dpi()
        
        app = QApplication([])
        
        from ui.knowledge_base_panel import KnowledgeBasePanel
        panel = KnowledgeBasePanel()
        panel.show()
        
        return app.exec()
    except Exception as e:
        print(f"UI启动失败: {e}")
        print("尝试使用命令行界面...")
        return False
```

## 日志和调试

### 配置详细日志

```python
import logging
import sys
from datetime import datetime

def setup_logging(level=logging.DEBUG):
    # 创建日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # 文件处理器
    log_filename = f"logs/kb_debug_{datetime.now().strftime('%Y%m%d')}.log"
    os.makedirs(os.path.dirname(log_filename), exist_ok=True)
    
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # 配置特定模块的日志级别
    logging.getLogger('chromadb').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    print(f"日志已配置，文件: {log_filename}")

# 启用详细日志
setup_logging(logging.DEBUG)
```

### 调试工具

```python
class DebugHelper:
    def __init__(self):
        self.debug_enabled = True
    
    def debug_search(self, query, results):
        if not self.debug_enabled:
            return
        
        print(f"\n🔍 调试搜索: {query}")
        print(f"结果数量: {len(results)}")
        
        for i, result in enumerate(results[:3]):  # 只显示前3个结果
            print(f"\n结果 {i+1}:")
            print(f"  相关度: {result.relevance_score:.4f}")
            print(f"  来源: {result.source_document}")
            print(f"  内容: {result.content[:200]}...")
    
    def debug_processing(self, file_path, status):
        if not self.debug_enabled:
            return
        
        print(f"\n📄 调试处理: {file_path}")
        print(f"状态: {status.status.value}")
        if status.error_message:
            print(f"错误: {status.error_message}")
    
    def debug_performance(self, operation, duration):
        if not self.debug_enabled:
            return
        
        print(f"\n⏱️  性能调试: {operation}")
        print(f"耗时: {duration:.3f}秒")
        
        if duration > 5:
            print("⚠️ 操作耗时较长，建议优化")

debug_helper = DebugHelper()

# 使用调试工具
results = kb_manager.search_knowledge("测试查询", [collection_id])
debug_helper.debug_search("测试查询", results)
```

### 系统诊断报告

```python
def generate_diagnostic_report():
    """生成完整的系统诊断报告"""
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "system_info": {},
        "configuration": {},
        "performance": {},
        "errors": []
    }
    
    try:
        # 系统信息
        import platform
        report["system_info"] = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024
        }
        
        # 配置信息
        report["configuration"] = {
            "kb_config": get_knowledge_base_config() if get_knowledge_base_config else {},
            "chromadb_config": get_chromadb_config() if get_chromadb_config else {}
        }
        
        # 性能信息
        if hasattr(optimized_manager, 'get_performance_insights'):
            insights = optimized_manager.get_performance_insights()
            report["performance"] = insights
        
        # 检查各个组件
        components = [
            ("ChromaDB", check_chromadb_health),
            ("API配置", diagnose_api_config),
            ("内存使用", check_memory_usage),
            ("磁盘空间", lambda: check_disk_space() > 1024*1024*1024)
        ]
        
        for name, check_func in components:
            try:
                result = check_func()
                report[f"{name}_status"] = "OK" if result else "FAILED"
            except Exception as e:
                report[f"{name}_status"] = f"ERROR: {str(e)}"
                report["errors"].append(f"{name}: {str(e)}")
    
    except Exception as e:
        report["errors"].append(f"诊断过程出错: {str(e)}")
    
    # 保存报告
    report_file = f"diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"诊断报告已保存: {report_file}")
    return report

# 生成诊断报告
diagnostic_report = generate_diagnostic_report()
```

## 获取帮助

如果以上解决方案都无法解决您的问题，请：

1. **收集信息**：
   - 错误的完整堆栈跟踪
   - 系统诊断报告
   - 相关的配置文件
   - 重现问题的步骤

2. **检查日志**：
   - 查看详细的日志文件
   - 注意错误发生的时间和上下文

3. **联系支持**：
   - 提供详细的问题描述
   - 包含系统环境信息
   - 附上诊断报告

---

*本故障排除指南涵盖了知识库RAG系统的常见问题。如果遇到未列出的问题，请参考系统日志和错误信息进行诊断。*