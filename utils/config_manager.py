import configparser
import os

def get_model_config(service_type):
    """
    Reads the model configuration from the config.ini file for a specific service.

    Args:
        service_type (str): The type of service, either 'vlm' or 'llm'.

    Returns:
        dict: A dictionary containing 'api_key', 'model_name', 'base_url', 'proxy', and optionally 'llm_provider'.
               Returns None if the section is not found or key is missing.
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
    if service_type == 'llm':
        llm_provider = config.get('llm', 'llm_provider', fallback='gemini')

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

    return config_data