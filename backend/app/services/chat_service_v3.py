"""ChatService V3: session context + context/RAG fusion orchestration."""

import asyncio
import os
import sys
import threading
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from agents.supervisor_agent import SupervisorAgent
from app.config import settings
from app.services.rag_runtime import get_rag_tool, rag_params_manager
from core.session_context import SessionContext, SessionContextManager
from langchain_openai import ChatOpenAI
from tools.rag.context_rag_fusion import RetrievalQuality, context_rag_fusion_layer


class ChatServiceV3:
    """Main chat service for backend API."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.session_manager = SessionContextManager()
        self.supervisor = SupervisorAgent()

        self.rag_tool = None
        self._docs_loaded = False
        self._docs_load_lock = threading.Lock()
        self._init_rag_tool()

        self.fusion_layer = context_rag_fusion_layer

        self.llm = ChatOpenAI(
            api_key=settings.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY", ""),
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
            temperature=0.1,
            streaming=False,
        )

        self.greeting_message = self._load_greeting_message()

    def _load_greeting_message(self) -> str:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        greeting_path = os.path.join(project_root, "data", "docs", "招呼消息.txt")
        try:
            with open(greeting_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return "您好！我是智能客服，有什么可以帮您的吗？"

    def _init_rag_tool(self):
        try:
            self.rag_tool = get_rag_tool()
            print("[OK] RAG tool initialized")
        except Exception as e:
            print(f"[WARN] failed to initialize RAG tool: {e}")
            self.rag_tool = None

    def _ensure_documents_loaded(self):
        if self._docs_loaded:
            return
        with self._docs_load_lock:
            if self._docs_loaded:
                return
            self._load_documents()
            self._docs_loaded = True

    async def _ensure_documents_loaded_async(self):
        if self._docs_loaded:
            return
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._ensure_documents_loaded)

    def _load_documents(self):
        if not self.rag_tool:
            return

        try:
            docs_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                "data",
                "docs",
            )
            if not os.path.exists(docs_dir):
                return

            loaded_count = 0
            for filename in sorted(os.listdir(docs_dir)):
                if not filename.endswith((".txt", ".pdf", ".docx")):
                    continue

                file_path = os.path.join(docs_dir, filename)
                try:
                    # Avoid duplicate chunks across restarts by replacing existing chunks per source file.
                    try:
                        self.rag_tool.delete_documents_by_source(file_path)
                    except Exception as cleanup_error:
                        print(f"[WARN] failed to cleanup old chunks for {filename}: {cleanup_error}")

                    documents = self.rag_tool.load_document(file_path)
                    if documents:
                        self.rag_tool.add_documents_to_vector_db(documents)
                        loaded_count += len(documents)
                except Exception as e:
                    print(f"[WARN] failed to load doc {filename}: {e}")

            if loaded_count > 0:
                print(f"[OK] loaded {loaded_count} chunks into vector store")
        except Exception as e:
            print(f"[WARN] failed to preload docs: {e}")

    @staticmethod
    def _validate_session_access(context: Optional[SessionContext], user_id: str):
        if not user_id:
            raise ValueError("user_id is required")
        if context is not None and context.user_id != user_id:
            raise PermissionError("session access denied for current user")

    async def process_message(
        self,
        session_id: str,
        message: str,
        history: List[Dict[str, str]] = None,
        enable_context_rag_fusion: bool = True,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            self._validate_session_access(None, user_id or "")
            await self._ensure_documents_loaded_async()

            context = self.session_manager.get_session(session_id, user_id=user_id)
            self._validate_session_access(context, user_id or "")

            is_new_session = False
            if context is None:
                context = self.session_manager.create_session(session_id=session_id, user_id=user_id)
                is_new_session = True

            if history:
                self._sync_history_to_context(context, history, message)

            if enable_context_rag_fusion:
                fusion_result = await self._process_with_fusion(context, message)
                rag_result = {
                    "success": True,
                    "documents": fusion_result.metadata.get("retrieval_result", {}).get("documents", []),
                    "has_relevant_info": fusion_result.quality != RetrievalQuality.NONE,
                }
            else:
                rag_result = await self._retrieve_with_rag(message, context)
                fusion_result = None

            if rag_result.get("documents"):
                context.update_rag_cache(message, rag_result["documents"])
                context.update_skill_context(
                    "rag",
                    {
                        "documents": rag_result["documents"],
                        "has_relevant_info": rag_result.get("has_relevant_info", False),
                        "query": message,
                    },
                )

            result = await self.supervisor.process(message, context)

            context.add_turn(
                role="assistant",
                content=result.get("message", ""),
                agent_name="supervisor",
                intent=result.get("intent"),
                rag_results=rag_result.get("documents", []),
                evaluation_score=result.get("evaluation_score", 0.0),
                metadata={
                    "confidence": result.get("intent_confidence", result.get("confidence", 0.0)),
                    "entities": fusion_result.metadata.get("entities", []) if fusion_result else [],
                    "fusion_quality": fusion_result.quality.value if fusion_result else None,
                },
            )

            try:
                context.persist_long_term_memory()
            except Exception as persist_error:
                print(f"[WARN] failed to persist long-term memory: {persist_error}")

            return {
                "session_id": session_id,
                "message": result.get("message", ""),
                "intent": result.get("intent"),
                "confidence": result.get("intent_confidence", result.get("confidence")),
                "customer_type": context.metadata.get("customer_type"),
                "skills_used": result.get("skills_used", []),
                "sources": result.get("sources", []),
                "timestamp": datetime.now(),
                "greeting": self.greeting_message if is_new_session else None,
                "retrieved_documents": rag_result.get("documents", []),
                "retrieved_count": len(rag_result.get("documents", [])),
                "has_relevant_info": rag_result.get("has_relevant_info", False),
                "context_summary": self._get_context_summary(context),
                "fusion_info": {
                    "enabled": enable_context_rag_fusion,
                    "quality": fusion_result.quality.value if fusion_result else "N/A",
                    "strategy": fusion_result.fusion_strategy.value if fusion_result else "N/A",
                    "confidence": fusion_result.confidence if fusion_result else 0.0,
                    "context_strength": fusion_result.metadata.get("context_strength", 0) if fusion_result else 0,
                }
                if fusion_result
                else None,
            }

        except (PermissionError, ValueError):
            raise
        except Exception as e:
            import traceback

            print(f"[ERR] process_message failed: {e}")
            traceback.print_exc()
            return {
                "session_id": session_id,
                "message": f"抱歉，处理请求失败: {str(e)}",
                "intent": "error",
                "confidence": 0.0,
                "customer_type": None,
                "skills_used": [],
                "sources": [],
                "timestamp": datetime.now(),
                "retrieved_documents": [],
                "retrieved_count": 0,
                "has_relevant_info": False,
            }

    async def stream_process_message(
        self,
        session_id: str,
        message: str,
        history: List[Dict[str, str]] = None,
        chunk_size: int = 40,
        user_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        result = await self.process_message(
            session_id=session_id,
            message=message,
            history=history,
            user_id=user_id,
        )

        full_message = result.get("message", "") or ""
        step = max(1, chunk_size)
        for i in range(0, len(full_message), step):
            yield {"content": full_message[i : i + step], "done": False}

        yield {
            "content": "",
            "done": True,
            "meta": {
                "intent": result.get("intent"),
                "customer_type": result.get("customer_type"),
                "greeting": result.get("greeting"),
                "skills_used": result.get("skills_used", []),
            },
        }

    async def _process_with_fusion(self, context: SessionContext, message: str) -> Any:
        def rag_retrieval_func(query: str, metadata_hints: Dict[str, Any] = None) -> Dict[str, Any]:
            _ = metadata_hints
            try:
                if not self.rag_tool:
                    return {"documents": [], "success": False}

                chat_history = [{"role": t.role, "content": t.content} for t in context.turn_history[-6:]]
                runtime_params = rag_params_manager.get_params()
                return self.rag_tool.retrieve(
                    query=query,
                    top_k=runtime_params.get("top_k", 5),
                    enable_self_rag=True,
                    llm=self.llm,
                    use_cache=True,
                    use_hybrid=runtime_params.get("enable_hybrid", True),
                    use_rerank=runtime_params.get("enable_rerank", True),
                    chat_history=chat_history,
                )
            except Exception as e:
                print(f"[ERR] RAG retrieval failed: {e}")
                return {"documents": [], "success": False}

        intent = self._infer_intent_from_context(context)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.fusion_layer.process(
                query=message,
                session_context=context,
                rag_retrieval_func=rag_retrieval_func,
                intent=intent,
            ),
        )

    def _infer_intent_from_context(self, context: SessionContext) -> str:
        for turn in reversed(context.turn_history[-6:]):
            if turn.intent and turn.intent != "general":
                return turn.intent
        if context.metadata.get("current_product"):
            return "sales"
        return "general"

    async def _retrieve_with_rag(self, query: str, context: SessionContext) -> Dict[str, Any]:
        if not self.rag_tool:
            return {"success": False, "documents": [], "has_relevant_info": False}

        try:
            chat_history = [{"role": t.role, "content": t.content} for t in context.turn_history[-6:]]
            runtime_params = rag_params_manager.get_params()

            loop = asyncio.get_running_loop()
            retrieval_result = await loop.run_in_executor(
                None,
                lambda: self.rag_tool.retrieve(
                    query=query,
                    top_k=runtime_params.get("top_k", 5),
                    enable_self_rag=True,
                    llm=self.llm,
                    use_cache=True,
                    use_hybrid=runtime_params.get("enable_hybrid", True),
                    use_rerank=runtime_params.get("enable_rerank", True),
                    chat_history=chat_history,
                ),
            )

            documents = retrieval_result.get("documents", [])
            return {
                "success": retrieval_result.get("success", False),
                "documents": documents,
                "has_relevant_info": bool(documents),
                "enhanced_query": retrieval_result.get("contextualized_query"),
            }
        except Exception as e:
            print(f"[ERR] RAG retrieval failed: {e}")
            return {"success": False, "documents": [], "has_relevant_info": False}

    def _sync_history_to_context(
        self,
        context: SessionContext,
        history: List[Dict[str, str]],
        current_message: str = None,
    ):
        if len(context.turn_history) != 0 or not history:
            return

        history_to_sync = history
        if current_message and history and history[-1].get("role") == "user" and history[-1].get("content") == current_message:
            history_to_sync = history[:-1]

        for msg in history_to_sync:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ["user", "assistant"]:
                context.add_turn(role=role, content=content, agent_name="history_sync")

    def _get_context_summary(self, context: SessionContext) -> Dict[str, Any]:
        three_tier = context.get_three_tier_context() if hasattr(context, "get_three_tier_context") else {}
        return {
            "session_id": context.session_id,
            "turn_count": len(context.turn_history),
            "customer_type": context.metadata.get("customer_type"),
            "current_product": context.metadata.get("current_product"),
            "skills_used": list(
                {
                    t.agent_name
                    for t in context.turn_history
                    if t.agent_name and t.agent_name != "history_sync"
                }
            ),
            "intents": list({t.intent for t in context.turn_history if t.intent}),
            "context_strength": self._calculate_context_strength(context),
            "three_tier_stats": three_tier.get("stats", {}),
            "medium_term_summary": three_tier.get("medium_term_summary", ""),
            "long_term_context": three_tier.get("long_term_text", ""),
        }

    def _calculate_context_strength(self, context: SessionContext) -> float:
        score = 0.0

        if hasattr(context, "get_three_tier_context"):
            tier_context = context.get_three_tier_context()
            stats = tier_context.get("stats", {})
            if stats.get("short_term_turns", 0) > 3:
                score += 0.3
            if stats.get("compressed_memories", 0) > 0:
                score += 0.2
            if tier_context.get("long_term_text"):
                score += 0.2
            if tier_context.get("intent_continuity"):
                score += 0.1

        if len(context.turn_history) > 3:
            score += 0.3
        if context.metadata.get("customer_type"):
            score += 0.2
        if context.metadata.get("current_product"):
            score += 0.2
        if context.skill_context:
            score += 0.2
        if len(context.turn_history) > 10:
            score += 0.1

        return min(score, 1.0)

    def get_session_history(self, session_id: str, user_id: Optional[str] = None) -> List[Dict[str, str]]:
        context = self.session_manager.get_session(session_id, user_id=user_id)
        if context is None:
            return []
        if not user_id:
            raise ValueError("user_id is required")
        if context.user_id != user_id:
            raise PermissionError("session access denied for current user")
        return [{"role": t.role, "content": t.content} for t in context.turn_history]

    def clear_session(self, session_id: str, user_id: Optional[str] = None) -> bool:
        context = self.session_manager.get_session(session_id, user_id=user_id)
        if not user_id:
            raise ValueError("user_id is required")
        if context and context.user_id != user_id:
            raise PermissionError("session access denied for current user")
        return self.session_manager.delete_session(session_id, user_id=user_id, remove_persisted=True)

    def get_fusion_stats(self) -> Dict[str, Any]:
        return {
            "fusion_layer": "ContextRAGFusionLayer",
            "capabilities": [
                "Context-to-RAG",
                "RAG-to-Context",
                "Adaptive Fusion",
                "Quality Assessment",
            ],
            "fusion_strategies": {
                "RAG_PRIMARY": "Prefer RAG for high-quality retrieval",
                "CONTEXT_PRIMARY": "Prefer context for weak retrieval",
                "HYBRID": "Blend retrieval and context",
                "CONTEXT_ONLY": "Use only context for simple dialog",
            },
        }


_chat_service_v3_instance: Optional[ChatServiceV3] = None
_chat_service_v3_lock = threading.Lock()


def get_chat_service_v3() -> ChatServiceV3:
    global _chat_service_v3_instance
    with _chat_service_v3_lock:
        if _chat_service_v3_instance is None:
            _chat_service_v3_instance = ChatServiceV3()
    return _chat_service_v3_instance


class _LazyChatServiceV3Proxy:
    def __getattr__(self, item):
        return getattr(get_chat_service_v3(), item)


chat_service_v3 = _LazyChatServiceV3Proxy()
