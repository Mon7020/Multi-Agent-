"""
检查 ChromaDB 数据内容
"""

import os

path = 'd:/agentlearn/ai-engineer-training/projects/test2langchain/chroma_data'

if os.path.exists(path):
    print(f'目录: {path}')

    # 列出所有文件和子目录
    for root, dirs, files in os.walk(path):
        level = root.replace(path, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f'{indent}{os.path.basename(root)}/')

        sub_indent = ' ' * 2 * (level + 1)
        for file in files:
            filepath = os.path.join(root, file)
            size = os.path.getsize(filepath)
            print(f'{sub_indent}{file} ({size} bytes)')
else:
    print(f'目录不存在: {path}')

print('\n总结: ChromaDB 使用持久化存储，删除后重启会自动重建')
