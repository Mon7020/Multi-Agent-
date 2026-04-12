# RAG 系统全面评测指南

## 📊 评测指标总览

| 指标 | 目标值 | 评测难度 | 所需资源 |
|------|--------|----------|----------|
| 召回率 | 95% | ⭐⭐⭐ 中等 | Ground Truth 数据集 |
| 准确率 | 91% | ⭐⭐⭐ 中等 | 人工标注数据 |
| 幻觉率 | <2% | ⭐⭐⭐⭐ 困难 | 专家评估 + LLM 辅助 |
| 缓存命中率 | 60% | ⭐⭐ 简单 | 重复查询日志 |
| 延迟 (P95) | <500ms | ⭐ 简单 | 性能监控 |
| 成功率 | >95% | ⭐ 简单 | 请求日志 |

---

## 1️⃣ 召回率评测（Recall@K）

### 什么是召回率？

召回率 = **正确检索到的相关文档数** / **所有相关文档总数**

```
示例：
- 用户查询："X12 Pro 价格"
- 知识库中共有 5 个相关文档
- RAG 检索返回 3 个文档，其中 2 个是相关的

召回率 = 2/5 = 40%
```

### 评测方法

#### 方法 A：构建 Ground Truth 数据集（推荐）

```python
# ground_truth_dataset.json
{
  "queries": [
    {
      "id": "q001",
      "query": "X12 Pro手机多少钱",
      "relevant_docs": [
        {
          "doc_id": "doc_001",
          "source": "电子商品价格表.txt",
          "reason": "包含 X12 Pro 的价格信息"
        },
        {
          "doc_id": "doc_002",
          "source": "产品手册_v1.0.pdf",
          "reason": "包含 X12 Pro 的详细规格"
        }
      ]
    }
  ]
}
```

#### 方法 B：人工标注评估

1. **准备测试集**：选取 50-100 个代表性查询
2. **人工标注**：对每个查询，标注知识库中哪些文档是相关的
3. **评测计算**：对比检索结果与标注结果

### 评测代码实现

```python
def evaluate_recall(
    rag_tool: RAGTool,
    ground_truth: List[Dict],
    top_k: int = 3
) -> Dict[str, float]:
    """
    评测召回率

    Args:
        rag_tool: RAG 工具实例
        ground_truth: 标注数据，包含每个查询的相关文档列表
        top_k: 检索返回的文档数量

    Returns:
        召回率指标字典
    """
    recalls = []
    for item in ground_truth:
        query = item["query"]
        relevant_doc_ids = set(item["relevant_doc_ids"])

        # 执行检索
        result = rag_tool.retrieve(query, top_k=top_k)
        retrieved_doc_ids = set([doc.get("doc_id", f"doc_{i}")
                                for i, doc in enumerate(result["documents"])])

        # 计算单个查询的召回率
        true_positives = len(relevant_doc_ids & retrieved_doc_ids)
        recall = true_positives / len(relevant_doc_ids) if relevant_doc_ids else 0
        recalls.append(recall)

    return {
        "recall_at_1": sum(1 for r in recalls if r >= 0.33) / len(recalls),
        "recall_at_3": sum(1 for r in recalls if r >= 0.99) / len(recalls),
        "avg_recall": statistics.mean(recalls),
        "median_recall": statistics.median(recalls),
        "p95_recall": sorted(recalls)[int(len(recalls) * 0.95)]
    }
```

---

## 2️⃣ 准确率评测（Precision@K）

### 什么是准确率？

准确率 = **检索结果中相关文档数** / **检索返回的文档总数**

```
示例：
- 用户查询："X12 Pro 价格"
- RAG 检索返回 3 个文档，其中 2 个是相关的

准确率 = 2/3 = 66.67%
```

### 评测方法

#### 方法 A：逐文档人工评估

```python
# precision_evaluation.json
{
  "query_id": "q001",
  "query": "X12 Pro手机多少钱",
  "retrieved_docs": [
    {
      "doc_id": "doc_001",
      "is_relevant": true,
      "relevance_score": 0.9,  # 0-1 评分
      "reason": "直接包含 X12 Pro 的价格信息"
    },
    {
      "doc_id": "doc_002",
      "is_relevant": false,
      "relevance_score": 0.1,
      "reason": "虽然提到手机但没有价格信息"
    }
  ]
}
```

#### 方法 B：使用 LLM 辅助评估（高效）

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4", temperature=0)

