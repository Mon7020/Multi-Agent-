# 认证库 MySQL 迁移设计

## 1. 背景

当前项目的账号/认证数据默认存放在 SQLite 文件 [app.db](D:/agentlearn/ai-engineer-training/projects/test2langchain/data/auth/app.db)，对应实现位于 [auth_service.py](D:/agentlearn/ai-engineer-training/projects/test2langchain/backend/app/services/auth_service.py)。  
知识库、记忆、前台策略和审计日志仍分别使用文件系统、JSON 或 JSONL 存储；本次改造不触碰这些模块。

当前代码已经具备 MySQL 连接分支，但仍缺少以下闭环：

- MySQL 专用建表逻辑
- SQLite 到 MySQL 的一次性迁移能力
- 固定种子账号初始化能力
- 与现有测试体系兼容的可验证实现

本次目标是在不改变知识库存储模型的前提下，把认证主存储切换为 MySQL，并完成现有 SQLite 用户迁移。

## 2. 本次范围

### 2.1 纳入范围

- 将认证/账号主存储从 SQLite 切换到 MySQL
- 在 MySQL 中自动创建 `users` 表
- 把现有 SQLite 用户迁移到 MySQL
- 确保存在四个固定角色账号
- 补充配置说明、迁移脚本、测试与操作文档

### 2.2 明确保留不变

- 知识库文件存储与 `registry.json`
- 知识库历史版本与快照目录
- 记忆层 JSON 存储
- 前台展示策略 JSON 存储
- 审计日志 JSONL 存储

### 2.3 明确不纳入

- 知识库改用 MySQL
- 记忆层改用 MySQL
- 引入 SQLAlchemy / Alembic
- 重构整套认证接口或 repository 架构

## 3. 输入约束

### 3.1 目标 MySQL 连接

本地目标库由用户提供，但凭据不写入仓库。仓库内文档与默认配置只保留占位形式：

```text
mysql+pymysql://<user>:<password>@127.0.0.1:3306/testdb?charset=utf8mb4
```

实现与文档均要求通过环境变量或本地配置注入真实连接串。

### 3.2 种子账号

迁移完成后，系统必须确保以下账号存在：

- `super_admin1`
- `admin1`
- `operator1`
- `user1`

初始密码统一为：

```text
ChangeMe123!
```

这些账号用于本地验收和联调，不作为生产默认口令策略。

## 4. 设计目标

本次改造完成后，系统应满足：

- 认证服务默认可直接连接 MySQL 并自动确保表存在
- 现有 SQLite 里的用户可迁移到 MySQL，保留原 `user_id`
- 后台账号管理、登录、鉴权、角色与状态控制行为保持不变
- 知识库、记忆、前台策略和审计模块行为不受影响
- 现有依赖 SQLite 的测试仍能继续运行

## 5. 方案对比

### 方案 A：最小改造，推荐

在现有 [auth_service.py](D:/agentlearn/ai-engineer-training/projects/test2langchain/backend/app/services/auth_service.py) 上补齐 MySQL DDL、迁移脚本和种子账号脚本。

优点：

- 改动最小
- 与当前 API 和测试兼容
- 交付快

缺点：

- 存储层仍然集中在单服务文件内

### 方案 B：抽象 repository 层

将 SQLite/MySQL 存储拆成独立 repository，再由 `AuthService` 调用。

优点：

- 结构更清晰

缺点：

- 明显超出本次范围
- 会扩大回归面

### 方案 C：引入 ORM 和迁移框架

切换到 SQLAlchemy + Alembic。

优点：

- 长期规范

缺点：

- 对当前项目过重
- 会显著增加实施成本

### 结论

采用方案 A。

## 6. 存储设计

### 6.1 认证主表

MySQL 端只引入一张业务表：

#### `users`

字段：

- `id VARCHAR(64) PRIMARY KEY`
- `username VARCHAR(64) NOT NULL UNIQUE`
- `password_salt VARCHAR(255) NOT NULL`
- `password_hash VARCHAR(255) NOT NULL`
- `created_at BIGINT NOT NULL`
- `status VARCHAR(32) NOT NULL DEFAULT 'active'`
- `role VARCHAR(32) NOT NULL DEFAULT 'user'`
- `last_login_at BIGINT NULL`
- `password_updated_at BIGINT NULL`
- `updated_at BIGINT NULL`

索引：

- `PRIMARY KEY (id)`
- `UNIQUE KEY uk_users_username (username)`
- 可选普通索引：`idx_users_role`
- 可选普通索引：`idx_users_status`

推荐建表 SQL：

```sql
CREATE TABLE IF NOT EXISTS users (
  id VARCHAR(64) NOT NULL,
  username VARCHAR(64) NOT NULL,
  password_salt VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  role VARCHAR(32) NOT NULL DEFAULT 'user',
  last_login_at BIGINT NULL,
  password_updated_at BIGINT NULL,
  updated_at BIGINT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_users_username (username),
  KEY idx_users_role (role),
  KEY idx_users_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 6.2 字段语义

必须保持与现有 SQLite 语义一致：

- `id` 是跨模块关联键，迁移时不能重写
- `username` 全局唯一
- `status` 继续使用当前枚举语义：`active` / `disabled`
- `role` 继续使用当前角色语义：`user` / `operator` / `admin` / `super_admin`
- 时间字段继续使用 Unix 时间戳整数

## 7. 服务端设计

### 7.1 `AuthService` 保持现有接口

以下方法语义不变：

- `register`
- `login`
- `get_user_by_id`
- `list_users`
- `update_user_role`
- `update_user_status`
- `create_token`
- `verify_token`

这样可以避免改动后台 API、权限服务和前端调用。

### 7.2 数据库 URL 解析

[auth_service.py](D:/agentlearn/ai-engineer-training/projects/test2langchain/backend/app/services/auth_service.py) 继续支持：

- `sqlite:///...`
- `mysql+pymysql://...`

