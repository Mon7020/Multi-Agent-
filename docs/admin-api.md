# 后台 API 文档

## 基础信息

- 用户 API 基础路径：`/api/v1`
- 后台 API 基础路径：`/api/admin`
- 认证方式：`Authorization: Bearer <token>`

角色边界：

- `super_admin`：全部后台权限
- `admin`：总览、记忆、知识库、设置、账号管理
- `operator`：总览、记忆管理、知识库查看
- `user`：无后台权限

## 用户前台接口

### `GET /api/v1/knowledge-base`

说明：

- 需要登录
- 返回当前角色允许访问的只读知识库列表
- 列表过滤条件为：`deleted=false`、`published=true`、`visible_to_frontend=true`、`allowed_roles` 包含当前角色

响应字段：

- `documents`
  - `id`：稳定文档标识，等于后台 `document_id`
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
- 使用稳定 `document_id` 获取详情
- 如果文档未发布、前台隐藏、已删除或当前角色无权访问，返回 `404`

### `GET /api/v1/knowledge-base/params`

说明：

- 需要登录
- 返回当前 RAG 运行参数摘要、缓存统计和运行指标

## 后台总览

### `GET /api/admin/dashboard/summary`

权限：

- `operator`
- `admin`
- `super_admin`

## 后台记忆管理

### `GET /api/admin/memory/users`

权限：

- `operator`
- `admin`
- `super_admin`

查询参数：

- `query`：按 `user_id` 或 `username` 搜索
- `active_only`：按上下文活跃状态筛选

### `GET /api/admin/memory/users/{user_id}`

权限：

- `operator`
- `admin`
- `super_admin`

### `POST /api/admin/memory/users/{user_id}/preferences`

权限：

- `operator`
- `admin`
- `super_admin`

请求体示例：

```json
{
  "key": "preferred_channel",
  "value": "wechat",
  "confidence": 0.8
}
```

### `DELETE /api/admin/memory/users/{user_id}/context`

权限：

- `operator`
- `admin`
- `super_admin`

### `DELETE /api/admin/memory/users/{user_id}`

权限：

- `operator`
- `admin`
- `super_admin`

## 后台知识库管理

知识库后台以稳定 `document_id` 为主键，所有写操作都会写入审计日志，并维护 `chunk_count`、`checksum`、`deleted` 等运行指标。

### `GET /api/admin/knowledge/documents`

权限：

- `operator`
- `admin`
- `super_admin`

查询参数：

- `keyword`：按文件名、描述、标签搜索
- `status`：`active`、`deleted`、`all`
- `published`：可选布尔值
- `visible_to_frontend`：可选布尔值

响应字段：

- `document_id`
- `filename`
- `file_type`
- `storage_name`
- `storage_path`
- `size`
- `checksum`
- `chunk_count`
- `description`
- `tags`
- `published`
- `visible_to_frontend`
- `allowed_roles`
- `deleted`
- `created_at`
- `created_by`
- `updated_at`
- `updated_by`
- `deleted_at`
- `deleted_by`
- `upload_time`
- `update_time`

### `GET /api/admin/knowledge/documents/{document_id}`

权限：

- `operator`
- `admin`
- `super_admin`

说明：

- 返回单个文档完整元数据
- 支持获取已删除文档详情

### `POST /api/admin/knowledge/documents`

权限：

- `admin`
- `super_admin`

请求类型：

- `multipart/form-data`

表单字段：

- `file`：必填，支持 `.txt`、`.pdf`、`.docx`
- `description`：可选
- `tags`：可选，JSON 数组字符串
- `allowed_roles`：可选，JSON 数组字符串
- `published`：可选，布尔值
- `visible_to_frontend`：可选，布尔值

行为：

- 上传新文件到 `data/docs/`
- 写入向量库并刷新 `chunk_count`
- 生成新的稳定 `document_id`
- 写入知识库注册表 `data/knowledge/registry.json`

常见错误：

- `400`：文件名或类型非法
- `409`：同名活动文档已存在

### `PATCH /api/admin/knowledge/documents/{document_id}`

权限：

- `admin`
- `super_admin`

请求体示例：

```json
{
  "description": "产品 FAQ",
  "tags": ["faq", "release"],
  "visible_to_frontend": true,
  "published": true,
  "allowed_roles": ["user", "operator", "admin", "super_admin"]
}
```

说明：

- 仅更新元数据
- 不替换文件内容
- 兼容旧调用方式：仍允许部分历史逻辑按文件名进入服务层

### `POST /api/admin/knowledge/documents/{document_id}/replace`

权限：

- `admin`
- `super_admin`

请求类型：

- `multipart/form-data`

表单字段：

- `file`：必填，新文件

行为：

- 保留原有 `document_id`
- 删除旧文件分块并覆盖活动文件
- 重新生成 `checksum`、`size`、`chunk_count`
- 已发布文档替换后保留原发布状态

常见错误：

- `400`：文档已删除，不能直接替换
- `409`：新文件名与其他活动文档冲突

### `DELETE /api/admin/knowledge/documents/{document_id}`

权限：

- `admin`
- `super_admin`

行为：

- 软删除文档
- 文件从 `data/docs/` 移动到 `data/knowledge/trash/`
- 删除对应向量分块
- 将注册表状态更新为 `deleted=true`

### `POST /api/admin/knowledge/documents/{document_id}/restore`

权限：

- `admin`
- `super_admin`

行为：

- 从回收目录恢复文件
- 重新建立向量分块
- 恢复后强制设置：
  - `deleted=false`
  - `published=false`
  - `visible_to_frontend=false`

## 后台系统设置

### `GET /api/admin/settings/summary`

权限：

- `admin`
- `super_admin`

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

当前知识库相关写入场景：

- `create_document`
- `replace_document`
- `update_document`
- `update_access`
- `delete_document`
- `restore_document`

其他主要写入场景：

- 后台总览访问
- 记忆偏好更新
- 记忆清理
- 运行参数更新
