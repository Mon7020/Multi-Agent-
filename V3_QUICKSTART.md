# ChatService V3 快速启动

本文档面向“先跑起来再说”的场景，按当前仓库实际结构整理，覆盖用户前台、记忆管理后台，以及最新的中文化管理页面。

## 1. 环境准备

在项目根目录 `test2langchain` 执行：

```bash
conda create -n test3 python=3.10 -y
conda activate test3
pip install -r requirements.txt -r backend/requirements.txt
```

如果还没有 `.env`，先复制：

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

至少确认这些变量已经填写：

- `OPENAI_API_KEY`
- `DEEPSEEK_API_KEY`
- `AMAP_API_KEY`
- `TAVILY_API_KEY`
- `DATABASE_URL`

默认数据库：

```env
DATABASE_URL=sqlite:///data/auth/app.db
```

## 2. 启动后端

推荐在项目根目录执行：

```bash
python backend/run_backends.py
```

也可以在 `backend` 目录执行：

```bash
cd backend
python run_backends.py
```

启动成功后可访问：

- 用户 API 文档：`http://localhost:8000/docs`
- 用户健康检查：`http://localhost:8000/api/v1/health`
- 管理 API 文档：`http://localhost:8001/docs`
- 管理健康检查：`http://localhost:8001/health`

## 3. 启动用户前台

新开一个终端窗口：

```bash
cd frontend
npm install
npm run dev
```

用户前台地址：`http://localhost:5173`

## 4. 启动记忆管理后台前端

再开一个终端窗口，在 `frontend` 目录执行：

```bash
npm run admin
```

管理后台地址：`http://localhost:5174/admin.html`

补充说明：

- `npm run admin` 会使用 `5174` 端口启动独立后台页面
- 该命令自带 `--open /admin.html`，通常会自动打开浏览器
- 当前记忆后台已经全部汉化，指标、按钮、状态、提示文案均为中文
- 开发态下，`/api` 代理到 `8000`，`/api/admin` 代理到 `8001`

## 5. 推荐启动顺序

1. 后端：`python backend/run_backends.py`
2. 用户前台：`cd frontend && npm run dev`
3. 管理后台：`cd frontend && npm run admin`

## 6. 启动后检查

建议至少确认这 6 个地址：

- 用户前台：`http://localhost:5173`
- 管理后台：`http://localhost:5174/admin.html`
- 用户 API 文档：`http://localhost:8000/docs`
- 管理 API 文档：`http://localhost:8001/docs`
- 用户健康检查：`http://localhost:8000/api/v1/health`
- 管理健康检查：`http://localhost:8001/health`

## 7. 常见问题

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

### 管理后台接口请求失败

请确认：

- 后端已通过 `python backend/run_backends.py` 正常启动
- 管理 API 可访问 `http://localhost:8001/docs`
- 管理前端是通过 `npm run admin` 启动，而不是直接双击本地静态文件

原因是开发态依赖 Vite 代理把 `/api/admin` 转发到 `8001`。

### 端口被占用

默认端口：

- 后端：`8000`、`8001`
- 前端：`5173`、`5174`

请先结束占用端口的进程，再重新启动。
