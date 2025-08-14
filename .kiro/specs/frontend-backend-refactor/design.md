# 设计文档

## 概述

本设计文档基于QuizGazer前后端分离重构需求，详细描述了系统的技术架构、组件设计、数据模型和实现方案。系统将从单体PySide6桌面应用重构为现代化的分布式架构，包含Tauri客户端、FastAPI服务端和React网页端。

## 架构设计

### 整体架构

```mermaid
graph TB
    subgraph "客户端层"
        TC[Tauri客户端<br/>React + TypeScript]
        WC[网页端<br/>React + TypeScript]
    end
    
    subgraph "API网关层"
        AG[API网关<br/>Nginx/Traefik]
    end
    
    subgraph "服务层"
        AS[认证服务<br/>FastAPI]
        AIS[AI服务<br/>FastAPI]
        KS[知识库服务<br/>FastAPI]
        US[用户服务<br/>FastAPI]
        MS[监控服务<br/>FastAPI]
    end
    
    subgraph "数据层"
        PG[(PostgreSQL<br/>用户数据)]
        RD[(Redis<br/>缓存/会话)]
        VD[(向量数据库<br/>Milvus)]
        FS[文件存储<br/>MinIO/S3]
    end
    
    subgraph "外部服务"
        AI1[AI服务1<br/>OpenAI]
        AI2[AI服务2<br/>Claude]
        AI3[AI服务3<br/>其他]
        LB[AI负载均衡器]
        ES[邮件服务<br/>SMTP]
    end
    
    TC --> AG
    WC --> AG
    AG --> AS
    AG --> AIS
    AG --> KS
    AG --> US
    AG --> MS
    
    AS --> PG
    AS --> RD
    AS --> ES
    
    AIS --> LB
    LB --> AI1
    LB --> AI2
    LB --> AI3
    AIS --> RD
    
    KS --> PG
    KS --> VD
    KS --> FS
    
    US --> PG
    US --> RD
    
    MS --> PG
    MS --> RD
```

### 技术栈选择

#### 客户端 (Tauri)
- **前端框架**: React 18 + TypeScript
- **状态管理**: Zustand (轻量级状态管理)
- **UI组件**: Tailwind CSS + Headless UI
- **HTTP客户端**: Axios
- **系统调用**: Tauri API (Rust)

#### 服务端
- **API框架**: FastAPI (Python)
- **认证**: JWT + OAuth2
- **数据库ORM**: SQLAlchemy + Alembic
- **异步处理**: Celery + Redis
- **API文档**: OpenAPI/Swagger

#### 网页端
- **前端框架**: React 18 + TypeScript
- **路由**: React Router v6
- **状态管理**: React Query + Zustand
- **UI组件**: Ant Design + Tailwind CSS
- **构建工具**: Vite

#### 数据存储
- **关系数据库**: PostgreSQL 14+
- **缓存**: Redis 7+
- **向量数据库**: Milvus
- **文件存储**: MinIO (S3兼容)

#### 部署运维
- **容器化**: Docker + Docker Compose
- **反向代理**: Nginx
- **监控**: Prometheus + Grafana
- **日志**: ELK Stack (Elasticsearch + Logstash + Kibana)

## 组件和接口设计

### 1. 认证服务 (Auth Service)

#### 核心功能
- 用户注册/登录/登出
- JWT Token生成和验证
- 邮箱验证码发送
- 密码重置
- 用户权限管理

#### API接口设计

```python
# 用户注册
POST /api/auth/register
{
    "email": "user@example.com",
    "password": "password123",
    "username": "username"
}

# 邮箱验证
POST /api/auth/verify-email
{
    "email": "user@example.com",
    "verification_code": "123456"
}

# 用户登录
POST /api/auth/login
{
    "email": "user@example.com",
    "password": "password123"
}

# Token刷新
POST /api/auth/refresh
{
    "refresh_token": "refresh_token_here"
}

# 密码重置
POST /api/auth/reset-password
{
    "email": "user@example.com"
}

POST /api/auth/confirm-reset
{
    "email": "user@example.com",
    "reset_code": "123456",
    "new_password": "new_password123"
}
```

#### 中间件设计
```python
class AuthMiddleware:
    async def authenticate_token(self, token: str) -> User:
        """验证JWT Token并返回用户信息"""
        pass
    
    async def check_token_balance(self, user_id: int) -> int:
        """检查用户Token余额"""
        pass
    
    async def deduct_token(self, user_id: int, amount: int = 1) -> bool:
        """扣除用户Token"""
        pass
```

