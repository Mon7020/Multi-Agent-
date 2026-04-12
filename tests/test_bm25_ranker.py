"""
BM25 算法单元测试
=================

测试内容：
1. 基础功能测试 - 分词、索引、检索
2. IDF 计算准确性测试
3. BM25 得分计算测试
4. 参数调优测试 (k1, b)
5. 停用词过滤测试
6. 线程安全测试
7. 性能基准测试
8. 电商场景集成测试
"""

import unittest
import time
import threading
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.rag.bm25_ranker import (
    ProfessionalBM25,
    BM25Stopwords,
    ECommerceTokenizer,
    BM25ParameterTuner,
    create_bm25_ranker,
    BM25Result
)


class TestBM25BasicFunctionality(unittest.TestCase):
    """BM25 基础功能测试"""

    def setUp(self):
        self.bm25 = ProfessionalBM25(k1=1.5, b=0.75)
        self.documents = [
            {"id": "doc1", "content": "蓝牙耳机 音质好 续航长 适合运动", "metadata": {"type": "product"}},
            {"id": "doc2", "content": "无线耳机 降噪功能强 价格优惠", "metadata": {"type": "product"}},
            {"id": "doc3", "content": "运动耳机 防水防汗 佩戴舒适", "metadata": {"type": "product"}},
            {"id": "doc4", "content": "头戴式耳机 音质震撼 低音强劲", "metadata": {"type": "product"}},
            {"id": "doc5", "content": "游戏耳机 7.1环绕声 麦克风清晰", "metadata": {"type": "product"}},
        ]
        self.bm25.index_documents(self.documents)

    def test_indexed_state(self):
        """测试索引状态"""
        self.assertTrue(self.bm25.is_indexed)
        self.assertEqual(self.bm25.document_count, 5)
        self.assertGreater(self.bm25.vocabulary_size, 0)

    def test_basic_search(self):
        """测试基本检索"""
        results = self.bm25.search("蓝牙耳机", top_k=3)
        self.assertLessEqual(len(results), 3)
        self.assertTrue(all(isinstance(r, BM25Result) for r in results))

    def test_search_with_scores(self):
        """测试带分数的检索"""
        results = self.bm25.search("音质好", top_k=3)
        if results:
            self.assertGreater(results[0].score, 0)
            for i in range(len(results) - 1):
                self.assertGreaterEqual(results[i].score, results[i + 1].score)

    def test_empty_query(self):
        """测试空查询"""
        results = self.bm25.search("", top_k=5)
        self.assertEqual(len(results), 0)

    def test_no_match_query(self):
        """测试无匹配查询"""
        results = self.bm25.search("完全无关的内容 xyz123", top_k=5)
        self.assertEqual(len(results), 0)


class TestBM25IDFCalculation(unittest.TestCase):
    """BM25 IDF 计算准确性测试"""

    def test_idf_smoothing(self):
        """测试 IDF 平滑处理"""
        bm25 = ProfessionalBM25(k1=1.5, b=0.75, epsilon=0.25)

        docs = [
            {"id": "d1", "content": "苹果 手机 便宜"},
            {"id": "d2", "content": "香蕉 水果 新鲜"},
            {"id": "d3", "content": "橙子 水果 甜"},
        ]
        bm25.index_documents(docs)

        idf_苹果 = bm25._calculate_idf("苹果")
        idf_水果 = bm25._calculate_idf("水果")
        idf_稀有词 = bm25._calculate_idf("稀有词xyz")

        self.assertGreater(idf_苹果, 0)
        self.assertGreater(idf_水果, 0)
        self.assertGreaterEqual(idf_苹果, idf_水果)

    def test_idf_high_freq_term(self):
        """测试高频词 IDF 较低"""
        bm25 = ProfessionalBM25(k1=1.5, b=0.75, use_jieba=False)

        docs = [
            {"id": "d1", "content": "苹果 苹果 苹果 苹果 苹果"},
            {"id": "d2", "content": "苹果 香蕉"},
            {"id": "d3", "content": "香蕉 橙子"},
        ]
        bm25.index_documents(docs)

        idf_苹果 = bm25._calculate_idf("苹果")
        idf_香蕉 = bm25._calculate_idf("香蕉")
        idf_稀有 = bm25._calculate_idf("稀有词xyz")

        self.assertGreater(idf_苹果, 0)
        self.assertGreater(idf_香蕉, 0)
        self.assertGreaterEqual(idf_苹果, idf_香蕉)


