import asyncio
import json

import pytest
from fastapi import WebSocketDisconnect

from app.api.v1 import chat


class Socket:
    def __init__(self):
        self.headers = {}
        self.query_params = {}
        self.incoming = asyncio.Queue()
        self.outgoing = asyncio.Queue()

    async def accept(self):
        pass

    async def receive_text(self):
        value = await self.incoming.get()
        if value is None:
            raise WebSocketDisconnect()
        return json.dumps(value)

    async def send_json(self, value):
        await self.outgoing.put(value)


@pytest.mark.asyncio
async def test_same_session_connections_remain_isolated(monkeypatch):
    monkeypatch.setattr(chat, '_resolve_ws_user_id', lambda ws, message_token, requested_user_id: message_token)

    class Service:
        class Sessions:
            def get_session(self, session_id):
                return type('Session', (), {'user_id': 'owner'})()

        session_manager = Sessions()

        async def stream_process_message(self, **kwargs):
            yield {'content': kwargs['message'], 'done': True}

    monkeypatch.setattr(chat, 'chat_service', Service())
    a, b, intruder = Socket(), Socket(), Socket()
    tasks = [asyncio.create_task(chat.websocket_chat(ws, 'shared')) for ws in (a, b, intruder)]
    try:
        for ws in (a, b, intruder):
            assert (await asyncio.wait_for(ws.outgoing.get(), 1))['type'] == 'greeting'
        await a.incoming.put({'message': 'first', 'token': 'owner'})
        await b.incoming.put({'message': 'second', 'token': 'owner'})
        await intruder.incoming.put({'message': 'steal', 'token': 'other'})
        assert 'denied' in (await asyncio.wait_for(intruder.outgoing.get(), 1))['content']
        for ws, expected in ((a, 'first'), (b, 'second')):
            assert (await asyncio.wait_for(ws.outgoing.get(), 1))['type'] == 'status'
            assert (await asyncio.wait_for(ws.outgoing.get(), 1))['content'] == expected
            assert (await asyncio.wait_for(ws.outgoing.get(), 1))['type'] == 'done'
        await a.incoming.put(None)
        await asyncio.wait_for(tasks[0], 1)
        await b.incoming.put({'message': 'still connected', 'token': 'owner'})
        assert (await asyncio.wait_for(b.outgoing.get(), 1))['type'] == 'status'
        assert (await asyncio.wait_for(b.outgoing.get(), 1))['content'] == 'still connected'
    finally:
        for ws in (b, intruder):
            await ws.incoming.put(None)
        await asyncio.gather(*tasks)