### 2. AI服务 (AI Service)

#### 核心功能
- VLM图像识别
- LLM文本问答
- 知识库RAG问答
- Token计费管理

#### API接口设计

```python
# 图像问题识别
POST /api/ai/extract-question
Headers: Authorization: Bearer <token>
Content-Type: multipart/form-data
{
    "image": <image_file>,
    "screen_info": {
        "width": 1920,
        "height": 1080
    }
}

# 文本问答
POST /api/ai/answer-question
Headers: Authorization: Bearer <token>
{
    "question": "问题内容",
    "context": "可选的上下文信息"
}

# 知识库问答
POST /api/ai/knowledge-answer
Headers: Authorization: Bearer <token>
{
    "question": "问题内容",
    "knowledge_base_id": "kb_123",
    "top_k": 5
}

# 直接图像问答
POST /api/ai/image-answer
Headers: Authorization: Bearer <token>
Content-Type: multipart/form-data
{
    "image": <image_file>,
    "question": "可选的问题描述"
}
```

#### AI服务架构

```python
class AILoadBalancer:
    def __init__(self):
        self.providers = [
            {"name": "openai", "weight": 50, "client": OpenAIClient()},
            {"name": "claude", "weight": 30, "client": ClaudeClient()},
            {"name": "gemini", "weight": 20, "client": GeminiClient()}
        ]
        self.current_weights = {p["name"]: p["weight"] for p in self.providers}
    
    async def get_available_provider(self, model_type: str) -> AIClient:
        """根据权重和可用性选择AI服务提供商"""
        available_providers = [p for p in self.providers if await p["client"].is_available()]
        if not available_providers:
            raise AIServiceUnavailableError()
        
        # 加权随机选择
        return self._weighted_random_choice(available_providers)
    
    def update_weights(self, weights: Dict[str, int]):
        """动态更新服务权重"""
        self.current_weights.update(weights)

class AIService:
    def __init__(self):
        self.load_balancer = AILoadBalancer()
        self.token_manager = TokenManager()
    
    async def extract_question_from_image(self, image: bytes, user_id: int) -> str:
        """从图像中提取问题"""
        await self.token_manager.deduct_token(user_id, 1)
        vlm_client = await self.load_balancer.get_available_provider("vlm")
        return await vlm_client.extract_text(image)
    
    async def answer_question(self, question: str, user_id: int) -> str:
        """回答文本问题"""
        await self.token_manager.deduct_token(user_id, 1)
        llm_client = await self.load_balancer.get_available_provider("llm")
        return await llm_client.generate_answer(question)
```

#### AI服务配置管理

```python
# AI服务配置
class AIProviderConfig(BaseModel):
    name: str
    type: str  # "openai", "claude", "gemini", etc.
    api_key: str
    base_url: str
    models: Dict[str, str]  # {"vlm": "gpt-4-vision", "llm": "gpt-4"}
    weight: int = 10
    max_requests_per_minute: int = 60
    timeout: int = 30
    is_active: bool = True

# 配置API接口
POST /api/admin/ai-providers
{
    "name": "openai-primary",
    "type": "openai",
    "api_key": "sk-xxx",
    "base_url": "https://api.openai.com/v1",
    "models": {
        "vlm": "gpt-4-vision-preview",
        "llm": "gpt-4-turbo"
    },
    "weight": 50,
    "max_requests_per_minute": 100
}

# 更新权重
PUT /api/admin/ai-providers/weights
{
    "openai-primary": 60,
    "claude-backup": 25,
    "gemini-fallback": 15
}
```

### 3. 知识库服务 (Knowledge Base Service)

#### 核心功能
- 知识库CRUD操作
- 文档上传和处理
- 向量搜索和RAG
- 权限和定价管理

#### 数据模型设计

```python
class KnowledgeBase(BaseModel):
    id: str
    name: str
    description: str
    owner_id: int
    type: KnowledgeBaseType  # PUBLIC, PRIVATE, PAID
    price: Optional[int] = None  # Token价格
    created_at: datetime
    updated_at: datetime
    document_count: int
    is_active: bool

class Document(BaseModel):
    id: str
    knowledge_base_id: str
    filename: str
    content_type: str
    file_size: int
    upload_time: datetime
    processed: bool
    chunk_count: int

class KnowledgeBasePurchase(BaseModel):
    id: str
    user_id: int
    knowledge_base_id: str
    purchase_time: datetime
    price_paid: int
```

