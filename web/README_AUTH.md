# QuizGazer 认证系统说明

## 功能概述

已为QuizGazer历史记录系统添加了完整的登录认证功能：

- ✅ 用户登录页面
- ✅ JWT Token认证
- ✅ 自动跳转（未登录跳转到登录页）
- ✅ Token过期自动登出
- ✅ 安全的密码哈希存储

## 快速开始

### 1. 安装依赖

```bash
cd web/backend
pip install -r requirements.txt
```

新增的依赖包括：
- `python-jose[cryptography]` - JWT token处理
- `passlib[bcrypt]` - 密码哈希
- `python-dotenv` - 环境变量管理

### 2. 配置环境变量（可选）

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，修改密钥：

```env
SECRET_KEY=your-very-secure-random-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

**重要**: 生产环境务必修改 `SECRET_KEY` 为随机字符串！

### 3. 启动服务

```bash
cd web/backend
python main.py
```

或使用uvicorn：

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 访问系统

- 主页: http://localhost:8000/
- 登录页: http://localhost:8000/login
- API文档: http://localhost:8000/docs

## 默认账号

```
用户名: admin
密码: admin123
```

## 使用说明

### 登录流程

1. 访问主页时，如果未登录会自动跳转到登录页
2. 输入用户名和密码登录
3. 登录成功后自动跳转到主页
4. Token有效期为24小时（可配置）

### 登出

点击页面右上角的"退出"按钮即可登出。

### Token管理

- Token存储在浏览器的 `localStorage` 中
- 每次API请求自动携带Token
- Token过期后会自动跳转到登录页

## API端点

### 认证相关

- `POST /api/auth/login` - 用户登录
- `GET /api/auth/me` - 获取当前用户信息
- `POST /api/auth/logout` - 用户登出

### 受保护的端点

以下端点需要认证：
- `/api/quiz/*` - 所有答题记录相关接口
- `/api/stats` - 统计信息接口

### 公开端点

- `/api/health` - 健康检查
- `/ws` - WebSocket连接

## 添加新用户

目前用户存储在 `web/backend/auth.py` 的 `USERS_DB` 字典中。

要添加新用户，编辑 `auth.py`：

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 生成密码哈希
hashed = pwd_context.hash("your_password")
print(hashed)

# 添加到USERS_DB
USERS_DB = {
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("admin123"),
        "disabled": False,
    },
    "newuser": {
        "username": "newuser",
        "hashed_password": hashed,
        "disabled": False,
    }
}
```

**注意**: 生产环境建议使用数据库存储用户信息。

## 安全建议

### 生产环境部署

1. **修改SECRET_KEY**: 使用强随机字符串
   ```python
   import secrets
   print(secrets.token_urlsafe(32))
   ```

2. **使用HTTPS**: 确保所有通信加密

3. **限制CORS**: 修改 `main.py` 中的CORS配置
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://yourdomain.com"],  # 指定域名
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

4. **使用数据库**: 将用户信息存储到数据库而非内存

5. **添加速率限制**: 防止暴力破解

6. **启用日志**: 记录登录尝试

## 自定义配置

### 修改Token过期时间

编辑 `web/backend/auth.py`：

```python
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时
```

或通过环境变量：

```env
ACCESS_TOKEN_EXPIRE_MINUTES=720  # 12小时
```

### 修改密码策略

编辑 `web/frontend/login.js` 中的验证规则：

```javascript
const rules = {
    password: [
        { required: true, message: '请输入密码', trigger: 'blur' },
        { min: 8, message: '密码长度至少8位', trigger: 'blur' }
    ]
};
```

## 故障排除

### 问题1: 登录后立即跳转回登录页

**原因**: Token未正确保存或后端认证失败

**解决**:
1. 检查浏览器控制台是否有错误
2. 检查 `localStorage` 中是否有 `access_token`
3. 检查后端日志

### 问题2: Token过期提示

**原因**: Token已过期（默认24小时）

**解决**: 重新登录即可

### 问题3: 无法访问API

**原因**: 请求未携带Token或Token无效

**解决**:
1. 确保前端正确发送Authorization头
2. 检查Token格式: `Bearer <token>`
3. 验证Token是否过期

## 技术栈

- **后端认证**: FastAPI + python-jose + passlib
- **前端**: Vue 3 + Element Plus
- **Token**: JWT (JSON Web Token)
- **密码加密**: bcrypt

## 文件结构

```
web/
├── backend/
│   ├── auth.py              # 认证中间件和工具
│   ├── main.py              # 主应用（已更新）
│   ├── api/endpoints/
│   │   └── auth.py          # 认证API端点
│   ├── .env.example         # 环境变量示例
│   └── requirements.txt     # 依赖（已更新）
└── frontend/
    ├── login.html           # 登录页面
    ├── login.js             # 登录逻辑
    ├── index.html           # 主页（已更新）
    └── app.js               # 主应用逻辑（已更新）
```

## 后续改进建议

1. 添加用户注册功能
2. 添加密码重置功能
3. 添加记住我功能
4. 添加多因素认证(2FA)
5. 使用数据库存储用户
6. 添加用户权限管理
7. 添加登录日志
8. 添加验证码防护
