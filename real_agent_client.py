#!/usr/bin/env python3
"""
真实Agent客户端
用于连接实际运行的智能客服Agent服务
替换agent_test_suite.py中的MockAgentClient
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Optional
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class RealAgentClient:
    """
    真实Agent客户端，连接FastAPI后端服务
    """
    
    def __init__(self, base_url: str = "http://localhost:8000", session_id: Optional[str] = None):
        """
        初始化客户端
        
        Args:
            base_url: Agent服务的基础URL
            session_id: 会话ID，如果为None则自动生成
        """
        self.base_url = base_url.rstrip('/')
        self.session_id = session_id or f"test_session_{int(time.time())}"
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=30)  # 30秒超时
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.session:
            await self.session.close()
    
    async def chat(self, message: str, stream: bool = False) -> Dict:
        """
        发送消息到Agent服务
        
        Args:
            message: 用户消息
            stream: 是否使用流式输出
            
        Returns:
            Agent响应字典
        """
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        
        url = f"{self.base_url}/api/v1/chat"
        
        payload = {
            "session_id": self.session_id,
            "message": message,
            "stream": stream
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        try:
            if stream:
                return await self._chat_stream(url, payload, headers)
            else:
                return await self._chat_normal(url, payload, headers)
                
        except aiohttp.ClientError as e:
            return {
                "message": f"连接Agent服务失败: {str(e)}",
                "intent": "error",
                "intent_confidence": 0,
                "skills_used": [],
                "success": False,
                "error": str(e)
            }
        except asyncio.TimeoutError:
            return {
                "message": "请求超时，请检查Agent服务是否正常运行",
                "intent": "error",
                "intent_confidence": 0,
                "skills_used": [],
                "success": False,
                "error": "timeout"
            }
        except Exception as e:
            return {
                "message": f"处理请求时发生错误: {str(e)}",
                "intent": "error",
                "intent_confidence": 0,
                "skills_used": [],
                "success": False,
                "error": str(e)
            }
    
    async def _chat_normal(self, url: str, payload: Dict, headers: Dict) -> Dict:
        """普通聊天请求"""
        async with self.session.post(url, json=payload, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                error_text = await response.text()
                return {
                    "message": f"Agent服务返回错误: {response.status}",
                    "intent": "error",
                    "intent_confidence": 0,
                    "skills_used": [],
                    "success": False,
                    "error": error_text
                }
    
    async def _chat_stream(self, url: str, payload: Dict, headers: Dict) -> Dict:
        """流式聊天请求"""
        # 修改headers以支持流式
        headers["Accept"] = "text/event-stream"
        
        full_response = ""
        async with self.session.post(url, json=payload, headers=headers) as response:
            if response.status == 200:
                async for line in response.content:
                    if line:
                        line_text = line.decode('utf-8').strip()
                        if line_text.startswith('data: '):
                            data = line_text[6:]  # 去掉'data: '前缀
                            if data == '[DONE]':
                                break
                            try:
                                chunk = json.loads(data)
                                if 'message' in chunk:
                                    full_response += chunk['message']
                            except json.JSONDecodeError:
                                pass
                
                # 流式请求返回完整响应
                return {
                    "message": full_response,
                    "intent": "stream_response",
                    "intent_confidence": 1.0,
                    "skills_used": ["streaming"],
                    "success": True
                }
            else:
                error_text = await response.text()
                return {
                    "message": f"流式请求失败: {response.status}",
                    "intent": "error",
                    "intent_confidence": 0,
                    "skills_used": [],
                    "success": False,
                    "error": error_text
                }
    
    async def get_health(self) -> Dict:
        """检查服务健康状态"""
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        
        url = f"{self.base_url}/api/v1/health"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status}"
                    }
        except Exception as e:
            return {
                "status": "unreachable",
                "error": str(e)
            }
    
    async def get_metrics(self) -> Dict:
        """获取服务指标"""
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        
        url = f"{self.base_url}/api/v1/metrics"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {
                        "error": f"HTTP {response.status}"
                    }
        except Exception as e:
            return {
                "error": str(e)
            }


async def test_connection():
    """测试连接"""
    async with RealAgentClient() as client:
        print("测试Agent服务连接...")
        
        # 测试健康检查
        health = await client.get_health()
        print(f"健康状态: {health}")
        
        if health.get('status') == 'healthy':
            print("✅ Agent服务运行正常")
            
            # 测试简单聊天
            print("\n测试简单聊天...")
            response = await client.chat("你好")
            print(f"响应: {response.get('message', '')[:100]}...")
            print(f"意图: {response.get('intent')}")
            print(f"置信度: {response.get('intent_confidence')}")
            
            return True
        else:
            print("❌ Agent服务不可用")
            print(f"错误: {health.get('error', '未知错误')}")
            return False


async def run_single_test(question: str):
    """运行单个测试"""
    async with RealAgentClient() as client:
        print(f"\n测试问题: {question}")
        start_time = time.time()
        
        response = await client.chat(question)
        elapsed = time.time() - start_time
        
        print(f"响应时间: {elapsed:.2f}秒")
        print(f"响应内容: {response.get('message', '')[:200]}...")
        print(f"意图: {response.get('intent')} (置信度: {response.get('intent_confidence', 0):.2f})")
        print(f"使用的技能: {response.get('skills_used', [])}")
        print(f"成功: {response.get('success', False)}")
        
        return response


async def main():
    """主函数"""
    print("真实Agent客户端测试")
    print("="*60)
    
    # 测试连接
    connected = await test_connection()
    
    if not connected:
        print("\n请确保Agent服务已启动:")
        print("1. 进入backend目录: cd backend")
        print("2. 启动服务: python -m uvicorn app.main:app --reload --port 8000")
        print("3. 等待服务启动完成后再运行测试")
        return
    
    # 运行示例测试
    test_questions = [
        "X12 Pro手机多少钱？",
        "推荐一款适合游戏的笔记本电脑",
        "你们支持七天无理由退货吗？",
        "你好",
        "谢谢你的帮助"
    ]
    
    print("\n" + "="*60)
    print("运行示例测试")
    print("="*60)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n测试 {i}/{len(test_questions)}")
        await run_single_test(question)
        await asyncio.sleep(1)  # 避免请求过快


if __name__ == "__main__":
    asyncio.run(main())