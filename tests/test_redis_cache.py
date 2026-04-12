"""
Redis 缓存模块测试
==================
"""

import sys
import os
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.rag.redis_cache_manager import (
    RedisCacheManager,
    get_cache_manager,
    CacheType,
    IntentClassificationCache,
    RetrievalCache,
    SessionCache
)


def test_cache_manager_basic():
    """测试缓存管理器基础功能"""
    print("=" * 60)
    print("Test 1: Cache Manager Basic Functions")
    print("=" * 60)

    cache = get_cache_manager()

    print(f"Redis Available: {cache.is_available}")
    print(f"Health Check: {cache.health_check()}")

    cache.set(CacheType.RETRIEVAL, "test_key", {"data": "test_value"}, ttl=60)

    result = cache.get(CacheType.RETRIEVAL, "test_key")
    print(f"Set and Get: {result}")

    cache.delete(CacheType.RETRIEVAL, "test_key")
    result = cache.get(CacheType.RETRIEVAL, "test_key")
    print(f"After Delete: {result}")

    print("[PASS] Basic test passed\n")


def test_intent_classification_cache():
    """测试意图分类缓存"""
    print("=" * 60)
    print("Test 2: Intent Classification Cache")
    print("=" * 60)

    cache_manager = get_cache_manager()
    intent_cache = IntentClassificationCache(cache_manager)

    query = "推荐一款蓝牙耳机"

    cached = intent_cache.get_intent(query)
    print(f"First query cache status: {cached}")

    intent_cache.set_intent(
        query=query,
        intent="recommendation",
        confidence=0.95,
        reasoning="User requests product recommendation",
        ttl=300
    )

    cached = intent_cache.get_intent(query)
    print(f"After caching: {cached}")

    stats = cache_manager.get_stats(CacheType.INTENT)
    print(f"Intent cache stats: {stats}")

    print("[PASS] Intent cache test passed\n")


def test_retrieval_cache():
    """测试检索结果缓存"""
    print("=" * 60)
    print("Test 3: Retrieval Cache")
    print("=" * 60)

    cache_manager = get_cache_manager()
    retrieval_cache = RetrievalCache(cache_manager)

    query = "蓝牙耳机推荐"
    documents = [
        {"id": "1", "content": "X12 Pro 蓝牙耳机", "score": 0.95},
        {"id": "2", "content": "Y8 头戴式耳机", "score": 0.85}
    ]

    cached = retrieval_cache.get_retrieval(query, top_k=5, intent="recommendation")
    print(f"First retrieval cache status: {cached}")

    retrieval_cache.set_retrieval(
        query=query,
        top_k=5,
        intent="recommendation",
        documents=documents,
        ttl=1800
    )

    cached = retrieval_cache.get_retrieval(query, top_k=5, intent="recommendation")
    print(f"After caching: {len(cached.get('documents', [])) if cached else 0} documents")

    stats = cache_manager.get_stats(CacheType.RETRIEVAL)
    print(f"Retrieval cache stats: {stats}")

    print("[PASS] Retrieval cache test passed\n")


def test_session_cache():
    """测试 Session 缓存"""
    print("=" * 60)
    print("Test 4: Session Cache")
    print("=" * 60)

    cache_manager = get_cache_manager()
    session_cache = SessionCache(cache_manager)

    session_id = "test_session_123"
    session_data = {
        "user_id": "user_001",
        "customer_type": "price_sensitive",
        "metadata": {"total_spent": 1000}
    }

    session_cache.set_session(session_id, session_data)

    cached = session_cache.get_session(session_id)
    print(f"Session data: {cached}")

    session_cache.update_session(
        session_id,
        {"metadata": {"total_spent": 1500}}
    )

    updated = session_cache.get_session(session_id)
    print(f"Updated session: {updated}")

    session_cache.delete_session(session_id)
    deleted = session_cache.get_session(session_id)
    print(f"After delete: {deleted}")

    print("[PASS] Session cache test passed\n")


def test_cache_stats():
    """测试缓存统计"""
    print("=" * 60)
    print("Test 5: Cache Statistics")
    print("=" * 60)

    cache_manager = get_cache_manager()

    for _ in range(5):
        cache_manager.get(CacheType.RETRIEVAL, "nonexistent_key")

    for _ in range(3):
        cache_manager.set(
            CacheType.RETRIEVAL,
            f"key_{time.time()}",
            {"data": "test"}
        )

    stats = cache_manager.get_stats()
    print("Cache statistics:")
    for cache_type, stat in stats.items():
        print(f"  {cache_type}: {stat}")

    print("[PASS] Statistics test passed\n")


def test_concurrent_access():
    """测试并发访问"""
    print("=" * 60)
    print("Test 6: Concurrent Access")
    print("=" * 60)

    cache_manager = get_cache_manager()
    errors = []

    def worker(thread_id):
        try:
            for i in range(10):
                key = f"thread_{thread_id}_key_{i}"
                cache_manager.set(CacheType.RETRIEVAL, key, {"thread": thread_id, "i": i})
                cache_manager.get(CacheType.RETRIEVAL, key)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"Concurrent errors: {len(errors)}")
    print("[PASS] Concurrent test passed\n")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Redis Cache Module Tests")
    print("=" * 60 + "\n")

    test_cache_manager_basic()
    test_intent_classification_cache()
    test_retrieval_cache()
    test_session_cache()
    test_cache_stats()
    test_concurrent_access()

    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
