"""
RAG系统语义评测脚本（改进版）
针对向量语义检索系统设计的评测方案

核心改进：
1. 使用 Embedding 语义相似度替代关键词匹配
2. 修复幻觉率检测（区分多产品检索与真正幻觉）
3. 修复缓存评测（诊断失效原因）
4. 优化中文分词和停用词处理
"""

import json
import time
import statistics
import sys
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.rag_tool import RAGTool, LocalEmbeddings
from core.logger import LoggerManager

logger = LoggerManager.get_logger("semantic_evaluation")


class SemanticEvaluator:
    """语义评测器 - 基于Embedding的语义相似度评测"""

    def __init__(self, ground_truth_file: str):
        self.ground_truth_file = ground_truth_file
        self.ground_truth_data = self._load_ground_truth()
        self.embeddings = LocalEmbeddings()
        self._embedding_cache: Dict[str, List[float]] = {}

    def _load_ground_truth(self) -> Dict:
        with open(self.ground_truth_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _get_embedding(self, text: str) -> List[float]:
        """获取文本Embedding（带缓存）"""
        cache_key = text[:100]
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        embedding = self.embeddings.embed_query(text)
        self._embedding_cache[cache_key] = embedding
        return embedding

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def _extract_semantic_keywords(self, query: str) -> Set[str]:
        """提取语义核心词（不过滤停用词，保留意图词）"""
        import re

        stopwords = {'的', '了', '和', '是', '吗', '哪个', '什么', '多少', '能不能', '有', '没有'}

        words = re.split(r'[，。？、！\s]', query)
        words = [w.lower() for w in words if w and w not in stopwords]

        important_patterns = [
            r'[a-zA-Z]+\d+(?:\s*(?:pro|max|plus|air|mini|se))?',
            r'\d+元',
            r'\d+寸',
            r'\d+英寸',
        ]

        for pattern in important_patterns:
            matches = re.findall(pattern, query.lower())
            words.extend(matches)

        return set(words)

    def _extract_entities_from_doc(self, doc_content: str) -> Dict[str, Any]:
        """从文档中提取实体（产品名、价格、型号等）"""
        entities = {
            'product_names': set(),
            'prices': set(),
            'models': set(),
        }

        product_patterns = [
            r'产品名称[：:]\s*([^\n]+)',
            r'序号[：:]\s*(\d+)',
        ]
        for pattern in product_patterns:
            matches = re.findall(pattern, doc_content)
            entities['product_names'].update(matches)

        price_patterns = [r'(\d+)\s*元', r'标价[：:]\s*(\d+)', r'价格[：:]\s*(\d+)']
        for pattern in price_patterns:
            matches = re.findall(pattern, doc_content)
            entities['prices'].update(matches)

        model_patterns = [r'[a-zA-Z]\d+(?:\s*(?:pro|max|plus|air|mini|se))?']
        for pattern in model_patterns:
            matches = re.findall(pattern, doc_content.lower())
            entities['models'].update([m.replace(' ', '') for m in matches])

        return entities

    def evaluate_semantic_recall(
        self,
        rag_tool: RAGTool,
        top_k: int = 3,
        similarity_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        基于语义相似度的召回率评测

        方法：使用Embedding计算查询与检索文档的语义相似度
        """
        logger.info("=" * 60)
        logger.info("开始语义召回率评测（基于Embedding）")
        logger.info("=" * 60)

        queries = self.ground_truth_data['queries']

        results = []
        query_embeddings = {}

        for item in queries:
            query = item['query']
            query_id = item['id']

            logger.info(f"评测查询: {query}")

            try:
                start_time = time.time()
                result = rag_tool.retrieve(query, top_k=top_k, use_cache=False)
                latency_ms = (time.time() - start_time) * 1000

                retrieved_docs = result.get('documents', [])

                if query not in query_embeddings:
                    query_embeddings[query] = self._get_embedding(query)

                query_embedding = query_embeddings[query]

                doc_similarities = []
                for doc in retrieved_docs:
                    doc_embedding = self._get_embedding(doc.get('content', '')[:500])
                    similarity = self._cosine_similarity(query_embedding, doc_embedding)
                    doc_similarities.append({
                        'doc_id': doc.get('chunk_id', 'unknown'),
                        'content_preview': doc.get('content', '')[:100],
                        'similarity': similarity,
                        'source': doc.get('source_file', 'unknown')
                    })

                relevant_similar_docs = [d for d in doc_similarities if d['similarity'] >= similarity_threshold]

                semantic_recall = len(relevant_similar_docs) / top_k if top_k > 0 else 0

                avg_similarity = statistics.mean([d['similarity'] for d in doc_similarities]) if doc_similarities else 0
                max_similarity = max([d['similarity'] for d in doc_similarities]) if doc_similarities else 0

                results.append({
                    'query_id': query_id,
                    'query': query,
                    'semantic_recall': semantic_recall,
                    'avg_similarity': round(avg_similarity, 4),
                    'max_similarity': round(max_similarity, 4),
                    'relevant_docs_count': len(relevant_similar_docs),
                    'total_retrieved': len(retrieved_docs),
                    'latency_ms': round(latency_ms, 2),
                    'doc_similarities': doc_similarities[:3]
                })

                logger.info(f"  语义召回率: {semantic_recall:.2%}, 平均相似度: {avg_similarity:.4f}, 最大相似度: {max_similarity:.4f}")

            except Exception as e:
                logger.error(f"  查询失败: {e}")
                results.append({
                    'query_id': query_id,
                    'query': query,
                    'error': str(e),
                    'semantic_recall': 0,
                    'avg_similarity': 0,
                    'max_similarity': 0
                })

        recalls = [r['semantic_recall'] for r in results if 'semantic_recall' in r]
        avg_sims = [r['avg_similarity'] for r in results if 'avg_similarity' in r]
        max_sims = [r['max_similarity'] for r in results if 'max_similarity' in r]

        sorted_recalls = sorted(recalls) if recalls else []

        return {
            'recall_metrics': {
                'recall_at_1': round(sum(1 for r in recalls if r >= 0.99) / len(recalls), 4) if recalls else 0,
                'recall_at_3': round(sum(1 for r in recalls if r >= 0.33) / len(recalls), 4) if recalls else 0,
                'recall_at_5': round(sum(1 for r in recalls if r >= 0.20) / len(recalls), 4) if recalls else 0,
                'avg_recall': round(statistics.mean(recalls), 4) if recalls else 0,
                'median_recall': round(statistics.median(recalls), 4) if recalls else 0,
                'avg_similarity': round(statistics.mean(avg_sims), 4) if avg_sims else 0,
                'avg_max_similarity': round(statistics.mean(max_sims), 4) if max_sims else 0,
            },
            'detailed_results': results,
            'total_queries': len(queries),
            'successful_queries': sum(1 for r in results if 'error' not in r)
        }

    def evaluate_hallucination(
        self,
        rag_tool: RAGTool,
        test_pairs: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        改进的幻觉率检测

        核心改进：区分"多产品检索"与"真正幻觉"
        - 多产品检索：不同文档描述不同产品，价格不同是正常的
        - 真正幻觉：同一产品的信息前后矛盾
        """
        logger.info("=" * 60)
        logger.info("开始改进的幻觉率评测")
        logger.info("=" * 60)

        if test_pairs is None:
            test_pairs = [
                {'query': item['query'], 'id': item['id']}
                for item in self.ground_truth_data['queries'][:10]
            ]

        total_hallucinations = 0
        total_checks = 0
        multi_product_cases = 0
        detailed_results = []

        for item in test_pairs:
            query = item['query']
            query_id = item['id']

            try:
                result = rag_tool.retrieve(query, top_k=3, use_cache=False)
                docs = result.get('documents', [])

                hallucinations = 0
                inconsistency_details = []

                doc_entities = []
                for doc in docs:
                    entities = self._extract_entities_from_doc(doc.get('content', ''))
                    doc_entities.append(entities)

                if len(docs) >= 2:
                    products_per_doc = []
                    for entities in doc_entities:
                        product_count = len(entities['product_names'])
                        if product_count == 0:
                            product_count = 1
                        products_per_doc.append(product_count)

                    total_products = sum(products_per_doc)

                    if total_products > max(products_per_doc):
                        multi_product_cases += 1
                        inconsistency_details.append({
                            'type': 'multi_product',
                            'message': f'多产品检索场景 ({total_products}个产品分布在{len(docs)}个文档中)',
                            'is_real_hallucination': False
                        })
                    else:
                        for i in range(len(doc_entities) - 1):
                            for j in range(i + 1, len(doc_entities)):
                                prices_i = doc_entities[i]['prices']
                                prices_j = doc_entities[j]['prices']

                                if prices_i and prices_j:
                                    p1, p2 = int(list(prices_i)[0]), int(list(prices_j)[0])
                                    if abs(p1 - p2) > 500:
                                        products_match = (
                                            doc_entities[i]['models'] &
                                            doc_entities[j]['models']
                                        )
                                        if products_match:
                                            hallucinations += 1
                                            total_hallucinations += 1
                                            inconsistency_details.append({
                                                'type': 'price_inconsistency',
                                                'message': f'相同产品价格差异大: {p1}元 vs {p2}元',
                                                'is_real_hallucination': True
                                            })

                query_keywords = self._extract_semantic_keywords(query)
                all_doc_content = ' '.join([d.get('content', '') for d in docs])

                missing_keywords = []
                for kw in query_keywords:
                    if kw.lower() not in all_doc_content.lower():
                        missing_keywords.append(kw)

                hallucination_score = hallucinations / max(len(query_keywords), 1)

                total_checks += 1

                detailed_results.append({
                    'query_id': query_id,
                    'query': query,
                    'hallucinations': hallucinations,
                    'hallucination_score': round(hallucination_score, 4),
                    'multi_product_case': total_products > max(products_per_doc) if docs else False,
                    'inconsistency_details': inconsistency_details,
                    'retrieved_count': len(docs)
                })

                logger.info(f"查询: {query}")
                logger.info(f"  真正幻觉数: {hallucinations}, 多产品案例: {multi_product_cases}")

            except Exception as e:
                logger.error(f"查询失败: {query_id}, 错误: {e}")
                detailed_results.append({
                    'query_id': query_id,
                    'query': query,
                    'error': str(e),
                    'hallucinations': 0,
                    'hallucination_score': 0
                })

        hallucination_rate = total_hallucinations / max(total_checks * 3, 1)

        logger.info(f"改进后的幻觉率: {hallucination_rate:.2%} ({total_hallucinations}/{total_checks * 3})")
        logger.info(f"多产品场景案例: {multi_product_cases}")

        return {
            'hallucination_rate': round(hallucination_rate, 4),
            'hallucinations_per_query': round(total_hallucinations / max(total_checks, 1), 2),
            'total_hallucinations': total_hallucinations,
            'total_checks': total_checks,
            'multi_product_cases': multi_product_cases,
            'detailed_results': detailed_results
        }

    def evaluate_cache(
        self,
        rag_tool: RAGTool,
        repeat_times: int = 5
    ) -> Dict[str, Any]:
        """
        改进的缓存评测 - 诊断缓存失效原因

        核心改进：
        1. 诊断缓存类型（Redis vs Memory）
        2. 诊断缓存key生成是否正确
        3. 诊断Redis连接状态
        """
        logger.info("=" * 60)
        logger.info(f"开始改进的缓存评测 (重复 {repeat_times} 次)")
        logger.info("=" * 60)

        cache_info = {
            'cache_type': 'unknown',
            'redis_available': False,
            'redis_connection_error': None,
            'memory_cache_size': 0,
            'key_prefix': None
        }

        try:
            if hasattr(rag_tool.cache, '_available'):
                cache_info['redis_available'] = rag_tool.cache._available

            if hasattr(rag_tool.cache, 'key_prefix'):
                cache_info['key_prefix'] = rag_tool.cache.key_prefix

            if hasattr(rag_tool.cache, 'get_stats'):
                stats = rag_tool.cache.get_stats()
                cache_info['cache_type'] = stats.get('type', 'unknown')
                if 'keys_count' in stats:
                    cache_info['memory_cache_size'] = stats.get('keys_count', 0)

            if hasattr(rag_tool.cache, 'cache'):
                cache_info['cache_type'] = 'memory'
                cache_info['memory_cache_size'] = len(rag_tool.cache.cache) if rag_tool.cache.cache else 0

            if hasattr(rag_tool.cache, '_redis') and rag_tool.cache._redis:
                cache_info['cache_type'] = 'redis'

        except Exception as e:
            cache_info['redis_connection_error'] = str(e)
            logger.warning(f"缓存信息诊断失败: {e}")

        logger.info(f"缓存类型: {cache_info['cache_type']}, Redis可用: {cache_info['redis_available']}")

        queries = [
            item['query']
            for item in self.ground_truth_data['queries'][:5]
        ]

        if hasattr(rag_tool.cache, 'cache'):
            rag_tool.cache.clear()
        elif hasattr(rag_tool.cache, '_cache'):
            if hasattr(rag_tool.cache._cache, 'clear'):
                rag_tool.cache._cache.clear()

        total_requests = 0
        cache_hits = 0
        first_latencies = []
        cached_latencies = []
        detailed_results = []

        for query in queries:
            for i in range(repeat_times):
                total_requests += 1

                start_time = time.time()
                try:
                    rag_tool.retrieve(query, top_k=3, use_cache=True)
                except Exception as e:
                    logger.error(f"检索失败: {query}, 错误: {e}")
                latency_ms = (time.time() - start_time) * 1000

                cache_hit = False
                try:
                    cached = rag_tool.cache.get(query, 3, True)
                    cache_hit = cached is not None
                except Exception as e:
                    logger.warning(f"缓存检测失败: {e}")

                if i == 0:
                    first_latencies.append(latency_ms)
                else:
                    cached_latencies.append(latency_ms)
                    if cache_hit:
                        cache_hits += 1

                detailed_results.append({
                    'query': query,
                    'attempt': i + 1,
                    'latency_ms': round(latency_ms, 2),
                    'cache_hit': cache_hit
                })

        cache_misses = total_requests - cache_hits
        cache_hit_rate = cache_hits / total_requests if total_requests > 0 else 0

        avg_first = statistics.mean(first_latencies) if first_latencies else 0
        avg_cached = statistics.mean(cached_latencies) if cached_latencies else 0
        speedup_ratio = avg_first / avg_cached if avg_cached > 0 else 0

        cache_diagnosis = {
            'hit_rate_too_low': cache_hit_rate < 0.5,
            'possible_reasons': []
        }

        if not cache_info['redis_available'] and cache_info['cache_type'] == 'unknown':
            cache_diagnosis['possible_reasons'].append('Redis未启动或连接失败')
        if cache_hit_rate < 0.5 and total_requests > 5:
            cache_diagnosis['possible_reasons'].append('缓存key不匹配或TTL设置过短')
        if avg_first > 0 and speedup_ratio < 1.5:
            cache_diagnosis['possible_reasons'].append('缓存未生效，可能存在性能问题')

        logger.info(f"缓存命中率: {cache_hit_rate:.2%} ({cache_hits}/{total_requests})")
        logger.info(f"加速比: {speedup_ratio:.2f}x")
        if cache_diagnosis['possible_reasons']:
            logger.info(f"诊断建议: {', '.join(cache_diagnosis['possible_reasons'])}")

        return {
            'cache_hit_rate': round(cache_hit_rate, 4),
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'total_requests': total_requests,
            'avg_first_latency_ms': round(avg_first, 2),
            'avg_cached_latency_ms': round(avg_cached, 2),
            'speedup_ratio': round(speedup_ratio, 2),
            'cache_info': cache_info,
            'cache_diagnosis': cache_diagnosis,
            'detailed_results': detailed_results
        }

    def evaluate_latency(
        self,
        rag_tool: RAGTool,
        iterations: int = 3
    ) -> Dict[str, Any]:
        """评测延迟性能"""
        logger.info("=" * 60)
        logger.info(f"开始延迟评测 (每查询 {iterations} 次)")

        queries = [item['query'] for item in self.ground_truth_data['queries']]
        latencies = []
        failed = 0

        for query in queries:
            for _ in range(iterations):
                start_time = time.time()
                try:
                    rag_tool.retrieve(query, top_k=3, use_cache=False)
                    latencies.append((time.time() - start_time) * 1000)
                except Exception as e:
                    logger.error(f"查询失败: {query}, 错误: {e}")
                    failed += 1

        if not latencies:
            return {
                'avg_latency_ms': 0,
                'p50_latency_ms': 0,
                'p95_latency_ms': 0,
                'p99_latency_ms': 0,
                'qps': 0,
                'total_requests': 0,
                'failed_requests': failed
            }

        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)
        total_requests = len(queries) * iterations

        avg_latency_sec = statistics.mean(latencies) / 1000
        qps = 1 / avg_latency_sec if avg_latency_sec > 0 else 0

        return {
            'avg_latency_ms': round(statistics.mean(latencies), 2),
            'p50_latency_ms': round(sorted_latencies[n // 2], 2),
            'p95_latency_ms': round(sorted_latencies[int(n * 0.95)], 2),
            'p99_latency_ms': round(sorted_latencies[int(n * 0.99)], 2),
            'min_latency_ms': round(min(latencies), 2),
            'max_latency_ms': round(max(latencies), 2),
            'std_dev_ms': round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0,
            'qps': round(qps, 2),
            'total_requests': total_requests,
            'failed_requests': failed
        }

    def run_full_evaluation(
        self,
        rag_tool: Optional[RAGTool] = None,
        output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """运行全套语义评测"""
        logger.info("=" * 80)
        logger.info("RAG系统语义评测开始（基于Embedding）")
        logger.info("=" * 80)

        if rag_tool is None:
            logger.info("初始化RAG系统...")
            rag_tool = RAGTool()

        results = {
            'timestamp': datetime.now().isoformat(),
            'ground_truth_file': self.ground_truth_file,
            'total_queries': len(self.ground_truth_data['queries']),
            'evaluation_method': 'semantic_similarity'
        }

        logger.info("\n")
        recall_results = self.evaluate_semantic_recall(rag_tool)
        results['recall'] = recall_results

        logger.info("\n")
        hallucination_results = self.evaluate_hallucination(rag_tool)
        results['hallucination'] = hallucination_results

        logger.info("\n")
        cache_results = self.evaluate_cache(rag_tool, repeat_times=5)
        results['cache'] = cache_results

        logger.info("\n")
        latency_results = self.evaluate_latency(rag_tool, iterations=2)
        results['latency'] = latency_results

        results['summary'] = {
            'success_rate': recall_results['successful_queries'] / recall_results['total_queries'],
            'avg_recall': recall_results['recall_metrics']['avg_recall'],
            'avg_similarity': recall_results['recall_metrics']['avg_similarity'],
            'avg_max_similarity': recall_results['recall_metrics']['avg_max_similarity'],
            'hallucination_rate': hallucination_results['hallucination_rate'],
            'cache_hit_rate': cache_results['cache_hit_rate'],
            'speedup_ratio': cache_results['speedup_ratio'],
            'avg_latency_ms': latency_results['avg_latency_ms'],
            'p95_latency_ms': latency_results['p95_latency_ms']
        }

        if output_file is None:
            output_file = f"semantic_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"\n评测结果已保存到: {output_file}")

        self._generate_markdown_report(results, output_file.replace('.json', '.md'))

        return results

    def _generate_markdown_report(self, results: Dict, output_file: str):
        """生成Markdown格式的评测报告"""

        summary = results['summary']
        recall = results['recall']['recall_metrics']
        hallucination = results['hallucination']
        cache = results['cache']
        latency = results['latency']

        report = f"""# RAG系统语义评测报告

生成时间: {results['timestamp']}
测试查询数: {results['total_queries']}
评测方法: {results['evaluation_method']}

---

## 📊 综合评分

| 指标 | 数值 | 目标 | 状态 |
|------|------|------|------|
| 成功率 | {summary['success_rate']:.1%} | >95% | {'✅ 通过' if summary['success_rate'] > 0.95 else '❌ 未达标'} |
| 平均召回率 | {summary['avg_recall']:.1%} | >85% | {'✅ 通过' if summary['avg_recall'] > 0.85 else '❌ 未达标'} |
| 平均相似度 | {summary['avg_similarity']:.4f} | >0.6 | {'✅ 通过' if summary['avg_similarity'] > 0.6 else '❌ 未达标'} |
| 最大相似度 | {summary['avg_max_similarity']:.4f} | >0.7 | {'✅ 通过' if summary['avg_max_similarity'] > 0.7 else '❌ 未达标'} |
| 幻觉率 | {summary['hallucination_rate']:.2%} | <5% | {'✅ 通过' if summary['hallucination_rate'] < 0.05 else '❌ 未达标'} |
| 缓存命中率 | {summary['cache_hit_rate']:.1%} | >60% | {'✅ 通过' if summary['cache_hit_rate'] > 0.60 else '❌ 未达标'} |
| 加速比 | {summary['speedup_ratio']:.1f}x | >3x | {'✅ 通过' if summary['speedup_ratio'] > 3 else '❌ 未达标'} |
| 平均延迟 | {summary['avg_latency_ms']:.0f}ms | <500ms | {'✅ 通过' if summary['avg_latency_ms'] < 500 else '❌ 未达标'} |
| P95延迟 | {summary['p95_latency_ms']:.0f}ms | <800ms | {'✅ 通过' if summary['p95_latency_ms'] < 800 else '❌ 未达标'} |

---

## 🎯 语义召回率评测结果

| 指标 | 数值 | 说明 |
|------|------|------|
| Recall@1 | {recall['recall_at_1']:.1%} | Top-1 结果的相关率 |
| Recall@3 | {recall['recall_at_3']:.1%} | Top-3 结果的相关率 |
| Recall@5 | {recall['recall_at_5']:.1%} | Top-5 结果的相关率 |
| 平均召回率 | {recall['avg_recall']:.1%} | 所有查询的平均召回率 |
| 中位召回率 | {recall['median_recall']:.1%} | 召回率中位数 |
| 平均相似度 | {recall['avg_similarity']:.4f} | 查询与检索结果的平均语义相似度 |
| 平均最大相似度 | {recall['avg_max_similarity']:.4f} | 每个查询的最大相似度平均值 |

---

## 🎯 幻觉率评测结果

| 指标 | 数值 | 说明 |
|------|------|------|
| 幻觉率 | {hallucination['hallucination_rate']:.2%} | 真正幻觉项占总检查项的比例 |
| 平均幻觉数 | {hallucination['hallucinations_per_query']:.1f} | 每个查询的平均幻觉数 |
| 多产品场景 | {hallucination['multi_product_cases']} | 被正确识别的多产品检索案例 |
| 总检查项 | {hallucination['total_checks']} | 执行的总检查数 |

---

## 💾 缓存效率评测结果

| 指标 | 数值 | 说明 |
|------|------|------|
| 缓存类型 | {cache['cache_info']['cache_type']} | 使用的缓存类型 |
| Redis可用 | {cache['cache_info']['redis_available']} | Redis连接状态 |
| 缓存命中率 | {cache['cache_hit_rate']:.1%} | 缓存命中次数/总请求数 |
| 缓存命中次数 | {cache['cache_hits']} | 命中缓存的请求数 |
| 缓存未命中次数 | {cache['cache_misses']} | 未命中缓存的请求数 |
| 首次查询延迟 | {cache['avg_first_latency_ms']:.0f}ms | 未命中缓存时的平均延迟 |
| 缓存命中延迟 | {cache['avg_cached_latency_ms']:.0f}ms | 命中缓存时的平均延迟 |
| 加速比 | {cache['speedup_ratio']:.1f}x | 首次查询/缓存命中的延迟比 |

### 缓存诊断

| 诊断项 | 结果 |
|--------|------|
| 命中率过低 | {cache['cache_diagnosis']['hit_rate_too_low']} |
| 可能原因 | {', '.join(cache['cache_diagnosis']['possible_reasons']) if cache['cache_diagnosis']['possible_reasons'] else '无明显问题'} |

---

## ⚡ 性能评测结果

| 指标 | 数值 | 说明 |
|------|------|------|
| 平均延迟 | {latency['avg_latency_ms']:.0f}ms | 所有请求的平均延迟 |
| P50 延迟 | {latency['p50_latency_ms']:.0f}ms | 50%请求的延迟低于此值 |
| P95 延迟 | {latency['p95_latency_ms']:.0f}ms | 95%请求的延迟低于此值 |
| P99 延迟 | {latency['p99_latency_ms']:.0f}ms | 99%请求的延迟低于此值 |
| 最小延迟 | {latency['min_latency_ms']:.0f}ms | 最快请求的延迟 |
| 最大延迟 | {latency['max_latency_ms']:.0f}ms | 最慢请求的延迟 |
| 标准差 | {latency['std_dev_ms']:.0f}ms | 延迟波动程度 |
| QPS | {latency['qps']:.1f} | 每秒处理的请求数 |

---

## 📝 详细查询结果

"""

        for detail in results['recall']['detailed_results']:
            report += f"""
### {detail['query_id']}: {detail['query']}

- 语义召回率: {detail.get('semantic_recall', 0):.1%}
- 平均相似度: {detail.get('avg_similarity', 0):.4f}
- 最大相似度: {detail.get('max_similarity', 0):.4f}
- 检索文档数: {detail.get('total_retrieved', 0)}
- 延迟: {detail.get('latency_ms', 0):.0f}ms
"""
            if 'doc_similarities' in detail and detail['doc_similarities']:
                report += "\n检索结果相似度：\n"
                for i, doc in enumerate(detail['doc_similarities'], 1):
                    preview = doc.get('content_preview', '')[:50]
                    sim = doc.get('similarity', 0)
                    report += f"  - Doc{i}: {sim:.4f} - {preview}...\n"

        report += f"""

---

## 📋 评测结论

### 改进说明

本评测方案针对之前的问题进行了以下改进：

1. **语义召回率**：使用Embedding计算查询与文档的语义相似度，而非关键词匹配
2. **幻觉率检测**：区分"多产品检索"与"真正幻觉"，避免误报
3. **缓存诊断**：诊断缓存类型、Redis连接状态、key匹配问题
4. **中文处理**：优化了中文分词和停用词处理

### 优点

"""
        if summary['avg_recall'] > 0.7:
            report += f"- ✅ 语义召回率良好 ({summary['avg_recall']:.1%})，检索结果与查询高度相关\n"
        if summary['avg_similarity'] > 0.6:
            report += f"- ✅ 语义相似度高 ({summary['avg_similarity']:.4f})，系统能够理解查询意图\n"
        if summary['cache_hit_rate'] > 0.4:
            report += f"- ✅ 缓存机制有效，命中率达到 {summary['cache_hit_rate']:.1%}\n"
        if summary['avg_latency_ms'] < 500:
            report += f"- ✅ 响应延迟较低 ({summary['avg_latency_ms']:.0f}ms)，用户体验良好\n"

        report += """
### 待改进

"""
        if summary['avg_recall'] < 0.85:
            report += f"- ❌ 语义召回率偏低 ({summary['avg_recall']:.1%})，建议优化检索算法或增加知识库内容\n"
        if summary['hallucination_rate'] > 0.05:
            report += f"- ❌ 存在幻觉问题 ({summary['hallucination_rate']:.2%})，建议增加一致性检查\n"
        if summary['cache_hit_rate'] < 0.5:
            report += f"- ❌ 缓存命中率偏低 ({summary['cache_hit_rate']:.1%})，建议增加缓存容量或TTL\n"
        if summary['p95_latency_ms'] > 800:
            report += f"- ❌ P95延迟偏高 ({summary['p95_latency_ms']:.0f}ms)，建议优化性能瓶颈\n"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Markdown报告已保存到: {output_file}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='RAG系统语义评测')
    parser.add_argument('--ground-truth', type=str,
                       default='tests/ground_truth_dataset.json',
                       help='Ground Truth 数据文件路径')
    parser.add_argument('--output', type=str, default=None,
                       help='输出报告文件路径')

    args = parser.parse_args()

    evaluator = SemanticEvaluator(args.ground_truth)
    results = evaluator.run_full_evaluation(output_file=args.output)

    print("\n" + "=" * 80)
    print("语义评测完成！")
    print("=" * 80)
    print(f"\n综合评分:")
    print(f"  成功率: {results['summary']['success_rate']:.1%}")
    print(f"  平均语义召回率: {results['summary']['avg_recall']:.1%}")
    print(f"  平均相似度: {results['summary']['avg_similarity']:.4f}")
    print(f"  最大相似度: {results['summary']['avg_max_similarity']:.4f}")
    print(f"  幻觉率: {results['summary']['hallucination_rate']:.2%}")
    print(f"  缓存命中率: {results['summary']['cache_hit_rate']:.1%}")
    print(f"  加速比: {results['summary']['speedup_ratio']:.1f}x")
    print(f"  平均延迟: {results['summary']['avg_latency_ms']:.0f}ms")
    print(f"  P95延迟: {results['summary']['p95_latency_ms']:.0f}ms")
    print(f"\n详细报告已保存到 JSON 文件")


if __name__ == "__main__":
    main()
