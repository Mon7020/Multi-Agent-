"""
评测模块

提供 Test2LangChain 项目的综合评测能力，包括：

1. ResponseEvaluator - Agent 输出质量评测
2. SemanticEvaluator - 语义相似度评测
3. MetricsCollector - 指标收集和追踪
4. EvaluationSuite - 综合评测套件

评测维度：
- Relevance: 回复相关性
- Accuracy: 信息准确性
- Completeness: 回复完整度
- Helpfulness: 整体有用性
- RAG Recall: RAG 召回率
- Hallucination Rate: 幻觉率

使用示例：
    from evaluation import EvaluationSuite
    import asyncio

    suite = EvaluationSuite()
    results = asyncio.run(suite.run_all())
"""

from evaluation.metrics import (
    MetricType,
    MetricResult,
    EvaluationReport,
    METRIC_THRESHOLDS
)
from evaluation.evaluator import ResponseEvaluator
from evaluation.semantic_evaluator import SemanticEvaluator
from evaluation.tracker import EvaluationTracker
from evaluation.runner import EvaluationSuite

__all__ = [
    # 指标
    "MetricType",
    "MetricResult",
    "EvaluationReport",
    "METRIC_THRESHOLDS",
    # 评测器
    "ResponseEvaluator",
    "SemanticEvaluator",
    # 追踪器
    "EvaluationTracker",
    # 综合评测
    "EvaluationSuite",
]

__version__ = "1.0.0"
