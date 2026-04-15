# 后台 API 文档

## 基础信息

- 用户 API 基址：`/api/v1`
- 后台 API 基址：`/api/admin`
- 认证方式：`Authorization: Bearer <token>`

角色边界：

- `super_admin`：全部后台接口
- `admin`：记忆、知识库、设置、账号管理
- `operator`：后台总览、记忆管理、知识库查看
- `user`：无后台接口权限

## 用户前台相关接口

### `GET /api/v1/knowledge-base`

说明：

- 需要登录
- 仅返回“已发布 + 前台可见 + 当前角色允许访问”的文件

响应字段：

- `documents`
  - `id`
  - `filename`
  - `file_path`
  - `file_type`
  - `chunk_count`
  - `size`
  - `upload_time`
  - `update_time`
- `total`

### `GET /api/v1/knowledge-base/{document_id}`

说明：

- 需要登录
- 如果文件不在当前角色可见范围内，返回 `404`

### `GET /api/v1/knowledge-base/params`

说明：

- 需要登录
- 前台只读获取当前运行参数摘要

## 后台总览

### `GET /api/admin/dashboard/summary`

权限：

- `operator`
- `admin`
- `super_admin`

响应：

- `current_user`
- `modules`

## 后台记忆管理

### `GET /api/admin/memory/users`

权限：

- `operator`
- `admin`
- `super_admin`

查询参数：

- `query`：按 `user_id` 或 `username` 搜索
- `active_only`：可选，按内存活跃状态筛选

### `GET /api/admin/memory/users/{user_id}`

权限：

- `operator`
- `admin`
- `super_admin`

说明：

- 返回该用户的上下文快照和长期画像
- 若无记忆数据，返回 `404`

### `POST /api/admin/memory/users/{user_id}/preferences`

权限：

- `operator`
- `admin`
- `super_admin`

请求体：

```json
{
  "key": "preferred_channel",
  "value": "wechat",
  "confidence": 0.8
}
```

说明：

- 写入长期偏好
- 同步更新上下文元数据
- 记录审计日志

### `DELETE /api/admin/memory/users/{user_id}/context`

权限：

- `operator`
- `admin`
- `super_admin`

说明：

- 清理该用户的上下文记忆
- 记录审计日志

### `DELETE /api/admin/memory/users/{user_id}`

权限：

- `operator`
- `admin`
- `super_admin`

说明：

- 清理该用户全部记忆数据
- 记录审计日志

## 后台知识库管理

### `GET /api/admin/knowledge/documents`

权限：

- `operator`
- `admin`
- `super_admin`

响应字段：

- `document_id`
- `filename`
- `file_type`
- `size`
- `upload_time`
- `update_time`
- `visible_to_frontend`
- `published`
- `allowed_roles`

### `PATCH /api/admin/knowledge/documents/{document_id}`

权限：

- `admin`
- `super_admin`

请求体示例：

```json
{
  "visible_to_frontend": true,
  "published": true,
  "allowed_roles": ["user", "operator", "admin", "super_admin"]
}
```

说明：

- 控制前台显示 / 隐藏
- 控制草稿 / 已发布
- 控制允许访问的角色
- 记录审计日志

## 后台系统设置

### `GET /api/admin/settings/summary`

权限：

- `admin`
- `super_admin`

响应：

- `runtime_params`
- `permission_model`
- `frontend_policy`

### `POST /api/admin/settings/runtime`

权限：

- `admin`
- `super_admin`

请求体示例：

```json
{
  "chunk_size": 400,
  "chunk_overlap": 50,
  "top_k": 5,
  "similarity_threshold": 0.3,
  "enable_cache": true,
  "enable_rerank": true,
  "enable_hybrid": true,
  "enable_self_rag": false
}
```

说明：

- 更新运行参数
- 写入后台审计日志
- 如果运行期 RAG 实例已经加载，则同步应用到实例

## 后台账号管理

### `GET /api/admin/users`

权限：

- `admin`
- `super_admin`

查询参数：

- `q`
- `role`
- `status`

### `PATCH /api/admin/users/{user_id}/role`

权限：

- `super_admin`

请求体示例：

```json
{
  "role": "operator"
}
```

## 审计日志

默认文件：

- `logs/admin_audit.jsonl`

当前已覆盖的写入场景：

- 后台总览访问
- 记忆偏好更新
- 记忆清理
- 知识库显隐 / 发布 / 角色范围更新
- 运行参数更新