#### API接口设计

```python
# 创建知识库
POST /api/kb/create
Headers: Authorization: Bearer <token>
{
    "name": "知识库名称",
    "description": "描述",
    "type": "PUBLIC",  # PUBLIC, PRIVATE, PAID
    "price": 10  # 仅收费知识库需要
}

# 上传文档
POST /api/kb/{kb_id}/documents
Headers: Authorization: Bearer <token>
Content-Type: multipart/form-data
{
    "files": [<file1>, <file2>]
}

# 搜索知识库
GET /api/kb/search?q=关键词&type=PUBLIC&page=1&size=20

# 购买知识库
POST /api/kb/{kb_id}/purchase
Headers: Authorization: Bearer <token>

# 收藏知识库
POST /api/kb/{kb_id}/favorite
Headers: Authorization: Bearer <token>

# 获取用户收藏的知识库
GET /api/kb/favorites
Headers: Authorization: Bearer <token>
```

### 4. 用户服务 (User Service)

#### 核心功能
- 用户信息管理
- Token余额管理
- 使用历史记录
- 收藏和购买记录

#### API接口设计

```python
# 获取用户信息
GET /api/user/profile
Headers: Authorization: Bearer <token>

# 更新用户信息
PUT /api/user/profile
Headers: Authorization: Bearer <token>
{
    "username": "new_username",
    "avatar": "avatar_url"
}

# 获取Token余额
GET /api/user/balance
Headers: Authorization: Bearer <token>

# 获取使用历史
GET /api/user/usage-history?page=1&size=20
Headers: Authorization: Bearer <token>

# 获取购买记录
GET /api/user/purchases?page=1&size=20
Headers: Authorization: Bearer <token>
```

## 数据模型

### 用户相关表结构

```sql
-- 用户表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    token_balance INTEGER DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Token使用记录表
CREATE TABLE token_usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    api_endpoint VARCHAR(255) NOT NULL,
    tokens_used INTEGER NOT NULL,
    request_data JSONB,
    response_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 邮箱验证码表
CREATE TABLE email_verifications (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    code VARCHAR(10) NOT NULL,
    type VARCHAR(20) NOT NULL, -- 'register', 'reset_password'
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 知识库相关表结构

```sql
-- 知识库表
CREATE TABLE knowledge_bases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id INTEGER REFERENCES users(id),
    type VARCHAR(20) NOT NULL, -- 'PUBLIC', 'PRIVATE', 'PAID'
    price INTEGER, -- Token价格，仅收费知识库
    document_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 文档表
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_base_id UUID REFERENCES knowledge_bases(id),
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100),
    file_size INTEGER,
    file_path VARCHAR(500),
    processed BOOLEAN DEFAULT FALSE,
    chunk_count INTEGER DEFAULT 0,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 知识库购买记录表
CREATE TABLE knowledge_base_purchases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id),
    knowledge_base_id UUID REFERENCES knowledge_bases(id),
    price_paid INTEGER NOT NULL,
    purchase_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, knowledge_base_id)
);

-- 知识库收藏表
CREATE TABLE knowledge_base_favorites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id),
    knowledge_base_id UUID REFERENCES knowledge_bases(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, knowledge_base_id)
);

-- 知识库评价表
CREATE TABLE knowledge_base_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id),
    knowledge_base_id UUID REFERENCES knowledge_bases(id),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, knowledge_base_id)
);
```

## AI服务负载均衡设计

### 负载均衡策略

#### 1. 加权轮询
```python
class WeightedRoundRobin:
    def __init__(self, providers: List[AIProviderConfig]):
        self.providers = providers
        self.current_weights = {p.name: 0 for p in providers}
        self.total_weight = sum(p.weight for p in providers)
    
    def select_provider(self) -> AIProviderConfig:
        """选择下一个服务提供商"""
        max_current_weight = -1
        selected_provider = None
        
        for provider in self.providers:
            if not provider.is_active:
                continue
                
            self.current_weights[provider.name] += provider.weight
            
            if self.current_weights[provider.name] > max_current_weight:
                max_current_weight = self.current_weights[provider.name]
                selected_provider = provider
        
        if selected_provider:
            self.current_weights[selected_provider.name] -= self.total_weight
        
        return selected_provider
