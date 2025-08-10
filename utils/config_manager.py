import configparser
import os
from typing import Dict, Optional, Any

def get_app_config():
    """
    Reads the application configuration from the config.ini file.
    
    Returns:
        dict: A dictionary containing application configuration details.
    """
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    
    if not os.path.exists(config_path):
        print(f"Error: config.ini not found at {config_path}")
        return {}
        
    config.read(config_path)
    
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
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    
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
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    
    if not os.path.exists(config_path):
        print(f"Error: config.ini not found at {config_path}")
        return None
        
    config.read(config_path)

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
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    
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
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    
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
    port = config.getint('chromadb', 'port', fallback=None) if config.get('chromadb', 'port', fallback='') else None
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
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    
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


def save_knowledge_base_config(config_data: Dict[str, Any]):
    """
    Saves knowledge base configuration to the config.ini file.
    
    Args:
        config_data (dict): A dictionary containing knowledge base configuration details.
    """
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    
    if os.path.exists(config_path):
        config.read(config_path)
    
    if 'knowledge_base' not in config:
        config.add_section('knowledge_base')
    
    # Update knowledge base settings
    for key, value in config_data.items():
        config.set('knowledge_base', key, str(value))
    
    # Write to file
    with open(config_path, 'w') as configfile:
        config.write(configfile)


def save_chromadb_config(config_data: Dict[str, Any]):
    """
    Saves ChromaDB configuration to the config.ini file.
    
    Args:
        config_data (dict): A dictionary containing ChromaDB configuration details.
    """
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    
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
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    
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