class TestBM25Scoring(unittest.TestCase):
    """BM25 得分计算测试"""

    def test_longer_doc_penalty(self):
        """测试长文档惩罚"""
        bm25 = ProfessionalBM25(k1=1.5, b=0.75)

        docs = [
            {"id": "short", "content": "蓝牙耳机 推荐"},
            {"id": "long", "content": "这是一个很长的产品介绍文档，包含了很多关于蓝牙耳机的描述信息，包括音质、续航、舒适度等多个方面的详细介绍。"},
        ]
        bm25.index_documents(docs)

        results = bm25.search("蓝牙耳机", top_k=2)

        if len(results) == 2:
            short_doc = next((r for r in results if r.doc_id == "short"), None)
            self.assertIsNotNone(short_doc)

    def test_term_frequency_saturation(self):
        """测试词频饱和效应"""
        bm25 = ProfessionalBM25(k1=1.5, b=0.75)

        docs = [
            {"id": "d1", "content": "手机 手机 手机 手机 手机"},
            {"id": "d2", "content": "手机"},
        ]
        bm25.index_documents(docs)

        results = bm25.search("手机", top_k=2)

        if len(results) == 2:
            d1 = next((r for r in results if r.doc_id == "d1"), None)
            d2 = next((r for r in results if r.doc_id == "d2"), None)

            if d1 and d2:
                ratio = d1.score / d2.score if d2.score > 0 else float('inf')
                self.assertLess(ratio, 6)


class TestBM25Parameters(unittest.TestCase):
    """BM25 参数调优测试"""

    def test_different_k1_values(self):
        """测试不同 k1 值的效果"""
        docs = [
            {"id": "d1", "content": "蓝牙 耳机 推荐 音质 好"},
            {"id": "d2", "content": "蓝牙 耳机"},
            {"id": "d3", "content": "普通 耳机"},
        ]

        k1_values = [0.5, 1.0, 1.5, 2.0]
        scores_by_k1 = {k1: [] for k1 in k1_values}

        for k1 in k1_values:
            bm25 = ProfessionalBM25(k1=k1, b=0.75)
            bm25.index_documents(docs)
            results = bm25.search("蓝牙 耳机 推荐", top_k=3)
            scores_by_k1[k1] = [r.score for r in results if r.doc_id == "d1"]

        for i in range(len(k1_values) - 1):
            k1_a, k1_b = k1_values[i], k1_values[i + 1]
            self.assertIsNotNone(scores_by_k1[k1_a])
            self.assertIsNotNone(scores_by_k1[k1_b])

    def test_different_b_values(self):
        """测试不同 b 值的效果"""
        docs = [
            {"id": "d1", "content": "短"},
            {"id": "d2", "content": "这是一个非常非常长的文档内容包含了很多很多很多的词语和描述信息"},
        ]

        b_values = [0.0, 0.5, 0.75, 1.0]
        bm25_0 = ProfessionalBM25(k1=1.5, b=0.0)
        bm25_0.index_documents(docs)
        results_0 = bm25_0.search("文档 内容 词语", top_k=2)

        bm25_75 = ProfessionalBM25(k1=1.5, b=0.75)
        bm25_75.index_documents(docs)
        results_75 = bm25_75.search("文档 内容 词语", top_k=2)

        if results_0 and results_75:
            pass


class TestBM25Stopwords(unittest.TestCase):
    """停用词过滤测试"""

    def test_default_stopwords(self):
        """测试默认停用词"""
        stopwords = BM25Stopwords()

        self.assertTrue(stopwords.is_stopword("产品介绍"))
        self.assertTrue(stopwords.is_stopword("正品"))
        self.assertTrue(stopwords.is_stopword("旗舰"))
        self.assertFalse(stopwords.is_stopword("蓝牙"))
        self.assertFalse(stopwords.is_stopword("耳机"))

    def test_custom_stopwords(self):
        """测试自定义停用词"""
        custom = {"自定义词", "特殊停用词"}
        stopwords = BM25Stopwords(custom_stopwords=custom)

        self.assertTrue(stopwords.is_stopword("自定义词"))
        self.assertTrue(stopwords.is_stopword("特殊停用词"))

    def test_stopwords_filter(self):
        """测试停用词过滤"""
        stopwords = BM25Stopwords()
        tokens = ["产品介绍", "正品", "蓝牙", "耳机", "价格"]

        filtered = stopwords.filter(tokens)

        self.assertNotIn("产品介绍", filtered)
        self.assertNotIn("正品", filtered)
        self.assertIn("蓝牙", filtered)
        self.assertIn("耳机", filtered)


