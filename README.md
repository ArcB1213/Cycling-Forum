# 数据库课程设计

本仓库为同济大学计算机系的数据库课程设计项目代码，包含用于展示“三大环赛”数据的前端、后端与数据处理脚本

**项目概览**

- 前端：Vue 3 + TypeScript（Vite 构建）
- 后端：Flask + SQLAlchemy（SQLite 数据库用于本地开发）
- 数据：CSV 抓取脚本 + 导入脚本，将爬取结果导入数据库
- API：REST 风格接口，供前端调用

**快速目录结构**

- `backend/`：Flask 后端应用，包含 `app.py`、`models/`、数据库文件 `cycling_stats.db`（若已生成）
- `cycling-forum/`：前端 Vue 项目（Vite + TypeScript）
- `tdf-scraper.py`, `tdf-scraper2.py`：爬虫脚本（用于抓取赛事数据）
- `temp.py`：示例图像/原型生成脚本
- `README.md`：本文件

**本地开发 — 先决条件**

- Node.js（建议 18+）与 npm 或 pnpm/yarn
- Python 3.8+（建议使用虚拟环境或 conda）
- 推荐：在 Windows 上使用 PowerShell

**后端（Flask） 本地运行**

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

3. 安装依赖（若项目包含 requirements.txt）：

```powershell
pip install -r requirements.txt
```

4. 运行后端（默认端口 5000）：

```powershell
python app.py
```

后端启动后，API 根路径通常为 `http://127.0.0.1:5000/api`。

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

默认使用 Vite，前端会在 `http://localhost:5173`（或命令行显示的端口）提供预览。

**已实现的主要 API（快速列表）**

- `GET /api/races` — 返回赛事列表（环法、环意等）
- `GET /api/races/<race_id>/editions` — 返回该赛事的届数（按年份）
- `GET /api/editions/<edition_id>/stages` — 返回该届赛事的赛段列表
- `GET /api/stages/<stage_id>/results` — 返回某一赛段的成绩列表
- `GET /api/riders` — 返回车手列表
- `GET /api/riders/<rider_id>` — 返回车手统计（参赛数、冠军数、效力车队）
- `GET /api/riders/<rider_id>/races` — 返回该车手的所有参赛赛段记录
- `GET /api/riders/<rider_id>/wins` — 返回该车手的所有赛段冠军记录

(更多细节请查看 `backend/app.py`）

**前端已实现页面**

- `LandingPage`：主页，具有颜色主题与导航入口
- `RacesView`：赛事 → 届数 → 赛段 的下拉联动，并展示赛段成绩
- `RidersView`：车手搜索与浏览
- `RiderDetailView`：车手详情页，包含参赛记录、赛段冠军与车队历史

**数据导入与爬虫**

- `tdf-scraper.py`, `tdf-scraper2.py`：爬取数据脚本（请在运行前阅读脚本头部注释，确认依赖与目标 URL）
- 数据导入脚本（若存在于 `backend/models/` 或 `backend/scripts/`）会将 CSV 数据插入到 SQLite 数据库

**调试与测试提示**

- 如果前端调用 API 返回 CORS 错误，确认后端已启用 CORS（`backend/app.py` 使用 flask-cors）并且后端在运行。
- 若出现依赖缺失（如 `flask` 或 `sqlalchemy`），请在后端环境中运行 `pip install -r requirements.txt` 或手动安装所需包。

**常见命令一览（PowerShell）**

```powershell
# 启动后端（在 backend 目录）
python app.py

# 启动前端（在 cycling-forum 目录）
npm install
npm run dev
```

**联系/作者**

- 仓库所有者 / GitHub: `ArcB1213`

---
