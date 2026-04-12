"""
Agent 输出评测器
使用 LLM-as-Judge 和规则引擎对 Agent 输出进行多维度评测
"""

import json
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

from core.logger import LoggerManager
from evaluation.metrics import (
    MetricType, MetricResult, EvaluationReport,
    METRIC_THRESHOLDS
)

logger = LoggerManager.get_logger("evaluator")


class ResponseEvaluator:
    """
    Agent 输出质量评测器

    评测维度：
    1. Relevance - 回复与问题相关性
    2. Accuracy - 信息准确性（是否基于 RAG 结果）
    3. Completeness - 回复完整度
    4. Helpfulness - 整体有用性
    5. RAG Recall - RAG 召回率
    6. Sensitive Info Leak - 敏感信息泄露
    7. Hallucination Rate - 幻觉率
    """

    def __init__(self, llm=None):
        self._llm = llm
        self._initialized = False

    def _ensure_llm(self):
        """确保 LLM 已初始化"""
        if self._llm is None and not self._initialized:
            try:
                import os
                import sys
                sys.path.append(os.path.dirname(os.path.dirname(__file__)))
                from config.settings import settings

                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(
                    api_key=settings.api.deepseek_api_key or settings.api.openai_api_key,
                    base_url=settings.api.deepseek_base_url or settings.api.openai_base_url,
                    model="deepseek-chat",
                    temperature=0.1
                )
                self._initialized = True
                logger.info("[ResponseEvaluator] LLM 初始化完成")
            except Exception as e:
                logger.error(f"[ResponseEvaluator] LLM 初始化失败: {e}")

    def evaluate(
        self,
        query: str,
        response: str,
        context: Dict[str, Any] = None
    ) -> EvaluationReport:
        """
        评测单次 Agent 输出

        Args:
            query: 用户问题
            response: Agent 回复
            context: 上下文（包含 rag_results, skill_results 等）

        Returns:
            EvaluationReport
        """
        context = context or {}
        session_id = context.get("session_id", "unknown")

        report = EvaluationReport(
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            query=query,
            response=response,
            skill_results=context.get("skill_results", []),
            rag_results=context.get("rag_results", []),
            tool_usage=context.get("tools_used", [])
        )

        # 1. Relevance - 回复相关性
        report.metrics[MetricType.RELEVANCE.value] = self._evaluate_relevance(query, response)

        # 2. RAG Recall - RAG 召回率
        rag_results = context.get("rag_results", [])
        report.metrics[MetricType.RAG_RECALL.value] = self._evaluate_rag_recall(
            query, response, rag_results
        )

        # 3. Accuracy - 准确性
        report.metrics[MetricType.ACCURACY.value] = self._evaluate_accuracy(
            query, response, rag_results
        )

        # 4. Completeness - 完整性
        report.metrics[MetricType.COMPLETENESS.value] = self._evaluate_completeness(
            query, response, context
        )

        # 5. Helpfulness - 有用性
        report.metrics[MetricType.HELPFULNESS.value] = self._evaluate_helpfulness(
            query, response, context
        )

        # 6. Sensitive Info Leak - 敏感信息泄露
        report.metrics[MetricType.SENSITIVE_INFO_LEAK.value] = self._evaluate_sensitive_leak(
            response, context
        )

        # 7. Hallucination Rate - 幻觉率
        report.metrics[MetricType.HALLUCINATION_RATE.value] = self._evaluate_hallucination(
            query, response, rag_results
        )

        # 计算总体评分
        report.calculate_overall()

        logger.info(
            f"[ResponseEvaluator] 评测完成: session={session_id}, "
            f"总分={report.overall_score:.3f}, 等级={report.grade}"
        )

        return report

    def _evaluate_relevance(self, query: str, response: str) -> MetricResult:
        """评估回复相关性"""
        if not response or len(response) < 5:
            return MetricResult(
                metric_type=MetricType.RELEVANCE,
                value=0.0,
                details="回复过短",
                threshold=METRIC_THRESHOLDS.get(MetricType.RELEVANCE)
            )

        query_keywords = set(query.lower().split())
        response_lower = response.lower()

        # 计算关键词覆盖率
        matched = sum(1 for kw in query_keywords if len(kw) > 1 and kw in response_lower)
        coverage = matched / len(query_keywords) if query_keywords else 0

        # 检查是否答非所问
        negative_patterns = ["无法回答", "不知道", "无法处理", "无法理解"]
        is_off_topic = any(p in response_lower for p in negative_patterns) and coverage < 0.2

        if is_off_topic:
            return MetricResult(
                metric_type=MetricType.RELEVANCE,
                value=max(coverage, 0.2),
                details="回复可能偏离主题",
                threshold=METRIC_THRESHOLDS.get(MetricType.RELEVANCE)
            )

        return MetricResult(
            metric_type=MetricType.RELEVANCE,
            value=min(coverage + 0.3, 1.0),  # 基础分 0.3
            details=f"关键词匹配覆盖率: {coverage:.2%}",
            threshold=METRIC_THRESHOLDS.get(MetricType.RELEVANCE)
        )

    def _evaluate_rag_recall(
        self,
        query: str,
        response: str,
        rag_results: List[Dict]
    ) -> MetricResult:
        """评估 RAG 召回率"""
        if not rag_results:
            return MetricResult(
                metric_type=MetricType.RAG_RECALL,
                value=0.5,  # 无 RAG 结果时给中等分
                details="无 RAG 检索结果",
                threshold=METRIC_THRESHOLDS.get(MetricType.RAG_RECALL)
            )

        if not response:
            return MetricResult(
                metric_type=MetricType.RAG_RECALL,
                value=0.0,
                details="无回复",
                threshold=METRIC_THRESHOLDS.get(MetricType.RAG_RECALL)
            )

        response_lower = response.lower()
        recalled = 0
        total = len(rag_results)

        for doc in rag_results:
            content = doc.get("content", "").lower()
            # 检查文档内容是否在回复中被引用
            # 取文档中的关键句子
            key_phrases = content[:200].split("。")
            for phrase in key_phrases:
                phrase = phrase.strip()
                if len(phrase) > 5 and phrase in response_lower:
                    recalled += 1
                    break

        recall_rate = recalled / total if total > 0 else 0

        return MetricResult(
            metric_type=MetricType.RAG_RECALL,
            value=recall_rate,
            details=f"RAG 召回率: {recalled}/{total}",
            threshold=METRIC_THRESHOLDS.get(MetricType.RAG_RECALL)
        )

    def _evaluate_accuracy(
        self,
        query: str,
        response: str,
        rag_results: List[Dict]
    ) -> MetricResult:
        """评估信息准确性"""
        # 检查回复中是否有与 RAG 结果矛盾的信息
        if not rag_results:
            # 无 RAG 结果时，主要依赖规则判断
            return self._rule_based_accuracy(query, response)

        response_lower = response.lower()
        inaccuracies = 0

        # 检查敏感信息泄露（如果回复中提到了不该说的价格）
        sensitive_patterns = [
            r"成本价?[:：]?\s*\d+",
            r"底价?[:：]?\s*\d+",
            r"最多只能?降?到?\s*\d+"
        ]

        for pattern in sensitive_patterns:
            if re.search(pattern, response_lower):
                inaccuracies += 1

        # 检查数字一致性（回复中的价格应该与 RAG 结果一致）
        price_pattern = r"(\d{3,5})元"
        response_prices = re.findall(price_pattern, response)
        rag_prices = []
        for doc in rag_results:
            rag_prices.extend(re.findall(price_pattern, doc.get("content", "")))

        if response_prices and rag_prices:
            # 检查回复中的价格是否在合理范围内
            rag_max = max(int(p) for p in rag_prices)
            rag_min = min(int(p) for p in rag_prices)
            for price_str in response_prices:
                price = int(price_str)
                # 如果价格低于最低价，可能有问题
                if rag_min <= price <= rag_max:
                    continue
                else:
                    inaccuracies += 0.5

        accuracy = max(1.0 - inaccuracies * 0.2, 0.0)

        return MetricResult(
            metric_type=MetricType.ACCURACY,
            value=accuracy,
            details=f"准确性评分: {accuracy:.2%}, 发现 {inaccuracies} 个潜在问题",
            threshold=METRIC_THRESHOLDS.get(MetricType.ACCURACY)
        )

    def _rule_based_accuracy(self, query: str, response: str) -> MetricResult:
        """基于规则的准确性评估"""
        issues = []

        # 检查回复中的声明是否过于绝对
        if any(phrase in response for phrase in ["绝对", "保证", "一定", "肯定"]):
            # 检查是否有条件限制
            if not any(phrase in response for phrase in ["如果", "可能", "一般", "通常"]):
                issues.append("声明过于绝对")

        # 检查是否在编造信息
        if len(response) > 500 and not any(
            phrase in response.lower()
            for phrase in ["根据", "知识库", "查询", "显示", "可以", "需要"]
        ):
            issues.append("长回复缺乏引用来源")

        accuracy = max(1.0 - len(issues) * 0.15, 0.0)

        return MetricResult(
            metric_type=MetricType.ACCURACY,
            value=accuracy,
            details=f"规则评估准确性: {accuracy:.2%}" + (f", 问题: {','.join(issues)}" if issues else ""),
            threshold=METRIC_THRESHOLDS.get(MetricType.ACCURACY)
        )

    def _evaluate_completeness(
        self,
        query: str,
        response: str,
        context: Dict[str, Any]
    ) -> MetricResult:
        """评估回复完整度"""
        if not response:
            return MetricResult(
                metric_type=MetricType.COMPLETENESS,
                value=0.0,
                details="无回复",
                threshold=METRIC_THRESHOLDS.get(MetricType.COMPLETENESS)
            )

        score = 0.5  # 基础分

        # 长度评估
        if len(response) > 50:
            score += 0.1
        if len(response) > 150:
            score += 0.1

        # 检查是否回答了问题的各个方面
        query_type = context.get("intent", "general")

        if query_type == "sales":
            # 销售场景：是否包含价格、产品信息
            if any(kw in response.lower() for kw in ["价格", "元", "推荐", "特点"]):
                score += 0.15
            if "产品" in response or any(p in response for p in ["推荐", "适合"]):
                score += 0.1

        elif query_type == "tech_support":
            # 技术支持：是否包含步骤
            step_indicators = ["1.", "2.", "第一步", "第二步", "首先", "然后", "最后"]
            if any(ind in response for ind in step_indicators):
                score += 0.2

        elif query_type == "negotiation":
            # 谈判场景：是否给出明确价格
            if "元" in response or any(kw in response for kw in ["优惠", "便宜", "折扣"]):
                score += 0.15

        # 检查是否有总结
        if any(phrase in response for phrase in ["总之", "总结", "综上", "总的来说"]):
            score += 0.05

        return MetricResult(
            metric_type=MetricType.COMPLETENESS,
            value=min(score, 1.0),
            details=f"完整度评分: {score:.2%}",
            threshold=METRIC_THRESHOLDS.get(MetricType.COMPLETENESS)
        )

    def _evaluate_helpfulness(
        self,
        query: str,
        response: str,
        context: Dict[str, Any]
    ) -> MetricResult:
        """评估整体有用性"""
        score = 0.5

        # 检查是否有实质帮助
        helpful_indicators = [
            "可以", "推荐", "建议", "帮助", "方案",
            "步骤", "方法", "解决", "优惠", "推荐"
        ]

        helpful_count = sum(1 for ind in helpful_indicators if ind in response.lower())
        score += min(helpful_count * 0.05, 0.25)

        # 检查是否有后续行动指引
        follow_up_indicators = ["可以", "需要", "如果", "建议您", "欢迎您"]
        if any(ind in response for ind in follow_up_indicators):
            score += 0.1

        # 检查语气是否友好
        friendly_indicators = ["您好", "请问", "谢谢", "很高兴", "祝您"]
        if any(ind in response for ind in friendly_indicators):
            score += 0.1

        # 负面指标
        negative_indicators = ["无法", "不能", "不知道", "不清楚", "抱歉"]
        negative_count = sum(1 for ind in negative_indicators if ind in response)
        score -= min(negative_count * 0.05, 0.2)

        return MetricResult(
            metric_type=MetricType.HELPFULNESS,
            value=max(min(score, 1.0), 0.0),
            details=f"有用性评分: {score:.2%}",
            threshold=METRIC_THRESHOLDS.get(MetricType.HELPFULNESS)
        )

    def _evaluate_sensitive_leak(
        self,
        response: str,
        context: Dict[str, Any]
    ) -> MetricResult:
        """评估敏感信息泄露"""
        response_lower = response.lower()

        # 敏感信息模式
        leak_patterns = [
            (r"成本价?[:：]?\s*\d+", "泄露成本价"),
            (r"底价?[:：]?\s*\d+", "泄露底价"),
            (r"最多只能?降?到?\s*\d+", "泄露底价"),
            (r"内部价?[:：]?\s*\d+", "泄露内部价格"),
        ]

        leaks = []
        for pattern, description in leak_patterns:
            if re.search(pattern, response_lower):
                leaks.append(description)

        # 如果是谈判场景，客户询问底价是合理的，需要更细致判断
        intent = context.get("intent", "")
        if intent == "negotiation":
            # 谈判中可以透露最大优惠价，但不能透露成本价
            leak_patterns_cost = [
                (r"成本价?[:：]?\s*\d+", "泄露成本价"),
            ]
            for pattern, description in leak_patterns_cost:
                if re.search(pattern, response_lower):
                    leaks.append(description)

        leak_rate = len(leaks) * 0.25  # 每次泄露扣 0.25

        return MetricResult(
            metric_type=MetricType.SENSITIVE_INFO_LEAK,
            value=min(leak_rate, 1.0),
            details=f"敏感信息泄露: {', '.join(leaks) if leaks else '无'}",
            threshold=METRIC_THRESHOLDS.get(MetricType.SENSITIVE_INFO_LEAK)
        )

    def _evaluate_hallucination(
        self,
        query: str,
        response: str,
        rag_results: List[Dict]
    ) -> MetricResult:
        """评估幻觉率"""
        if not rag_results:
            # 无 RAG 结果时，使用规则判断
            return self._rule_based_hallucination(response)

        response_lower = response.lower()
        hallucinations = 0

        # 获取 RAG 中的产品/价格信息
        rag_facts = set()
        for doc in rag_results:
            content = doc.get("content", "")
            # 提取产品名和价格
            products = re.findall(r"产品名称[:：]\s*([^\n]+)", content)
            prices = re.findall(r"(?:标价|最大优惠价|成本价)[:：]\s*(\d+)", content)
            rag_facts.update(products)
            rag_facts.update(prices)

        # 检查回复中是否有 RAG 中不存在的信息
        suspicious_claims = [
            "最好的", "最强的", "最便宜的", "唯一的",
            "保证", "绝对不会", "100%"
        ]

        for claim in suspicious_claims:
            if claim in response_lower:
                # 检查是否有依据
                if not any(word in response_lower for word in ["根据", "资料显示", "知识库"]):
                    hallucinations += 0.1

        # 检查回复中提到的具体信息是否与 RAG 一致
        response_prices = re.findall(r"\d{3,5}元", response)
        for price_match in response_prices:
            price = int(re.findall(r"\d+", price_match)[0])
            # 检查价格是否在合理范围内
            rag_prices = [int(p) for p in re.findall(r"\d{3,5}", " ".join(rag_facts))]
            if rag_prices and price < min(rag_prices) * 0.5:
                hallucinations += 0.1

        return MetricResult(
            metric_type=MetricType.HALLUCINATION_RATE,
            value=min(hallucinations, 1.0),
            details=f"幻觉率评估: {min(hallucinations, 1.0):.2%}",
            threshold=METRIC_THRESHOLDS.get(MetricType.HALLUCINATION_RATE)
        )

    def _rule_based_hallucination(self, response: str) -> MetricResult:
        """基于规则的幻觉检测"""
        score = 0.0

        # 检测无依据的绝对性声明
        if any(phrase in response for phrase in ["绝对", "保证", "100%", "一定"]):
            if not any(phrase in response for phrase in ["根据", "通常", "一般", "可能"]):
                score += 0.2

        # 检测长回复中是否缺乏引用
        if len(response) > 300:
            if not any(phrase in response.lower() for phrase in ["根据", "查询", "知识库", "显示"]):
                score += 0.1

        return MetricResult(
            metric_type=MetricType.HALLUCINATION_RATE,
            value=min(score, 1.0),
            details=f"规则幻觉检测: {min(score, 1.0):.2%}",
            threshold=METRIC_THRESHOLDS.get(MetricType.HALLUCINATION_RATE)
        )


# 全局实例
response_evaluator = ResponseEvaluator()
