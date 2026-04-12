# GitHub 上传指南

本文档详细说明本项目上传到GitHub时，哪些文件是必须的，哪些不应该上传。

## 📊 项目总体概况

| 类别 | 大小 | 说明 |
|------|------|------|
| Python源代码 | ~2MB | 核心项目文件 |
| 前端代码 | ~50MB | 包含node_modules（不上传） |
| 向量数据库 | ~50MB | ChromaDB数据（不上传） |
| 日志文件 | ~5MB | 运行时日志（不上传） |
| 文档数据 | ~200KB | 知识库文档（上传） |

---

## ✅ 必须上传的文件

### 1. 核心源代码 (必须)
```
agents/              # Agent实现
backend/             # FastAPI后端服务
config/              # 配置文件
  ├── settings.py
  └── __init__.py
core/                # 核心功能模块
data/                # 知识库数据（见下方说明）
docs/                # 项目文档
evaluation/          # 评测模块（包含改进版）
monitoring/          # 监控模块
skills/              # 技能系统
tests/               # 测试脚本
tools/               # 工具模块
```

### 2. 配置和依赖文件 (必须)
```
requirements.txt           # Python依赖
.env.example              # 环境变量模板（不含敏感信息）
backend/requirements.txt   # 后端依赖
frontend/package.json      # 前端依赖配置
frontend/vite.config.js    # Vite配置
```

### 3. 前端源代码和构建文件 (必须)
```
frontend/src/              # 前端源代码
frontend/dist/             # 构建输出（可选，如果需要直接部署）
frontend/index.html        # 入口文件
```

### 4. 文档和说明文件 (必须)
```
README.md                  # 项目主README
V3_QUICKSTART.md          # V3版本快速开始
gent_test_guide.md        # 测试指南
evaluation/README.md      # 评测改进说明
evaluation/IMPROVEMENTS_SUMMARY.md  # 改进总结
```

### 5. 知识库数据文件 (必须)
```
data/docs/                 # 知识库文档
  ├── 产品手册_v1.0.pdf
  ├── 常见问题_FAQ.txt
  ├── 电子商品价格表.txt
  └── ...

data/skills_data/          # 技能数据
  ├── product_discounts.yaml
  └── tech_support_kb.yaml
```

---

## ❌ 不应该上传的文件

### 1. 敏感信息 (绝对不要上传！)
```
.env                       # 包含API密钥等敏感信息 ⚠️
```
**原因**: 包含真实的API密钥（OpenAI、DeepSeek、高德地图、Tavily等）

**替代方案**: 已提供 `.env.example` 模板，用户需要自行复制并重命名

### 2. Python缓存文件 (不要上传)
```
__pycache__/               # Python字节码缓存
*.pyc                      # 编译后的Python文件
.pytest_cache/             # 测试缓存
```
**原因**: 自动生成，占用空间，可重复生成

### 3. 向量数据库 (不要上传)
```
chroma_data/               # ChromaDB向量数据库 (~50MB)
  ├── chroma.sqlite3
  └── */data_level0.bin
```
**原因**:
- 体积大（约50MB）
- 包含生成的向量嵌入，可由源代码重新生成
- 可能包含临时/测试数据

**替代方案**: 提供 `rebuild_index.py` 脚本让用户本地重建

### 4. 日志文件 (不要上传)
```
logs/                      # 日志目录 (~5MB)
*.log                      # 所有日志文件
backend.log
debug_output.txt
```
**原因**: 运行时生成，包含调试信息，可能敏感

### 5. 前端依赖 (不要上传)
```
frontend/node_modules/     # npm依赖 (~43MB)
```
**原因**:
- 体积巨大（约43MB）
- 可通过 `npm install` 重新安装

**替代方案**: 提供 `package.json` 和 `package-lock.json`

