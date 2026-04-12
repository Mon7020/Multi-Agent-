#!/usr/bin/env python3
"""
智能客服Agent测试套件
测试Agent的检索能力、上下文能力、沟通能力
基于知识库文件：电子商品价格表.txt、常见问题_FAQ.txt、product_discounts.yaml
"""

import asyncio
import json
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

@dataclass
class TestCase:
    """测试用例定义"""
    id: str
    question: str
    expected_keywords: List[str]  # 期望回答中包含的关键词
    expected_intent: str  # 期望的意图分类
    difficulty: str  # easy/medium/hard
    test_type: str  # retrieval/context/communication
    follow_up: Optional[str] = None  # 后续问题（用于上下文测试）
    context_dependency: Optional[str] = None  # 上下文依赖说明

class TestType(Enum):
    """测试类型枚举"""
    RETRIEVAL = "retrieval"  # 检索能力测试
    CONTEXT = "context"      # 上下文能力测试
    COMMUNICATION = "communication"  # 沟通能力测试

class TestSuite:
    """测试套件主类"""
    
    def __init__(self):
        self.test_cases = self._load_test_cases()
        self.results = []
        
    def _load_test_cases(self) -> List[TestCase]:
        """加载测试用例"""
        return [
            # ==================== 检索能力测试 ====================
            TestCase(
                id="R001",
                question="X12 Pro手机多少钱？",
                expected_keywords=["X12 Pro", "3999", "3299", "智能手机"],
                expected_intent="price_inquiry",
                difficulty="easy",
                test_type="retrieval",
                context_dependency="需要从价格表中检索X12 Pro的价格信息"
            ),
            TestCase(
                id="R002",
                question="推荐一款适合游戏的笔记本电脑",
                expected_keywords=["拯救者", "游戏", "笔记本电脑", "RTX4060", "11999"],
                expected_intent="recommendation",
                difficulty="medium",
                test_type="retrieval",
                context_dependency="需要理解'适合游戏'的语义，检索游戏本相关信息"
            ),
            TestCase(
                id="R003",
                question="SoundPods Pro和FreeBuds SE有什么区别？",
                expected_keywords=["SoundPods Pro", "FreeBuds SE", "降噪", "续航", "价格"],
                expected_intent="comparison",
                difficulty="hard",
                test_type="retrieval",
                context_dependency="需要同时检索两款耳机的详细信息并进行对比"
            ),
            TestCase(
                id="R004",
                question="你们支持七天无理由退货吗？",
                expected_keywords=["七天无理由退货", "不影响二次销售", "申请"],
                expected_intent="general",
                difficulty="easy",
                test_type="retrieval",
                context_dependency="需要从FAQ中检索退货政策"
            ),
            TestCase(
                id="R005",
                question="有没有2000元以下的降噪耳机？",
                expected_keywords=["降噪耳机", "2000元以下", "WH-1000XM5", "2199", "SoundPods Pro"],
                expected_intent="recommendation",
                difficulty="medium",
                test_type="retrieval",
                context_dependency="需要理解价格区间约束，检索符合条件的耳机"
            ),
            
            # ==================== 上下文能力测试 ====================
            TestCase(
                id="C001",
                question="我想买一款笔记本电脑",
                expected_keywords=["笔记本电脑", "推荐", "ThinkBook", "小新Pro"],
                expected_intent="sales",
                difficulty="easy",
                test_type="context",
                follow_up="第二款详细介绍下",
                context_dependency="后续问题'第二款'需要依赖前一轮的推荐列表"
            ),
            TestCase(
                id="C002",
                question="X12手机怎么样？",
                expected_keywords=["X12", "2999", "天玑9200", "OLED"],
                expected_intent="product_spec",
                difficulty="medium",
                test_type="context",
                follow_up="那X12 Pro呢？",
                context_dependency="需要记住前一轮讨论的是X12，对比X12 Pro"
            ),
            TestCase(
                id="C003",
                question="推荐一款蓝牙耳机",
                expected_keywords=["蓝牙耳机", "推荐", "SoundPods Pro", "FreeBuds SE"],
                expected_intent="sales",
                difficulty="medium",
                test_type="context",
                follow_up="第一款能便宜点吗？",
                context_dependency="需要记住推荐的第一款耳机，并进行价格谈判"
            ),
            TestCase(
                id="C004",
                question="下单后可以取消订单吗？",
                expected_keywords=["取消订单", "未发货", "我的订单"],
                expected_intent="general",
                difficulty="easy",
                test_type="context",
                follow_up="那如果已经发货了呢？",
                context_dependency="需要基于FAQ信息进行逻辑推理"
            ),
            TestCase(
                id="C005",
                question="我想买一个平板电脑，预算4000左右",
                expected_keywords=["平板电脑", "4000", "MatePad Pro", "3399", "AirPad"],
                expected_intent="sales",
                difficulty="hard",
                test_type="context",
                follow_up="刚才说的那款能连接手写笔吗？",
                context_dependency="需要记住推荐的平板型号，并回答特定功能问题"
            ),
            
            # ==================== 沟通能力测试 ====================
            TestCase(
                id="M001",
                question="你好",
                expected_keywords=["你好", "欢迎", "帮助"],
                expected_intent="greeting",
                difficulty="easy",
                test_type="communication",
                context_dependency="测试基本问候和礼貌用语"
            ),
            TestCase(
                id="M002",
                question="谢谢你的帮助",
                expected_keywords=["不客气", "欢迎", "随时"],
                expected_intent="farewell",
                difficulty="easy",
                test_type="communication",
                context_dependency="测试结束对话的礼貌回应"
            ),
            TestCase(
                id="M003",
                question="这个太贵了，能不能便宜点？",
                expected_keywords=["优惠", "折扣", "价格", "考虑"],
                expected_intent="negotiation",
                difficulty="medium",
                test_type="communication",
                context_dependency="测试价格谈判的话术和策略"
            ),
            TestCase(
                id="M004",
                question="我不太确定选哪个，你有什么建议吗？",
                expected_keywords=["建议", "根据", "需求", "推荐"],
                expected_intent="sales",
                difficulty="medium",
                test_type="communication",
                context_dependency="测试引导性提问和需求挖掘能力"
            ),
            TestCase(
                id="M005",
                question="你们的产品是正品吗？质量有保证吗？",
                expected_keywords=["正品", "保证", "官方", "验证", "假一赔三"],
                expected_intent="general",
                difficulty="easy",
                test_type="communication",
                context_dependency="测试处理客户疑虑的沟通技巧"
            ),
            
            # ==================== 综合能力测试 ====================
            TestCase(
                id="I001",
                question="我想买一个礼物送人，预算3000以内，有什么推荐？",
                expected_keywords=["3000以内", "推荐", "礼物", "智能手机", "平板", "耳机"],
                expected_intent="sales",
                difficulty="hard",
                test_type="retrieval",
                context_dependency="需要理解'礼物'场景，结合预算约束进行推荐"
            ),
            TestCase(
                id="I002",
                question="我的耳机连不上手机怎么办？",
                expected_keywords=["连接", "蓝牙", "重启", "重置", "帮助"],
                expected_intent="tech_support",
                difficulty="medium",
                test_type="communication",
                context_dependency="测试技术支持场景的问题解决能力"
            ),
            TestCase(
                id="I003",
                question="刚才说的那款笔记本电脑，续航怎么样？",
                expected_keywords=["续航", "电池", "小时", "持久"],
                expected_intent="product_spec",
                difficulty="hard",
                test_type="context",
                context_dependency="需要依赖前文提到的笔记本电脑型号，检索续航信息"
            ),
            TestCase(
                id="I004",
                question="有没有适合设计师用的设备？",
                expected_keywords=["设计师", "适合", "笔记本电脑", "平板", "显示器"],
                expected_intent="recommendation",
                difficulty="medium",
                test_type="retrieval",
                context_dependency="需要理解'设计师'的专业需求，检索相关设备"
            ),
            TestCase(
                id="I005",
                question="我要出差，需要轻便的办公设备",
                expected_keywords=["出差", "轻便", "办公", "笔记本电脑", "平板", "便携"],
                expected_intent="sales",
                difficulty="hard",
                test_type="retrieval",
                context_dependency="需要理解'出差轻便'的场景需求，进行精准推荐"
            ),
        ]
    
    async def run_single_test(self, test_case: TestCase, agent_client) -> Dict:
        """运行单个测试用例"""
        print(f"\n{'='*60}")
        print(f"测试用例 {test_case.id}: {test_case.question}")
        print(f"类型: {test_case.test_type} | 难度: {test_case.difficulty}")
        
        start_time = time.time()
        
        try:
            # 第一轮对话
            response1 = await agent_client.chat(test_case.question)
            elapsed1 = time.time() - start_time
            
            # 分析第一轮响应
            result1 = self._analyze_response(
                response1, test_case, "第一轮"
            )
            
            # 如果有后续问题，进行第二轮测试
            if test_case.follow_up:
                print(f"\n[上下文测试] 后续问题: {test_case.follow_up}")
                start_time2 = time.time()
                response2 = await agent_client.chat(test_case.follow_up)
                elapsed2 = time.time() - start_time2
                
                result2 = self._analyze_response(
                    response2, test_case, "第二轮", 
                    previous_response=response1
                )
                
                # 检查上下文连贯性
                context_score = self._evaluate_context_coherence(
                    response1, response2, test_case
                )
                result2["context_coherence_score"] = context_score
                result2["response_time"] = elapsed2
            else:
                result2 = None
                context_score = None
            
            # 计算总分
            total_score = self._calculate_total_score(result1, result2, context_score)
            
            return {
                "test_id": test_case.id,
                "question": test_case.question,
                "test_type": test_case.test_type,
                "difficulty": test_case.difficulty,
                "first_response": result1,
                "second_response": result2,
                "total_score": total_score,
                "context_dependency": test_case.context_dependency
            }
            
        except Exception as e:
            print(f"测试失败: {e}")
            return {
                "test_id": test_case.id,
                "error": str(e),
                "total_score": 0
            }
    
    def _analyze_response(self, response: Dict, test_case: TestCase, 
                         round_label: str, previous_response: Dict = None) -> Dict:
        """分析Agent响应"""
        response_text = response.get("message", "").lower()
        
        # 关键词匹配度
        keyword_matches = []
        for keyword in test_case.expected_keywords:
            if keyword.lower() in response_text:
                keyword_matches.append(keyword)
        
        keyword_score = len(keyword_matches) / len(test_case.expected_keywords) if test_case.expected_keywords else 1.0
        
        # 意图匹配
        actual_intent = response.get("intent", "unknown")
        intent_match = actual_intent == test_case.expected_intent
        
        # 响应质量评估
        quality_score = self._evaluate_response_quality(response_text)
        
        # 检查是否包含检索来源（仅对检索测试）
        has_sources = "source" in response_text or "来自" in response_text or "根据" in response_text
        
        return {
            "round": round_label,
            "response_text": response.get("message", "")[:200] + "..." if len(response.get("message", "")) > 200 else response.get("message", ""),
            "actual_intent": actual_intent,
            "expected_intent": test_case.expected_intent,
            "intent_match": intent_match,
            "keyword_matches": keyword_matches,
            "keyword_score": keyword_score,
            "has_sources": has_sources,
            "quality_score": quality_score,
            "confidence": response.get("intent_confidence", 0),
            "skills_used": response.get("skills_used", [])
        }
    
    def _evaluate_response_quality(self, text: str) -> float:
        """评估响应质量"""
        score = 0.0
        
        # 长度适中（50-300字）
        length = len(text)
        if 50 <= length <= 300:
            score += 0.3
        elif length > 50:
            score += 0.2
        else:
            score += 0.1
        
        # 结构清晰（包含标点、分段）
        if any(punct in text for punct in ["。", "！", "？", "\n", "；"]):
            score += 0.3
        
        # 专业术语使用
        professional_terms = ["您好", "感谢", "建议", "推荐", "根据", "支持", "保证"]
        if any(term in text for term in professional_terms):
            score += 0.2
        
        # 礼貌用语
        polite_terms = ["请", "谢谢", "不客气", "欢迎", "抱歉"]
        if any(term in text for term in polite_terms):
            score += 0.2
        
        return min(score, 1.0)
    
    def _evaluate_context_coherence(self, response1: Dict, response2: Dict, 
                                   test_case: TestCase) -> float:
        """评估上下文连贯性"""
        text1 = response1.get("message", "").lower()
        text2 = response2.get("message", "").lower()
        
        score = 0.0
        
        # 检查是否引用前文内容
        if test_case.follow_up and "第二款" in test_case.follow_up:
            # 检查是否识别了"第二款"的指代
            if "第二" in text2 or "2款" in text2 or "第二个" in text2:
                score += 0.4
        
        # 检查话题连贯性
        common_words = set(text1.split()[:20]) & set(text2.split()[:20])
        if len(common_words) > 2:
            score += 0.3
        
        # 检查逻辑连贯性
        if "刚才" in text2 or "之前" in text2 or "上面" in text2:
            score += 0.3
        
        return min(score, 1.0)
    
    def _calculate_total_score(self, result1: Dict, result2: Dict, 
                              context_score: float) -> float:
        """计算总分"""
        if not result1:
            return 0.0
        
        # 第一轮得分
        score1 = (
            result1["keyword_score"] * 0.4 +
            (1.0 if result1["intent_match"] else 0.0) * 0.3 +
            result1["quality_score"] * 0.3
        )
        
        total = score1
        
        # 如果有第二轮，加入第二轮得分
        if result2:
            score2 = (
                result2["keyword_score"] * 0.3 +
                (1.0 if result2["intent_match"] else 0.0) * 0.2 +
                result2["quality_score"] * 0.2
            )
            total = (score1 * 0.6 + score2 * 0.4)
            
            # 加入上下文连贯性得分
            if context_score is not None:
                total = total * 0.8 + context_score * 0.2
        
        return round(total * 100, 2)  # 转换为百分制
    
    async def run_all_tests(self, agent_client, test_types=None):
        """运行所有测试"""
        print("="*60)
        print("开始运行智能客服Agent测试套件")
        print("="*60)
        
        if test_types:
            filtered_cases = [tc for tc in self.test_cases if tc.test_type in test_types]
        else:
            filtered_cases = self.test_cases
        
        print(f"测试用例总数: {len(filtered_cases)}")
        
        for test_case in filtered_cases:
            result = await self.run_single_test(test_case, agent_client)
            self.results.append(result)
        
        # 生成报告
        self.generate_report()
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*60)
        print("测试报告")
        print("="*60)
        
        if not self.results:
            print("没有测试结果")
            return
        
        # 按测试类型分组
        type_groups = {}
        for result in self.results:
            if "error" in result:
                continue
            test_type = result.get("test_type", "unknown")
            if test_type not in type_groups:
                type_groups[test_type] = []
            type_groups[test_type].append(result)
        
        # 总体统计
        total_tests = len([r for r in self.results if "error" not in r])
        passed_tests = len([r for r in self.results if r.get("total_score", 0) >= 60])
        avg_score = sum(r.get("total_score", 0) for r in self.results if "error" not in r) / total_tests if total_tests > 0 else 0
        
        print(f"\n总体统计:")
        print(f"  测试用例总数: {total_tests}")
        print(f"  通过测试数: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        print(f"  平均得分: {avg_score:.1f}/100")
        
        # 按类型统计
        print(f"\n按测试类型统计:")
        for test_type, results in type_groups.items():
            type_count = len(results)
            type_avg = sum(r.get("total_score", 0) for r in results) / type_count if type_count > 0 else 0
            type_passed = len([r for r in results if r.get("total_score", 0) >= 60])
            
            print(f"  {test_type.upper():<15} 数量: {type_count:<3} 平均分: {type_avg:5.1f} 通过率: {type_passed/type_count*100:5.1f}%")
        
        # 按难度统计
        print(f"\n按难度统计:")
        difficulty_groups = {"easy": [], "medium": [], "hard": []}
        for result in self.results:
            if "error" in result:
                continue
            # 从test_cases中查找难度
            for tc in self.test_cases:
                if tc.id == result.get("test_id"):
                    difficulty_groups[tc.difficulty].append(result)
                    break
        
        for difficulty, results in difficulty_groups.items():
            if results:
                diff_count = len(results)
                diff_avg = sum(r.get("total_score", 0) for r in results) / diff_count
                diff_passed = len([r for r in results if r.get("total_score", 0) >= 60])
                
                print(f"  {difficulty.upper():<15} 数量: {diff_count:<3} 平均分: {diff_avg:5.1f} 通过率: {diff_passed/diff_count*100:5.1f}%")
        
        # 详细结果
        print(f"\n详细测试结果:")
        print(f"{'ID':<6} {'类型':<12} {'难度':<8} {'得分':<6} {'状态':<8} {'关键词匹配':<10}")
        print("-"*60)
        
        for result in self.results:
            if "error" in result:
                status = "ERROR"
                score = 0
                keyword_match = "N/A"
            else:
                score = result.get("total_score", 0)
                status = "PASS" if score >= 60 else "FAIL"
                first_res = result.get("first_response", {})
                keyword_match = f"{len(first_res.get('keyword_matches', []))}/{len(self._get_test_case(result['test_id']).expected_keywords)}"
            
            # 查找测试用例
            tc = self._get_test_case(result.get("test_id", ""))
            test_type = tc.test_type if tc else "unknown"
            difficulty = tc.difficulty if tc else "unknown"
            
            print(f"{result.get('test_id', 'N/A'):<6} {test_type:<12} {difficulty:<8} {score:<6.1f} {status:<8} {keyword_match:<10}")
        
        # 保存结果到文件
        self._save_results_to_file()
    
    def _get_test_case(self, test_id: str) -> Optional[TestCase]:
        """根据ID查找测试用例"""
        for tc in self.test_cases:
            if tc.id == test_id:
                return tc
        return None
    
    def _save_results_to_file(self):
        """保存测试结果到文件"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_{timestamp}.json"
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        # 准备保存的数据
        save_data = {
            "timestamp": timestamp,
            "results": self.results,
            "summary": {
                "total_tests": len([r for r in self.results if "error" not in r]),
                "passed_tests": len([r for r in self.results if r.get("total_score", 0) >= 60]),
                "average_score": sum(r.get("total_score", 0) for r in self.results if "error" not in r) / len([r for r in self.results if "error" not in r]) if any("error" not in r for r in self.results) else 0
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n测试结果已保存到: {filepath}")


class MockAgentClient:
    """
    Mock Agent客户端，用于测试
    实际使用时需要替换为真实的Agent客户端
    """
    
    def __init__(self):
        self.session_id = "test_session_" + str(int(time.time()))
        self.conversation_history = []
    
    async def chat(self, message: str) -> Dict:
        """模拟Agent聊天接口"""
        # 这里应该调用真实的Agent服务
        # 暂时返回模拟响应
        
        # 模拟处理延迟
        await asyncio.sleep(0.5)
        
        # 简单意图识别
        intent = self._detect_intent(message)
        
        # 模拟响应生成
        response = self._generate_response(message, intent)
        
        # 记录对话历史
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": response["message"]
        })
        
        return response
    
    def _detect_intent(self, message: str) -> str:
        """简单意图识别"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["你好", "嗨", "hello"]):
            return "greeting"
        elif any(word in message_lower for word in ["谢谢", "感谢"]):
            return "farewell"
        elif any(word in message_lower for word in ["多少钱", "价格", "价"]):
            return "price_inquiry"
        elif any(word in message_lower for word in ["推荐", "建议", "选哪个"]):
            return "recommendation"
        elif any(word in message_lower for word in ["区别", "对比", "比较"]):
            return "comparison"
        elif any(word in message_lower for word in ["怎么办", "怎么", "如何"]):
            return "tech_support"
        elif any(word in message_lower for word in ["便宜", "优惠", "折扣"]):
            return "negotiation"
        else:
            return "general"
    
    def _generate_response(self, message: str, intent: str) -> Dict:
        """生成模拟响应"""
        responses = {
            "greeting": "您好！欢迎来到环球优选，我是智能客服助手。有什么可以帮助您的吗？",
            "farewell": "不客气！很高兴为您服务。如果还有其他问题，随时联系我。祝您购物愉快！",
            "price_inquiry": "根据我们的价格表，X12 Pro手机的标价是3999元，活动期间最大优惠价是3299元。这是一款旗舰级智能手机，配备6.7英寸AMOLED曲面屏和骁龙8 Gen3处理器。",
            "recommendation": "根据您的需求，我为您推荐以下几款产品：\n1. 【智能手机 X12 Pro】 - 旗舰性能，拍照出色\n2. 【笔记本电脑 小新Pro 16】 - 大屏高性能，适合设计工作\n3. 【无线降噪耳机 WH-1000XM5】 - 顶级降噪，音质卓越\n您对哪款更感兴趣呢？",
            "comparison": "SoundPods Pro和FreeBuds SE的主要区别：\n1. 降噪能力：SoundPods Pro支持主动降噪40dB，FreeBuds SE是半入耳式设计\n2. 续航时间：SoundPods Pro总续航40小时，FreeBuds SE是25小时\n3. 价格：SoundPods Pro标价599元，FreeBuds SE标价399元\n根据您的需求选择适合的款式。",
            "tech_support": "耳机连接问题可以尝试以下步骤：\n1. 确保手机蓝牙已开启\n2. 将耳机放入充电盒，然后取出重新配对\n3. 重启手机蓝牙功能\n4. 如果还是不行，可以尝试重置耳机\n需要更详细的指导吗？",
            "negotiation": "我理解您对价格的关注。目前X12 Pro手机的最大优惠价是3299元，这已经是非常有竞争力的价格了。如果您今天下单，我可以为您申请额外的礼品或延长保修服务。",
            "general": "关于您的问题，根据我们的常见问题解答：下单后未发货的订单可以在'我的订单'中直接取消。如果订单已经发货，则无法取消。您还有其他问题吗？"
        }
        
        return {
            "message": responses.get(intent, "我理解您的问题，让我为您查询相关信息。"),
            "intent": intent,
            "intent_confidence": 0.8,
            "skills_used": ["general_knowledge"],
            "success": True
        }


async def main():
    """主函数"""
    # 创建测试套件
    test_suite = TestSuite()
    
    # 创建Mock Agent客户端
    # 实际使用时替换为真实的Agent客户端
    agent_client = MockAgentClient()
    
    # 运行测试
    print("选择测试模式:")
    print("1. 全部测试")
    print("2. 仅测试检索能力")
    print("3. 仅测试上下文能力")
    print("4. 仅测试沟通能力")
    
    choice = input("请输入选择 (1-4): ").strip()
    
    test_types_map = {
        "1": None,  # 全部
        "2": ["retrieval"],
        "3": ["context"],
        "4": ["communication"]
    }
    
    test_types = test_types_map.get(choice, None)
    
    await test_suite.run_all_tests(agent_client, test_types)


if __name__ == "__main__":
    asyncio.run(main())