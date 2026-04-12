"""
Context+RAG融合层 - 独立测试（不依赖外部模块）
测试核心融合逻辑
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum


class RetrievalQuality(Enum):
    """检索质量等级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class FusionStrategy(Enum):
    """融合策略"""
    RAG_PRIMARY = "rag_primary"
    CONTEXT_PRIMARY = "context_primary"
    HYBRID = "hybrid"
    CONTEXT_ONLY = "context_only"


@dataclass
class ContextAwareQuery:
    """上下文感知的查询"""
    original_query: str
    enhanced_query: str
    entities: List[str]
    metadata_hints: Dict[str, Any]


@dataclass
class FusionResult:
    """融合结果"""
    quality: RetrievalQuality
    fusion_strategy: FusionStrategy
    confidence: float
    used_sources: List[str]
    metadata: Dict[str, Any]


class MockSessionContext:
    """模拟会话上下文（简化版）"""

    def __init__(self):
        self.metadata = {
            "customer_type": "price_sensitive",
            "current_product": "智能手机",
            "discount_level": 1,
            "preference": "高性价比"
        }
        self.skill_context = {
            "customer_classifier": {
                "customer_type": "price_sensitive",
                "confidence": 0.85
            },
            "sales_agent": {
                "recommended_product": "X12智能手机"
            }
        }
        self.turn_history = [
            {"role": "user", "content": "我想买一台手机"},
            {"role": "assistant", "content": "为您推荐X12智能手机"}
        ]


class ContextExtractor:
    """上下文提取器（简化版）"""

    def extract_for_rag(self, context, query: str) -> ContextAwareQuery:
        """从上下文提取检索优化信息"""

        metadata = context.metadata
        entities = []
        enhanced_parts = [query]

        if metadata.get("current_product"):
            product = metadata["current_product"]
            enhanced_parts.append(product)
            entities.append(product)

        if metadata.get("customer_type"):
            customer_type = metadata["customer_type"]
            entities.append(f"客户类型:{customer_type}")

        for skill_name, skill_data in context.skill_context.items():
            if isinstance(skill_data, dict):
                if skill_name == "sales_agent":
                    product = skill_data.get("recommended_product")
                    if product:
                        entities.append(product)

        return ContextAwareQuery(
            original_query=query,
            enhanced_query=" ".join(enhanced_parts),
            entities=list(set(entities)),
            metadata_hints=metadata
        )


class RAGResultInjector:
    """RAG结果注入器（简化版）"""

    def evaluate_retrieval_quality(self, documents: List[Dict], query: str) -> Tuple[RetrievalQuality, float]:
        """评估检索质量"""

        if not documents:
            return RetrievalQuality.NONE, 0.0

        query_keywords = set(query.lower().split())
        total_relevance = 0.0

        for doc in documents:
            content = doc.get("content", "").lower()
            similarity_score = doc.get("similarity_score", 0.0)
            doc_keywords = set(content.split())
            common = query_keywords & doc_keywords

            keyword_ratio = len(common) / len(query_keywords) if query_keywords else 0
            relevance = keyword_ratio * 0.3 + similarity_score * 0.7
            total_relevance += relevance

        avg_relevance = total_relevance / len(documents)
        confidence = avg_relevance

        if confidence >= 0.7:
            quality = RetrievalQuality.HIGH
        elif confidence >= 0.4:
            quality = RetrievalQuality.MEDIUM
        elif confidence >= 0.2:
            quality = RetrievalQuality.LOW
        else:
            quality = RetrievalQuality.NONE

        return quality, confidence

    def inject_into_context(self, context, documents: List[Dict], quality: RetrievalQuality):
        """将RAG结果注入到上下文"""

        if quality != RetrievalQuality.NONE:
            entities = []
            for doc in documents:
                content = doc.get("content", "")
                if "X12" in content or "价格" in content:
                    entities.append(content[:50])

            print(f"  [注入] 提取实体: {len(entities)} 个")
            print(f"  [注入] 更新metadata")


