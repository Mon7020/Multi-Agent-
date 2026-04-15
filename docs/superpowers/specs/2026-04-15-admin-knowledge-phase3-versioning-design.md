# 后台知识库 Phase 3 设计：版本历史与安全回滚

## 1. 背景

截至 2026-04-15，后台知识库 Phase 2 已完成以下能力：

- 稳定 `document_id`
- 知识文件上传、替换、软删除、恢复
- 元数据编辑
- 后台列表、详情、状态筛选
- 前台只读知识库按发布状态、显隐状态和角色范围过滤
- `chunk_count`、`checksum` 等运行指标展示

当前系统已经具备日常运营闭环，但仍缺少一个关键能力：当管理员替换了错误文件、误上传了错误版本，或者希望回退到上一个稳定版本时，系统没有可追溯、可审计、可安全恢复的版本机制。

本阶段目标是在不引入数据库、不引入审批流、不引入在线编辑器的前提下，为后台知识库补齐“版本历史 + 安全回滚”能力。

## 2. 本阶段范围

### 2.1 纳入范围

- 为每个知识文档建立独立的版本历史清单
- 在文档创建、替换、回滚时生成不可变版本快照
- 后台提供版本列表与版本详情查看能力
- 后台提供基于历史版本的回滚能力
- 回滚后重新计算并展示最新文件指标
- 增加版本相关审计日志
- 增加后端、API、前端页面测试与文档

### 2.2 明确决策

- 版本历史只记录“内容版本”与其对应的基础元数据快照
- 回滚采用“基于历史版本生成一个新的当前版本”的方式，而不是直接把系统指针切回旧版本
- 回滚范围采用“受限版 2”：
  - 回滚：文件内容、展示文件名、描述、标签
  - 不自动回滚：`published`、`visible_to_frontend`、`allowed_roles`、`deleted`
- 已删除文档不能直接回滚，必须先恢复再回滚
- 历史版本只允许查看与回滚，不允许直接编辑

### 2.3 不纳入范围

- 在线 diff
- 历史版本正文预览
- 批量回滚
- 审批发布流
- 发布状态、权限范围、删除状态随历史版本自动回退

## 3. 设计目标

本阶段完成后，系统应满足：

- 管理员可查看每个知识文档的版本历史
- 管理员可选择一个历史版本安全回滚
- 回滚成功后，当前文档生成一个新的版本记录
- 回滚不会隐式改变当前发布策略、前台显隐策略、访问角色和删除状态
- 所有版本创建、替换、回滚都能被审计追踪
- 前后端展示的文件指标始终以当前生效版本为准

## 4. 设计原则

### 4.1 当前态与历史态分离

- `registry.json` 继续只表示“当前生效文档状态”
- 历史版本单独存储，不与当前态混写

### 4.2 历史版本不可变

- 版本快照一旦生成，不允许修改
- 后续任何回滚行为都产生一个新的版本，而不是覆写旧版本

### 4.3 回滚只回滚内容，不回滚运营决策

- 历史版本代表知识内容快照
- 发布、显隐、角色范围和删除状态属于当前后台运营策略
- 两者必须解耦，防止旧版本把当前线上策略偷偷改回去

### 4.4 失败时以“当前版本不变”为底线

- 任一步骤失败，都不能让当前文档进入半成功状态
- 必须保证失败后当前文件、当前 registry、当前向量状态仍可用

## 5. 数据模型

### 5.1 当前文档主记录

`data/knowledge/registry.json` 继续保存每个 `document_id` 的当前记录，保持 Phase 2 结构为主，不额外承载历史版本数组。

当前记录新增或明确以下字段：

- `document_id`
- `current_version_id`
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

其中：

- `current_version_id` 指向当前生效版本
- `published`、`visible_to_frontend`、`allowed_roles`、`deleted` 仍只代表当前运营态

### 5.2 版本快照记录

每个版本快照至少包含：

- `version_id`
- `version_no`
- `document_id`
- `action`
  - `create`
  - `replace`
  - `rollback`
- `source_version_id`
  - 仅在 `rollback` 时填写，表示回滚目标版本
- `filename`
- `file_type`
- `snapshot_storage_name`
- `snapshot_storage_path`
- `size`
- `checksum`
- `chunk_count`
- `description`
- `tags`
- `created_at`
- `created_by`
- `reason`
  - 仅在回滚时可选填写

### 5.3 存储目录

沿用当前活动文件目录：

