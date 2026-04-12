"""
Prometheus 指标监控模块
提供 Agent 系统的可观测性指标
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

from core.logger import LoggerManager

logger = LoggerManager.get_logger("monitoring")


class MetricsCollector:
    """
    指标收集器

    收集并暴露以下指标：
    - 请求计数 (counter)
    - 请求延迟 (histogram)
    - 技能使用统计 (counter)
    - 意图分布 (counter)
    - RAG 检索统计 (counter)
    - 评估分数 (gauge)
    """

    def __init__(self):
        # 计数器
        self._request_count: Dict[str, int] = defaultdict(int)
        self._skill_usage_count: Dict[str, int] = defaultdict(int)
        self._intent_distribution: Dict[str, int] = defaultdict(int)
        self._rag_cache_hits: int = 0
        self._rag_cache_misses: int = 0
        self._error_count: int = 0

        # 直方图（延迟分布）
        self._response_latencies: list = []

        # Gauge（当前值）
        self._active_sessions: int = 0
        self._avg_evaluation_score: float = 0.0

        # 指标锁定（用于线程安全）
        self._lock = False

        # 时间窗口
        self._window_start = time.time()
        self._window_duration = 60  # 1分钟窗口

        logger.info("[MetricsCollector] 初始化完成")

    def record_request(self, intent: str = "unknown") -> None:
        """记录一次请求"""
        self._request_count[intent] += 1

    def record_skill_usage(self, skill_name: str) -> None:
        """记录 Skill 使用"""
        self._skill_usage_count[skill_name] += 1

    def record_intent(self, intent: str) -> None:
        """记录意图识别"""
        self._intent_distribution[intent] += 1

    def record_response_latency(self, latency_ms: float) -> None:
        """记录响应延迟"""
        self._response_latencies.append(latency_ms)

        # 保持直方图大小合理（最多1000个样本）
        if len(self._response_latencies) > 1000:
            self._response_latencies = self._response_latencies[-1000:]

    def record_rag_cache_hit(self) -> None:
        """记录 RAG 缓存命中"""
        self._rag_cache_hits += 1

    def record_rag_cache_miss(self) -> None:
        """记录 RAG 缓存未命中"""
        self._rag_cache_misses += 1

    def record_error(self) -> None:
        """记录错误"""
        self._error_count += 1

    def set_active_sessions(self, count: int) -> None:
        """设置活跃会话数"""
        self._active_sessions = count

    def update_evaluation_score(self, score: float) -> None:
        """更新评估分数（滑动平均）"""
        # 简单的滑动平均
        current = self._avg_evaluation_score
        n = self._request_count_total()
        if n > 0:
            self._avg_evaluation_score = current + (score - current) / n

    def _request_count_total(self) -> int:
        """获取总请求数"""
        return sum(self._request_count.values())

    def _get_stats(self) -> Dict[str, Any]:
        """获取统计数据"""
        # 计算延迟统计
        latencies = self._response_latencies
        if latencies:
            sorted_latencies = sorted(latencies)
            p50 = sorted_latencies[len(sorted_latencies) // 2]
            p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]
            avg_latency = sum(latencies) / len(latencies)
        else:
            p50 = p95 = p99 = avg_latency = 0

        # 计算缓存命中率
        cache_total = self._rag_cache_hits + self._rag_cache_misses
        cache_hit_rate = self._rag_cache_hits / cache_total if cache_total > 0 else 0

        return {
            "timestamp": datetime.now().isoformat(),
            "window_duration_seconds": time.time() - self._window_start,
            "requests": {
                "total": self._request_count_total(),
                "by_intent": dict(self._request_count),
            },
            "latency_ms": {
                "avg": round(avg_latency, 2),
                "p50": round(p50, 2),
                "p95": round(p95, 2),
                "p99": round(p99, 2),
                "sample_count": len(latencies)
            },
            "skills": {
                "usage": dict(self._skill_usage_count),
            },
            "intents": {
                "distribution": dict(self._intent_distribution)
            },
            "rag": {
                "cache_hits": self._rag_cache_hits,
                "cache_misses": self._rag_cache_misses,
                "cache_hit_rate": round(cache_hit_rate, 4)
            },
            "errors": {
                "count": self._error_count,
                "rate": round(self._error_count / max(self._request_count_total(), 1), 4)
            },
            "sessions": {
                "active": self._active_sessions
            },
            "evaluation": {
                "avg_score": round(self._avg_evaluation_score, 4)
            }
        }

    def reset(self) -> None:
        """重置统计（通常在导出后调用）"""
        self._request_count.clear()
        self._skill_usage_count.clear()
        self._intent_distribution.clear()
        self._response_latencies.clear()
        self._rag_cache_hits = 0
        self._rag_cache_misses = 0
        self._error_count = 0
        self._window_start = time.time()
        logger.info("[MetricsCollector] 统计已重置")

    def export_prometheus_format(self) -> str:
        """
        导出 Prometheus 格式的指标

        Returns:
            Prometheus 格式的文本指标
        """
        stats = self._get_stats()

        lines = [
            "# HELP agent_requests_total Total number of agent requests",
            "# TYPE agent_requests_total counter",
        ]

        # 请求计数
        for intent, count in stats["requests"]["by_intent"].items():
            lines.append(f'agent_requests_total{{intent="{intent}"}} {count}')
        lines.append(f'agent_requests_total{{intent="total"}} {stats["requests"]["total"]}')

        # 延迟直方图（使用摘要）
        lines.extend([
            "# HELP agent_response_latency_ms Response latency in milliseconds",
            "# TYPE agent_response_latency_ms summary",
            f'agent_response_latency_ms{{quantile="0.5"}} {stats["latency_ms"]["p50"]}',
            f'agent_response_latency_ms{{quantile="0.95"}} {stats["latency_ms"]["p95"]}',
            f'agent_response_latency_ms{{quantile="0.99"}} {stats["latency_ms"]["p99"]}',
            f'agent_response_latency_ms_sum {stats["latency_ms"]["avg"] * stats["latency_ms"]["sample_count"]}',
            f'agent_response_latency_ms_count {stats["latency_ms"]["sample_count"]}',
        ])

        # Skill 使用
        lines.extend([
            "# HELP agent_skill_usage_total Skill usage count",
            "# TYPE agent_skill_usage_total counter",
        ])
        for skill, count in stats["skills"]["usage"].items():
            lines.append(f'agent_skill_usage_total{{skill="{skill}"}} {count}')

        # 意图分布
        lines.extend([
            "# HELP agent_intent_distribution_total Intent distribution",
            "# TYPE agent_intent_distribution_total counter",
        ])
        for intent, count in stats["intents"]["distribution"].items():
            lines.append(f'agent_intent_distribution_total{{intent="{intent}"}} {count}')

        # RAG 缓存
        lines.extend([
            "# HELP agent_rag_cache_hits_total RAG cache hits",
            "# TYPE agent_rag_cache_hits_total counter",
            f'agent_rag_cache_hits_total {stats["rag"]["cache_hits"]}',
            "# HELP agent_rag_cache_misses_total RAG cache misses",
            "# TYPE agent_rag_cache_misses_total counter",
            f'agent_rag_cache_misses_total {stats["rag"]["cache_misses"]}',
        ])

        # 错误
        lines.extend([
            "# HELP agent_errors_total Total number of errors",
            "# TYPE agent_errors_total counter",
            f'agent_errors_total {stats["errors"]["count"]}',
        ])

        # 活跃会话
        lines.extend([
            "# HELP agent_active_sessions Current number of active sessions",
            "# TYPE agent_active_sessions gauge",
            f'agent_active_sessions {stats["sessions"]["active"]}',
        ])

        # 平均评估分数
        lines.extend([
            "# HELP agent_evaluation_score_avg Average evaluation score",
            "# TYPE agent_evaluation_score_avg gauge",
            f'agent_evaluation_score_avg {stats["evaluation"]["avg_score"]}',
        ])

        return "\n".join(lines)

    def get_summary(self) -> str:
        """获取人类可读的摘要"""
        stats = self._get_stats()

        summary_parts = [
            "=== Agent System Metrics ===",
            f"总请求数: {stats['requests']['total']}",
            f"意图分布: {stats['intents']['distribution']}",
            f"平均延迟: {stats['latency_ms']['avg']:.2f}ms (P95: {stats['latency_ms']['p95']:.2f}ms)",
            f"RAG缓存命中率: {stats['rag']['cache_hit_rate']:.2%}",
            f"错误率: {stats['errors']['rate']:.2%}",
            f"活跃会话: {stats['sessions']['active']}",
            f"平均评估分: {stats['evaluation']['avg_score']:.3f}",
            f"Skill使用: {stats['skills']['usage']}",
        ]

        return "\n".join(summary_parts)


# 全局单例
metrics_collector = MetricsCollector()
