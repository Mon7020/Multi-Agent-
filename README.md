# Test2LangChain 项目运行指南

## 📋 项目概述

这是一个基于 **LangChain + DeepSeek** 的智能客服系统，支持：
- 多任务问答
- RAG（检索增强生成）
- 上下文工程（多轮对话）
- 技能系统（销售、技术支持、议价）
- 前后端分离架构

---

## 🚀 环境准备

### 1. 克隆项目

```bash
cd d:\agentlearn\ai-engineer-training\projects
# 项目已存在: test2langchain
```

### 2. 创建虚拟环境（推荐）

```bash
# 使用 conda
conda create -n test2langchain python=3.10
conda activate test2langchain

# 或使用 venv
python -m venv venv
.\venv\Scripts\activate
```

### 3. 安装依赖

```bash
cd test2langchain
pip install -r requirements.txt
```

### 4. 配置环境变量

复制 `.env.example` 为 `.env`：

```bash
copy .env.example .env
```

编辑 `.env` 文件：

```env
# DeepSeek API 配置
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# 应用配置
APP_NAME=智能客服系统
LOG_LEVEL=INFO
```

---

## 🖥️ 运行方式

### 方式一：仅运行后端 API（推荐开发使用）

```bash
cd test2langchain

# 方式1：直接运行
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# 方式2：使用 FastAPI
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# 方式3：Python 模块方式
python -m backend.app.main
```

**API 地址**: http://localhost:8000

**API 文档**: http://localhost:8000/docs

---

### 方式二：前后端分离

#### 1. 启动后端

```bash
# 终端1
cd test2langchain
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. 启动前端

```bash
# 终端2
cd test2langchain/frontend
npm install
npm run dev
```

**前端地址**: http://localhost:5173

---

### 方式三：构建前端后一体化运行

```bash
# 1. 构建前端
cd test2langchain/frontend
npm install
npm run build

# 2. 启动后端（自动加载前端）
cd test2langchain
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

**访问**: http://localhost:8000

---

## 🧪 运行测试

### 运行所有测试

```bash
cd test2langchain
python -m pytest tests/ -v
```

### 运行特定测试

```bash
# 上下文工程测试（推荐）
python -m pytest tests/test_context_engineering.py -v

# 基准测试
python tests/run_benchmark.py

# 智能评估
python tests/smart_evaluation.py

# 全套评估
python tests/full_evaluation.py
```

### 查看测试报告

```bash
# 查看最新报告
ls -t reports/
cat reports/$(ls -t reports/ | head -1)
```

---

## 📡 API 接口

### 聊天接口

```
POST /api/v1/chat
Content-Type: application/json

{
  "message": "X12 Pro多少钱？",
  "user_id": "user_001",
  "session_id": "session_001"
}
```

### 健康检查

```
GET /api/v1/health
```

### 知识库管理

```
GET /api/v1/knowledge_base/documents
POST /api/v1/knowledge_base/rebuild
```

### 评估接口

```
GET /api/v1/evaluation/metrics
POST /api/v1/evaluation/run
```

---

## 📁 项目结构

```
test2langchain/
├── backend/
│   └── app/
│       ├── main.py           # FastAPI 主入口
│       ├── api/v1/            # API 路由
│       │   ├── chat.py        # 聊天接口
│       │   ├── skills.py      # 技能接口
│       │   ├── health.py      # 健康检查
│       │   └── ...
│       └── services/          # 业务逻辑
│           ├── chat_service_v2.py
│           └── evaluation_service.py
│
├── frontend/                  # Vue.js 前端
│   ├── src/
│   │   ├── components/        # 组件
│   │   ├── api/              # API 调用
│   │   └── App.vue           # 主应用
│   └── index.html
│
├── tools/                     # 工具层
│   ├── rag/                  # RAG 工具
│   │   ├── rag_tool.py      # RAG 主工具
│   │   ├── context_engineering.py  # 上下文工程
│   │   ├── enhanced_context.py    # 增强上下文
│   │   └── ...
│   ├── skills/              # 技能系统
│   └── amap_weather_tool.py # 天气工具
│
├── core/                      # 核心模块
│   ├── session_context.py   # 会话上下文
│   ├── agent_factory.py     # Agent 工厂
│   └── logger.py            # 日志系统
│
├── tests/                    # 测试文件
│   ├── test_context_engineering.py
│   ├── benchmark.py
│   └── full_evaluation.py
│
├── reports/                   # 测试报告
├── data/                      # 数据文件
│   ├── docs/                # 知识库文档
│   └── memory/              # 记忆存储
│
├── config/
│   └── settings.py          # 配置管理
│
└── requirements.txt          # Python 依赖
```

---

## ⚙️ 主要配置

### RAG 配置 (config/settings.py)

```python
# 向量模型
embedding_model: "shibing624/text2vec-base-chinese"  # 中文模型
embedding_dimension: 768

# ChromaDB
chroma_persist_directory: "./chroma_data"

# 缓存
cache_max_size: 10000
cache_ttl: 86400  # 24小时

# RAG 参数
top_k: 5
rerank_top_k: 3
```

### Redis 配置

```python
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

---

## 🔧 常见问题

### 1. 缺少依赖

```bash
pip install -r requirements.txt
```

### 2. Redis 连接失败

确保 Redis 已启动：

```bash
# Windows
redis-server

# 或使用 Docker
docker run -d -p 6379:6379 redis
```

### 3. 模型下载失败

首次运行会自动下载中文向量模型（shibing624/text2vec-base-chinese），需要网络连接。

### 4. 端口占用

```bash
# 查看端口占用
netstat -ano | findstr :8000

# 结束进程
taskkill /PID <PID> /F
```

---

## 📊 性能测试

### 运行基准测试

```bash
cd test2langchain
python tests/run_benchmark.py
```

### 查看性能指标

报告保存在 `reports/` 目录：

- `benchmark_report_*.json` - 基准测试
- `full_evaluation_report_*.json` - 全套评估
- `smart_evaluation_report_*.json` - 智能评估

---

## 🎯 推荐流程

### 1. 开发调试

```bash
# 终端1：启动后端
uvicorn backend.app.main:app --reload --port 8000

# 终端2：启动前端
cd frontend && npm run dev

# 访问 http://localhost:5173
```

### 2. 生产部署

```bash
# 1. 构建前端
cd frontend && npm run build

# 2. 配置 Nginx 或直接运行
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# 3. 配置反向代理（Nginx）
```

### 3. 运行测试

```bash
# 上下文工程测试（推荐先运行）
python -m pytest tests/test_context_engineering.py -v

# 查看测试结果
cat reports/test_context_engineering_summary.txt
```

---

## 📝 其他工具脚本

| 脚本 | 说明 |
|------|------|
| `check_vector_dim.py` | 检查向量维度 |
| `diagnose_rag.py` | RAG 诊断 |
| `diagnose_bm25.py` | BM25 诊断 |
| `rebuild_vectors.py` | 重建向量索引 |
| `rebuild_with_optimization.py` | 优化重建 |

---

## 📞 技术支持

如有问题，请检查：

1. `reports/` 中的测试报告
2. `docs/context_engineering_implementation.md` - 上下文工程文档
3. `tests/README.md` - 测试说明

---

**最后更新**: 2026-04-07
