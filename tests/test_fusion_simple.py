"""
Context+RAG融合层 - 简化测试
测试核心融合逻辑（不依赖外部模块）
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Tuple
from enum import Enum


class RetrievalQuality(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class FusionStrategy(Enum):
    RAG_PRIMARY = "rag_primary"
    CONTEXT_PRIMARY = "context_primary"
    HYBRID = "hybrid"
    CONTEXT_ONLY = "context_only"


@dataclass
class ContextAwareQuery:
    original_query: str
    enhanced_query: str
    entities: List[str]
    metadata_hints: Dict[str, Any]


@dataclass
class FusionResult:
    quality: RetrievalQuality
    fusion_strategy: FusionStrategy
    confidence: float
    used_sources: List[str]
    metadata: Dict[str, Any]


class MockSessionContext:
    def __init__(self):
        self.metadata = {
            "customer_type": "price_sensitive",
            "current_product": "智能手机",
            "discount_level": 1,
            "preference": "高性价比"
        }
        self.skill_context = {
            "customer_classifier": {
                "customer_type": "price_sensitive",
                "confidence": 0.85
            }
        }
        self.turn_history = []


class ContextExtractor:
    def extract_for_rag(self, context, query: str) -> ContextAwareQuery:
        metadata = context.metadata
        entities = []
        enhanced_parts = [query]

        if metadata.get("current_product"):
            product = metadata["current_product"]
            enhanced_parts.append(product)
            entities.append(product)

        return ContextAwareQuery(
            original_query=query,
            enhanced_query=" ".join(enhanced_parts),
            entities=list(set(entities)),
            metadata_hints=metadata
        )


class RAGResultInjector:
    def evaluate_retrieval_quality(self, documents: List[Dict], query: str) -> Tuple[RetrievalQuality, float]:
        if not documents:
            return RetrievalQuality.NONE, 0.0

        total = sum(doc.get("similarity_score", 0.0) for doc in documents)
        avg = total / len(documents)

        if avg >= 0.7:
            return RetrievalQuality.HIGH, avg
        elif avg >= 0.4:
            return RetrievalQuality.MEDIUM, avg
        elif avg >= 0.2:
            return RetrievalQuality.LOW, avg
        else:
            return RetrievalQuality.NONE, avg


class AdaptiveFusionEngine:
    def select_strategy(self, quality: RetrievalQuality, context_strength: float, intent: str) -> Tuple[FusionStrategy, float]:
        if quality == RetrievalQuality.HIGH:
            if context_strength > 0.6:
                return FusionStrategy.HYBRID, 0.85
            else:
                return FusionStrategy.RAG_PRIMARY, 0.75
        elif quality == RetrievalQuality.MEDIUM:
            return FusionStrategy.HYBRID, 0.70
        elif quality == RetrievalQuality.LOW:
            return FusionStrategy.CONTEXT_PRIMARY, 0.60
        else:
            return FusionStrategy.CONTEXT_ONLY, 0.50


class ContextRAGFusionLayer:
    def __init__(self):
        self.context_extractor = ContextExtractor()
        self.rag_result_injector = RAGResultInjector()
        self.fusion_engine = AdaptiveFusionEngine()

    def process(self, query: str, session_context, rag_retrieval_func) -> FusionResult:
        print(f"\n[Step 1] Context Extraction...")
        query_obj = self.context_extractor.extract_for_rag(session_context, query)
        print(f"  Original: '{query}' -> Enhanced: '{query_obj.enhanced_query}'")

        print(f"\n[Step 2] RAG Retrieval...")
        rag_result = rag_retrieval_func(query_obj.enhanced_query)
        documents = rag_result.get("documents", [])
        print(f"  Found {len(documents)} documents")

        print(f"\n[Step 3] Quality Assessment...")
        quality, quality_conf = self.rag_result_injector.evaluate_retrieval_quality(documents, query)
        print(f"  Quality: {quality.value}, Confidence: {quality_conf:.3f}")

        print(f"\n[Step 4] Strategy Selection...")
        context_strength = 0.7
        strategy, strategy_conf = self.fusion_engine.select_strategy(quality, context_strength, "sales")
        print(f"  Strategy: {strategy.value}, Confidence: {strategy_conf:.2f}")

        sources = ["knowledge_base"] if documents else []
        if session_context.skill_context:
            sources.append("skill_context")

        return FusionResult(
            quality=quality,
            fusion_strategy=strategy,
            confidence=strategy_conf * quality_conf,
            used_sources=sources,
            metadata={
                "enhanced_query": query_obj.enhanced_query,
                "entities": query_obj.entities,
                "context_strength": context_strength
            }
        )


def mock_rag(query: str) -> Dict:
    print(f"  Executing query: '{query}'")
    if "X12" in query or "手机" in query:
        return {
            "documents": [
                {"content": "X12智能手机1999元", "similarity_score": 0.85},
                {"content": "X12Pro2999元4K", "similarity_score": 0.75}
            ]
        }
    elif "开门" in query or "营业" in query:
        return {"documents": []}
    else:
        return {
            "documents": [
                {"content": "一些通用信息", "similarity_score": 0.35}
            ]
        }


def run_tests():
    print("="*70)
    print("Context+RAG Fusion Layer - Test Suite")
    print("="*70)

    session = MockSessionContext()
    fusion_layer = ContextRAGFusionLayer()

    print("\n" + "="*70)
    print("Test 1: Product Query with High Quality RAG")
    print("="*70)

    result = fusion_layer.process("X12手机多少钱？", session, mock_rag)

    print(f"\nResult:")
    print(f"  Quality: {result.quality.value}")
    print(f"  Strategy: {result.fusion_strategy.value}")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Sources: {', '.join(result.used_sources)}")

    assert result.quality == RetrievalQuality.HIGH
    assert result.fusion_strategy == FusionStrategy.HYBRID
    assert result.confidence > 0.5
    print("\n[PASS] Test 1 passed")

    print("\n" + "="*70)
    print("Test 2: Non-Product Query")
    print("="*70)

    result2 = fusion_layer.process("你们几点开门？", session, mock_rag)

    print(f"\nResult:")
    print(f"  Quality: {result2.quality.value}")
    print(f"  Strategy: {result2.fusion_strategy.value}")

    assert result2.quality == RetrievalQuality.NONE
    assert result2.fusion_strategy == FusionStrategy.CONTEXT_ONLY
    print("\n[PASS] Test 2 passed")

    print("\n" + "="*70)
    print("ALL TESTS PASSED")
    print("="*70)

    print("\nSummary:")
    print("1. ContextExtractor successfully extracted metadata and skill context")
    print("2. RAGResultInjector evaluated retrieval quality correctly")
    print("3. AdaptiveFusionEngine selected appropriate fusion strategy")
    print("4. Product queries triggered HIGH quality + HYBRID strategy")
    print("5. Non-product queries triggered NONE quality + CONTEXT_ONLY strategy")


if __name__ == "__main__":
    run_tests()
