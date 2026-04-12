const { Document, Packer, Paragraph, TextRun, LevelFormat, AlignmentType, BorderStyle } = require('docx');
const fs = require('fs');

function title(text, size = 28) {
    return new Paragraph({
        children: [new TextRun({ text, font: "黑体", size, bold: true, color: "020617" })],
        spacing: { after: 8, line: 200, lineRule: "auto" }
    });
}

function para(text, size = 21) {
    return new Paragraph({
        children: [new TextRun({ text, size })],
        spacing: { after: 6, line: 200, lineRule: "auto" }
    });
}

function divider() {
    return new Paragraph({
        children: [],
        border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "94A3B8", space: 2 } },
        spacing: { before: 90, after: 20, line: 200, lineRule: "auto" }
    });
}

function mixedPara(runs, spacing) {
    return new Paragraph({
        children: runs.map(r => new TextRun(typeof r === 'string' ? { text: r, size: 21 } : r)),
        spacing: spacing || { after: 6 }
    });
}

function bulletItem(text, size = 21) {
    return new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun({ text, size })],
        spacing: { after: 3, line: 200, lineRule: "auto" }
    });
}

function subTitle(text, size = 21) {
    return new Paragraph({
        children: [new TextRun({ text, size, bold: true })],
        spacing: { before: 10, after: 6, line: 200, lineRule: "auto" }
    });
}

function bulletItemSub(text, size = 20) {
    return new Paragraph({
        numbering: { reference: "bullets2", level: 0 },
        children: [new TextRun({ text, size })],
        spacing: { after: 3, line: 200, lineRule: "auto" }
    });
}

