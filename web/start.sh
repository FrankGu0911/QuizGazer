#!/bin/bash

echo "========================================"
echo "QuizGazer 历史记录系统启动脚本"
echo "========================================"
echo ""

cd backend

echo "[1/3] 检查依赖..."
if ! pip show python-jose > /dev/null 2>&1; then
    echo "正在安装依赖..."
    pip install -r requirements.txt
else
    echo "依赖已安装"
fi

echo ""
echo "[2/3] 创建必要目录..."
mkdir -p data
mkdir -p uploads/images
mkdir -p exports

echo ""
echo "[3/3] 启动服务..."
echo ""
echo "========================================"
echo "服务地址:"
echo "  主页: http://localhost:8000/"
echo "  登录: http://localhost:8000/login"
echo "  API文档: http://localhost:8000/docs"
echo ""
echo "默认账号:"
echo "  用户名: admin"
echo "  密码: admin123"
echo "========================================"
echo ""

python main.py
