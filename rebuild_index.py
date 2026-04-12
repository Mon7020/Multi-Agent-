"""
重建 ChromaDB 索引脚本
完全删除旧数据并重新加载知识库
"""

import sys
import os
import shutil
sys.path.insert(0, os.path.dirname(__file__))

from tools.rag_tool import RAGTool
import chromadb
from chromadb.config import Settings

print("=" * 80)
print("重建 ChromaDB 索引")
print("=" * 80)

# 1. 完全删除 ChromaDB 数据
chroma_path = 'd:/agentlearn/ai-engineer-training/projects/test2langchain/chroma_data'
if os.path.exists(chroma_path):
    print("\n[1] 删除旧索引...")
    shutil.rmtree(chroma_path)
    print("  [OK] 已删除旧索引")
else:
    print("\n[1] 索引目录不存在")

# 2. 重置 ChromaDB 客户端
print("\n[2] 重置 ChromaDB 客户端...")

# 3. 手动加载知识库文档
print("\n[3] 手动加载知识库...")

# 创建 RAGTool（会重新初始化 ChromaDB）
rag = RAGTool()

# 检查当前集合状态
print(f"\n[4] 检查集合状态...")
if rag.collection:
    count = rag.collection.count()
    print(f"  当前文档数: {count}")

    if count == 0:
        print("  集合为空，需要重新加载文档")
    else:
        print("  集合已有文档，将使用现有数据")
else:
    print("  集合不存在，需要重新创建")

# 4. 测试检索
print("\n[5] 测试检索...")
result = rag.retrieve("X12 Pro手机多少钱", top_k=3)
docs = result.get('documents', [])
print(f"  检索到 {len(docs)} 个文档")

for i, doc in enumerate(docs[:3]):
    content = doc.get('content', doc.get('page_content', ''))[:80]
    method = doc.get('retrieval_method', 'unknown')
    score = doc.get('similarity_score', 0)
    print(f"\n  --- 结果 {i+1} ---")
    print(f"  方法: {method}")
    print(f"  分数: {score:.4f}")
    print(f"  内容: {content}...")

print("\n" + "=" * 80)
print("重建完成")
print("=" * 80)
