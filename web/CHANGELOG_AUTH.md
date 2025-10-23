# 认证功能更新日志

## 2025-10-24 - 添加登录认证系统

### 新增功能

#### 🔐 认证系统
- JWT Token认证机制
- 安全的密码哈希存储（bcrypt）
- Token自动过期管理（默认24小时）
- 登录状态持久化（localStorage）

#### 🎨 用户界面
- 全新登录页面（`login.html`）
  - 响应式设计
  - 支持深色/浅色主题
  - 表单验证
  - 回车键快捷登录
- 主页添加登出按钮
- 显示当前登录用户名

#### 🔒 安全特性
- 所有API端点添加认证保护
- 未登录自动跳转到登录页
- Token过期自动登出
- 密码最小长度验证
- 防止未授权访问

#### 🛠️ 开发工具
- 用户管理脚本（`manage_users.py`）
  - 添加新用户
  - 生成密码哈希
  - 验证密码
  - 生成安全密钥
- 快速启动脚本（`start.sh` / `start.bat`）
- 环境变量配置示例（`.env.example`）

### 文件变更

#### 新增文件
```
web/
├── frontend/
│   ├── login.html          # 登录页面
│   └── login.js            # 登录逻辑
├── backend/
│   ├── auth.py             # 认证中间件
│   ├── manage_users.py     # 用户管理工具
│   ├── .env.example        # 环境变量示例
│   └── api/endpoints/
│       └── auth.py         # 认证API端点
├── start.sh                # Linux/Mac启动脚本
├── start.bat               # Windows启动脚本
├── README_AUTH.md          # 认证系统文档
└── CHANGELOG_AUTH.md       # 本文件
```

#### 修改文件
```
web/
├── frontend/
│   ├── index.html          # 添加登出按钮
│   └── app.js              # 添加认证逻辑
└── backend/
    ├── main.py             # 集成认证路由
    └── requirements.txt    # 添加认证依赖
```

### 依赖更新

新增Python包：
- `python-jose[cryptography]>=3.3.0` - JWT处理
- `passlib[bcrypt]>=1.7.4` - 密码加密
- `python-dotenv>=1.0.0` - 环境变量管理

### API变更

#### 新增端点
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/me` - 获取当前用户
- `POST /api/auth/logout` - 用户登出
- `GET /login` - 登录页面

#### 受保护端点
以下端点现在需要认证：
- `GET /api/quiz/records` - 获取记录列表
- `GET /api/quiz/record/{id}` - 获取单条记录
- `POST /api/quiz/record-with-image` - 创建记录
- `DELETE /api/quiz/record/{id}` - 删除记录
- `GET /api/stats` - 获取统计信息

#### 公开端点
- `GET /api/health` - 健康检查
- `GET /ws` - WebSocket连接

### 默认账号

```
用户名: admin
密码: admin123
```

### 使用说明

#### 安装依赖
```bash
cd web/backend
pip install -r requirements.txt
```

#### 启动服务

**Linux/Mac:**
```bash
cd web
chmod +x start.sh
./start.sh
```

**Windows:**
```cmd
cd web
start.bat
```

**手动启动:**
```bash
cd web/backend
python main.py
```

#### 访问系统
- 主页: http://localhost:8000/
- 登录: http://localhost:8000/login
- API文档: http://localhost:8000/docs

### 配置说明

#### 环境变量（可选）

创建 `web/backend/.env` 文件：

```env
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

#### 添加新用户

使用用户管理工具：

```bash
cd web/backend
python manage_users.py
```

或手动编辑 `auth.py` 中的 `USERS_DB`。

### 安全建议

⚠️ **生产环境部署前必须：**

1. 修改 `SECRET_KEY` 为强随机字符串
2. 使用HTTPS加密通信
3. 限制CORS允许的域名
4. 使用数据库存储用户信息
5. 添加速率限制防止暴力破解
6. 启用访问日志

### 已知限制

- 用户信息存储在内存中（重启后丢失）
- 没有用户注册功能
- 没有密码重置功能
- 没有多因素认证
- 没有用户权限管理

### 后续计划

- [ ] 数据库用户存储
- [ ] 用户注册功能
- [ ] 密码重置功能
- [ ] 记住我功能
- [ ] 多因素认证(2FA)
- [ ] 用户权限管理
- [ ] 登录日志记录
- [ ] 验证码防护

### 技术栈

- **认证**: JWT (JSON Web Token)
- **密码加密**: bcrypt
- **后端框架**: FastAPI
- **前端框架**: Vue 3 + Element Plus

### 兼容性

- Python 3.8+
- 现代浏览器（Chrome, Firefox, Safari, Edge）
- 支持Windows, Linux, macOS

### 故障排除

详见 `README_AUTH.md` 文档。

---

**版本**: 1.0.0  
**日期**: 2025-10-24  
**作者**: Kiro AI Assistant
