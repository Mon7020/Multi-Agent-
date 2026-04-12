"""
统一会话上下文管理器（线程安全版本）
打通 Agent Memory 和 Skill Context，实现会话状态的统一管理

线程安全设计：
1. SessionContextManager 使用 threading.Lock 保护 _sessions 字典
2. SessionContext 使用 threading.RLock 保护所有可变状态
"""

import threading
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

from core.logger import LoggerManager

logger = LoggerManager.get_logger("session_context")


@dataclass
class TurnRecord:
    """单轮对话记录"""
    role: str  # user / assistant
    content: str
    agent_name: Optional[str] = None  # 处理该轮对话的 Agent/Skill 名称
    intent: Optional[str] = None  # 识别到的意图
    rag_results: Optional[List[Dict]] = None  # RAG 检索结果
    evaluation_score: float = 0.0  # 该轮输出的评估分数
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class SessionContext:
    """
    统一会话上下文（线程安全版本）

    核心设计：
    - memory: LangChain ConversationBufferMemory，用于 LLM 对话上下文
    - skill_context: Skill 执行产生的业务上下文（客户类型、产品偏好等）
    - turn_history: 完整的对话轨迹，用于 evaluation 和追踪
    - metadata: 会话元数据（用户信息、session 创建时间等）

    线程安全：所有可变状态都通过 RLock 保护
    """

    def __init__(self, session_id: str, max_history: int = 50):
        self.session_id = session_id
        self.max_history = max_history
        self.created_at = datetime.now()

        # 线程锁 - 保护所有可变状态
        self._lock = threading.RLock()

        # LangChain Memory，用于 LLM 对话上下文
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            max_len=max_history
        )

        # Skill 执行产生的业务上下文
        # 结构: {skill_name: SkillResult.data}
        self.skill_context: Dict[str, Any] = {}

        # 客户元数据
        self.metadata: Dict[str, Any] = {
            "customer_type": None,  # rational / price_sensitive / difficult / hesitant / urgent
            "customer_name": None,
            "current_product": None,  # 当前讨论的产品
            "preference": None,  # 用户偏好
            "discount_level": 1,  # 当前谈判折扣层级
            "total_spent": 0.0,  # 累计消费（如果是回头客）
        }

        # 对话轨迹（用于 evaluation）
        self.turn_history: List[TurnRecord] = []

        # RAG 检索结果缓存（避免重复检索）
        self.rag_cache: Dict[str, Any] = {}

        logger.info(f"[SessionContext] 会话创建（线程安全）: {session_id}")

    def add_turn(
        self,
        role: str,
        content: str,
        agent_name: str = None,
        intent: str = None,
        rag_results: List[Dict] = None,
        evaluation_score: float = 0.0,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        添加一轮对话记录（线程安全）

        Args:
            role: user / assistant
            content: 对话内容
            agent_name: 处理该轮的 Agent/Skill 名称
            intent: 识别到的意图
            rag_results: RAG 检索结果
            evaluation_score: 输出质量评分
            metadata: 额外元数据
        """
        with self._lock:
            turn = TurnRecord(
                role=role,
                content=content,
                agent_name=agent_name,
                intent=intent,
                rag_results=rag_results,
                evaluation_score=evaluation_score,
                metadata=metadata or {}
            )
            self.turn_history.append(turn)

            # 更新 memory（供 LLM 使用）
            if role == "user":
                self.memory.chat_memory.add_user_message(content)
            else:
                self.memory.chat_memory.add_ai_message(content)

            # 维护大小限制
            if len(self.turn_history) > self.max_history * 2:
                self.turn_history = self.turn_history[-self.max_history:]

    def update_skill_context(
        self,
        skill_name: str,
        result_data: Any,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        更新 Skill 产生的业务上下文（线程安全）

        Args:
            skill_name: Skill 名称
            result_data: Skill 执行结果数据
            metadata: 额外元数据
        """
        with self._lock:
            self.skill_context[skill_name] = {
                "data": result_data,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }

            # 从 Skill 结果中提取关键信息到 metadata
            if skill_name == "customer_classifier" and isinstance(result_data, dict):
                if "customer_type" in result_data:
                    self.metadata["customer_type"] = result_data["customer_type"]
                if "strategy" in result_data:
                    self.metadata["service_strategy"] = result_data["strategy"]

            elif skill_name == "negotiation" and isinstance(result_data, dict):
                product_data = result_data.get("product", {})
                if "name" in product_data:
                    self.metadata["current_product"] = product_data["name"]
                if "discount_level" in result_data:
                    self.metadata["discount_level"] = result_data["discount_level"]

            logger.debug(f"[SessionContext] Skill上下文更新: {skill_name}")

    def get_skill_context(self, skill_name: str) -> Optional[Any]:
        """获取指定 Skill 的上下文（线程安全）"""
        with self._lock:
            return self.skill_context.get(skill_name)

    def get_unified_context(self) -> Dict[str, Any]:
        """
        获取统一的上下文字典（线程安全）

        用于：
        - 传递给 SkillManager.process()
        - 传递给 SupervisorAgent 做决策
        """
        with self._lock:
            return {
                "session_id": self.session_id,
                "memory": self.memory.load_memory_variables({}),
                "skill_context": dict(self.skill_context),  # 返回副本
                "metadata": dict(self.metadata),  # 返回副本
                "recent_history": [
                    {"role": t.role, "content": t.content}
                    for t in self.turn_history[-10:]
                ]
            }

    def get_context_for_skill(self, skill_name: str) -> Dict[str, Any]:
        """
        获取传递给特定 Skill 的上下文（线程安全）

        Args:
            skill_name: Skill 名称

        Returns:
            包含历史和 Skill 上下文的字典
        """
        with self._lock:
            unified = {
                "session_id": self.session_id,
                "memory": self.memory.load_memory_variables({}),
                "skill_context": dict(self.skill_context),
                "metadata": dict(self.metadata),
                "recent_history": [
                    {"role": t.role, "content": t.content}
                    for t in self.turn_history[-10:]
                ]
            }
            skill_context = unified.get("skill_context", {})

            # 添加历史（用于需要历史记录的 Skill）
            history = [
                {"role": t.role, "content": t.content}
                for t in self.turn_history[-6:]
            ]

            return {
                "query": unified["recent_history"][-1]["content"] if unified["recent_history"] else "",
                "history": history,
                "rag_results": self.rag_cache.get("recent_rag_results", []),
                "customer_type": self.metadata.get("customer_type"),
                "current_product": self.metadata.get("current_product"),
                "preference": self.metadata.get("preference"),
                "discount_level": self.metadata.get("discount_level", 1),
                **{f"{skill_name}_result": skill_context.get(skill_name)}
            }

    def update_rag_cache(self, query: str, results: List[Dict]) -> None:
        """更新 RAG 结果缓存（线程安全）"""
        with self._lock:
            self.rag_cache["last_query"] = query
            self.rag_cache["last_rag_results"] = results
            self.rag_cache["recent_rag_results"] = results

    def get_average_evaluation_score(self) -> float:
        """获取平均评估分数（线程安全）"""
        with self._lock:
            if not self.turn_history:
                return 0.0

            scores = [t.evaluation_score for t in self.turn_history if t.evaluation_score > 0]
            return sum(scores) / len(scores) if scores else 0.0

    def get_session_summary(self) -> Dict[str, Any]:
        """获取会话摘要（线程安全）"""
        with self._lock:
            total_turns = len(self.turn_history)
            user_turns = sum(1 for t in self.turn_history if t.role == "user")
            assistant_turns = total_turns - user_turns

            skills_used = list(set(
                t.agent_name for t in self.turn_history
                if t.agent_name and t.agent_name != "general"
            ))

            intents_detected = list(set(
                t.intent for t in self.turn_history
                if t.intent
            ))

            return {
                "session_id": self.session_id,
                "created_at": self.created_at.isoformat(),
                "duration_seconds": (datetime.now() - self.created_at).total_seconds(),
                "total_turns": total_turns,
                "user_turns": user_turns,
                "assistant_turns": assistant_turns,
                "skills_used": skills_used,
                "intents_detected": intents_detected,
                "customer_type": self.metadata.get("customer_type"),
                "current_product": self.metadata.get("current_product"),
                "avg_evaluation_score": round(self.get_average_evaluation_score(), 3),
                "metadata": dict(self.metadata)
            }

    def clear(self) -> None:
        """清空会话（线程安全）"""
        with self._lock:
            self.memory.clear()
            self.skill_context.clear()
            self.turn_history.clear()
            self.rag_cache.clear()
            self.metadata = {
                "customer_type": None,
                "customer_name": None,
                "current_product": None,
                "preference": None,
                "discount_level": 1,
                "total_spent": 0.0,
            }
            logger.info(f"[SessionContext] 会话已清空: {self.session_id}")


class SessionContextManager:
    """
    SessionContext 管理器（线程安全版本）

    负责创建、存储、检索会话上下文

    线程安全：
    - 使用 threading.Lock 保护 _sessions 字典的并发访问
    - 每个 SessionContext 内部使用 RLock 保护自己的状态
    """

    _instance = None
    _lock = threading.Lock()  # 类级别的锁，保护单例创建

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        # 双重检查锁定已经在 __new__ 中处理
        with self._lock:
            if self._initialized:
                return
            self._initialized = True
            # 实例级别的锁，保护 _sessions 字典
            self._sessions_lock = threading.Lock()
            self._sessions: Dict[str, SessionContext] = {}
            logger.info("[SessionContextManager] 初始化完成（线程安全）")

    def create_session(self, session_id: str, max_history: int = 50) -> SessionContext:
        """
        创建或获取会话（线程安全）

        Args:
            session_id: 会话 ID
            max_history: 最大历史记录数

        Returns:
            SessionContext 实例
        """
        with self._sessions_lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionContext(session_id, max_history)
                logger.info(f"[SessionContextManager] 创建新会话: {session_id}")
            return self._sessions[session_id]

    def get_session(self, session_id: str) -> Optional[SessionContext]:
        """获取已有会话（线程安全）"""
        with self._sessions_lock:
            return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """删除会话（线程安全）"""
        with self._sessions_lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info(f"[SessionContextManager] 删除会话: {session_id}")
                return True
            return False

    def list_sessions(self) -> List[str]:
        """列出所有会话 ID（线程安全）"""
        with self._sessions_lock:
            return list(self._sessions.keys())

    def get_all_sessions_summary(self) -> List[Dict[str, Any]]:
        """获取所有会话摘要（线程安全）"""
        with self._sessions_lock:
            return [
                session.get_session_summary()
                for session in self._sessions.values()
            ]


# 全局单例
session_context_manager = SessionContextManager()
