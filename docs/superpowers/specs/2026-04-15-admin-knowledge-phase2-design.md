# 后台知识库管理 Phase 2 设计

## 1. 背景

2026-04-14 完成的后台 Phase 1 已经提供：

- 统一后台壳层与导航
- 角色与权限底座
- 后台知识库列表入口
- 知识文件的发布 / 隐藏 / 角色范围控制
- 前台只读知识库展示

但当前知识库后台仍停留在“状态开关”层面，缺少日常运营需要的完整管理流程：

- 不能在后台上传新知识文件
- 不能对已有文件做元数据维护
- 不能替换文件并保留稳定业务标识
- 不能做软删除与恢复
- 文档列表缺少分块数量等运营指标
- 后台知识库接口仍以 `filename` 为主键，后续扩展空间不足

本阶段目标是把知识库模块从“后台骨架”推进到“可日常运营”的完整子模块，但仍保持实现边界收敛，不在本阶段引入完整版本仓储、审批流和在线编辑器。

## 2. 本阶段范围

### 纳入范围

- 后台上传知识文件
- 后台编辑知识文件元数据
- 后台替换上传已有知识文件
- 后台软删除与恢复知识文件
- 后台列表与详情显示知识文件指标
- 统一审计日志
- 后端测试与前端页面级测试补齐

### 明确决策

- 编辑方式：仅支持元数据编辑，不支持后台在线修改文件内容
- 文件替换：通过重新上传替换当前文件
- 删除策略：软删除，可恢复
- 已发布文件替换规则：替换成功后直接覆盖当前发布版本
- 恢复策略：恢复后默认 `published=false` 且 `visible_to_frontend=false`

### 不纳入范围

- 富文本或通用在线编辑器
- 完整版本历史浏览器
- 审批流
- 批量上传 / 批量删除 / 批量恢复
- 多租户或组织级知识库隔离

## 3. 目标

本阶段完成后，后台知识库模块应满足：

- 管理员可独立完成上传、编辑、替换、删除、恢复
- 运营可只读查看知识库状态和关键指标
- 前台只读取“未删除 + 已发布 + 前台可见 + 当前角色允许访问”的文档
- 后台列表与前台展示复用统一的知识文件主记录
- 高风险操作具备审计记录

## 4. 设计原则

- 业务主键与文件名解耦：不再以 `filename` 作为唯一标识，统一引入稳定的 `document_id`
- 文件系统优先：继续使用本地文件系统和 JSON 元数据，不引入数据库
- 兼容现有 RAG 接入：保留现有文档入库与分块流程，只补齐后台治理层
- 先运营闭环，再做高级能力：本阶段优先解决完整管理闭环，不提前实现版本中心

## 5. 数据模型

### 5.1 文档主记录

当前 `registry.json` 从“文件名到权限配置”的映射，升级为“文档主记录集合”。

每条记录至少包含：

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

### 5.2 字段说明

- `document_id`
  - 稳定业务主键
  - 一旦创建不再变化
  - 后台 API 和前台展示统一使用该主键
- `filename`
  - 当前展示给用户的原始文件名
  - 可随替换上传更新
- `storage_name`
  - 实际落盘文件名
  - 用于避免同名冲突
- `storage_path`
  - 当前活跃文件或回收文件的实际路径
- `checksum`
  - 文件内容校验值，用于识别替换前后差异
- `chunk_count`
  - 当前文件实际分块数量
  - 作为后台知识库关键运营指标之一
- `deleted`
  - 文档软删除标记

### 5.3 存储目录

- 活跃文件目录：`data/docs/`
- 回收文件目录：`data/knowledge/trash/`
- 知识库主记录：`data/knowledge/registry.json`

软删除时，文件从活跃目录移动到回收目录，并更新主记录状态；恢复时再移动回活跃目录。

## 6. 状态流转

### 6.1 创建上传

- 管理员上传新文件
- 系统生成新的 `document_id`
- 文件写入活跃目录
- 进行分块与向量入库
- 写入主记录
- 默认建议值：
  - `published=false`
  - `visible_to_frontend=false`
  - `allowed_roles=["user","operator","admin","super_admin"]`

### 6.2 元数据编辑

管理员可编辑：

