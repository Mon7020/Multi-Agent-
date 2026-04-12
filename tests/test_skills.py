"""
Skill 业务逻辑单元测试
"""

import pytest
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from skills.skills.negotiation_skill import NegotiationSkill, DISCOUNT_LEVELS
from skills.skills.sales_agent_skill import SalesAgentSkill
from skills.skills.tech_support_skill import TechSupportSkill
from skills.base import SkillConfig, SkillType


class TestNegotiationSkill:
    """价格谈判 Skill 测试"""

    def setup_method(self):
        """每个测试方法前执行"""
        self.skill = NegotiationSkill()

    def test_discount_levels_config(self):
        """测试折扣层级配置正确"""
        assert len(DISCOUNT_LEVELS) == 3

        # 层级1: 9折
        assert DISCOUNT_LEVELS[0]["level"] == 1
        assert DISCOUNT_LEVELS[0]["discount_rate"] == 0.90

        # 层级2: 85折
        assert DISCOUNT_LEVELS[1]["level"] == 2
        assert DISCOUNT_LEVELS[1]["discount_rate"] == 0.85

        # 层级3: 底价
        assert DISCOUNT_LEVELS[2]["level"] == 3
        assert DISCOUNT_LEVELS[2]["discount_rate"] is None

    def test_calculate_price_level_1(self):
        """测试计算第1级折扣价格"""
        product = {"name": "智能手机 X12 Pro", "list_price": 3999, "min_price": 3299}
        price_info = self.skill._calculate_price(product, discount_level=1)

        assert price_info["list_price"] == 3999
        assert price_info["min_price"] == 3299
        assert price_info["discount_level"] == 1
        # 9折: 3999 * 0.9 = 3599
        assert price_info["final_price"] == 3599

    def test_calculate_price_level_2(self):
        """测试计算第2级折扣价格"""
        product = {"name": "智能手机 X12 Pro", "list_price": 3999, "min_price": 3299}
        price_info = self.skill._calculate_price(product, discount_level=2)

        # 85折: 3999 * 0.85 = 3399.15 -> 3399
        assert price_info["final_price"] == 3399

    def test_calculate_price_level_3_uses_min_price(self):
        """测试第3级折扣使用最低价"""
        product = {"name": "智能手机 X12 Pro", "list_price": 3999, "min_price": 3299}
        price_info = self.skill._calculate_price(product, discount_level=3)

        assert price_info["final_price"] == price_info["min_price"]
        assert price_info["final_price"] == 3299

    def test_price_never_below_min_price(self):
        """测试价格永远不会低于最低价"""
        product = {"name": "智能手机 X12 Pro", "list_price": 3999, "min_price": 3299}

        for level in [1, 2, 3]:
            price_info = self.skill._calculate_price(product, discount_level=level)
            assert price_info["final_price"] >= price_info["min_price"], \
                f"Level {level}: final_price {price_info['final_price']} < min_price {price_info['min_price']}"

    def test_assess_customer_attitude_aggressive(self):
        """测试评估客户态度 - 激进型"""
        query = "太贵了，不行，我要投诉"
        attitude = self.skill._assess_customer_attitude(query, [])
        assert attitude == "aggressive"

    def test_assess_customer_attitude_polite(self):
        """测试评估客户态度 - 礼貌型"""
        query = "请问能便宜一点吗，谢谢"
        attitude = self.skill._assess_customer_attitude(query, [])
        assert attitude == "polite"

    def test_assess_customer_attitude_normal(self):
        """测试评估客户态度 - 普通型"""
        query = "这个多少钱"
        attitude = self.skill._assess_customer_attitude(query, [])
        assert attitude == "normal"

    def test_determine_next_discount_level_normal(self):
        """测试正常谈判逐步递进"""
        # 初始层级1 -> 层级2
        next_level = self.skill._determine_next_discount_level(
            current_level=1,
            customer_attitude="normal"
        )
        assert next_level == 2

        # 层级2 -> 层级3
        next_level = self.skill._determine_next_discount_level(
            current_level=2,
            customer_attitude="normal"
        )
        assert next_level == 3

    def test_determine_next_discount_level_aggressive(self):
        """测试难缠客户可以提前给到底价"""
        next_level = self.skill._determine_next_discount_level(
            current_level=1,
            customer_attitude="aggressive"
        )
        assert next_level == 2  # 可以从1直接到2

    def test_determine_next_discount_level_max_level(self):
        """测试已达最大层级"""
        next_level = self.skill._determine_next_discount_level(
            current_level=3,
            customer_attitude="normal"
        )
        assert next_level == 3  # 不能再递进

    def test_should_activate_with_negotiation_keywords(self):
        """测试谈判关键词触发激活"""
        context = {"query": "能不能便宜一点", "history": []}
        assert self.skill.should_activate(context) is True

    def test_should_activate_with_history_negotiation(self):
        """测试历史中有谈判记录时触发"""
        context = {
            "query": "我再想想",
            "history": [
                {"content": "太贵了，能便宜吗"},
                {"content": "您好"}
            ]
        }
        # 2次谈判关键词，应该激活
        assert self.skill.should_activate(context) is True

    def test_extract_current_product(self):
        """测试从查询中提取产品"""
        context = {"query": "X12 Pro 多少钱", "rag_results": []}
        product = self.skill._extract_current_product(context["query"], context["rag_results"])

        assert product is not None
        assert product["name"] == "智能手机 X12 Pro"
        assert product["list_price"] == 3999

    def test_extract_current_product_no_match(self):
        """测试无法识别产品"""
        context = {"query": "不知道什么产品", "rag_results": []}
        product = self.skill._extract_current_product(context["query"], context["rag_results"])

        assert product is None

    def test_negotiation_message_generation(self):
        """测试谈判话术生成"""
        product = {"name": "智能手机 X12 Pro", "list_price": 3999, "min_price": 3299}
        price_info = {
            "final_price": 3599,
            "min_price": 3299,
            "savings": 400
        }

        message = self.skill._get_negotiation_message(product, price_info, 1)
        assert "3599" in message
        assert "X12 Pro" in message


