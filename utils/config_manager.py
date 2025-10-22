import configparser
import os
from typing import Dict, Optional, Any
import sys

def safe_read_config(config: configparser.ConfigParser, config_path: str) -> bool:
    """
    安全地读取配置文件，处理编码问题
    
    Args:
        config: ConfigParser实例
        config_path: 配置文件路径
        
    Returns:
        bool: 是否成功读取
    """
    try:
        # 首先尝试UTF-8编码
        config.read(config_path, encoding='utf-8')
        return True
    except UnicodeDecodeError:
        try:
            # 如果UTF-8失败，尝试GBK编码
            config.read(config_path, encoding='gbk')
            return True
        except UnicodeDecodeError:
            try:
                # 最后尝试系统默认编码
                config.read(config_path)
                return True
            except Exception as e:
                print(f"Error reading config file {config_path}: {e}")
                return False
    except Exception as e:
        print(f"Error reading config file {config_path}: {e}")
        return False

def get_config_path() -> str:
    """
    获取 config.ini 的绝对路径，智能适应开发环境和 PyInstaller 打包环境。
    - 在打包后的 .exe 环境中，它会寻找与 .exe同目录的 config.ini。
    - 在开发环境中（直接运行 .py），它会根据您原来的逻辑，寻找上级目录的 config.ini。
    """
    if getattr(sys, 'frozen', False):
        # 如果是 PyInstaller 打包的 .exe
        # sys.executable 是 .exe 文件的绝对路径
        base_path = os.path.dirname(sys.executable)
        # 假设 config.ini 与 exe 文件在同一目录下
        return os.path.join(base_path, 'config.ini')
    else:
        # 如果是直接运行 .py 文件
        # __file__ 是当前脚本的绝对路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 沿用您原来的逻辑，配置文件在上一级目录
        return os.path.abspath(os.path.join(script_dir, '..', 'config.ini'))

def get_app_config():
    """
    Reads the application configuration from the config.ini file.
    
    Returns:
        dict: A dictionary containing application configuration details.
    """
    config = configparser.ConfigParser()
    config_path = get_config_path()
    
    if not os.path.exists(config_path):
        print(f"Error: config.ini not found at {config_path}")
        return {}
        
    if not safe_read_config(config, config_path):
        print(f"Error: Failed to read config.ini at {config_path}")
        return {}
    
    # Get app settings with defaults
    if 'app' not in config:
        config.add_section('app')
    
    screen_number = config.getint('app', 'screen_number', fallback=1)
    
    return {
        'screen_number': screen_number
    }

def save_app_config(config_data):
    """
    Saves application configuration to the config.ini file.
    
    Args:
        config_data (dict): A dictionary containing application configuration details.
    """
    config = configparser.ConfigParser()
    config_path = get_config_path()
    
    if os.path.exists(config_path):
        config.read(config_path)
    
    if 'app' not in config:
        config.add_section('app')
    
    # Update app settings
    if 'screen_number' in config_data:
        config.set('app', 'screen_number', str(config_data['screen_number']))
    
    # Write to file
    with open(config_path, 'w') as configfile:
        config.write(configfile)

def get_model_config(service_type):
    """
    Reads the model configuration from the config.ini file for a specific service.

    Args:
        service_type (str): The type of service, either 'vlm' or 'llm'.

    Returns:
        dict: A dictionary containing model configuration details.
              Returns None if the section is not found or a required key is missing.
    """
    if service_type not in ['vlm', 'llm']:
        raise ValueError("service_type must be either 'vlm' or 'llm'")

    config = configparser.ConfigParser()
    config_path = get_config_path()
    
    if not os.path.exists(config_path):
        print(f"Error: config.ini not found at {config_path}")
        return None
        
    if not safe_read_config(config, config_path):
        print(f"Error: Failed to read config.ini at {config_path}")
        return None

    if service_type not in config:
        print(f"Error: Section [{service_type}] not found in config.ini.")
        return None

    api_key = config.get(service_type, 'api_key', fallback=None)
    model_name = config.get(service_type, 'model_name', fallback=None)
    base_url = config.get(service_type, 'base_url', fallback=None)
    proxy = config.get(service_type, 'proxy', fallback=None)
    llm_provider = None
    google_api_key = None
    if service_type == 'llm':
        llm_provider = config.get('llm', 'llm_provider', fallback='gemini')
        google_api_key = config.get('llm', 'google_api_key', fallback=None)

    # Treat an empty string for base_url or proxy as None
    if base_url is not None and not base_url.strip():
        base_url = None
    if proxy is not None and not proxy.strip():
        proxy = None

    if not api_key or f'YOUR_{service_type.upper()}_API_KEY_HERE' in api_key:
        print(f"Error: API key for [{service_type}] not set in config.ini.")
        return None
    
    if not model_name:
        print(f"Error: model_name for [{service_type}] not set in config.ini.")
        return None

    config_data = {
        'api_key': api_key,
        'model_name': model_name,
        'base_url': base_url,
        'proxy': proxy
    }

    if llm_provider:
        config_data['llm_provider'] = llm_provider
    if google_api_key:
        config_data['google_api_key'] = google_api_key

    return config_data


