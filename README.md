# 数据库课程设计（Cycling Forum 项目）

本仓库为课程设计项目代码，包含用于展示“三大环赛”数据的前端、后端与数据处理脚本，并扩展为一个简单的社交论坛（含用户注册/邮箱验证/头像与个人中心）。

**项目概览**

- 前端：Vue 3 + TypeScript（Vite 构建）
- 后端：FastAPI + SQLAlchemy（支持异步操作，使用 MySQL 存储）
- 缓存：Redis（用于热点数据缓存、浏览量 Write-Back 与高并发优化）
- 认证：JWT（访问/刷新 token） + `passlib` 密码哈希
- 迁移：Alembic 管理数据库版本与性能索引
- 邮件：SMTP（用于邮箱验证与重置密码）
- 论坛：完整的发帖/评论/删除功能，支持多级评论树结构 + WebSocket 实时更新
- 性能：支持异步 API 路由、缓存预热、限流保护与批量查询优化
- 测试：包含 Locust 压力测试脚本、自动化测试用例与性能基准测试

**快速目录结构**

- `backend/`：FastAPI 后端，包含 `app.py`、`models/`、`schemas.py`、上传目录 `uploads/` 等
- `cycling-forum/`：前端 Vue 项目（Vite + TypeScript）
- `Data Scraper/`：数据抓取脚本与原始 CSV 文件

**本地开发 — 先决条件**

- Node.js（建议 18+）与 npm 或 pnpm/yarn
- Python 3.10+（建议使用虚拟环境或 conda）
- MySQL（或本地调整为其它兼容数据库）

**可选：Redis（缓存加速，本地 WSL）**

- 项目支持使用 Redis 作为缓存/会话提升访问效率（推荐在本地开发或测试使用）。
- 如果你在 Windows 上使用 WSL（例如 Ubuntu 24.04.2），可以在 WSL 中安装并运行 Redis：

```bash
# 在 WSL（Ubuntu）中安装并启动 redis-server
sudo apt update
sudo apt install -y redis-server
sudo service redis-server start

# 验证 Redis 是否可用
redis-cli ping    # 应返回 PONG
```

- 后端示例环境变量：

```
REDIS_URL=redis://127.0.0.1:6379/0
```

- 在 WSL2 下，使用 `127.0.0.1` 或 `localhost` 一般即可从 Windows 访问运行在 WSL 中的 Redis；如果遇到网络问题，请确认 WSL 网络设置或使用 `wsl hostname -I` 检查 IP。

- 后端代码会通过该 `REDIS_URL` 连接 Redis，用于缓存热点请求（如排行榜/统计）和加速会话校验。

**后端（FastAPI） 本地运行**

1. 进入后端目录：

```powershell
cd "d:\Database Courese Design\backend"
```

2. 创建并激活 Python 环境（可选，示例使用 conda）：

```powershell
conda create -n tdf-backend python=3.10 -y
conda activate tdf-backend
```

或使用 venv：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. 安装依赖：

```powershell
pip install -r requirements.txt
```

4. 配置环境变量（示例）：

- `DATABASE_URL`（例如：mysql+pymysql://user:pass@localhost/dbname）
- `SECRET_KEY`（JWT 与其它加密用途）
- SMTP 配置（`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`）

5. 运行后端（默认使用端口 8000）：

```powershell
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

后端 API 根路径为 `http://127.0.0.1:8000/api`。

**前端（Vue） 本地运行**

1. 进入前端目录：

```powershell
cd "d:\Database Courese Design\cycling-forum"
```

2. 安装依赖并启动开发服务器：

```powershell
npm install
npm run dev
```

前端默认由 Vite 提供，通常在 `http://localhost:5173` 运行。

**主要 API（摘要）**

- 用户与认证：

  - `POST /api/async/auth/register` — 异步注册（发送验证邮件）
  - `POST /api/async/auth/login` — 异步登录
  - `GET /api/auth/me` — 获取当前用户信息
  - `PUT /api/auth/update-nickname` — 修改昵称（模态框交互）
  - `GET /api/auth/my-ratings` — 获取用户的所有评分历史（支持分页）
  - `GET /api/auth/my-posts` — 获取用户发表的论坛帖子（支持分页）

- 论坛功能（核心新增）：

  - `GET /api/async/forum/posts` — 分页获取帖子列表
  - `POST /api/async/forum/posts` — 创建新帖子
  - `GET /api/async/forum/posts/{post_id}` — 获取帖子详情（含浏览量统计）
  - `DELETE /api/async/forum/posts/{post_id}` — 删除帖子（作者权限）
  - `POST /api/async/forum/posts/{post_id}/view` — 增加浏览量（Redis Write-Back）
  - `GET /api/async/forum/posts/{post_id}/comments` — 获取评论树状结构（🚀 批量查询优化）
  - `POST /api/async/forum/posts/{post_id}/comments` — 创建评论/回复
  - `DELETE /api/async/forum/posts/{post_id}/comments/{comment_id}` — 删除评论（作者权限）
  - **WebSocket**: `/ws/forum/posts/{post_id}` — 实时评论推送

