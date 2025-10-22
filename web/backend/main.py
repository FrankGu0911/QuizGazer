"""
QuizGazer 历史记录后端服务
FastAPI 应用入口
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from database import engine, Base
from api.endpoints import quiz, stats, websocket, health

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建 FastAPI 应用
app = FastAPI(
    title="QuizGazer History API",
    description="QuizGazer 答题历史记录管理系统",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建必要的目录
os.makedirs("uploads/images", exist_ok=True)
os.makedirs("exports", exist_ok=True)

# 前端文件路径
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
FRONTEND_DIR = os.path.abspath(FRONTEND_DIR)

# 注册API路由
app.include_router(health.router)
app.include_router(quiz.router)
app.include_router(stats.router)
app.include_router(websocket.router)

# 挂载静态文件
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 前端页面路由
@app.get("/")
async def root():
    """根路径 - 重定向到前端页面"""
    if os.path.exists(os.path.join(FRONTEND_DIR, "index.html")):
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
    else:
        return {
            "message": "QuizGazer History API",
            "version": "1.0.0",
            "docs": "/docs",
            "frontend": "前端文件未找到，请检查 frontend 目录"
        }

@app.get("/app")
async def frontend_app():
    """前端应用入口"""
    frontend_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    else:
        return {"error": "前端文件未找到"}

@app.get("/history")
async def history_page():
    """历史记录页面别名"""
    return await frontend_app()

# 静态文件服务 - 必须在最后，因为使用了通配符
@app.get("/app.js")
async def frontend_js():
    """前端JS文件"""
    js_path = os.path.join(FRONTEND_DIR, "app.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    else:
        raise HTTPException(status_code=404, detail="JS文件未找到")

# 通用静态文件服务 - 必须在所有其他路由之后
@app.get("/{filename}")
async def serve_frontend_files(filename: str):
    """服务前端静态文件"""
    # 只允许特定的文件类型
    allowed_extensions = ['.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg']
    
    if any(filename.endswith(ext) for ext in allowed_extensions):
        file_path = os.path.join(FRONTEND_DIR, filename)
        if os.path.exists(file_path):
            # 根据文件扩展名设置正确的媒体类型
            media_type_map = {
                '.js': 'application/javascript',
                '.css': 'text/css',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.ico': 'image/x-icon',
                '.svg': 'image/svg+xml'
            }
            
            ext = next((ext for ext in allowed_extensions if filename.endswith(ext)), '.js')
            media_type = media_type_map.get(ext, 'application/octet-stream')
            
            return FileResponse(file_path, media_type=media_type)
    
    # 如果不是静态文件，返回404
    raise HTTPException(status_code=404, detail="File not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
