# 2026-04-15 后台知识库 Phase 2 测试报告

## 范围

本报告覆盖后台知识库 Phase 2 已落地的能力：

- 知识库注册表升级到稳定 `document_id`
- 后台上传、替换、软删除、恢复接口
- 前台只读知识库改为基于注册表和 `document_id`
- 后台知识库页面的指标展示、状态筛选和读写权限边界

## 执行环境

- 仓库：`test2langchain`
- 分支：`feature/admin-knowledge-phase2`
- Python：`D:\agentlearn\miniconda\envs\test3\python.exe`
- Node：仓库 `frontend` 目录内 `npm`

## 后端验证

执行命令：

```bash
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_admin_registry -v
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_admin_phase2_api -v
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_visibility -v
```

结果：

- `tests.admin.test_knowledge_admin_registry`：2/2 通过
- `tests.admin.test_knowledge_admin_phase2_api`：1/1 通过
- `tests.admin.test_knowledge_visibility`：5/5 通过

覆盖点：

- 旧版知识库注册表自动迁移到 v2
- 未登记文件自动补入注册表
- 后台创建文档
- 替换文档并保留同一 `document_id`
- 软删除文档
- 恢复文档后默认隐藏且未发布
- 前台知识库列表返回稳定 `document_id`
- 前台按角色、发布状态、显隐和删除状态过滤
- `operator` 无法修改后台知识库状态

说明：

- 后端知识库测试使用假的 RAG tool，避免依赖真实向量库和外部模型下载，聚焦接口与注册表行为。

## 前端验证

执行命令：

```bash
cd frontend
npm run test:admin
npm run build
```

结果：

- `vitest`：3 个测试文件、7 个测试全部通过
- `vite build`：构建成功

覆盖点：

- 后台导航与壳层状态
- 后台知识库页面展示 `chunk_count` 等指标
- `operator` 只读态
- 已删除文档状态展示
- 后台知识库上传入口与状态筛选 UI 契约

## 本阶段结论

当前 Phase 2 已具备继续推进的基础：

- 后台知识库读写链路已经闭环
- 前后台对同一文档注册表和稳定 `document_id` 达成一致
- 删除与恢复策略符合当前产品决策
- 后台知识库页面已经具备运营可用性

## 后续建议

1. 补充后台知识库页面的更多交互测试，例如保存、删除、恢复和替换成功后的 UI 刷新
2. 增加文档详情接口的前端使用场景，减少列表数据和详情数据的耦合
3. 在后续阶段补充更完整的管理员操作手册和演示截图
