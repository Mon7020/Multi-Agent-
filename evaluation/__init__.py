"""
评测模块

提供RAG系统的评测功能：
- metrics.py: 基础指标定义
- semantic_evaluator.py: 语义评测器（改进版）

使用示例：
    from evaluation.semantic_evaluator import SemanticEvaluator
    from evaluation.metrics import MetricType, MetricResult, EvaluationReport
"""

from .metrics import (
    MetricType,
    MetricResult,
    EvaluationReport,
    METRIC_THRESHOLDS
)

try:
    from .semantic_evaluator import (
        SemanticEvaluator,
        SemanticMetrics
    )
except ImportError as e:
    import logging
    logging.getLogger("evaluation").warning(f"语义评测器导入失败: {e}")
    SemanticEvaluator = None
    SemanticMetrics = None

__all__ = [
    # 基础指标
    'MetricType',
    'MetricResult',
    'EvaluationReport',
    'METRIC_THRESHOLDS',
    # 语义评测器
    'SemanticEvaluator',
    'SemanticMetrics',
]