### 6. 评测报告和临时文件 (不要上传)
```
full_evaluation_report_*.json     # 评测报告
full_evaluation_report_*.md
semantic_evaluation_report_*.json
benchmark_report_*.txt
*.tmp
*.temp
```
**原因**: 运行评测脚本后生成，不应提交到版本控制

### 7. IDE和编辑器文件 (不要上传)
```
.idea/                     # IntelliJ IDEA
.vscode/                   # VS Code
*.swp                      # Vim交换文件
.DS_Store                  # macOS
Thumbs.db                  # Windows
```

### 8. 用户个人数据 (可选，建议不上传)
```
data/memory/long_term/*_profile.json   # 用户个人配置文件
```
**原因**: 可能包含隐私数据

---

## 📋 文件清单汇总

### 上传统计

| 类别 | 文件数 | 大小(约) | 是否上传 |
|------|--------|----------|----------|
| Python源代码 | ~80个 | 2MB | ✅ 必须 |
| 前端src/ | ~15个 | 100KB | ✅ 必须 |
| 知识库文档 | ~5个 | 180KB | ✅ 必须 |
| 配置文件 | ~5个 | 10KB | ✅ 必须 |
| 项目文档 | ~10个 | 100KB | ✅ 必须 |
| node_modules/ | ~1000+ | 43MB | ❌ 不要 |
| chroma_data/ | ~20个 | 50MB | ❌ 不要 |
| __pycache__/ | ~50个 | 1MB | ❌ 不要 |
| 日志文件 | ~15个 | 5MB | ❌ 不要 |
| .env | 1个 | 1KB | ❌ 不要 |

### 预计上传大小
- **实际代码**: ~3MB
- **知识库数据**: ~200KB
- **总计**: ~3-5MB（非常轻量！）

---

## 🚀 快速上传步骤

### 1. 确保.gitignore已配置
```bash
# 检查.gitignore是否存在
cat .gitignore
```

### 2. 清理不需要的文件
```bash
# 删除Python缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 删除日志
rm -rf logs/*
rm -f *.log backend.log debug_output.txt

# 删除评测报告
rm -f full_evaluation_report_* benchmark_report_*
```

### 3. 准备环境配置
```bash
# 确保.env.example存在且不含敏感信息
cat .env.example
```

### 4. 初始化Git并上传
```bash
# 初始化
git init

# 添加所有文件（.gitignore会自动排除不需要的）
git add .

# 提交
git commit -m "Initial commit: Multi-task QA Assistant with RAG"

# 添加远程仓库
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git

# 推送
git push -u origin main
```

---

## 📝 README模板建议

在上传到GitHub后，建议更新 `README.md` 添加以下章节：

```markdown
## 环境配置

1. 复制环境变量模板：
   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env` 文件，填入你的API密钥：
   - OpenAI API Key
   - DeepSeek API Key
   - 高德地图API Key
   - Tavily API Key

3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

4. 构建向量数据库：
   ```bash
   python rebuild_index.py
   ```

## 运行项目

```bash
# 启动后端
python backend/app/main.py

# 启动前端（开发模式）
cd frontend
npm install
npm run dev
```
```

---

## ⚠️ 重要提醒

1. **永远不要上传 `.env` 文件** - 包含真实的API密钥
2. **永远不要上传 `chroma_data/`** - 可重建，体积大
3. **永远不要上传 `node_modules/`** - 可通过npm安装
4. **定期清理日志文件** - 避免泄露敏感信息

---

## 🔍 验证上传

上传后，验证GitHub仓库只包含：
- ✅ 源代码文件 (.py, .js, .vue等)
- ✅ 配置文件 (requirements.txt, package.json等)
- ✅ 文档文件 (.md)
- ✅ 知识库数据 (.txt, .pdf, .yaml等)
- ❌ 没有 .env 文件
- ❌ 没有 __pycache__ 目录
- ❌ 没有 chroma_data 目录
- ❌ 没有 node_modules 目录
- ❌ 没有 .log 文件
