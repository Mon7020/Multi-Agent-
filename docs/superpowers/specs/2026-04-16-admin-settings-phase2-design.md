# 后台系统设置增强 Phase 2 设计

## 1. 背景

当前后台系统设置模块已经具备以下基础能力：

- 后台可查看当前运行参数摘要
- 后台可修改 RAG 运行参数
- 后台可查看权限模型说明
- 后台可查看前台只读策略摘要

但它仍停留在“参数入口 + 说明页”阶段，距离后台治理模块还有明显差距：

- 运行参数缺少更清晰的分组、校验边界和独立错误处理
- 前台展示策略还只是写死在服务层返回值中，不能作为正式配置管理
- 设置模块与知识库模块、记忆模块的边界虽然已形成共识，但还没有被设计文档和接口边界明确固化
- 前台页面还没有消费正式的“前台展示策略”配置

本阶段目标是在不引入数据库、不引入动态角色权限编辑器、不把用户画像混入系统设置的前提下，把系统设置模块增强到“可运营、可配置、可测试”的水平。

## 2. 本阶段范围

### 2.1 纳入范围

- 继续保留后台运行参数治理
- 将前台展示策略升级为正式可配置项
- 继续在后台展示只读权限模型说明
- 明确系统设置、知识库、记忆管理三者的职责边界
- 补齐后端服务、API、前端页面、测试和文档

### 2.2 明确决策

- 用户个人偏好继续归记忆管理，不进入系统设置
- 前台知识库只能查看允许展示的文件，且始终只读
- 后台知识库可以查看全部文件，并继续负责访问规则维护
- 知识库单文件的 `published`、`visible_to_frontend`、`allowed_roles` 继续在知识库模块维护
- 系统设置模块只负责系统级运行参数和前台展示策略

### 2.3 不纳入范围

- 用户个人偏好编辑
- 知识库单文件访问规则编辑
- 动态角色权限模型编辑
- 密码重置、组织架构、审批流
- 前台知识库在线编辑

## 3. 设计目标

本阶段完成后，系统应满足：

- 管理员可以在后台集中维护系统运行参数
- 管理员可以在后台集中维护前台展示策略
- 设置页中不同区块可独立保存、独立报错、互不污染
- 前台知识库和前台设置摘要可以读取正式配置，而不是依赖写死文案
- 设置模块不会和知识库模块、记忆模块产生职责重叠

## 4. 模块边界

### 4.1 系统设置模块负责

- RAG 运行参数
- 前台展示策略
- 权限模型说明的只读展示

### 4.2 知识库模块负责

- 所有知识文件的后台列表、详情和编辑
- 单文件访问规则维护
- 发布状态、前台显隐、允许角色维护
- 版本历史与安全回滚

### 4.3 记忆管理模块负责

- 用户上下文快照
- 用户长期偏好
- 偏好修正、上下文清理、记忆审计

### 4.4 前台模块边界

- 前台知识库：只展示允许展示的文件，只读不可编辑
- 前台设置页：只展示允许公开的摘要信息，不承担后台治理功能

## 5. 数据模型与存储

### 5.1 运行参数

继续使用现有 `rag_params_manager` 作为运行参数的唯一来源，不新增第二套存储。

当前纳入配置的参数包括：

- `chunk_size`
- `chunk_overlap`
- `top_k`
- `similarity_threshold`
- `enable_cache`
- `enable_rerank`
- `enable_hybrid`
- `enable_self_rag`

### 5.2 前台展示策略

新增独立配置文件：

- `data/settings/frontend_policy.json`

设计原则：

- 与知识库注册表、用户记忆、账号数据分离
- 只保存“系统级展示策略”
- 不承载知识库单文件访问规则

建议结构：

```json
{
  "knowledge_base": {
    "intro_text": "这里只展示当前账号角色允许访问且已经发布的知识文件。",
    "empty_state_text": "当前角色暂无可访问的知识文件。",
    "readonly_notice": "知识文件的编辑、发布和访问规则统一在后台维护。",
    "show_document_metrics": true
  },
  "settings": {
    "show_summary": true,
    "show_runtime_overview": true,
    "show_permission_notice": true,
    "readonly_notice": "前台只保留系统摘要，正式配置请在后台维护。"
  }
}
```

### 5.3 默认值策略

- 若 `frontend_policy.json` 不存在，系统返回内置默认值
- 若文件内容非法，系统记录日志并回退到默认值
- 不允许通过 API 提交任意未知字段

## 6. 后端设计

### 6.1 服务层职责

继续复用：

- `backend/app/services/settings_admin_service.py`

新增职责：

- 读取默认前台展示策略
- 从 JSON 文件读取和持久化前台展示策略
- 校验前台展示策略请求体
- 在 `get_summary()` 中返回完整配置
- 为运行参数和前台策略分别写审计日志

不负责：

- 修改知识库访问规则
- 修改用户个人偏好
- 动态修改角色权限边界

### 6.2 API 设计

保留：

- `GET /api/admin/settings/summary`
- `POST /api/admin/settings/runtime`

新增：

- `POST /api/admin/settings/frontend-policy`

#### `GET /api/admin/settings/summary`

权限：

- `admin`
- `super_admin`

返回：

- `runtime_params`
- `frontend_policy`
- `permission_model`

#### `POST /api/admin/settings/runtime`

权限：

- `admin`
- `super_admin`

用途：

- 更新运行参数

请求体继续使用当前运行参数结构。

