"""
知识库管理 API
支持文档的上传、查看、编辑、删除
"""
import os
import sys
import tempfile
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# 导入RAG工具的缓存类
from tools.rag_tool import LocalCache

router = APIRouter()

# 全局RAGTool实例缓存（避免重复创建）
_rag_tool_instance = None


def get_rag_tool():
    """获取RAG工具实例（单例模式）"""
    global _rag_tool_instance
    if _rag_tool_instance is None:
        from tools.rag_tool import RAGTool
        _rag_tool_instance = RAGTool()
    return _rag_tool_instance


# ============ RAG参数运行时管理器 ============

class RAGParamsManager:
    """
    RAG参数运行时管理器（单例）
    存储当前生效的RAG参数，支持动态修改
    """
    _instance = None
    _params = {
        "chunk_size": 400,
        "chunk_overlap": 50,
        "top_k": 5,
        "similarity_threshold": 0.3,
        "enable_cache": True,
        "enable_rerank": True,
        "enable_hybrid": True,  # 默认启用BM25混合检索
        "enable_self_rag": False
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_params(self) -> dict:
        """获取当前参数"""
        return self._params.copy()

    def update_params(self, params: dict):
        """更新参数"""
        self._params.update(params)
        print(f"[OK] RAG参数已更新: {self._params}")

    def get_chunk_size(self) -> int:
        return self._params["chunk_size"]

    def get_chunk_overlap(self) -> int:
        return self._params["chunk_overlap"]

    def get_top_k(self) -> int:
        return self._params["top_k"]

    def get_similarity_threshold(self) -> float:
        return self._params["similarity_threshold"]

    def get_enable_cache(self) -> bool:
        return self._params["enable_cache"]

    def get_enable_rerank(self) -> bool:
        return self._params["enable_rerank"]

    def get_enable_self_rag(self) -> bool:
        return self._params["enable_self_rag"]


# 全局RAG参数管理器
rag_params_manager = RAGParamsManager()


# ============ 响应模型 ============

class DocumentInfo(BaseModel):
    """文档信息"""
    id: str
    filename: str
    file_path: str
    file_type: str
    chunk_count: int
    size: int
    upload_time: str
    update_time: str


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    documents: List[DocumentInfo]
    total: int


class DocumentContentResponse(BaseModel):
    """文档内容响应"""
    id: str
    filename: str
    content: str
    chunks: List[dict]


class UpdateDocumentRequest(BaseModel):
    """更新文档请求"""
    content: str


class RAGParams(BaseModel):
    """RAG参数配置"""
    chunk_size: int = 400
    chunk_overlap: int = 50
    top_k: int = 5
    similarity_threshold: float = 0.3
    enable_cache: bool = True
    enable_rerank: bool = True
    enable_hybrid: bool = True  # 默认启用BM25混合检索
    enable_self_rag: bool = False


class RAGParamsResponse(BaseModel):
    """RAG参数响应"""
    params: RAGParams
    cache_stats: dict
    metrics: dict


# ============ 辅助函数 ============

def get_project_root():
    """获取项目根目录"""
    # 从 backend/app/api/v1/knowledge_base.py 向上5层到项目根目录
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

def get_docs_dir():
    """获取知识库目录"""
    project_root = get_project_root()
    docs_dir = os.path.join(project_root, 'data', 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    return docs_dir

def get_document_id_from_filename(filename: str, docs_dir: str) -> Optional[str]:
    """根据文件名获取文档ID"""
    if not os.path.exists(docs_dir):
        return None
    # 遍历查找匹配的文件
    for f in os.listdir(docs_dir):
        if f == filename:
            return f
    return None


# ============ API 路由 ============

@router.get("/knowledge-base", response_model=DocumentListResponse)
async def list_documents():
    """列出知识库中的所有文档"""
    docs_dir = get_docs_dir()

    all_files = sorted([f for f in os.listdir(docs_dir) if os.path.isfile(os.path.join(docs_dir, f))])

    documents = []
    
    chunk_counts = {}
    try:
        rag_tool = get_rag_tool()
        if rag_tool.collection and rag_tool._db_available:
            all_docs = rag_tool.collection.get(include=["metadatas"])
            if all_docs and all_docs.get("metadatas"):
                for metadata in all_docs["metadatas"]:
                    source = metadata.get("source_file") or metadata.get("file_path", "")
                    if source:
                        filename = os.path.basename(source)
                        chunk_counts[filename] = chunk_counts.get(filename, 0) + 1
    except Exception as e:
        print(f"[WARN] 获取chunk数量失败: {e}")
    
    for idx, filename in enumerate(all_files):
        file_path = os.path.join(docs_dir, filename)
        stat = os.stat(file_path)
        file_ext = os.path.splitext(filename)[1].lower()

        doc_id = str(idx + 1)

        documents.append(DocumentInfo(
            id=doc_id,
            filename=filename,
            file_path=file_path,
            file_type=file_ext,
            chunk_count=chunk_counts.get(filename, 0),
            size=stat.st_size,
            upload_time=datetime.fromtimestamp(stat.st_ctime).isoformat(),
            update_time=datetime.fromtimestamp(stat.st_mtime).isoformat()
        ))

    return DocumentListResponse(
        documents=documents,
        total=len(documents)
    )


@router.post("/knowledge-base/upload")
async def upload_document(
    file: UploadFile = File(...),
    chunk_size: int = Form(None),
    chunk_overlap: int = Form(None)
):
    """上传文档到知识库"""
    docs_dir = get_docs_dir()

    # 验证文件类型
    allowed_types = ['.txt', '.pdf', '.docx']
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型。支持的类型: {', '.join(allowed_types)}"
        )

    # 安全验证：文件名不能包含路径分隔符，防止路径遍历攻击
    if '/' in file.filename or '\\' in file.filename or '..' in file.filename:
        raise HTTPException(
            status_code=400,
            detail="文件名无效"
        )

    # 文件大小验证（限制 10MB）
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制（最大 {MAX_FILE_SIZE // (1024*1024)}MB）"
        )

    # 保存文件（使用安全的文件名）
    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join(docs_dir, safe_filename)

    # 如果文件已存在，先删除旧版本
    if os.path.exists(file_path):
        os.remove(file_path)

    with open(file_path, 'wb') as f:
        f.write(content)

    # 加载到向量数据库，使用运行时参数
    try:
        rag_tool = get_rag_tool()

        # 使用运行时参数（如果表单没有提供，使用默认值）
        actual_chunk_size = chunk_size if chunk_size is not None else rag_params_manager.get_chunk_size()
        actual_chunk_overlap = chunk_overlap if chunk_overlap is not None else rag_params_manager.get_chunk_overlap()

        # 删除该文件在向量库中的旧版本（防止重复积累）
        deleted_count = 0
        try:
            deleted_count = rag_tool.delete_documents_by_source(file_path)
            if deleted_count > 0:
                print(f"[INFO] 已删除旧版本文档块: {deleted_count} 个")
        except Exception as e:
            print(f"[WARN] 删除旧文档块失败: {e}")

        documents = rag_tool.load_document(file_path, actual_chunk_size, actual_chunk_overlap)
        doc_ids = rag_tool.add_documents_to_vector_db(documents)

        return {
            "success": True,
            "message": f"文档 '{safe_filename}' 上传成功 (chunk_size={actual_chunk_size}, overlap={actual_chunk_overlap})",
            "filename": safe_filename,
            "chunk_count": len(doc_ids),
            "chunk_size": actual_chunk_size,
            "chunk_overlap": actual_chunk_overlap,
            "file_size": len(content)
        }
    except Exception as e:
        # 删除上传的文件
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-base/params", response_model=RAGParamsResponse)
async def get_rag_params():
    """获取RAG参数配置"""
    from config.settings import settings

    # 优先使用运行时参数，否则使用配置文件默认值
    runtime_params = rag_params_manager.get_params()

    params = RAGParams(
        chunk_size=runtime_params["chunk_size"],
        chunk_overlap=runtime_params["chunk_overlap"],
        top_k=runtime_params["top_k"],
        similarity_threshold=runtime_params["similarity_threshold"],
        enable_cache=runtime_params["enable_cache"],
        enable_rerank=runtime_params["enable_rerank"],
        enable_self_rag=runtime_params["enable_self_rag"]
    )

    try:
        rag_tool = get_rag_tool()
        cache_stats = rag_tool.get_cache_stats()
        metrics = rag_tool.get_metrics()
    except:
        cache_stats = {}
        metrics = {}

    return RAGParamsResponse(
        params=params,
        cache_stats=cache_stats,
        metrics=metrics
    )


@router.post("/knowledge-base/params")
async def update_rag_params(params: RAGParams):
    """更新RAG参数配置"""
    # 更新运行时参数
    rag_params_manager.update_params(params.model_dump())

    try:
        rag_tool = get_rag_tool()

        # 1. 更新文本分割器参数（chunk_size, chunk_overlap）
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        rag_tool.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=params.chunk_size,
            chunk_overlap=params.chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", "，", "、"]
        )
        print(f"[OK] 文本分割器已更新: chunk_size={params.chunk_size}, overlap={params.chunk_overlap}")

        # 2. 更新缓存设置
        if params.enable_cache:
            if not hasattr(rag_tool, '_create_redis_cache'):
                rag_tool.cache = LocalCache(
                    max_size=1000,
                    default_ttl=3600
                )
            else:
                try:
                    rag_tool.cache = rag_tool._create_redis_cache()
                except:
                    rag_tool.cache = LocalCache(max_size=1000, default_ttl=3600)
        else:
            rag_tool.cache = LocalCache(max_size=1000, default_ttl=3600)

        print(f"[OK] 缓存设置已更新: enable_cache={params.enable_cache}")

        # 3. 更新Rerank开关
        if not params.enable_rerank and hasattr(rag_tool, 'reranker'):
            rag_tool.reranker = None
            print(f"[OK] Rerank已禁用")
        elif params.enable_rerank and (not hasattr(rag_tool, 'reranker') or rag_tool.reranker is None):
            from tools.rag_tool import Reranker
            rag_tool.reranker = Reranker()
            print(f"[OK] Rerank已启用")

    except Exception as e:
        print(f"[WARN] 更新RAGTool参数失败: {e}")
        import traceback
        traceback.print_exc()

    return {
        "success": True,
        "message": f"参数已更新并生效 (chunk_size={params.chunk_size}, top_k={params.top_k})",
        "params": params.model_dump()
    }


