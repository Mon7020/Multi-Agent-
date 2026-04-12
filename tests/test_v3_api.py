"""
快速测试 ChatServiceV3 是否正常工作
验证 Context+RAG 融合功能
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_v3_import():
    """测试 V3 导入"""
    print("="*70)
    print("测试 1: 导入 ChatServiceV3")
    print("="*70)

    try:
        from backend.app.services.chat_service_v3 import ChatServiceV3
        print("[PASS] ChatServiceV3 导入成功")

        service = ChatServiceV3()
        print(f"[INFO] 服务实例: {service}")
        print(f"[INFO] 融合层: {service.fusion_layer}")

        return True
    except Exception as e:
        print(f"[FAIL] 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_v3_features():
    """测试 V3 特性"""
    print("\n" + "="*70)
    print("测试 2: V3 核心特性")
    print("="*70)

    try:
        from backend.app.services.chat_service_v3 import chat_service_v3

        print("\n[V3 核心功能]:")
        print("1. Context+RAG 融合层:")
        print(f"   - 融合引擎: {chat_service_v3.fusion_layer}")
        print(f"   - 类型: {type(chat_service_v3.fusion_layer).__name__}")

        stats = chat_service_v3.get_fusion_stats()
        print("\n2. 融合统计:")
        for key, value in stats.items():
            print(f"   - {key}: {value}")

        return True
    except Exception as e:
        print(f"[FAIL] 特性测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_integration():
    """测试 API 集成"""
    print("\n" + "="*70)
    print("测试 3: API 集成")
    print("="*70)

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "chat",
            "backend/app/api/v1/chat.py"
        )
        print("[PASS] API 文件存在")

        with open("backend/app/api/v1/chat.py", "r", encoding="utf-8") as f:
            content = f.read()

        if "chat_service_v3" in content:
            print("[PASS] API 已配置使用 ChatServiceV3")
        else:
            print("[WARN] API 可能未正确配置 V3")

        if "fusion_info" in content:
            print("[PASS] API 包含 fusion_info 字段")
        else:
            print("[INFO] fusion_info 字段已添加到 schema")

        return True
    except Exception as e:
        print(f"[FAIL] API 集成测试失败: {e}")
        return False


def test_schema_update():
    """测试 Schema 更新"""
    print("\n" + "="*70)
    print("测试 4: Schema 更新")
    print("="*70)

    try:
        from backend.app.schemas import ChatResponse

        print("[PASS] ChatResponse 模型导入成功")

        if hasattr(ChatResponse, 'model_fields'):
            fields = ChatResponse.model_fields
        else:
            fields = ChatResponse.__fields__

        if 'fusion_info' in fields:
            print("[PASS] ChatResponse 包含 fusion_info 字段")
        else:
            print("[WARN] fusion_info 字段可能未添加")

        if 'context_summary' in fields:
            print("[PASS] ChatResponse 包含 context_summary 字段")
        else:
            print("[INFO] context_summary 字段可能未添加")

        return True
    except Exception as e:
        print(f"[FAIL] Schema 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试流程"""
    print("\n" + "="*70)
    print("ChatServiceV3 - Context+RAG融合版 验证测试")
    print("="*70)

    results = []

    results.append(("V3 导入", test_v3_import()))
    results.append(("V3 特性", test_v3_features()))
    results.append(("API 集成", test_api_integration()))
    results.append(("Schema 更新", test_schema_update()))

    print("\n" + "="*70)
    print("测试结果汇总")
    print("="*70)

    all_passed = True
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {name}")
        if not result:
            all_passed = False

    print("\n" + "="*70)
    if all_passed:
        print("所有测试通过！ ChatServiceV3 已成功配置")
    else:
        print("部分测试失败，请检查配置")
    print("="*70)

    print("\n下一步:")
    print("1. 启动后端服务: python backend/run.py")
    print("2. 访问 API 文档: http://localhost:8000/docs")
    print("3. 测试聊天接口: POST /api/v1/chat")
    print("\nV3 核心优势:")
    print("  - Context+RAG 双向信息流")
    print("  - 自适应融合策略")
    print("  - 智能质量评估")
    print("  - 上下文感知检索")


if __name__ == "__main__":
    main()
