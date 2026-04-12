"""
重建向量索引脚本
1. 删除旧的 ChromaDB 数据
2. 用中文模型重新嵌入文档
"""

import sys
import os
import shutil
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 80)
print("重建向量索引")
print("=" * 80)

# 1. 删除旧的 ChromaDB 数据
chroma_path = 'd:/agentlearn/ai-engineer-training/projects/test2langchain/chroma_data'
if os.path.exists(chroma_path):
    print("\n[1] 删除旧的 ChromaDB 数据...")
    try:
        shutil.rmtree(chroma_path)
        print("  [OK] 已删除旧索引")
    except Exception as e:
        print(f"  [ERROR] 删除失败: {e}")
        print("  可能仍有进程在占用文件，尝试手动关闭所有 Python 窗口")
else:
    print("  [INFO] 索引目录不存在，无需删除")

# 2. 验证目录已删除
if not os.path.exists(chroma_path):
    print("  [OK] 确认目录已删除")

    # 3. 导入并初始化 RAGTool（将自动用中文模型嵌入）
    print("\n[2] 初始化 RAG 工具（将自动用中文模型嵌入文档）...")
    from tools.rag_tool import RAGTool

    print("\n[3] 验证 ChromaDB 状态...")
    rag = RAGTool()

    if rag.collection:
        count = rag.collection.count()
        print(f"  文档数量: {count}")
        if count > 0:
            print("  [OK] 文档已成功嵌入！")
        else:
            print("  [WARNING] 文档数量为 0，可能需要手动重新加载")
    else:
        print("  [ERROR] ChromaDB 集合不存在")

    # 4. 测试检索
    print("\n[4] 测试向量检索:")
    test_query = "X12 Pro手机多少钱"
    print(f"  查询: {test_query}")

    result = rag.retrieve(test_query, top_k=3)
    docs = result.get('documents', [])
    print(f"  检索到 {len(docs)} 个文档:")

    for i, doc in enumerate(docs[:3]):
        content = doc.get('content', doc.get('page_content', ''))[:100]
        method = doc.get('retrieval_method', 'unknown')
        score = doc.get('similarity_score', 0)
        print(f"\n  --- 结果 {i+1} ---")
        print(f"  方法: {method}")
        print(f"  分数: {score:.4f}")
        print(f"  内容: {content}...")

else:
    print("\n[ERROR] 无法删除旧索引！")
    print("请手动关闭所有 Python 窗口，然后重新运行此脚本")

print("\n" + "=" * 80)
print("重建完成")
print("=" * 80)