@router.post("/knowledge-base/reload")
async def reload_knowledge_base():
    """重新加载知识库（使用当前运行的参数）"""
    try:
        rag_tool = get_rag_tool()

        # 获取当前运行时参数
        runtime_params = rag_params_manager.get_params()
        chunk_size = runtime_params.get('chunk_size', 400)
        chunk_overlap = runtime_params.get('chunk_overlap', 50)
        print(f"[INFO] 使用运行时参数重新加载: chunk_size={chunk_size}, overlap={chunk_overlap}")

        # 彻底清空并重建集合
        if not rag_tool.clear_and_rebuild_collection():
            raise RuntimeError("清空重建集合失败")

        print(f"[INFO] 集合已清空重建，开始加载文档...")

        # 加载所有文档（使用当前参数）
        docs_dir = get_docs_dir()
        total_chunks = 0

        for filename in sorted(os.listdir(docs_dir)):
            file_path = os.path.join(docs_dir, filename)
            if os.path.isfile(file_path) and filename.endswith(('.txt', '.pdf', '.docx')):
                try:
                    documents = rag_tool.load_document(file_path, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
                    doc_ids = rag_tool.add_documents_to_vector_db(documents)
                    total_chunks += len(doc_ids)
                    current_count = rag_tool.collection.count()
                    print(f"[OK] {filename}: {len(doc_ids)} 块 (集合当前: {current_count})")
                except Exception as e:
                    print(f"[ERR] 加载 {filename} 失败: {e}")

        # 最终验证
        final_count = rag_tool.collection.count()
        print(f"[INFO] 知识库重载完成: 集合文档数={final_count}, 报告={total_chunks}")

        return {
            "success": True,
            "message": f"知识库已重新加载 (chunk_size={chunk_size}, overlap={chunk_overlap})",
            "total_chunks": total_chunks,
            "verified_chunks": final_count,
            "params_used": {
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-base/clear-cache")
async def clear_cache():
    """清除缓存"""
    try:
        rag_tool = get_rag_tool()
        rag_tool.clear_cache()
        return {
            "success": True,
            "message": "缓存已清除"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-base/cache/health")
async def cache_health():
    """缓存健康检查"""
    try:
        rag_tool = get_rag_tool()
        cache = rag_tool.cache

        # 判断缓存类型
        cache_type = "unknown"
        redis_available = False

        if hasattr(cache, '_available'):
            redis_available = cache._available
            cache_type = "redis" if redis_available else "memory"
        elif hasattr(cache, 'get_stats'):
            cache_type = "memory"

        # 获取缓存统计
        cache_stats = cache.get_stats() if hasattr(cache, 'get_stats') else {}

        # 获取 RAG 指标
        rag_metrics = rag_tool.metrics.get_summary() if hasattr(rag_tool, 'metrics') else {}

        return {
            "success": True,
            "cache_type": cache_type,
            "redis_available": redis_available,
            "cache_stats": cache_stats,
            "rag_metrics": rag_metrics
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "cache_type": "unknown",
            "redis_available": False
        }


@router.get("/knowledge-base/{document_id}")
async def get_document(document_id: str):
    """获取文档内容和元信息"""
    docs_dir = get_docs_dir()

    # 获取排序后的文件列表
    all_files = sorted([f for f in os.listdir(docs_dir) if os.path.isfile(os.path.join(docs_dir, f))])

    # 使用document_id作为索引（从1开始）
    try:
        idx = int(document_id) - 1
        if idx < 0 or idx >= len(all_files):
            raise HTTPException(status_code=404, detail="文档不存在")
        filename = all_files[idx]
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的文档ID")

    file_path = os.path.join(docs_dir, filename)

    # 读取文件内容
    try:
        if filename.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        elif filename.endswith('.pdf'):
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                content = "\n".join([page.extract_text() or "" for page in pdf.pages])
        elif filename.endswith('.docx'):
            import docx
            doc = docx.Document(file_path)
            content = "\n".join([para.text for para in doc.paragraphs])
        else:
            content = "不支持的文件类型"

        return DocumentContentResponse(
            id=document_id,
            filename=filename,
            content=content,
            chunks=[]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/knowledge-base/{document_id}")
async def update_document(document_id: str, request: UpdateDocumentRequest):
    """更新文档内容"""
    docs_dir = get_docs_dir()

    # 获取排序后的文件列表
    all_files = sorted([f for f in os.listdir(docs_dir) if os.path.isfile(os.path.join(docs_dir, f))])

    # 使用document_id作为索引
    try:
        idx = int(document_id) - 1
        if idx < 0 or idx >= len(all_files):
            raise HTTPException(status_code=404, detail="文档不存在")
        filename = all_files[idx]
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的文档ID")

    file_path = os.path.join(docs_dir, filename)

    try:
        # 更新文件内容
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(request.content)

        # 重新加载到向量数据库
        rag_tool = get_rag_tool()

        # 只删除该文件在向量库中的旧版本（不删除其他文件）
        deleted_count = 0
        try:
            deleted_count = rag_tool.delete_documents_by_source(file_path)
            if deleted_count > 0:
                print(f"[INFO] 已删除旧版本文档块: {deleted_count} 个")
        except Exception as e:
            print(f"[WARN] 删除旧文档块失败: {e}")

        # 重新加载
        documents = rag_tool.load_document(file_path)
        doc_ids = rag_tool.add_documents_to_vector_db(documents)

        return {
            "success": True,
            "message": f"文档 '{filename}' 更新成功",
            "chunk_count": len(doc_ids)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/knowledge-base/{document_id}")
async def delete_document(document_id: str):
    """删除文档"""
    docs_dir = get_docs_dir()

    # 获取排序后的文件列表
    all_files = sorted([f for f in os.listdir(docs_dir) if os.path.isfile(os.path.join(docs_dir, f))])

    # 使用document_id作为索引
    try:
        idx = int(document_id) - 1
        if idx < 0 or idx >= len(all_files):
            raise HTTPException(status_code=404, detail="文档不存在")
        filename = all_files[idx]
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的文档ID")

    file_path = os.path.join(docs_dir, filename)

    try:
        # 删除文件
        os.remove(file_path)

        # 只删除该文件在向量库中的旧版本
        rag_tool = get_rag_tool()
        deleted_count = 0
        try:
            deleted_count = rag_tool.delete_documents_by_source(file_path)
            if deleted_count > 0:
                print(f"[INFO] 已删除文档块: {deleted_count} 个")
        except Exception as e:
            print(f"[WARN] 删除文档块失败: {e}")

        return {
            "success": True,
            "message": f"文档 '{filename}' 已删除"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