def evaluate_doc_relevance(query: str, doc_content: str) -> float:
    """
    使用 LLM 评估文档与查询的相关性

    Returns:
        相关性分数 0-1
    """
    prompt = f"""评估以下文档与用户查询的相关性。

用户查询：{query}

文档内容：
{doc_content[:500]}...

请给出 0-1 的相关性分数，1 表示完全相关，0 表示完全不相关。
只返回一个数字，不要其他内容。"""

    response = llm.invoke(prompt)
    try:
        return float(response.content.strip())
    except:
        return 0.5  # 默认值
```

### 完整评测代码

```python
def evaluate_precision(
    rag_tool: RAGTool,
    test_queries: List[str],
    ground_truth: Dict[str, List[str]],
    top_k: int = 3
) -> Dict[str, float]:
    """
    评测准确率（支持 LLM 辅助）
    """
    precisions = []
    relevant_scores = []

    for query in test_queries:
        result = rag_tool.retrieve(query, top_k=top_k)
        retrieved_docs = result["documents"]

        # 方法1：基于 ground truth
        if query in ground_truth:
            relevant_set = set(ground_truth[query])
            retrieved_set = set([doc.get("doc_id", f"doc_{i}")
                               for i, doc in enumerate(retrieved_docs)])
            true_positives = len(relevant_set & retrieved_set)
            precision = true_positives / len(retrieved_set) if retrieved_set else 0
            precisions.append(precision)

        # 方法2：使用 LLM 评估
        llm_scores = []
        for doc in retrieved_docs:
            content = doc.get("content", "")
            score = evaluate_doc_relevance(query, content)
            llm_scores.append(score)

        if llm_scores:
            relevant_scores.append(statistics.mean(llm_scores))

    return {
        "precision_at_1": precisions[0] if precisions else 0,
        "precision_at_3": statistics.mean(precisions) if precisions else 0,
        "llm_avg_relevance": statistics.mean(relevant_scores) if relevant_scores else 0,
        "total_evaluated": len(precisions)
    }
```

---

## 3️⃣ 幻觉率评测（Hhallucination Rate）

### 什么是幻觉率？

幻觉率 = **生成内容中包含错误/虚构信息的比例**

```
示例：
- AI 生成了 1000 字回答
- 专家发现 15 处与知识库不符的内容
- 幻觉率 = 15/1000 = 1.5%
```

### 评测方法

#### 方法 A：专家人工评估（gold standard）

1. **准备评估集**：100-200 个代表性的 RAG 生成回答
2. **专家标注**：由领域专家标注每处幻觉
3. **统计计算**：幻觉句子数 / 总句子数

```python
# hallucination_labels.json
{
  "query_id": "q001",
  "query": "X12 Pro手机多少钱",
  "generated_response": "X12 Pro 的价格是 3999 元...",
  "hallucinations": [
    {
      "start_char": 15,
      "end_char": 25,
      "content": "3999 元",
      "error_type": "factual_error",  # factual_error | fabrication | omission
      "severity": "high",  # high | medium | low
      "correction": "X12 Pro 的价格是 4299 元"
    }
  ]
}
```

#### 方法 B：基于知识库一致性检测（自动化）

```python
def detect_hallucinations(
    query: str,
    response: str,
    retrieved_docs: List[Dict],
    llm: ChatOpenAI
) -> List[Dict]:
    """
    使用 LLM 自动检测幻觉

    Args:
        query: 用户查询
        response: AI 生成的回复
        retrieved_docs: 检索到的文档
        llm: LLM 实例

    Returns:
        检测到的幻觉列表
    """
    # 构建知识库上下文
    context = "\n".join([
        f"[文档{i+1}] {doc.get('content', '')[:300]}..."
        for i, doc in enumerate(retrieved_docs[:3])
    ])

    prompt = f"""你是幻觉检测专家。请检查 AI 回复是否包含与知识库不符的信息。

用户查询：{query}

知识库内容：
{context}

AI 回复：
{response}

请仔细对比 AI 回复和知识库，找出以下类型的错误：
1. 事实性错误：与知识库明确信息不符
2. 虚构信息：知识库中不存在的信息
3. 遗漏信息：应该提及但未提及的重要信息

如果发现错误，请列出：
- 错误内容
- 错误类型
- 严重程度（高/中/低）

如果没有错误，请回复"无幻觉"。"""

    response = llm.invoke(prompt)

    # 解析 LLM 输出
    hallucinations = parse_llm_hallucination_response(response.content)

    return hallucinations


