# API配置示例

本文档提供了知识库RAG系统与各种AI服务提供商集成的配置示例。

## 目录

- [OpenAI配置](#openai配置)
- [Azure OpenAI配置](#azure-openai配置)
- [Google AI配置](#google-ai配置)
- [Anthropic配置](#anthropic配置)
- [本地模型配置](#本地模型配置)
- [自定义API配置](#自定义api配置)
- [环境变量配置](#环境变量配置)
- [配置验证](#配置验证)

## OpenAI配置

### 基本配置

```python
# config/ai_services.py
OPENAI_CONFIG = {
    "provider": "openai",
    "api_key": "sk-your-api-key-here",
    "model": "gpt-3.5-turbo",
    "embedding_model": "text-embedding-ada-002",
    "max_tokens": 2000,
    "temperature": 0.7,
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": 1.0
}

# 使用配置
from core import ai_services

ai_services.configure_openai(OPENAI_CONFIG)
```

### 高级配置

```python
OPENAI_ADVANCED_CONFIG = {
    "provider": "openai",
    "api_key": "sk-your-api-key-here",
    "organization": "org-your-org-id",  # 可选
    "model": "gpt-4",
    "embedding_model": "text-embedding-ada-002",
    "max_tokens": 4000,
    "temperature": 0.3,
    "top_p": 0.9,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
    "timeout": 60,
    "max_retries": 5,
    "retry_delay": 2.0,
    "request_timeout": 30,
    "rate_limit": {
        "requests_per_minute": 60,
        "tokens_per_minute": 90000
    },
    "proxy": {
        "http": "http://proxy.example.com:8080",
        "https": "https://proxy.example.com:8080"
    }
}
```

### 环境变量方式

```bash
# .env 文件
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_ORGANIZATION=org-your-org-id
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002
OPENAI_MAX_TOKENS=2000
OPENAI_TEMPERATURE=0.7
```

```python
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_CONFIG = {
    "provider": "openai",
    "api_key": os.getenv("OPENAI_API_KEY"),
    "organization": os.getenv("OPENAI_ORGANIZATION"),
    "model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
    "embedding_model": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002"),
    "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "2000")),
    "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
}
```

## Azure OpenAI配置

### 基本配置

```python
AZURE_OPENAI_CONFIG = {
    "provider": "azure_openai",
    "api_key": "your-azure-api-key",
    "azure_endpoint": "https://your-resource.openai.azure.com/",
    "api_version": "2023-12-01-preview",
    "deployment_name": "gpt-35-turbo",
    "embedding_deployment": "text-embedding-ada-002",
    "max_tokens": 2000,
    "temperature": 0.7,
    "timeout": 30
}

# 使用配置
ai_services.configure_azure_openai(AZURE_OPENAI_CONFIG)
```

### 完整配置

```python
AZURE_OPENAI_FULL_CONFIG = {
    "provider": "azure_openai",
    "api_key": "your-azure-api-key",
    "azure_endpoint": "https://your-resource.openai.azure.com/",
    "api_version": "2023-12-01-preview",
    "deployment_name": "gpt-4",
    "embedding_deployment": "text-embedding-ada-002",
    "max_tokens": 4000,
    "temperature": 0.3,
    "top_p": 0.9,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
    "timeout": 60,
    "max_retries": 3,
    "retry_delay": 1.0,
    "azure_ad_token": None,  # 如果使用Azure AD认证
    "azure_ad_token_provider": None,
    "headers": {
        "User-Agent": "KnowledgeBase-RAG/1.0"
    }
}
```

### 环境变量配置

```bash
# .env 文件
AZURE_OPENAI_API_KEY=your-azure-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2023-12-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-35-turbo
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
```

## Google AI配置

### Gemini配置

```python
GOOGLE_AI_CONFIG = {
    "provider": "google_ai",
    "api_key": "your-google-ai-api-key",
    "model": "gemini-pro",
    "embedding_model": "embedding-001",
    "max_tokens": 2048,
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 40,
    "timeout": 30,
    "safety_settings": [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        }
    ]
}

# 使用配置
ai_services.configure_google_ai(GOOGLE_AI_CONFIG)
```

### Vertex AI配置

```python
VERTEX_AI_CONFIG = {
    "provider": "vertex_ai",
    "project_id": "your-gcp-project-id",
    "location": "us-central1",
    "credentials_path": "/path/to/service-account.json",
    "model": "gemini-pro",
    "embedding_model": "textembedding-gecko",
    "max_tokens": 2048,
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 40
}
```

## Anthropic配置

### Claude配置

```python
ANTHROPIC_CONFIG = {
    "provider": "anthropic",
    "api_key": "your-anthropic-api-key",
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 4000,
    "temperature": 0.7,
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": 1.0,
    "system_prompt": "You are a helpful AI assistant with access to a knowledge base."
}

# 使用配置
ai_services.configure_anthropic(ANTHROPIC_CONFIG)
```

### 高级配置

```python
ANTHROPIC_ADVANCED_CONFIG = {
    "provider": "anthropic",
    "api_key": "your-anthropic-api-key",
    "model": "claude-3-opus-20240229",
    "max_tokens": 4000,
    "temperature": 0.3,
    "top_p": 0.9,
    "top_k": 250,
    "timeout": 60,
    "max_retries": 5,
    "retry_delay": 2.0,
    "system_prompt": "You are an expert AI assistant...",
    "stop_sequences": ["Human:", "Assistant:"],
    "headers": {
        "anthropic-version": "2023-06-01"
    }
}
```

## 本地模型配置

### Ollama配置

```python
OLLAMA_CONFIG = {
    "provider": "ollama",
    "base_url": "http://localhost:11434",
    "model": "llama2",
    "embedding_model": "nomic-embed-text",
    "timeout": 120,
    "stream": False,
    "options": {
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40,
        "repeat_penalty": 1.1,
        "num_ctx": 4096
    }
}

# 使用配置
ai_services.configure_ollama(OLLAMA_CONFIG)
```

### LM Studio配置

```python
LM_STUDIO_CONFIG = {
    "provider": "lm_studio",
    "base_url": "http://localhost:1234/v1",
    "api_key": "not-needed",
    "model": "local-model",
    "embedding_model": "local-embedding-model",
    "max_tokens": 2000,
    "temperature": 0.7,
    "timeout": 60
}
```

### vLLM配置

```python
VLLM_CONFIG = {
    "provider": "vllm",
    "base_url": "http://localhost:8000/v1",
    "api_key": "token-abc123",
    "model": "meta-llama/Llama-2-7b-chat-hf",
    "max_tokens": 2000,
    "temperature": 0.7,
    "top_p": 0.9,
    "timeout": 60
}
```

## 自定义API配置

### 通用REST API配置

```python
CUSTOM_API_CONFIG = {
    "provider": "custom",
    "base_url": "https://api.example.com/v1",
    "api_key": "your-custom-api-key",
    "model": "custom-model",
    "embedding_model": "custom-embedding-model",
    "headers": {
        "Authorization": "Bearer your-token",
        "Content-Type": "application/json",
        "User-Agent": "KnowledgeBase-RAG/1.0"
    },
    "endpoints": {
        "chat": "/chat/completions",
        "embeddings": "/embeddings"
    },
    "request_format": {
        "chat": {
            "model": "{model}",
            "messages": "{messages}",
            "max_tokens": "{max_tokens}",
            "temperature": "{temperature}"
        },
        "embeddings": {
            "model": "{embedding_model}",
            "input": "{input}"
        }
    },
    "response_format": {
        "chat": "choices[0].message.content",
        "embeddings": "data[0].embedding"
    },
    "timeout": 30,
    "max_retries": 3
}
```

### 自定义处理器

```python
class CustomAPIHandler:
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(config.get("headers", {}))
    
    def generate_response(self, messages, **kwargs):
        """生成聊天响应"""
        url = f"{self.config['base_url']}{self.config['endpoints']['chat']}"
        
        payload = {
            "model": self.config["model"],
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 2000),
            "temperature": kwargs.get("temperature", 0.7)
        }
        
        response = self.session.post(url, json=payload, timeout=self.config["timeout"])
        response.raise_for_status()
        
        return response.json()["choices"][0]["message"]["content"]
    
    def generate_embeddings(self, texts):
        """生成嵌入向量"""
        url = f"{self.config['base_url']}{self.config['endpoints']['embeddings']}"
        
        payload = {
            "model": self.config["embedding_model"],
            "input": texts
        }
        
        response = self.session.post(url, json=payload, timeout=self.config["timeout"])
        response.raise_for_status()
        
        return [item["embedding"] for item in response.json()["data"]]

# 注册自定义处理器
ai_services.register_custom_handler("custom", CustomAPIHandler(CUSTOM_API_CONFIG))
```

## 环境变量配置

### 统一环境变量

```bash
# .env 文件 - 统一配置
AI_PROVIDER=openai
AI_API_KEY=your-api-key
AI_MODEL=gpt-3.5-turbo
AI_EMBEDDING_MODEL=text-embedding-ada-002
AI_MAX_TOKENS=2000
AI_TEMPERATURE=0.7
AI_TIMEOUT=30
AI_MAX_RETRIES=3

# OpenAI特定配置
OPENAI_ORGANIZATION=org-your-org-id

# Azure OpenAI特定配置
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2023-12-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-35-turbo

# Google AI特定配置
GOOGLE_AI_PROJECT_ID=your-gcp-project-id
GOOGLE_AI_LOCATION=us-central1

# Anthropic特定配置
ANTHROPIC_VERSION=2023-06-01

# 本地模型配置
OLLAMA_BASE_URL=http://localhost:11434
LM_STUDIO_BASE_URL=http://localhost:1234/v1
```

### 配置加载器

```python
import os
from typing import Dict, Any
from dotenv import load_dotenv

class ConfigLoader:
    def __init__(self):
        load_dotenv()
        self.provider = os.getenv("AI_PROVIDER", "openai")
    
    def load_config(self) -> Dict[str, Any]:
        """根据提供商加载相应配置"""
        base_config = {
            "provider": self.provider,
            "api_key": os.getenv("AI_API_KEY"),
            "model": os.getenv("AI_MODEL"),
            "embedding_model": os.getenv("AI_EMBEDDING_MODEL"),
            "max_tokens": int(os.getenv("AI_MAX_TOKENS", "2000")),
            "temperature": float(os.getenv("AI_TEMPERATURE", "0.7")),
            "timeout": int(os.getenv("AI_TIMEOUT", "30")),
            "max_retries": int(os.getenv("AI_MAX_RETRIES", "3"))
        }
        
        if self.provider == "openai":
            base_config.update({
                "organization": os.getenv("OPENAI_ORGANIZATION")
            })
        elif self.provider == "azure_openai":
            base_config.update({
                "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
                "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT")
            })
        elif self.provider == "google_ai":
            base_config.update({
                "project_id": os.getenv("GOOGLE_AI_PROJECT_ID"),
                "location": os.getenv("GOOGLE_AI_LOCATION")
            })
        elif self.provider == "ollama":
            base_config.update({
                "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            })
        
        return base_config

# 使用配置加载器
config_loader = ConfigLoader()
ai_config = config_loader.load_config()
ai_services.configure(ai_config)
```

## 配置验证

### 配置验证器

```python
from typing import Dict, Any, List
import requests

class ConfigValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置的完整性和正确性"""
        self.errors.clear()
        self.warnings.clear()
        
        # 基本字段验证
        required_fields = ["provider", "api_key", "model"]
        for field in required_fields:
            if not config.get(field):
                self.errors.append(f"缺少必需字段: {field}")
        
        # 提供商特定验证
        provider = config.get("provider")
        if provider == "openai":
            self._validate_openai_config(config)
        elif provider == "azure_openai":
            self._validate_azure_openai_config(config)
        elif provider == "google_ai":
            self._validate_google_ai_config(config)
        elif provider == "anthropic":
            self._validate_anthropic_config(config)
        elif provider == "ollama":
            self._validate_ollama_config(config)
        
        # 数值范围验证
        self._validate_numeric_ranges(config)
        
        return len(self.errors) == 0
    
    def _validate_openai_config(self, config: Dict[str, Any]):
        """验证OpenAI配置"""
        api_key = config.get("api_key", "")
        if not api_key.startswith("sk-"):
            self.errors.append("OpenAI API密钥格式不正确")
        
        model = config.get("model", "")
        valid_models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"]
        if model not in valid_models:
            self.warnings.append(f"模型 '{model}' 可能不受支持")
    
    def _validate_azure_openai_config(self, config: Dict[str, Any]):
        """验证Azure OpenAI配置"""
        endpoint = config.get("azure_endpoint", "")
        if not endpoint.startswith("https://") or not endpoint.endswith(".openai.azure.com/"):
            self.errors.append("Azure OpenAI端点格式不正确")
        
        if not config.get("deployment_name"):
            self.errors.append("缺少Azure部署名称")
    
    def _validate_google_ai_config(self, config: Dict[str, Any]):
        """验证Google AI配置"""
        if config.get("provider") == "vertex_ai":
            if not config.get("project_id"):
                self.errors.append("缺少GCP项目ID")
            if not config.get("location"):
                self.errors.append("缺少GCP区域")
    
    def _validate_anthropic_config(self, config: Dict[str, Any]):
        """验证Anthropic配置"""
        api_key = config.get("api_key", "")
        if not api_key.startswith("sk-ant-"):
            self.errors.append("Anthropic API密钥格式不正确")
    
    def _validate_ollama_config(self, config: Dict[str, Any]):
        """验证Ollama配置"""
        base_url = config.get("base_url", "")
        try:
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                self.warnings.append("无法连接到Ollama服务")
        except Exception:
            self.warnings.append("无法验证Ollama连接")
    
    def _validate_numeric_ranges(self, config: Dict[str, Any]):
        """验证数值范围"""
        max_tokens = config.get("max_tokens", 0)
        if max_tokens <= 0 or max_tokens > 32000:
            self.warnings.append(f"max_tokens值 ({max_tokens}) 可能不合理")
        
        temperature = config.get("temperature", 0.7)
        if temperature < 0 or temperature > 2:
            self.errors.append(f"temperature值 ({temperature}) 超出有效范围 [0, 2]")
        
        timeout = config.get("timeout", 30)
        if timeout <= 0 or timeout > 300:
            self.warnings.append(f"timeout值 ({timeout}) 可能不合理")
    
    def test_connection(self, config: Dict[str, Any]) -> bool:
        """测试API连接"""
        try:
            # 这里应该根据不同提供商实现实际的连接测试
            # 简化示例
            if config.get("provider") == "openai":
                return self._test_openai_connection(config)
            elif config.get("provider") == "azure_openai":
                return self._test_azure_openai_connection(config)
            # ... 其他提供商的测试
            return True
        except Exception as e:
            self.errors.append(f"连接测试失败: {str(e)}")
            return False
    
    def _test_openai_connection(self, config: Dict[str, Any]) -> bool:
        """测试OpenAI连接"""
        # 实际实现中应该调用OpenAI API进行测试
        return True
    
    def _test_azure_openai_connection(self, config: Dict[str, Any]) -> bool:
        """测试Azure OpenAI连接"""
        # 实际实现中应该调用Azure OpenAI API进行测试
        return True
    
    def get_validation_report(self) -> Dict[str, Any]:
        """获取验证报告"""
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings
        }

# 使用配置验证器
validator = ConfigValidator()
is_valid = validator.validate_config(ai_config)

if is_valid:
    print("✅ 配置验证通过")
    # 测试连接
    if validator.test_connection(ai_config):
        print("✅ 连接测试成功")
    else:
        print("❌ 连接测试失败")
else:
    print("❌ 配置验证失败")
    report = validator.get_validation_report()
    for error in report["errors"]:
        print(f"  错误: {error}")
    for warning in report["warnings"]:
        print(f"  警告: {warning}")
```

## 配置模板

### 开发环境配置

```python
# config/development.py
DEVELOPMENT_CONFIG = {
    "provider": "ollama",
    "base_url": "http://localhost:11434",
    "model": "llama2",
    "embedding_model": "nomic-embed-text",
    "max_tokens": 1000,
    "temperature": 0.8,
    "timeout": 60,
    "debug": True,
    "log_level": "DEBUG"
}
```

### 生产环境配置

```python
# config/production.py
PRODUCTION_CONFIG = {
    "provider": "openai",
    "api_key": os.getenv("OPENAI_API_KEY"),
    "model": "gpt-3.5-turbo",
    "embedding_model": "text-embedding-ada-002",
    "max_tokens": 2000,
    "temperature": 0.3,
    "timeout": 30,
    "max_retries": 5,
    "retry_delay": 2.0,
    "debug": False,
    "log_level": "INFO",
    "rate_limit": {
        "requests_per_minute": 60,
        "tokens_per_minute": 90000
    }
}
```

### 测试环境配置

```python
# config/testing.py
TESTING_CONFIG = {
    "provider": "mock",
    "model": "mock-model",
    "embedding_model": "mock-embedding",
    "max_tokens": 100,
    "temperature": 0.0,
    "timeout": 5,
    "mock_responses": {
        "chat": "这是一个模拟响应",
        "embeddings": [[0.1, 0.2, 0.3] * 512]  # 1536维向量
    }
}
```

## 最佳实践

### 1. 安全性

- **不要在代码中硬编码API密钥**
- **使用环境变量或安全的配置管理系统**
- **定期轮换API密钥**
- **限制API密钥的权限范围**

### 2. 性能优化

- **设置合理的超时时间**
- **使用连接池减少连接开销**
- **实现重试机制处理临时故障**
- **监控API使用量和成本**

### 3. 错误处理

- **实现优雅的降级机制**
- **记录详细的错误日志**
- **提供用户友好的错误消息**
- **设置合理的重试策略**

### 4. 监控和调试

- **启用详细的日志记录**
- **监控API响应时间和成功率**
- **设置告警机制**
- **定期测试配置的有效性**

---

*本文档提供了各种AI服务提供商的配置示例，请根据您的具体需求选择合适的配置方案。*