- 车手评分系统：

  - `POST /api/riders/{id}/ratings` — 提交或修改评分（一个用户对一个车手限一条）
  - `GET /api/riders/{id}/ratings` — 获取车手的所有评价（支持分页）
  - `GET /api/riders/{id}/rating-stats` — 获取车手评分统计（平均分、各星级分布）
  - `DELETE /api/riders/{id}/ratings` — 删除自己的评价

- 数据查询（支持分页与异步）：
  - `GET /api/async/riders` — 分页获取车手列表
  - `GET /api/async/riders/{id}/races` — 分页获取车手参赛记录
  - `GET /api/async/stages/{id}/results` — 分页获取赛段成绩单
  - `GET /api/async/races` — 获取赛事列表（带缓存）

**性能优化与压力测试**

本项目针对高并发场景进行了深度优化，包括论坛模块的批量查询和缓存策略：

### 🚀 论坛性能优化

1. **评论查询批量优化**：

   - **问题**：原递归查询导致 N+1 问题，50 条评论需 50 次数据库查询
   - **方案**：一次性批量查询所有评论，在内存中构建树结构
   - **成果**：查询次数从 O(n) 降到 O(1)，**性能提升 25-50 倍**
   - **实测**：平均响应时间 4ms，可轻松支持数千并发请求

2. **数据库索引优化**（5 个新增索引）：

   ```sql
   ✅ idx_forum_posts_deleted_created      -- 帖子列表查询
   ✅ idx_forum_comments_query             -- 评论过滤查询
   ✅ idx_forum_comments_root_created      -- 子回复批量查询
   ✅ idx_forum_comments_parent_created    -- 直接回复查询
   ✅ idx_forum_comments_author            -- 作者评论查询
   ```

3. **浏览量 Write-Back 策略**：
   - 使用 Redis 缓存热点数据，5 分钟批量回写 MySQL
   - 避免频繁的行锁竞争，减少数据库压力

### 🏗️ 其他性能优化

1.  **异步架构**：
    - 后端全面采用 `FastAPI` + `SQLAlchemy (AsyncSession)`，显著提升了 I/O 密集型任务的并发处理能力。
    - 完全异步的 WebSocket 评论推送
2.  **Redis 缓存层**：
    - 对高频访问的静态数据（如赛事列表、车手基本信息）和统计数据（如评分分布）引入了 Redis 缓存。
    - 浏览量 Write-Back，浏览量更新延迟 5 分钟，大幅减少数据库写入
    - 实现了缓存自动失效与更新机制，平衡了数据一致性与响应速度。
3.  **Locust 压力测试**：
    - 提供了 `backend/locustfile_ratings.py` 脚本，专门用于模拟大规模用户并发评分。
    - **测试特性**：
      - 线程安全的测试用户分配机制（使用 `threading.Lock`）。
      - 自动同步现有评分状态，避免数据库唯一性约束冲突。
      - 模拟真实用户行为权重（查看评分 vs 提交评分）。
    - **运行方式**：
      ```bash
      cd backend
      locust -f locustfile_ratings.py
      ```
4.  **性能测试工具**：
    - 提供 `backend/test_forum_performance.py` 脚本进行论坛评论查询性能基准测试
    - 实时评估论坛系统的并发处理能力

**分页功能说明**

为了提升大数据量下的前端加载速度，本项目在以下模块实现了全栈分页：

- **车手列表**：支持按姓名搜索与分页。
- **车手参赛记录**：在车手详情页中，历史战绩支持分页切换。
- **评分历史**：用户个人中心的“我的评分”支持分页查看。
- **赛段成绩**：大规模成绩单采用后端分页，减少单次传输数据量。

**前端功能亮点**

- 个人中心（`UserProfileView`）：
  - 可查看用户信息、查看头像大图、上传/修改头像、修改昵称与密码
  - **新增**：标签页切换功能，可查看用户的评分历史和发表的论坛帖子
  - 点击帖子可直接跳转到帖子详情页
- 论坛功能（`ForumView` 与 `PostDetailView`）：

  - 论坛首页：帖子列表展示，支持分页加载
  - 帖子详情：
    - 浏览量统计（Redis 缓存 + Write-Back）
    - 多级评论树状结构展示（支持分页）
    - 实时评论推送（WebSocket）
    - 作者权限：发表者可删除自己的帖子和评论
  - 创建帖子：支持标题和正文输入，异步提交

- 点击头像会打开模态框查看大图，模态框内可直接选择并上传新头像，上传后页面会实时更新。

**调试与注意事项**

- 如果前端出现 CORS 问题，确认后端已启用 CORS 并正确允许前端地址。
- 修改后端代码（如新增接口）后请重启 `uvicorn`，以确保路由生效。
- 确保 `.env` 或环境变量中配置了正确的数据库与 SMTP 凭证，邮箱验证与重置密码功能依赖 SMTP 可用性。

**常见命令**

```powershell
# 启动后端（backend 目录）
uvicorn app:app --reload --host 127.0.0.1 --port 8000

# 启动前端（cycling-forum 目录）
npm install
npm run dev
```

**联系 / 作者**

- 仓库所有者: ArcB1213