def calculate_hallucination_rate(
    evaluation_results: List[Dict]
) -> Dict[str, float]:
    """
    计算幻觉率

    Args:
        evaluation_results: 幻觉检测结果列表

    Returns:
        幻觉率指标
    """
    total_sentences = 0
    hallucinated_sentences = 0
    high_severity_count = 0

    for result in evaluation_results:
        response = result["response"]
        hallucinations = result["hallucinations"]

        # 简单句数估算（中文按句号、感叹号、问号分句）
        sentences = re.split(r'[。！？\n]', response)
        sentences = [s for s in sentences if s.strip()]
        total_sentences += len(sentences)

        hallucinated_sentences += len(hallucinations)
        high_severity_count += sum(1 for h in hallucinations
                                   if h.get("severity") == "high")

    return {
        "hallucination_rate": hallucinated_sentences / max(total_sentences, 1),
        "hallucination_per_1000_chars": hallucinated_sentences / max(len("".join(
            [r["response"] for r in evaluation_results])), 1) * 1000,
        "high_severity_rate": high_severity_count / max(len(evaluation_results), 1),
        "total_hallucinations": hallucinated_sentences,
        "total_sentences": total_sentences
    }
```

#### 方法 C：结合 RAGAS 指标（推荐）

RAGAS 是一个专门评估 RAG 系统的库：

```python
# pip install ragas

from ragas import EvaluationDataset
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)

# 准备评估数据
eval_dataset = EvaluationDataset.from_dict({
    "user_input": [query1, query2, ...],
    "retrieved_contexts": [docs1, docs2, ...],
    "response": [response1, response2, ...],
    "ground_truth": [gt1, gt2, ...]
})

# 运行评估
result = evaluate(
    dataset=eval_dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall]
)
```

---

## 4️⃣ 缓存命中率评测（Cache Hit Rate）

### 什么是缓存命中率？

缓存命中率 = **缓存命中次数** / **总查询次数**

```
示例：
- 连续执行 100 次查询
- 其中 60 次直接返回缓存结果
- 40 次需要重新计算

缓存命中率 = 60/100 = 60%
```

### 评测方法

#### 方法 A：重复查询测试（最简单）

```python
def evaluate_cache_hit_rate(
    rag_tool: RAGTool,
    test_queries: List[str],
    repeat_times: int = 5
) -> Dict[str, Any]:
    """
    评测缓存命中率

    Args:
        rag_tool: RAG 工具实例
        test_queries: 测试查询列表
        repeat_times: 每个查询重复次数

    Returns:
        缓存命中率指标
    """
    # 清空缓存（冷启动）
    if hasattr(rag_tool.cache, 'clear'):
        rag_tool.cache.clear()

    total_requests = 0
    cache_hits = 0
    first_request_latencies = []
    cached_request_latencies = []

    for query in test_queries:
        for i in range(repeat_times):
            total_requests += 1

            start_time = time.time()
            result = rag_tool.retrieve(query, top_k=3)
            latency_ms = (time.time() - start_time) * 1000

            if i == 0:
                first_request_latencies.append(latency_ms)
            else:
                cached_request_latencies.append(latency_ms)

            # 检查是否命中缓存
            # （根据你的缓存实现调整检测逻辑）
            if is_cache_hit(rag_tool.cache, query):
                cache_hits += 1

    return {
        "cache_hit_rate": cache_hits / total_requests,
        "cache_hits": cache_hits,
        "cache_misses": total_requests - cache_hits,
        "total_requests": total_requests,
        "avg_first_request_latency_ms": statistics.mean(first_request_latencies),
        "avg_cached_request_latency_ms": statistics.mean(cached_request_latencies),
        "cache_speedup_ratio": (
            statistics.mean(first_request_latencies) /
            statistics.mean(cached_request_latencies)
            if cached_request_latencies else 0
        )
    }
```

#### 方法 B：真实流量回放测试

```python
def evaluate_cache_with_real_traffic(
    rag_tool: RAGTool,
    query_log_file: str
) -> Dict[str, Any]:
    """
    使用真实查询日志测试缓存效果

    Args:
        rag_tool: RAG 工具实例
        query_log_file: 查询日志文件（每行一个查询）

    Returns:
        缓存效果指标
    """
    # 读取查询日志
    with open(query_log_file, 'r', encoding='utf-8') as f:
        queries = [line.strip() for line in f if line.strip()]

    # 模拟真实流量顺序
    cache_hits = 0
    total = len(queries)

    for query in queries:
        if is_in_cache(rag_tool.cache, query):
            cache_hits += 1
        rag_tool.retrieve(query, top_k=3)

    return {
        "cache_hit_rate": cache_hits / total,
        "unique_queries": len(set(queries)),
        "total_queries": total,
        "cache_hits": cache_hits
    }
