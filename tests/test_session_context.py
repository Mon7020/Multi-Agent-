"""
SessionContext 单元测试
"""

import pytest
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from core.session_context import SessionContext, TurnRecord


class TestTurnRecord:
    """单轮对话记录测试"""

    def test_turn_record_creation(self):
        """测试创建对话记录"""
        turn = TurnRecord(
            role="user",
            content="推荐一款手机",
            agent_name="sales_agent",
            intent="sales",
            evaluation_score=0.85
        )

        assert turn.role == "user"
        assert turn.content == "推荐一款手机"
        assert turn.agent_name == "sales_agent"
        assert turn.intent == "sales"
        assert turn.evaluation_score == 0.85
        assert turn.timestamp is not None


class TestSessionContext:
    """会话上下文测试"""

    def setup_method(self):
        """每个测试方法前执行"""
        self.context = SessionContext(session_id="test_001", max_history=10)

    def test_session_creation(self):
        """测试会话创建"""
        assert self.context.session_id == "test_001"
        assert self.context.max_history == 10
        assert self.context.metadata["customer_type"] is None
        assert self.context.metadata["discount_level"] == 1

    def test_add_turn(self):
        """测试添加对话轮次"""
        self.context.add_turn(
            role="user",
            content="推荐一款手机",
            agent_name="sales_agent",
            intent="sales"
        )

        assert len(self.context.turn_history) == 1
        assert self.context.turn_history[0].role == "user"
        assert self.context.turn_history[0].content == "推荐一款手机"

    def test_add_multiple_turns(self):
        """测试添加多轮对话"""
        self.context.add_turn(role="user", content="你好")
        self.context.add_turn(role="assistant", content="您好，有什么可以帮助您的吗？")
        self.context.add_turn(role="user", content="推荐一款手机")

        assert len(self.context.turn_history) == 3

    def test_add_turn_updates_memory(self):
        """测试添加对话自动更新 memory"""
        self.context.add_turn(role="user", content="推荐一款手机")

        memory_vars = self.context.memory.load_memory_variables({})
        assert len(memory_vars.get("chat_history", [])) > 0

    def test_update_skill_context(self):
        """测试更新 Skill 上下文"""
        self.context.update_skill_context(
            skill_name="customer_classifier",
            result_data={
                "customer_type": "price_sensitive",
                "confidence": 0.85
            }
        )

        skill_ctx = self.context.get_skill_context("customer_classifier")
        assert skill_ctx is not None
        assert skill_ctx["customer_type"] == "price_sensitive"

    def test_update_skill_context_extracts_metadata(self):
        """测试更新 Skill 上下文时提取元数据"""
        self.context.update_skill_context(
            skill_name="customer_classifier",
            result_data={
                "customer_type": "rational",
                "strategy": {"approach": "专业详细"}
            }
        )

        assert self.context.metadata["customer_type"] == "rational"
        assert self.context.metadata["service_strategy"] == {"approach": "专业详细"}

    def test_update_negotiation_context(self):
        """测试更新谈判上下文提取产品信息"""
        self.context.update_skill_context(
            skill_name="negotiation",
            result_data={
                "product": {"name": "X12 Pro", "list_price": 3999},
                "discount_level": 2
            }
        )

        assert self.context.metadata["current_product"] == "X12 Pro"
        assert self.context.metadata["discount_level"] == 2

    def test_get_unified_context(self):
        """测试获取统一上下文"""
        self.context.add_turn(role="user", content="你好")
        self.context.update_skill_context("customer_classifier", {"customer_type": "normal"})

        unified = self.context.get_unified_context()

        assert "session_id" in unified
        assert "memory" in unified
        assert "skill_context" in unified
        assert "metadata" in unified
        assert unified["session_id"] == "test_001"

    def test_get_context_for_skill(self):
        """测试获取特定 Skill 的上下文"""
        self.context.add_turn(role="user", content="推荐手机")
        self.context.update_skill_context("customer_classifier", {"customer_type": "rational"})

        skill_ctx = self.context.get_context_for_skill("customer_classifier")

        assert "query" in skill_ctx
        assert "history" in skill_ctx
        assert "customer_classifier_result" in skill_ctx
        assert skill_ctx["customer_type"] == "rational"

    def test_update_rag_cache(self):
        """测试更新 RAG 缓存"""
        docs = [{"content": "X12 Pro 价格3999元", "score": 0.95}]
        self.context.update_rag_cache("X12 Pro", docs)

        assert self.context.rag_cache["last_query"] == "X12 Pro"
        assert self.context.rag_cache["last_rag_results"] == docs

    def test_get_average_evaluation_score(self):
        """测试获取平均评估分数"""
        self.context.add_turn(role="user", content="问1", evaluation_score=0.8)
        self.context.add_turn(role="user", content="问2", evaluation_score=0.9)
        self.context.add_turn(role="user", content="问3", evaluation_score=0.0)  # 无评分

        avg_score = self.context.get_average_evaluation_score()
        assert avg_score == (0.8 + 0.9) / 2

    def test_get_session_summary(self):
        """测试获取会话摘要"""
        self.context.add_turn(role="user", content="你好")
        self.context.add_turn(role="assistant", content="您好")
        self.context.add_turn(role="user", content="推荐手机", agent_name="sales_agent", intent="sales")

        summary = self.context.get_session_summary()

        assert summary["session_id"] == "test_001"
        assert summary["total_turns"] == 3
        assert summary["user_turns"] == 2
        assert summary["assistant_turns"] == 1
        assert "sales_agent" in summary["skills_used"]
        assert "sales" in summary["intents_detected"]

    def test_clear_context(self):
        """测试清空会话"""
        self.context.add_turn(role="user", content="你好")
        self.context.update_skill_context("customer_classifier", {"customer_type": "normal"})

        self.context.clear()

        assert len(self.context.turn_history) == 0
        assert len(self.context.skill_context) == 0
        assert self.context.metadata["customer_type"] is None

    def test_history_size_limit(self):
        """测试历史大小限制"""
        max_history = self.context.max_history

        # 添加超过限制的轮次
        for i in range(max_history * 2 + 5):
            self.context.add_turn(role="user", content=f"消息{i}")

        # 应该自动裁剪
        assert len(self.context.turn_history) <= max_history * 2


class TestSessionContextManager:
    """会话上下文管理器测试"""

    def test_create_and_get_session(self):
        """测试创建和获取会话"""
        from core.session_context import SessionContextManager

        manager = SessionContextManager()

        # 创建会话
        ctx1 = manager.create_session("session_001")
        assert ctx1.session_id == "session_001"

        # 再次获取同一个会话
        ctx2 = manager.get_session("session_001")
        assert ctx2 is ctx1  # 应该是同一个对象

        # 获取不存在的会话
        ctx3 = manager.get_session("nonexistent")
        assert ctx3 is None

    def test_delete_session(self):
        """测试删除会话"""
        from core.session_context import SessionContextManager

        manager = SessionContextManager()

        manager.create_session("session_001")
        assert manager.get_session("session_001") is not None

        manager.delete_session("session_001")
        assert manager.get_session("session_001") is None

    def test_list_sessions(self):
        """测试列出所有会话"""
        from core.session_context import SessionContextManager

        manager = SessionContextManager()

        manager.create_session("session_001")
        manager.create_session("session_002")
        manager.create_session("session_003")

        sessions = manager.list_sessions()
        assert len(sessions) >= 3
        assert "session_001" in sessions
        assert "session_002" in sessions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
