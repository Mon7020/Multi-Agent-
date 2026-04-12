"""
评测指标定义模块
定义 Agent 系统各项评测指标
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List


class MetricType(Enum):
    """指标类型枚举"""
    # 对话质量指标
    RELEVANCE = "relevance"           # 回复与问题相关性 (0-1)
    ACCURACY = "accuracy"             # 信息准确性 (0-1)
    COMPLETENESS = "completeness"     # 回复完整度 (0-1)
    HELPFULNESS = "helpfulness"       # 整体有用性 (0-1)

    # 业务指标
    NEGOTIATION_EFFECTIVENESS = "negotiation_effectectiveness"  # 谈判有效性
    SALES_CONVERSION = "sales_conversion"  # 销售转化率
    CUSTOMER_SATISFACTION = "customer_satisfaction"  # 客户满意度

    # 技术指标
    RAG_RECALL = "rag_recall"         # RAG 召回率 (0-1)
    RAG_PRECISION = "rag_precision"   # RAG 精确率 (0-1)
    RESPONSE_LATENCY = "response_latency"  # 响应延迟 (ms)
    TOOL_USAGE_RATE = "tool_usage_rate"  # 工具使用率

    # 安全指标
    SENSITIVE_INFO_LEAK = "sensitive_info_leak"  # 敏感信息泄露 (0-1, 越小越好)
    HALLUCINATION_RATE = "hallucination_rate"  # 幻觉率 (0-1, 越小越好)


@dataclass
class MetricResult:
    """单条指标结果"""
    metric_type: MetricType
    value: float
    details: str = ""
    threshold: float = None  # 及格线

    def is_passed(self) -> bool:
        """是否通过"""
        if self.threshold is None:
            return True
        return self.value >= self.threshold

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_type": self.metric_type.value,
            "value": round(self.value, 4),
            "details": self.details,
            "threshold": self.threshold,
            "passed": self.is_passed()
        }


@dataclass
class EvaluationReport:
    """完整评测报告"""
    session_id: str
    timestamp: str
    query: str
    response: str

    # 指标得分
    metrics: Dict[str, MetricResult] = field(default_factory=dict)

    # 总体评分
    overall_score: float = 0.0
    grade: str = "N/A"  # A/B/C/D/F

    # 详细数据
    skill_results: List[Dict] = field(default_factory=list)
    rag_results: List[Dict] = field(default_factory=list)
    tool_usage: List[str] = field(default_factory=list)

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def calculate_overall(self) -> float:
        """计算总体评分"""
        if not self.metrics:
            return 0.0

        # 权重配置
        weights = {
            MetricType.RELEVANCE: 0.20,
            MetricType.ACCURACY: 0.25,
            MetricType.COMPLETENESS: 0.15,
            MetricType.HELPFULNESS: 0.15,
            MetricType.RAG_RECALL: 0.10,
            MetricType.SENSITIVE_INFO_LEAK: 0.10,
            MetricType.HALLUCINATION_RATE: 0.05,
        }

        total_weight = sum(weights.values())
        weighted_sum = 0.0

        for metric_type, weight in weights.items():
            if metric_type.value in self.metrics:
                # 对于"越小越好"的指标，取反
                if metric_type in [MetricType.SENSITIVE_INFO_LEAK, MetricType.HALLUCINATION_RATE]:
                    weighted_sum += (1 - self.metrics[metric_type.value].value) * weight
                else:
                    weighted_sum += self.metrics[metric_type.value].value * weight

        self.overall_score = weighted_sum / total_weight

        # 计算等级
        if self.overall_score >= 0.9:
            self.grade = "A"
        elif self.overall_score >= 0.8:
            self.grade = "B"
        elif self.overall_score >= 0.7:
            self.grade = "C"
        elif self.overall_score >= 0.6:
            self.grade = "D"
        else:
            self.grade = "F"

        return self.overall_score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "query": self.query,
            "response": self.response,
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
            "overall_score": round(self.overall_score, 4),
            "grade": self.grade,
            "skill_results": self.skill_results,
            "tool_usage": self.tool_usage,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EvaluationReport':
        """从字典创建"""
        report = cls(
            session_id=data["session_id"],
            timestamp=data["timestamp"],
            query=data["query"],
            response=data["response"],
            overall_score=data.get("overall_score", 0.0),
            grade=data.get("grade", "N/A"),
            skill_results=data.get("skill_results", []),
            rag_results=data.get("rag_results", []),
            tool_usage=data.get("tool_usage", []),
            metadata=data.get("metadata", {})
        )
        report.metrics = {
            k: MetricResult(
                metric_type=MetricType(v["metric_type"]),
                value=v["value"],
                details=v.get("details", ""),
                threshold=v.get("threshold")
            )
            for k, v in data.get("metrics", {}).items()
        }
        return report


# 指标阈值配置
METRIC_THRESHOLDS = {
    MetricType.RELEVANCE: 0.7,
    MetricType.ACCURACY: 0.8,
    MetricType.COMPLETENESS: 0.6,
    MetricType.HELPFULNESS: 0.7,
    MetricType.RAG_RECALL: 0.6,
    MetricType.SENSITIVE_INFO_LEAK: 0.1,  # 越小越好
    MetricType.HALLUCINATION_RATE: 0.1,  # 越小越好
    MetricType.RESPONSE_LATENCY: 5000,  # ms
}
