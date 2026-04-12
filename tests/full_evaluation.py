"""
RAG系统全套评测脚本
包含：召回率、准确率、幻觉率、缓存命中率、延迟测试
"""

import json
import time
import statistics
import sys
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.rag_tool import RAGTool
from core.logger import LoggerManager

logger = LoggerManager.get_logger("full_evaluation")


@dataclass
class EvaluationMetrics:
    """评测指标数据类"""
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    avg_recall: float
    median_recall: float
    
    precision_at_1: float
    precision_at_3: float
    precision_at_5: float
    avg_precision: float
    
    hallucination_rate: float
    hallucination_per_1000_chars: float
    hallucination_count: int
    
    cache_hit_rate: float
    cache_hits: int
    cache_misses: int
    speedup_ratio: float
    
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    qps: float
    
    success_rate: float
    total_tests: int


class FullEvaluation:
    """全套评测类"""
    
    def __init__(self, ground_truth_file: str):
        self.ground_truth_file = ground_truth_file
        self.ground_truth_data = self._load_ground_truth()
        self.results = {}
        
    def _load_ground_truth(self) -> Dict:
        """加载 Ground Truth 数据"""
        with open(self.ground_truth_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def evaluate_recall_and_precision(
        self,
        rag_tool: RAGTool,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        评测召回率和准确率
        
        使用关键词匹配代替文档ID匹配（因为文档ID是动态生成的）
        """
        logger.info("=" * 60)
        logger.info("开始评测召回率和准确率")
        logger.info("=" * 60)
        
        queries = self.ground_truth_data['queries']
        
        recalls = []
        precisions = []
        keyword_match_rates = []
        detailed_results = []
        
        for item in queries:
            query = item['query']
            relevant_keywords = self._extract_keywords(query)
            
            logger.info(f"评测查询: {query}")
            
            try:
                start_time = time.time()
                result = rag_tool.retrieve(query, top_k=top_k)
                latency_ms = (time.time() - start_time) * 1000
                
                retrieved_docs = result.get('documents', [])
                
                # 提取检索文档中的关键词
                retrieved_keywords = self._extract_keywords_from_docs(retrieved_docs)
                
                # 计算召回率（基于关键词）
                matched_keywords = relevant_keywords & retrieved_keywords
                keyword_recall = len(matched_keywords) / len(relevant_keywords) if relevant_keywords else 0
                recalls.append(keyword_recall)
                
                # 计算准确率（检索文档中包含的相关关键词比例）
                keyword_precision = len(matched_keywords) / len(retrieved_keywords) if retrieved_keywords else 0
                precisions.append(keyword_precision)
                
                # 关键词匹配率
                match_rate = len(matched_keywords) / max(len(relevant_keywords), 1)
                keyword_match_rates.append(match_rate)
                
                # 检查是否命中缓存
                cache_hit = hasattr(rag_tool.cache, '_cache') and hasattr(rag_tool.cache, 'get')
                try:
                    cached = rag_tool.cache.get(query, top_k, True)
                    cache_hit = cached is not None
                except:
                    cache_hit = False
                
                detailed_results.append({
                    'query_id': item['id'],
                    'query': query,
                    'relevant_keywords': list(relevant_keywords),
                    'retrieved_keywords': list(retrieved_keywords),
                    'matched_keywords': list(matched_keywords),
                    'keyword_recall': round(keyword_recall, 4),
                    'keyword_precision': round(keyword_precision, 4),
                    'retrieved_count': len(retrieved_docs),
                    'latency_ms': round(latency_ms, 2),
                    'cache_hit': cache_hit
                })
                
                logger.info(f"  召回率: {keyword_recall:.2%}, 准确率: {keyword_precision:.2%}")
                logger.info(f"  匹配关键词: {matched_keywords}")
                
            except Exception as e:
                logger.error(f"  查询失败: {e}")
                recalls.append(0)
                precisions.append(0)
                keyword_match_rates.append(0)
                detailed_results.append({
                    'query_id': item['id'],
                    'query': query,
                    'error': str(e),
                    'keyword_recall': 0,
                    'keyword_precision': 0
                })
        
        # 计算统计指标
        sorted_recalls = sorted(recalls)
        sorted_precisions = sorted(precisions)
        n = len(sorted_recalls)
        
        return {
            'recall_metrics': {
                'recall_at_1': round(sum(1 for r in recalls if r >= 0.99) / len(recalls), 4) if recalls else 0,
                'recall_at_3': round(sum(1 for r in recalls if r >= 0.33) / len(recalls), 4) if recalls else 0,
                'avg_recall': round(statistics.mean(recalls), 4) if recalls else 0,
                'median_recall': round(statistics.median(recalls), 4) if recalls else 0,
                'p95_recall': round(sorted_recalls[int(n * 0.95)], 4) if recalls and n > 0 else 0,
            },
            'precision_metrics': {
                'precision_at_1': round(sorted_precisions[0], 4) if sorted_precisions else 0,
                'precision_at_3': round(statistics.mean(precisions), 4) if precisions else 0,
                'avg_keyword_match_rate': round(statistics.mean(keyword_match_rates), 4) if keyword_match_rates else 0,
            },
            'detailed_results': detailed_results,
            'total_queries': len(queries),
            'successful_queries': sum(1 for r in recalls if r > 0)
        }
    
    def _extract_keywords(self, query: str) -> Set[str]:
        """从查询中提取关键词"""
        # 移除常见停用词
        stopwords = {'的', '了', '和', '是', '吗', '怎么', '哪个', '什么', '多少', '能不能', '有', '没有'}
        
        # 简单分词（按标点和空格）
        words = re.split(r'[，。？、！\s]', query)
        words = [w.lower() for w in words if w and w not in stopwords and len(w) > 1]
        
        return set(words)
    
    def _extract_keywords_from_docs(self, docs: List[Dict]) -> Set[str]:
        """从检索文档中提取关键词"""
        all_text = ""
        for doc in docs:
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            if isinstance(metadata, dict):
                source = metadata.get('source', '')
            else:
                source = str(metadata)
            all_text += content + source
        
        # 提取数字（价格、型号等）
        numbers = set(re.findall(r'\d+', all_text))
        
        # 提取英文单词（产品名、型号等）
        english = set(re.findall(r'[a-zA-Z]+', all_text.lower()))
        
        # 提取中文词组
        chinese_words = set()
        for match in re.finditer(r'[\u4e00-\u9fa5]{2,}', all_text):
            word = match.group()
            if len(word) <= 6:  # 排除过长的匹配
                chinese_words.add(word.lower())
        
        return numbers | english | chinese_words
    
    def evaluate_hallucination(
        self,
        rag_tool: RAGTool,
        test_pairs: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        评测幻觉率
        
        方法：基于检索结果与查询的一致性检测
        - 检查检索文档中是否包含查询关键词
        - 检查检索文档之间是否一致
        """
        logger.info("=" * 60)
        logger.info("开始评测幻觉率")
        logger.info("=" * 60)
        
        if test_pairs is None:
            # 使用 Ground Truth 中的查询
            test_pairs = [
                {'query': item['query'], 'id': item['id']}
                for item in self.ground_truth_data['queries'][:10]
            ]
        
        total_inconsistencies = 0
        total_checks = 0
        detailed_results = []
        
        for item in test_pairs:
            query = item['query']
            query_id = item['id']
            
            try:
                result = rag_tool.retrieve(query, top_k=3)
                docs = result.get('documents', [])
                
                inconsistencies = 0
                
                # 检查1：检索文档是否包含查询关键词
                query_keywords = self._extract_keywords(query)
                doc_keywords = self._extract_keywords_from_docs(docs)
                
                missing_keywords = query_keywords - doc_keywords
                if missing_keywords:
                    inconsistencies += len(missing_keywords)
                
                # 检查2：文档间一致性（简单检查）
                if len(docs) >= 2:
                    for i in range(len(docs) - 1):
                        doc1_text = docs[i].get('content', '')
                        doc2_text = docs[i+1].get('content', '')
                        
                        # 检查价格一致性
                        prices1 = re.findall(r'(\d+)\s*元', doc1_text)
                        prices2 = re.findall(r'(\d+)\s*元', doc2_text)
                        
                        # 如果两个文档都有价格，检查是否一致（允许范围差异）
                        if prices1 and prices2:
                            p1, p2 = int(prices1[0]), int(prices2[0])
                            if abs(p1 - p2) > 500:  # 价格差异过大可能是幻觉
                                inconsistencies += 1
                
                total_inconsistencies += inconsistencies
                total_checks += 1
                
                hallucination_score = inconsistencies / max(len(query_keywords), 1)
                
                detailed_results.append({
                    'query_id': query_id,
                    'query': query,
                    'inconsistencies': inconsistencies,
                    'hallucination_score': round(hallucination_score, 4),
                    'retrieved_count': len(docs)
                })
                
                logger.info(f"查询: {query}")
                logger.info(f"  不一致项: {inconsistencies}, 幻觉分数: {hallucination_score:.2%}")
                
            except Exception as e:
                logger.error(f"查询失败: {query_id}, 错误: {e}")
                detailed_results.append({
                    'query_id': query_id,
                    'query': query,
                    'error': str(e),
                    'inconsistencies': 0,
                    'hallucination_score': 0
                })
        
        # 计算幻觉率
        hallucination_rate = total_inconsistencies / max(total_checks * 3, 1)  # 假设每个查询最多3个检查项
        
        return {
            'hallucination_rate': round(hallucination_rate, 4),
            'hallucinations_per_query': round(total_inconsistencies / max(total_checks, 1), 2),
            'total_inconsistencies': total_inconsistencies,
            'total_checks': total_checks,
            'detailed_results': detailed_results
        }
    
    def evaluate_cache_hit_rate(
        self,
        rag_tool: RAGTool,
        repeat_times: int = 5
    ) -> Dict[str, Any]:
        """
        评测缓存命中率
        """
        logger.info("=" * 60)
        logger.info(f"开始评测缓存命中率 (重复 {repeat_times} 次)")
        logger.info("=" * 60)
        
        queries = [
            item['query'] 
            for item in self.ground_truth_data['queries'][:5]
        ]
        
        # 清空缓存
        if hasattr(rag_tool.cache, 'cache'):
            rag_tool.cache.cache.clear()
        elif hasattr(rag_tool.cache, '_cache'):
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
                
                # 检测是否命中缓存
                cache_hit = False
                try:
                    cached = rag_tool.cache.get(query, 3, True)
                    cache_hit = cached is not None
                except:
                    pass
                
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
        
        logger.info(f"缓存命中率: {cache_hit_rate:.2%} ({cache_hits}/{total_requests})")
        logger.info(f"首次查询平均延迟: {avg_first:.2f}ms")
        logger.info(f"缓存命中平均延迟: {avg_cached:.2f}ms")
        logger.info(f"加速比: {speedup_ratio:.2f}x")
        
        return {
            'cache_hit_rate': round(cache_hit_rate, 4),
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'total_requests': total_requests,
            'avg_first_latency_ms': round(avg_first, 2),
            'avg_cached_latency_ms': round(avg_cached, 2),
            'speedup_ratio': round(speedup_ratio, 2),
            'detailed_results': detailed_results
        }
    
    def evaluate_latency(
        self,
        rag_tool: RAGTool,
        iterations: int = 3
    ) -> Dict[str, Any]:
        """
        评测延迟性能
        """
        logger.info("=" * 60)
        logger.info(f"开始评测延迟 (每查询 {iterations} 次)")
        logger.info("=" * 60)
        
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
        
        # 计算 QPS（简化）
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
        """
        运行全套评测
        """
        logger.info("=" * 80)
        logger.info("RAG系统全套评测开始")
        logger.info("=" * 80)
        
        if rag_tool is None:
            logger.info("初始化RAG系统...")
            rag_tool = RAGTool()
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'ground_truth_file': self.ground_truth_file,
            'total_queries': len(self.ground_truth_data['queries'])
        }
        
        # 1. 评测召回率和准确率
        logger.info("\n")
        recall_precision_results = self.evaluate_recall_and_precision(rag_tool)
        results['recall_precision'] = recall_precision_results
        
        # 2. 评测幻觉率
        logger.info("\n")
        hallucination_results = self.evaluate_hallucination(rag_tool)
        results['hallucination'] = hallucination_results
        
        # 3. 评测缓存命中率
        logger.info("\n")
        cache_results = self.evaluate_cache_hit_rate(rag_tool, repeat_times=5)
        results['cache'] = cache_results
        
        # 4. 评测延迟
        logger.info("\n")
        latency_results = self.evaluate_latency(rag_tool, iterations=2)
        results['latency'] = latency_results
        
        # 计算综合评分
        results['summary'] = {
            'success_rate': recall_precision_results['successful_queries'] / recall_precision_results['total_queries'],
            'avg_recall': recall_precision_results['recall_metrics']['avg_recall'],
            'avg_precision': recall_precision_results['precision_metrics']['precision_at_3'],
            'hallucination_rate': hallucination_results['hallucination_rate'],
            'cache_hit_rate': cache_results['cache_hit_rate'],
            'avg_latency_ms': latency_results['avg_latency_ms'],
            'p95_latency_ms': latency_results['p95_latency_ms']
        }
        
        # 保存结果
        if output_file is None:
            output_file = f"full_evaluation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n评测结果已保存到: {output_file}")
        
        # 生成 Markdown 报告
        self._generate_markdown_report(results, output_file.replace('.json', '.md'))
        
        return results
    
    def _generate_markdown_report(self, results: Dict, output_file: str):
        """生成 Markdown 格式的评测报告"""
        
        summary = results['summary']
        recall = results['recall_precision']['recall_metrics']
        precision = results['recall_precision']['precision_metrics']
        hallucination = results['hallucination']
        cache = results['cache']
        latency = results['latency']
        
        report = f"""# RAG系统全套评测报告

生成时间: {results['timestamp']}
测试查询数: {results['total_queries']}

---

## 📊 综合评分

| 指标 | 数值 | 目标 | 状态 |
|------|------|------|------|
| 成功率 | {summary['success_rate']:.1%} | >95% | {'✅ 通过' if summary['success_rate'] > 0.95 else '❌ 未达标'} |
| 平均召回率 | {summary['avg_recall']:.1%} | >85% | {'✅ 通过' if summary['avg_recall'] > 0.85 else '❌ 未达标'} |
| 平均准确率 | {summary['avg_precision']:.1%} | >80% | {'✅ 通过' if summary['avg_precision'] > 0.80 else '❌ 未达标'} |
| 幻觉率 | {summary['hallucination_rate']:.2%} | <5% | {'✅ 通过' if summary['hallucination_rate'] < 0.05 else '❌ 未达标'} |
| 缓存命中率 | {summary['cache_hit_rate']:.1%} | >60% | {'✅ 通过' if summary['cache_hit_rate'] > 0.60 else '❌ 未达标'} |
| 平均延迟 | {summary['avg_latency_ms']:.0f}ms | <500ms | {'✅ 通过' if summary['avg_latency_ms'] < 500 else '❌ 未达标'} |
| P95延迟 | {summary['p95_latency_ms']:.0f}ms | <800ms | {'✅ 通过' if summary['p95_latency_ms'] < 800 else '❌ 未达标'} |

---

## 🎯 召回率评测结果

| 指标 | 数值 | 说明 |
|------|------|------|
| Recall@1 | {recall['recall_at_1']:.1%} | Top-1 结果的相关率 |
| Recall@3 | {recall['recall_at_3']:.1%} | Top-3 结果的相关率 |
| 平均召回率 | {recall['avg_recall']:.1%} | 所有查询的平均召回率 |
| 中位召回率 | {recall['median_recall']:.1%} | 召回率中位数 |
| P95召回率 | {recall['p95_recall']:.1%} | 95%查询达到的召回率 |

---

## 🎯 准确率评测结果

| 指标 | 数值 | 说明 |
|------|------|------|
| Precision@1 | {precision['precision_at_1']:.1%} | Top-1 结果的准确率 |
| Precision@3 | {precision['precision_at_3']:.1%} | Top-3 结果的平均准确率 |
| 关键词匹配率 | {precision['avg_keyword_match_rate']:.1%} | 检索结果与查询的关键词匹配程度 |

---

## 🎯 幻觉率评测结果

| 指标 | 数值 | 说明 |
|------|------|------|
| 幻觉率 | {hallucination['hallucination_rate']:.2%} | 不一致项占总检查项的比例 |
| 平均不一致数 | {hallucination['hallucinations_per_query']:.1f} | 每个查询的平均不一致项 |
| 总不一致项 | {hallucination['total_inconsistencies']} | 检测到的总不一致项 |
| 总检查项 | {hallucination['total_checks']} | 执行的总检查数 |

---

## 💾 缓存效率评测结果

| 指标 | 数值 | 说明 |
|------|------|------|
| 缓存命中率 | {cache['cache_hit_rate']:.1%} | 缓存命中次数/总请求数 |
| 缓存命中次数 | {cache['cache_hits']} | 命中缓存的请求数 |
| 缓存未命中次数 | {cache['cache_misses']} | 未命中缓存的请求数 |
| 首次查询延迟 | {cache['avg_first_latency_ms']:.0f}ms | 未命中缓存时的平均延迟 |
| 缓存命中延迟 | {cache['avg_cached_latency_ms']:.0f}ms | 命中缓存时的平均延迟 |
| 加速比 | {cache['speedup_ratio']:.1f}x | 首次查询/缓存命中的延迟比 |

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
        
        # 添加详细查询结果
        for detail in results['recall_precision']['detailed_results']:
            report += f"""