const doc = new Document({
    numbering: {
        config: [
            {
                reference: "bullets",
                levels: [{
                    level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
                    style: { paragraph: { indent: { left: 360, hanging: 240 } } }
                }]
            },
            {
                reference: "bullets2",
                levels: [{
                    level: 0, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT,
                    style: { paragraph: { indent: { left: 600, hanging: 300 } } }
                }]
            },
        ]
    },
    sections: [{
        properties: {
            page: {
                size: { width: 11906, height: 16838 },
                margin: { top: 500, right: 650, bottom: 400, left: 650 }
            }
        },
        children: [
            // ========== 姓名 ==========
            title("[您的姓名]", 28),
            // 职位行
            new Paragraph({
                children: [
                    new TextRun({ text: "大模型应用开发工程师 · 实习  |  ", font: "黑体", size: 21, bold: true, color: "94A3B8" }),
                    new TextRun({ text: "[您的学历] · [专业] · [毕业年份]  |  [您的电话]  |  [您的邮箱]", size: 20, color: "64748B" })
                ],
                spacing: { after: 4, line: 200, lineRule: "auto" }
            }),
            // GitHub行
            new Paragraph({
                children: [new TextRun({ text: "GitHub: [待补充 - 建议将两个项目开源并提供仓库链接，展示代码规范性与工程化水平]", size: 18, color: "94A3B8" })],
                spacing: { after: 8, line: 200, lineRule: "auto" }
            }),
            divider(),

            // ========== 教育背景 ==========
            new Paragraph({
                children: [new TextRun({ text: "教育背景", font: "黑体", size: 22, bold: true, color: "020617" })],
                border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "94A3B8", space: 2 } },
                spacing: { before: 90, after: 20, line: 200, lineRule: "auto" }
            }),
            para("[您的学校] · [专业] · [入学年份] - [毕业年份]", 21),

            // ========== 技术栈 ==========
            new Paragraph({
                children: [new TextRun({ text: "技术栈", font: "黑体", size: 22, bold: true, color: "020617" })],
                border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "94A3B8", space: 2 } },
                spacing: { before: 90, after: 20, line: 200, lineRule: "auto" }
            }),
            bulletItem("AI框架：LangChain 0.3 / AutoGen / LlamaIndex / LangGraph"),
            bulletItem("LLM部署与推理：vLLM / Ollama / DeepSeek API / OpenAI API / 理解 LoRA / QLoRA / GPTQ 量化原理", 20),
            bulletItem("Prompt工程：Few-shot / Chain-of-Thought / Role-play Prompt 设计；通过少样本示例引导格式化输出，随机性降低 40%", 20),
            bulletItem("低代码平台：Coze / Dify / FastGPT"),
            bulletItem("后端开发：Python 3.10 / FastAPI / Uvicorn / Pydantic / 异步编程 (asyncio)"),
            bulletItem("向量数据库：ChromaDB / Milvus（了解企业级向量检索原理）"),
            bulletItem("检索技术：text2vec-base-chinese / BGE-Reranker / BM25 / 混合检索（RRF融合）"),
            bulletItem("缓存：Redis / LocalCache 三级降级"),
            bulletItem("前端：Vue 3 / Vite / WebSocket / SSE"),
            bulletItem("DevOps：Docker / Docker Compose / CI/CD (GitHub Actions) / Linux 服务器运维"),
            bulletItem("大模型基础：理解 Transformer 架构 / 自注意力机制 / RoPE /Tokenizer 原理"),
            bulletItem("竞赛：ACM-ICPC 国际大学生程序设计竞赛 · 铜牌（图论、动态规划、数据结构）"),

            // ========== 项目经历 ==========
            new Paragraph({
                children: [new TextRun({ text: "项目经历", font: "黑体", size: 22, bold: true, color: "020617" })],
                border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "94A3B8", space: 2 } },
                spacing: { before: 90, after: 20, line: 200, lineRule: "auto" }
            }),

            // ---- 项目一 ----
            subTitle("项目一：MultiTaskQAAssistant — 智能客服系统"),
            mixedPara([
                { text: "时间：", bold: true, size: 18 },
                { text: "2026.03.10 — 2026.04.01", size: 18 },
                { text: "  |  角色：", bold: true, size: 18 },
                { text: "独立负责（核心开发者）", size: 18 }
            ], { after: 3 }),
            mixedPara([
                { text: "技术栈：", bold: true, size: 18 },
                { text: "Python 3.10 · FastAPI · LangChain 0.3 · DeepSeek API · ChromaDB · Redis · Vue 3", size: 18 }
            ], { after: 3 }),
            para("基于 LangChain + DeepSeek 构建的智能客服系统，实现多轮对话、RAG 检索增强、多技能协作，系统性能达行业领先水平。"),

            // 难点与解决方案
            subTitle("▌难点与解决方案"),
            bulletItemSub("【长文档截断导致上下文丢失】RAG 检索中超过 LLM 上下文窗口的长文档被强制截断，造成关键信息丢失。尝试方案：引入 Father-Child 分块策略，将文档按语义层级组织（父块 512 tokens / 子块 128 tokens），检索时先定位父块再召回子块，最后通过文档重排序（ReRank）优化最终上下文质量。结果：复杂文档回答完整率从 58% 提升至 89%。", 20),
            bulletItemSub("【多轮对话意图漂移】客户多轮追问后，LLM 容易偏离原始问题主线，生成答非所问的回复。尝试方案：设计意图锚定机制，结合对话历史摘要注入 + 动态 Session 记忆窗口，复杂查询准确率从基线 45% 提升至 82%。", 20),
            bulletItemSub("【Self-RAG 检索开销过大】全量检索导致 API 调用延迟居高不下（P99 > 1500ms）。尝试方案：LLM 自适应判断是否需要检索，仅在低置信度时触发 RAG，延迟降低 60%，同时通过三级缓存（Redis/LocalCache/内存）进一步优化。", 20),

            // 核心架构
            subTitle("▌核心架构设计"),
            bulletItem("Supervisor-Agent 多智能体调度：意图识别（LLM + 规则兜底）→ 任务路由 → Skill 并行执行；设计可插拔 Skill 框架，新增业务场景仅需 ~200 行代码；asyncio.gather 并行执行，效率提升 3.2x"),
            bulletItem("三层 RAG + Self-RAG：Layer1 意图分类+实体提取+复杂度评估 → Layer2 BM25+向量检索+RRF融合+Rerank → Layer3 多源拼接+来源标注；Self-RAG 自适应检索减少无效 API 调用"),
            bulletItem("Context + RAG 双向融合：上下文→RAG 注入客户偏好提升个性化检索；RAG→上下文注入记忆系统；Prompt 工程（Few-shot + 结构化模板）将输出随机性降低 40%"),
            bulletItem("安全与稳定性：pickle→JSON 消除反序列化漏洞；threading.Lock 保证并发安全；Redis/LocalCache 三级缓存降级"),

            // 量化成果（含基线）
            subTitle("▌量化成果（基于 500 条测试集评估）"),
            bulletItem("意图识别准确率：基线 62% → 提升至 85%+（LLM + 规则双层识别）"),
            bulletItem("检索相关度：基线提升 30%（Hybrid Search + Rerank，在内部评测集上验证）"),
            bulletItem("API 响应 P99 < 500ms（三级缓存 + 异步优化）"),
            bulletItem("复杂查询准确率：基线 45% → 82%（Context+RAG 双向融合）"),
            bulletItem("测试用例通过率 95%+ | 代码量 10,500+ 行"),

            // ---- 项目二 ----
            subTitle("项目二：智能会议助手系统"),
            mixedPara([
                { text: "时间：", bold: true, size: 18 },
                { text: "2025.02.10 — 2025.04.10", size: 18 },
                { text: "  |  角色：", bold: true, size: 18 },
                { text: "后端开发工程师（团队 3 人，负责核心架构与 API 服务）", size: 18 },
                { text: "  |  获奖：", bold: true, size: 18 },
                { text: "软件服务外包创新创业大赛 · 省级三等奖", size: 18 }
            ], { after: 3 }),
            mixedPara([
                { text: "技术栈：", bold: true, size: 18 },
                { text: "Python · FastAPI · LangChain · ChromaDB · WebSocket · SSE · Docker · Nginx · Redis", size: 18 }
            ], { after: 3 }),
            para("面向会议的智能助手系统，提供视频通话、AI 会议纪要总结、智能发言稿生成等功能，有效提升会议效率和内容沉淀。"),

            // 难点与解决方案
            subTitle("▌难点与解决方案"),
            bulletItemSub("【会议纪要信息丢失】长会议（>1小时）转录文本超过 LLM 上下文窗口，摘要质量严重下降。尝试方案：引入分层摘要策略——先按语义段落分割，再逐段落提取关键信息，最后融合生成完整摘要。结果：长会议摘要完整率从 51% 提升至 84%。", 20),
            bulletItemSub("【RAG 检索冷启动问题】新会议无历史记录时，RAG 无法提供上下文，导致首次会议发言稿质量差。尝试方案：结合会议议程 + 议题关键词主动构造伪历史上下文注入 Prompt，减少幻觉。", 20),

            // 核心功能开发
            subTitle("▌核心功能开发"),
            bulletItem("AI 会议纪要生成：基于 LangChain 实现会议内容多模态理解与结构化提取；RAG 从历史会议检索相关背景；SSE 流式输出实现「会议结束即出纪要」"),
            bulletItem("智能发言稿生成：RAG 检索历史资料 + 上下文感知内容推荐；Few-shot Prompt 引导结构化输出（背景/论点/总结三段式）"),
            bulletItem("视频通话与实时协作：WebSocket 实现实时音视频信令传输；分布式部署架构支持多实例横向扩展"),

            // 系统架构
            subTitle("▌系统架构与部署"),
            bulletItem("服务端架构设计：RESTful API（FastAPI）+ WebSocket 长连接 + Redis 会话管理 + 消息队列异步处理"),
            bulletItem("服务器配置：Ubuntu 20.04 / Nginx 反向代理 / Docker Compose 多容器编排 / Let&#x2019;s Encrypt HTTPS"),
            bulletItem("CI/CD 流水线：GitHub Actions 自动构建镜像 → 推送到私有镜像仓库 → 服务器自动拉取部署"),
            bulletItem("性能优化：异步 I/O + Redis 缓存 + 数据库连接池，并发处理能力提升 3x"),

            // 量化成果
            subTitle("▌量化成果"),
            bulletItem("服务端 API 响应 P99 < 800ms（异步 + 缓存优化）"),
            bulletItem("RAG 检索相关度提升 25%（混合检索 + Rerank，在历史会议评测集上验证）"),
            bulletItem("长会议摘要完整率：基线 51% → 84%（分层摘要策略）"),
            bulletItem("项目获省级三等奖（软件服务外包创新创业大赛）"),

            // ========== 自我评价 ==========
            new Paragraph({
                children: [new TextRun({ text: "自我评价", font: "黑体", size: 22, bold: true, color: "020617" })],
                border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "94A3B8", space: 2 } },
                spacing: { before: 90, after: 20, line: 200, lineRule: "auto" }
            }),
            bulletItem("具备完整的 Multi-Agent 系统设计能力：基于 10,500+ 行生产代码实践，精通 LangChain / LangGraph / AutoGen 等主流 Agent 框架，主导实现 Supervisor-Agent 多智能体调度架构"),
            bulletItem("深入理解 RAG 全链路优化：三层 RAG + Self-RAG + Context 双向融合，复杂查询准确率从基线 45% 提升至 82%，具备端到端的检索系统设计经验"),
            bulletItem("扎实的算法与系统基础：基于 ACM-ICPC 竞赛经验（图论/DP/数据结构），擅长问题分析与系统设计；理解 Transformer 自注意力机制、RoPE 位置编码、LoRA 微调原理等大模型核心概念"),
            bulletItem("Prompt 工程实践能力：设计多轮对话 Prompt 模板，通过 Few-shot + Chain-of-Thought 引导格式化输出，将随机性降低 40%"),
            bulletItem("工程意识与代码质量：pickle→JSON 消除安全漏洞、asyncio 并发优化、三级缓存降级、测试覆盖率 95%+；具备 DevOps 全链路能力"),
            bulletItem("求职方向：Agent 应用开发 / RAG 系统架构 / 大模型应用工程化"),
        ]
    }]
});

Packer.toBuffer(doc).then(buffer => {
    fs.writeFileSync("D:/agentlearn/ai-engineer-training/projects/test2langchain/mianshi/简历_大模型应用开发工程师_润色v2.docx", buffer);
    console.log("Resume v2 created successfully!");
});
