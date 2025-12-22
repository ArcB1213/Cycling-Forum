import asyncio
import aiohttp
import time
import random
import sys
import os

# 添加父目录到 sys.path 以便导入（如果需要）
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://127.0.0.1:8000"
NUM_USERS = 10  # 模拟并发用户数
RIDER_ID = 1    # 测试的目标车手 ID

# 重新设计：使用直接数据库操作来创建测试用户
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from models.database import async_engine, AsyncSessionLocal
from models.models import User
from auth import get_password_hash

async def create_test_users(num_users):
    """在数据库中直接创建已验证的测试用户"""
    users = []
    async with AsyncSessionLocal() as db:
        for i in range(num_users):
            email = f"stress_v5_{i}@test.com"
            nickname = f"stress_v5_{i}"
            
            # 检查是否存在
            result = await db.execute(select(User).filter(User.email == email))
            user = result.scalar_one_or_none()
            
            if not user:
                user = User(
                    email=email,
                    nickname=nickname,
                    hashed_password=get_password_hash("password123"),
                    is_verified=True, # 直接设置为已验证
                    avatar="default"
                )
                db.add(user)
            else:
                # 确保是已验证的
                if not user.is_verified:
                    user.is_verified = True
            
            users.append({"email": email, "password": "password123"})
        
        await db.commit()
    
    # 显式关闭引擎连接池，防止 Event loop is closed 错误
    await async_engine.dispose()
    return users

async def login(session, email, password):
    """登录获取 Token"""
    async with session.post(f"{BASE_URL}/api/async/auth/login", json={
        "email": email,
        "password": password
    }) as resp:
        if resp.status == 200:
            data = await resp.json()
            return data["access_token"]
        else:
            print(f"Login failed for {email}: {resp.status}")
            return None

async def submit_rating(session, token, rider_id):
    """提交评分"""
    score = random.randint(1, 5)
    comment = f"Stress test rating {score}"
    
    start_time = time.time()
    async with session.post(
        f"{BASE_URL}/api/riders/{rider_id}/ratings",
        json={"score": score, "comment": comment, "rider_id": rider_id},
        headers={"Authorization": f"Bearer {token}"}
    ) as resp:
        duration = time.time() - start_time
        return resp.status, duration

async def main():
    print(f"Preparing {NUM_USERS} test users in database...")
    try:
        users_creds = await create_test_users(NUM_USERS)
    except Exception as e:
        print(f"Failed to create users in DB. Make sure you are running this from the backend directory or have correct python path. Error: {e}")
        return

    print("Users prepared. Starting stress test...")
    
    async with aiohttp.ClientSession() as session:
        # 1. 批量登录
        tasks = [login(session, u["email"], u["password"]) for u in users_creds]
        tokens = await asyncio.gather(*tasks)
        tokens = [t for t in tokens if t]
        
        if not tokens:
            print("No tokens obtained. Aborting.")
            return
            
        print(f"Logged in {len(tokens)} users.")
        
        # 2. 并发评分
        print(f"Starting concurrent ratings for Rider {RIDER_ID}...")
        start_time = time.time()
        
        tasks = [submit_rating(session, token, RIDER_ID) for token in tokens]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # 3. 统计结果
        success_count = sum(1 for status, _ in results if status == 200)
        fail_count = sum(1 for status, _ in results if status != 200)
        avg_latency = sum(duration for _, duration in results) / len(results)
        
        print("\n=== Test Results ===")
        print(f"Total Requests: {len(results)}")
        print(f"Concurrency: {NUM_USERS}")
        print(f"Total Time: {total_time:.2f}s")
        print(f"RPS (Requests/sec): {len(results) / total_time:.2f}")
        print(f"Average Latency: {avg_latency*1000:.2f}ms")
        print(f"Success: {success_count}")
        print(f"Failed: {fail_count}")
        
        if fail_count > 0:
            print("Failure Status Codes:")
            from collections import Counter
            status_counts = Counter(status for status, _ in results if status != 200)
            for status, count in status_counts.items():
                print(f"  {status}: {count}")

if __name__ == "__main__":
    # Windows 下 asyncio 的策略调整
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
