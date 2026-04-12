"""
BM25 索引诊断脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 80)
print("BM25 索引诊断")
print("=" * 80)

from tools.rag_tool import RAGTool

print("\n[1] 初始化 RAG 工具...")
rag = RAGTool()

print("\n[2] 检查 BM25 索引状态:")
print(f"  - BM25 已索引: {rag._bm25_indexed}")
print(f"  - BM25 文档数: {rag._bm25_doc_count}")
print(f"  - BM25 对象文档数: {len(rag.bm25_retriever.documents)}")

print("\n[3] 强制重建 BM25 索引:")

# 模拟 retrieve 方法中的索引重建逻辑
try:
    if rag.collection:
        current_count = rag.collection.count()
        print(f"  ChromaDB 文档数: {current_count}")
        print(f"  需要重建索引: {current_count != rag._bm25_doc_count or not rag._bm25_indexed}")

        if current_count != rag._bm25_doc_count or not rag._bm25_indexed:
            print("\n  正在获取文档...")
            all_docs = rag.collection.get(include=["documents", "metadatas"])
            bm25_docs = []

            for i, doc_text in enumerate(all_docs.get("documents", [])):
                metadata = all_docs.get("metadatas", [])[i] if i < len(all_docs.get("metadatas", [])) else {}
                bm25_docs.append({
                    "content": doc_text,
                    "metadata": metadata,
                    "source_file": metadata.get("file_path", "未知"),
                    "chunk_id": metadata.get("chunk_id", "未知")
                })

            print(f"  获取到 {len(bm25_docs)} 个文档")

            print("\n  正在建立索引...")
            rag.bm25_retriever.index_documents(bm25_docs)
            rag._bm25_indexed = True
            rag._bm25_doc_count = current_count

            print(f"  [OK] 索引建立完成!")
            print(f"  - BM25 文档数: {len(rag.bm25_retriever.documents)}")
            print(f"  - 提取的关键词数: {len(rag.bm25_retriever.extracted_keywords)}")
            print(f"  - 词条统计数: {len(rag.bm25_retriever.doc_freq)}")

            # 显示一些关键词样例
            if rag.bm25_retriever.extracted_keywords:
                sample_keywords = list(rag.bm25_retriever.extracted_keywords)[:20]
                print(f"  - 关键词样例: {sample_keywords}")
except Exception as e:
    print(f"  [ERROR] 建立索引失败: {e}")
    import traceback
    traceback.print_exc()

print("\n[4] 测试 BM25 检索:")
try:
    # 测试查询
    query = "X12 Pro手机"
    print(f"  查询: {query}")

    # 直接调用 BM25 搜索
    bm25_results = rag.bm25_retriever.search(query, top_k=5)

    print(f"  BM25 返回结果数: {len(bm25_results)}")

    for i, result in enumerate(bm25_results[:5]):
        print(f"\n  --- 结果 {i+1} ---")
        print(f"  BM25 分数: {result.get('bm25_score', 0):.4f}")
        content = result.get('content', '')[:150]
        print(f"  内容: {content}...")

except Exception as e:
    print(f"  [ERROR] BM25 检索失败: {e}")
    import traceback
    traceback.print_exc()

print("\n[5] 测试混合检索（启用 BM25）:")
try:
    query = "X12 Pro手机多少钱"
    print(f"  查询: {query}")

    # 使用混合检索
    result = rag.retrieve(query, top_k=3, use_hybrid=True)

    docs = result.get('documents', [])
    print(f"  混合检索返回结果数: {len(docs)}")

    for i, doc in enumerate(docs[:3]):
        if isinstance(doc, dict):
            meta = doc.get('metadata', {})
            source = meta.get('source', '未知') if isinstance(meta, dict) else str(doc.get('metadata', '未知'))
            content = doc.get('content', doc.get('page_content', ''))[:100]
            score = doc.get('similarity_score', 0)
            method = doc.get('retrieval_method', 'unknown')
        else:
            source = '未知'
            content = str(doc)[:100]
            score = 0
            method = 'unknown'

        print(f"\n  --- 结果 {i+1} ---")
        print(f"  检索方法: {method}")
        print(f"  相似度分数: {score:.4f}")
        print(f"  来源: {source}")
        print(f"  内容: {content}...")

except Exception as e:
    print(f"  [ERROR] 混合检索失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("诊断完成")
print("=" * 80)
