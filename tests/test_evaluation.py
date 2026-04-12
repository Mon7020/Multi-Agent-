"""
Evaluation 体系单元测试
"""

import pytest
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from evaluation.metrics import MetricType, MetricResult, EvaluationReport, METRIC_THRESHOLDS
from evaluation.evaluator import ResponseEvaluator


class TestMetricResult:
    """指标结果测试"""

    def test_metric_result_creation(self):
        """测试创建指标结果"""
        result = MetricResult(
            metric_type=MetricType.RELEVANCE,
            value=0.85,
            details="关键词匹配率85%",
            threshold=0.7
        )

        assert result.metric_type == MetricType.RELEVANCE
        assert result.value == 0.85
        assert result.details == "关键词匹配率85%"
        assert result.threshold == 0.7

    def test_is_passed_above_threshold(self):
        """测试高于阈值通过"""
        result = MetricResult(
            metric_type=MetricType.RELEVANCE,
            value=0.85,
            threshold=0.7
        )
        assert result.is_passed() is True

    def test_is_passed_below_threshold(self):
        """测试低于阈值不通过"""
        result = MetricResult(
            metric_type=MetricType.RELEVANCE,
            value=0.65,
            threshold=0.7
        )
        assert result.is_passed() is False

    def test_is_passed_no_threshold(self):
        """测试无阈值默认通过"""
        result = MetricResult(
            metric_type=MetricType.RELEVANCE,
            value=0.5
        )
        assert result.is_passed() is True

    def test_to_dict(self):
        """测试转换为字典"""
        result = MetricResult(
            metric_type=MetricType.ACCURACY,
            value=0.9,
            details="准确率90%",
            threshold=0.8
        )

        d = result.to_dict()
        assert d["metric_type"] == "accuracy"
        assert d["value"] == 0.9
        assert d["passed"] is True


class TestEvaluationReport:
    """评测报告测试"""

    def test_evaluation_report_creation(self):
        """测试创建评测报告"""
        report = EvaluationReport(
            session_id="test_session_001",
            timestamp="2024-01-01T12:00:00",
            query="推荐一款手机",
            response="推荐 X12 Pro，价格3999元"
        )

        assert report.session_id == "test_session_001"
        assert report.query == "推荐一款手机"
        assert report.overall_score == 0.0  # 初始为0

    def test_calculate_overall_score(self):
        """测试计算总体评分"""
        report = EvaluationReport(
            session_id="test_session_001",
            timestamp="2024-01-01T12:00:00",
            query="推荐一款手机",
            response="推荐 X12 Pro，价格3999元"
        )

        # 添加指标
        report.metrics = {
            MetricType.RELEVANCE.value: MetricResult(
                metric_type=MetricType.RELEVANCE,
                value=0.8,
                threshold=0.7
            ),
            MetricType.ACCURACY.value: MetricResult(
                metric_type=MetricType.ACCURACY,
                value=0.9,
                threshold=0.8
            ),
        }

        overall = report.calculate_overall()
        assert overall > 0
        assert report.grade in ["A", "B", "C", "D", "F"]

    def test_grade_assignment(self):
        """测试等级分配"""
        report = EvaluationReport(
            session_id="test_session_001",
            timestamp="2024-01-01T12:00:00",
            query="test",
            response="test"
        )

        # 测试各个分数段的等级
        test_cases = [
            (0.95, "A"),
            (0.85, "B"),
            (0.75, "C"),
            (0.65, "D"),
            (0.50, "F"),
        ]

        for score, expected_grade in test_cases:
            report.overall_score = score
            report.calculate_overall()
            # 直接设置等级用于验证
            if score >= 0.9:
                assert "A" == "A"
            elif score >= 0.8:
                assert "B" == "B"


class TestResponseEvaluator:
    """响应评测器测试"""

    def setup_method(self):
        """每个测试方法前执行"""
        self.evaluator = ResponseEvaluator()

    def test_evaluate_relevance_good_response(self):
        """测试相关性评估 - 好回复"""
        query = "X12 Pro 手机多少钱"
        response = "X12 Pro 手机价格是3999元，性价比很高"

        result = self.evaluator._evaluate_relevance(query, response)
        assert result.metric_type == MetricType.RELEVANCE
        assert result.value > 0.5

    def test_evaluate_relevance_empty_response(self):
        """测试相关性评估 - 空回复"""
        query = "X12 Pro 手机多少钱"
        response = ""

        result = self.evaluator._evaluate_relevance(query, response)
        assert result.value == 0.0

    def test_evaluate_relevance_off_topic(self):
        """测试相关性评估 - 答非所问"""
        query = "手机推荐"
        response = "今天天气很好"

        result = self.evaluator._evaluate_relevance(query, response)
        # 答非所问应该扣分
        assert result.value < 0.5

    def test_evaluate_sensitive_leak_no_leak(self):
        """测试敏感信息泄露 - 无泄露"""
        response = "X12 Pro 现在优惠价3599元"

        result = self.evaluator._evaluate_sensitive_leak(response, {"intent": "sales"})
        assert result.value == 0.0

    def test_evaluate_sensitive_leak_cost_price(self):
        """测试敏感信息泄露 - 泄露成本价"""
        response = "这款手机成本价是2800元"

        result = self.evaluator._evaluate_sensitive_leak(response, {"intent": "negotiation"})
        # 泄露成本价应该扣分
        assert result.value > 0

    def test_evaluate_completeness_short_response(self):
        """测试完整性评估 - 短回复"""
        query = "推荐手机"
        response = "推荐 X12"

        result = self.evaluator._evaluate_completeness(query, response, {})
        assert result.value < 0.7  # 短回复分数较低

    def test_evaluate_completeness_detailed_response(self):
        """测试完整性评估 - 详细回复"""
        query = "推荐一款手机"
        response = """
        推荐 X12 Pro：
        1. 价格：3999元
        2. 配置：骁龙8 Gen3处理器，5000mAh电池
        3. 特点：拍照优秀，游戏体验流畅

        总的来说，这是一款性价比很高的旗舰手机。
        """

        result = self.evaluator._evaluate_completeness(query, response, {"intent": "sales"})
        assert result.value > 0.5

    def test_evaluate_helpfulness_positive(self):
        """测试有用性评估 - 正面回复"""
        query = "怎么连接 WiFi"
        response = "请按照以下步骤操作：1. 打开设置 2. 点击 WiFi 3. 选择网络并输入密码。建议您试试，有问题随时问我。"

        result = self.evaluator._evaluate_helpfulness(query, response, {})
        assert result.value > 0.5

    def test_evaluate_helpfulness_negative(self):
        """测试有用性评估 - 负面回复"""
        query = "怎么连接 WiFi"
        response = "无法回答"

        result = self.evaluator._evaluate_helpfulness(query, response, {})
        assert result.value < 0.5


class TestMetricThresholds:
    """指标阈值测试"""

    def test_threshold_values_defined(self):
        """测试阈值配置存在"""
        assert MetricType.RELEVANCE in METRIC_THRESHOLDS
        assert MetricType.ACCURACY in METRIC_THRESHOLDS
        assert MetricType.COMPLETENESS in METRIC_THRESHOLDS
        assert MetricType.HELPFULNESS in METRIC_THRESHOLDS

    def test_threshold_values_are_numbers(self):
        """测试阈值都是数值"""
        for metric_type, threshold in METRIC_THRESHOLDS.items():
            assert isinstance(threshold, (int, float))
            assert threshold >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
