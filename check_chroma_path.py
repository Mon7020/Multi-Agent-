"""
检查 ChromaDB 数据路径
"""

import os

paths = [
    'd:/agentlearn/ai-engineer-training/projects/test2langchain/chroma_data',
    'd:/agentlearn/ai-engineer-training/projects/test2langchain/.chroma',
    'd:/agentlearn/ai-engineer-training/projects/test2langchain/data/chroma',
    'd:/agentlearn/ai-engineer-training/.chroma',
    os.path.expanduser('~/.chroma'),
]

print('检查 ChromaDB 数据目录:')
for path in paths:
    exists = os.path.exists(path)
    print(f'  {path}: {"存在" if exists else "不存在"}')

    if exists and os.path.isdir(path):
        try:
            files = os.listdir(path)
            print(f'    包含 {len(files)} 个文件/目录')
        except:
            pass