### {detail['query_id']}: {detail['query']}

- 召回率: {detail.get('keyword_recall', 0):.1%}
- 准确率: {detail.get('keyword_precision', 0):.1%}
- 检索文档数: {detail.get('retrieved_count', 0)}
- 延迟: {detail.get('latency_ms', 0):.0f}ms
- 缓存: {'命中' if detail.get('cache_hit') else '未命中'}
"""
            if 'matched_keywords' in detail:
                report += f"- 匹配关键词: {', '.join(detail['matched_keywords'])}\n"
        
        report += f"""

---

## 📋 评测结论

### 优点

"""
        
        # 自动生成优点
        if summary['avg_recall'] > 0.7:
            report += f"- ✅ 检索召回率良好 ({summary['avg_recall']:.1%})，能够检索到相关文档\n"
        if summary['avg_precision'] > 0.6:
            report += f"- ✅ 检索准确率良好 ({summary['avg_precision']:.1%})，检索结果相关性高\n"
        if summary['cache_hit_rate'] > 0.4:
            report += f"- ✅ 缓存机制有效，命中率达到 {summary['cache_hit_rate']:.1%}\n"
        if summary['avg_latency_ms'] < 500:
            report += f"- ✅ 响应延迟较低 ({summary['avg_latency_ms']:.0f}ms)，用户体验良好\n"
        
        report += """
