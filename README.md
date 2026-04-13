# MultiTaskQAAssistant

基于 FastAPI + LangChain 的多 Agent 智能客服项目，包含：
- Supervisor 路由调度
- Skills 插件化能力
- RAG 检索增强
- 三层上下文记忆

## 运行环境

```bash
conda create -n test3 python=3.10 -y
conda activate test3
pip install -r requirements.txt
```

## 启动后端

```bash
uvicorn backend.app.main:app --reload --port 8000
```

OpenAPI 文档：`http://localhost:8000/docs`

## API（当前真实路由）

### Chat

1. `POST /api/v1/chat`

```json
{
  "session_id": "session_001",
  "user_id": "user_001",
  "message": "X12 Pro 多少钱？",
  "history": []
}
```

2. `POST /api/v1/chat/stream`

请求体同 `/chat`，返回 SSE 数据流。

3. `GET /api/v1/chat/history/{session_id}?user_id=user_001`

4. `DELETE /api/v1/chat/history/{session_id}?user_id=user_001`

说明：`user_id` 是必填，用于会话授权校验。

### Skills

1. `GET /api/v1/skills`
2. `GET /api/v1/skills/stats`
3. `GET /api/v1/skills/{skill_name}`

### Health

1. `GET /api/v1/health`

### Knowledge Base

1. `GET /api/v1/knowledge-base`
2. `POST /api/v1/knowledge-base/upload`（`multipart/form-data`）
3. `GET /api/v1/knowledge-base/{document_id}`
4. `PUT /api/v1/knowledge-base/{document_id}`
5. `DELETE /api/v1/knowledge-base/{document_id}`
6. `GET /api/v1/knowledge-base/params`
7. `POST /api/v1/knowledge-base/params`
8. `POST /api/v1/knowledge-base/reload`
9. `POST /api/v1/knowledge-base/clear-cache`
10. `GET /api/v1/knowledge-base/cache/health`

说明：`document_id` 现在为稳定 ID（文件名），前端已做 URL 编码。

## 前端

```bash
cd frontend
npm install
npm run dev
```

默认地址：`http://localhost:5173`


