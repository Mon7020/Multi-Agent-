"""
RAG系统基准测试脚本
用于量化评估系统的检索质量、性能和稳定性

测试指标:
- 检索质量: 召回率、准确率、F1分数、MRR
- 性能指标: 延迟(P50/P95/P99)、QPS、吞吐量
- 缓存效率: 命中率、预热时间
- 并发能力: 最大并发数、错误率
"""

import json
import time
import asyncio
import statistics
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.rag_tool import RAGTool
from core.logger import LoggerManager

logger = LoggerManager.get_logger("benchmark")


@dataclass
class RetrievalResult:
    """单次检索结果"""
    query_id: str
    query: str
    retrieved_docs: List[Dict[str, Any]]
    latency_ms: float
    cache_hit: bool
    timestamp: str


@dataclass
class QualityMetrics:
    """检索质量指标"""
    recall: float
    precision: float
    f1_score: float
    mrr: float
    ndcg: float


@dataclass
class PerformanceMetrics:
    """性能指标"""
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    std_dev_ms: float
    qps: float
    total_requests: int
    failed_requests: int


@dataclass
class CacheMetrics:
    """缓存指标"""
    hit_count: int
    miss_count: int
    hit_rate: float
    avg_hit_latency_ms: float
    avg_miss_latency_ms: float


@dataclass
class ConcurrencyMetrics:
    """并发测试指标"""
    max_concurrent: int
    success_count: int
    error_count: int
    error_rate: float
    throughput: float


