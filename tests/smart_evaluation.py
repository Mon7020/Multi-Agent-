"""
优化版全套评测脚本
使用语义匹配而非简单关键词匹配
"""

import json
import time
import statistics
import sys
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Set
from sentence_transformers import SentenceTransformer

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.rag_tool import RAGTool
from core.logger import LoggerManager

logger = LoggerManager.get_logger("smart_evaluation")


class SmartEvaluator:
    """智能评测器 - 使用语义相似度而非关键词匹配"""

    def __init__(self):
        self.model = SentenceTransformer('shibing624/text2vec-base-chinese')

    def extract_keywords(self, text: str) -> Set[str]:
        """提取关键词"""
        keywords = set()

        # 提取中文词（2-4字）
        chinese = re.findall(r'[\u4e00-\u9fa5]{2,4}', text)
        keywords.update(chinese)

        # 提取英文和数字组合
        english = re.findall(r'[a-zA-Z0-9]+', text.lower())
        keywords.update(english)

        # 提取数字
        numbers = re.findall(r'\d+', text)
        keywords.update(numbers)

        return keywords

    def is_relevant(self, query: str, doc_content: str, threshold: float = 0.5) -> bool:
        """
        判断文档是否与查询相关
        使用语义相似度
        """
        # 计算相似度
        embeddings = self.model.encode([query, doc_content[:500]])
        similarity = self._cosine_similarity(embeddings[0], embeddings[1])

        return similarity > threshold

    def _cosine_similarity(self, vec1, vec2) -> float:
        """计算余弦相似度"""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        return dot / (norm1 * norm2) if norm1 * norm2 > 0 else 0

    def evaluate_retrieval(self, rag_tool: RAGTool, test_cases: List[Dict]) -> Dict:
        """评测检索质量"""
        results = []

        for case in test_cases:
            query = case['query']
            expected_category = case.get('category', '')

            # 执行检索
            start_time = time.time()
            retrieval_result = rag_tool.retrieve(query, top_k=3)
            latency_ms = (time.time() - start_time) * 1000

            docs = retrieval_result.get('documents', [])

            # 评估每个文档
            relevant_count = 0
            for doc in docs:
                content = doc.get('content', doc.get('page_content', ''))
                if self.is_relevant(query, content):
                    relevant_count += 1

            # 计算指标
            recall = relevant_count / min(3, relevant_count + 1)
            precision = relevant_count / len(docs) if docs else 0

            results.append({
                'query': query,
                'expected_category': expected_category,
                'retrieved_count': len(docs),
                'relevant_count': relevant_count,
                'recall': recall,
                'precision': precision,
                'latency_ms': latency_ms,
                'is_relevant': relevant_count > 0
            })

            logger.info(f"查询: {query}")
            logger.info(f"  检索: {len(docs)} 个文档, {relevant_count} 个相关")
            logger.info(f"  召回率: {recall:.2%}, 准确率: {precision:.2%}")

        # 汇总
        relevant_queries = sum(1 for r in results if r['is_relevant'])
        avg_recall = statistics.mean([r['recall'] for r in results])
        avg_precision = statistics.mean([r['precision'] for r in results])
        avg_latency = statistics.mean([r['latency_ms'] for r in results])
        latencies = sorted([r['latency_ms'] for r in results])
        n = len(latencies)

        return {
            'total_queries': len(results),
            'relevant_queries': relevant_queries,
            'success_rate': relevant_queries / len(results),
            'avg_recall': avg_recall,
            'avg_precision': avg_precision,
            'avg_latency_ms': avg_latency,
            'p50_latency_ms': latencies[n // 2],
            'p95_latency_ms': latencies[int(n * 0.95)],
            'detailed_results': results
        }


def main():
    """主函数"""
    print("=" * 80)
    print("RAG 系统智能评测")
    print("=" * 80)

    print("\n初始化 RAG 系统...")
    rag = RAGTool()

    print("\n初始化评测器...")
    evaluator = SmartEvaluator()

    # 测试用例
    test_cases = [
        {"query": "X12 Pro手机多少钱", "category": "手机"},
        {"query": "X12 和 X12 Pro 有什么区别", "category": "手机"},
        {"query": "AirPad 平板电脑的价格", "category": "平板"},
        {"query": "蓝牙耳机推荐", "category": "耳机"},
        {"query": "智能手表哪个好", "category": "手表"},
        {"query": "游戏笔记本推荐", "category": "笔记本"},
        {"query": "路由器推荐", "category": "路由器"},
        {"query": "怎么退货", "category": "售后"},
        {"query": "怎么联系客服", "category": "售后"},
        {"query": "保修期多久", "category": "售后"},
    ]

    print("\n执行评测...")
    results = evaluator.evaluate_retrieval(rag, test_cases)

    # 打印结果
    print("\n" + "=" * 80)
    print("评测结果")
    print("=" * 80)

    print(f"\n总体统计:")
    print(f"  总查询数: {results['total_queries']}")
    print(f"  相关查询数: {results['relevant_queries']}")
    print(f"  查询成功率: {results['success_rate']:.1%}")

    print(f"\n检索质量:")
    print(f"  平均召回率: {results['avg_recall']:.1%}")
    print(f"  平均准确率: {results['avg_precision']:.1%}")

    print(f"\n性能指标:")
    print(f"  平均延迟: {results['avg_latency_ms']:.0f}ms")
    print(f"  P50 延迟: {results['p50_latency_ms']:.0f}ms")
    print(f"  P95 延迟: {results['p95_latency_ms']:.0f}ms")

    print("\n" + "=" * 80)
    print("评测完成")
    print("=" * 80)

    # 保存结果
    output_file = f"smart_evaluation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存到: {output_file}")


if __name__ == "__main__":
    main()
