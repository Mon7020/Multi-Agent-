"""
RAG 系统诊断脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 80)
print("RAG 系统诊断报告")
print("=" * 80)

from tools.rag_tool import RAGTool

print("\n[1] 初始化 RAG 工具...")
rag = RAGTool()

print("\n[2] 检查 ChromaDB 状态:")
print(f"  - ChromaDB 可用: {rag._db_available}")
print(f"  - Collection 对象存在: {rag.collection is not None}")

if rag.collection:
    count = rag.collection.count()
    print(f"  - 文档数量: {count}")

    if count == 0:
        print("  [WARNING] 文档数量为 0！知识库未加载！")
    elif count < 10:
        print(f"  [WARNING] 文档数量太少 ({count})，可能有问题")
    else:
        print(f"  [OK] 文档数量正常 ({count})")
else:
    print("  [ERROR] Collection 对象为 None！")

print("\n[3] 检查 ChromaDB 集合详情:")
try:
    if rag.collection:
        meta = rag.collection.metadata
        print(f"  - 集合元数据: {meta}")

        print("\n[4] 采样查看文档内容:")
        try:
            results = rag.collection.get(limit=3, include=['documents', 'metadatas'])
            for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas'])):
                print(f"\n  --- 文档 {i+1} ---")
                print(f"  内容预览: {doc[:200]}...")
                print(f"  元数据: {meta}")
        except Exception as e:
            print(f"  获取文档失败: {e}")
except Exception as e:
    print(f"  错误: {e}")

print("\n[5] 检查 BM25 索引状态:")
print(f"  - BM25 已索引: {rag._bm25_indexed}")
print(f"  - BM25 文档数: {rag._bm25_doc_count}")

print("\n[6] 测试向量检索:")
try:
    if rag.collection is None:
        print("  [ERROR] Collection 为 None，无法测试")
    else:
        result = rag.collection.query(
            query_texts=['X12 Pro手机'],
            n_results=3,
            include=['documents', 'metadatas', 'distances']
        )
        if result['documents'] and result['documents'][0]:
            print(f"  [OK] 向量检索成功，返回 {len(result['documents'][0])} 条结果")
            for i, (doc, meta, dist) in enumerate(zip(
                result['documents'][0],
                result['metadatas'][0],
                result['distances'][0]
            )):
                print(f"\n  --- 结果 {i+1} (距离: {dist:.4f}) ---")
                print(f"  来源: {meta.get('source', '未知')}")
                print(f"  内容: {doc[:150]}...")
        else:
            print("  [ERROR] 向量检索返回空结果")
except Exception as e:
    print(f"  [ERROR] 向量检索失败: {e}")

print("\n[7] 测试查询接口:")
try:
    query_result = rag.retrieve('X12 Pro手机多少钱', top_k=3)
    docs = query_result.get('documents', [])
    print(f"  检索结果数: {len(docs)}")

    for i, doc in enumerate(docs[:3]):
        if isinstance(doc, dict):
            meta = doc.get('metadata', {})
            source = meta.get('source', '未知') if isinstance(meta, dict) else '未知'
            content = doc.get('content', doc.get('page_content', ''))[:100]
        else:
            source = '未知'
            content = str(doc)[:100]
        print(f"\n  --- 结果 {i+1} ---")
        print(f"  来源: {source}")
        print(f"  内容: {content}...")
except Exception as e:
    print(f"  [ERROR] 查询失败: {e}")

print("\n" + "=" * 80)
print("诊断完成")
print("=" * 80)
