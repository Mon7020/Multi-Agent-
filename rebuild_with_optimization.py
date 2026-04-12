"""
优化后重建向量索引
1. 删除旧索引
2. 用优化后的配置重新嵌入文档
"""

import sys
import os
import shutil
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 80)
print("优化后重建向量索引")
print("=" * 80)

# 1. 删除旧的 ChromaDB 数据
chroma_path = 'd:/agentlearn/ai-engineer-training/projects/test2langchain/chroma_data'
if os.path.exists(chroma_path):
    print("\n[1] 删除旧索引...")
    try:
        shutil.rmtree(chroma_path)
        print("  [OK] 已删除旧索引")
    except Exception as e:
        print(f"  [ERROR] 删除失败: {e}")
        print("  请手动关闭所有 Python 窗口")
else:
    print("  [INFO] 索引目录不存在")

# 2. 验证目录已删除
if not os.path.exists(chroma_path):
    print("  [OK] 确认目录已删除")

    # 3. 初始化 RAGTool（使用优化后的配置）
    print("\n[2] 初始化 RAG 工具（使用优化配置）...")
    from tools.rag_tool import RAGTool

    rag = RAGTool()

    # 4. 检查缓存配置
    print("\n[3] 检查缓存配置:")
    print(f"  缓存类型: {type(rag.cache).__name__}")
    if hasattr(rag.cache, 'max_size'):
        print(f"  缓存容量: {rag.cache.max_size}")
    if hasattr(rag.cache, 'default_ttl'):
        print(f"  缓存TTL: {rag.cache.default_ttl}秒 = {rag.cache.default_ttl/3600:.0f}小时")

    # 5. 检查集合配置
    print("\n[4] 检查集合配置:")
    if rag.collection:
        meta = rag.collection.metadata
        print(f"  HNSW 参数:")
        print(f"    space: {meta.get('hnsw:space', 'N/A')}")
        print(f"    construction_ef: {meta.get('hnsw:construction_ef', 'N/A')}")
        print(f"    search_ef: {meta.get('hnsw:search_ef', 'N/A')}")
        print(f"    M: {meta.get('hnsw:M', 'N/A')}")
        print(f"  文档数量: {rag.collection.count()}")

    # 6. 测试检索
    print("\n[5] 测试检索性能:")
    import time

    test_queries = [
        "X12 Pro手机",
        "蓝牙耳机",
        "智能手表"
    ]

    latencies = []
    for query in test_queries:
        start = time.time()
        result = rag.retrieve(query, top_k=3)
        latency = (time.time() - start) * 1000
        latencies.append(latency)
        print(f"  查询: {query}")
        print(f"    延迟: {latency:.0f}ms")
        print(f"    结果数: {len(result.get('documents', []))}")

    print(f"\n  平均延迟: {sum(latencies)/len(latencies):.0f}ms")

else:
    print("\n[ERROR] 无法删除旧索引！")

print("\n" + "=" * 80)
print("重建完成")
print("=" * 80)
