"""
ChromaDB 查询 API 端点
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List
import chromadb
from chromadb.config import Settings
from pydantic import BaseModel
import configparser
import os
import requests

router = APIRouter(prefix="/api/chromadb", tags=["chromadb"])


class QueryRequest(BaseModel):
    collection_name: str
    query_text: str
    n_results: int = 10


class QueryResult(BaseModel):
    id: str
    document: str
    metadata: dict
    distance: float


def get_config():
    """读取配置文件"""
    config = configparser.ConfigParser()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 尝试多个可能的配置文件路径
    config_paths = [
        'config.ini',  # 当前工作目录
        os.path.join(os.getcwd(), 'config.ini'),  # 明确的工作目录
        os.path.join(current_dir, '..', '..', 'config.ini'),  # web/backend/config.ini
        os.path.join(current_dir, '..', '..', '..', 'config.ini'),  # 项目根目录
        os.path.join(current_dir, '..', '..', '..', '..', 'config.ini'),  # 再上一级
    ]
    
    for config_path in config_paths:
        abs_path = os.path.abspath(config_path)
        if os.path.exists(abs_path):
            try:
                config.read(abs_path, encoding='utf-8')
                print(f"✓ 成功加载配置文件: {abs_path}")
                return config, abs_path
            except Exception as e:
                print(f"✗ 读取配置文件失败 {abs_path}: {e}")
                continue
    
    print("✗ 未找到配置文件")
    return config, None


def get_embedding_function():
    """根据配置文件获取 embedding 函数"""
    config, config_path = get_config()
    
    if not config_path:
    
    if 'embedding_api' not in config:
        return None
    
    endpoint = config.get('embedding_api', 'endpoint', fallback=None)
    api_key = config.get('embedding_api', 'api_key', fallback=None)
    model = config.get('embedding_api', 'model', fallback=None)
    
    if not all([endpoint, api_key, model]):
        return None
    
    # 创建自定义 embedding 函数
    class CustomEmbeddingFunction:
        def __init__(self, endpoint, api_key, model):
            self.endpoint = endpoint
            self.api_key = api_key
            self.model = model
        
        def __call__(self, input):
            """生成 embeddings"""
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # 确保 input 是列表
            if isinstance(input, str):
                texts = [input]
            else:
                texts = input
            
            payload = {
                'model': self.model,
                'input': texts,
                'encoding_format': 'float'
            }
            
            try:
                response = requests.post(self.endpoint, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                # 提取 embeddings
                embeddings = [item['embedding'] for item in data['data']]
                return embeddings
            except Exception as e:
                raise Exception(f"Embedding API 调用失败: {str(e)}")
    
    return CustomEmbeddingFunction(endpoint, api_key, model)


def get_chromadb_client():
    """根据配置文件获取 ChromaDB 客户端"""
    config, config_path = get_config()
    
    if not config_path or 'chromadb' not in config:
        # 默认使用本地连接
        print("未找到配置文件或配置不完整，使用默认本地连接")
        return chromadb.PersistentClient(path="./data/chromadb")
    
    connection_type = config.get('chromadb', 'connection_type', fallback='local')
    
    if connection_type == 'remote':
        host = config.get('chromadb', 'host', fallback='localhost')
        port = config.getint('chromadb', 'port', fallback=8000)
        ssl_enabled = config.getboolean('chromadb', 'ssl_enabled', fallback=False)
        auth_token = config.get('chromadb', 'auth_token', fallback=None)
        
        # 构建远程连接URL
        protocol = 'https' if ssl_enabled else 'http'
        url = f"{protocol}://{host}:{port}"
        
        # 创建远程客户端
        settings = Settings(
            chroma_api_impl="chromadb.api.fastapi.FastAPI",
            chroma_server_host=host,
            chroma_server_http_port=port,
            chroma_server_ssl_enabled=ssl_enabled,
        )
        
        # 如果有认证令牌，添加到headers
        headers = {}
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'
            headers['X-Chroma-Token'] = auth_token
        
        try:
            client = chromadb.HttpClient(
                host=host,
                port=port,
                ssl=ssl_enabled,
                headers=headers
            )
            return client
        except Exception as e:
            raise Exception(f"无法连接到远程 ChromaDB 服务器 {url}: {str(e)}")
    else:
        # 本地连接
        path = config.get('chromadb', 'path', fallback='./data/chromadb')
        return chromadb.PersistentClient(path=path)


@router.get("/config")
async def get_config_info():
    """获取 ChromaDB 配置信息（用于调试）"""
    config, found_path = get_config()
    
    result = {
        "config_file": found_path or "未找到",
        "working_directory": os.getcwd()
    }
    if found_path and config.has_section('chromadb'):
        result.update({
            "chromadb": {
                "connection_type": config.get('chromadb', 'connection_type', fallback='local'),
                "host": config.get('chromadb', 'host', fallback='N/A'),
                "port": config.get('chromadb', 'port', fallback='N/A'),
                "ssl_enabled": config.get('chromadb', 'ssl_enabled', fallback='N/A'),
                "path": config.get('chromadb', 'path', fallback='N/A')
            }
        })
    if found_path and config.has_section('embedding_api'):
        result["embedding_api"] = {
            "endpoint": config.get('embedding_api', 'endpoint', fallback='N/A'),
            "model": config.get('embedding_api', 'model', fallback='N/A'),
            "configured": True
        }
    else:
        result["embedding_api"] = {"configured": False}
    
    if not found_path:
        result["error"] = "配置文件未找到"
    
    return result


@router.get("/collections")
async def get_collections():
    """获取所有集合列表"""
    try:
        client = get_chromadb_client()
        collections = client.list_collections()
        
        collection_info = []
        for col in collections:
            collection_info.append({
                "name": col.name,
                "count": col.count(),
                "metadata": col.metadata
            })
        
        return {"collections": collection_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取集合列表失败: {str(e)}")


@router.post("/query")
async def query_collection(request: QueryRequest):
    """查询集合"""
    try:
        client = get_chromadb_client()
        embedding_function = get_embedding_function()
        
        # 获取集合
        try:
            if embedding_function:
                collection = client.get_collection(
                    name=request.collection_name,
                    embedding_function=embedding_function
                )
            else:
                collection = client.get_collection(name=request.collection_name)
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"集合 '{request.collection_name}' 不存在: {str(e)}")
        
        # 执行查询
        try:
            results = collection.query(
                query_texts=[request.query_text],
                n_results=request.n_results
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
        
        # 格式化结果
        formatted_results = []
        if results['ids'] and len(results['ids']) > 0:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    "id": results['ids'][0][i],
                    "document": results['documents'][0][i] if results['documents'] else "",
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else 0.0
                })
        
        return {
            "collection": request.collection_name,
            "query": request.query_text,
            "results": formatted_results,
            "total": len(formatted_results)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/collection/{collection_name}/sample")
async def get_collection_sample(collection_name: str, limit: int = 5):
    """获取集合的示例数据"""
    try:
        client = get_chromadb_client()
        
        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            raise HTTPException(status_code=404, detail=f"集合 '{collection_name}' 不存在")
        
        # 获取前N条数据
        results = collection.get(limit=limit)
        
        samples = []
        if results['ids']:
            for i in range(len(results['ids'])):
                samples.append({
                    "id": results['ids'][i],
                    "document": results['documents'][i] if results['documents'] else "",
                    "metadata": results['metadatas'][i] if results['metadatas'] else {}
                })
        
        return {
            "collection": collection_name,
            "samples": samples,
            "total_count": collection.count()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取示例数据失败: {str(e)}")
