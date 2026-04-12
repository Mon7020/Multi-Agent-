"""
聊天服务 V3 - Context+RAG融合版
在V2基础上，深度集成Context+RAG融合层，实现双向信息流

核心改进：
1. Context → RAG: 利用SessionContext优化RAG检索策略
2. RAG → Context: 将RAG结果智能注入三层记忆
3. 自适应融合: 根据检索质量动态调整生成策略
"""

import sys
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from app.config import settings

from core.session_context import SessionContext, SessionContextManager
from agents.supervisor_agent import SupervisorAgent

from app.api.v1.knowledge_base import get_rag_tool

from langchain_openai import ChatOpenAI

from tools.rag.context_rag_fusion import (
    context_rag_fusion_layer,
    ContextRAGFusionLayer,
    RetrievalQuality,
    FusionStrategy
)

from tools.amap_weather_tool import weather_tool
from tools.tavily_search_tool import search_tool


class ChatServiceV3:
    """
    聊天服务 V3 - Context+RAG融合版

    核心流程（相比V2的改进）：
    1. Context提取 → ContextRAGFusionLayer处理
    2. 使用融合层的增强查询执行RAG检索
    3. RAG结果注入 → 自动更新metadata和skill_context
    4. 自适应融合 → 根据质量选择最佳融合策略
    5. 构建融合上下文 → 传递给SupervisorAgent
    """

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
        self._init_rag_tool()

        self.fusion_layer = context_rag_fusion_layer

        self.llm = ChatOpenAI(
            api_key=settings.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY", ""),
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
            temperature=0.1,
            streaming=False
        )

        self.greeting_message = self._load_greeting_message()

    def _load_greeting_message(self) -> str:
        """加载招呼消息"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        greeting_path = os.path.join(project_root, 'data', 'docs', '招呼消息.txt')
        try:
            with open(greeting_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            print(f"[WARN] 加载招呼消息失败: {e}")
            return "您好！我是智能客服，有什么可以帮您的吗？"

        print("[OK] ChatServiceV3 初始化完成 (Context+RAG融合版)")

    def _init_rag_tool(self):
        """初始化RAG工具"""
        try:
            self.rag_tool = get_rag_tool()
            self._load_documents()
            print("[OK] RAG工具初始化完成")
        except Exception as e:
            print(f"[WARN] RAG工具初始化失败: {e}")
            self.rag_tool = None

    def _load_documents(self):
        """加载知识库文档"""
        if not self.rag_tool:
            return

        try:
            docs_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                'data', 'docs'
            )

            if not os.path.exists(docs_dir):
                print(f"[WARN] 知识库目录不存在: {docs_dir}")
                return

            loaded_count = 0
            for filename in os.listdir(docs_dir):
                if filename.endswith(('.txt', '.pdf', '.docx')):
                    file_path = os.path.join(docs_dir, filename)
                    print(f"[DOC] 正在加载文档: {filename}")
                    try:
                        documents = self.rag_tool.load_document(file_path)
                        if documents:
                            self.rag_tool.add_documents_to_vector_db(documents)
                            loaded_count += len(documents)
                            print(f"   [OK] 已加载 {len(documents)} 个文档块")
                    except Exception as e:
                        print(f"   [ERR] 加载失败: {str(e)}")

            if loaded_count > 0:
                print(f"[OK] 知识库加载完成，共 {loaded_count} 个文档块")
            else:
                print("[WARN] 知识库为空")

        except Exception as e:
            print(f"[WARN] 加载知识库时出错: {str(e)}")

    async def process_message(
        self,
        session_id: str,
        message: str,
        history: List[Dict[str, str]] = None,
        enable_context_rag_fusion: bool = True
    ) -> Dict[str, Any]:
        """
        处理消息 - Context+RAG融合

        Args:
            session_id: 会话ID
            message: 用户消息
            history: 可选的外部历史记录
            enable_context_rag_fusion: 是否启用Context+RAG融合（默认启用）

        Returns:
            处理结果
        """
        try:
            context = self.session_manager.get_session(session_id)

            is_new_session = False
            if context is None:
                context = self.session_manager.create_session(session_id)
                is_new_session = True
                print(f"[Session] 创建新会话: {session_id}")
            else:
                print(f"[Session] 复用已有会话: {session_id}, 历史: {len(context.turn_history)} 条")

            if history and len(history) > 0:
                self._sync_history_to_context(context, history, message)

            if enable_context_rag_fusion:
                fusion_result = await self._process_with_fusion(context, message)
                rag_result = {
                    "success": True,
                    "documents": fusion_result.metadata.get("retrieval_result", {}).get("documents", []),
                    "has_relevant_info": fusion_result.quality != RetrievalQuality.NONE
                }
            else:
                rag_result = await self._retrieve_with_rag(message, context)
                fusion_result = None

            if rag_result.get("documents"):
                context.update_rag_cache(message, rag_result["documents"])

            if rag_result.get("documents"):
                context.update_skill_context("rag", {
                    "documents": rag_result["documents"],
                    "has_relevant_info": rag_result.get("has_relevant_info", False),
                    "query": message
                })

            result = await self.supervisor.process(message, context)

            context.add_turn(
                role="assistant",
                content=result.get("message", ""),
                agent_name="supervisor",
                intent=result.get("intent"),
                evaluation_score=result.get("evaluation_score", 0.0)
            )

            response_data = {
                "session_id": session_id,
                "message": result.get("message", ""),
                "intent": result.get("intent"),
                "confidence": result.get("confidence"),
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
                    "context_strength": fusion_result.metadata.get("context_strength", 0) if fusion_result else 0
                } if fusion_result else None
            }

            print(f"\n[响应] 会话ID: {session_id}")
            print(f"   意图: {result.get('intent')} (置信度: {result.get('confidence', 0):.2f})")
            print(f"   客户类型: {context.metadata.get('customer_type')}")
            print(f"   Skills: {result.get('skills_used', [])}")
            print(f"   检索文档数: {len(rag_result.get('documents', []))}")
            if fusion_result:
                print(f"   融合质量: {fusion_result.quality.value}")
                print(f"   融合策略: {fusion_result.fusion_strategy.value}")
                print(f"   上下文强度: {fusion_result.metadata.get('context_strength', 0):.2f}")

            return response_data

        except Exception as e:
            print(f"[ERR] 处理消息失败: {e}")
            import traceback
            traceback.print_exc()

            return {
                "session_id": session_id,
                "message": f"抱歉，处理您的请求时出现错误：{str(e)}",
                "intent": "error",
                "confidence": 0.0,
                "customer_type": None,
                "skills_used": [],
                "sources": [],
                "timestamp": datetime.now(),
                "retrieved_documents": [],
                "retrieved_count": 0,
                "has_relevant_info": False
            }

    async def _process_with_fusion(
        self,
        context: SessionContext,
        message: str
    ) -> Any:
        """
        使用Context+RAG融合层处理

        Args:
            context: 会话上下文
            message: 用户消息

        Returns:
            FusionResult
        """
        print(f"\n{'='*60}")
        print(f"[FUSION] 开始Context+RAG融合处理")
        print(f"{'='*60}")

        def rag_retrieval_func(query: str, metadata_hints: Dict[str, Any] = None) -> Dict[str, Any]:
            """RAG检索函数（供融合层调用）"""
            try:
                chat_history = [
                    {"role": t.role, "content": t.content}
                    for t in context.turn_history[-6:]
                ]

                from app.api.v1.knowledge_base import rag_params_manager
                runtime_params = rag_params_manager.get_params()

                result = self.rag_tool.retrieve(
                    query=query,
                    top_k=runtime_params.get('top_k', 5),
                    enable_self_rag=True,  # 启用 Self-RAG
                    llm=self.llm,
                    use_cache=True,
                    use_hybrid=runtime_params.get('enable_hybrid', True),
                    use_rerank=runtime_params.get('enable_rerank', True),
                    chat_history=chat_history
                )

                return result
            except Exception as e:
                print(f"[ERR] RAG检索失败: {e}")
                return {"documents": [], "success": False}

        intent = self._infer_intent_from_context(context)

        fusion_result = self.fusion_layer.process(
            query=message,
            session_context=context,
            rag_retrieval_func=rag_retrieval_func,
            intent=intent
        )

        print(f"\n[FUSION] 融合结果摘要:")
        print(f"   检索质量: {fusion_result.quality.value}")
        print(f"   融合策略: {fusion_result.fusion_strategy.value}")
        print(f"   置信度: {fusion_result.confidence:.2f}")
        print(f"   数据源: {', '.join(fusion_result.used_sources)}")
        print(f"   处理时间: {fusion_result.metadata.get('total_process_time', 0):.3f}s")
        print(f"   提取实体: {fusion_result.metadata.get('entities', [])}")

        fusion_result.metadata["retrieval_result"] = {
            "documents": []
        }

        return fusion_result

    def _infer_intent_from_context(self, context: SessionContext) -> str:
        """从上下文推断意图"""
        recent_turns = [
            {"role": t.role, "content": t.content, "intent": t.intent}
            for t in context.turn_history[-6:]
        ]

        for turn in reversed(recent_turns):
            if turn.get("intent") and turn["intent"] != "general":
                return turn["intent"]

        metadata = context.metadata
        if metadata.get("current_product"):
            return "sales"

        return "general"

    async def _retrieve_with_rag(
        self,
        query: str,
        context: SessionContext
    ) -> Dict[str, Any]:
        """标准RAG检索（未使用融合层）"""
        if not self.rag_tool:
            return {"success": False, "documents": [], "has_relevant_info": False}

        try:
            chat_history = [
                {"role": t.role, "content": t.content}
                for t in context.turn_history[-6:]
            ]

            from app.api.v1.knowledge_base import rag_params_manager
            runtime_params = rag_params_manager.get_params()

            loop = asyncio.get_event_loop()
            retrieval_result = await loop.run_in_executor(
                None,
                lambda: self.rag_tool.retrieve(
                    query=query,
                    top_k=runtime_params.get('top_k', 5),
                    enable_self_rag=True,  # 启用 Self-RAG
                    llm=self.llm,
                    use_cache=True,
                    use_hybrid=runtime_params.get('enable_hybrid', True),
                    use_rerank=runtime_params.get('enable_rerank', True),
                    chat_history=chat_history
                )
            )

            documents = retrieval_result.get("documents", [])
            has_relevant_info = len(documents) > 0

            return {
                "success": retrieval_result.get("success", False),
                "documents": documents,
                "has_relevant_info": has_relevant_info,
                "enhanced_query": retrieval_result.get("contextualized_query")
            }

        except Exception as e:
            print(f"[ERR] RAG检索失败: {e}")
            return {"success": False, "documents": [], "has_relevant_info": False}

    def _sync_history_to_context(
        self,
        context: SessionContext,
        history: List[Dict[str, str]],
        current_message: str = None
    ):
        """将外部历史同步到SessionContext"""
        existing_history_len = len(context.turn_history)

        if existing_history_len == 0 and len(history) > 0:
            if current_message and len(history) > 0:
                last_msg = history[-1]
                if (last_msg.get("role") == "user" and
                    last_msg.get("content") == current_message):
                    history_to_sync = history[:-1]
                else:
                    history_to_sync = history
            else:
                history_to_sync = history

            if len(history_to_sync) > 0:
                for msg in history_to_sync:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role in ["user", "assistant"]:
                        context.add_turn(
                            role=role,
                            content=content,
                            agent_name="history_sync"
                        )
                print(f"[Session] 从外部同步 {len(history_to_sync)} 条历史记录")

    def _get_context_summary(self, context: SessionContext) -> Dict[str, Any]:
        """获取上下文摘要"""
        return {
            "session_id": context.session_id,
            "turn_count": len(context.turn_history),
            "customer_type": context.metadata.get("customer_type"),
            "current_product": context.metadata.get("current_product"),
            "skills_used": list(set(
                t.agent_name for t in context.turn_history
                if t.agent_name and t.agent_name != "history_sync"
            )),
            "intents": list(set(
                t.intent for t in context.turn_history
                if t.intent
            )),
            "context_strength": self._calculate_context_strength(context)
        }

    def _calculate_context_strength(self, context: SessionContext) -> float:
        """计算上下文强度"""
        score = 0.0

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

    def get_session_history(self, session_id: str) -> List[Dict[str, str]]:
        """获取会话历史"""
        context = self.session_manager.get_session(session_id)
        if context is None:
            return []

        return [
            {"role": t.role, "content": t.content}
            for t in context.turn_history
        ]

    def clear_session(self, session_id: str) -> bool:
        """清除会话"""
        try:
            self.session_manager.delete_session(session_id)
            print(f"[Session] 会话已清除: {session_id}")
            return True
        except Exception as e:
            print(f"[ERR] 清除会话失败: {e}")
            return False

    def get_fusion_stats(self) -> Dict[str, Any]:
        """获取融合统计信息"""
        return {
            "fusion_layer": "ContextRAGFusionLayer",
            "capabilities": [
                "Context-to-RAG: 利用元数据和Skill上下文优化检索",
                "RAG-to-Context: 智能注入RAG结果到上下文",
                "Adaptive Fusion: 根据检索质量自适应选择融合策略",
                "Quality Assessment: 自动评估检索结果质量"
            ],
            "fusion_strategies": {
                "RAG_PRIMARY": "当检索质量高且上下文弱时使用",
                "CONTEXT_PRIMARY": "当检索质量低时使用",
                "HYBRID": "当检索质量和上下文都较好时使用",
                "CONTEXT_ONLY": "简单对话（问候/告别）时使用"
            }
        }


chat_service_v3 = ChatServiceV3()
