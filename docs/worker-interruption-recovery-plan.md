# Worker 领单后中断恢复计划

基线为本地 `e99e688`，对应总计划第 4 项。当前 Worker 单独执行 Redis 出队、设置 RQ 状态和保存任务元数据。进程在这些步骤之间退出可能丢失待处理项，在处理期间退出可能留下长期处于 running 的记录。公开查询与重试沿用现有任务 ID 和管理 API。

1. **在隔离 Redis 上建立失败用例。** 使用原项目 Worker 入口或其生产调用链，独立子进程运行一个带同步信号的测试 handler。父进程收到已领单信号后强制结束 Worker，记录队列、RQ、管理 API 的实际状态。覆盖领取与登记之间的窗口。使用临时认证库和独立队列。
2. **选定可恢复的领取方式。** 核对仓库固定的 RQ 版本及部署平台，优先验证其原生执行登记、心跳、过期清理及启动方式。若现有自定义 Worker 继续承担领取，需原子记录领取与所有者，使每个任务都能在待处理队列或可恢复记录中找到。按任务类型领取时也要保留其他任务。
3. **规定超时和重试语义。** 写明心跳间隔、过期时间、检测周期、谁负责检测，以及服务恢复后的最长等待时间。健康长任务应续期。对于索引重建这类可能已产生副作用的操作，过期后优先登记明确、可人工核对和重试的失败状态。每次领取有独立标识，旧执行者迟到的心跳与结果不能覆盖新尝试。处理升级前已有的 queued/running 记录，并保留原有同版本去重和冲突响应。
4. **通过可重复的验收。** 在真实 Redis 用至少两个独立进程验证强制终止后能在公布时限内恢复或转为可重试失败。核对 RQ、任务查询与管理 API 的状态及错误原因。在无存活 Worker 时说明谁能让状态收敛。验证健康长任务、竞争回收、迟到写回、手动重试和旧记录，再跑现有空闲消费、并发去重、管理端回归。
5. **交付。** 将实测耗时、配置默认值、故障前后状态和命令写入总计划或项目已有运维文档。核对差异，提交此项相关的计划、代码、测试和说明到本地 Git，并报告提交哈希以及未验证的部署条件。

## 实施与操作约定（2026-11-25）

- 使用原有自定义 Worker；Redis WATCH/MULTI 原子提交队列移除、任务 running、唯一执行令牌与租约。未匹配类型的任务留在原队列。RQ job 状态同步为 started/failed/finished/queued，但此实现不创建 RQ 原生 execution/started/failed registry，也不使用 RQ Worker 的 heartbeat/清理机制；运维应以本服务及管理 API 为准。
- 默认租约 30 秒，执行中每 5 秒心跳一次；Redis 服务端时间决定过期。空闲 Worker 每次循环（默认 1 秒）扫描，管理 API 的任务读取也会检查目标任务。正常 Redis 响应且有空闲 Worker 时，预计最后心跳后约 31 秒内检查到过期；若 Worker 忙于长任务，下一次领取才扫描。没有运行 Worker 时，单次任务查询或列表查询可触发收敛；没有 Worker 和查询时没有后台定时器，状态不会自行变化，不能承诺固定墙钟时限。
- 过期后标记 `failed`，错误要求核对副作用；不会自动重试。操作员必须先确认旧执行者已终止并核对索引等副作用，再通过管理 API 手动重试。租约令牌阻止旧执行者更新 Redis 状态，但不能撤销或阻止已经发生的外部副作用；业务写入仍需要幂等和版本保护。正常 handler 抛异常沿用原有按次数自动重排的行为。
- 升级前必须停止所有旧版 Worker：旧版没有心跳与令牌，不能与新版安全混跑。升级后扫描把无租约的旧 running 任务标为需核对的 failed，并把出队后尚未登记、仍为 queued 的旧记录放回队列。原有同版本去重及重试冲突检查保留。
- 扫描当前逐条读取任务索引与 job，适用于现有小规模队列；未验证大队列性能、Redis 故障/网络分区或跨平台部署。生产配置目前使用代码默认值；不要把测试用的短租约视为生产阈值。

## 隔离验收记录

使用 Windows Python 3.10、RQ 2.1、WSL 中仅监听本机 16389 的独立 Redis 7.0.15（无持久化）、临时认证 SQLite 与每测试独立队列。测试通过生产 `TaskWorker.run_once/run_forever` 调用链启动独立子进程，以 Redis 信号同步后由父进程强制结束该进程：

- Redis 事务提交前被杀：job 与 API 数据保持 queued，RQ 状态 queued，任务仍在队列。
- handler 内被杀：短租约 1.5 秒配置下，约 1.422 秒通过查询转为 failed；管理 API 与 RQ job 均显示 failed，附需核对副作用的原因。管理 API 手动重试后新领取产生不同令牌，旧令牌的心跳与完成写回被拒绝。
- 默认 30 秒租约：无存活 Worker，反复调用任务查询触发回收，强制终止后 30.093 秒观测到 failed。此数包含进程终止与轮询时延，并非 Redis 不可用时的保证。
- 覆盖了长于租约的健康任务心跳续期、并发回收仅一次、遗留 queued/running 记录、空闲消费、并发去重、重试冲突与后台相关回归。

隔离 Redis 已启动并且临时 `DATABASE_URL`、`RAG_PARAMS_DB` 已设置时，从仓库根目录运行：

```powershell
$env:TEST_REDIS_URL='redis://127.0.0.1:16389/0'
$env:REDIS_PORT='16389'
$env:DATABASE_URL='sqlite:///' + ((Join-Path $env:TEMP ('auth-recovery-' + [guid]::NewGuid().ToString() + '.db')) -replace '\\','/')
$env:RAG_PARAMS_DB=Join-Path $env:TEMP ('rag-recovery-' + [guid]::NewGuid().ToString() + '.db')
$env:HF_HUB_OFFLINE='1'
D:\agentlearn\miniconda\envs\test3\python.exe -m pytest -q -s tests/admin/test_redis_worker_process.py tests/admin/test_task_queue_service.py tests/admin/test_admin_access_and_audit.py tests/admin/test_knowledge_async_tasks.py tests/admin/test_knowledge_base_reload_api.py
```

本轮结果：28 passed。测试 Redis 和认证库应为专用临时实例，不能指向生产数据。
