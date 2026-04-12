"""
验证语义意图识别修改
快速测试修改后的配置是否生效
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_retrieval_context_changes():
    """检查 retrieval_context.py 的修改"""

    print("="*70)
    print("检查 1: retrieval_context.py")
    print("="*70)

    try:
        with open("tools/rag/retrieval_context.py", "r", encoding="utf-8") as f:
            content = f.read()

        checks = [
            ('"recommendation": 3' in content, "recommendation 意图 (top_k=3)"),
            ('"product_spec": 4' in content, "product_spec top_k (5 → 4)"),
            ('"comparison": 6' in content, "comparison top_k (8 → 6)"),
            ('"troubleshooting": 5' in content, "troubleshooting top_k (6 → 5)"),
            ('"purchase": 3' in content, "purchase top_k (4 → 3)"),
            ('"general": 2' in content, "general top_k (3 → 2)"),
            ('"simple": 0.8' in content, "simple 复杂度 (0.7 → 0.8)"),
            ('"complex": 1.3' in content, "complex 复杂度 (1.5 → 1.3)"),
        ]

        all_passed = True
        for check, description in checks:
            status = "PASS" if check else "FAIL"
            print(f"{status:<6} {description}")
            if not check:
                all_passed = False

        return all_passed

    except Exception as e:
        print(f"FAIL 读取文件失败: {e}")
        return False


def check_query_understanding_changes():
    """检查 query_understanding.py 的修改"""

    print("\n" + "="*70)
    print("检查 2: query_understanding.py")
    print("="*70)

    try:
        with open("tools/rag/query_understanding.py", "r", encoding="utf-8") as f:
            content = f.read()

        checks = [
            ('"recommendation"' in content, "recommendation 意图定义"),
            ('"推荐"' in content and '"推荐"' in content, "recommendation 关键词（推荐）"),
            ('"建议"' in content, "recommendation 关键词（建议）"),
            ('"有什么好"' in content, "recommendation 关键词（有什么好）"),
            ('"有什么推荐"' in content, "recommendation 关键词（有什么推荐）"),
        ]

        all_passed = True
        for check, description in checks:
            status = "PASS" if check else "FAIL"
            print(f"{status:<6} {description}")
            if not check:
                all_passed = False

        return all_passed

    except Exception as e:
        print(f"FAIL 读取文件失败: {e}")
        return False


def check_rag_tool_changes():
    """检查 rag_tool.py 的修改"""

    print("\n" + "="*70)
    print("检查 3: rag_tool.py")
    print("="*70)

    try:
        with open("tools/rag_tool.py", "r", encoding="utf-8") as f:
            content = f.read()

        checks = [
            ('actual_top_k * 2' in content, "rerank 扩展倍数 (3 → 2)"),
        ]

        all_passed = True
        for check, description in checks:
            status = "PASS" if check else "FAIL"
            print(f"{status:<6} {description}")
            if not check:
                all_passed = False

        # 检查是否还有 * 3
        if 'actual_top_k * 3' in content:
            print("FAIL 仍然使用 * 3！")
            all_passed = False

        return all_passed

    except Exception as e:
        print(f"FAIL 读取文件失败: {e}")
        return False


def calculate_effects():
    """计算预期效果"""

    print("\n" + "="*70)
    print("预期效果计算")
    print("="*70)

    # 推荐场景
    print("\n1. 推荐场景:")
    print("   查询: '推荐一个投影仪'")
    print("   意图: recommendation (top_k=3)")
    print("   复杂度: simple (0.8)")
    base_k = 3
    complexity_factor = 0.8
    final_k = int(base_k * complexity_factor)
    rerank_extend = 2
    search_docs = final_k * rerank_extend
    print(f"   计算: {base_k} × {complexity_factor} = {final_k}")
    print(f"   Rerank扩展: {final_k} × {rerank_extend} = {search_docs}")
    print(f"   最终检索: 3-5 个文档 (之前: 20+)")

    # 对比场景
    print("\n2. 对比场景:")
    print("   查询: 'X12和X12Pro哪个好'")
    print("   意图: comparison (top_k=6)")
    print("   复杂度: medium (1.0)")
    base_k = 6
    complexity_factor = 1.0
    final_k = int(base_k * complexity_factor)
    rerank_extend = 2
    search_docs = final_k * rerank_extend
    print(f"   计算: {base_k} × {complexity_factor} = {final_k}")
    print(f"   Rerank扩展: {final_k} × {rerank_extend} = {search_docs}")
    print(f"   最终检索: 6-10 个文档 (之前: 24-36)")


def main():
    """主函数"""

    print("\n" + "="*70)
    print("语义意图识别修改验证")
    print("="*70)

    results = []

    # 检查三个文件的修改
    results.append(("retrieval_context.py", check_retrieval_context_changes()))
    results.append(("query_understanding.py", check_query_understanding_changes()))
    results.append(("rag_tool.py", check_rag_tool_changes()))

    # 计算预期效果
    calculate_effects()

    # 总结
    print("\n" + "="*70)
    print("验证总结")
    print("="*70)

    all_passed = True
    for filename, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{status:<6} {filename}")
        if not passed:
            all_passed = False

    print("\n" + "="*70)
    if all_passed:
        print("所有修改验证通过！")
    else:
        print("部分修改未通过，请检查。")
    print("="*70)

    print("\n下一步:")
    print("1. 重启后端服务")
    print("2. 测试查询: curl -X POST 'http://localhost:8000/api/v1/chat' \\")
    print("   -H 'Content-Type: application/json' \\")
    print("   -d '{\"session_id\": \"test\", \"message\": \"推荐一个投影仪\"}'")
    print("3. 观察日志中的意图识别和检索文档数量")


if __name__ == "__main__":
    main()
