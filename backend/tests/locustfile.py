"""
API 性能压测脚本
使用 Locust 对同步和异步接口进行对比测试
"""
from locust import HttpUser, task, between
import random

class CyclingAPIUser(HttpUser):
    """模拟用户行为 - 测试异步 API 性能"""
    wait_time = between(1, 3)  # 用户请求间隔 1-3 秒
    
    # ============ 赛事相关 API ============
    @task(5)
    def get_races_async(self):
        """测试异步获取赛事列表（高频）"""
        self.client.get("/api/async/races", name="[异步] 获取赛事列表")
    
    @task(3)
    def get_editions_async(self):
        """测试异步获取赛事届数"""
        self.client.get("/api/async/races/1/editions", name="[异步] 获取赛事届数")
    
    @task(2)
    def get_stages_async(self):
        """测试异步获取赛段列表"""
        edition_id = random.randint(1, 5)
        self.client.get(f"/api/async/editions/{edition_id}/stages", name="[异步] 获取赛段列表")
    
    @task(2)
    def get_stage_results_async(self):
        """测试异步获取赛段结果（复杂查询）"""
        stage_id = random.randint(1, 20)
        self.client.get(f"/api/async/stages/{stage_id}/results", name="[异步] 获取赛段结果")
    
    # ============ 骑手相关 API ============
    @task(4)
    def get_riders_async(self):
        """测试异步获取骑手列表"""
        self.client.get("/api/async/riders", name="[异步] 获取骑手列表")
    
    @task(3)
    def get_rider_detail_async(self):
        """测试异步获取骑手详情"""
        rider_id = random.randint(1, 100)
        self.client.get(f"/api/async/riders/{rider_id}", name="[异步] 获取骑手详情")
    
    @task(2)
    def get_rider_races_async(self):
        """测试异步获取骑手参赛记录（复杂查询）"""
        rider_id = random.randint(1, 50)
        self.client.get(f"/api/async/riders/{rider_id}/races", name="[异步] 获取骑手参赛记录")
    
    @task(1)
    def get_rider_wins_async(self):
        """测试异步获取骑手冠军记录"""
        rider_id = random.randint(1, 50)
        self.client.get(f"/api/async/riders/{rider_id}/wins", name="[异步] 获取骑手冠军记录")
    
    # ============ 同步 API 对比（可选）============
    # @task(1)
    # def get_stage_results_sync(self):
    #     """测试同步获取赛段结果（对比基准）"""
    #     self.client.get("/api/stages/1/results", name="[同步] 获取赛段结果")

    # @task(2)
    # def get_rider_detail_sync(self):
    #     """测试同步获取骑手详情"""
    #     rider_id = random.randint(1, 100)
    #     self.client.get(f"/api/riders/{rider_id}", name="[同步] 获取骑手详情")
    
    def on_start(self):
        """用户启动时执行"""
        pass
    
    def on_stop(self):
        """用户停止时执行"""
        pass


# ============ 运行说明 ============
# 1. 安装: pip install locust
# 2. 启动: locust -f locustfile.py --host=http://localhost:8000
# 3. 访问: http://localhost:8089
# 4. 配置压测参数:
#    - Number of users (peak concurrency): 100-500
#    - Spawn rate (users started/second): 10-20
#    - Host: http://localhost:8000
# 5. 点击 "Start swarming" 开始压测
# 6. 观察指标:
#    - RPS (Requests Per Second): 异步应为同步的 3-5 倍
#    - Response Time (ms): 异步应 < 100ms，同步可能 > 300ms
#    - Failure Rate: 应保持 0%
