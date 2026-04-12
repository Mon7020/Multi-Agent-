"""
意图分类器单元测试
===================
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.rag.intent_classifier import (
    IntentType,
    IntentClassificationResult,
    KeywordIntentClassifier,
    LLMIntentClassifier,
    UnifiedIntentClassifier,
    create_intent_classifier,
    get_all_intent_types,
    get_intent_description,
    INTENT_DESCRIPTIONS,
    INTENT_KEYWORDS
)


class TestIntentTypeEnum:
    """测试意图类型枚举"""

    def test_all_intent_types_exist(self):
        expected = ["price_inquiry", "product_spec", "comparison",
                   "troubleshooting", "purchase", "recommendation", "general"]
        for intent_str in expected:
            intent = IntentType(intent_str)
            assert intent.value == intent_str

    def test_intent_value(self):
        assert IntentType.RECOMMENDATION.value == "recommendation"
        assert IntentType.PRICE_INQUIRY.value == "price_inquiry"


class TestKeywordIntentClassifier:
    """测试关键词意图分类器"""

    def setup_method(self):
        self.classifier = KeywordIntentClassifier()

    def test_price_inquiry(self):
        result = self.classifier.classify("这个投影仪多少钱")
        assert result.intent == IntentType.PRICE_INQUIRY
        assert result.method == "keyword"

    def test_recommendation(self):
        result = self.classifier.classify("推荐一款蓝牙耳机")
        assert result.intent == IntentType.RECOMMENDATION

    def test_comparison(self):
        result = self.classifier.classify("X12和Y8哪个好")
        assert result.intent == IntentType.COMPARISON

    def test_product_spec(self):
        result = self.classifier.classify("这款手机的参数是什么")
        assert result.intent == IntentType.PRODUCT_SPEC

    def test_troubleshooting(self):
        result = self.classifier.classify("耳机坏了怎么维修")
        assert result.intent == IntentType.TROUBLESHOOTING

    def test_purchase(self):
        result = self.classifier.classify("我想下单购买")
        assert result.intent == IntentType.PURCHASE

    def test_general(self):
        result = self.classifier.classify("你好")
        assert result.intent == IntentType.GENERAL

    def test_batch_classification(self):
        queries = ["价格多少", "推荐产品", "有什么区别"]
        results = self.classifier.classify_batch(queries)
        assert len(results) == 3


class TestUnifiedIntentClassifier:
    """测试统一意图分类器（无LLM时回退到关键词）"""

    def setup_method(self):
        self.classifier = UnifiedIntentClassifier(llm=None)

    def test_basic_classification(self):
        result = self.classifier.classify("推荐一款耳机")
        assert result.intent == IntentType.RECOMMENDATION
        assert result.confidence > 0

    def test_cache_functionality(self):
        query = "这个产品多少钱"
        result1 = self.classifier.classify(query)
        result2 = self.classifier.classify(query)
        assert "[memory_cached]" in result2.reasoning or "[redis_cached]" in result2.reasoning or "[cached]" in result2.reasoning
        assert self.classifier.get_memory_cache_size() == 1

    def test_clear_cache(self):
        self.classifier.classify("测试查询")
        assert self.classifier.get_memory_cache_size() == 1
        self.classifier.clear_cache()
        assert self.classifier.get_memory_cache_size() == 0


class TestIntentClassificationResult:
    """测试分类结果数据类"""

    def test_to_tuple(self):
        result = IntentClassificationResult(
            intent=IntentType.RECOMMENDATION,
            confidence=0.95,
            reasoning="用户请求推荐"
        )
        intent_str, confidence, reasoning = result.to_tuple()
        assert intent_str == "recommendation"
        assert confidence == 0.95

    def test_string_representation(self):
        result = IntentClassificationResult(
            intent=IntentType.PRICE_INQUIRY,
            confidence=0.88,
            reasoning="用户询问价格"
        )
        s = str(result)
        assert "price_inquiry" in s
        assert "0.88" in s


class TestFactoryFunction:
    """测试工厂函数"""

    def test_create_keyword_classifier(self):
        classifier = create_intent_classifier(method="keyword")
        assert isinstance(classifier, KeywordIntentClassifier)

    def test_create_llm_classifier(self):
        classifier = create_intent_classifier(llm=None, method="llm")
        assert isinstance(classifier, LLMIntentClassifier)

    def test_create_unified_classifier(self):
        classifier = create_intent_classifier(method="unified")
        assert isinstance(classifier, UnifiedIntentClassifier)


class TestHelperFunctions:
    """测试辅助函数"""

    def test_get_all_intent_types(self):
        intents = get_all_intent_types()
        assert len(intents) == 7
        assert IntentType.RECOMMENDATION in intents

    def test_get_intent_description(self):
        desc = get_intent_description(IntentType.RECOMMENDATION)
        assert "推荐" in desc


class TestIntegration:
    """集成测试"""

    def test_query_understanding_layer_import(self):
        from tools.rag.query_understanding import QueryUnderstandingLayer
        layer = QueryUnderstandingLayer(llm=None)
        assert layer is not None

    def test_context_rag_fusion_import(self):
        from tools.rag.context_rag_fusion import ContextRAGFusionLayer
        layer = ContextRAGFusionLayer(llm=None)
        assert layer is not None
        assert isinstance(layer._intent_classifier, UnifiedIntentClassifier)

    def test_full_classification_flow(self):
        classifier = UnifiedIntentClassifier(llm=None)

        test_cases = [
            ("X12耳机价格多少", IntentType.PRICE_INQUIRY),
            ("有什么好用的耳机推荐", IntentType.RECOMMENDATION),
            ("X12和Y8有什么区别", IntentType.COMPARISON),
            ("耳机的参数配置是什么", IntentType.PRODUCT_SPEC),
            ("耳机有故障怎么办", IntentType.TROUBLESHOOTING),
            ("我想买一个耳机", IntentType.PURCHASE),
        ]

        for query, expected_intent in test_cases:
            result = classifier.classify(query)
            assert result.intent == expected_intent, f"Query: {query}, Expected: {expected_intent}, Got: {result.intent}"


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Intent Classifier Unit Tests")
    print("=" * 60)

    test_classes = [
        TestIntentTypeEnum,
        TestKeywordIntentClassifier,
        TestUnifiedIntentClassifier,
        TestIntentClassificationResult,
        TestFactoryFunction,
        TestHelperFunctions,
        TestIntegration,
    ]

    total_tests = 0
    passed_tests = 0

    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        instance = test_class()
        setup_method = getattr(instance, 'setup_method', None)

        for method_name in dir(instance):
            if method_name.startswith('test_'):
                if setup_method:
                    try:
                        setup_method()
                    except:
                        pass

                try:
                    method = getattr(instance, method_name)
                    method()
                    print(f"  [PASS] {method_name}")
                    passed_tests += 1
                except Exception as e:
                    print(f"  [FAIL] {method_name}: {e}")

                total_tests += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed_tests}/{total_tests} tests passed")
    print("=" * 60)

    return passed_tests == total_tests


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
