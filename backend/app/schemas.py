"""
Pydantic 模型定义
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ChatMessage(BaseModel):
    role: str = Field(..., description="角色: user/assistant/system")
    content: str = Field(..., description="消息内容")
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="会话ID")
    message: str = Field(..., description="用户消息")
    history: Optional[List[ChatMessage]] = Field(default=[], description="对话历史")


class ChatResponse(BaseModel):
    session_id: str
    message: str
    customer_type: Optional[str] = None
    skills_used: List[str] = []
    sources: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.now)
    intent: Optional[str] = None
    evaluation_score: Optional[float] = None
    retrieved_documents: List[Dict[str, Any]] = Field(default_factory=list)
    retrieved_count: int = 0
    has_relevant_info: bool = False
    context_summary: Optional[Dict[str, Any]] = None
    fusion_info: Optional[Dict[str, Any]] = Field(default=None, description="Context+RAG融合信息")
    greeting: Optional[str] = Field(default=None, description="新会话招呼消息")


class SkillInfo(BaseModel):
    name: str
    description: str
    skill_type: str
    enabled: bool


class SkillsListResponse(BaseModel):
    skills: List[SkillInfo]
    count: int


class HistoryResponse(BaseModel):
    session_id: str
    messages: List[ChatMessage]
    count: int


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime


# ============ Evaluation Schemas ============

class EvaluationRequest(BaseModel):
    session_id: str = Field(..., description="会话ID")
    query: str = Field(..., description="用户问题")
    response: str = Field(..., description="Agent回复")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="上下文信息")


class MetricResultSchema(BaseModel):
    metric_type: str
    value: float
    details: str = ""
    threshold: Optional[float] = None
    passed: bool = True


class EvaluationResponse(BaseModel):
    session_id: str
    timestamp: str
    query: str
    response: str
    metrics: Dict[str, MetricResultSchema]
    overall_score: float
    grade: str
    skill_results: List[Dict] = Field(default_factory=list)
    tool_usage: List[str] = Field(default_factory=list)


class EvaluationReportResponse(BaseModel):
    session_id: str
    statistics: Dict[str, Any]
    global_stats: Dict[str, Any]
