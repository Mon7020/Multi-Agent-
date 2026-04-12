# Test2LangChain GitHub 上传文件筛选指南

> 生成时间: 2026-04-12
> 项目: 基于 LangChain + DeepSeek 的智能客服系统

---

## 📋 文件分类总览

| 类别 | 数量 | 说明 |
|------|------|------|
| **必须保留** | 约 60+ 个文件 | 核心源代码、配置、文档 |
| **必须排除** | 约 20+ 个文件/目录 | 敏感信息、缓存、依赖、生成文件 |
| **可选保留** | 约 10+ 个文件 | 测试数据、示例报告 |

---

## ✅ 必须保留的文件

### 1. 项目配置（根目录）

```
.env.example              # 环境变量模板（不含敏感信息）
.gitignore               # Git忽略配置
requirements.txt         # Python依赖
README.md                # 项目说明文档
V3_QUICKSTART.md         # V3快速启动指南
agent_test_guide.md      # Agent测试指南
agent_test_suite.py      # Agent测试套件
项目简介.md               # 中文项目简介（可选）
```

### 2. 后端代码（backend/）

```
backend/
├── requirements.txt              # 后端依赖
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI主入口
│   ├── config.py                 # 应用配置
│   ├── schemas.py                # Pydantic模型
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── chat.py           # 聊天接口
│   │       ├── skills.py         # 技能接口
│   │       ├── health.py         # 健康检查
│   │       ├── evaluation.py     # 评估接口
│   │       ├── knowledge_base.py # 知识库接口
│   │       └── metrics.py        # 指标接口
│   └── services/
│       ├── __init__.py
│       ├── chat_service_v2.py    # 聊天服务V2
│       ├── chat_service_v3.py    # 聊天服务V3
│       └── evaluation_service.py # 评估服务
```

### 3. 前端代码（frontend/）

```
frontend/
├── index.html                    # HTML入口
├── package.json                  # npm配置
├── vite.config.js               # Vite配置（如果有）
└── src/
    ├── App.vue                   # 主应用组件
    ├── main.js                   # 入口文件（如果有）
    ├── api/
    │   └── index.js              # API调用封装
    └── components/
        └── ChatPanel.vue         # 聊天面板组件
```

**注意**: 不要上传 `frontend/node_modules/` 和 `frontend/.vite/`

### 4. Agent代码（agents/）

```
agents/
├── __init__.py
└── supervisor_agent.py           # 主管Agent实现
```

### 5. 核心模块（core/）

```
core/
├── __init__.py
├── agent_factory.py              # Agent工厂
├── logger.py                     # 日志系统
└── session_context.py            # 会话上下文管理
```

### 6. 配置模块（config/）

```
config/
├── __init__.py
└── settings.py                   # 全局配置
```

### 7. 工具层（tools/）

```
tools/
├── __init__.py
├── rag_tool.py                   # RAG主工具
├── amap_weather_tool.py          # 高德天气工具
├── tavily_search_tool.py         # Tavily搜索工具
└── rag/                          # RAG子模块（如果有）
    └── __init__.py
```

### 8. 技能系统（skills/）

```
skills/
├── __init__.py
├── base.py                       # 技能基类
├── manager.py                    # 技能管理器
├── registry.py                   # 技能注册表
├── data_loader.py                # 数据加载器
└── skills/                       # 具体技能实现
    ├── sales_skill.py
    ├── tech_support_skill.py
    └── negotiation_skill.py
```

### 9. 评估模块（evaluation/）

```
evaluation/
├── __init__.py
├── evaluator.py                  # 评估器
├── semantic_evaluator.py         # 语义评估器
├── metrics.py                    # 评估指标
└── tracker.py                    # 追踪器
```

### 10. 监控模块（monitoring/）

```
monitoring/
├── __init__.py
└── metrics.py                    # 性能指标监控
```

### 11. 数据文件（data/）

```
data/
├── docs/                         # 知识库文档
│   ├── 产品手册_v1.0.pdf
│   ├── 常见问题_FAQ.txt
│   ├── 招呼消息.txt
│   ├── 用户指南_2024.docx
│   └── 电子商品价格表.txt
├── skills_data/                  # 技能数据
│   ├── product_discounts.yaml
│   └── tech_support_kb.yaml
└── memory/                       # 记忆存储（可选）
    └── long_term/
        └── .gitkeep              # 保留空目录
```