- `description`
- `tags`
- `published`
- `visible_to_frontend`
- `allowed_roles`

元数据编辑不修改文件内容，不重建 `document_id`。

### 6.3 替换上传

- 管理员为已有文档上传新文件
- 保留原 `document_id`
- 使用新文件覆盖当前活跃文件
- 先清理旧文件对应的向量分块，再重新做分块与向量入库
- 更新 `filename`、`storage_name`、`storage_path`、`size`、`checksum`、`chunk_count`
- 若文档当前为已发布，替换成功后继续保持已发布

本阶段不保留完整版本浏览器，仅保留审计日志中的替换前后摘要。

### 6.4 软删除

- 文档标记为 `deleted=true`
- 文件移动到回收目录
- 删除该文档对应的向量分块
- 前台立即不可见
- 后台默认活跃列表不再显示，需切换到“已删除”或“全部”视图查看

### 6.5 恢复

- 文件从回收目录恢复到活跃目录
- 文档标记为 `deleted=false`
- 重新建立该文档的向量分块
- 为降低误操作风险，恢复后强制：
  - `published=false`
  - `visible_to_frontend=false`

## 6.6 迁移策略

系统已存在 Phase 1 的知识文件与旧版 `registry.json`，本阶段需要做兼容迁移。

迁移原则：

- 现有 `data/docs/` 下的文件继续保留
- 旧记录中的 `visible_to_frontend`、`published`、`allowed_roles` 需要被继承
- 对每个现存文件生成新的稳定 `document_id`
- 补齐缺失的 `description`、`tags`、`checksum`、`chunk_count`、审计相关字段默认值

迁移方式建议采用“服务启动或首次读取时自动升级”：

- 若检测到旧版 registry 结构，则自动转换为新版主记录结构
- 转换成功后覆盖写回新版 `registry.json`
- 若某文件存在但无记录，则按默认规则补建记录
- 若记录存在但文件不存在，则跳过前台展示，并在后台标记异常状态供后续清理

## 7. 文件指标设计

后台知识库列表和详情必须展示以下指标：

- 文件大小
- 文件类型
- 分块数量 `chunk_count`
- 上传时间
- 更新时间
- 发布状态
- 前台可见状态
- 删除状态
- 允许访问角色
- 校验值 `checksum`

其中 `chunk_count` 为本阶段明确要求的关键运营指标。

后台和前台都应复用统一的文档指标来源，避免出现后台显示值与前台只读知识库值不一致。

## 8. API 设计

后台接口统一放在 `/api/admin/knowledge` 下。

### 8.1 `GET /api/admin/knowledge/documents`

查询参数：

- `keyword`
- `status=active|deleted|all`
- `published`
- `visible_to_frontend`

返回：

- 文档列表
- 每条记录的完整基础指标

权限：

- `operator`
- `admin`
- `super_admin`

### 8.2 `POST /api/admin/knowledge/documents`

请求类型：

- `multipart/form-data`

请求内容：

- 文件
- `description`
- `tags`
- `published`
- `visible_to_frontend`
- `allowed_roles`

行为：

- 创建新文档
- 分块入库
- 返回文档详情与指标

权限：

- `admin`
- `super_admin`

### 8.3 `GET /api/admin/knowledge/documents/{document_id}`

返回：

- 单文档详情
- 全量状态与指标

权限：

- `operator`
- `admin`
- `super_admin`

### 8.4 `PATCH /api/admin/knowledge/documents/{document_id}`

行为：

- 仅修改元数据
- 不修改文件内容

权限：

- `admin`
- `super_admin`

### 8.5 `POST /api/admin/knowledge/documents/{document_id}/replace`

请求类型：

- `multipart/form-data`

行为：

- 上传新文件替换当前文件
- 保留原 `document_id`
- 重建分块结果
- 更新文档指标

权限：

- `admin`
- `super_admin`

### 8.6 `DELETE /api/admin/knowledge/documents/{document_id}`

行为：

- 软删除文档
- 文件移入回收目录

权限：

- `admin`
- `super_admin`

### 8.7 `POST /api/admin/knowledge/documents/{document_id}/restore`

行为：

- 恢复已删除文档
- 恢复后默认隐藏且未发布

权限：

- `admin`
- `super_admin`

