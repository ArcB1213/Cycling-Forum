# 车手评分功能压力测试指南

## 脚本概述

`locustfile_ratings.py` 是一个基于 Locust 框架的压力测试脚本，用于测试车手评分功能的性能和稳定性。

## 核心特性

### 1. **智能用户管理**

- 自动在数据库中创建 50 个测试用户（可配置）
- 所有测试用户预验证，直接支持登录
- 每个并发用户对应一个数据库用户

### 2. **评分规则模拟**

- ✅ **提交评分**：用户对未评分的车手提交新评分（权重 3）
- ✅ **修改评分**：用户对已评分的车手更新评分（权重 5）
- ✅ **查询统计**：获取车手的评分统计数据（权重 2）
- ✅ **查询列表**：分页查看车手的所有评分（权重 2）
- ✅ **我的评分**：查看当前用户的所有评分（权重 1）

### 3. **配置参数**

```python
NUM_USERS = 50      # 并发测试用户数
NUM_RIDERS = 5      # 测试的车手数量（ID从1开始）
```

修改这两个参数可以调整测试规模。

## 安装依赖

```bash
pip install locust
```

## 运行方式

### 方式 1：Web UI 界面（推荐用于手动配置）

```bash
cd backend
locust -f locustfile_ratings.py --host http://127.0.0.1:8000
```

然后打开浏览器访问 `http://localhost:8089`，在 UI 中配置：

- **Number of users (peak concurrency)**: 并发用户数
- **Spawn rate (users per second)**: 每秒增加的用户数
- **Duration**: 测试持续时间

### 方式 2：命令行直接运行（推荐用于自动化测试）

```bash
cd backend
locust -f locustfile_ratings.py --host http://127.0.0.1:8000 \
  -u 50 \
  -r 5 \
  -t 10m \
  --headless
```

### 方式 3：编程方式运行

```bash
cd backend
python -c "
from locustfile_ratings import *
from locust import main

sys.argv = ['locust', '-f', 'locustfile_ratings.py', '--host', 'http://127.0.0.1:8000', '-u', '50', '-r', '5', '-t', '10m', '--headless']
main.main()
"
```

## 命令行参数说明

| 参数         | 示例                    | 说明                        |
| ------------ | ----------------------- | --------------------------- |
| `-f`         | `locustfile_ratings.py` | Locust 文件路径             |
| `--host`     | `http://127.0.0.1:8000` | 后端服务地址                |
| `-u`         | `50`                    | 总并发用户数                |
| `-r`         | `5`                     | 每秒增加的用户数（ramp up） |
| `-t`         | `10m`                   | 测试持续时间（10 分钟）     |
| `--headless` | -                       | 无 UI 模式，直接运行        |
| `--csv`      | `results`               | 导出 CSV 报告               |

## 测试场景说明

### 用户行为流程

```
1. 启动 → 登录 → 初始化评分状态
2. 随机选择任务执行（基于权重）：
   ├─ 提交评分 (50%) - 对未评分的车手
   ├─ 修改评分 (30%) - 对已评分的车手
   ├─ 查询统计 (10%) - 获取评分数据
   ├─ 查询列表 (7%)  - 分页查看评分
   └─ 我的评分 (3%)  - 查看用户评分历史
3. 重复执行，直到测试结束
```

### 评分限制

- **一个用户对一个车手只能有一次评分记录**
- **已评分的评分可以无限次修改**
- **不同用户的评分相互独立**

## 预期结果指标

### 性能指标

| 指标                  | 说明                       |
| --------------------- | -------------------------- |
| **Total Requests**    | 总请求数                   |
| **Failure Rate**      | 失败率（应 < 1%）          |
| **Avg Response Time** | 平均响应时间（应 < 500ms） |
| **95th Percentile**   | 95%用户的响应时间          |
| **99th Percentile**   | 99%用户的响应时间          |

### 通过标准

- ✅ 失败率 < 1%
- ✅ 平均响应时间 < 500ms
- ✅ P95 < 1000ms
- ✅ P99 < 2000ms

## 实际测试建议

### 初始测试（了解系统基线）

```bash
locust -f locustfile_ratings.py --host http://127.0.0.1:8000 \
  -u 10 -r 2 -t 5m --headless
```

### 中等负载测试（常规场景）

```bash
locust -f locustfile_ratings.py --host http://127.0.0.1:8000 \
  -u 50 -r 5 -t 10m --headless
```

### 高负载测试（压力测试）

```bash
locust -f locustfile_ratings.py --host http://127.0.0.1:8000 \
  -u 200 -r 10 -t 15m --headless
```

## 导出测试结果

```bash
locust -f locustfile_ratings.py --host http://127.0.0.1:8000 \
  -u 50 -r 5 -t 10m \
  --headless \
  --csv=rating_results
```

会生成两个 CSV 文件：

- `rating_results_stats.csv` - 统计数据
- `rating_results_stats_history.csv` - 时间序列数据

## 常见问题

### Q1: 测试前需要启动什么服务？

需要启动后端服务：

```bash
cd backend
uvicorn app:app --reload
```

### Q2: 创建测试用户会修改真实数据吗？

是的，测试用户会被添加到数据库。建议在开发/测试数据库上运行，不要在生产环境运行。

### Q3: 如何清理测试用户？

```python
# 在 Python Shell 中运行
import asyncio
from models.database import AsyncSessionLocal
from models.models import User
from sqlalchemy import select

async def cleanup():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).filter(User.email.like('load_test_%')))
        users = result.scalars().all()
        for user in users:
            await db.delete(user)
        await db.commit()

asyncio.run(cleanup())
```

### Q4: 为什么看不到 Web UI？

确保已安装 Locust 依赖，并且使用了正确的命令（去掉`--headless`参数）。

## 修改测试参数

### 修改并发用户数

```python
# 在脚本中修改
NUM_USERS = 100  # 改为100个用户
```

### 修改测试车手数

```python
NUM_RIDERS = 10  # 改为10个车手
```

### 调整任务权重

```python
# 在 RatingLoadTestUser 类中修改 @task 装饰器的数字
@task(5)  # 权重为5
def update_rating(self):
    pass
```

### 修改等待时间

```python
# 请求之间的等待时间
wait_time = between(2, 5)  # 改为2-5秒
```

## 故障排查

### 错误：无法连接到数据库

- 检查 MySQL/PostgreSQL 是否运行
- 检查`models/database.py`中的数据库连接配置
- 检查数据库凭证是否正确

### 错误：模块导入失败

- 确保在`backend`目录运行脚本
- 确保所有依赖已安装：`pip install -r requirements.txt`

### 登录失败

- 检查后端服务是否运行
- 检查`--host`参数是否正确（默认`http://127.0.0.1:8000`）

## 性能优化建议

1. **数据库连接池**：确保`AsyncSessionLocal`使用了连接池
2. **缓存策略**：评分统计可以使用缓存减少数据库查询
3. **异步处理**：某些操作可以异步化进一步提升吞吐量
4. **索引优化**：确保`rating.rider_id`和`rating.user_id`有索引

## 相关文件

- `locustfile_ratings.py` - 压力测试脚本
- `test_ratings.py` - 用户创建参考
- `app.py` - 后端 API 实现
- `models/models.py` - 数据库模型

---

**最后更新**：2025-12-22  
**脚本版本**：1.0
