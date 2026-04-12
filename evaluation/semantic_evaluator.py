"""
语义评测模块 - 解决关键词匹配与语义检索不匹配的问题

核心改进：
1. 使用Embedding余弦相似度替代关键词匹配
2. 支持同义词扩展和语义相关性判断
3. 修复幻觉检测逻辑（正确处理多产品场景）
4. 修复缓存命中率检测
"""

import json
import time
import statistics
import sys
import os
import re
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.rag_tool import RAGTool
from core.logger import LoggerManager

logger = LoggerManager.get_logger("semantic_evaluator")


@dataclass
class SemanticMetrics:
    """语义评测指标"""
    # 检索质量指标
    semantic_recall: float = 0.0          # 语义召回率
    semantic_precision: float = 0.0       # 语义准确率
    mrr: float = 0.0                      # 平均倒数排名
    ndcg: float = 0.0                     # 归一化折损累计增益

    # 幻觉检测指标
    hallucination_rate: float = 0.0       # 幻觉率
    contradiction_count: int = 0          # 矛盾数量

    # 缓存性能指标
    cache_hit_rate: float = 0.0           # 缓存命中率
    speedup_ratio: float = 0.0            # 加速比

    # 延迟指标
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'semantic_recall': round(self.semantic_recall, 4),
            'semantic_precision': round(self.semantic_precision, 4),
            'mrr': round(self.mrr, 4),
            'ndcg': round(self.ndcg, 4),
            'hallucination_rate': round(self.hallucination_rate, 4),
            'contradiction_count': self.contradiction_count,
            'cache_hit_rate': round(self.cache_hit_rate, 4),
            'speedup_ratio': round(self.speedup_ratio, 2),
            'avg_latency_ms': round(self.avg_latency_ms, 2),
            'p50_latency_ms': round(self.p50_latency_ms, 2),
            'p95_latency_ms': round(self.p95_latency_ms, 2),
        }