默认值改为 MySQL 占位说明，但真实连接优先由环境变量 `DATABASE_URL` 提供。

### 7.3 建表逻辑

当前共享 DDL 不能直接安全复用到 MySQL。实现时需要拆分：

- SQLite 使用现有兼容逻辑
- MySQL 使用单独的 `CREATE TABLE IF NOT EXISTS users (...)`

列补齐逻辑也需分支处理，避免 MySQL 与 SQLite 的元数据查询方式混淆。

### 7.4 迁移与种子职责

建议新增独立脚本，而不是把迁移逻辑塞进服务启动：

- 启动只负责确保表存在
- 迁移脚本负责 SQLite -> MySQL 数据复制
- 种子脚本负责确保四个角色账号存在

这样可以避免每次启动都带来副作用。

## 8. 数据迁移设计

### 8.1 迁移来源

来源 SQLite：

[app.db](D:/agentlearn/ai-engineer-training/projects/test2langchain/data/auth/app.db)

### 8.2 迁移规则

逐条读取 SQLite `users` 表，写入 MySQL `users` 表。

保留字段：

- `id`
- `username`
- `password_salt`
- `password_hash`
- `created_at`
- `status`
- `role`
- `last_login_at`
- `password_updated_at`
- `updated_at`

### 8.3 冲突策略

若 MySQL 中已存在相同 `id` 或 `username`：

- 默认按“幂等迁移”处理
- 如果目标记录内容一致，则跳过
- 如果目标记录内容不一致，则报错并停止，不做静默覆盖

这样可以避免把人工修改过的 MySQL 用户意外冲掉。

### 8.4 迁移顺序

1. 确保 MySQL 表存在
2. 扫描 SQLite 用户
3. 逐条写入 MySQL
4. 输出迁移统计
5. 再执行种子账号保证逻辑

## 9. 种子账号设计

### 9.1 保证存在的账号

必须确保存在：

- `super_admin1` -> `super_admin`
- `admin1` -> `admin`
- `operator1` -> `operator`
- `user1` -> `user`

### 9.2 种子策略

建议按用户名查找：

- 若不存在：创建账号，状态设为 `active`
- 若已存在：不改用户名、不重置密码，但修正 `role` 与 `status`

### 9.3 密码策略

仅在“账号不存在”时使用初始密码 `ChangeMe123!` 创建。

如果账号已存在，不主动覆盖原密码，防止破坏已有使用环境。

## 10. 配置设计

### 10.1 默认配置

[settings.py](D:/agentlearn/ai-engineer-training/projects/test2langchain/config/settings.py) 中的 `database_url` 描述需要更新为“推荐使用 MySQL”，但仓库里不写真实密码。

### 10.2 本地运行

本地通过环境变量注入真实连接：

```powershell
$env:DATABASE_URL='mysql+pymysql://root:***@127.0.0.1:3306/testdb?charset=utf8mb4'
```

### 10.3 脚本接口

迁移脚本至少支持：

- 指定源 SQLite 路径
- 指定目标 `DATABASE_URL`
- 幂等执行

种子脚本至少支持：

- 指定目标 `DATABASE_URL`
- 幂等执行

## 11. 测试设计

### 11.1 保留现有测试

现有依赖 `auth_service.reconfigure(database_url=sqlite:///...)` 的测试必须继续可跑，不能因为默认库切到 MySQL 就失效。

### 11.2 新增测试

至少新增以下覆盖：

- MySQL 建表逻辑测试
- 从 SQLite 源库迁移用户到目标库的测试
- 种子账号创建测试
- 种子账号重复执行的幂等测试

### 11.3 最小验收路径

本地验收最小链路：

1. 运行迁移脚本
2. 运行种子脚本
3. 使用 MySQL 配置启动后端
4. 验证登录
5. 验证后台用户列表/详情/状态与角色接口

## 12. 风险与防护

### 12.1 风险：MySQL DDL 与 SQLite 兼容逻辑串用

防护：

- 明确拆分 SQLite/MySQL schema 分支

### 12.2 风险：迁移覆盖现有 MySQL 用户

防护：

- 冲突即报错，不静默覆盖

### 12.3 风险：种子账号反复执行导致密码被重置

防护：

- 已存在账号不重置密码

### 12.4 风险：默认配置把敏感连接串写入仓库

防护：

- 仓库只保留占位配置与文档说明
- 真实连接通过环境变量提供

## 13. 实施后预期结果

完成后，项目将具备以下状态：

- 认证主存储切换到 MySQL
- 现有 SQLite 用户可无损迁移到 MySQL
- 四个角色账号固定存在，便于验收
- 知识库与文件存储完全保持不变
- 现有后台账号管理功能无需改接口即可继续工作