class BenchmarkTestData:
    """测试数据加载器"""

    def __init__(self, data_file: str):
        self.data_file = data_file
        self.test_queries: List[Dict] = []
        self.edge_cases: List[Dict] = []
        self.targets: Dict[str, float] = {}
        self._load()

    def _load(self):
        """加载测试数据"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.test_queries = data.get('queries', [])
            self.edge_cases = data.get('edge_cases', [])
            self.targets = data.get('performance_targets', {})

            logger.info(f"加载测试数据: {len(self.test_queries)} 个标准查询, "
                       f"{len(self.edge_cases)} 个边界测试")
        except Exception as e:
            logger.error(f"加载测试数据失败: {e}")
            raise


class RetrievalQualityEvaluator:
    """检索质量评估器"""

    def __init__(self, top_k: int = 3):
        self.top_k = top_k

    def evaluate_single_query(
        self,
        retrieved_docs: List[Dict[str, Any]],
        expected_doc_ids: List[str],
        expected_keywords: List[str]
    ) -> Tuple[QualityMetrics, Dict[str, Any]]:
        """
        评估单个查询的检索质量

        Args:
            retrieved_docs: 检索返回的文档列表
            expected_doc_ids: 预期应该返回的文档ID列表
            expected_keywords: 预期应该包含的关键词列表

        Returns:
            质量指标和详细评估结果
        """
        retrieved_ids = [doc.get('doc_id', f"doc_{i}") for i, doc in enumerate(retrieved_docs)]

        relevant_set = set(expected_doc_ids)
        retrieved_set = set(retrieved_ids[:self.top_k])

        true_positives = len(relevant_set & retrieved_set)
        false_positives = len(retrieved_set - relevant_set)
        false_negatives = len(relevant_set - retrieved_set)

        recall = true_positives / len(relevant_set) if relevant_set else 0.0
        precision = true_positives / len(retrieved_set) if retrieved_set else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        mrr = self._calculate_mrr(retrieved_ids, relevant_set)

        ndcg = self._calculate_ndcg(
            retrieved_docs,
            expected_doc_ids,
            expected_keywords
        )

        keywords_found = self._check_keywords(retrieved_docs, expected_keywords)

        metrics = QualityMetrics(
            recall=round(recall, 4),
            precision=round(precision, 4),
            f1_score=round(f1, 4),
            mrr=round(mrr, 4),
            ndcg=round(ndcg, 4)
        )

        details = {
            'true_positives': true_positives,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'keywords_found': keywords_found,
            'keywords_total': len(expected_keywords)
        }

        return metrics, details

    def _calculate_mrr(self, retrieved_ids: List[str], relevant_set: set) -> float:
        """计算平均倒数排名 (Mean Reciprocal Rank)"""
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in relevant_set:
                return 1.0 / (i + 1)
        return 0.0

    def _calculate_ndcg(
        self,
        retrieved_docs: List[Dict[str, Any]],
        expected_ids: List[str],
        expected_keywords: List[str]
    ) -> float:
        """计算归一化折损累积增益 (NDCG)"""
        if not retrieved_docs or not expected_ids:
            return 0.0

        dcg = 0.0
        for i, doc in enumerate(retrieved_docs[:self.top_k]):
            doc_id = doc.get('doc_id', f"doc_{i}")
            relevance = 1.0 if doc_id in expected_ids else 0.0
            relevance += 0.5 if self._doc_contains_keywords(doc, expected_keywords) else 0.0
            dcg += relevance / (i + 1)

        ideal_dcg = sum([1.5 / (i + 1) for i in range(min(len(expected_ids), self.top_k))])

        return dcg / ideal_dcg if ideal_dcg > 0 else 0.0

    def _doc_contains_keywords(self, doc: Dict[str, Any], keywords: List[str]) -> bool:
        """检查文档是否包含关键词"""
        doc_text = (doc.get('content', '') + doc.get('text', '') +
                   doc.get('metadata', {}).get('description', '')).lower()
        return any(kw.lower() in doc_text for kw in keywords)

    def _check_keywords(
        self,
        retrieved_docs: List[Dict[str, Any]],
        expected_keywords: List[str]
    ) -> List[str]:
        """检查哪些关键词在检索结果中被找到"""
        found = []
        for kw in expected_keywords:
            for doc in retrieved_docs[:self.top_k]:
                doc_text = (doc.get('content', '') + doc.get('text', '') +
                           str(doc.get('metadata', {}))).lower()
                if kw.lower() in doc_text:
                    found.append(kw)
                    break
        return found


class PerformanceCollector:
    """性能指标收集器"""

    def __init__(self):
        self.latencies: List[float] = []
        self.cache_hits: List[bool] = []
        self.errors: List[str] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def record(self, latency_ms: float, cache_hit: bool, error: Optional[str] = None):
        """记录单次请求"""
        self.latencies.append(latency_ms)
        self.cache_hits.append(cache_hit)
        if error:
            self.errors.append(error)

    def calculate_metrics(self) -> PerformanceMetrics:
        """计算性能指标"""
        if not self.latencies:
            return PerformanceMetrics(
                avg_latency_ms=0, p50_latency_ms=0, p95_latency_ms=0, p99_latency_ms=0,
                min_latency_ms=0, max_latency_ms=0, std_dev_ms=0, qps=0,
                total_requests=0, failed_requests=0
            )

        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)

        duration = (self.end_time - self.start_time) if self.end_time and self.start_time else 1.0

        return PerformanceMetrics(
            avg_latency_ms=round(statistics.mean(self.latencies), 2),
            p50_latency_ms=round(sorted_latencies[n // 2], 2),
            p95_latency_ms=round(sorted_latencies[int(n * 0.95)], 2),
            p99_latency_ms=round(sorted_latencies[int(n * 0.99)], 2),
            min_latency_ms=round(min(self.latencies), 2),
            max_latency_ms=round(max(self.latencies), 2),
            std_dev_ms=round(statistics.stdev(self.latencies), 2) if len(self.latencies) > 1 else 0,
            qps=round(len(self.latencies) / duration, 2),
            total_requests=len(self.latencies),
            failed_requests=len(self.errors)
        )

    def calculate_cache_metrics(self) -> CacheMetrics:
        """计算缓存指标"""
        hits = sum(1 for h in self.cache_hits if h)
        misses = len(self.cache_hits) - hits

        hit_latencies = [self.latencies[i] for i, h in enumerate(self.cache_hits) if h]
        miss_latencies = [self.latencies[i] for i, h in enumerate(self.cache_hits) if not h]

        return CacheMetrics(
            hit_count=hits,
            miss_count=misses,
            hit_rate=round(hits / len(self.cache_hits), 4) if self.cache_hits else 0,
            avg_hit_latency_ms=round(statistics.mean(hit_latencies), 2) if hit_latencies else 0,
            avg_miss_latency_ms=round(statistics.mean(miss_latencies), 2) if miss_latencies else 0
        )


class RAGBenchmark:
    """RAG系统基准测试主类"""

    def __init__(self, data_file: str, top_k: int = 3):
        self.test_data = BenchmarkTestData(data_file)
        self.quality_evaluator = RetrievalQualityEvaluator(top_k)
        self.top_k = top_k
        self.results: List[RetrievalResult] = []
        self.perf_collector = PerformanceCollector()
        self.quality_results: List[Dict[str, Any]] = []

    def warmup_cache(self, rag_tool: RAGTool, warmup_queries: List[str]):
        """预热缓存"""
        logger.info(f"开始缓存预热，执行 {len(warmup_queries)} 次查询...")
        for query in warmup_queries:
            try:
                rag_tool.retrieve(query, top_k=self.top_k)
            except Exception as e:
                logger.warning(f"预热查询失败: {query}, 错误: {e}")
        logger.info("缓存预热完成")

    def run_single_query(self, rag_tool: RAGTool, query_item: Dict) -> Dict[str, Any]:
        """执行单个查询并评估"""
        query = query_item['query']
        query_id = query_item['id']
        expected_ids = query_item.get('expected_doc_ids', [])
        expected_keywords = query_item.get('expected_keywords', [])

        start_time = time.time()
        cache_hit = False

        try:
            retrieval_result = rag_tool.retrieve(query, top_k=self.top_k)
            retrieved_docs = retrieval_result.get("documents", []) if isinstance(retrieval_result, dict) else []
            cache_hit = hasattr(rag_tool, 'cache') and hasattr(rag_tool.cache, '_cache')

            latency_ms = (time.time() - start_time) * 1000

            result = RetrievalResult(
                query_id=query_id,
                query=query,
                retrieved_docs=retrieved_docs,
                latency_ms=latency_ms,
                cache_hit=cache_hit,
                timestamp=datetime.now().isoformat()
            )
            self.results.append(result)

            quality_metrics, quality_details = self.quality_evaluator.evaluate_single_query(
                retrieved_docs, expected_ids, expected_keywords
            )

            self.perf_collector.record(latency_ms, cache_hit)

            return {
                'query_id': query_id,
                'query': query,
                'quality_metrics': asdict(quality_metrics),
                'quality_details': quality_details,
                'latency_ms': latency_ms,
                'cache_hit': cache_hit,
                'retrieved_count': len(retrieved_docs)
            }

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self.perf_collector.record(latency_ms, False, str(e))
            logger.error(f"查询失败: {query_id}, 错误: {e}")

            return {
                'query_id': query_id,
                'query': query,
                'error': str(e),
                'latency_ms': latency_ms,
                'cache_hit': False,
                'retrieved_count': 0
            }

    def run_sequential_test(self, rag_tool: RAGTool) -> Dict[str, Any]:
        """顺序执行测试"""
        logger.info("=" * 60)
        logger.info("开始顺序执行测试")
        logger.info("=" * 60)

        self.perf_collector.start_time = time.time()

        for query_item in self.test_data.test_queries:
            logger.info(f"执行查询: {query_item['query']}")
            result = self.run_single_query(rag_tool, query_item)
            self.quality_results.append(result)

        self.perf_collector.end_time = time.time()

        return self._generate_summary()

    def run_concurrent_test(
        self,
        rag_tool: RAGTool,
        concurrent_level: int = 10,
        repeat: int = 3
    ) -> Dict[str, Any]:
        """并发测试"""
        logger.info("=" * 60)
        logger.info(f"开始并发测试 (并发数: {concurrent_level}, 轮次: {repeat})")
        logger.info("=" * 60)

        test_queries = self.test_data.test_queries * repeat
        concurrent_metrics = ConcurrencyMetrics(
            max_concurrent=concurrent_level,
            success_count=0,
            error_count=0,
            error_rate=0.0,
            throughput=0.0
        )

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=concurrent_level) as executor:
            futures = []
            for query_item in test_queries:
                future = executor.submit(self.run_single_query, rag_tool, query_item)
                futures.append(future)

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if 'error' in result:
                        concurrent_metrics.error_count += 1
                    else:
                        concurrent_metrics.success_count += 1
                except Exception as e:
                    concurrent_metrics.error_count += 1
                    logger.error(f"并发测试异常: {e}")

        end_time = time.time()
        duration = end_time - start_time

        concurrent_metrics.throughput = round(
            concurrent_metrics.success_count / duration, 2
        )
        concurrent_metrics.error_rate = round(
            concurrent_metrics.error_count / len(test_queries), 4
        )

        return asdict(concurrent_metrics)

    def _generate_summary(self) -> Dict[str, Any]:
        """生成测试摘要"""
        perf_metrics = self.perf_collector.calculate_metrics()
        cache_metrics = self.perf_collector.calculate_cache_metrics()

        successful_results = [r for r in self.quality_results if 'error' not in r]

        avg_recall = statistics.mean([r['quality_metrics']['recall'] for r in successful_results]) if successful_results else 0
        avg_precision = statistics.mean([r['quality_metrics']['precision'] for r in successful_results]) if successful_results else 0
        avg_f1 = statistics.mean([r['quality_metrics']['f1_score'] for r in successful_results]) if successful_results else 0
        avg_mrr = statistics.mean([r['quality_metrics']['mrr'] for r in successful_results]) if successful_results else 0
        avg_ndcg = statistics.mean([r['quality_metrics']['ndcg'] for r in successful_results]) if successful_results else 0

        success_rate = len(successful_results) / len(self.quality_results) if self.quality_results else 0

        return {
            'test_timestamp': datetime.now().isoformat(),
            'total_queries': len(self.quality_results),
            'successful_queries': len(successful_results),
            'success_rate': round(success_rate, 4),
            'quality_metrics': {
                'avg_recall': round(avg_recall, 4),
                'avg_precision': round(avg_precision, 4),
                'avg_f1_score': round(avg_f1, 4),
                'avg_mrr': round(avg_mrr, 4),
                'avg_ndcg': round(avg_ndcg, 4)
            },
            'performance_metrics': asdict(perf_metrics),
            'cache_metrics': asdict(cache_metrics),
            'target_comparison': self._compare_with_targets({
                'recall': avg_recall,
                'precision': avg_precision,
                'avg_latency': perf_metrics.avg_latency_ms,
                'p95_latency': perf_metrics.p95_latency_ms,
                'cache_hit_rate': cache_metrics.hit_rate,
                'success_rate': success_rate
            }),
            'detailed_results': self.quality_results
        }

    def _compare_with_targets(self, actual: Dict[str, float]) -> Dict[str, Any]:
        """与目标值对比"""
        targets = self.test_data.targets
        comparison = {}

        if 'recall_at_3' in targets:
            comparison['recall'] = {
                'target': targets['recall_at_3'],
                'actual': actual.get('recall', 0),
                'pass': actual.get('recall', 0) >= targets['recall_at_3'],
                'gap': round(actual.get('recall', 0) - targets['recall_at_3'], 4)
            }

        if 'precision_at_3' in targets:
            comparison['precision'] = {
                'target': targets['precision_at_3'],
                'actual': actual.get('precision', 0),
                'pass': actual.get('precision', 0) >= targets['precision_at_3'],
                'gap': round(actual.get('precision', 0) - targets['precision_at_3'], 4)
            }

        if 'avg_latency_ms' in targets:
            comparison['avg_latency'] = {
                'target': targets['avg_latency_ms'],
                'actual': actual.get('avg_latency', 0),
                'pass': actual.get('avg_latency', 0) <= targets['avg_latency_ms'],
                'gap': round(actual.get('avg_latency', 0) - targets['avg_latency_ms'], 4)
            }

        if 'p95_latency_ms' in targets:
            comparison['p95_latency'] = {
                'target': targets['p95_latency_ms'],
                'actual': actual.get('p95_latency', 0),
                'pass': actual.get('p95_latency', 0) <= targets['p95_latency_ms'],
                'gap': round(actual.get('p95_latency', 0) - targets['p95_latency_ms'], 4)
            }

        if 'cache_hit_rate' in targets:
            comparison['cache_hit_rate'] = {
                'target': targets['cache_hit_rate'],
                'actual': actual.get('cache_hit_rate', 0),
                'pass': actual.get('cache_hit_rate', 0) >= targets['cache_hit_rate'],
                'gap': round(actual.get('cache_hit_rate', 0) - targets['cache_hit_rate'], 4)
            }

        if 'success_rate' in targets:
            comparison['success_rate'] = {
                'target': targets['success_rate'],
                'actual': actual.get('success_rate', 0),
                'pass': actual.get('success_rate', 0) >= targets['success_rate'],
                'gap': round(actual.get('success_rate', 0) - targets['success_rate'], 4)
            }

        return comparison

    def generate_report(self, output_file: Optional[str] = None) -> str:
        """生成测试报告"""
        summary = self._generate_summary()

        report_lines = [
            "=" * 80,
            "RAG系统基准测试报告",
            "=" * 80,
            f"测试时间: {summary['test_timestamp']}",
            f"总查询数: {summary['total_queries']}",
            f"成功查询: {summary['successful_queries']}",
            f"成功率: {summary['success_rate']:.2%}",
            "",
            "-" * 80,
            "【检索质量指标】",
            "-" * 80,
            f"平均召回率 (Recall@3): {summary['quality_metrics']['avg_recall']:.2%}",
            f"平均准确率 (Precision@3): {summary['quality_metrics']['avg_precision']:.2%}",
            f"平均 F1 分数: {summary['quality_metrics']['avg_f1_score']:.4f}",
            f"平均 MRR: {summary['quality_metrics']['avg_mrr']:.4f}",
            f"平均 NDCG: {summary['quality_metrics']['avg_ndcg']:.4f}",
            "",
            "-" * 80,
            "【性能指标】",
            "-" * 80,
            f"平均延迟: {summary['performance_metrics']['avg_latency_ms']:.2f}ms",
            f"P50 延迟: {summary['performance_metrics']['p50_latency_ms']:.2f}ms",
            f"P95 延迟: {summary['performance_metrics']['p95_latency_ms']:.2f}ms",
            f"P99 延迟: {summary['performance_metrics']['p99_latency_ms']:.2f}ms",
            f"最小延迟: {summary['performance_metrics']['min_latency_ms']:.2f}ms",
            f"最大延迟: {summary['performance_metrics']['max_latency_ms']:.2f}ms",
            f"标准差: {summary['performance_metrics']['std_dev_ms']:.2f}ms",
            f"QPS: {summary['performance_metrics']['qps']:.2f}",
            "",
            "-" * 80,
            "【缓存效率】",
            "-" * 80,
            f"缓存命中: {summary['cache_metrics']['hit_count']}",
            f"缓存未命中: {summary['cache_metrics']['miss_count']}",
            f"缓存命中率: {summary['cache_metrics']['hit_rate']:.2%}",
            f"命中时平均延迟: {summary['cache_metrics']['avg_hit_latency_ms']:.2f}ms",
            f"未命中时平均延迟: {summary['cache_metrics']['avg_miss_latency_ms']:.2f}ms",
            f"延迟改善: {((summary['cache_metrics']['avg_miss_latency_ms'] - summary['cache_metrics']['avg_hit_latency_ms']) / summary['cache_metrics']['avg_miss_latency_ms'] * 100):.1f}%" if summary['cache_metrics']['avg_miss_latency_ms'] > 0 else "N/A",
            "",
            "-" * 80,
            "【目标达成情况】",
            "-" * 80,
        ]

        for metric_name, comparison in summary['target_comparison'].items():
            status = "✓ 通过" if comparison['pass'] else "✗ 未达标"
            gap_str = f"+{comparison['gap']:.4f}" if comparison['gap'] >= 0 else f"{comparison['gap']:.4f}"
            report_lines.append(
                f"{metric_name}: 目标={comparison['target']:.2f}, "
                f"实际={comparison['actual']:.2f}, 差距={gap_str} {status}"
            )

        report_lines.extend([
            "",
            "-" * 80,
            "【详细查询结果】",
            "-" * 80,
        ])

        for result in summary['detailed_results']:
            if 'error' in result:
                report_lines.append(
                    f"[{result['query_id']}] {result['query']} - 错误: {result['error']}"
                )
            else:
                report_lines.append(
                    f"[{result['query_id']}] {result['query']}\n"
                    f"  召回率: {result['quality_metrics']['recall']:.2%}, "
                    f"准确率: {result['quality_metrics']['precision']:.2%}, "
                    f"F1: {result['quality_metrics']['f1_score']:.4f}\n"
                    f"  延迟: {result['latency_ms']:.2f}ms, "
                    f"缓存: {'命中' if result['cache_hit'] else '未命中'}, "
                    f"检索文档数: {result['retrieved_count']}"
                )

        report_lines.append("=" * 80)

        report_text = "\n".join(report_lines)

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            logger.info(f"测试报告已保存到: {output_file}")

        json_output = output_file.replace('.txt', '.json') if output_file else None
        if json_output:
            with open(json_output, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            logger.info(f"JSON报告已保存到: {json_output}")

        return report_text


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='RAG系统基准测试')
    parser.add_argument('--data', type=str,
                       default='tests/benchmark_test_data.json',
                       help='测试数据文件路径')
    parser.add_argument('--top-k', type=int, default=3,
                       help='检索返回的文档数量')
    parser.add_argument('--warmup', action='store_true',
                       help='是否预热缓存')
    parser.add_argument('--concurrent', type=int, default=10,
                       help='并发测试的并发数')
    parser.add_argument('--repeat', type=int, default=3,
                       help='并发测试的重复次数')
    parser.add_argument('--output', type=str, default=None,
                       help='输出报告文件路径')

    args = parser.parse_args()

    logger.info("初始化RAG系统...")
    rag_tool = RAGTool()

    benchmark = RAGBenchmark(args.data, args.top_k)

    warmup_queries = [
        "X12 Pro手机多少钱",
        "手机进水了怎么办",
        "能不能便宜一点"
    ]
    if args.warmup:
        benchmark.warmup_cache(rag_tool, warmup_queries)

    perf_results = benchmark.run_sequential_test(rag_tool)

    if args.concurrent > 0:
        concurrent_results = benchmark.run_concurrent_test(
            rag_tool,
            concurrent_level=args.concurrent,
            repeat=args.repeat
        )
        perf_results['concurrent_test'] = concurrent_results

    output_file = args.output or f"benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report = benchmark.generate_report(output_file)

    print("\n" + report)

    return perf_results


if __name__ == "__main__":
    main()