### 12. 测试文件（tests/）

```
tests/
├── __init__.py
├── README.md                     # 测试说明
├── evaluation_guide.md           # 评估指南
├── benchmark.py                  # 基准测试
├── full_evaluation.py            # 完整评估
├── full_evaluation_v2.py         # 评估V2
├── semantic_evaluation.py        # 语义评估
├── smart_evaluation.py           # 智能评估
├── test_context_engineering.py   # 上下文工程测试
├── test_skills.py                # 技能测试
├── test_v3_api.py                # V3 API测试
├── test_evaluation.py            # 评估测试
├── test_api_fix.py               # API修复测试
├── test_fix_verification.py      # 修复验证
├── benchmark_test_data.json      # 测试数据
└── ground_truth_dataset.json     # 基准数据集
```

### 13. 文档（docs/）

```
docs/
├── context_engineering_implementation.md    # 上下文工程实现
├── context_rag_fusion_design.md             # RAG Fusion设计
├── HYBRID_SEARCH_WEIGHT_ANALYSIS.md         # 混合搜索权重分析
├── INTENT_RECOGNITION_ANALYSIS.md           # 意图识别分析
├── RAG_SELF_RAG_ANALYSIS.md                 # Self-RAG分析
├── SEMANTIC_INTENT_IMPLEMENTATION.md        # 语义意图实现
└── 系统问题诊断报告.md                        # 诊断报告（可选）
```

---

## ❌ 必须排除的文件/目录

### 1. 敏感信息

```
.env                          # 包含API密钥等敏感信息
.env.local
.env.*.local
*.pem
*.key
secrets.yaml
secrets.json
```

### 2. Python缓存

```
__pycache__/                  # Python字节码缓存
*.py[cod]
*$py.class
*.so
.pytest_cache/
.mypy_cache/
.dmypy.json
.pytype/
cython_debug/
```

### 3. 前端依赖和构建

```
frontend/node_modules/        # npm依赖（可通过npm install安装）
frontend/.vite/               # Vite缓存
frontend/dist/                # 构建输出（可选保留，建议排除）
npm-debug.log*
yarn-debug.log*
yarn-error.log*
*.local
```

### 4. 向量数据库和生成数据

```
chroma_data/                  # ChromaDB向量数据库（大文件，可重建）
*.sqlite3
*.db
*.bin
vector_store/
embeddings_cache/
```

### 5. 日志文件

```
logs/
*.log
backend/*.log
backend.log
log/
debug_output.txt
```

### 6. 运行时生成的报告（可选排除）

```
full_evaluation_report_*.json
full_evaluation_report_*.md
semantic_evaluation_report_*.json
benchmark_report_*.txt
reports/*.json                # 如果reports/目录只有生成的报告
reports/*.md
reports/*.txt
```

### 7. IDE和编辑器文件

```
.idea/                        # JetBrains IDE
.vscode/                      # VS Code（可选保留配置）
*.swp
*.swo
*~
.DS_Store                     # macOS
Thumbs.db                     # Windows
```

### 8. Claude Code相关

```
.claude/                      # Claude Code本地配置
```

### 9. 调试和诊断脚本（可选排除）

```
check_chroma_content.py       # 诊断脚本
check_chroma_path.py
check_vector_dim.py
diagnose_bm25.py
diagnose_rag.py
quick_diagnose.py
rebuild_index.py              # 重建脚本
rebuild_vectors.py
rebuild_with_optimization.py
create_resume.js              # 简历生成脚本
create_resume_v2.js
create_resume_v3.js
md_to_pdf.py                  # PDF生成
real_agent_client.py          # 测试客户端
```

### 10. 分发和打包

```
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
.coverage
htmlcov/
.tox/
.nox/
```

---

## ⚠️ 可选保留的文件（根据需求）

### 1. 测试报告（reports/）

**建议**: 可以保留几个代表性的报告作为示例，但不保留所有历史报告。

