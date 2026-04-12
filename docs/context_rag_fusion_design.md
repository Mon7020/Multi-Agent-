# Context+RAG融合方案设计文档

## 📋 概述

本方案旨在打通**上下文管理(Context Engineering)**和**RAG系统**之间的双向信息流，实现更智能的检索和更准确的生成。

## 🎯 核心问题

### 原有架构的问题

1. **Context → RAG 单向缺失**
   - RAG检索时没有充分利用 `SessionContext.metadata`（客户类型、产品偏好、折扣层级）
   - 没有利用 `SessionContext.skill_context`（业务上下文）优化检索策略
   - 查询增强只使用了对话历史，忽略了用户画像和业务状态

2. **RAG → Context 单向缺失**
   - RAG结果没有智能注入到三层记忆中
   - 检索到的关键实体（产品名、型号、价格）没有提取到metadata
   - 没有根据检索质量动态调整上下文使用策略

3. **融合策略不智能**
   - 无论检索质量高低，都采用相同的融合策略
   - 没有根据上下文强度调整生成策略
   - 简单对话和复杂查询采用相同处理方式

## 🏗️ 融合方案架构

### 双向信息流设计

```
┌─────────────────────────────────────────────────────────────┐
│                     用户输入                                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              ContextExtractor (上下文提取器)                 │
│  • 从SessionContext提取metadata                              │
│  • 从skill_context提取业务上下文                             │
│  • 从对话历史提取关键实体                                    │
│  • 生成检索优化提示                                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    ┌──────────────┐
                    │  增强的查询   │
                    └──────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   RAG检索层                                 │
│  • 使用增强查询执行检索                                      │
│  • Self-RAG决策                                            │
│  • Hybrid Search (向量+BM25)                               │
│  • Rerank重排序                                            │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    ┌──────────────┐
                    │  RAG结果     │
                    │  (文档列表)  │
                    └──────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│           RAGResultInjector (RAG结果注入器)                  │
│  • 评估检索质量 (HIGH/MEDIUM/LOW/NONE)                     │
│  • 提取关键实体到metadata                                  │
│  • 更新skill_context                                       │
│  • 更新rag_cache                                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│        AdaptiveFusionEngine (自适应融合引擎)                 │
│  • 计算上下文强度                                           │
│  • 选择融合策略                                             │
│  • 构建融合上下文                                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    ┌──────────────┐
                    │ FusionResult │
                    │   (融合结果)  │
                    └──────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     LLM生成                                 │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 核心组件详解

### 1. ContextExtractor (上下文提取器)

**职责**: 从SessionContext中提取用于优化RAG检索的信息

**提取内容**:
- `metadata`: 客户类型、产品偏好、折扣层级
- `skill_context`: 业务执行产生的上下文（推荐产品、谈判状态等）
- `turn_history`: 对话历史中的关键实体

**输出**:
```python
@dataclass
class ContextAwareQuery:
    original_query: str           # 原始查询
    enhanced_query: str           # 增强后的查询
    entities: List[str]          # 提取的实体
    intent: str                   # 推断的意图
    metadata_hints: Dict          # 元数据提示
    skill_context_applied: bool   # 是否应用了Skill上下文
```

**增强查询示例**:
```
原始查询: "X12多少钱？"
增强查询: "X12多少钱？ 智能手机 客户类型:price_sensitive X12智能手机"
```

### 2. RAGResultInjector (RAG结果注入器)

**职责**: 将RAG结果智能注入到SessionContext

**注入内容**:
1. **质量评估**: 评估检索结果质量（HIGH/MEDIUM/LOW/NONE）
2. **实体提取**: 从文档中提取产品名、型号、价格等
3. **Metadata更新**: 将关键实体更新到`context.metadata`
4. **Skill Context更新**: 将检索摘要更新到`context.skill_context`

**质量评估算法**:
```python
# 综合评分 = 关键词匹配度(30%) + 相似度分数(70%)
keyword_ratio = len(common_keywords) / len(query_keywords)
relevance = keyword_ratio * 0.3 + similarity_score * 0.7
confidence = relevance * 0.6 + coverage * 0.4

# 阈值
HIGH: confidence >= 0.7
MEDIUM: confidence >= 0.4
LOW: confidence >= 0.2
NONE: confidence < 0.2
```

### 3. AdaptiveFusionEngine (自适应融合引擎)

**职责**: 根据检索质量和上下文强度选择最佳融合策略

**融合策略选择**:

| 检索质量 | 上下文强度 | 选择策略 | 说明 |
|---------|-----------|---------|------|
| HIGH | >0.6 | HYBRID | 两者结合，效果最佳 |
| HIGH | ≤0.6 | RAG_PRIMARY | 检索质量高，依赖检索结果 |
| MEDIUM | >0.5 | HYBRID | 两者结合 |
| MEDIUM | ≤0.5 | CONTEXT_PRIMARY | 更依赖上下文 |
| LOW | 任意 | CONTEXT_PRIMARY | 检索质量低，依赖上下文 |
| NONE | 任意 | CONTEXT_ONLY | 无检索结果，仅用上下文 |

**特殊情况**:
- `greeting`/`farewell` 意图 → 始终使用 `CONTEXT_ONLY`

**融合上下文构建**:
```python
# 根据策略决定组件优先级
RAG_PRIMARY: ["rag", "short", "medium", "long", "skill"]
CONTEXT_PRIMARY: ["short", "skill", "rag", "medium", "long"]
HYBRID: ["rag", "short", "skill", "medium", "long"]
CONTEXT_ONLY: ["short", "skill", "medium", "long"]
```

## 📊 融合层核心类

### ContextRAGFusionLayer

**主处理流程**:

```python
def process(
    query: str,
    session_context: SessionContext,
    rag_retrieval_func: Callable,
    intent: str = "general"
) -> FusionResult:
    """
    完整的Context+RAG融合流程

    1. ContextExtractor: 提取检索优化信息
    2. RAG检索: 使用增强查询执行检索
    3. RAGResultInjector: 评估质量并注入
    4. AdaptiveFusionEngine: 选择策略并构建融合上下文
    5. 返回FusionResult供生成使用
    """
