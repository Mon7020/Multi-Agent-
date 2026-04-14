# MultiTaskQAAssistant

基于 FastAPI + LangChain 的多 Agent 智能客服项目，包含对话、知识库、技能统计、用户认证，以及独立的三层记忆管理后台。

如果你只想快速启动项目，直接看 [V3_QUICKSTART.md](./V3_QUICKSTART.md)。

## 当前功能

- 用户前台：登录、对话、知识库、设置页
- 用户认证：注册、登录、Token 鉴权、当前用户信息查询
- 三层记忆：短期记忆、中期压缩摘要、长期用户画像
- 记忆管理后台：查看用户记忆、写入偏好、清除上下文、清除全部记忆
- 后端双服务：用户 API 使用 `8000`，管理 API 使用 `8001`
- 前端双入口：用户前台使用 `5173`，管理后台使用 `5174/admin.html`

## 最近同步

### 2026-04-14

- 三层记忆已按 `user_id` 持久化绑定，不再只依赖临时 `session_id`
- 用户上下文快照落盘到 `data/memory/session_context/{user_id}_context.json`
- 长期用户画像落盘到 `data/memory/long_term/{user_id}_profile.json`
- 新增独立记忆管理后台 API，端口 `8001`
- 新增独立记忆管理后台前端，端口 `5174`，页面为 `http://localhost:5174/admin.html`
- 记忆管理后台页面已全部汉化，指标、按钮、状态、提示文案均为中文
- 后端统一通过 `python backend/run_backends.py` 同时启动两个服务

## 环境准备

建议使用 Conda：

```bash
conda create -n test3 python=3.10 -y
conda activate test3
pip install -r requirements.txt -r backend/requirements.txt
```

如果没有 `.env`，先复制：

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

至少需要确认这些环境变量：

- `OPENAI_API_KEY`
- `DEEPSEEK_API_KEY`
- `AMAP_API_KEY`
- `TAVILY_API_KEY`
- `DATABASE_URL`

默认数据库是：

```env
DATABASE_URL=sqlite:///data/auth/app.db
```

如果改用 MySQL，可写成：

```env
DATABASE_URL=mysql+pymysql://user:password@host:port/database?charset=utf8mb4
```

## 启动方式

### 1. 启动后端

在项目根目录执行：

```bash
python backend/run_backends.py
```

也可以进入 `backend` 目录执行：

```bash
cd backend
python run_backends.py
```

启动后可访问：

- 用户 API 文档：`http://localhost:8000/docs`
- 用户健康检查：`http://localhost:8000/api/v1/health`
- 管理 API 文档：`http://localhost:8001/docs`
- 管理健康检查：`http://localhost:8001/health`

### 2. 启动用户前台

```bash
cd frontend
npm install
npm run dev
```

访问地址：`http://localhost:5173`

### 3. 启动记忆管理后台前端

仍然在 `frontend` 目录执行：

```bash
npm run admin
```

访问地址：`http://localhost:5174/admin.html`

说明：

- `npm run admin` 会使用 Vite 在 `5174` 端口启动独立页面
- 该命令包含 `--open /admin.html`，默认会自动打开管理后台页面
- 开发态下，`/api` 会代理到 `8000`，`/api/admin` 会代理到 `8001`

## 推荐启动顺序

1. `python backend/run_backends.py`
2. `cd frontend && npm run dev`
3. `cd frontend && npm run admin`

## 主要接口

### 认证

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/memory`
- `POST /api/v1/auth/memory/resolve`

所有受保护接口都需要：

```http
Authorization: Bearer <token>
```

### 对话

- `POST /api/v1/chat`
- `POST /api/v1/chat/stream`
- `GET /api/v1/chat/history/{session_id}`
- `DELETE /api/v1/chat/history/{session_id}`

### 技能

- `GET /api/v1/skills`
- `GET /api/v1/skills/stats`
- `GET /api/v1/skills/{skill_name}`

### 知识库

- `GET /api/v1/knowledge-base`
- `POST /api/v1/knowledge-base/upload`
- `GET /api/v1/knowledge-base/{document_id}`
- `PUT /api/v1/knowledge-base/{document_id}`
- `DELETE /api/v1/knowledge-base/{document_id}`
- `GET /api/v1/knowledge-base/params`
- `POST /api/v1/knowledge-base/params`
- `POST /api/v1/knowledge-base/reload`
- `POST /api/v1/knowledge-base/clear-cache`
- `GET /api/v1/knowledge-base/cache/health`

### 记忆管理后台

- `GET /api/admin/memory/users`
- `GET /api/admin/memory/users/{user_id}`
- `POST /api/admin/memory/users/{user_id}/preferences`
- `DELETE /api/admin/memory/users/{user_id}/context`
- `DELETE /api/admin/memory/users/{user_id}`

用途：

- 查看某个用户的短期记忆、中期摘要、长期画像
- 从后台直接写入长期偏好
- 清除已持久化上下文
- 清除某个用户的全部记忆

## 记忆后台说明

管理后台页面地址：

- 开发态：`http://localhost:5174/admin.html`

当前页面包含：

- 用户列表与在线状态
- 核心指标卡片
- 长期画像查看
- 上下文元数据查看
- 最近对话查看
- 中期记忆摘要查看
- 偏好修正与记忆清理操作

当前界面文案已统一为中文，包括：

- 指标名称
- 状态标签
- 操作按钮
- 空状态提示
- 成功和失败消息
- 确认弹窗

## 数据落盘位置

- 认证数据库：`data/auth/app.db`
- 会话上下文：`data/memory/session_context/`
- 长期用户画像：`data/memory/long_term/`

## 常见问题

### `ModuleNotFoundError: No module named 'app'`

优先在项目根目录执行：

```bash
python backend/run_backends.py
```

### `No module named 'uuid_utils'`

重新安装依赖：

```bash
conda activate test3
pip install -r requirements.txt -r backend/requirements.txt
```

### 端口被占用

默认端口：

- 后端：`8000`、`8001`
- 前端：`5173`、`5174`

请先结束占用端口的进程，再重新启动。