```
# 保留示例报告（选1-2个最新的）
reports/full_evaluation_report_20260410_095038.md
reports/full_evaluation_report_20260410_095038.json

# 排除历史报告
reports/full_evaluation_report_*.json   # 其他日期
reports/full_evaluation_report_*.md
reports/benchmark_report_*.txt
```

### 2. 用户配置文件（data/memory/）

**建议**: 如果包含真实用户数据，应该排除。

```
# 排除
# data/memory/long_term/*_profile.json

# 保留（如果是示例/测试数据）
data/memory/long_term/test_user_001_profile.json
```

### 3. 前端构建文件（frontend/dist/）

**建议**: 排除，因为可以通过 `npm run build` 重新生成。

```
# 排除
frontend/dist/
```

---

## 📁 推荐的 .gitignore 配置

项目已配置好 `.gitignore`，以下是关键规则：

```gitignore
# 1. 敏感信息
.env
.env.local
.env.*.local
*.pem
*.key

# 2. Python缓存
__pycache__/
*.py[cod]
*.so
.pytest_cache/
.mypy_cache/

# 3. 向量数据库
chroma_data/
*.sqlite3
*.db
vector_store/

# 4. 日志
logs/
*.log
debug_output.txt

# 5. 前端依赖
frontend/node_modules/
frontend/.vite/

# 6. 运行时报告
full_evaluation_report_*.json
full_evaluation_report_*.md
benchmark_report_*.txt

# 7. 用户数据（可选）
data/memory/long_term/*_profile.json

# 8. IDE
.idea/
.vscode/
.DS_Store

# 9. Claude Code
.claude/
```

---

## 📊 文件清单汇总

### 核心必传文件统计

| 目录 | 文件数 | 说明 |
|------|--------|------|
| 根目录 | 8 | 配置、文档、入口 |
| backend/ | 16 | API、服务、配置 |
| frontend/src/ | 4 | Vue组件、API |
| agents/ | 2 | Agent实现 |
| core/ | 4 | 核心模块 |
| config/ | 2 | 全局配置 |
| tools/ | 4 | 工具实现 |
| skills/ | 5+ | 技能系统 |
| evaluation/ | 5 | 评估模块 |
| monitoring/ | 2 | 监控 |
| data/docs/ | 5 | 知识库文档 |
| data/skills_data/ | 2 | 技能数据 |
| tests/ | 15+ | 测试文件 |
| docs/ | 7 | 技术文档 |
| **总计** | **约 80+** | **核心代码和文档** |

---

## 🚀 上传前检查清单

- [ ] 复制 `.env.example` 为 `.env` 并在本地配置API密钥
- [ ] 确认 `.gitignore` 包含所有敏感文件和缓存
- [ ] 删除或排除 `__pycache__/` 目录
- [ ] 删除或排除 `frontend/node_modules/`
- [ ] 删除或排除 `chroma_data/`
- [ ] 删除或排除 `logs/`
- [ ] 选择性保留/删除 `reports/` 中的历史报告
- [ ] 确认没有包含真实用户数据
- [ ] 运行测试确认项目可用：
  ```bash
  python -m pytest tests/test_context_engineering.py -v
  ```

---

## 📝 上传命令示例

```bash
# 1. 初始化Git（如果还没初始化）
git init

# 2. 添加所有要上传的文件
git add .

# 3. 检查要上传的文件列表
git status

# 4. 提交
git commit -m "Initial commit: Test2LangChain智能客服系统"

# 5. 添加远程仓库
git remote add origin https://github.com/yourusername/test2langchain.git

# 6. 推送
git push -u origin master
```

---

## 🔍 常见问题

### Q: 为什么不需要上传 node_modules？
**A**: `node_modules/` 可以通过 `npm install` 根据 `package.json` 重新安装，上传会占用大量空间且容易冲突。

### Q: 为什么不需要上传 chroma_data？
**A**: 向量数据库会在首次运行时自动创建和填充，上传会包含大文件（可能几百MB）。

### Q: 测试报告是否需要上传？
**A**: 建议保留1-2个最新报告作为示例，让其他人了解评估结果格式，但不需要保留所有历史报告。

### Q: .vscode 配置是否需要上传？
**A**: 如果包含团队共享的调试配置可以保留，否则建议排除。

---

**最后更新**: 2026-04-12
