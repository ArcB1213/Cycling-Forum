"""
限流功能测试脚本
用于测试各个认证端点的限流保护
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_register_rate_limit():
    """测试注册端点限流（2次/分钟）"""
    print("\n=== 测试注册端点限流 (2次/分钟) ===")
    endpoint = f"{BASE_URL}/api/async/auth/register"
    
    for i in range(4):  # 尝试 4 次，第 3 次应该被拒绝
        payload = {
            "email": f"test{i}@example.com",
            "password": "Test@123456",
            "nickname": f"testuser{i}",
            "avatar": None
        }
        try:
            response = requests.post(endpoint, json=payload)
            status = response.status_code
            result = response.json()
            
            if status == 429:
                print(f"✓ 第 {i+1} 次请求 - 限流触发: {result.get('detail')}")
            elif status == 400:
                print(f"✓ 第 {i+1} 次请求 - 注册失败(正常): {result.get('detail')}")
            elif status == 200:
                print(f"✓ 第 {i+1} 次请求 - 注册成功: {status}")
            else:
                print(f"✓ 第 {i+1} 次请求 - 状态码: {status}")
        except Exception as e:
            print(f"✗ 第 {i+1} 次请求异常: {str(e)}")
        time.sleep(0.1)


def test_login_rate_limit():
    """测试登录端点限流（10次/分钟）"""
    print("\n=== 测试登录端点限流 (10次/分钟) ===")
    endpoint = f"{BASE_URL}/api/async/auth/login"
    
    for i in range(12):  # 尝试 12 次，第 11 次应该被拒绝
        payload = {
            "email": f"test{i}@example.com",
            "password": "wrongpassword"
        }
        try:
            response = requests.post(endpoint, json=payload)
            status = response.status_code
            result = response.json()
            
            if status == 429:
                print(f"✓ 第 {i+1} 次请求 - 限流触发: {result.get('detail')}")
            else:
                print(f"✓ 第 {i+1} 次请求 - 状态码: {status}")
        except Exception as e:
            print(f"✗ 第 {i+1} 次请求异常: {str(e)}")
        time.sleep(0.05)


def test_verify_email_rate_limit():
    """测试邮箱验证端点限流（5次/分钟）"""
    print("\n=== 测试邮箱验证端点限流 (5次/分钟) ===")
    endpoint = f"{BASE_URL}/api/async/auth/verify-email"
    
    for i in range(7):  # 尝试 7 次，第 6 次应该被拒绝
        payload = {
            "token": f"fake_token_{i}"
        }
        try:
            response = requests.post(endpoint, json=payload)
            status = response.status_code
            result = response.json()
            
            if status == 429:
                print(f"✓ 第 {i+1} 次请求 - 限流触发: {result.get('detail')}")
            else:
                print(f"✓ 第 {i+1} 次请求 - 状态码: {status}")
        except Exception as e:
            print(f"✗ 第 {i+1} 次请求异常: {str(e)}")
        time.sleep(0.05)


def test_forgot_password_rate_limit():
    """测试忘记密码端点限流（10次/小时）"""
    print("\n=== 测试忘记密码端点限流 (10次/小时) ===")
    endpoint = f"{BASE_URL}/api/auth/forgot-password"
    
    for i in range(12):  # 尝试 12 次，第 11 次应该被拒绝
        payload = {
            "email": f"test{i}@example.com"
        }
        try:
            response = requests.post(endpoint, json=payload)
            status = response.status_code
            result = response.json()
            
            if status == 429:
                print(f"✓ 第 {i+1} 次请求 - 限流触发: {result.get('detail')}")
            else:
                print(f"✓ 第 {i+1} 次请求 - 状态码: {status}")
        except Exception as e:
            print(f"✗ 第 {i+1} 次请求异常: {str(e)}")
        time.sleep(0.05)


if __name__ == "__main__":
    print("🧪 开始测试限流功能...")
    print(f"📍 服务器地址: {BASE_URL}")
    
    try:
        # 检查服务器是否可用
        response = requests.get(f"{BASE_URL}/")
        print(f"✓ 服务器可用: {response.status_code}\n")
    except Exception as e:
        print(f"✗ 服务器无法连接: {str(e)}")
        print("请确保服务器已启动: uvicorn app:app --reload\n")
        exit(1)
    
    # 运行测试
    test_register_rate_limit()
    test_login_rate_limit()
    test_verify_email_rate_limit()
    test_forgot_password_rate_limit()
    
    print("\n✅ 测试完成！")