```

#### 2. 健康检查
```python
class HealthChecker:
    def __init__(self):
        self.health_status = {}
        self.check_interval = 30  # 秒
    
    async def check_provider_health(self, provider: AIProviderConfig) -> bool:
        """检查AI服务提供商健康状态"""
        try:
            client = self._get_client(provider)
            response = await client.health_check()
            self.health_status[provider.name] = {
                "is_healthy": True,
                "last_check": datetime.now(),
                "response_time": response.response_time
            }
            return True
        except Exception as e:
            self.health_status[provider.name] = {
                "is_healthy": False,
                "last_check": datetime.now(),
                "error": str(e)
            }
            return False
    
    async def start_health_monitoring(self):
        """启动健康检查定时任务"""
        while True:
            for provider in self.providers:
                await self.check_provider_health(provider)
            await asyncio.sleep(self.check_interval)
```

#### 3. 限流和重试
```python
class RateLimiter:
    def __init__(self):
        self.request_counts = {}
        self.reset_time = {}
    
    async def can_make_request(self, provider_name: str) -> bool:
        """检查是否可以发起请求"""
        now = datetime.now()
        minute_key = now.strftime("%Y-%m-%d %H:%M")
        
        if provider_name not in self.request_counts:
            self.request_counts[provider_name] = {}
        
        current_count = self.request_counts[provider_name].get(minute_key, 0)
        max_requests = self._get_provider_limit(provider_name)
        
        return current_count < max_requests

