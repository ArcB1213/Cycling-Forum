# 数据库课程设计（Cycling Forum 项目）———— AI 生成的 README

本仓库为课程设计项目代码，包含用于展示“三大环赛”数据的前端、后端与数据处理脚本，并扩展为一个简单的社交论坛（含用户注册/邮箱验证/头像与个人中心）。

**项目概览**

- 前端：Vue 3 + TypeScript（Vite 构建）
- 后端：FastAPI + SQLAlchemy（开发时使用 MySQL，使用 Alembic 管理迁移）
- 认证：JWT（访问/刷新 token） + `passlib` 密码哈希
- 邮件：SMTP（用于邮箱验证与重置密码）
- 文件：头像文件上传并通过后端静态路由提供访问

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

  - `POST /api/auth/register` — 注册（会发送验证邮件）
  - `POST /api/auth/login` — 登录（返回 `access_token` / `refresh_token`）
  - `POST /api/auth/verify-email` — 邮箱验证
  - `POST /api/auth/resend-verification` — 重新发送验证邮件
  - `POST /api/auth/forgot-password` — 发送密码重置邮件
  - `POST /api/auth/reset-password` — 重置密码
  - `PUT /api/auth/update-nickname` — 修改昵称（需登录）
  - `PUT /api/auth/update-password` — 修改密码（需登录）
  - `POST /api/auth/update-avatar` — 上传并更新当前用户头像（需登录）

- 文件上传与静态：

  - `POST /api/upload/avatar` — 仅上传图片并返回 `avatar_url`
  - 已上传文件通过 `/uploads/avatars/<filename>` 提供访问

- 数据查询（示例）：
  - `GET /api/races`, `GET /api/riders`, `GET /api/editions/...` 等（详见 `backend/app.py`）

**前端功能亮点**

- 个人中心（`UserProfileView`）：可查看用户信息、查看头像大图、上传/修改头像、修改昵称与密码。
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
