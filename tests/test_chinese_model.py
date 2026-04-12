"""
测试中文向量模型效果
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from tools.rag_tool import RAGTool

print("=" * 80)
print("测试中文向量模型")
print("=" * 80)

print("\n[1] 初始化 RAG 工具（将下载中文模型）...")
rag = RAGTool()

print("\n[2] 测试向量检索:")
print("  查询: X12 Pro手机")

result = rag.collection.query(
    query_texts=['X12 Pro手机'],
    n_results=5,
    include=['documents', 'distances']
)

print(f"\n  返回 {len(result['documents'][0])} 个结果:")
for i, (doc, dist) in enumerate(zip(result['documents'][0], result['distances'][0])):
    print(f"\n  --- 结果 {i+1} (距离: {dist:.4f}) ---")
    print(f"  {doc[:150]}...")

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