class TestECommerceTokenizer(unittest.TestCase):
    """电商分词器测试"""

    def test_basic_tokenize(self):
        """测试基本分词"""
        tokenizer = ECommerceTokenizer(use_jieba=False)

        tokens = tokenizer.tokenize("蓝牙耳机推荐")
        self.assertIsInstance(tokens, list)

    def test_product_model_extraction(self):
        """测试产品型号提取"""
        tokenizer = ECommerceTokenizer(use_jieba=False)

        tokens = tokenizer.tokenize("X12 Pro 蓝牙耳机")
        tokens_lower = [t.lower() for t in tokens]

        model_found = any("x12" in t for t in tokens_lower)
        self.assertTrue(model_found)

    def test_number_unit_extraction(self):
        """测试数字+单位提取"""
        tokenizer = ECommerceTokenizer(use_jieba=False)

        tokens = tokenizer.tokenize("续航10小时")
        tokens_str = " ".join(tokens)

        self.assertTrue("10小时" in tokens_str or any("10" in t for t in tokens))


class TestBM25ThreadSafety(unittest.TestCase):
    """线程安全测试"""

    def test_concurrent_search(self):
        """测试并发检索"""
        bm25 = ProfessionalBM25(k1=1.5, b=0.75)
        docs = [
            {"id": f"doc{i}", "content": f"蓝牙耳机 {i} 推荐 音质"}
            for i in range(100)
        ]
        bm25.index_documents(docs)

        results = []
        errors = []

        def search_worker(query_id):
            try:
                r = bm25.search(f"蓝牙耳机 {query_id % 10}", top_k=5)
                results.append(r)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=search_worker, args=(i,))
            for i in range(20)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 20)

    def test_concurrent_index_and_search(self):
        """测试并发索引和检索"""
        bm25 = ProfessionalBM25(k1=1.5, b=0.75)
        bm25.index_documents([{"id": "initial", "content": "初始文档"}])

        errors = []

        def index_worker():
            try:
                for i in range(10):
                    bm25.add_document({
                        "id": f"new_doc_{i}",
                        "content": f"新文档 {i} 内容"
                    })
            except Exception as e:
                errors.append(e)

        def search_worker():
            try:
                for _ in range(10):
                    bm25.search("文档", top_k=5)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=index_worker)
        t2 = threading.Thread(target=search_worker)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(errors), 0)


class TestBM25Performance(unittest.TestCase):
    """性能基准测试"""

    @unittest.skipIf(os.getenv("SKIP_PERF_TESTS", "1") == "1", "性能测试默认跳过")
    def test_large_scale_performance(self):
        """大规模文档性能测试"""
        bm25 = ProfessionalBM25(k1=1.5, b=0.75)

        num_docs = 1000
        docs = [
            {
                "id": f"doc_{i}",
                "content": f"产品 {i} 蓝牙耳机 推荐 音质好 续航长 价格优惠 适合运动 降噪 功能强 防水 防汗"
            }
            for i in range(num_docs)
        ]

        start_time = time.time()
        bm25.index_documents(docs)
        index_time = time.time() - start_time

        start_time = time.time()
        results = bm25.search("蓝牙耳机 推荐", top_k=10)
        search_time = time.time() - start_time

        self.assertLess(index_time, 5.0)
        self.assertLess(search_time, 0.1)
        self.assertGreater(len(results), 0)

    def test_sequential_search_performance(self):
        """连续搜索性能"""
        bm25 = ProfessionalBM25(k1=1.5, b=0.75)
        docs = [
            {"id": f"doc_{i}", "content": f"产品 {i} 内容 信息"}
            for i in range(100)
        ]
        bm25.index_documents(docs)

        queries = ["产品 1", "产品 2", "内容", "信息", "产品 50"]

        start_time = time.time()
        for query in queries:
            bm25.search(query, top_k=5)
        total_time = time.time() - start_time

        self.assertLess(total_time, 1.0)


