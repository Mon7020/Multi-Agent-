# 后台账号管理增强 Phase 2 设计

## 1. 背景

当前后台账号管理模块已经具备以下基础能力：

- 用户列表
- 搜索与筛选
- 角色修改

但距离后台治理闭环还差几个关键能力：

- 缺少用户详情视图
- 缺少账号启用 / 禁用能力
- 缺少针对高风险操作的统一服务端权限约束

本阶段目标是在不引入邮件找回、短信验证码、审批流和组织架构的前提下，把账号管理增强到“后台可实际运营”的水平。

## 2. 本阶段范围

### 2.1 纳入范围

- 用户列表与筛选继续保留
- 新增用户详情查看
- 新增账号启用 / 禁用
- 保留角色修改能力
- 补齐服务端权限边界
- 补齐审计日志
- 补齐前后端测试

### 2.2 不纳入范围

- 管理员重置密码
- 邮件验证码或短信找回
- 双因子认证
- 审批流
- 组织架构

## 3. 权限模型

### 3.1 查看权限

- `admin` 可查看账号列表与用户详情
- `super_admin` 可查看账号列表与用户详情

### 3.2 启用 / 禁用权限

- `admin` 可启用 / 禁用 `user` 与 `operator`
- `admin` 不可启用 / 禁用 `admin`
- `admin` 不可启用 / 禁用 `super_admin`
- `admin` 不可禁用自己
- `super_admin` 可启用 / 禁用其他账号
- `super_admin` 不可禁用自己

### 3.3 角色修改权限

- `super_admin` 可修改其他账号角色
- `admin` 不可修改角色

### 3.4 自操作保护

本阶段采用保守策略，避免管理员误把自己锁出后台：

- 任何角色都不可禁用自己
- `super_admin` 不可修改自己的角色

这条规则是显式安全约束，不作为隐式实现细节。

## 4. 产品形态

采用“列表 + 右侧详情面板”的增强方案，不新开独立详情页。

原因：

- 与当前知识库后台的交互结构一致
- 改动范围可控
- 后续若继续扩展账号治理能力，不需要重做布局

## 5. 后端设计

### 5.1 API 范围

保留已有接口：

- `GET /api/admin/users`
- `PATCH /api/admin/users/{user_id}/role`

新增接口：

- `GET /api/admin/users/{user_id}`
- `PATCH /api/admin/users/{user_id}/status`

### 5.2 `GET /api/admin/users/{user_id}`

用途：

- 获取单个用户详情

权限：

- `admin`
- `super_admin`

返回字段建议至少包含：

- `user_id`
- `username`
- `role`
- `status`
- `created_at`
- `updated_at`
- `last_login_at`
- `password_updated_at`

### 5.3 `PATCH /api/admin/users/{user_id}/status`

用途：

- 启用或禁用账号

权限：

- `admin`
- `super_admin`

请求体：

```json
{
  "status": "disabled"
}
```

允许值：

- `active`
- `disabled`

服务端约束：

- `admin` 只能操作 `user` / `operator`
- `admin` 不能操作自己
- `super_admin` 不能操作自己

### 5.4 `PATCH /api/admin/users/{user_id}/role`

保留现有接口路径，但补充更严格的规则：

- 只有 `super_admin` 可调用
- 不允许修改自己的角色

## 6. 服务层设计

继续复用 `backend/app/services/user_admin_service.py` 作为账号管理服务入口，新增以下职责：

- `get_user_detail(actor_role, user_id)`
- `update_status(actor_id, actor_role, user_id, status)`
- 集中校验“能否查看 / 能否改状态 / 能否改角色”

建议新增内部策略函数：

- `_require_manageable_target(actor_id, actor_role, target_user, action)`

设计原则：

- 权限判断必须在服务层做最终收口
- API 层只做 schema 校验和错误映射
- 前端禁用态只是体验优化，不能替代服务端校验

## 7. 认证层数据变更

当前 `auth_service` 已经有 `status` 字段，但缺少正式更新接口。

本阶段建议新增：

- `update_user_status(user_id, status)`

行为：

- 仅更新状态和 `updated_at`
- 不改角色
- 不改密码时间

不新增密码重置相关字段和流程。

## 8. 前端页面设计

文件仍使用：

- `frontend/src/admin/pages/UsersAdminPage.vue`

### 8.1 列表区

保留：

- 搜索
- 角色筛选
- 状态筛选
- 刷新列表

列表字段建议为：

- 用户名
- 用户 ID
- 状态
- 角色
- 最近更新时间

### 8.2 详情区

新增右侧详情面板，选中用户后展示：

- 用户名
- 用户 ID
- 角色
- 状态
- 创建时间
- 最近更新时间
- 最近登录时间
- 密码最近更新时间

### 8.3 操作区

`admin` 可见：

- 禁用账号
- 启用账号

`super_admin` 额外可见：

- 角色选择器
- 保存角色按钮

禁用态规则：

- 当前用户本人：状态切换按钮禁用，并提示“不能禁用当前登录账号”
- `admin` 查看到 `admin` / `super_admin` 时：状态切换按钮禁用
- `admin` 不显示角色编辑控件

## 9. 审计日志

延续 `logs/admin_audit.jsonl`，保留：

- `update_role`

新增：

- `update_status`

`update_status` 至少记录：

- `actor_id`
- `target_id`
- `old_status`
- `new_status`

## 10. 错误处理

### 10.1 状态修改

- `400`：状态值非法
- `403`：越权操作、自操作禁用
- `404`：目标用户不存在

### 10.2 角色修改

- `400`：角色值非法
- `403`：非 `super_admin` 调用，或试图修改自己角色
- `404`：目标用户不存在

## 11. 测试策略

### 11.1 后端测试

补齐 `tests/admin/test_user_admin_api.py`，至少覆盖：

- 列表返回角色与状态
- 详情接口返回完整字段
- `admin` 可禁用普通用户
- `admin` 不可禁用 `admin`
- `admin` 不可禁用自己
- `super_admin` 可修改其他用户角色
- `super_admin` 不可修改自己角色

### 11.2 前端测试

新增或扩展后台账号页测试，至少覆盖：

- 列表加载与筛选
- 选中用户后详情面板刷新
- `admin` 仅看到状态切换，不看到角色编辑
- `super_admin` 看到角色编辑
- 禁用后列表和详情同步刷新

### 11.3 构建验证

继续保持：

- `test3` 环境后端测试
- `npm run test:admin`
- `npm run build`

## 12. 成功标准

本阶段完成后应满足：

- 后台可以查看用户详情
- `admin` / `super_admin` 可以启用 / 禁用账号
- `admin` 不能操作高权限账号
- 任何角色都不能禁用自己
- `super_admin` 可以修改其他账号角色
- `super_admin` 不能修改自己角色
- 前后端测试与构建验证通过

## 13. 实施顺序

建议按以下顺序推进：

1. `auth_service` 补状态更新接口
2. `user_admin_service` 收口权限策略
3. 后台用户 API 补详情与状态修改
4. 前端账号页补详情面板与操作区
5. 测试、文档与回归验证
