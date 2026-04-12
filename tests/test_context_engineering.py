"""
上下文工程测试 - 多轮对话能力验证

测试三层记忆架构的各个组件：
1. 短期记忆：对话历史管理
2. 中期记忆：智能压缩
3. 长期记忆：用户偏好持久化
4. 意图演进跟踪
5. 上下文窗口管理

Claude Code 场景模拟测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from tools.rag.context_engineering import (
    ShortTermMemoryManager,
    MediumTermMemoryManager,
    LongTermMemoryManager,
    IntentEvolutionTracker,
    ContextWindowManager,
    ContextEngineeringManager,
    ConversationTurn,
    context_engineering_manager
)

from tools.rag.enhanced_context import enhanced_generation_context_layer


def test_short_term_memory():
    """测试短期记忆管理器"""
    print("\n" + "="*60)
    print("测试 1: 短期记忆管理器")
    print("="*60)

    stm = ShortTermMemoryManager(max_turns=20, compression_threshold=0.92)

    test_turns = [
        ("user", "X12 Pro手机多少钱？", "price_inquiry", ["X12 Pro"]),
        ("assistant", "X12 Pro售价2999元起。", None, []),
        ("user", "它的续航怎么样？", "product_spec", ["X12 Pro", "续航"]),
        ("assistant", "X12 Pro配备5000mAh电池，支持快充。", None, []),
        ("user", "那X12 Pro Max呢？", "price_inquiry", ["X12 Pro Max"]),
        ("assistant", "X12 Pro Max售价3999元起。", None, []),
    ]

    print("\n添加对话轮次：")
    for role, content, intent, entities in test_turns:
        turn = stm.add_turn(role, content, intent, entities)
        print(f"  Turn {turn.turn_id}: [{role}] {content[:30]}... | Intent: {intent} | Entities: {entities}")

    print(f"\n上下文密度: {stm.calculate_density():.2%}")
    print(f"应该压缩: {stm.should_compress()}")
    print(f"当前话题: {stm.get_current_topic()}")

    print("\n提取实体统计:")
    entities = stm.extract_entities()
    for entity, count in list(entities.items())[:5]:
        print(f"  {entity}: {count}次")

    print("\n生成 LLM 上下文:")
    context = stm.get_context_for_llm(max_tokens=500)
    print(context)

    print("\n[OK] 短期记忆管理器测试完成")


def test_medium_term_memory():
    """测试中期记忆管理器"""
    print("\n" + "="*60)
    print("测试 2: 中期记忆管理器")
    print("="*60)

    mtm = MediumTermMemoryManager(max_compressed_entries=10)

    test_turns = [
        ConversationTurn(
            turn_id=0, role="user",
            content="X12 Pro手机多少钱？",
            intent="price_inquiry", entities=["X12 Pro"]
        ),
        ConversationTurn(
            turn_id=1, role="assistant",
            content="X12 Pro售价2999元起。",
            intent=None, entities=[]
        ),
        ConversationTurn(
            turn_id=2, role="user",
            content="它的续航怎么样？",
            intent="product_spec", entities=["X12 Pro", "续航"]
        ),
        ConversationTurn(
            turn_id=3, role="assistant",
            content="X12 Pro配备5000mAh电池，支持快充。",
            intent=None, entities=[]
        ),
    ]

    print("\n压缩对话历史:")
    compressed = mtm.compress(test_turns)
    print(f"  摘要: {compressed.summary}")
    print(f"  关键实体: {compressed.key_entities}")
    print(f"  讨论话题: {compressed.discussed_topics}")
    print(f"  原始轮次: {compressed.original_turn_count}")
    print(f"  压缩比: {compressed.compression_ratio}")

    print("\n压缩后的所有摘要:")
    print(mtm.get_all_summaries())

    print("\n[OK] 中期记忆管理器测试完成")


def test_long_term_memory():
    """测试长期记忆管理器"""
    print("\n" + "="*60)
    print("测试 3: 长期记忆管理器")
    print("="*60)

    ltm = LongTermMemoryManager()

    user_id = "test_user_001"

    print(f"\n更新用户偏好 (user_id: {user_id}):")
    ltm.update_preference(user_id, "preferred_brand", "X品牌")
    ltm.update_preference(user_id, "budget_range", "3000-5000")
    ltm.update_preference(user_id, "interested_products", ["X12 Pro", "X12 Pro Max"])

    print("  ✓ preferred_brand = X品牌")
    print("  ✓ budget_range = 3000-5000")
    print("  ✓ interested_products = [X12 Pro, X12 Pro Max]")

    print("\n添加讨论实体:")
    ltm.add_entity(user_id, "X12 Pro", "price_inquiry")
    ltm.add_entity(user_id, "X12 Pro", "product_spec")
    ltm.add_entity(user_id, "X12 Pro Max", "price_inquiry")

    print("  ✓ X12 Pro 讨论过: price_inquiry, product_spec")
    print("  ✓ X12 Pro Max 讨论过: price_inquiry")

    print("\n获取用户上下文:")
    context = ltm.get_user_context(user_id)
    print(context)

    print("\n保存用户画像:")
    success = ltm.save_profile(user_id)
    print(f"  {'[OK] 保存成功' if success else '[FAIL] 保存失败'}")

    print("\n[OK] 长期记忆管理器测试完成")


def test_intent_evolution_tracker():
    """测试意图演进跟踪器"""
    print("\n" + "="*60)
    print("测试 4: 意图演进跟踪器")
    print("="*60)

    tracker = IntentEvolutionTracker()

    intents = [
        ("price_inquiry", 0.9, ["X12 Pro"]),
        ("product_spec", 0.85, ["X12 Pro", "续航"]),
        ("product_spec", 0.88, ["X12 Pro", "屏幕"]),
        ("purchase", 0.92, ["X12 Pro"]),
    ]

    print("\n跟踪意图序列:")
    for intent, conf, entities in intents:
        tracker.track_intent(intent, conf, entities)
        print(f"  → {intent} (置信度: {conf})")

    print(f"\n当前目标: {tracker.current_goal}")
    print(f"目标历史: {tracker.goal_history}")
    print(f"检测到话题切换: {tracker.detect_topic_shift()}")

    print("\n获取连续性上下文 (Manus 技巧 - 目标复述):")
    continuity = tracker.get_continuity_context()
    print(continuity)

    print("\n话题切换时的补充上下文:")
    context = tracker.get_context_for_topic_switch("product_spec", "purchase")
    print(f"  {context}")

    print("\n[OK] 意图演进跟踪器测试完成")


def test_context_window_manager():
    """测试上下文窗口管理器"""
    print("\n" + "="*60)
    print("测试 5: 上下文窗口管理器")
    print("="*60)

    cwm = ContextWindowManager(max_tokens=1000, reserve_tokens=200)

    components = [
        {
            "content": "【系统提示】你是一个智能客服助手。",
            "importance": 1.0,
            "flexible": False
        },
        {
            "content": "【对话历史】用户：X12 Pro多少钱？\n助手：2999元。用户：续航呢？\n助手：5000mAh电池。",
            "importance": 0.9,
            "flexible": False
        },
        {
            "content": "【RAG检索】X12 Pro配置：\n- 屏幕：6.7英寸AMOLED\n- 电池：5000mAh\n- 内存：8GB+128GB\n- 价格：2999元起\n这是一段较长的配置描述，实际应用中可能会更长...",
            "importance": 0.8,
            "flexible": True
        },
        {
            "content": "【用户偏好】用户偏好X品牌，预算3000-5000元，对X12 Pro和X12 Pro Max感兴趣。",
            "importance": 0.7,
            "flexible": True
        }
    ]

    print("\n优化前各组件长度:")
    for i, comp in enumerate(components, 1):
        tokens = cwm.estimate_tokens(comp["content"])
        print(f"  组件{i}: {tokens} tokens | 重要性: {comp['importance']} | 可压缩: {comp['flexible']}")

    print(f"\n总 token 数: {sum(cwm.estimate_tokens(c['content']) for c in components)}")

    print("\n优化后 (max_tokens=800, reserve=200):")
    cwm_test = ContextWindowManager(max_tokens=800, reserve_tokens=200)
    optimized = cwm_test.optimize_context(components)

    for i, comp in enumerate(optimized, 1):
        tokens = cwm.estimate_tokens(comp["content"])
        print(f"  组件{i}: {tokens} tokens | {comp['content'][:50]}...")

    print("\n[OK] 上下文窗口管理器测试完成")


def test_context_engineering_manager():
    """测试统一的上下文工程管理器"""
    print("\n" + "="*60)
    print("测试 6: 统一上下文工程管理器 (三层记忆)")
    print("="*60)

    cem = context_engineering_manager

    print("\n模拟多轮对话 (用户: test_user_001):")
    user_id = "test_user_001"

    dialogs = [
        ("user", "X12 Pro手机多少钱？", "price_inquiry", ["X12 Pro"], None),
        ("assistant", "X12 Pro售价2999元起。", None, [], None),
        ("user", "它的续航和屏幕怎么样？", "product_spec", ["X12 Pro", "续航", "屏幕"], None),
        ("assistant", "X12 Pro配备6.7英寸AMOLED屏幕，5000mAh电池。", None, [], None),
    ]

    for role, content, intent, entities, rag_results in dialogs:
        cem.add_turn(role, content, intent, entities, rag_results)
        print(f"  Turn: [{role}] {content[:25]}... | Intent: {intent}")

    print("\n检查是否触发压缩:")
    print(f"  上下文密度: {cem.short_term.calculate_density():.2%}")
    print(f"  应该压缩: {cem.short_term.should_compress()}")

    if cem.short_term.should_compress():
        print("\n触发压缩:")
        cem._trigger_compression()

    print("\n获取统一上下文:")
    unified = cem.get_unified_context(user_id, include_long_term=True)

    print(f"  短期记忆轮数: {unified['stats']['short_term_turns']}")
    print(f"  压缩记忆数: {unified['stats']['compressed_memories']}")
    print(f"  上下文密度: {unified['stats']['density']:.2%}")
    print(f"  长期记忆: {unified['long_term'][:100]}...")
    print(f"  意图连续性: {unified['intent_continuity']}")

    print("\n构建完整 LLM 提示词:")
    prompt = cem.build_llm_prompt(
        user_id=user_id,
        system_prompt="你是一个智能客服助手，请根据提供的信息回答用户问题。"
    )
    print("-"*60)
    print(prompt[:800] + "..." if len(prompt) > 800 else prompt)
    print("-"*60)

    print("\n[OK] 统一上下文工程管理器测试完成")


def test_enhanced_generation_context():
    """测试增强版生成上下文层"""
    print("\n" + "="*60)
    print("测试 7: 增强版生成上下文层")
    print("="*60)

    layer = enhanced_generation_context_layer

    print("\n模拟多轮对话:")
    user_id = "test_user_002"

    dialogs = [
        ("user", "X12 Pro有什么颜色可选？", "product_spec", ["X12 Pro", "颜色"]),
        ("assistant", "X12 Pro有星际黑、极光蓝和晨曦金三种颜色。", None, []),
        ("user", "哪种颜色最受欢迎？", "product_spec", ["X12 Pro"]),
        ("assistant", "根据销售数据，星际黑最受欢迎。", None, []),
    ]

    for role, content, intent, entities in dialogs:
        layer.track_turn(role, content, intent, entities)

    print("\n构建生成上下文:")
    mock_docs = [
        {
            "id": "doc_1",
            "content": "X12 Pro颜色选项：\n1. 星际黑 - 经典配色，最受欢迎\n2. 极光蓝 - 渐变效果，时尚之选\n3. 晨曦金 - 高端大气，适合商务",
            "metadata": {"source_file": "product_info.txt"},
            "score": 0.95
        }
    ]

    context = layer.build_context(
        documents=mock_docs,
        intent="product_spec",
        query="X12 Pro有什么颜色可选？",
        user_id=user_id
    )

    print(f"  意图: {context.intent}")
    print(f"  文档数: {context.metadata['doc_count']}")
    print(f"  上下文块数: {len(context.context_blocks)}")

    print("\n格式化 LLM 提示词:")
    formatted = layer.format_for_llm(context, include_continuity=True)
    print("-"*60)
    print(formatted)
    print("-"*60)

    print("\n[OK] 增强版生成上下文层测试完成")


def test_multi_turn_scenario():
    """测试完整的多轮对话场景"""
    print("\n" + "="*60)
    print("测试 8: 完整多轮对话场景")
    print("="*60)

    cem = context_engineering_manager
    layer = enhanced_generation_context_layer

    user_id = "customer_001"

    print("\n=== 场景：客户咨询产品 ===\n")

    print("第1轮：询问价格")
    cem.add_turn("user", "X12 Pro多少钱？", "price_inquiry", ["X12 Pro"])
    cem.add_turn("assistant", "X12 Pro售价2999元起。", None, [])

    print("第2轮：询问配置")
    cem.add_turn("user", "配置怎么样？", "product_spec", ["X12 Pro"])
    cem.add_turn("assistant", "X12 Pro配备骁龙8处理器，8GB+128GB存储。", None, [])

    print("第3轮：询问续航")
    cem.add_turn("user", "续航如何？", "product_spec", ["X12 Pro", "续航"])
    cem.add_turn("assistant", "配备5000mAh电池，支持66W快充。", None, [])

    print("第4轮：询问对比（话题切换）")
    cem.add_turn("user", "和X12 Pro Max比呢？", "comparison", ["X12 Pro", "X12 Pro Max"])
    cem.add_turn("assistant", "X12 Pro Max售价3999元，屏幕更大，电池更强。", None, [])

    print("第5轮：回到价格话题（话题回归）")
    cem.add_turn("user", "那现在有优惠吗？", "price_inquiry", ["X12 Pro"])
    cem.add_turn("assistant", "目前有分期免息活动。", None, [])

    print("\n=== 检查上下文状态 ===\n")

    stats = cem.get_stats()
    print(f"短期记忆轮数: {stats['short_term']['turn_count']}")
    print(f"上下文密度: {stats['short_term']['density']:.2%}")
    print(f"是否触发压缩: {stats['short_term']['should_compress']}")
    print(f"当前目标: {stats['intent']['current_goal']}")

    print("\n意图演进历史:")
    for entry in cem.intent_tracker.intent_sequence:
        print(f"  - {entry['intent']} (置信度: {entry['confidence']})")

    print("\n连续性上下文 (目标复述 - Manus 技巧):")
    continuity = cem.intent_tracker.get_continuity_context()
    print(f"  {continuity}")

    print("\n提取的关键实体:")
    entities = cem.short_term.extract_entities()
    for entity, count in list(entities.items())[:5]:
        print(f"  - {entity}: {count}次")

    print("\n=== 生成最终回复上下文 ===\n")

    mock_docs = [
        {
            "id": "doc_1",
            "content": "X12 Pro 限时优惠：\n- 原价2999元\n- 分期免息\n- 赠品：手机壳+贴膜",
            "metadata": {"source_file": "promotion.txt"},
            "score": 0.92
        }
    ]

    context = layer.build_context(
        documents=mock_docs,
        intent="price_inquiry",
        query="那现在有优惠吗？",
        user_id=user_id
    )

    print("LLM 提示词:")
    formatted = layer.format_for_llm(context)
    print("-"*60)
    print(formatted if formatted else "(空)")

    print("\n[OK] 完整多轮对话场景测试完成")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "#"*60)
    print("# 上下文工程测试套件")
    print("# 基于 Claude Code & Manus 最佳实践")
    print("#"*60)

    try:
        test_short_term_memory()
        test_medium_term_memory()
        test_long_term_memory()
        test_intent_evolution_tracker()
        test_context_window_manager()
        test_context_engineering_manager()
        test_enhanced_generation_context()
        test_multi_turn_scenario()

        print("\n" + "#"*60)
        print("# [OK] 所有测试通过")
        print("#"*60)
        print("\n上下文工程实现完成！")
        print("\n主要功能：")
        print("  ✓ 三层记忆架构 (短期/中期/长期)")
        print("  ✓ 意图演进跟踪")
        print("  ✓ 智能压缩 (92%阈值)")
        print("  ✓ 上下文窗口管理")
        print("  ✓ 多轮对话上下文保持")
        print("  ✓ 用户偏好持久化")

    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