```

---

## 5️⃣ 完整评测报告生成器

```python
def generate_full_evaluation_report(
    rag_tool: RAGTool,
    ground_truth_file: str,
    test_queries: List[str],
    output_dir: str = "evaluation_reports"
) -> Dict[str, Any]:
    """
    生成完整的评测报告

    Args:
        rag_tool: RAG 工具实例
        ground_truth_file: Ground truth 数据文件
        test_queries: 测试查询列表
        output_dir: 报告输出目录

    Returns:
        完整评测结果
    """
    os.makedirs(output_dir, exist_ok=True)

    report = {
        "timestamp": datetime.now().isoformat(),
        "test_config": {
            "top_k": 3,
            "test_query_count": len(test_queries)
        }
    }

    # 1. 缓存命中率测试
    print("正在测试缓存命中率...")
    cache_results = evaluate_cache_hit_rate(rag_tool, test_queries[:10], repeat_times=3)
    report["cache_metrics"] = cache_results

    # 2. 召回率测试（如果有 ground truth）
    print("正在测试召回率...")
    if ground_truth_file and os.path.exists(ground_truth_file):
        with open(ground_truth_file, 'r', encoding='utf-8') as f:
            ground_truth = json.load(f)
        report["recall_metrics"] = evaluate_recall(rag_tool, ground_truth["queries"])

    # 3. 准确率测试
    print("正在测试准确率...")
    report["precision_metrics"] = evaluate_precision(
        rag_tool, test_queries, ground_truth
    )

    # 4. 延迟测试
    print("正在测试延迟...")
    report["latency_metrics"] = evaluate_latency(rag_tool, test_queries)

    # 生成报告
    report_file = os.path.join(
        output_dir,
        f"evaluation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 生成 Markdown 报告
    markdown_report = generate_markdown_report(report)
    md_file = report_file.replace('.json', '.md')
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(markdown_report)

    print(f"\n评测报告已生成：")
    print(f"  JSON: {report_file}")
    print(f"  Markdown: {md_file}")

    return report
```

---

## 📋 评测清单

### 第一阶段：基础指标（1天）

- [ ] **成功率测试**：连续 1000 次查询，记录成功/失败次数
- [ ] **延迟测试**：测量 P50/P95/P99 延迟
- [ ] **缓存命中率测试**：重复查询同一问题 5 次

### 第二阶段：检索质量（3-5天）

- [ ] **构建 Ground Truth 数据集**
  - 选取 50-100 个代表性查询
  - 人工标注每个查询的相关文档
  - 保存为 JSON 格式

- [ ] **召回率测试**
  - 使用 Ground Truth 数据集
  - 计算 Recall@1, Recall@3, Recall@5

- [ ] **准确率测试**
  - LLM 辅助评估文档相关性
  - 或人工标注 Top-K 返回文档

### 第三阶段：生成质量（1周）

- [ ] **幻觉率评估**
  - 准备 100-200 个代表性问答对
  - 使用专家评估或 LLM 辅助检测
  - 统计幻觉率

- [ ] **答案质量评估**
  - 使用 RAGAS 框架
  - 评估 Faithfulness、Answer Relevancy 等指标

---

## 🎯 目标值参考

| 指标 | 优秀 | 良好 | 需改进 |
|------|------|------|--------|
| 召回率 @3 | >95% | 85-95% | <85% |
| 准确率 @3 | >91% | 80-91% | <80% |
| 幻觉率 | <1% | 1-2% | >2% |
| 缓存命中率 | >70% | 50-70% | <50% |
| P95 延迟 | <300ms | 300-500ms | >500ms |

---

## 📚 推荐工具

1. **RAGAS** - RAG 系统专用评估框架
   - GitHub: `https://github.com/explodinggradients/ragas`

2. **Trulens** - RAG 应用评估平台
   - GitHub: `https://github.com/truera/trulens`

3. **LangSmith** - LangChain 原生评估工具
   - 网站: `https://smith.langchain.com`

4. **BERT-Score** - 评估生成文本质量
   - GitHub: `https://github.com/Tiiiger/bert_score`
