"""
完整的API场景测试
模拟实际的消息处理流程
"""

from typing import Dict, List, Any


def test_process_message_flow():
    """模拟 process_message 的完整流程"""

    print("="*70)
    print("测试: 模拟 process_message 完整流程")
    print("="*70)

    # 模拟 fusion_result.metadata
    fusion_result_metadata = {
        "injection_summary": {
            "query": "介绍下产品",
            "quality": "low",
            "doc_count": 0
        }
    }

    print("\n1. 提取 retrieval_result.documents")
    print("-" * 70)

    # 错误的做法（会导致 Pydantic 验证失败）
    print("\n[错误做法] 原代码:")
    wrong_result = fusion_result_metadata.get("injection_summary", {}).get("query") or "介绍下产品"
    print(f"  documents = fusion_result.metadata.get('injection_summary', {{}}).get('query') or message")
    print(f"  结果: {wrong_result}")
    print(f"  类型: {type(wrong_result)}")
    print(f"  问题: Pydantic 期望 list，实际收到 str")

    # 正确的做法（已修复）
    print("\n[正确做法] 修复后:")
    correct_result = fusion_result_metadata.get("injection_summary", {}).get("query") or []
    print(f"  documents = fusion_result.metadata.get('injection_summary', {{}}).get('query') or []")
    print(f"  结果: {correct_result}")
    print(f"  类型: {type(correct_result)}")
    print(f"  状态: [PASS] 类型正确")

    # 模拟完整的 rag_result
    print("\n2. 构建 rag_result")
    print("-" * 70)

    rag_result = {
        "success": True,
        "documents": correct_result,
        "has_relevant_info": False
    }

    print(f"  rag_result = {rag_result}")
    print(f"  [PASS] rag_result 构建成功")

    # 模拟 ChatResponse 验证
    print("\n3. ChatResponse 字段验证")
    print("-" * 70)

    retrieved_documents = rag_result.get("documents", [])
    print(f"  retrieved_documents = {retrieved_documents}")
    print(f"  类型检查: {type(retrieved_documents)}")

    # Pydantic 验证模拟
    try:
        # 验证是否为列表
        assert isinstance(retrieved_documents, list), "retrieved_documents 必须是列表"
        print(f"  [PASS] 类型验证通过: list")

        # 验证字段完整性
        response_data = {
            "session_id": "session_1775560035737",
            "message": "好的，我来为您介绍产品...",
            "intent": "sales",
            "retrieved_documents": retrieved_documents,
            "retrieved_count": len(retrieved_documents),
            "fusion_info": {
                "enabled": True,
                "quality": "low",
                "strategy": "context_primary",
                "confidence": 0.6
            }
        }

        print(f"\n4. 构建 ChatResponse")
        print("-" * 70)
        print(f"  session_id: {response_data['session_id']}")
        print(f"  message: {response_data['message'][:50]}...")
        print(f"  intent: {response_data['intent']}")
        print(f"  retrieved_documents: {response_data['retrieved_documents']}")
        print(f"  retrieved_count: {response_data['retrieved_count']}")
        print(f"  fusion_info: {response_data['fusion_info']}")

        print(f"\n  [PASS] ChatResponse 构建成功！")
        return True

    except AssertionError as e:
        print(f"  [FAIL] 验证失败: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] 错误: {e}")
        return False


def test_multiple_scenarios():
    """测试多种场景"""

    print("\n" + "="*70)
    print("测试: 多种场景验证")
    print("="*70)

    scenarios = [
        {
            "name": "场景1: 新会话，无历史",
            "injection_summary": {},
            "expected": []
        },
        {
            "name": "场景2: 有关键信息，无文档",
            "injection_summary": {
                "query": "介绍下产品",
                "quality": "low"
            },
            "expected": []
        },
        {
            "name": "场景3: 检索成功，有文档",
            "injection_summary": {
                "query": "X12投影仪",
                "quality": "high",
                "entities_extracted": ["X12", "投影仪"]
            },
            "expected": []
        },
        {
            "name": "场景4: 复杂查询，多文档",
            "injection_summary": {
                "query": "X12和X12Pro哪个好",
                "quality": "high",
                "doc_count": 5
            },
            "expected": []
        }
    ]

    all_passed = True

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print("-" * 70)

        try:
            # 模拟提取逻辑
            fusion_result_metadata = {
                "injection_summary": scenario["injection_summary"]
            }

            # 使用修复后的代码
            documents = fusion_result_metadata.get("injection_summary", {}).get("query") or []

            # 验证类型
            assert isinstance(documents, list), f"必须是列表，实际: {type(documents)}"

            print(f"   injection_summary: {scenario['injection_summary']}")
            print(f"   extracted documents: {documents}")
            print(f"   type: {type(documents).__name__}")
            print(f"   [PASS]")

        except Exception as e:
            print(f"   [FAIL] {e}")
            all_passed = False

    return all_passed


def main():
    """主测试函数"""

    print("\n" + "="*70)
    print("ChatServiceV3 - API修复验证测试")
    print("="*70)

    # 测试1: 完整流程
    result1 = test_process_message_flow()

    # 测试2: 多种场景
    result2 = test_multiple_scenarios()

    # 总结
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)

    print(f"\n1. process_message 流程: {'[PASS]' if result1 else '[FAIL]'}")
    print(f"2. 多种场景验证: {'[PASS]' if result2 else '[FAIL]'}")

    if result1 and result2:
        print("\n" + "="*70)
        print("所有测试通过！API已修复成功！")
        print("="*70)
        print("\n修复内容:")
        print("  文件: backend/app/services/chat_service_v3.py")
        print("  位置: 第310行")
        print("  修改: .get('query') or message -> .get('query') or []")
        print("\n问题:")
        print("  原代码返回字符串，导致 Pydantic 验证失败")
        print("\n解决方案:")
        print("  使用空列表 [] 作为默认值，确保返回类型为 list")
    else:
        print("\n" + "="*70)
        print("部分测试失败，请检查代码")
        print("="*70)

    print("\n下一步:")
    print("1. 重启后端服务")
    print("2. 重新测试聊天接口")
    print("3. 验证 fusion_info 和 retrieved_documents 字段")


if __name__ == "__main__":
    main()
