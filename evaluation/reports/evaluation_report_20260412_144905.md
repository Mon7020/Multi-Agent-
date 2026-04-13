# Test2LangChain 评测报告

**生成时间**: 2026-04-12 14:49:05

## 评测摘要

- **总测试数**: 15
- **通过数**: 13
- **失败数**: 2
- **通过率**: 86.7%
- **总耗时**: 3.08秒

## MCP 模块评测

**得分**: 100.0%

### protocol

- **状态**: ✅ 通过
- **详情**: 协议消息序列化/反序列化正常

### tools

- **状态**: ✅ 通过
- **详情**: 工具注册正常，共 4 个工具

### client

- **状态**: ✅ 通过
- **详情**: MCP 客户端初始化正常

### server

- **状态**: ✅ 通过
- **详情**: MCP 服务器初始化正常

### integrations

- **状态**: ✅ 通过
- **详情**: 集成完成，共 11 个工具

## SKILLS 模块评测

**得分**: 100.0%

### registry

- **状态**: ✅ 通过
- **详情**: 技能注册表正常，共 0 个技能

### manager

- **状态**: ✅ 通过
- **详情**: 技能管理器正常，共 5 个技能

### individual_skills

- **状态**: ✅ 通过
- **详情**: 技能初始化正常: ['sales_agent', 'tech_support', 'negotiation', 'customer_classifier', 'chat']

## RAG 模块评测

**得分**: 100.0%

### import

- **状态**: ✅ 通过
- **详情**: RAG 模块导入正常

### initialization

- **状态**: ✅ 通过
- **详情**: RAG 初始化检查通过

## AGENT 模块评测

**得分**: 100.0%

### factory

- **状态**: ✅ 通过
- **详情**: Agent 工厂正常: ['supervisor', 'sales_agent', 'tech_support_agent']

### supervisor

- **状态**: ✅ 通过
- **详情**: Supervisor Agent 初始化正常

### context

- **状态**: ✅ 通过
- **详情**: 会话上下文管理正常

## INTEGRATION 模块评测

**得分**: 0.0%

### api_endpoints

- **状态**: ❌ 失败
- **错误**: No module named 'app'

### end_to_end

- **状态**: ❌ 失败
- **错误**: No module named 'app'