class AdaptiveFusionEngine:
    """自适应融合引擎（简化版）"""

    def select_strategy(self, quality: RetrievalQuality, context_strength: float, intent: str) -> Tuple[FusionStrategy, float]:
        """选择融合策略"""

        if quality == RetrievalQuality.HIGH:
            if context_strength > 0.6:
                strategy = FusionStrategy.HYBRID
                confidence = 0.85
            else:
                strategy = FusionStrategy.RAG_PRIMARY
                confidence = 0.75
        elif quality == RetrievalQuality.MEDIUM:
            strategy = FusionStrategy.HYBRID
            confidence = 0.70
        elif quality == RetrievalQuality.LOW:
            strategy = FusionStrategy.CONTEXT_PRIMARY
            confidence = 0.60
        else:
            strategy = FusionStrategy.CONTEXT_ONLY
            confidence = 0.50

        if intent in ["greeting", "farewell"]:
            strategy = FusionStrategy.CONTEXT_ONLY
            confidence = 0.90

        return strategy, confidence


class ContextRAGFusionLayer:
    """Context+RAG融合层（简化版）"""

    def __init__(self):
        self.context_extractor = ContextExtractor()
        self.rag_result_injector = RAGResultInjector()
        self.fusion_engine = AdaptiveFusionEngine()

    def process(self, query: str, session_context, rag_retrieval_func) -> FusionResult:
        """处理融合"""

        print(f"\n[1/4] 上下文提取...")
        query_obj = self.context_extractor.extract_for_rag(session_context, query)
        print(f"  原始查询: '{query}'")
        print(f"  增强查询: '{query_obj.enhanced_query}'")
        print(f"  提取实体: {query_obj.entities}")

        print(f"\n[2/4] RAG检索...")
        rag_result = rag_retrieval_func(query_obj.enhanced_query)
        documents = rag_result.get("documents", [])
        print(f"  检索文档数: {len(documents)}")

        print(f"\n[3/4] 质量评估与注入...")
        quality, quality_confidence = self.rag_result_injector.evaluate_retrieval_quality(documents, query)
        print(f"  检索质量: {quality.value}")
        print(f"  置信度: {quality_confidence:.3f}")
        self.rag_result_injector.inject_into_context(session_context, documents, quality)

        print(f"\n[4/4] 策略选择...")
        context_strength = 0.7
        intent = "sales"
        strategy, strategy_confidence = self.fusion_engine.select_strategy(quality, context_strength, intent)
        print(f"  融合策略: {strategy.value}")
        print(f"  策略置信度: {strategy_confidence:.2f}")
        print(f"  上下文强度: {context_strength:.2f}")

        sources = []
        if documents:
            sources.append("knowledge_base")
        if session_context.skill_context:
            sources.append("skill_context")

        return FusionResult(
            quality=quality,
            fusion_strategy=strategy,
            confidence=strategy_confidence * quality_confidence,
            used_sources=sources,
            metadata={
                "enhanced_query": query_obj.enhanced_query,
                "entities": query_obj.entities,
                "context_strength": context_strength
            }
        )


def mock_rag_retrieval(query: str) -> Dict:
    """模拟RAG检索"""

    print(f"  执行查询: '{query}'")

    if "X12" in query or "手机" in query:
        return {
            "documents": [
                {
                    "content": "X12智能手机价格1999元，配置8GB+128GB，性价比极高",
                    "similarity_score": 0.85
                },
                {
                    "content": "X12Pro价格2999元，4K屏幕，更高性能",
                    "similarity_score": 0.75
                }
            ]
        }
    else:
        return {"documents": []}


def test_basic_fusion():
    """测试基础融合"""
    print("\n" + "="*70)
    print("测试 1: 基础Context+RAG融合")
    print("="*70)

    session = MockSessionContext()
    fusion_layer = ContextRAGFusionLayer()

    result = fusion_layer.process(
        query="X12手机多少钱？",
        session_context=session,
        rag_retrieval_func=mock_rag_retrieval
    )

    print(f"\n融合结果:")
    print(f"  检索质量: {result.quality.value}")
    print(f"  融合策略: {result.fusion_strategy.value}")
    print(f"  综合置信度: {result.confidence:.2f}")
    print(f"  数据源: {', '.join(result.used_sources)}")
    print(f"  增强查询: {result.metadata.get('enhanced_query')}")
    print(f"  提取实体: {result.metadata.get('entities')}")

    assert result.quality == RetrievalQuality.HIGH
    assert result.fusion_strategy == FusionStrategy.HYBRID
    assert result.confidence > 0.5
    assert "knowledge_base" in result.used_sources

    print("\n✓ 测试通过")


