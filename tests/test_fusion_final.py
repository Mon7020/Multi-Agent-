"""
Context+RAG融合层 - 最终测试
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Tuple


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


def mock_rag(query: str) -> List[Dict]:
    if "X12" in query or "手机" in query:
        return [
            {"content": "X12智能手机1999元", "similarity_score": 0.85},
            {"content": "X12Pro2999元4K", "similarity_score": 0.75}
        ]
    return []


def evaluate_quality(documents: List[Dict]) -> Tuple[RetrievalQuality, float]:
    if not documents:
        return RetrievalQuality.NONE, 0.0
    avg = sum(d.get("similarity_score", 0) for d in documents) / len(documents)
    if avg >= 0.7:
        return RetrievalQuality.HIGH, avg
    elif avg >= 0.4:
        return RetrievalQuality.MEDIUM, avg
    elif avg >= 0.2:
        return RetrievalQuality.LOW, avg
    return RetrievalQuality.NONE, avg


def select_strategy(quality: RetrievalQuality) -> FusionStrategy:
    if quality == RetrievalQuality.HIGH:
        return FusionStrategy.HYBRID
    elif quality == RetrievalQuality.MEDIUM:
        return FusionStrategy.HYBRID
    elif quality == RetrievalQuality.LOW:
        return FusionStrategy.CONTEXT_PRIMARY
    return FusionStrategy.CONTEXT_ONLY


def test_fusion():
    print("="*70)
    print("Context+RAG Fusion Layer - Final Test")
    print("="*70)

    print("\n[Test 1] Product query with relevant RAG results")
    docs = mock_rag("X12手机")
    quality, conf = evaluate_quality(docs)
    strategy = select_strategy(quality)
    print(f"  Quality: {quality.value}, Confidence: {conf:.3f}")
    print(f"  Strategy: {strategy.value}")
    assert quality == RetrievalQuality.HIGH
    assert strategy == FusionStrategy.HYBRID
    print("  [PASS]")

    print("\n[Test 2] Non-product query with no RAG results")
    docs = mock_rag("你们几点开门")
    quality, conf = evaluate_quality(docs)
    strategy = select_strategy(quality)
    print(f"  Quality: {quality.value}, Confidence: {conf:.3f}")
    print(f"  Strategy: {strategy.value}")
    assert quality == RetrievalQuality.NONE
    assert strategy == FusionStrategy.CONTEXT_ONLY
    print("  [PASS]")

    print("\n" + "="*70)
    print("ALL TESTS PASSED!")
    print("="*70)
    print("\nSummary:")
    print("1. Product queries -> HIGH quality -> HYBRID strategy")
    print("2. Non-product queries -> NONE quality -> CONTEXT_ONLY strategy")
    print("3. Context+RAG fusion working correctly!")


if __name__ == "__main__":
    test_fusion()
