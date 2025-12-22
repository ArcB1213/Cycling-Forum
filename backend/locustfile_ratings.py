import asyncio
import random
import sys
import os
import threading
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict

# 添加父目录到 sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from locust import HttpUser, task, between, events
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.database import AsyncSessionLocal, async_engine
from models.models import User
from auth import get_password_hash


# ============ 日志配置 ============
# 配置详细的错误日志
LOG_DIR = "stress_test_logs"
os.makedirs(LOG_DIR, exist_ok=True)

# 创建日志文件（带时间戳）
log_filename = os.path.join(LOG_DIR, f"locust_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("locust_ratings")

# 错误统计器
class ErrorStats:
    """全局错误统计"""
    def __init__(self):
        self.lock = threading.Lock()
        self.errors: Dict[str, List[dict]] = defaultdict(list)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.max_errors_per_type = 50  # 每种错误类型最多记录50条详细信息
    
    def record_error(self, endpoint: str, status_code: int, error_detail: str, 
                     user_email: Optional[str] = None, extra_info: Optional[dict] = None):
        """记录错误详情"""
        with self.lock:
            error_key = f"{endpoint}:{status_code}"
            self.error_counts[error_key] += 1
            
            # 只保留前N条详细错误
            if len(self.errors[error_key]) < self.max_errors_per_type:
                error_record = {
                    "timestamp": datetime.now().isoformat(),
                    "endpoint": endpoint,
                    "status_code": status_code,
                    "detail": error_detail[:500],  # 截断过长的错误信息
                    "user": user_email,
                    "extra": extra_info
                }
                self.errors[error_key].append(error_record)
                
                # 同时写入日志文件
                logger.error(f"[{endpoint}] Status={status_code} | User={user_email} | Detail={error_detail[:200]}")
    
    def get_summary(self) -> dict:
        """获取错误统计摘要"""
        with self.lock:
            return {
                "error_counts": dict(self.error_counts),
                "sample_errors": {k: v[:5] for k, v in self.errors.items()}  # 每种类型返回前5条样本
            }
    
    def print_summary(self):
        """打印错误摘要"""
        summary = self.get_summary()
        print("\n" + "=" * 70)
        print("📊 错误统计摘要")
        print("=" * 70)
        
        if not summary["error_counts"]:
            print("  ✅ 没有记录到任何错误！")
        else:
            print("\n错误计数:")
            for error_key, count in sorted(summary["error_counts"].items(), key=lambda x: -x[1]):
                print(f"  {error_key}: {count} 次")
            
            print("\n错误样本:")
            for error_key, samples in summary["sample_errors"].items():
                print(f"\n  [{error_key}]")
                for sample in samples[:3]:
                    print(f"    - {sample['timestamp']}: {sample['detail'][:100]}...")
        
        print("=" * 70)
        print(f"📁 详细日志已保存到: {log_filename}")
        print("=" * 70 + "\n")


# 全局错误统计实例
ERROR_STATS = ErrorStats()


@dataclass
class TestUser:
    """测试用户信息"""
    email: str
    password: str
    nickname: str
    user_id: Optional[int] = None
    token: Optional[str] = None


def parse_error_response(resp) -> str:
    """解析错误响应，提取详细信息"""
    try:
        # 尝试解析 JSON 响应
        data = resp.json()
        if isinstance(data, dict):
            # FastAPI 的标准错误格式
            if "detail" in data:
                return str(data["detail"])
            # 其他可能的格式
            return json.dumps(data, ensure_ascii=False)
        return str(data)
    except:
        # 如果不是 JSON，返回原始文本
        text = resp.text[:500] if resp.text else "无响应内容"
        return text if text else "空响应"


# ============ 全局测试数据 ============
TEST_USERS: List[TestUser] = []
RIDER_IDS: List[int] = []  # 测试的车手ID列表
NUM_USERS = 300  # 并发测试用户数
NUM_RIDERS = 10  # 测试的车手数量（从ID 1开始）


async def create_test_users_in_db(num_users: int) -> List[TestUser]:
    """在数据库中创建测试用户"""
    users = []
    print(f"🔧 正在创建测试用户... (总数: {num_users})")
    
    try:
        async with AsyncSessionLocal() as db:
            print(f"  ✓ 数据库连接成功")
            
            for i in range(num_users):
                if i % 10 == 0:  # 每10个用户输出一次进度
                    print(f"  进度: {i}/{num_users}")
                
                email = f"load_test_{i}@test.com"
                nickname = f"load_test_{i}"
                
                # 检查用户是否存在
                result = await db.execute(select(User).filter(User.email == email))
                user = result.scalar_one_or_none()

                if not user:
                    user = User(
                        email=email,
                        nickname=nickname,
                        hashed_password=get_password_hash("password123"),
                        is_verified=True,
                        avatar="default"
                    )
                    db.add(user)
                    await db.flush()  # 立即获取user_id
                
                users.append(TestUser(
                    email=email,
                    password="password123",
                    nickname=nickname,
                    user_id=user.user_id
                ))
            
            print(f"  ✓ 提交数据库更改...")
            await db.commit()
            print(f"  ✓ 完成！创建了 {len(users)} 个用户")
        
        await async_engine.dispose()
        
    except Exception as e:
        print(f"  ✗ 创建用户时出错: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    return users


def setup_test_data():
    """在Locust启动前设置测试数据（同步包装器）"""
    global TEST_USERS, RIDER_IDS
    
    try:
        # Windows 平台需要设置事件循环策略
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # 创建测试用户
        print(f"🔧 正在准备 {NUM_USERS} 个测试用户...")
        
        # 使用新的事件循环，避免与Locust的事件循环冲突
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            TEST_USERS = loop.run_until_complete(create_test_users_in_db(NUM_USERS))
        finally:
            loop.close()
        
        print(f"✅ 用户准备完成：{len(TEST_USERS)} 个用户")
        
        # 准备车手ID列表（假设数据库中有这些ID）
        RIDER_IDS = list(range(1, NUM_RIDERS + 1))
        print(f"✅ 测试车手ID：{RIDER_IDS}")
        
    except Exception as e:
        print(f"❌ 测试数据准备失败: {e}")
        import traceback
        traceback.print_exc()
        print("请确保你在backend目录中运行此脚本，并且数据库连接正常")


# ============ Locust 用户类 ============

class RatingLoadTestUser(HttpUser):
    """车手评分压力测试用户"""
    
    wait_time = between(1, 3)  # 请求之间等待 1-3 秒
    _user_counter = 0  # 类级别的用户计数器
    _counter_lock = threading.Lock()  # 线程锁，确保计数器线程安全
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_data: Optional[TestUser] = None
        self.assigned_riders: Dict[int, Dict] = {}  # rider_id -> {has_rated: bool, rating_id: int}
        
        # 线程安全地获取用户索引
        with RatingLoadTestUser._counter_lock:
            self._user_index = RatingLoadTestUser._user_counter
            RatingLoadTestUser._user_counter += 1
    
    def on_start(self):
        """用户启动时执行 - 登录"""
        if not TEST_USERS:
            print("❌ 没有可用的测试用户")
            return
        
        # 分配一个测试用户（循环分配）
        user_index = self._user_index % len(TEST_USERS)
        self.user_data = TEST_USERS[user_index]
        
        # 调试信息：确认用户分配
        if self._user_index < 5 or self._user_index % 10 == 0:
            print(f"  🔐 Locust实例#{self._user_index} → 测试用户 {self.user_data.email}")
        
        # 初始化车手评分状态
        for rider_id in RIDER_IDS:
            self.assigned_riders[rider_id] = {
                "has_rated": False,
                "rating_id": None,
                "last_score": None
            }
        
        # 登录
        self._login()
    
    def _login(self):
        """登录获取token"""
        if not self.user_data:
            logger.error("登录失败: user_data 为空")
            return
            
        with self.client.post(
            "/api/async/auth/login",
            json={
                "email": self.user_data.email,
                "password": self.user_data.password
            },
            catch_response=True,
            name="/api/async/auth/login"
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.user_data.token = data["access_token"]
                self.user_data.user_id = data["user"]["user_id"]
                resp.success()
            else:
                error_detail = parse_error_response(resp)
                ERROR_STATS.record_error(
                    endpoint="/api/async/auth/login",
                    status_code=resp.status_code,
                    error_detail=error_detail,
                    user_email=self.user_data.email
                )
                logger.error(f"登录失败 ({self.user_data.email}): [{resp.status_code}] {error_detail}")
                resp.failure(f"登录失败 [{resp.status_code}]: {error_detail[:100]}")
    
    def _get_headers(self):
        """获取带有认证令牌的请求头"""
        token = self.user_data.token if self.user_data else ""
        return {
            "Authorization": f"Bearer {token}"
        }
    
    @task(3)
    def submit_rating(self):
        """提交新评分（只能对未评分的车手）"""
        # 找一个还没有评分的车手
        available_riders = [rid for rid, info in self.assigned_riders.items() if not info["has_rated"]]
        
        if not available_riders:
            # 所有车手都已评分，跳过此任务
            return
        
        rider_id = random.choice(available_riders)
        score = random.randint(1, 5)
        comment = f"Pressure test score {score} - {random.choice(['Great rider!', 'Amazing performance!', 'Well done!', 'Impressive!', 'Love this rider!'])}"
        
        with self.client.post(
            f"/api/riders/{rider_id}/ratings",
            json={
                "rider_id": rider_id,
                "score": score,
                "comment": comment
            },
            headers=self._get_headers(),
            catch_response=True,
            name="/api/riders/[id]/ratings [POST]"
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.assigned_riders[rider_id]["has_rated"] = True
                self.assigned_riders[rider_id]["rating_id"] = data.get("rating_id")
                self.assigned_riders[rider_id]["last_score"] = score
                resp.success()
            else:
                error_detail = parse_error_response(resp)
                
                if resp.status_code == 409:
                    # 409 冲突 - 并发竞态条件导致的重复评分
                    self.assigned_riders[rider_id]["has_rated"] = True
                    self.assigned_riders[rider_id]["last_score"] = score
                    ERROR_STATS.record_error(
                        endpoint="/api/riders/[id]/ratings [POST]",
                        status_code=409,
                        error_detail=error_detail,
                        user_email=self.user_data.email if self.user_data else None,
                        extra_info={"rider_id": rider_id, "action": "submit"}
                    )
                    # 标记为成功，因为这是预期内的并发情况
                    resp.success()
                elif resp.status_code in (500, 503):
                    # 服务器错误 - 记录详细信息
                    ERROR_STATS.record_error(
                        endpoint="/api/riders/[id]/ratings [POST]",
                        status_code=resp.status_code,
                        error_detail=error_detail,
                        user_email=self.user_data.email if self.user_data else None,
                        extra_info={"rider_id": rider_id, "score": score, "action": "submit"}
                    )
                    resp.failure(f"提交评分失败 [{resp.status_code}]: {error_detail[:100]}")
                else:
                    # 其他错误
                    ERROR_STATS.record_error(
                        endpoint="/api/riders/[id]/ratings [POST]",
                        status_code=resp.status_code,
                        error_detail=error_detail,
                        user_email=self.user_data.email if self.user_data else None,
                        extra_info={"rider_id": rider_id, "score": score, "action": "submit"}
                    )
                    resp.failure(f"提交评分失败 [{resp.status_code}]: {error_detail[:100]}")
    
    @task(5)
    def update_rating(self):
        """修改评分（只能修改已评分的车手）"""
        # 找一个已经评分的车手
        rated_riders = [rid for rid, info in self.assigned_riders.items() if info["has_rated"]]
        
        if not rated_riders:
            # 没有已评分的车手，跳过此任务
            return
        
        rider_id = random.choice(rated_riders)
        old_score = self.assigned_riders[rider_id]["last_score"]
        new_score = random.randint(1, 5)
        
        # 避免重复提交相同的分数
        while new_score == old_score:
            new_score = random.randint(1, 5)
        
        comment = f"Updated to score {new_score} - {random.choice(['Changed my mind', 'Better understanding', 'Updated opinion', 'New perspective', 'Revised rating'])}"
        
        with self.client.post(
            f"/api/riders/{rider_id}/ratings",
            json={
                "rider_id": rider_id,
                "score": new_score,
                "comment": comment
            },
            headers=self._get_headers(),
            catch_response=True,
            name="/api/riders/[id]/ratings [POST - UPDATE]"
        ) as resp:
            if resp.status_code == 200:
                self.assigned_riders[rider_id]["last_score"] = new_score
                resp.success()
            else:
                error_detail = parse_error_response(resp)
                user_email = self.user_data.email if self.user_data else None
                
                if resp.status_code == 0:
                    # 状态码 0 通常表示连接问题
                    ERROR_STATS.record_error(
                        endpoint="/api/riders/[id]/ratings [POST - UPDATE]",
                        status_code=0,
                        error_detail="连接错误: 服务器无响应或连接被拒绝",
                        user_email=user_email,
                        extra_info={"rider_id": rider_id, "old_score": old_score, "new_score": new_score}
                    )
                    resp.failure("连接错误: 服务器无响应")
                elif resp.status_code == 401:
                    # Token 过期或无效
                    token_prefix = self.user_data.token[:20] if self.user_data and self.user_data.token else "None"
                    ERROR_STATS.record_error(
                        endpoint="/api/riders/[id]/ratings [POST - UPDATE]",
                        status_code=401,
                        error_detail=error_detail,
                        user_email=user_email,
                        extra_info={"rider_id": rider_id, "token_prefix": token_prefix}
                    )
                    # 尝试重新登录
                    self._login()
                    resp.failure(f"Token无效 [{resp.status_code}]: {error_detail[:100]}")
                elif resp.status_code in (500, 503):
                    # 服务器错误
                    ERROR_STATS.record_error(
                        endpoint="/api/riders/[id]/ratings [POST - UPDATE]",
                        status_code=resp.status_code,
                        error_detail=error_detail,
                        user_email=user_email,
                        extra_info={"rider_id": rider_id, "old_score": old_score, "new_score": new_score}
                    )
                    resp.failure(f"修改评分失败 [{resp.status_code}]: {error_detail[:100]}")
                else:
                    ERROR_STATS.record_error(
                        endpoint="/api/riders/[id]/ratings [POST - UPDATE]",
                        status_code=resp.status_code,
                        error_detail=error_detail,
                        user_email=user_email,
                        extra_info={"rider_id": rider_id, "old_score": old_score, "new_score": new_score}
                    )
                    resp.failure(f"修改评分失败 [{resp.status_code}]: {error_detail[:100]}")
    
    @task(2)
    def get_rating_stats(self):
        """查询车手评分统计"""
        rider_id = random.choice(RIDER_IDS)
        
        with self.client.get(
            f"/api/riders/{rider_id}/rating-stats",
            catch_response=True,
            name="/api/riders/[id]/rating-stats [GET]"
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                error_detail = parse_error_response(resp)
                ERROR_STATS.record_error(
                    endpoint="/api/riders/[id]/rating-stats [GET]",
                    status_code=resp.status_code,
                    error_detail=error_detail,
                    user_email=self.user_data.email if self.user_data else None,
                    extra_info={"rider_id": rider_id}
                )
                resp.failure(f"获取评分统计失败 [{resp.status_code}]: {error_detail[:100]}")
    
    @task(2)
    def get_rider_ratings(self):
        """查询车手的所有评分列表（分页）"""
        rider_id = random.choice(RIDER_IDS)
        page = random.randint(1, 3)
        
        with self.client.get(
            f"/api/riders/{rider_id}/ratings?page={page}&limit=10",
            catch_response=True,
            name="/api/riders/[id]/ratings [GET]"
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                error_detail = parse_error_response(resp)
                ERROR_STATS.record_error(
                    endpoint="/api/riders/[id]/ratings [GET]",
                    status_code=resp.status_code,
                    error_detail=error_detail,
                    user_email=self.user_data.email if self.user_data else None,
                    extra_info={"rider_id": rider_id, "page": page}
                )
                resp.failure(f"获取评分列表失败 [{resp.status_code}]: {error_detail[:100]}")
    
    @task(1)
    def get_my_ratings(self):
        """查询当前用户所有评分"""
        page = random.randint(1, 2)
        
        with self.client.get(
            f"/api/auth/my-ratings?page={page}&limit=10",
            headers=self._get_headers(),
            catch_response=True,
            name="/api/auth/my-ratings [GET]"
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                error_detail = parse_error_response(resp)
                ERROR_STATS.record_error(
                    endpoint="/api/auth/my-ratings [GET]",
                    status_code=resp.status_code,
                    error_detail=error_detail,
                    user_email=self.user_data.email if self.user_data else None,
                    extra_info={"page": page}
                )
                resp.failure(f"获取我的评分失败 [{resp.status_code}]: {error_detail[:100]}")


# ============ Locust 事件处理器 ============

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Locust 测试启动时执行"""
    print("\n" + "=" * 60)
    print("🚀 车手评分压力测试启动")
    print("=" * 60)
    
    # 重置用户计数器
    RatingLoadTestUser._user_counter = 0
    
    setup_test_data()
    
    logger.info(f"压力测试启动 - 用户数: {NUM_USERS}, 车手数: {NUM_RIDERS}")
    print(f"📁 错误日志将保存到: {log_filename}")
    print("=" * 60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Locust 测试停止时执行"""
    print("\n" + "=" * 60)
    print("🛑 压力测试完成")
    print("=" * 60)
    print(f"\n📊 测试统计：")
    print(f"  - 总请求数: {environment.stats.total.num_requests}")
    print(f"  - 失败数: {environment.stats.total.num_failures}")
    print(f"  - 平均响应时间: {environment.stats.total.avg_response_time:.0f}ms")
    print(f"  - 95% 响应时间: {environment.stats.total.get_response_time_percentile(0.95):.0f}ms")
    print(f"  - 99% 响应时间: {environment.stats.total.get_response_time_percentile(0.99):.0f}ms")
    
    # 输出详细的错误统计
    ERROR_STATS.print_summary()
    
    # 将错误摘要保存到 JSON 文件
    summary_file = os.path.join(LOG_DIR, f"error_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    try:
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(ERROR_STATS.get_summary(), f, ensure_ascii=False, indent=2)
        print(f"📁 错误摘要已保存到: {summary_file}")
    except Exception as e:
        print(f"⚠️ 保存错误摘要失败: {e}")
    
    logger.info(f"压力测试完成 - 总请求: {environment.stats.total.num_requests}, 失败: {environment.stats.total.num_failures}")
    print("=" * 60 + "\n")


# ============ 使用说明 ============
"""
运行此Locust脚本的方式：

1. 命令行启动（使用Web UI）：
   locust -f locustfile_ratings.py --host http://127.0.0.1:8000

2. 命令行启动（无UI，直接运行）：
   locust -f locustfile_ratings.py --host http://127.0.0.1:8000 -u 50 -r 10 -t 10m --headless

参数说明：
   -f: 指定Locust文件
   --host: 后端服务URL
   -u: 总用户数（NUM_USERS）
   -r: 每秒增加的用户数（ramp up rate）
   -t: 测试持续时间（如 10m 为10分钟）
   --headless: 无UI模式

配置参数（可在脚本中修改）：
   NUM_USERS: 并发测试用户数 (默认50)
   NUM_RIDERS: 测试的车手数量 (默认5，ID从1开始)
   
测试场景：
   - 用户登录后，随机对5个车手中的某个进行评分
   - 已评分的车手可以多次修改评分
   - 同时查询评分统计、评分列表等
   - 权重分配：提交评分(3) > 修改评分(5) > 获取统计(2) > 查询列表(2) > 我的评分(1)
"""