### 待改进

"""
        
        # 自动生成待改进项
        if summary['avg_recall'] < 0.85:
            report += f"- ❌ 召回率偏低 ({summary['avg_recall']:.1%})，建议优化检索算法或增加知识库内容\n"
        if summary['avg_precision'] < 0.8:
            report += f"- ❌ 准确率偏低 ({summary['avg_precision']:.1%})，建议优化重排序策略\n"
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
    
    parser = argparse.ArgumentParser(description='RAG系统全套评测')
    parser.add_argument('--ground-truth', type=str,
                       default='tests/ground_truth_dataset.json',
                       help='Ground Truth 数据文件路径')
    parser.add_argument('--output', type=str, default=None,
                       help='输出报告文件路径')
    
    args = parser.parse_args()
    
    evaluator = FullEvaluation(args.ground_truth)
    results = evaluator.run_full_evaluation(output_file=args.output)
    
    # 打印摘要
    print("\n" + "=" * 80)
    print("评测完成！")
    print("=" * 80)
    print(f"\n综合评分:")
    print(f"  成功率: {results['summary']['success_rate']:.1%}")
    print(f"  平均召回率: {results['summary']['avg_recall']:.1%}")
    print(f"  平均准确率: {results['summary']['avg_precision']:.1%}")
    print(f"  幻觉率: {results['summary']['hallucination_rate']:.2%}")
    print(f"  缓存命中率: {results['summary']['cache_hit_rate']:.1%}")
    print(f"  平均延迟: {results['summary']['avg_latency_ms']:.0f}ms")
    print(f"  P95延迟: {results['summary']['p95_latency_ms']:.0f}ms")
    print(f"\n详细报告已保存到 JSON 文件")


if __name__ == "__main__":
    main()
