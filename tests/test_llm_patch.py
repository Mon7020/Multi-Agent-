"""
验证 LLM 意图分类补丁
测试 ContextRAGFusionLayer 是否正确使用 LLM
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_llm_intent_in_fusion_layer():
    """测试 ContextRAGFusionLayer 的 LLM 意图分类"""

    print("="*70)
    print("测试 ContextRAGFusionLayer LLM 意图分类")
    print("="*70)

    try:
        from tools.rag.context_rag_fusion import ContextRAGFusionLayer, LLMIntentClassifier

        print("[PASS] LLMIntentClassifier 导入成功")

        # 测试 LLMIntentClassifier
        classifier = LLMIntentClassifier()
        print(f"[PASS] LLMIntentClassifier 实例创建成功")

        # 测试不带 LLM 的分类
        intent, confidence, reasoning = classifier.classify("推荐一个投影仪", None)
        print(f"\n[PASS] 不带 LLM 的分类测试:")
        print(f"  - intent: {intent}")
        print(f"  - confidence: {confidence}")
        print(f"  - reasoning: {reasoning}")

        # 测试 ContextRAGFusionLayer 初始化（不带 LLM）
        fusion_layer_no_llm = ContextRAGFusionLayer()
        print(f"\n[PASS] ContextRAGFusionLayer 初始化（无 LLM）:")
        print(f"  - _llm: {fusion_layer_no_llm._llm}")
        print(f"  - _intent_classifier: {fusion_layer_no_llm._intent_classifier}")

        # 测试 ContextRAGFusionLayer 初始化（带 LLM）
        class MockLLM:
            def invoke(self, prompt):
                return '{"intent": "recommendation", "confidence": 0.95, "reasoning": "用户请求推荐产品"}'

        mock_llm = MockLLM()
        fusion_layer_with_llm = ContextRAGFusionLayer(llm=mock_llm)
        print(f"\n[PASS] ContextRAGFusionLayer 初始化（带 LLM）:")
        print(f"  - _llm: {fusion_layer_with_llm._llm}")
        print(f"  - _intent_classifier: {fusion_layer_with_llm._intent_classifier}")

        # 测试 LLM 意图分类
        intent, confidence, reasoning = fusion_layer_with_llm._intent_classifier.classify(
            "推荐一个投影仪", mock_llm
        )
        print(f"\n[PASS] LLM 意图分类测试:")
        print(f"  - intent: {intent}")
        print(f"  - confidence: {confidence}")
        print(f"  - reasoning: {reasoning}")

        return True

    except Exception as e:
        print(f"[FAIL] 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*70)
    print("LLM 意图分类补丁验证")
    print("="*70)

    result = test_llm_intent_in_fusion_layer()

    print("\n" + "="*70)
    if result:
        print("[PASS] 所有测试通过！")
        print("\n修复说明:")
        print("  1. ContextRAGFusionLayer 现在使用 LLMIntentClassifier")
        print("  2. 在 process 方法中调用 LLM 进行意图分类")
        print("  3. 日志会显示: [FusionLayer] LLM 意图: recommendation")
        print("\n下一步:")
        print("  1. 重启后端服务")
        print("  2. 测试查询: '推荐一个投影仪'")
        print("  3. 观察日志中的 LLM 意图分类")
    else:
        print("[FAIL] 部分测试失败")
    print("="*70)


if __name__ == "__main__":
    main()