- 当前生效文件：`data/docs/`
- 删除回收目录：`data/knowledge/trash/`
- 当前文档主记录：`data/knowledge/registry.json`

新增历史目录：

- 版本历史根目录：`data/knowledge/history/`
- 单文档历史目录：`data/knowledge/history/<document_id>/`
- 单文档版本清单：`data/knowledge/history/<document_id>/manifest.json`
- 单版本文件快照：`data/knowledge/history/<document_id>/<version_id>/source.<ext>`

### 5.4 版本清单格式

`manifest.json` 建议结构：

- `document_id`
- `current_version_id`
- `latest_version_no`
- `versions`
  - 按时间升序存储完整版本快照元数据

其中 `versions` 为只追加列表，不对旧项做原地修改。

## 6. 状态流转

### 6.1 创建

- 管理员上传新文件
- 系统生成 `document_id`
- 系统生成首个 `version_id`
- 写入当前文件到 `data/docs/`
- 生成版本快照到 `history/<document_id>/<version_id>/`
- 建立当前主记录，`current_version_id` 指向首版本

### 6.2 替换

- 管理员为现有文档上传新文件
- 保持 `document_id` 不变
- 生成新的 `version_id`
- 更新当前活动文件
- 重新构建分块与指标
- 新版本追加到 `manifest.json`
- 当前主记录切换到新 `current_version_id`

### 6.3 回滚

- 管理员选定目标 `target_version_id`
- 系统读取该目标版本快照
- 以该历史版本为输入，生成一个新的当前版本
- 新版本 `action=rollback`
- 新版本 `source_version_id=target_version_id`
- 当前活动文件与当前主记录切换到新版本
- 目标历史版本本身保持不变

## 7. 回滚规则

### 7.1 回滚字段

回滚时同步回退到目标版本的字段：

- 文件内容
- `filename`
- `description`
- `tags`

### 7.2 不自动回滚字段

下列字段保持当前值，不跟随历史版本变化：

- `published`
- `visible_to_frontend`
- `allowed_roles`
- `deleted`

### 7.3 系统重新计算字段

以下字段必须根据回滚后的当前文件重新计算：

- `checksum`
- `chunk_count`
- `size`
- `storage_name`
- `storage_path`
- `updated_at`
- `updated_by`

### 7.4 禁止场景

- 当前文档 `deleted=true` 时不能回滚
- 历史版本文件缺失时不能回滚
- 目标版本不属于当前 `document_id` 时不能回滚

## 8. 服务层设计

核心逻辑继续集中在 `backend/app/services/knowledge_admin_service.py`，新增职责：

- 初始化历史目录与版本清单
- 生成 `version_id` 和递增 `version_no`
- 在创建、替换、回滚后写入历史快照
- 列出版本历史
- 获取版本详情
- 执行回滚

建议新增服务方法：

- `list_document_versions(document_id)`
- `get_document_version(document_id, version_id)`
- `create_version_snapshot(record, *, action, actor_id, reason=None, source_version_id=None)`
- `rollback_document(document_id, target_version_id, *, actor_id, reason=None)`

## 9. 回滚事务原则

回滚流程必须遵循“先构建成功，再切换当前态”的顺序：

1. 读取当前主记录和目标版本快照
2. 校验文档未删除、目标版本存在且属于该文档
3. 将目标历史文件复制到临时位置
4. 基于临时文件执行分块重建和指标计算
5. 全部成功后再覆盖当前活动文件
6. 更新 `registry.json` 当前主记录
7. 追加新的版本快照到 `manifest.json`
8. 写入审计日志

失败要求：

- 任一步失败都不切换当前 `current_version_id`
- 不覆盖当前活动文件
- 不写半条版本记录
- 不留下与当前记录不一致的向量状态

## 10. API 设计

后台接口统一挂在 `/api/admin/knowledge` 下。

### 10.1 `GET /api/admin/knowledge/documents/{document_id}/versions`

用途：

- 获取版本列表

权限：

- `operator`
- `admin`
- `super_admin`

返回字段：

- `document_id`
- `current_version_id`
- `versions`
  - `version_id`
  - `version_no`
  - `action`
  - `source_version_id`
  - `filename`
  - `checksum`
  - `chunk_count`
  - `created_at`
  - `created_by`

### 10.2 `GET /api/admin/knowledge/documents/{document_id}/versions/{version_id}`

用途：

- 获取单个版本快照详情

权限：

- `operator`
- `admin`
- `super_admin`

返回字段：

- 版本快照完整信息
- 是否当前版本

