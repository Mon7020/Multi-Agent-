"""
快速测试 LLM 意图分类修复
验证 self.llm 初始化问题是否已修复
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_rag_tool_initialization():
    """测试 RAGTool 初始化"""

    print("="*70)
    print("测试 RAGTool 初始化")
    print("="*70)

    try:
        # 测试导入（不会触发 __init__）
        from tools.rag_tool import RAGTool
        print("[PASS] RAGTool 导入成功")

        # 测试初始化（不使用 LLM）
        print("\n测试 RAGTool 初始化（不使用 LLM）...")
        rag_tool = RAGTool()
        print(f"[PASS] RAGTool 初始化成功")
        print(f"  - query_layer: {rag_tool.query_layer}")
        print(f"  - query_layer._llm: {rag_tool.query_layer._llm}")

        # 检查 query_layer 是否有 _llm 属性
        if hasattr(rag_tool.query_layer, '_llm'):
            print(f"[PASS] query_layer._llm 属性存在")
            if rag_tool.query_layer._llm is None:
                print(f"[INFO] _llm 为 None（将使用关键词回退）")
            else:
                print(f"[INFO] _llm 已设置")

        return True

    except AttributeError as e:
        print(f"[FAIL] AttributeError: {e}")
        print(f"  问题: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_update():
    """测试动态更新 LLM"""

    print("\n" + "="*70)
    print("测试动态更新 LLM")
    print("="*70)

    class MockLLM:
        def invoke(self, prompt):
            return '{"intent": "recommendation", "confidence": 0.95, "reasoning": "测试"}'

    try:
        from tools.rag.query_understanding import QueryUnderstandingLayer

        # 创建不带 LLM 的 layer
        layer = QueryUnderstandingLayer(llm=None)
        print(f"[PASS] 创建 QueryUnderstandingLayer（无 LLM）")
        print(f"  - _llm: {layer._llm}")

        # 动态更新 LLM
        mock_llm = MockLLM()
        layer._llm = mock_llm
        print(f"\n[PASS] 更新 _llm")
        print(f"  - _llm: {layer._llm}")

        # 测试意图分类
        intent, confidence, reasoning = layer.classify_intent("推荐一个投影仪")
        print(f"\n[PASS] 意图分类测试")
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
    print("LLM 意图分类修复验证")
    print("="*70)

    # 测试1: RAGTool 初始化
    result1 = test_rag_tool_initialization()

    # 测试2: 动态更新 LLM
    result2 = test_llm_update()

    # 总结
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)

    if result1 and result2:
        print("\n[PASS] 所有测试通过！")
        print("\n修复说明:")
        print("  1. RAGTool.__init__ 中使用 QueryUnderstandingLayer(llm=None)")
        print("  2. retrieve 方法中动态更新 self.query_layer._llm")
        print("  3. 如果有 LLM，使用 LLM 意图分类")
        print("  4. 如果无 LLM，使用关键词回退")
    else:
        print("\n[FAIL] 部分测试失败")


if __name__ == "__main__":
    main()