def get_knowledge_base_config() -> Optional[Dict[str, Any]]:
    """
    Reads the knowledge base configuration from the config.ini file.
    
    Returns:
        dict: A dictionary containing knowledge base configuration details.
              Returns None if the section is not found.
    """
    config = configparser.ConfigParser()
    config_path = get_config_path()
    
    if not os.path.exists(config_path):
        print(f"Error: config.ini not found at {config_path}")
        return None
        
    config.read(config_path)
    
    if 'knowledge_base' not in config:
        print("Warning: [knowledge_base] section not found in config.ini. Using defaults.")
        return {
            'enabled': False,
            'storage_path': './data/knowledge_base',
            'max_file_size_mb': 100,
            'chunk_size': 1000,
            'chunk_overlap': 200,
            'max_collections': 50,
            'background_processing': True,
            'max_concurrent_tasks': 3
        }
    
    return {
        'enabled': config.getboolean('knowledge_base', 'enabled', fallback=False),
        'storage_path': config.get('knowledge_base', 'storage_path', fallback='./data/knowledge_base'),
        'max_file_size_mb': config.getint('knowledge_base', 'max_file_size_mb', fallback=100),
        'chunk_size': config.getint('knowledge_base', 'chunk_size', fallback=1000),
        'chunk_overlap': config.getint('knowledge_base', 'chunk_overlap', fallback=200),
        'max_collections': config.getint('knowledge_base', 'max_collections', fallback=50),
        'background_processing': config.getboolean('knowledge_base', 'background_processing', fallback=True),
        'max_concurrent_tasks': config.getint('knowledge_base', 'max_concurrent_tasks', fallback=3)
    }


def get_chromadb_config() -> Optional[Dict[str, Any]]:
    """
    Reads the ChromaDB configuration from the config.ini file.
    
    Returns:
        dict: A dictionary containing ChromaDB configuration details.
              Returns None if the section is not found.
    """
    config = configparser.ConfigParser()
    config_path = get_config_path()
    
    if not os.path.exists(config_path):
        print(f"Error: config.ini not found at {config_path}")
        return None
        
    config.read(config_path)
    
    if 'chromadb' not in config:
        print("Warning: [chromadb] section not found in config.ini. Using local defaults.")
        return {
            'connection_type': 'local',
            'host': None,
            'port': None,
            'path': './data/chromadb',
            'auth_token': None,
            'ssl_enabled': False
        }
    
    connection_type = config.get('chromadb', 'connection_type', fallback='local')
    host = config.get('chromadb', 'host', fallback=None)
    port_str = config.get('chromadb', 'port', fallback='')
    port = config.getint('chromadb', 'port', fallback=8000) if port_str else 8000
    path = config.get('chromadb', 'path', fallback='./data/chromadb')
    auth_token = config.get('chromadb', 'auth_token', fallback=None)
    ssl_enabled = config.getboolean('chromadb', 'ssl_enabled', fallback=False)
    
    # Clean up empty strings
    if host is not None and not host.strip():
        host = None
    if auth_token is not None and not auth_token.strip():
        auth_token = None
    
    return {
        'connection_type': connection_type,
        'host': host,
        'port': port,
        'path': path,
        'auth_token': auth_token,
        'ssl_enabled': ssl_enabled
    }


