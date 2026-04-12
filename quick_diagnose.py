"""
快速诊断脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from tools.rag_tool import RAGTool

rag = RAGTool()

print("ChromaDB 状态:")
print(f"  文档数量: {rag.collection.count()}")
print(f"  BM25 已索引: {rag._bm25_indexed}")
print(f"  BM25 文档数: {rag._bm25_doc_count}")

print("\n测试向量检索:")
result = rag.collection.query(
    query_texts=['X12 Pro手机'],
    n_results=3,
    include=['documents', 'distances']
)
for i, (doc, dist) in enumerate(zip(result['documents'][0], result['distances'][0])):
    print(f"  结果{i+1} (距离:{dist:.4f}):")
    print(f"    {doc[:100]}...")

print("\n测试 BM25 检索:")
bm25_results = rag.bm25_retriever.search('X12 Pro手机', top_k=3)
for i, result in enumerate(bm25_results):
    content = result.get("content", "")[:100]
    score = result.get("bm25_score", 0)
    print(f"  结果{i+1} (分数:{score:.4f}):")
    print(f"    {content}...")
