"""
测试 Context+RAG融合层
验证双向信息流和自适应融合策略
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.session_context import SessionContext, SessionContextManager
from tools.rag.context_rag_fusion import (
    context_rag_fusion_layer,
    ContextExtractor,
    RAGResultInjector,
    AdaptiveFusionEngine,
    RetrievalQuality,
    FusionStrategy
)


def create_test_session() -> SessionContext:
    """创建测试会话"""
    manager = SessionContextManager()
    session = manager.create_session("test_fusion_001")

    session.add_turn(
        role="user",
        content="你好，我想买一台投影仪",
        agent_name="supervisor",
        intent="sales"
    )

    session.add_turn(
        role="assistant",
        content="您好！很高兴为您推荐投影仪。请问您有什么具体需求吗？",
        agent_name="supervisor"
    )

    session.update_skill_context("customer_classifier", {
        "customer_type": "price_sensitive",
        "confidence": 0.85,
        "strategy": "推荐性价比高的产品"
    })

    session.metadata["current_product"] = "智能投影仪"
    session.metadata["customer_type"] = "price_sensitive"

    return session


def mock_rag_retrieval(query: str, metadata_hints: dict = None) -> dict:
    """模拟RAG检索"""
    print(f"\n[Mock RAG] 执行检索:")
    print(f"  查询: '{query}'")
    print(f"  元数据提示: {metadata_hints}")

    if "投影仪" in query or "投影机" in query:
        return {
            "success": True,
            "documents": [
                {
                    "content": "产品名称：X12智能投影仪\n价格：2999元\n分辨率：1920x1080\n特点：高亮度，短焦距，内置音箱",
                    "source_file": "价格表.txt",
                    "similarity_score": 0.85,
                    "chunk_id": "chunk_001"
                },
                {
                    "content": "产品名称：X12Pro智能投影仪\n价格：3999元\n分辨率：4K\n特点：超高清，自动对焦，支持3D",
                    "source_file": "价格表.txt",
                    "similarity_score": 0.75,
                    "chunk_id": "chunk_002"
                }
            ]
        }
    elif "手机" in query:
        return {
            "success": True,
            "documents": [
                {
                    "content": "产品名称：X12智能手机\n价格：1999元\n配置：8GB+128GB",
                    "source_file": "价格表.txt",
                    "similarity_score": 0.70,
                    "chunk_id": "chunk_003"
                }
            ]
        }
    else:
        return {
            "success": True,
            "documents": [
                {
                    "content": "这是一个通用产品介绍...",
                    "source_file": "产品手册.txt",
                    "similarity_score": 0.40,
                    "chunk_id": "chunk_004"
                }
            ]
        }


def test_context_extractor():
    """测试上下文提取器"""
    print("\n" + "="*60)
    print("测试 1: ContextExtractor - 从SessionContext提取检索优化信息")
    print("="*60)

    session = create_test_session()
    extractor = ContextExtractor()

    query = "X12投影仪多少钱？"
    result = extractor.extract_for_rag(session, query)

    print(f"\n原始查询: '{query}'")
    print(f"增强查询: '{result.enhanced_query}'")
    print(f"提取实体: {result.entities}")
    print(f"推断意图: {result.intent}")
    print(f"元数据提示: {result.metadata_hints}")
    print(f"Skill上下文应用: {result.skill_context_applied}")

    assert result.enhanced_query != query, "查询应该被增强"
    assert len(result.entities) > 0, "应该提取到实体"
    assert result.metadata_hints.get("customer_type") == "price_sensitive", "应该包含客户类型"
    assert result.skill_context_applied == True, "应该应用了Skill上下文"

    print("\n✓ ContextExtractor 测试通过")


def test_rag_result_injector():
    """测试RAG结果注入器"""
    print("\n" + "="*60)
    print("测试 2: RAGResultInjector - 评估和注入RAG结果")
    print("="*60)

    session = create_test_session()
    injector = RAGResultInjector()

    documents = [
        {
            "content": "产品名称：X12智能投影仪\n价格：2999元\n分辨率：1920x1080",
            "source_file": "价格表.txt",
            "similarity_score": 0.85
        },
        {
            "content": "产品名称：X12Pro智能投影仪\n价格：3999元\n分辨率：4K",
            "source_file": "价格表.txt",
            "similarity_score": 0.75
        }
    ]

    query = "X12投影仪多少钱？"

    quality, confidence = injector.evaluate_retrieval_quality(documents, query)
    print(f"\n检索质量评估:")
    print(f"  质量等级: {quality.value}")
    print(f"  置信度: {confidence:.3f}")

    injection_summary = injector.inject_into_context(
        session, documents, query, quality, confidence
    )

    print(f"\n注入摘要:")
    print(f"  查询: {injection_summary['query']}")
    print(f"  质量: {injection_summary['quality']}")
    print(f"  文档数: {injection_summary['doc_count']}")
    print(f"  提取实体: {injection_summary['entities_extracted']}")
    print(f"  更新的元数据: {injection_summary['metadata_updated']}")

    assert quality in [RetrievalQuality.HIGH, RetrievalQuality.MEDIUM], "投影仪查询应该得到高质量结果"
    assert "rag_cache" in injection_summary["metadata_updated"], "应该更新RAG缓存"
    assert len(injection_summary["entities_extracted"]) > 0, "应该提取到实体"

    print("\n✓ RAGResultInjector 测试通过")


def test_adaptive_fusion_engine():
    """测试自适应融合引擎"""
    print("\n" + "="*60)
    print("测试 3: AdaptiveFusionEngine - 选择融合策略")
    print("="*60)

    engine = AdaptiveFusionEngine()

    test_cases = [
        (RetrievalQuality.HIGH, 0.8, "sales", FusionStrategy.HYBRID, "高质量+强上下文 → HYBRID"),
        (RetrievalQuality.HIGH, 0.3, "sales", FusionStrategy.RAG_PRIMARY, "高质量+弱上下文 → RAG_PRIMARY"),
        (RetrievalQuality.MEDIUM, 0.6, "tech_support", FusionStrategy.HYBRID, "中等质量 → HYBRID"),
        (RetrievalQuality.LOW, 0.7, "sales", FusionStrategy.CONTEXT_PRIMARY, "低质量 → CONTEXT_PRIMARY"),
        (RetrievalQuality.NONE, 0.5, "general", FusionStrategy.CONTEXT_ONLY, "无检索 → CONTEXT_ONLY"),
        (RetrievalQuality.HIGH, 0.5, "greeting", FusionStrategy.CONTEXT_ONLY, "问候语 → CONTEXT_ONLY"),
    ]

    for quality, context_strength, intent, expected_strategy, description in test_cases:
        strategy, confidence = engine.select_strategy(quality, context_strength, intent)

        print(f"\n测试: {description}")
        print(f"  实际策略: {strategy.value}")
        print(f"  置信度: {confidence:.2f}")

        assert strategy == expected_strategy, f"策略不匹配: {description}"

    print("\n✓ AdaptiveFusionEngine 测试通过")


def test_context_rag_fusion_layer():
    """测试完整的Context+RAG融合层"""
    print("\n" + "="*60)
    print("测试 4: ContextRAGFusionLayer - 完整融合流程")
    print("="*60)

    session = create_test_session()

    query = "X12投影仪多少钱？"
    intent = "sales"

    fusion_result = context_rag_fusion_layer.process(
        query=query,
        session_context=session,
        rag_retrieval_func=mock_rag_retrieval,
        intent=intent
    )

    print(f"\n融合结果:")
    print(f"  检索质量: {fusion_result.quality.value}")
    print(f"  融合策略: {fusion_result.fusion_strategy.value}")
    print(f"  置信度: {fusion_result.confidence:.2f}")
    print(f"  数据源: {', '.join(fusion_result.used_sources)}")
    print(f"  上下文强度: {fusion_result.metadata.get('context_strength', 0):.2f}")
    print(f"  处理时间: {fusion_result.metadata.get('total_process_time', 0):.3f}s")
    print(f"  增强查询: {fusion_result.metadata.get('enhanced_query', '')}")
    print(f"  提取实体: {fusion_result.metadata.get('entities', [])}")

    assert fusion_result.quality in [RetrievalQuality.HIGH, RetrievalQuality.MEDIUM], "应该有高质量检索"
    assert fusion_result.confidence > 0.5, "置信度应该较高"
    assert "knowledge_base" in fusion_result.used_sources, "应该使用知识库"
    assert len(fusion_result.metadata.get("entities", [])) > 0, "应该提取到实体"

    fusion_prompt = context_rag_fusion_layer.get_fusion_prompt(
        fusion_result,
        system_prompt="你是一个热情的客服助手"
    )
    print(f"\n生成的融合提示词:")
    print(fusion_prompt[:500] + "...")

    print("\n✓ ContextRAGFusionLayer 测试通过")


def test_context_rag_integration():
    """测试上下文和RAG的集成"""
    print("\n" + "="*60)
    print("测试 5: Context+RAG集成 - 验证双向信息流")
    print("="*60)

    manager = SessionContextManager()
    session = manager.create_session("test_integration_001")

    print("\n步骤 1: 初始对话")
    session.add_turn(
        role="user",
        content="我想买一台手机",
        agent_name="supervisor",
        intent="sales"
    )
    session.metadata["current_product"] = "智能手机"

    print(f"  当前产品: {session.metadata.get('current_product')}")
    print(f"  对话轮数: {len(session.turn_history)}")

    print("\n步骤 2: 第一次Context+RAG融合")
    result1 = context_rag_fusion_layer.process(
        query="有什么推荐的手机吗？",
        session_context=session,
        rag_retrieval_func=mock_rag_retrieval,
        intent="sales"
    )

    print(f"  检索质量: {result1.quality.value}")
    print(f"  融合策略: {result1.fusion_strategy.value}")
    print(f"  提取实体: {result1.metadata.get('entities', [])}")

    session.add_turn(
        role="assistant",
        content="为您推荐X12智能手机，性价比很高！",
        agent_name="sales_agent"
    )

    print("\n步骤 3: 更新客户上下文")
    session.metadata["current_product"] = "X12智能手机"
    session.metadata["customer_type"] = "rational"
    session.update_skill_context("sales_agent", {
        "recommended_product": "X12智能手机",
        "price_range": "2000-3000"
    })

    print(f"  当前产品: {session.metadata.get('current_product')}")
    print(f"  客户类型: {session.metadata.get('customer_type')}")
    print(f"  Skill上下文: {list(session.skill_context.keys())}")

    print("\n步骤 4: 第二次Context+RAG融合（使用更新后的上下文）")
    result2 = context_rag_fusion_layer.process(
        query="X12的具体价格？",
        session_context=session,
        rag_retrieval_func=mock_rag_retrieval,
        intent="price_inquiry"
    )

    print(f"  检索质量: {result2.quality.value}")
    print(f"  融合策略: {result2.fusion_strategy.value}")
    print(f"  增强查询: {result2.metadata.get('enhanced_query', '')}")
    print(f"  提取实体: {result2.metadata.get('entities', [])}")

    assert "X12" in result2.metadata.get("enhanced_query", ""), "增强查询应该包含X12"
    assert "智能手机" in result2.metadata.get("enhanced_query", ""), "增强查询应该包含产品类别"
    assert result2.quality == RetrievalQuality.HIGH, "价格查询应该有高质量结果"

    print("\n✓ Context+RAG集成测试通过")


def test_fusion_prompt_generation():
    """测试融合提示词生成"""
    print("\n" + "="*60)
    print("测试 6: 融合提示词生成")
    print("="*60)

    session = create_test_session()

    result = context_rag_fusion_layer.process(
        query="X12投影仪怎么样？",
        session_context=session,
        rag_retrieval_func=mock_rag_retrieval,
        intent="product_spec"
    )

    fusion_prompt = context_rag_fusion_layer.get_fusion_prompt(
        fusion_result=result,
        system_prompt="你是一个专业的客服助手"
    )

    print("\n生成的融合提示词:")
    print(fusion_prompt)

    assert "系统指令" in fusion_prompt, "应该包含系统指令"
    assert "检索信息" in fusion_prompt, "应该包含检索信息"
    assert "原始查询" in fusion_prompt, "应该包含原始查询"
    assert "检索质量" in fusion_prompt, "应该包含检索质量"

    if result.quality == RetrievalQuality.HIGH:
        assert "优先基于检索结果" in fusion_prompt, "高质量检索应该提示优先使用检索结果"

    print("\n✓ 融合提示词生成测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("Context+RAG融合层 - 完整测试套件")
    print("="*70)

    try:
        test_context_extractor()
        test_rag_result_injector()
        test_adaptive_fusion_engine()
        test_context_rag_fusion_layer()
        test_context_rag_integration()
        test_fusion_prompt_generation()

        print("\n" + "="*70)
        print("🎉 所有测试通过！")
        print("="*70)

        print("\n\n📋 测试总结:")
        print("✓ ContextExtractor: 成功从SessionContext提取检索优化信息")
        print("✓ RAGResultInjector: 成功评估检索质量并注入到上下文")
        print("✓ AdaptiveFusionEngine: 成功根据质量和上下文选择融合策略")
        print("✓ ContextRAGFusionLayer: 完整融合流程工作正常")
        print("✓ Context+RAG集成: 双向信息流验证成功")
        print("✓ 融合提示词生成: 成功生成结构化提示词")

        print("\n\n🔍 关键发现:")
        print("1. 上下文元数据（客户类型、产品偏好）被成功用于增强查询")
        print("2. Skill上下文被成功提取并应用到检索中")
        print("3. RAG结果被智能注入到SessionContext")
        print("4. 根据检索质量和上下文强度自适应选择融合策略")
        print("5. 生成的融合提示词包含质量信息和策略指导")

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
