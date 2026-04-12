"""
快速验证 V3 配置（无需导入模块）
"""

import os

def check_file_exists(path, description):
    """检查文件是否存在"""
    if os.path.exists(path):
        print(f"[OK] {description}: {path}")
        return True
    else:
        print(f"[FAIL] {description} 不存在: {path}")
        return False

def check_file_content(file_path, search_string, description):
    """检查文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if search_string in content:
            print(f"[OK] {description}")
            return True
        else:
            print(f"[FAIL] {description} - 未找到关键内容")
            return False
    except Exception as e:
        print(f"[FAIL] {description} - 读取失败: {e}")
        return False

def main():
    print("="*70)
    print("ChatServiceV3 配置验证")
    print("="*70)

    results = []

    print("\n1. 核心文件检查:")
    results.append(check_file_exists(
        "tools/rag/context_rag_fusion.py",
        "融合层核心文件"
    ))
    results.append(check_file_exists(
        "backend/app/services/chat_service_v3.py",
        "V3服务文件"
    ))
    results.append(check_file_exists(
        "backend/app/api/v1/chat.py",
        "API路由文件"
    ))
    results.append(check_file_exists(
        "backend/app/schemas.py",
        "数据模型文件"
    ))

    print("\n2. V3配置检查:")
    results.append(check_file_content(
        "backend/app/api/v1/chat.py",
        "chat_service_v3",
        "API使用V3服务"
    ))
    results.append(check_file_content(
        "backend/app/api/v1/chat.py",
        "Context+RAG融合",
        "API包含融合说明"
    ))

    print("\n3. Schema更新检查:")
    results.append(check_file_content(
        "backend/app/schemas.py",
        "fusion_info",
        "响应包含fusion_info"
    ))
    results.append(check_file_content(
        "backend/app/schemas.py",
        "context_summary",
        "响应包含context_summary"
    ))

    print("\n4. 融合层特性检查:")
    results.append(check_file_content(
        "tools/rag/context_rag_fusion.py",
        "ContextExtractor",
        "包含上下文提取器"
    ))
    results.append(check_file_content(
        "tools/rag/context_rag_fusion.py",
        "RAGResultInjector",
        "包含RAG结果注入器"
    ))
    results.append(check_file_content(
        "tools/rag/context_rag_fusion.py",
        "AdaptiveFusionEngine",
        "包含自适应融合引擎"
    ))
    results.append(check_file_content(
        "tools/rag/context_rag_fusion.py",
        "RetrievalQuality",
        "包含检索质量评估"
    ))
    results.append(check_file_content(
        "tools/rag/context_rag_fusion.py",
        "FusionStrategy",
        "包含融合策略枚举"
    ))

    print("\n" + "="*70)
    print("验证结果汇总")
    print("="*70)

    passed = sum(results)
    total = len(results)
    print(f"\n通过: {passed}/{total}")

    if passed == total:
        print("\n配置成功！ ChatServiceV3 已完全配置")
    else:
        print("\n部分配置缺失，请检查失败项")

    print("\n" + "="*70)
    print("V3 核心功能:")
    print("="*70)
    print("1. Context+RAG 双向信息流")
    print("2. 自适应融合策略 (HYBRID/RAG_PRIMARY/CONTEXT_PRIMARY/CONTEXT_ONLY)")
    print("3. 智能质量评估 (HIGH/MEDIUM/LOW/NONE)")
    print("4. 上下文感知检索优化")
    print("5. RAG结果智能注入到SessionContext")

    print("\n" + "="*70)
    print("启动方式:")
    print("="*70)
    print("1. 安装依赖: pip install -r backend/requirements.txt")
    print("2. 配置环境变量: 复制 .env.example 为 .env")
    print("3. 启动服务: uvicorn backend.app.main:app --reload")
    print("4. 访问API: http://localhost:8000/docs")

    print("\n" + "="*70)
    print("API调用示例:")
    print("="*70)
    print("""
POST /api/v1/chat
{
    "session_id": "user_001",
    "message": "X12投影仪多少钱？",
    "history": []
}

响应将包含:
- fusion_info: {
    "enabled": true,
    "quality": "high",
    "strategy": "hybrid",
    "confidence": 0.85,
    "context_strength": 0.7
  }
- context_summary: 会话摘要信息
- retrieved_documents: 检索到的文档
    """)

if __name__ == "__main__":
    main()