#### `POST /api/admin/settings/frontend-policy`

权限：

- `admin`
- `super_admin`

用途：

- 更新系统级前台展示策略

请求体示例：

```json
{
  "knowledge_base": {
    "intro_text": "这里只展示允许当前角色访问的知识文件。",
    "empty_state_text": "当前暂无可展示的知识文件。",
    "readonly_notice": "前台只读，编辑请前往后台。",
    "show_document_metrics": true
  },
  "settings": {
    "show_summary": true,
    "show_runtime_overview": true,
    "show_permission_notice": true,
    "readonly_notice": "如需修改配置，请由管理员在后台操作。"
  }
}
```

### 6.3 运行参数校验

后端必须在服务层做最终校验，建议至少包含：

- `chunk_size >= 100`
- `chunk_overlap >= 0`
- `chunk_overlap < chunk_size`
- `top_k >= 1`
- `0 <= similarity_threshold <= 1`

### 6.4 前台展示策略校验

校验原则：

- 顶层只允许 `knowledge_base`、`settings`
- 每个分组只允许白名单字段
- `show_*` 字段必须是布尔值
- `*_text`、`*_notice` 字段必须是字符串，长度受限

## 7. 前端设计

### 7.1 后台设置页结构

继续使用：

- `frontend/src/admin/pages/SettingsAdminPage.vue`

页面升级为 3 个稳定区块：

1. 运行参数
2. 前台展示策略
3. 权限模型说明

### 7.2 运行参数区块

建议按组展示：

- 分块参数
  - `chunk_size`
  - `chunk_overlap`
- 检索参数
  - `top_k`
  - `similarity_threshold`
- 能力开关
  - `enable_cache`
  - `enable_rerank`
  - `enable_hybrid`
  - `enable_self_rag`

交互要求：

- 独立保存按钮
- 独立加载态
- 独立成功提示
- 保存失败时不影响前台策略区块

### 7.3 前台展示策略区块

建议提供以下控件：

- 前台设置摘要是否显示
- 前台设置页是否显示运行参数摘要
- 前台设置页是否显示权限说明
- 前台知识库介绍文案
- 前台知识库空状态文案
- 前台知识库只读提示文案
- 前台知识库是否显示文件指标摘要
- 前台设置页只读提示文案

交互要求：

- 独立保存按钮
- 独立保存态
- 与运行参数区块解耦
- 错误信息明确显示到本区块

### 7.4 权限模型说明区块

继续保留只读展示，不提供在线编辑。

界面中需要明确标注：

- 知识库访问规则在知识库模块维护
- 用户个人偏好在记忆管理模块维护
- 设置模块只维护系统级配置

## 8. 前台消费方式

### 8.1 前台知识库页

建议更新：

- `frontend/src/components/KnowledgeBasePanel.vue`

消费 `frontend_policy.knowledge_base`：

- `intro_text`
- `empty_state_text`
- `readonly_notice`
- `show_document_metrics`

但不改变现有访问过滤原则：

- 只返回已发布
- 只返回前台可见
- 只返回当前角色允许访问的文件

### 8.2 前台设置摘要页

建议更新：

- `frontend/src/components/SettingsPanel.vue`

消费 `frontend_policy.settings`：

- `show_summary`
- `show_runtime_overview`
- `show_permission_notice`
- `readonly_notice`

## 9. 错误处理与审计

### 9.1 错误处理

运行参数更新：

- 非法数值返回 `400`
- 写入失败返回 `500`

前台展示策略更新：

- 非法字段或非法类型返回 `400`
- 写入失败返回 `500`

权限错误：

- 非 `admin` / `super_admin` 返回 `403`

### 9.2 审计日志

建议新增或明确以下动作：

- `update_runtime`
- `update_frontend_policy`

日志内容至少包含：

- `actor_id`
- `module=settings`
- `action`
- `target_type`
- `target_id`
- `result`
- 关键变更摘要

## 10. 测试方案

### 10.1 后端服务测试

- 默认前台展示策略加载
- 配置文件覆盖默认值
- 非法字段被拒绝
- 运行参数非法值被拒绝
- 审计日志写入成功

### 10.2 后端 API 测试

- `admin` 可读取设置摘要
- `admin` 可更新运行参数
- `admin` 可更新前台展示策略
- 普通 `user` 被拒绝
- 非法请求返回 `400`

### 10.3 前端页面测试

- 设置页加载成功
- 运行参数区块保存成功
- 运行参数区块保存失败
- 前台展示策略区块保存成功
- 前台展示策略区块保存失败
- 两个区块状态互不干扰

### 10.4 回归验证

- 后端 settings 测试通过
- 后台前端测试通过
- `npm run build` 通过
- 前台知识库与前台设置摘要编译通过

## 11. 验收标准

满足以下条件视为本阶段完成：

- 后台设置页形成正式的系统级治理模块
- 运行参数和前台展示策略均可独立保存
- 前台展示策略脱离写死返回值，成为正式配置
- 前台知识库和前台设置摘要可消费正式配置
- 设置模块与知识库、记忆模块的边界清晰且已在文档中固化
- 测试、构建和文档均补齐

## 12. 实施顺序建议

1. 扩展 `settings_admin_service.py`
2. 新增前台展示策略存储与校验
3. 扩展 `/api/admin/settings` 接口
4. 重构后台 `SettingsAdminPage.vue`
5. 更新前台 `KnowledgeBasePanel.vue` 与 `SettingsPanel.vue`
6. 补齐测试与文档