```

**FusionResult输出**:
```python
@dataclass
class FusionResult:
    quality: RetrievalQuality           # 检索质量
    fusion_strategy: FusionStrategy      # 融合策略
    confidence: float                    # 置信度
    used_sources: List[str]             # 使用的数据源
    context_summary: str                 # 上下文摘要
    metadata: Dict[str, Any]            # 元数据（增强查询、实体等）
```

## 🚀 使用方法

### 方法一: 使用ChatServiceV3（推荐）

```python
from backend.app.services.chat_service_v3 import chat_service_v3

response = await chat_service_v3.process_message(
    session_id="user_001",
    message="X12投影仪多少钱？",
    enable_context_rag_fusion=True  # 默认启用
)

# 响应中包含融合信息
print(response["fusion_info"])
# {
#     "enabled": True,
#     "quality": "high",
#     "strategy": "hybrid",
#     "confidence": 0.85,
#     "context_strength": 0.7
# }
```

### 方法二: 直接使用融合层

```python
from tools.rag.context_rag_fusion import context_rag_fusion_layer
from core.session_context import SessionContext

# 创建会话上下文
session = SessionContext("test_001")
session.metadata["customer_type"] = "price_sensitive"
session.metadata["current_product"] = "智能手机"

# 定义RAG检索函数
def rag_retrieval(query, metadata_hints):
    return your_rag_tool.retrieve(
        query=query,
        top_k=5,
        use_hybrid=True
    )

# 执行融合处理
fusion_result = context_rag_fusion_layer.process(
    query="X12手机怎么样？",
    session_context=session,
    rag_retrieval_func=rag_retrieval,
    intent="sales"
)

# 获取融合提示词
fusion_prompt = context_rag_fusion_layer.get_fusion_prompt(
    fusion_result,
    system_prompt="你是一个热情的客服"
)

# 调用LLM生成
response = llm.invoke(fusion_prompt + "\n\n用户问题：" + query)
```

## 📈 效果提升

### 定性提升

1. **检索更精准**: 利用用户画像和业务上下文优化查询
2. **上下文更丰富**: RAG结果智能注入，三层记忆联动
3. **生成更智能**: 根据质量自适应选择融合策略
4. **调试更透明**: 清晰的融合过程和策略选择日志

### 定量预期

| 场景 | V2效果 | V3融合效果 | 预期提升 |
|------|--------|-----------|---------|
| 多轮产品咨询 | 检索独立，无上下文感知 | 上下文感知检索，实体增强 | 相关性+15% |
| 价格谈判 | 检索和上下文分离 | 上下文指导检索，RAG注入谈判状态 | 准确率+20% |
| 复杂技术问题 | 简单历史拼接 | Skill上下文+RAG联动 | 问题解决率+25% |
| 简单问候 | 触发不必要检索 | CONTEXT_ONLY跳过检索 | 响应速度+50% |

## 🔍 测试验证

运行测试套件验证融合层功能:

```bash
cd projects/test2langchain
python tests/test_context_rag_fusion.py
```

**测试覆盖**:
- ✅ ContextExtractor: 上下文提取
- ✅ RAGResultInjector: 质量评估和注入
- ✅ AdaptiveFusionEngine: 策略选择
- ✅ ContextRAGFusionLayer: 完整融合流程
- ✅ Context+RAG集成: 双向信息流
- ✅ 融合提示词生成: 结构化提示词

## 📝 架构文件

| 文件 | 说明 |
|------|------|
| `tools/rag/context_rag_fusion.py` | 融合层核心实现 |
| `backend/app/services/chat_service_v3.py` | 集成融合层的聊天服务 |
| `tests/test_context_rag_fusion.py` | 测试套件 |
| `docs/context_rag_fusion_design.md` | 本文档 |

## 🔮 未来优化方向

1. **Query Rewriting**: 基于Skill上下文动态改写查询
2. **Multi-hop Reasoning**: 支持跨轮次的多跳推理
3. **Learning-based Fusion**: 使用机器学习学习最优融合策略
4. **Real-time Adaptation**: 根据用户反馈实时调整融合参数

---

**文档版本**: 1.0
**创建日期**: 2026-04-07
**维护者**: AI Engineer Team