def get_api_config(api_type: str) -> Optional[Dict[str, Any]]:
    """
    Reads the API configuration from the config.ini file for embedding or reranker APIs.
    
    Args:
        api_type (str): The type of API, either 'embedding_api' or 'reranker_api'.
    
    Returns:
        dict: A dictionary containing API configuration details.
              Returns None if the section is not found or required keys are missing.
    """
    if api_type not in ['embedding_api', 'reranker_api']:
        raise ValueError("api_type must be either 'embedding_api' or 'reranker_api'")
    
    config = configparser.ConfigParser()
    config_path = get_config_path()
    
    if not os.path.exists(config_path):
        print(f"Error: config.ini not found at {config_path}")
        return None
        
    config.read(config_path)
    
    if api_type not in config:
        print(f"Error: Section [{api_type}] not found in config.ini.")
        return None
    
    endpoint = config.get(api_type, 'endpoint', fallback=None)
    api_key = config.get(api_type, 'api_key', fallback=None)
    model = config.get(api_type, 'model', fallback=None)
    timeout = config.getint(api_type, 'timeout', fallback=30)
    
    if not endpoint or not endpoint.strip():
        print(f"Error: endpoint for [{api_type}] not set in config.ini.")
        return None
    
    if not api_key or 'your_' in api_key.lower() or 'api_key_here' in api_key.lower():
        print(f"Error: API key for [{api_type}] not set in config.ini.")
        return None
    
    if not model or not model.strip():
        print(f"Error: model for [{api_type}] not set in config.ini.")
        return None
    
    return {
        'endpoint': endpoint,
        'api_key': api_key,
        'model': model,
        'timeout': timeout
    }


def get_embedding_api_config() -> Optional[Dict[str, Any]]:
    """
    Reads the embedding API configuration from the config.ini file.
    
    Returns:
        dict: A dictionary containing embedding API configuration details.
    """
    return get_api_config('embedding_api')


def get_reranker_api_config() -> Optional[Dict[str, Any]]:
    """
    Reads the reranker API configuration from the config.ini file.
    
    Returns:
        dict: A dictionary containing reranker API configuration details.
    """
    return get_api_config('reranker_api')


def get_backend_config() -> Dict[str, Any]:
    """
    Reads the backend configuration from the config.ini file.
    
    Returns:
        dict: A dictionary containing backend configuration details.
    """
    config = configparser.ConfigParser()
    config_path = get_config_path()
    
    if not os.path.exists(config_path):
        print(f"Error: config.ini not found at {config_path}")
        return {
            'base_url': 'http://localhost:8000',
            'enable_history': False,
            'user_id': ''
        }
        
    if not safe_read_config(config, config_path):
        print(f"Error: Failed to read config.ini at {config_path}")
        return {
            'base_url': 'http://localhost:8000',
            'enable_history': False,
            'user_id': ''
        }
    
    if 'backend' not in config:
        print("Warning: [backend] section not found in config.ini. Using defaults.")
        return {
            'base_url': 'http://localhost:8000',
            'enable_history': False,
            'user_id': ''
        }
    
    return {
        'base_url': config.get('backend', 'base_url', fallback='http://localhost:8000'),
        'enable_history': config.getboolean('backend', 'enable_history', fallback=False),
        'user_id': config.get('backend', 'user_id', fallback='')
    }


def save_backend_config(config_data: Dict[str, Any]):
    """
    Saves backend configuration to the config.ini file.
    
    Args:
        config_data (dict): A dictionary containing backend configuration details.
    """
    config = configparser.ConfigParser()
    config_path = get_config_path()
    
    if os.path.exists(config_path):
        safe_read_config(config, config_path)
    
    if 'backend' not in config:
        config.add_section('backend')
    
    # Update backend settings
    for key, value in config_data.items():
        if isinstance(value, bool):
            config.set('backend', key, str(value).lower())
        else:
            config.set('backend', key, str(value))
    
    # Write to file with UTF-8 encoding
    with open(config_path, 'w', encoding='utf-8') as configfile:
        config.write(configfile)