## 9. 前台接口兼容策略

前台仍使用现有只读知识库接口：

- `GET /api/v1/knowledge-base`
- `GET /api/v1/knowledge-base/{document_id}`

但底层应改为基于知识文件主记录筛选，而不是直接按目录文件名推断。

前台仅能看到满足以下全部条件的文档：

- `deleted=false`
- `published=true`
- `visible_to_frontend=true`
- 当前用户角色包含在 `allowed_roles`

## 10. 后台页面设计

### 10.1 页面结构

知识库后台页从 Phase 1 的卡片式状态面板，升级为“列表表格 + 详情侧栏”结构。

页面包含：

- 顶部工具栏
- 文档表格
- 详情侧栏
- 上传 / 替换 / 删除 / 恢复确认交互

### 10.2 顶部工具栏

提供：

- 搜索框
- 状态筛选
- 发布状态筛选
- 前台可见性筛选
- “上传知识文件”按钮

### 10.3 表格列

- 文件名
- 标签
- 文件类型
- 文件大小
- 分块数量
- 发布状态
- 前台可见状态
- 更新时间
- 操作

### 10.4 详情侧栏

展示并编辑：

- 文档基础信息
- `document_id`
- `description`
- `tags`
- `checksum`
- `chunk_count`
- `allowed_roles`
- `published`
- `visible_to_frontend`
- 删除状态
- 最近更新时间与操作人

侧栏中提供操作：

- 保存元数据
- 替换上传
- 软删除
- 恢复

### 10.5 角色交互

- `operator`
  - 仅可查看列表、详情和指标
  - 所有写操作按钮禁用
- `admin` / `super_admin`
  - 可执行全部操作

### 10.6 高风险交互

以下操作必须有二次确认：

- 替换上传
- 软删除
- 恢复

## 11. 权限与安全

- 前端按钮裁剪不作为安全边界
- 所有写接口由服务端做角色校验
- 文件名与路径必须做白名单与路径穿越校验
- 仅允许已定义扩展名：
  - `.txt`
  - `.pdf`
  - `.docx`
- 替换上传、删除、恢复必须记录审计日志

## 12. 审计日志

以下行为必须写入后台审计日志：

- 上传新文档
- 编辑元数据
- 修改发布状态
- 修改前台显隐
- 修改允许角色
- 替换上传
- 软删除
- 恢复

每条审计至少包含：

- `actor_id`
- `module="knowledge"`
- `action`
- `target_type="document"`
- `target_id=document_id`
- `result`
- `timestamp`
- `before`
- `after`

替换上传额外记录：

- 旧文件大小 / 新文件大小
- 旧分块数 / 新分块数
- 旧校验值 / 新校验值

## 13. 测试策略

### 13.1 后端测试

至少覆盖：

- 上传新文档成功
- 上传非法扩展名失败
- 替换上传后保留原 `document_id`
- 替换上传后 `chunk_count` 与校验值更新
- 软删除后前台接口不可见
- 恢复后文档变为未发布且前台隐藏
- `operator` 无法执行写操作
- 审计日志记录正确

### 13.2 前端测试

至少覆盖：

- 知识库后台表格渲染
- 分块数量等指标展示正确
- 上传流程交互
- 替换上传交互
- 删除与恢复交互
- `operator` 只读限制
- 错误提示和确认弹窗

## 14. 验收标准

满足以下条件视为 Phase 2 完成：

- 管理员可在后台上传新知识文件
- 管理员可维护文档描述、标签、发布状态、前台显隐和角色范围
- 管理员可替换已有知识文件且保持稳定 `document_id`
- 管理员可软删除并恢复知识文件
- 恢复后的文档默认未发布且前台隐藏
- 后台列表和详情可显示分块数量等关键指标
- 前台只显示符合权限和状态条件的文档
- 关键写操作全部写入审计日志
- 后端测试、前端测试、前端构建通过

## 15. 实施顺序建议

建议按以下顺序推进：

1. 重构知识文件主记录模型
2. 补齐上传、替换、删除、恢复服务层
3. 调整后台 API
4. 调整前台只读知识库读取逻辑
5. 重构后台知识库页面
6. 补齐测试
7. 更新 README、API 文档和管理员手册