class RetryHandler:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
    
    async def execute_with_retry(self, func, *args, **kwargs):
        """带重试的执行函数"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                continue
        
        raise last_exception
```

### Milvus向量数据库集成

#### 1. 连接和配置
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

class MilvusService:
    def __init__(self, host: str = "localhost", port: int = 19530):
        self.host = host
        self.port = port
        self.connection_alias = "default"
        
    async def connect(self):
        """连接到Milvus"""
        connections.connect(
            alias=self.connection_alias,
            host=self.host,
            port=self.port
        )
    
    def create_knowledge_base_collection(self, kb_id: str):
        """为知识库创建集合"""
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536)
        ]
        
        schema = CollectionSchema(
            fields=fields,
            description=f"Knowledge base collection for {kb_id}"
        )
        
        collection = Collection(
            name=f"kb_{kb_id}",
            schema=schema,
            using=self.connection_alias
        )
        
        # 创建索引
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
        collection.create_index("embedding", index_params)
        
        return collection
```

#### 2. 向量搜索
```python
class VectorSearchService:
    def __init__(self, milvus_service: MilvusService):
        self.milvus = milvus_service
    
    async def search_similar_chunks(
        self, 
        kb_id: str, 
        query_embedding: List[float], 
        top_k: int = 5
    ) -> List[Dict]:
        """搜索相似文档块"""
        collection = Collection(f"kb_{kb_id}")
        collection.load()
        
        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10}
        }
        
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["document_id", "chunk_id", "content"]
        )
        
        return [
            {
                "document_id": hit.entity.get("document_id"),
                "chunk_id": hit.entity.get("chunk_id"),
                "content": hit.entity.get("content"),
                "score": hit.score
            }
            for hit in results[0]
        ]
```

## 错误处理     resul hit in  fore": hiscorent")ontget("city.": hit.entontentcy.get("chitenthit.": nk_id"chu         id"),ent_.get("docum hit.entityt_id":   "documen     {        turn [   re  ntent", "coidhunk_ "c,mbe"eeld=eddiery_emb    data=[qu        search(ction.llelts = co    resu   probe": 10}"n"COSINEtype": ctiokb_ib_{f"kn(lectioCol= ection 文档块"""搜索相似"     "   istt = intop_k:        ],: List[floaty_embeddingquer     tr, ch_similararasync def se_services = milvusce)vusServiMilrvice: sevus_(self, miliceServorSearchs Vectollectionn cex_params, indg"("embeddin_index.createction"nlist": 1": {"params        ",VF_FLAT"Iex_type":     "ind E",": "COSINc_typea  _aionnectelf.con     using=schemakb_{kb_id"ection(= Coll   ) kb_id}"or {ion fse collect baowledgef"Kncription=     desieldsds=fctionSchemaColleim=153CTOR, dVEType.FLOAT_ype=Data", dtbeddingem"535)th=65AR, max_leng.VARCHpe=DataTypetycontent", d"me=Schema(na  Field      max_length=.VARCHAR, ypeataTe=Did", dtype="chunk_ldSchema(nam     Fiength=100),le max_AR,pe.VARCHDataType=", dtyt_idme="documennaema(SchTrue),ue, auto_id=rimary=Tr4, is_pe.INT6ype=DataTypd", dt(name="iSchema集合""b_id: self, kn(e_collectioowledge_basnse  port=ost=self.hos h           tion.connec=selfias    alions.connectonnect       c "连接到Millf):ct(sedef conneync "default"on_alias = connectirt = por.pofhost = hoelf.= 19t port: inocalhost",  "lt: str =f, hos_init__(sel    def _vSchema, DaCollectionma, heFieldScn, ectio Collons,onnecti import c1. 连接和#### 集成eptionexcise last_ ra       ontintempt) (2 ** atsyncio.sleepait a     aws:retrie< self.max_attempt        if ep  last_exc              Exception a     except *kwargs)args, *func(* await     return             try:etries + f.max_rsel range(ttempt in ae Nonexception =ast_l函数带重试的执行   """     wargs):gs, **k*ar func, etry(self,ute_with_rexectri max_reetries =_rax3):int = :  max_retries_(self,_init_Hanryclass Rett < marent_councurrn ider_name)t(provovider_limi_get_prests = self.ax_requminute_key, 0.get(movider_name]s[prquest_count= self.rerent_count         curder_name] = [proviuest_countself.req sts:quest_counn self.ret ier_name noovid-%d"%Y-%mtrftime(.s = nowinute_key    m    tetime.noww = da no是否可以发起请求""检查    "    : str) -> boder_namef, provist(seln_make_requef casync de a_counts = uest.req(selft__def __iniva.check_intervialth(proider_he.providers:file True:时任务"""启动健康检查定   "" lf(se  ":errordatetime_check": "last       y": Falsis_health    "            er.name] =atus[providf.health_st   seltion xcep    except E    return T         onse_time.resp": responsno": datetime.cklast_cheru T = {me]ovider.natus[pr.health_sta     self       check()t.health_ent(pro_clielf._get snt ="nfig) -> bviderCorovider: AIPth(self, proalovider_heef check_pr d  0  #nterval = 3check_i.statulf.health_        se_(seit_def __in  

### 统一错误响应格式

```python
class APIError(BaseModel):
    code: str
    message: str
    details: Optional[Dict] = None

class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[APIError] = None
```

### 错误码定义

```python
class ErrorCodes:
    # 认证相关
    INVALID_TOKEN = "AUTH_001"
    TOKEN_EXPIRED = "AUTH_002"
    INSUFFICIENT_BALANCE = "AUTH_003"
    
    # 用户相关
    USER_NOT_FOUND = "USER_001"
    EMAIL_ALREADY_EXISTS = "USER_002"
    INVALID_CREDENTIALS = "USER_003"
    
    # 知识库相关
    KB_NOT_FOUND = "KB_001"
    KB_ACCESS_DENIED = "KB_002"
    KB_ALREADY_PURCHASED = "KB_003"
    
    # AI服务相关
    AI_SERVICE_ERROR = "AI_001"
    IMAGE_PROCESSING_ERROR = "AI_002"
```

## 测试策略

### 单元测试
- 每个服务的核心业务逻辑
- 数据模型的验证逻辑
- 工具函数和辅助方法

### 集成测试
- API接口的完整流程测试
- 数据库操作的集成测试
- 外部服务调用的模拟测试

### 端到端测试
- 用户注册到使用的完整流程
- 知识库创建到问答的完整流程
- 客户端与服务端的交互测试

### 性能测试
- API接口的响应时间测试
- 并发用户的负载测试
- 数据库查询性能测试

## 安全设计

### 认证和授权
- JWT Token认证机制
- 基于角色的访问控制(RBAC)
- API接口的权限验证

### 数据安全
- 密码使用bcrypt哈希存储
- 敏感数据传输使用HTTPS
- 数据库连接使用SSL

### 输入验证
- 所有API输入参数验证
- 文件上传类型和大小限制
- SQL注入和XSS攻击防护

### 限流和防护
- API调用频率限制
- 用户Token余额检查
- 异常请求监控和告警
## 客户端
设计 (Tauri)

### 架构设计

```mermaid
graph TB
    subgraph "UI层 (React)"
        LC[登录组件]
        MC[主界面组件]
        SC[截图组件]
        KC[知识库组件]
        SET[设置组件]
    end
    
    subgraph "状态管理 (Zustand)"
        AS[认证状态]
        US[用户状态]
        KS[知识库状态]
        SS[系统状态]
    end
    
    subgraph "服务层"
        API[API客户端]
        AUTH[认证服务]
        SCREEN[截图服务]
    end
    
    subgraph "Tauri后端 (Rust)"
        CMD[Tauri命令]
        SYS[系统调用]
        FILE[文件操作]
    end
    
    LC --> AS
    MC --> US
    SC --> SCREEN
    KC --> KS
    
    AS --> AUTH
    US --> API
    KS --> API
    
    AUTH --> API
    SCREEN --> CMD
    API --> CMD
    
    CMD --> SYS
    CMD --> FILE
```

### 核心组件设计

#### 1. 认证管理
```typescript
interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  tokenBalance: number;
}

class AuthService {
  async login(email: string, password: string): Promise<AuthResponse>;
  async logout(): Promise<void>;
  async refreshToken(): Promise<string>;
  async checkTokenBalance(): Promise<number>;
}
```

#### 2. 截图功能
```rust
// Tauri命令 (Rust)
#[tauri::command]
async fn take_screenshot(x: i32, y: i32, width: i32, height: i32) -> Result<String, String> {
    // 截图实现
}

#[tauri::command]
async fn get_screen_info() -> Result<Vec<ScreenInfo>, String> {
    // 获取屏幕信息
}
```

```typescript
// React组件
interface ScreenshotService {
  takeScreenshot(region: ScreenRegion): Promise<string>;
  getScreenInfo(): Promise<ScreenInfo[]>;
}
```

#### 3. 知识库集成
```typescript
interface KnowledgeBaseState {
  availableKBs: KnowledgeBase[];
  favoriteKBs: KnowledgeBase[];
  selectedKB: KnowledgeBase | null;
}

class KnowledgeBaseService {
  async getFavoriteKBs(): Promise<KnowledgeBase[]>;
  async searchPublicKBs(query: string): Promise<KnowledgeBase[]>;
  async purchaseKB(kbId: string): Promise<void>;
}
```

### UI组件设计

#### 主窗口组件
```typescript
const MainWindow: React.FC = () => {
  const [mode, setMode] = useState<'compact' | 'expanded'>('compact');
  const { isAuthenticated } = useAuthStore();
  
  if (!isAuthenticated) {
    return <LoginForm />;
  }
  
  return (
    <div className={`main-window ${mode}`}>
      {mode === 'compact' ? (
        <CompactView onScreenshot={() => setMode('expanded')} />
      ) : (
        <ExpandedView onBack={() => setMode('compact')} />
      )}
    </div>
  );
};
```

## 网页端设计

### 页面结构设计

```mermaid
graph TB
    subgraph "公共页面"
        HOME[首页]
        LOGIN[登录页]
        REGISTER[注册页]
    end
    
    subgraph "用户中心"
        PROFILE[个人资料]
        BALANCE[余额管理]
        HISTORY[使用历史]
        PURCHASES[购买记录]
    end
    
    subgraph "知识库管理"
        KB_LIST[知识库列表]
        KB_DETAIL[知识库详情]
        KB_CREATE[创建知识库]
        KB_EDIT[编辑知识库]
        DOC_MANAGE[文档管理]
    end
    
    subgraph "管理后台"
        ADMIN_USERS[用户管理]
        ADMIN_KB[知识库审核]
        ADMIN_STATS[统计分析]
    end
    
    HOME --> LOGIN
    HOME --> KB_LIST
    LOGIN --> PROFILE
    PROFILE --> BALANCE
    KB_LIST --> KB_DETAIL
    KB_DETAIL --> KB_CREATE
```

### 核心页面设计

#### 知识库浏览页面
```typescript
const KnowledgeBaseList: React.FC = () => {
  const [kbs, setKBs] = useState<KnowledgeBase[]>([]);
  const [filters, setFilters] = useState<KBFilters>({
    type: 'all',
    category: '',
    rating: 0
  });
  
  return (
    <div className="kb-list-page">
      <SearchBar onSearch={handleSearch} />
      <FilterPanel filters={filters} onChange={setFilters} />
      <KBGrid knowledgeBases={kbs} />
      <Pagination />
    </div>
  );
};
```

#### 知识库管理页面
```typescript
const KnowledgeBaseManage: React.FC = () => {
  const [kb, setKB] = useState<KnowledgeBase | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  
  return (
    <div className="kb-manage-page">
      <KBSettings kb={kb} onChange={setKB} />
      <DocumentUpload onUpload={handleDocumentUpload} />
      <DocumentList documents={documents} />
      <KBStats kbId={kb?.id} />
    </div>
  );
};
```

## 部署架构

### Docker容器化设计

```yaml
# docker-compose.yml
version: '3.8'

services:
  # API网关
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - auth-service
      - ai-service
      - kb-service

  # 认证服务
  auth-service:
    build: ./services/auth
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/quizgazer
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      - postgres
      - redis

  # AI服务
  ai-service:
    build: ./services/ai
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

  # 知识库服务
  kb-service:
    build: ./services/knowledge-base
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/quizgazer
      - MILVUS_URL=http://milvus:19530
      - MINIO_URL=http://minio:9000
    depends_on:
      - postgres
      - milvus
      - minio

  # 数据库
  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=quizgazer
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # 缓存
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  # 向量数据库
  milvus:
    image: milvusdb/milvus:latest
    command: ["milvus", "run", "standalone"]
    environment:
      - ETCD_ENDPOINTS=etcd:2379
      - MINIO_ADDRESS=minio:9000
    ports:
      - "19530:19530"
    depends_on:
      - etcd
      - minio
    volumes:
      - milvus_data:/var/lib/milvus

  # Milvus依赖的etcd
  etcd:
    image: quay.io/coreos/etcd:v3.5.0
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
    command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd
    volumes:
      - etcd_data:/etcd

  # 文件存储
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=admin
      - MINIO_ROOT_PASSWORD=password
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  redis_data:
  milvus_data:
  etcd_data:
  minio_data:
```

### 监控和日志

```yaml
# 监控服务
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

  # 日志收集
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
```

## 性能优化

### 缓存策略
- **Redis缓存**: 用户会话、API响应、知识库元数据
- **CDN缓存**: 静态资源、文档文件
- **数据库缓存**: 查询结果缓存、连接池优化

### 数据库优化
- **索引优化**: 为常用查询字段创建索引
- **分区表**: 按时间分区存储日志数据
- **读写分离**: 主从复制，读操作分流

### API优化
- **异步处理**: 文档处理、邮件发送等耗时操作
- **批量操作**: 支持批量上传、批量查询
- **分页查询**: 大数据量查询分页返回

### 前端优化
- **代码分割**: 按路由和功能模块分割代码
- **懒加载**: 组件和资源按需加载
- **缓存策略**: HTTP缓存、本地存储缓存

## 扩展性设计

### 微服务架构
- **服务拆分**: 按业务领域拆分独立服务
- **服务发现**: 使用Consul或Kubernetes服务发现
- **负载均衡**: 支持多实例部署和负载均衡

### 数据库扩展
- **水平分片**: 按用户ID分片存储用户数据
- **垂直分库**: 按业务模块分离数据库
- **读写分离**: 主从复制支持读操作扩展

### 消息队列
- **异步处理**: 使用Celery+Redis处理异步任务
- **事件驱动**: 服务间通过事件进行解耦通信
- **任务调度**: 定时任务和延时任务处理

## 迁移策略

### 数据迁移
1. **用户数据迁移**: 从现有配置文件迁移用户设置
2. **知识库迁移**: 将现有知识库数据迁移到新的向量数据库
3. **配置迁移**: AI模型配置迁移到服务端环境变量

### 功能迁移
1. **阶段一**: 搭建基础服务端架构和API
2. **阶段二**: 重构客户端，对接服务端API
3. **阶段三**: 开发网页端管理界面
4. **阶段四**: 完善监控、日志和运维功能

### 兼容性考虑
- **API版本管理**: 支持多版本API并存
- **渐进式迁移**: 支持新旧系统并行运行
- **数据同步**: 迁移期间保持数据一致性