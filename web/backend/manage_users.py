#!/usr/bin/env python3
"""
用户管理工具
用于添加、删除、修改用户
"""

import sys
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def add_user():
    """添加新用户"""
    print("\n=== 添加新用户 ===")
    username = input("用户名: ").strip()
    
    if not username:
        print("❌ 用户名不能为空")
        return
    
    password = input("密码: ").strip()
    
    if len(password) < 6:
        print("❌ 密码长度至少6位")
        return
    
    hashed = generate_password_hash(password)
    
    print("\n✅ 用户创建成功！")
    print("\n请将以下代码添加到 auth.py 的 USERS_DB 字典中：")
    print("-" * 60)
    print(f'''    "{username}": {{
        "username": "{username}",
        "hashed_password": "{hashed}",
        "disabled": False,
    }},''')
    print("-" * 60)


def generate_hash():
    """生成密码哈希"""
    print("\n=== 生成密码哈希 ===")
    password = input("密码: ").strip()
    
    if not password:
        print("❌ 密码不能为空")
        return
    
    hashed = generate_password_hash(password)
    print(f"\n密码哈希: {hashed}")


def verify_hash():
    """验证密码哈希"""
    print("\n=== 验证密码哈希 ===")
    password = input("密码: ").strip()
    hashed = input("哈希值: ").strip()
    
    if verify_password(password, hashed):
        print("✅ 密码匹配")
    else:
        print("❌ 密码不匹配")


def generate_secret_key():
    """生成安全密钥"""
    import secrets
    print("\n=== 生成安全密钥 ===")
    key = secrets.token_urlsafe(32)
    print(f"\n安全密钥: {key}")
    print("\n请将此密钥添加到 .env 文件中：")
    print(f"SECRET_KEY={key}")


def main():
    """主菜单"""
    while True:
        print("\n" + "=" * 60)
        print("QuizGazer 用户管理工具")
        print("=" * 60)
        print("1. 添加新用户")
        print("2. 生成密码哈希")
        print("3. 验证密码哈希")
        print("4. 生成安全密钥")
        print("0. 退出")
        print("=" * 60)
        
        choice = input("\n请选择操作 (0-4): ").strip()
        
        if choice == "1":
            add_user()
        elif choice == "2":
            generate_hash()
        elif choice == "3":
            verify_hash()
        elif choice == "4":
            generate_secret_key()
        elif choice == "0":
            print("\n再见！")
            break
        else:
            print("❌ 无效的选择")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(0)