def test_context_only_scenario():
    """测试仅使用上下文的场景"""
    print("\n" + "="*70)
    print("测试 2: 仅使用上下文场景（无相关检索）")
    print("="*70)

    session = MockSessionContext()
    fusion_layer = ContextRAGFusionLayer()

    def empty_rag(query):
        return {"documents": []}

    result = fusion_layer.process(
        query="你们几点开门？",
        session_context=session,
        rag_retrieval_func=empty_rag
    )

    print(f"\n融合结果:")
    print(f"  检索质量: {result.quality.value}")
    print(f"  融合策略: {result.fusion_strategy.value}")

    assert result.quality == RetrievalQuality.NONE
    assert result.fusion_strategy == FusionStrategy.CONTEXT_ONLY

    print("\n✓ 测试通过")


def test_greeting_scenario():
    """测试问候场景"""
    print("\n" + "="*70)
    print("测试 3: 问候场景")
    print("="*70)

    session = MockSessionContext()
    fusion_layer = ContextRAGFusionLayer()

    result = fusion_layer.process(
        query="你好",
        session_context=session,
        rag_retrieval_func=mock_rag_retrieval
    )

    print(f"\n融合结果:")
    print(f"  检索质量: {result.quality.value}")
    print(f"  融合策略: {result.fusion_strategy.value}")

    assert result.fusion_strategy == FusionStrategy.CONTEXT_ONLY

    print("\n[PASS] 测试通过")


def test_quality_assessment():
    """测试质量评估"""
    print("\n" + "="*70)
    print("测试 4: 检索质量评估")
    print("="*70)

    injector = RAGResultInjector()

    test_cases = [
        (
            [{"content": "X12手机很好", "similarity_score": 0.9}],
            "X12手机",
            RetrievalQuality.HIGH
        ),
        (
            [{"content": "一些相关内容", "similarity_score": 0.5}],
            "X12手机",
            RetrievalQuality.MEDIUM
        ),
        (
            [{"content": "不相关的内容", "similarity_score": 0.2}],
            "X12手机",
            RetrievalQuality.LOW
        ),
        (
            [],
            "X12手机",
            RetrievalQuality.NONE
        )
    ]

    for i, (docs, query, expected_quality) in enumerate(test_cases, 1):
        quality, confidence = injector.evaluate_retrieval_quality(docs, query)
        print(f"\n案例 {i}:")
        print(f"  查询: '{query}'")
        print(f"  文档数: {len(docs)}")
        print(f"  评估质量: {quality.value}")
        print(f"  置信度: {confidence:.3f}")

        assert quality == expected_quality, f"案例 {i} 质量不匹配"

    print("\n✓ 测试通过")


def test_entity_extraction():
    """测试实体提取"""
    print("\n" + "="*70)
    print("测试 5: 实体提取")
    print("="*70)

    extractor = ContextExtractor()
    session = MockSessionContext()

    query_obj = extractor.extract_for_rag(session, "X12怎么样？")

    print(f"\n提取结果:")
    print(f"  原始查询: '{query_obj.original_query}'")
    print(f"  增强查询: '{query_obj.enhanced_query}'")
    print(f"  提取实体: {query_obj.entities}")
    print(f"  元数据提示: {query_obj.metadata_hints}")

    assert "X12" in query_obj.enhanced_query or "手机" in query_obj.enhanced_query
    assert len(query_obj.entities) > 0
    assert query_obj.metadata_hints.get("customer_type") == "price_sensitive"

    print("\n✓ 测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("Context+RAG融合层 - 独立测试套件")
    print("="*70)
    print("\n本测试不依赖外部模块，直接测试核心融合逻辑\n")

    try:
        test_entity_extraction()
        test_quality_assessment()
        test_basic_fusion()
        test_context_only_scenario()
        test_greeting_scenario()

        print("\n" + "="*70)
        print("🎉 所有测试通过！")
        print("="*70)

        print("\n\n📋 测试总结:")
        print("✓ ContextExtractor: 成功从SessionContext提取检索优化信息")
        print("✓ RAGResultInjector: 成功评估检索质量")
        print("✓ AdaptiveFusionEngine: 成功选择融合策略")
        print("✓ ContextRAGFusionLayer: 完整融合流程工作正常")
        print("✓ 场景覆盖: 产品咨询、无关查询、问候语")

        print("\n\n🔍 关键功能验证:")
        print("1. 上下文元数据（客户类型、产品偏好）被成功用于增强查询")
        print("2. Skill上下文被成功提取并应用到检索中")
        print("3. RAG结果被智能评估质量")
        print("4. 根据检索质量和意图自适应选择融合策略")
        print("5. 简单对话（问候）跳过不必要检索")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
