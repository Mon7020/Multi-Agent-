"""
聊天 API
支持 Chat Service V3（Context+RAG融合版）

线程安全设计：
- ConnectionManager 使用 threading.Lock 保护 WebSocket 连接
- 所有端点都有统一的错误处理
- 输入验证确保 session_id 和 message 格式正确

核心特性：
1. Context+RAG融合 - 双向信息流
2. 自适应融合策略 - 根据检索质量动态选择
3. 智能质量评估 - 自动评估检索结果质量
"""

import json
import threading
from typing import List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, Query
from fastapi.responses import StreamingResponse

from app.schemas import ChatRequest, ChatResponse, ChatMessage
# 使用 Chat Service V3（Context+RAG融合版）
from app.services.chat_service_v3 import chat_service_v3 as chat_service

router = APIRouter()


# WebSocket 连接管理器（线程安全）
class ConnectionManager:
    def __init__(self):
        self._lock = threading.Lock()
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """连接 WebSocket（线程安全）"""
        await websocket.accept()
        with self._lock:
            self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        """断开 WebSocket 连接（线程安全）"""
        with self._lock:
            if session_id in self.active_connections:
                del self.active_connections[session_id]

    async def send_message(self, session_id: str, message: dict):
        """发送消息（线程安全）"""
        with self._lock:
            if session_id in self.active_connections:
                await self.active_connections[session_id].send_json(message)


manager = ConnectionManager()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    处理用户消息

    输入验证：
    - session_id: 非空字符串，最大 128 字符
    - message: 非空字符串，最大 4096 字符
    """
    # 输入验证
    if not request.session_id or len(request.session_id) > 128:
        raise HTTPException(status_code=400, detail="session_id 无效")

    if not request.message or len(request.message) > 4096:
        raise HTTPException(status_code=400, detail="message 无效")

    try:
        history_dict = [h.model_dump() for h in request.history] if request.history else []

        result = await chat_service.process_message(
            session_id=request.session_id,
            message=request.message,
            history=history_dict
        )

        return ChatResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"处理消息失败: {str(e)}")


@router.post("/chat/stream")
async def stream_chat(request: ChatRequest):
    """
    流式对话 (SSE)

    输入验证：
    - session_id: 非空字符串，最大 128 字符
    - message: 非空字符串，最大 4096 字符
    """
    # 输入验证
    if not request.session_id or len(request.session_id) > 128:
        raise HTTPException(status_code=400, detail="session_id 无效")

    if not request.message or len(request.message) > 4096:
        raise HTTPException(status_code=400, detail="message 无效")

    def generate():
        try:
            history_dict = [h.model_dump() for h in request.history] if request.history else []

            # 检查 chat_service 是否有流式处理方法
            if hasattr(chat_service, 'stream_process_message'):
                for chunk in chat_service.stream_process_message(
                    session_id=request.session_id,
                    message=request.message,
                    history=history_dict
                ):
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            else:
                # 如果没有流式方法，返回模拟的完成消息
                yield f"data: {json.dumps({'error': '流式处理不可用'}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/chat/history/{session_id}")
async def get_history(session_id: str):
    """
    获取对话历史

    输入验证：
    - session_id: 非空字符串，最大 128 字符
    """
    # 输入验证
    if not session_id or len(session_id) > 128:
        raise HTTPException(status_code=400, detail="session_id 无效")

    try:
        # 使用正确的方法名
        history = chat_service.get_session_history(session_id)
        messages = [
            ChatMessage(role=msg["role"], content=msg["content"])
            for msg in history
        ]
        return {"session_id": session_id, "messages": messages, "count": len(messages)}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


@router.delete("/chat/history/{session_id}")
async def clear_history(session_id: str):
    """
    清空对话历史

    输入验证：
    - session_id: 非空字符串，最大 128 字符
    """
    # 输入验证
    if not session_id or len(session_id) > 128:
        raise HTTPException(status_code=400, detail="session_id 无效")

    try:
        # 使用正确的方法名
        success = chat_service.clear_session(session_id)
        if success:
            return {"message": "历史已清空", "session_id": session_id}
        else:
            return {"message": "会话不存在", "session_id": session_id}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"清空历史失败: {str(e)}")


@router.websocket("/chat/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket 流式对话

    支持实时流式输出，适合前端流式渲染

    输入验证：
    - session_id: 非空字符串，最大 128 字符
    """
    # 输入验证
    if not session_id or len(session_id) > 128:
        await websocket.close(code=4000, reason="session_id 无效")
        return

    await manager.connect(websocket, session_id)

    try:
        # 加载招呼消息
        greeting_message = chat_service.greeting_message if hasattr(chat_service, 'greeting_message') else "您好！有什么可以帮您的吗？"

        # WebSocket连接建立后，立即发送招呼消息
        await manager.send_message(session_id, {
            "type": "greeting",
            "content": greeting_message,
            "is_greeting": True
        })

        # 接收初始消息
        data = await websocket.receive_text()
        message_data = json.loads(data)

        message = message_data.get("message", "")
        history = message_data.get("history", [])

        # 验证 message
        if not message or len(message) > 4096:
            await manager.send_message(session_id, {
                "type": "error",
                "content": "message 无效"
            })
            return

        # 发送思考中状态
        await manager.send_message(session_id, {
            "type": "status",
            "content": "思考中..."
        })

        # 流式处理
        if hasattr(chat_service, 'stream_process_message'):
            for chunk in chat_service.stream_process_message(
                session_id=session_id,
                message=message,
                history=history
            ):
                await manager.send_message(session_id, {
                    "type": "chunk",
                    "content": chunk.get("content", ""),
                    "done": chunk.get("done", False)
                })
        else:
            # 如果没有流式方法，直接处理
            result = await chat_service.process_message(
                session_id=session_id,
                message=message,
                history=history
            )
            await manager.send_message(session_id, {
                "type": "chunk",
                "content": result.get("message", ""),
                "done": True
            })

        # 发送完成状态
        await manager.send_message(session_id, {
            "type": "done",
            "content": ""
        })

    except json.JSONDecodeError:
        await manager.send_message(session_id, {
            "type": "error",
            "content": "无效的 JSON 格式"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        await manager.send_message(session_id, {
            "type": "error",
            "content": f"处理失败: {str(e)}"
        })
    finally:
        manager.disconnect(session_id)
