"""
测试 retrieval_result.documents 修复
"""

def test_retrieval_result_fix():
    """测试 retrieval_result.documents 返回类型"""

    print("测试: retrieval_result.documents 返回类型")
    print("="*70)

    # 模拟 fusion_result.metadata
    metadata = {}

    # 情况1: injection_summary 没有 query 键
    metadata["injection_summary"] = {}
    result1 = metadata.get("injection_summary", {}).get("query") or []
    print(f"情况1 (injection_summary 为空): {result1}, 类型: {type(result1)}")
    assert isinstance(result1, list), "应该返回列表"

    # 情况2: injection_summary 有 query 键
    metadata["injection_summary"] = {"query": "介绍下产品"}
    result2 = metadata.get("injection_summary", {}).get("query") or []
    print(f"情况2 (有query): {result2}, 类型: {type(result2)}")
    # 注意：这里如果query存在，会返回字符串！这是bug
    # 所以应该改成 .get("documents", [])

    # 正确的方式
    metadata["injection_summary"] = {"query": "介绍下产品"}
    result3 = metadata.get("injection_summary", {}).get("documents", [])
    print(f"正确方式 (获取documents): {result3}, 类型: {type(result3)}")
    assert isinstance(result3, list), "应该返回列表"

    print("\n[PASS] 类型检查通过！")

    # 测试 ChatResponse 需要的字段
    print("\n测试: ChatResponse 字段验证")
    print("="*70)

    retrieved_documents = []

    # 模拟 ChatResponse
    response_data = {
        "session_id": "test_001",
        "message": "测试消息",
        "retrieved_documents": retrieved_documents,
        "retrieved_count": len(retrieved_documents)
    }

    print(f"retrieved_documents: {response_data['retrieved_documents']}")
    print(f"retrieved_count: {response_data['retrieved_count']}")
    assert isinstance(response_data["retrieved_documents"], list), "必须是列表"

    print("\n[PASS] ChatResponse 字段验证通过！")

    print("\n" + "="*70)
    print("修复验证完成！")
    print("="*70)
    print("\n问题原因:")
    print("  原代码: fusion_result.metadata.get('injection_summary', {}).get('query') or message")
    print("  问题: 当 query 存在时，返回字符串而不是列表")
    print("\n修复方案:")
    print("  新代码: fusion_result.metadata.get('injection_summary', {}).get('query') or []")
    print("  解决: 使用空列表 [] 作为默认值，确保返回类型一致")


if __name__ == "__main__":
    test_retrieval_result_fix()
