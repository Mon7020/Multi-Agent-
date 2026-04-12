"""
检查向量维度是否匹配
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sentence_transformers import SentenceTransformer
from tools.rag_tool import RAGTool

print("=" * 80)
print("检查向量维度")
print("=" * 80)

# 1. 检查旧模型维度
print("\n[1] 检查 all-MiniLM-L6-v2 (旧模型) 向量维度:")
old_model = SentenceTransformer('all-MiniLM-L6-v2')
test_text = ["X12 Pro手机"]
old_embedding = old_model.encode(test_text)
print(f"  向量维度: {old_embedding.shape}")
print(f"  样例向量: {old_embedding[0][:5]}...")

# 2. 检查新模型维度
print("\n[2] 检查 text2vec-base-chinese (新模型) 向量维度:")
new_model = SentenceTransformer('shibing624/text2vec-base-chinese')
new_embedding = new_model.encode(test_text)
print(f"  向量维度: {new_embedding.shape}")
print(f"  样例向量: {new_embedding[0][:5]}...")

# 3. 检查 ChromaDB 中存储的向量维度
print("\n[3] 检查 ChromaDB 中存储的向量维度:")
rag = RAGTool()

# 获取一条数据查看其向量
if rag.collection:
    result = rag.collection.get(limit=1, include=['embeddings'])
    if result['embeddings'] and result['embeddings'][0]:
        stored_embedding = result['embeddings'][0]
        print(f"  存储的向量维度: {len(stored_embedding)}")
        print(f"  存储的向量样例: {stored_embedding[:5]}...")

        # 4. 对比
        print("\n[4] 维度对比:")
        print(f"  旧模型维度: {old_embedding.shape[1]}")
        print(f"  新模型维度: {new_embedding.shape[1]}")
        print(f"  ChromaDB存储维度: {len(stored_embedding)}")

        if old_embedding.shape[1] != new_embedding.shape[1]:
            print("\n  ❌ 维度不匹配！这就是检索不准确的原因！")
            print("  解决方案：需要用新模型重新生成并存储向量")
        else:
            print("\n  ✅ 维度匹配")
    else:
        print("  ChromaDB中没有存储向量数据")
else:
    print("  ChromaDB集合为空")

print("\n" + "=" * 80)