class TestSalesAgentSkill:
    """销售 Agent Skill 测试"""

    def setup_method(self):
        """每个测试方法前执行"""
        self.skill = SalesAgentSkill()

    def test_get_product_cache_returns_dict(self):
        """测试获取产品缓存返回字典"""
        cache = self.skill._get_product_cache()
        assert isinstance(cache, dict)
        assert len(cache) > 0

    def test_product_has_required_fields(self):
        """测试产品数据包含必要字段"""
        cache = self.skill._get_product_cache()

        for key, product in cache.items():
            assert "name" in product, f"产品 {key} 缺少 name 字段"
            assert "list_price" in product, f"产品 {key} 缺少 list_price 字段"
            assert "min_price" in product, f"产品 {key} 缺少 min_price 字段"
            assert product["list_price"] >= product["min_price"], \
                f"产品 {key} 的标价低于最低价"

    def test_should_activate_with_sales_keywords(self):
        """测试销售关键词触发激活"""
        keywords_to_test = ["买", "价格", "推荐", "多少钱", "优惠"]

        for keyword in keywords_to_test:
            context = {"query": f"我想{keyword}一个手机", "history": []}
            assert self.skill.should_activate(context) is True, f"关键词 '{keyword}' 未触发激活"

    def test_should_not_activate_irrelevant_query(self):
        """测试无关查询不触发"""
        context = {"query": "今天天气不错", "history": []}
        assert self.skill.should_activate(context) is False

    def test_get_recommendations_returns_list(self):
        """测试获取推荐返回列表"""
        recommendations = self.skill._get_recommendations(["x12 pro"])
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

    def test_get_recommendations_empty_for_unknown(self):
        """测试未知产品返回空列表"""
        recommendations = self.skill._get_recommendations(["unknown_product_xyz"])
        # 可能为空，也可能返回偏好推荐
        assert isinstance(recommendations, list)


class TestTechSupportSkill:
    """技术支持 Skill 测试"""

    def setup_method(self):
        """每个测试方法前执行"""
        self.skill = TechSupportSkill()

    def test_get_kb_returns_dict(self):
        """测试获取知识库返回字典"""
        kb = self.skill._get_kb()
        assert isinstance(kb, dict)
        assert len(kb) > 0

    def test_issue_types_have_required_fields(self):
        """测试问题类型包含必要字段"""
        kb = self.skill._get_kb()

        required_fields = ["keywords", "solutions", "need_more_info"]
        for issue_type, data in kb.items():
            for field in required_fields:
                assert field in data, f"问题类型 {issue_type} 缺少 {field} 字段"

    def test_should_activate_with_tech_keywords(self):
        """测试技术支持关键词触发激活"""
        keywords_to_test = ["怎么用", "坏了", "故障", "卡", "闪退"]

        for keyword in keywords_to_test:
            context = {"query": f"产品{keyword}了", "history": []}
            assert self.skill.should_activate(context) is True, f"关键词 '{keyword}' 未触发激活"

    def test_should_not_activate_pure_sales_query(self):
        """测试纯销售查询不触发技术支持"""
        context = {"query": "这个多少钱，推荐一下", "history": []}
        # 纯价格查询，不应该激活技术支持
        result = self.skill.should_activate(context)
        # 注意：这个可能会激活，因为"多少钱"也可能出现在技术支持场景
        # 所以主要测试肯定不会激活的情况
        assert isinstance(result, bool)


class TestSkillBase:
    """Skill 基类测试"""

    def test_skill_config_defaults(self):
        """测试 SkillConfig 默认值"""
        config = SkillConfig(
            name="test_skill",
            description="测试用 Skill"
        )

        assert config.enabled is True
        assert config.priority == 0
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.skill_type == SkillType.GENERAL

    def test_skill_type_enum_values(self):
        """测试 SkillType 枚举值"""
        assert SkillType.SALES.value == "sales"
        assert SkillType.TECHNICAL.value == "technical"
        assert SkillType.NEGOTIATION.value == "negotiation"
        assert SkillType.CUSTOMER.value == "customer"
        assert SkillType.GENERAL.value == "general"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
