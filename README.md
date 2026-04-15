# MultiTaskQAAssistant

基于 FastAPI + LangChain 的多模块智能客服项目，当前包含用户前台、统一后台管理系统、三层记忆能力、知识库与运行参数管理、用户认证和角色权限控制。

如果你只想先把项目跑起来，直接看 [V3_QUICKSTART.md](./V3_QUICKSTART.md)。

## 当前阶段

2026-04-14 的 Phase 1 已完成以下后台基础能力：

- 统一后台入口与路由壳层
- 角色模型：`super_admin`、`admin`、`operator`、`user`
- 后台仪表盘、记忆管理、知识库管理、系统设置、账号管理
- 记忆管理后台审计日志、服务端搜索筛选和全中文界面
- 前台知识库改为只读展示，仅显示“已发布 + 前台可见 + 当前角色允许访问”的文件
- 前台设置改为只读摘要，运行参数与权限策略统一迁移到后台
- 后台可控制知识文件的“前台显示 / 隐藏”“草稿 / 已发布”“允许访问角色”

## 系统结构

- 用户 API：`http://localhost:8000`
- 后台 API：`http://localhost:8001`
- 用户前台：`http://localhost:5173`
- 后台前端：`http://localhost:5174/admin.html`

主要模块：

- 用户前台
  - 登录、对话、只读知识库、只读设置摘要
- 后台管理系统
  - 总览、记忆管理、知识库管理、系统设置、账号管理
- 记忆系统
  - 短期记忆、中期摘要、长期偏好画像
- 权限系统
  - Token 鉴权、角色判定、后台路由守卫、服务端权限校验

## 环境准备

推荐使用 Conda：

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

## 启动方式

### 1. 启动双后端

在项目根目录执行：

```bash
python backend/run_backends.py
```

启动成功后可访问：

- 用户 API 文档：`http://localhost:8000/docs`
- 用户健康检查：`http://localhost:8000/api/v1/health`
- 后台 API 文档：`http://localhost:8001/docs`
- 后台健康检查：`http://localhost:8001/health`

### 2. 启动用户前台

```bash
cd frontend
npm install
npm run dev
```

访问地址：`http://localhost:5173`

### 3. 启动后台前端

仍然在 `frontend` 目录执行：

```bash
npm run admin
```

访问地址：`http://localhost:5174/admin.html`

说明：

- `npm run admin` 使用 Vite 在 `5174` 端口启动后台页面
- 开发态下，`/api` 代理到 `8000`，`/api/admin` 代理到 `8001`

## 角色说明

- `super_admin`
  - 全部后台能力
  - 可调整角色与系统运行参数
- `admin`
  - 可管理记忆、知识库、设置、账号
- `operator`
  - 可进入后台查看总览、记忆、知识库
  - 对知识库配置为只读，不可修改发布和显隐
- `user`
  - 仅可访问用户前台

## 核心接口

### 用户认证

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/memory`
- `POST /api/v1/auth/memory/resolve`

### 用户前台知识库

- `GET /api/v1/knowledge-base`
- `GET /api/v1/knowledge-base/{document_id}`
- `GET /api/v1/knowledge-base/params`

说明：

- 列表和详情都要求登录
- 只返回当前角色允许访问且已发布、允许前台显示的文件

### 后台接口

- 总览
  - `GET /api/admin/dashboard/summary`
- 记忆管理
  - `GET /api/admin/memory/users`
  - `GET /api/admin/memory/users/{user_id}`
  - `POST /api/admin/memory/users/{user_id}/preferences`
  - `DELETE /api/admin/memory/users/{user_id}/context`
  - `DELETE /api/admin/memory/users/{user_id}`
- 知识库管理
  - `GET /api/admin/knowledge/documents`
  - `PATCH /api/admin/knowledge/documents/{document_id}`
- 系统设置
  - `GET /api/admin/settings/summary`
  - `POST /api/admin/settings/runtime`
- 账号管理
  - `GET /api/admin/users`
  - `PATCH /api/admin/users/{user_id}/role`

更详细的接口说明见 [docs/admin-api.md](./docs/admin-api.md)。

## 文档

- 后台 API 文档：[docs/admin-api.md](./docs/admin-api.md)
- 用户手册：[docs/admin-user-guide.md](./docs/admin-user-guide.md)
- 管理员指南：[docs/admin-admin-guide.md](./docs/admin-admin-guide.md)
- Phase 1 测试报告：[docs/reports/2026-04-14-admin-backoffice-foundation-test-report.md](./docs/reports/2026-04-14-admin-backoffice-foundation-test-report.md)

## 测试与验证

后端验证：

```bash
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest \
  tests.admin.test_auth_role_foundation \
  tests.admin.test_admin_access_and_audit \
  tests.admin.test_user_admin_api \
  tests.admin.test_memory_admin_api \
  tests.admin.test_knowledge_visibility \
  tests.admin.test_settings_admin_api \
  tests.test_memory_admin_localization -v
```

前端验证：

```bash
cd frontend
npm run test:admin
npm run build
```

## 数据目录

- 认证数据库：`data/auth/app.db`
- 记忆上下文：`data/memory/session_context/`
- 长期画像：`data/memory/long_term/`
- 知识文件：`data/docs/`
- 知识文件权限元数据：`data/knowledge/registry.json`
- 后台审计日志：`logs/admin_audit.jsonl`

## 常见问题

### `ModuleNotFoundError: No module named 'app'`

优先在项目根目录执行：

```bash
python backend/run_backends.py
```

### 后台页面可以打开，但接口失败

确认以下三项：

- `python backend/run_backends.py` 已正常启动
- `http://localhost:8001/docs` 可访问
- 后台前端是通过 `npm run admin` 启动，而不是直接打开静态文件

### 端口被占用

默认端口：

- 后端：`8000`、`8001`
- 前端：`5173`、`5174`

请先结束占用端口的进程，再重新启动。