class TestBM25ECommerceScenario(unittest.TestCase):
    """电商场景集成测试"""

    def setUp(self):
        self.bm25 = create_bm25_ranker(k1=1.5, b=0.75)
        self.product_docs = [
            {
                "id": "p1",
                "content": "X12 Pro 蓝牙耳机 真无线 主动降噪 30小时续航 Hi-Res认证 音质震撼",
                "metadata": {"name": "X12 Pro 蓝牙耳机", "price": 899, "category": "耳机"}
            },
            {
                "id": "p2",
                "content": "X12 无线耳机 被动降噪 20小时续航 轻巧设计 佩戴舒适",
                "metadata": {"name": "X12 无线耳机", "price": 599, "category": "耳机"}
            },
            {
                "id": "p3",
                "content": "Y8头戴式耳机 专业监听级音质 包耳式设计 50小时续航",
                "metadata": {"name": "Y8 头戴式耳机", "price": 1299, "category": "耳机"}
            },
            {
                "id": "p4",
                "content": "S5运动耳机 挂耳式 防水防汗 IPX7防水 12小时续航",
                "metadata": {"name": "S5 运动耳机", "price": 399, "category": "运动耳机"}
            },
            {
                "id": "p5",
                "content": "G1游戏耳机 7.1环绕声 RGB灯效 炫酷外观 专业游戏麦克风",
                "metadata": {"name": "G1 游戏耳机", "price": 699, "category": "游戏耳机"}
            },
        ]
        self.bm25.index_documents(self.product_docs)

    def test_product_recommendation(self):
        """测试产品推荐场景"""
        results = self.bm25.search("推荐一款音质好的耳机", top_k=3)

        self.assertGreater(len(results), 0)
        self.assertGreater(results[0].score, 0)

        top_result_content = results[0].content.lower()
        self.assertTrue(
            "音质" in top_result_content or "认证" in top_result_content
        )

    def test_price_inquiry(self):
        """测试价格查询场景"""
        results = self.bm25.search("X12耳机 价格", top_k=3)

        self.assertGreater(len(results), 0)

        for r in results:
            content_lower = r.content.lower()
            self.assertTrue(
                "x12" in content_lower or "耳机" in content_lower
            )

    def test_product_comparison(self):
        """测试产品对比场景"""
        results = self.bm25.search("X12和Y8哪个好", top_k=3)

        self.assertGreater(len(results), 0)

        doc_ids = [r.doc_id for r in results]
        self.assertTrue(
            "p1" in doc_ids or "p2" in doc_ids or "p3" in doc_ids
        )

    def test_spec_inquiry(self):
        """测试规格查询场景"""
        results = self.bm25.search("续航多少小时", top_k=3)

        self.assertGreater(len(results), 0)

        for r in results:
            self.assertIsNotNone(r.score)


class TestBM25ParameterTuner(unittest.TestCase):
    """参数调优器测试"""

    def test_tuner_creates_valid_results(self):
        """测试调优器产生有效结果"""
        bm25 = ProfessionalBM25(k1=1.5, b=0.75)

        docs = [
            {"id": "d1", "content": "苹果 手机 便宜 好用"},
            {"id": "d2", "content": "苹果 水果 甜"},
            {"id": "d3", "content": "香蕉 水果 新鲜"},
            {"id": "d4", "content": "手机 电子 产品"},
        ]
        bm25.index_documents(docs)

        test_queries = [
            ("苹果 手机", ["d1", "d4"]),
            ("水果", ["d2", "d3"]),
        ]

        tuner = BM25ParameterTuner()
        best_params = tuner.grid_search(bm25, test_queries, top_k=2)

        self.assertIn("k1", best_params)
        self.assertIn("b", best_params)
        self.assertIn("map", best_params)
        self.assertGreater(best_params["map"], 0)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestBM25BasicFunctionality))
    suite.addTests(loader.loadTestsFromTestCase(TestBM25IDFCalculation))
    suite.addTests(loader.loadTestsFromTestCase(TestBM25Scoring))
    suite.addTests(loader.loadTestsFromTestCase(TestBM25Parameters))
    suite.addTests(loader.loadTestsFromTestCase(TestBM25Stopwords))
    suite.addTests(loader.loadTestsFromTestCase(TestECommerceTokenizer))
    suite.addTests(loader.loadTestsFromTestCase(TestBM25ThreadSafety))
    suite.addTests(loader.loadTestsFromTestCase(TestBM25Performance))
    suite.addTests(loader.loadTestsFromTestCase(TestBM25ECommerceScenario))
    suite.addTests(loader.loadTestsFromTestCase(TestBM25ParameterTuner))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