def save_knowledge_base_config(config_data: Dict[str, Any]):
    """
    Saves knowledge base configuration to the config.ini file.
    
    Args:
        config_data (dict): A dictionary containing knowledge base configuration details.
    """
    print("📄 [配置管理器] 开始保存知识库配置到 config.ini")
    print(f"📝 [配置管理器] 接收到的配置数据: {config_data}")
    
    config = configparser.ConfigParser()
    config_path = get_config_path()
    print(f"📂 [配置管理器] 配置文件路径: {config_path}")
    
    if os.path.exists(config_path):
        print("📖 [配置管理器] 读取现有配置文件...")
        config.read(config_path)
    else:
        print("🆕 [配置管理器] 配置文件不存在，将创建新文件")
    
    if 'knowledge_base' not in config:
        print("➕ [配置管理器] 添加 [knowledge_base] 配置节")
        config.add_section('knowledge_base')
    else:
        print("✅ [配置管理器] [knowledge_base] 配置节已存在")
    
    # Update knowledge base settings
    print("🔄 [配置管理器] 更新知识库设置...")
    for key, value in config_data.items():
        # Convert boolean values to lowercase strings for INI format
        if isinstance(value, bool):
            str_value = str(value).lower()
            print(f"   - {key}: {value} -> {str_value} (布尔值转换)")
            config.set('knowledge_base', key, str_value)
        else:
            print(f"   - {key}: {value}")
            config.set('knowledge_base', key, str(value))
    
    # Write to file
    print("💾 [配置管理器] 写入配置文件...")
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    
    print("✅ [配置管理器] 知识库配置保存完成")


def save_chromadb_config(config_data: Dict[str, Any]):
    """
    Saves ChromaDB configuration to the config.ini file.
    
    Args:
        config_data (dict): A dictionary containing ChromaDB configuration details.
    """
    config = configparser.ConfigParser()
    config_path = get_config_path()
    
    if os.path.exists(config_path):
        config.read(config_path)
    
    if 'chromadb' not in config:
        config.add_section('chromadb')
    
    # Update ChromaDB settings
    for key, value in config_data.items():
        if value is not None:
            config.set('chromadb', key, str(value))
        else:
            config.set('chromadb', key, '')
    
    # Write to file
    with open(config_path, 'w') as configfile:
        config.write(configfile)


def save_embedding_api_config(config_data: Dict[str, Any]):
    """
    Saves embedding API configuration to the config.ini file.
    
    Args:
        config_data (dict): A dictionary containing embedding API configuration details.
    """
    save_api_config('embedding_api', config_data)


def save_reranker_api_config(config_data: Dict[str, Any]):
    """
    Saves reranker API configuration to the config.ini file.
    
    Args:
        config_data (dict): A dictionary containing reranker API configuration details.
    """
    save_api_config('reranker_api', config_data)


def save_api_config(api_type: str, config_data: Dict[str, Any]):
    """
    Saves API configuration to the config.ini file.
    
    Args:
        api_type (str): The type of API, either 'embedding_api' or 'reranker_api'.
        config_data (dict): A dictionary containing API configuration details.
    """
    if api_type not in ['embedding_api', 'reranker_api']:
        raise ValueError("api_type must be either 'embedding_api' or 'reranker_api'")
    
    config = configparser.ConfigParser()
    config_path = get_config_path()
    
    if os.path.exists(config_path):
        config.read(config_path)
    
    if api_type not in config:
        config.add_section(api_type)
    
    # Update API settings
    for key, value in config_data.items():
        if value is not None:
            config.set(api_type, key, str(value))
        else:
            config.set(api_type, key, '')
    
    # Write to file
    with open(config_path, 'w') as configfile:
        config.write(configfile)


def validate_knowledge_base_config() -> bool:
    """
    Validates the knowledge base configuration.
    
    Returns:
        bool: True if configuration is valid, False otherwise.
    """
    kb_config = get_knowledge_base_config()
    if not kb_config:
        return False
    
    if not kb_config['enabled']:
        return True  # If disabled, no need to validate further
    
    # Check if storage path is accessible
    storage_path = kb_config['storage_path']
    try:
        os.makedirs(storage_path, exist_ok=True)
    except Exception as e:
        print(f"Error: Cannot create storage path {storage_path}: {e}")
        return False
    
    # Validate ChromaDB config
    chromadb_config = get_chromadb_config()
    if not chromadb_config:
        return False
    
    if chromadb_config['connection_type'] == 'local':
        # Check if local path is accessible
        db_path = chromadb_config['path']
        try:
            os.makedirs(db_path, exist_ok=True)
        except Exception as e:
            print(f"Error: Cannot create ChromaDB path {db_path}: {e}")
            return False
    
    return True