### 10.3 `POST /api/admin/knowledge/documents/{document_id}/rollback`

用途：

- 基于历史版本生成新的当前版本

权限：

- `admin`
- `super_admin`

请求体：

- `target_version_id`
- `reason` 可选

返回：

- 当前文档最新详情
- `new_version_id`
- `target_version_id`

### 10.4 异常响应

- `404`：目标版本不存在
- `400`：目标版本不属于当前文档
- `409`：文档已删除或目标历史版本不可回滚
- `403`：角色无权执行回滚

## 11. 前端页面设计

在现有后台知识库详情区内新增“版本历史”区块，不新开独立页面。

### 11.1 版本列表

默认展示最近 10 条版本记录，按时间倒序：

- `version_no`
- `version_id`
- `action`
- `filename`
- `chunk_count`
- `checksum` 摘要
- `created_by`
- `created_at`
- 当前版本标记

### 11.2 版本详情

选中一个历史版本后，展示：

- `filename`
- `description`
- `tags`
- `size`
- `chunk_count`
- `checksum`
- `action`
- `source_version_id`
- `created_at`
- `created_by`

### 11.3 回滚交互

- `admin` / `super_admin` 可见“回滚到此版本”
- `operator` 仅查看，不可回滚
- 当前文档已删除时，按钮禁用并提示“请先恢复文档”
- 点击回滚前弹确认框，明确说明：
  - 会回滚：文件内容、文件名、描述、标签
  - 不会回滚：发布状态、前台可见、访问角色、删除状态

### 11.4 回滚成功后的页面行为

- 刷新当前文档详情
- 刷新版本历史列表
- 指标区刷新 `size`、`chunk_count`、`checksum`、`updated_at`
- 提示“已基于版本 X 生成新版本 Y”

## 12. 审计日志

继续写入 `logs/admin_audit.jsonl`，新增事件：

- `knowledge.version.create`
- `knowledge.version.replace`
- `knowledge.version.rollback`

其中 `knowledge.version.rollback` 至少记录：

- `document_id`
- `target_version_id`
- `new_version_id`
- `actor_id`
- `reason`
- 回滚字段范围摘要
- 回滚前 `checksum`
- 回滚后 `checksum`
- 回滚前 `chunk_count`
- 回滚后 `chunk_count`

## 13. 错误处理

### 13.1 后端错误

- `target_version_id` 不存在：返回 `404`
- `target_version_id` 不属于当前文档：返回 `400`
- 当前文档已删除：返回 `409`
- 历史文件缺失或损坏：返回 `409`
- 分块重建或入库失败：回滚整体失败，不切换当前版本

### 13.2 审计失败策略

本阶段采用严格策略：若回滚成功但审计写入失败，则整次回滚视为失败。

原因：

- 回滚属于高风险操作
- 没有审计记录的状态变化会形成维护灰区
- 在当前架构下，宁可失败重试，也不接受“状态已变但无法追责”

## 14. 测试策略

### 14.1 后端单元测试

优先使用 `test3` 环境，覆盖：

- 首次创建文档时生成初始版本
- 替换后追加新版本
- 回滚后生成新版本，而不是覆写历史版本
- 回滚后 `published`、`visible_to_frontend`、`allowed_roles`、`deleted` 保持不变
- 已删除文档不能回滚
- 历史文件缺失时回滚失败

### 14.2 API 测试

覆盖：

- `GET versions`
- `GET version detail`
- `POST rollback`
- `operator` 只读
- `admin` / `super_admin` 可回滚

### 14.3 前端交互测试

覆盖：

- 版本列表展示
- 选择版本查看详情
- 回滚确认框
- 回滚成功后列表刷新
- 回滚成功后指标刷新
- 已删除文档禁用回滚

## 15. 交付物

本阶段交付：

- 后端版本历史与回滚服务实现
- 后台版本历史接口
- 后台知识库页面版本历史区块
- 测试代码与测试报告
- `README.md`、管理员指南、API 文档更新

## 16. 成功标准

满足以下条件即可认为本阶段完成：

- 每个知识文档都有可查询的版本历史
- 替换与回滚都会生成新的不可变版本记录
- 回滚后当前文件和指标正确更新
- 回滚不会改变当前发布/显隐/角色/删除状态
- 后台页面可完成版本查看和回滚操作
- 相关测试与构建验证通过

## 17. 实施顺序

建议按以下顺序推进：

1. 后端版本模型与服务层
2. 后台 API
3. 前端版本历史区块与回滚交互
4. 文档、测试报告与回归验证