class SemanticEvaluator:
    """
    语义评测器 - 基于Embedding的评测方法

    解决原有关键词匹配评测的问题：
    1. 使用余弦相似度衡量语义相关性
    2. 支持查询-文档对的语义匹配
    3. 正确处理中文语义
    """

    # 同义词词典 - 用于扩展查询语义
    SYNONYMS = {
        # 产品相关
        '手机': ['手机', '智能手机', 'Phone', ' handset'],
        '耳机': ['耳机', '耳麦', 'Headphones', 'Earphones'],
        '电脑': ['电脑', '计算机', '笔记本', 'PC', 'Computer'],
        '平板': ['平板', '平板电脑', 'Pad', 'Tablet'],
        '手表': ['手表', '腕表', '智能手表', 'Watch'],

        # 属性相关
        '价格': ['价格', '多少钱', '售价', '费用', '报价', '元'],
        '便宜': ['便宜', '优惠', '实惠', '低价', '折扣', '促销'],
        '贵': ['贵', '昂贵', '高价', '豪华', '高端'],

        # 服务相关
        '退货': ['退货', '退款', '退换', '退'],
        '保修': ['保修', '质保', '售后', '维修', '保养'],
        '客服': ['客服', '服务', '售后', '咨询', '联系'],

        # 功能相关
        '防水': ['防水', '防潮', '防尘'],
        '续航': ['续航', '电池', '待机', '使用时间'],
        '拍照': ['拍照', '摄影', '相机', '镜头', '像素'],
    }

    # 合理的停用词 - 保留业务相关词
    STOPWORDS = {
        '的', '了', '和', '是', '在', '有', '我', '都', '个', '与', '也', '对',
        '能', '很', '可以', '就', '不', '会', '要', '没有', '到', '更', '让',
        '给', '上', '这', '他', '们', '来', '去', '把', '还', '但', '而', '或',
        '它', '她', '我们', '你们', '他们', '它们', '咱们', '大家', '人家',
        # 保留业务相关词：'怎么', '多少', '哪个', '什么' 等
    }

    def __init__(self, embedding_model=None):
        """
        初始化语义评测器

        Args:
            embedding_model: 可选，传入已有的embedding模型
        """
        self.embedding_model = embedding_model
        self._embedding_cache = {}  # 缓存embedding避免重复计算

    def _get_embedding(self, text: str) -> np.ndarray:
        """获取文本的embedding向量（带缓存）"""
        # 使用文本hash作为缓存key
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()[:16]

        if text_hash in self._embedding_cache:
            return self._embedding_cache[text_hash]

        # 如果没有传入模型，使用简单的字符级embedding作为fallback
        if self.embedding_model is None:
            # 简化的字符级embedding（用于测试）
            embedding = self._simple_char_embedding(text)
        else:
            # 使用真实的embedding模型
            try:
                embedding = np.array(self.embedding_model.encode(text))
            except Exception as e:
                logger.warning(f"Embedding模型调用失败，使用fallback: {e}")
                embedding = self._simple_char_embedding(text)

        self._embedding_cache[text_hash] = embedding
        return embedding

    def _simple_char_embedding(self, text: str, dim: int = 128) -> np.ndarray:
        """
        简化的字符级embedding（fallback方案）
        基于字符频率的哈希，用于无模型时的测试
        """
        embedding = np.zeros(dim)
        text = text.lower()

        # 字符哈希
        for i, char in enumerate(text):
            idx = (hash(char) + i * 31) % dim
            embedding[idx] += 1.0

        # 提取关键词特征
        # 提取产品型号（如 X12, X12Pro）
        products = re.findall(r'[a-zA-Z]\d+(?:\s*(?:pro|max|plus|air|mini|se))?', text)
        for prod in products:
            for j, char in enumerate(prod[:10]):
                idx = (hash(char) + j * 17) % dim
                embedding[idx] += 2.0  # 产品型号权重更高

        # 提取价格
        prices = re.findall(r'\d+\s*元', text)
        for price in prices[:3]:
            idx = hash('price') % dim
            embedding[idx] += float(re.findall(r'\d+', price)[0]) / 1000.0

        # L2归一化
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算两个向量的余弦相似度"""
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 * norm2 == 0:
            return 0.0

        return float(dot / (norm1 * norm2))

    def _extract_semantic_keywords(self, text: str) -> Set[str]:
        """
        提取语义关键词（改进版）

        改进点：
        1. 正确处理中文词汇
        2. 不过滤单字符（保留"元"等）
        3. 提取产品型号
        """
        keywords = set()
        text_lower = text.lower()

        # 1. 提取产品型号（如 X12, X12 Pro, X12Pro）
        product_models = re.findall(r'[a-zA-Z]\d+(?:\s*(?:pro|max|plus|air|mini|se))?', text_lower)
        for model in product_models:
            keywords.add(model.replace(' ', ''))  # 添加无空格版本
            keywords.add(model)  # 添加原始版本

        # 2. 提取中文词汇（2-4字词组）
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', text)
        for word in chinese_words:
            if word not in self.STOPWORDS:
                keywords.add(word)

        # 3. 提取数字（价格、型号等）
        numbers = re.findall(r'\d+', text)
        keywords.update(numbers)

        # 4. 提取英文单词（产品名、品牌等）
        english_words = re.findall(r'[a-zA-Z]{2,}', text_lower)
        keywords.update(english_words)

        # 5. 扩展同义词
        expanded_keywords = set()
        for kw in keywords:
            expanded_keywords.add(kw)
            # 查找同义词
            for key, synonyms in self.SYNONYMS.items():
                if kw in synonyms:
                    expanded_keywords.update(synonyms)

        return expanded_keywords

    def _is_semantically_relevant(self, query: str, doc_content: str, threshold: float = 0.3) -> Tuple[bool, float]:
        """
        判断文档是否与查询语义相关

        Args:
            query: 查询文本
            doc_content: 文档内容
            threshold: 相似度阈值

        Returns:
            (是否相关, 相似度分数)
        """
        # 方法1: Embedding相似度
        query_emb = self._get_embedding(query)
        doc_emb = self._get_embedding(doc_content[:500])  # 限制长度

        semantic_sim = self._cosine_similarity(query_emb, doc_emb)

        # 方法2: 关键词匹配度（作为辅助）
        query_keywords = self._extract_semantic_keywords(query)
        doc_keywords = self._extract_semantic_keywords(doc_content)

        if query_keywords:
            keyword_overlap = len(query_keywords & doc_keywords) / len(query_keywords)
        else:
            keyword_overlap = 0.0

        # 综合评分（语义为主）
        combined_score = semantic_sim * 0.7 + keyword_overlap * 0.3

        return combined_score > threshold, combined_score

    def _check_contradiction(self, docs: List[Dict]) -> List[Dict]:
        """
        检查文档间的矛盾（改进版）

        改进点：
        1. 区分不同产品的属性（不将不同产品的价格视为矛盾）
        2. 识别同一产品的冲突信息
        """
        contradictions = []

        if len(docs) < 2:
            return contradictions

        # 提取每个文档的产品和价格信息
        doc_info = []
        for doc in docs:
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})

            # 提取产品名称
            products = re.findall(r'产品名称[：:]\s*([^\n]+)', content)
            if not products:
                products = re.findall(r'[a-zA-Z]\d+(?:\s*(?:pro|max|plus|air|mini|se))?', content.lower())

            # 提取价格
            prices = re.findall(r'(\d+)\s*元', content)

            doc_info.append({
                'products': products,
                'prices': [int(p) for p in prices],
                'content': content[:200]
            })

        # 检查同一产品的价格矛盾
        for i in range(len(doc_info)):
            for j in range(i + 1, len(doc_info)):
                info1, info2 = doc_info[i], doc_info[j]

                # 判断是否为同一产品
                same_product = bool(
                    set(info1['products']) & set(info2['products'])
                )

                if same_product and info1['prices'] and info2['prices']:
                    # 同一产品的价格差异检查
                    for p1 in info1['prices']:
                        for p2 in info2['prices']:
                            if abs(p1 - p2) > 100:  # 同一产品价格差异>100元视为矛盾
                                contradictions.append({
                                    'type': 'price_contradiction',
                                    'product': list(set(info1['products']) & set(info2['products']))[0],
                                    'price1': p1,
                                    'price2': p2,
                                    'severity': 'high' if abs(p1 - p2) > 500 else 'medium'
                                })

        return contradictions

    def evaluate_retrieval_quality(
        self,
        rag_tool: RAGTool,
        test_cases: List[Dict],
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        评测检索质量（语义版）

        Args:
            rag_tool: RAG工具实例
            test_cases: 测试用例列表
            top_k: 检索数量

        Returns:
            评测结果字典
        """
        logger.info("=" * 80)
        logger.info("开始语义检索质量评测")
        logger.info("=" * 80)

        results = []
        all_relevances = []
        all_scores = []
        reciprocal_ranks = []

        for case in test_cases:
            query = case['query']
            expected_category = case.get('category', '')

            logger.info(f"\n评测查询: {query}")

            try:
                # 执行检索
                start_time = time.time()
                retrieval_result = rag_tool.retrieve(query, top_k=top_k, use_cache=False)
                latency_ms = (time.time() - start_time) * 1000

                docs = retrieval_result.get('documents', [])

                # 评估每个文档的语义相关性
                relevance_scores = []
                first_relevant_rank = None

                for rank, doc in enumerate(docs, 1):
                    content = doc.get('content', doc.get('page_content', ''))
                    is_relevant, score = self._is_semantically_relevant(query, content)

                    relevance_scores.append({
                        'rank': rank,
                        'is_relevant': is_relevant,
                        'score': score,
                        'content_preview': content[:100] + '...' if len(content) > 100 else content
                    })

                    if is_relevant and first_relevant_rank is None:
                        first_relevant_rank = rank

                    all_scores.append(score)

                # 计算MRR（平均倒数排名）
                if first_relevant_rank:
                    reciprocal_ranks.append(1.0 / first_relevant_rank)
                else:
                    reciprocal_ranks.append(0.0)

                # 计算该查询的指标
                relevant_count = sum(1 for r in relevance_scores if r['is_relevant'])
                recall = relevant_count / min(top_k, len(docs)) if docs else 0
                precision = relevant_count / len(docs) if docs else 0

                all_relevances.append({
                    'query': query,
                    'recall': recall,
                    'precision': precision,
                    'relevant_count': relevant_count,
                    'total_docs': len(docs),
                    'latency_ms': latency_ms,
                    'first_relevant_rank': first_relevant_rank,
                    'relevance_scores': relevance_scores
                })

                logger.info(f"  召回率: {recall:.2%}, 准确率: {precision:.2%}")
                logger.info(f"  延迟: {latency_ms:.1f}ms")

            except Exception as e:
                logger.error(f"  评测失败: {e}")
                all_relevances.append({
                    'query': query,
                    'recall': 0,
                    'precision': 0,
                    'error': str(e)
                })

        # 计算汇总指标
        recalls = [r['recall'] for r in all_relevances if 'recall' in r]
        precisions = [r['precision'] for r in all_relevances if 'precision' in r]
        latencies = [r['latency_ms'] for r in all_relevances if 'latency_ms' in r]

        metrics = {
            'total_queries': len(test_cases),
            'successful_queries': len([r for r in all_relevances if 'error' not in r]),

            # 语义召回率和准确率
            'semantic_recall': statistics.mean(recalls) if recalls else 0,
            'semantic_precision': statistics.mean(precisions) if precisions else 0,

            # MRR
            'mrr': statistics.mean(reciprocal_ranks) if reciprocal_ranks else 0,

            # 延迟统计
            'avg_latency_ms': statistics.mean(latencies) if latencies else 0,
            'p50_latency_ms': statistics.median(latencies) if latencies else 0,
            'p95_latency_ms': np.percentile(latencies, 95) if len(latencies) >= 2 else (latencies[0] if latencies else 0),

            # 详细结果
            'detailed_results': all_relevances
        }

        logger.info("\n" + "=" * 80)
        logger.info("检索质量评测完成")
        logger.info(f"  平均语义召回率: {metrics['semantic_recall']:.2%}")
        logger.info(f"  平均语义准确率: {metrics['semantic_precision']:.2%}")
        logger.info(f"  MRR: {metrics['mrr']:.4f}")
        logger.info(f"  平均延迟: {metrics['avg_latency_ms']:.1f}ms")

        return metrics

    def evaluate_hallucination(
        self,
        rag_tool: RAGTool,
        test_cases: List[Dict],
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        评测幻觉率（改进版）

        改进点：
        1. 正确处理多产品场景
        2. 识别真正的矛盾而非正常的价格差异
        """
        logger.info("=" * 80)
        logger.info("开始幻觉率评测（改进版）")
        logger.info("=" * 80)

        all_contradictions = []
        total_checks = 0

        for case in test_cases:
            query = case['query']

            try:
                retrieval_result = rag_tool.retrieve(query, top_k=top_k, use_cache=False)
                docs = retrieval_result.get('documents', [])

                # 检查矛盾
                contradictions = self._check_contradiction(docs)

                if contradictions:
                    logger.info(f"查询 '{query}' 发现 {len(contradictions)} 个矛盾:")
                    for c in contradictions:
                        logger.info(f"  - {c}")

                all_contradictions.extend([{
                    'query': query,
                    **c
                } for c in contradictions])

                total_checks += 1

            except Exception as e:
                logger.error(f"评测失败: {query}, 错误: {e}")

        # 计算幻觉率
        high_severity = sum(1 for c in all_contradictions if c.get('severity') == 'high')
        hallucination_rate = high_severity / max(total_checks, 1)

        metrics = {
            'total_checks': total_checks,
            'total_contradictions': len(all_contradictions),
            'high_severity_count': high_severity,
            'hallucination_rate': hallucination_rate,
            'contradictions_per_query': len(all_contradictions) / max(total_checks, 1),
            'detailed_contradictions': all_contradictions
        }

        logger.info("\n" + "=" * 80)
        logger.info("幻觉率评测完成")
        logger.info(f"  总矛盾数: {metrics['total_contradictions']}")
        logger.info(f"  高严重性矛盾: {metrics['high_severity_count']}")
        logger.info(f"  幻觉率: {metrics['hallucination_rate']:.2%}")

        return metrics

    def evaluate_cache_performance(
        self,
        rag_tool: RAGTool,
        test_queries: List[str],
        repeat_times: int = 5
    ) -> Dict[str, Any]:
        """
        评测缓存性能（修复版）

        修复点：
        1. 正确检测缓存命中
        2. 正确计算加速比
        3. 诊断缓存问题
        """
        logger.info("=" * 80)
        logger.info(f"开始缓存性能评测 (重复 {repeat_times} 次)")
        logger.info("=" * 80)

        # 首先清除缓存
        rag_tool.clear_cache()
        logger.info("缓存已清除")

        results = []
        cache_hits = 0
        cache_misses = 0
        first_latencies = []
        cached_latencies = []

        for query in test_queries:
            for i in range(repeat_times):
                start_time = time.time()
                try:
                    result = rag_tool.retrieve(query, top_k=3, use_cache=True)
                    # 检查结果是否来自缓存
                    is_from_cache = result.get('from_cache', False)
                except Exception as e:
                    logger.error(f"检索失败: {query}, 错误: {e}")
                    is_from_cache = False

                latency_ms = (time.time() - start_time) * 1000

                # 判断缓存命中（第1次是miss，后续如果快则视为hit）
                if i == 0:
                    first_latencies.append(latency_ms)
                    cache_misses += 1
                    is_hit = False
                else:
                    cached_latencies.append(latency_ms)
                    # 如果延迟显著低于首次，认为是缓存命中
                    is_hit = latency_ms < first_latencies[-1] * 0.8 if first_latencies else False
                    if is_hit:
                        cache_hits += 1
                    else:
                        cache_misses += 1

                results.append({
                    'query': query,
                    'attempt': i + 1,
                    'latency_ms': latency_ms,
                    'cache_hit': is_hit
                })

        # 计算指标
        total_requests = len(test_queries) * repeat_times
        cache_hit_rate = cache_hits / (total_requests - len(test_queries)) if (total_requests - len(test_queries)) > 0 else 0

        avg_first = statistics.mean(first_latencies) if first_latencies else 0
        avg_cached = statistics.mean(cached_latencies) if cached_latencies else 0
        speedup_ratio = avg_first / avg_cached if avg_cached > 0 else 1.0

        # 诊断缓存问题
        diagnosis = []
        if cache_hit_rate == 0:
            diagnosis.append("缓存命中率为0，可能原因：")
            diagnosis.append("  1. Redis未启动或配置错误")
            diagnosis.append("  2. 缓存key生成逻辑不一致")
            diagnosis.append("  3. 缓存TTL设置过短")
            diagnosis.append("  4. 每次检索生成不同的缓存key")

            # 检查缓存配置
            try:
                cache_stats = rag_tool.get_cache_stats()
                diagnosis.append(f"  缓存状态: {cache_stats}")
            except Exception as e:
                diagnosis.append(f"  获取缓存状态失败: {e}")

        metrics = {
            'total_requests': total_requests,
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'cache_hit_rate': cache_hit_rate,
            'avg_first_latency_ms': round(avg_first, 2),
            'avg_cached_latency_ms': round(avg_cached, 2),
            'speedup_ratio': round(speedup_ratio, 2),
            'diagnosis': diagnosis,
            'detailed_results': results
        }

        logger.info("\n" + "=" * 80)
        logger.info("缓存性能评测完成")
        logger.info(f"  缓存命中率: {metrics['cache_hit_rate']:.1%}")
        logger.info(f"  首次延迟: {metrics['avg_first_latency_ms']:.1f}ms")
        logger.info(f"  缓存命中延迟: {metrics['avg_cached_latency_ms']:.1f}ms")
        logger.info(f"  加速比: {metrics['speedup_ratio']:.2f}x")

        if diagnosis:
            for d in diagnosis:
                logger.info(f"  {d}")

        return metrics

    def run_full_evaluation(
        self,
        rag_tool: RAGTool,
        test_cases: List[Dict] = None,
        output_file: str = None
    ) -> Dict[str, Any]:
        """
        运行完整评测
        """
        logger.info("=" * 80)
        logger.info("语义评测系统 - 完整评测开始")
        logger.info("=" * 80)

        # 默认测试用例
        if test_cases is None:
            test_cases = [
                {"query": "X12 Pro手机多少钱", "category": "手机"},
                {"query": "X12 和 X12 Pro 有什么区别", "category": "手机"},
                {"query": "AirPad 平板电脑的价格", "category": "平板"},
                {"query": "蓝牙耳机推荐", "category": "耳机"},
                {"query": "智能手表哪个好", "category": "手表"},
                {"query": "游戏笔记本推荐", "category": "笔记本"},
                {"query": "怎么退货", "category": "售后"},
                {"query": "保修期多久", "category": "售后"},
                {"query": "降噪耳机推荐", "category": "耳机"},
                {"query": "最便宜的手机", "category": "手机"},
            ]

        all_results = {
            'timestamp': datetime.now().isoformat(),
            'total_test_cases': len(test_cases),
            'test_cases': test_cases
        }

        # 1. 评测检索质量
        logger.info("\n")
        retrieval_results = self.evaluate_retrieval_quality(rag_tool, test_cases)
        all_results['retrieval'] = retrieval_results

        # 2. 评测幻觉率
        logger.info("\n")
        hallucination_results = self.evaluate_hallucination(rag_tool, test_cases[:5])
        all_results['hallucination'] = hallucination_results

        # 3. 评测缓存性能
        logger.info("\n")
        test_queries = [case['query'] for case in test_cases[:3]]
        cache_results = self.evaluate_cache_performance(rag_tool, test_queries, repeat_times=5)
        all_results['cache'] = cache_results

        # 汇总
        all_results['summary'] = {
            'semantic_recall': retrieval_results.get('semantic_recall', 0),
            'semantic_precision': retrieval_results.get('semantic_precision', 0),
            'mrr': retrieval_results.get('mrr', 0),
            'hallucination_rate': hallucination_results.get('hallucination_rate', 0),
            'cache_hit_rate': cache_results.get('cache_hit_rate', 0),
            'speedup_ratio': cache_results.get('speedup_ratio', 1.0),
            'avg_latency_ms': retrieval_results.get('avg_latency_ms', 0),
            'p95_latency_ms': retrieval_results.get('p95_latency_ms', 0),
        }

        # 保存结果
        if output_file is None:
            output_file = f"semantic_evaluation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        logger.info(f"\n完整评测结果已保存到: {output_file}")

        return all_results


def main():
    """主函数"""
    print("=" * 80)
    print("语义评测系统")
    print("=" * 80)

    print("\n初始化 RAG 系统...")
    rag = RAGTool()

    print("\n初始化评测器...")
    evaluator = SemanticEvaluator()

    print("\n运行完整评测...")
    results = evaluator.run_full_evaluation(rag)

    # 打印摘要
    summary = results['summary']
    print("\n" + "=" * 80)
    print("评测摘要")
    print("=" * 80)
    print(f"  语义召回率: {summary['semantic_recall']:.2%}")
    print(f"  语义准确率: {summary['semantic_precision']:.2%}")
    print(f"  MRR: {summary['mrr']:.4f}")
    print(f"  幻觉率: {summary['hallucination_rate']:.2%}")
    print(f"  缓存命中率: {summary['cache_hit_rate']:.1%}")
    print(f"  加速比: {summary['speedup_ratio']:.2f}x")
    print(f"  平均延迟: {summary['avg_latency_ms']:.1f}ms")
    print(f"  P95延迟: {summary['p95_latency_ms']:.1f}ms")
    print("=" * 80)


if __name__ == "__main__":
    main()
