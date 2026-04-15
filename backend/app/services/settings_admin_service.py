from __future__ import annotations

from typing import Dict, Optional

from app.services.audit_log_service import AuditLogService
from app.services.rag_runtime import get_loaded_rag_tool, rag_params_manager


class SettingsAdminService:
    def __init__(self) -> None:
        self.audit_log_service = AuditLogService()

    @staticmethod
    def _permission_model() -> Dict[str, Dict[str, object]]:
        return {
            "roles": {
                "super_admin": {
                    "label": "超级管理员",
                    "capabilities": ["全部后台模块", "角色与权限策略", "系统安全配置", "知识库发布控制"],
                },
                "admin": {
                    "label": "管理员",
                    "capabilities": ["记忆管理", "知识库显隐与发布", "系统设置", "账号管理"],
                },
                "operator": {
                    "label": "运营",
                    "capabilities": ["查看后台总览", "记忆管理", "查看知识库模块"],
                },
                "user": {
                    "label": "前台用户",
                    "capabilities": ["对话", "只读知识库", "只读设置摘要"],
                },
            }
        }

    def get_summary(self) -> Dict[str, object]:
        return {
            "runtime_params": rag_params_manager.get_params(),
            "permission_model": self._permission_model(),
            "frontend_policy": {
                "knowledge_base": "前台仅展示已发布且允许当前角色访问的文档，不提供编辑能力。",
                "settings": "前台只保留只读摘要，运行参数和权限策略统一在后台维护。",
            },
        }

    def update_runtime_params(self, params: Dict[str, object], actor_id: Optional[str] = None) -> Dict[str, object]:
        rag_params_manager.update_params(params)

        try:
            rag_tool = get_loaded_rag_tool()
            if rag_tool is None:
                raise RuntimeError("rag tool not loaded")

            from langchain_text_splitters import RecursiveCharacterTextSplitter
            from tools.rag_tool import LocalCache

            rag_tool.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=int(params["chunk_size"]),
                chunk_overlap=int(params["chunk_overlap"]),
                separators=["\n\n", "\n", ".", "?", "!", ",", "。", "？", "！", "，"],
            )

            if params.get("enable_cache"):
                if hasattr(rag_tool, "_create_redis_cache"):
                    try:
                        rag_tool.cache = rag_tool._create_redis_cache()
                    except Exception:
                        rag_tool.cache = LocalCache(max_size=1000, default_ttl=3600)
                else:
                    rag_tool.cache = LocalCache(max_size=1000, default_ttl=3600)
            else:
                rag_tool.cache = LocalCache(max_size=1000, default_ttl=3600)

            if not params.get("enable_rerank") and hasattr(rag_tool, "reranker"):
                rag_tool.reranker = None
            elif params.get("enable_rerank") and getattr(rag_tool, "reranker", None) is None:
                from tools.rag_tool import Reranker

                rag_tool.reranker = Reranker()
        except Exception as exc:
            print(f"[WARN] failed to apply runtime params into rag tool: {exc}")

        if actor_id:
            self.audit_log_service.write(
                actor_id=actor_id,
                module="settings",
                action="update_runtime",
                target_type="rag_params",
                target_id="runtime",
                result="success",
                extra={"chunk_size": params.get("chunk_size"), "top_k": params.get("top_k")},
            )

        return rag_params_manager.get_params()


settings_admin_service = SettingsAdminService()
