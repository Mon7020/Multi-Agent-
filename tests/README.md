# 测试文件夹说明

## 📁 文件夹结构

```
test2langchain/
├── tests/                    # 测试文件文件夹
│   ├── __init__.py
│   ├── benchmark.py          # 基准测试
│   ├── benchmark_test_data.json
│   ├── evaluation_guide.md   # 评估指南
│   ├── full_evaluation.py    # 全套评估
│   ├── ground_truth_dataset.json
│   ├── run_benchmark.py      # 快速运行基准测试
│   ├── smart_evaluation.py   # 智能评估
│   ├── test_chinese_model.py # 中文模型测试
│   ├── test_context_engineering.py  # 上下文工程测试
│   ├── test_evaluation.py   # 评估测试
│   ├── test_session_context.py  # 会话上下文测试
│   └── test_skills.py        # 技能测试
│
├── reports/                  # 测试报告文件夹
│   ├── benchmark_report_*.json (3个)
│   ├── full_evaluation_report_*.json (9个)
│   └── smart_evaluation_report_*.json (3个)
```

## 📝 tests/ 文件夹说明

### 测试文件

| 文件名 | 说明 |
|--------|------|
| `benchmark.py` | 基准测试主程序 |
| `run_benchmark.py` | 快速运行基准测试脚本 |
| `full_evaluation.py` | 全套性能评估测试 |
| `smart_evaluation.py` | 智能评估测试（语义匹配） |
| `test_context_engineering.py` | 上下文工程测试（8个测试用例） |
| `test_chinese_model.py` | 中文向量模型测试 |
| `test_evaluation.py` | 评估功能测试 |
| `test_session_context.py` | 会话上下文测试 |
| `test_skills.py` | 技能测试 |

### 数据文件

| 文件名 | 说明 |
|--------|------|
| `benchmark_test_data.json` | 基准测试数据集 |
| `ground_truth_dataset.json` | 标准答案数据集（15个标注查询） |
| `evaluation_guide.md` | 评估指南文档 |

## 📊 reports/ 文件夹说明

### 报告类型

| 类型 | 数量 | 说明 |
|------|------|------|
| `benchmark_report_*.json` | 3个 | 基准测试报告 |
| `full_evaluation_report_*.json` | 9个 | 全套评估报告 |
| `smart_evaluation_report_*.json` | 3个 | 智能评估报告 |

### 报告格式

每个报告都是 JSON 格式，包含：
- `timestamp`: 测试时间
- `test_type`: 测试类型
- `metrics`: 性能指标
- `results`: 详细结果

## 🚀 运行测试

### 运行所有测试

```bash
cd projects/test2langchain
python -m pytest tests/ -v
```

### 运行特定测试

```bash
# 上下文工程测试
python -m pytest tests/test_context_engineering.py -v

# 基准测试
python tests/run_benchmark.py

# 智能评估
python tests/smart_evaluation.py

# 全套评估
python tests/full_evaluation.py
```

### 查看报告

```bash
# 列出所有报告
ls reports/

# 查看最新报告
cat reports/$(ls -t reports/ | head -1)
```

## 📈 测试报告模板

```json
{
  "timestamp": "2026-04-07T10:00:00",
  "test_type": "benchmark|full_evaluation|smart_evaluation",
  "environment": {
    "model": "shibing624/text2vec-base-chinese",
    "chroma_version": "...",
    "embedding_dimension": 768
  },
  "metrics": {
    "total_queries": 15,
    "success_rate": 0.93,
    "avg_recall": 0.75,
    "avg_precision": 0.70,
    "avg_latency_ms": 134
  },
  "results": [
    {
      "query": "X12 Pro手机",
      "expected_docs": ["doc1", "doc2"],
      "retrieved_docs": [...],
      "metrics": {...}
    }
  ]
}
```

## 🔄 更新历史

- **2026-04-07**: 创建文件结构
  - 将测试文件统一放入 `tests/` 文件夹
  - 创建 `reports/` 文件夹存放测试报告
  - 更新导入路径

## 📌 注意事项

1. 所有测试文件使用相对导入，确保可以从项目根目录运行
2. 报告文件按时间戳命名，便于追踪历史
3. 建议定期清理旧报告（保留最近30天）
4. 测试数据文件（JSON）不应修改，作为基准数据集

## 🎯 最佳实践

### 添加新测试

1. 在 `tests/` 文件夹中创建新文件
2. 使用 `test_*.py` 命名规范
3. 更新 `tests/README.md`

### 生成新报告

1. 运行相应测试脚本
2. 报告自动保存到 `reports/` 文件夹
3. 报告命名格式：`{test_type}_report_{timestamp}.json`

### 查看测试覆盖率

```bash
python -m pytest tests/ --cov=tools --cov-report=html
```

---

**最后更新**: 2026-04-07
