const { Document, Packer, Paragraph, TextRun, LevelFormat, AlignmentType, BorderStyle } = require('docx');
const fs = require('fs');

function title(text, size = 28) {
    return new Paragraph({
        children: [new TextRun({ text, font: "黑体", size, bold: true, color: "020617" })],
        spacing: { after: 8, line: 200, lineRule: "auto" }
    });
}

function para(text, size = 21, bold = false, color = "000000") {
    return new Paragraph({
        children: [new TextRun({ text, size, bold, color })],
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

function mixedPara(runs, spacing = { after: 6 }) {
    return new Paragraph({
        children: runs.map(r => new TextRun(typeof r === 'string' ? { text: r, size: 21 } : r)),
        spacing
    });
}

function bulletItem(parts, size = 21) {
    return new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: parts.map(p => new TextRun(typeof p === 'string' ? { text: p, size } : p)),
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
            // 姓名
            title("[您的姓名]", 28),
            // 职位行
            new Paragraph({
                children: [
                    new TextRun({ text: "大模型应用开发工程师 · 实习  |  ", font: "黑体", size: 21, bold: true, color: "94A3B8" }),
                    new TextRun({ text: "[您的学历] · [专业] · [毕业年份]  |  [您的电话]  |  [您的邮箱]  |  GitHub: [如有]", size: 20, color: "64748B" })
                ],
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
            bulletItem(["AI框架：LangChain 0.3 / AutoGen / LlamaIndex / LangGraph"], 20),
            bulletItem(["LLM部署：vLLM / Ollama / DeepSeek API / OpenAI API"], 20),
            bulletItem(["低代码平台：Coze / Dify / FastGPT"], 20),
            bulletItem(["后端开发：Python 3.10 / FastAPI / Uvicorn / Pydantic"], 20),
            bulletItem(["向量数据库：ChromaDB / Milvus"], 20),
            bulletItem(["检索技术：text2vec-base-chinese / BGE-Reranker / BM25 / 混合检索（RRF融合）"], 20),
            bulletItem(["缓存：Redis / LocalCache 三级降级"], 20),
            bulletItem(["前端：Vue 3 / Vite / WebSocket / SSE"], 20),
            bulletItem(["DevOps：Docker / CI/CD (GitHub Actions) / Linux 服务器部署"], 20),
            bulletItem(["竞赛：ACM-ICPC 国际大学生程序设计竞赛 · 铜牌（图论、动态规划、数据结构）"], 20),

            // ========== 项目经历 ==========
            new Paragraph({
                children: [new TextRun({ text: "项目经历", font: "黑体", size: 22, bold: true, color: "020617" })],
                border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "94A3B8", space: 2 } },
                spacing: { before: 90, after: 20, line: 200, lineRule: "auto" }
            }),

            // ---- 项目一 ----
            subTitle("项目一：MultiTaskQAAssistant — 智能客服系统"),
            mixedPara([{ text: "时间：", bold: true, size: 18 }, { text: "2026.03.10 — 2026.04.01", size: 18 }], { after: 3 }),
            mixedPara([{ text: "技术栈：", bold: true, size: 18 }, { text: "Python 3.10 · FastAPI · LangChain 0.3 · DeepSeek API · ChromaDB · Redis · Vue 3", size: 18 }], { after: 3 }),
            para("基于 LangChain + DeepSeek 构建的智能客服系统，实现多轮对话、RAG 检索增强、多技能协作，系统性能达行业领先水平。", 21),

            subTitle("Supervisor-Agent 多智能体调度"),
            bulletItem(["实现意图识别（LLM + 规则兜底）→ 任务路由 → Skill 并行执行的完整调度链路"]),
            bulletItem(["设计可插拔 Skill 框架，新增业务场景仅需 ~200 行代码；使用 asyncio.gather 并行执行，效率提升 3.2x"]),

            subTitle("三层 RAG + Self-RAG 自适应检索"),
            bulletItem(["Layer 1 查询理解：意图分类 + 实体提取 + 复杂度评估"]),
            bulletItem(["Layer 2 混合检索：BM25 + 向量检索 + RRF 融合 + Rerank 重排"]),
            bulletItem(["Layer 3 生成上下文：多源拼接 + 来源标注"]),
            bulletItem(["Self-RAG 自适应检索：LLM 判断是否需要检索，延迟降低 60%"]),

            subTitle("Context + RAG 双向融合"),
            bulletItem(["上下文→RAG：客户类型/偏好注入检索查询，提升个性化检索质量"]),
            bulletItem(["RAG→上下文：高质量检索结果注入记忆系统，复杂查询准确率从 45% 提升至 82%"]),

            subTitle("安全与稳定性"),
            bulletItem(["pickle→JSON 消除反序列化漏洞；threading.Lock 保证并发安全；Redis/LocalCache 三级缓存降级"]),

            subTitle("量化成果"),
            bulletItem(["意图识别准确率 85%+（LLM + 规则双层识别）"]),
            bulletItem(["检索相关度提升 30%（Hybrid Search + Rerank）"]),
            bulletItem(["API 响应 P99 < 500ms（三级缓存优化）"]),
            bulletItem(["测试用例通过率 95%+ | 代码量 10,500+ 行"]),

            // ---- 项目二 ----
            subTitle("项目二：智能会议助手系统"),
            mixedPara([{ text: "时间：", bold: true, size: 18 }, { text: "2025.02.10 — 2025.04.10", size: 18 }, { text: "  |  角色：", bold: true, size: 18 }, { text: "后端开发工程师 · 服务器部署", size: 18 }, { text: "  |  获奖：", bold: true, size: 18 }, { text: "软件服务外包创新创业大赛 · 省级三等奖", size: 18 }], { after: 3 }),
            mixedPara([{ text: "技术栈：", bold: true, size: 18 }, { text: "Python · FastAPI · LangChain · ChromaDB · WebSocket · SSE · Docker", size: 18 }], { after: 3 }),
            para("面向会议的智能助手系统，提供视频通话、AI 会议纪要总结、智能发言稿生成等功能，有效提升会议效率和内容沉淀。"),

            subTitle("核心功能开发"),
            bulletItem(["AI 会议纪要生成：基于 LangChain 实现会议内容的多模态理解与结构化提取；使用 RAG 从历史会议检索相关背景；支持 SSE 流式输出"]),
            bulletItem(["智能发言稿生成：结合 RAG 检索的历史资料，自动生成个性化发言稿；上下文感知的内容推荐优化检索质量"]),
            bulletItem(["视频通话与实时协作：基于 WebSocket 实现实时音视频信令传输；分布式部署架构，支持多实例横向扩展"]),

            subTitle("系统架构与部署"),
            bulletItem(["负责服务端架构设计与核心业务逻辑开发"]),
            bulletItem(["配置 Linux 服务器环境，搭建 CI/CD 部署流水线，实现 RESTful API 接口服务"]),
            bulletItem(["使用 Docker 容器化部署，结合 Redis 实现会话状态管理和消息队列异步处理"]),

            subTitle("量化成果"),
            bulletItem(["服务端 API 响应 P99 < 800ms（异步 + 缓存优化）"]),
            bulletItem(["RAG 检索相关度提升 25%（混合检索 + Rerank）"]),
            bulletItem(["项目获省级三等奖（软件服务外包创新创业大赛）"]),

            // ========== 自我评价 ==========
            new Paragraph({
                children: [new TextRun({ text: "自我评价", font: "黑体", size: 22, bold: true, color: "020617" })],
                border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "94A3B8", space: 2 } },
                spacing: { before: 90, after: 20, line: 200, lineRule: "auto" }
            }),
            bulletItem(["具备完整的 Multi-Agent 系统设计能力，精通 LangChain / LangGraph / AutoGen 等主流 Agent 开发框架，主导实现 Supervisor-Agent 多智能体调度架构"]),
            bulletItem(["深入理解 RAG、Self-RAG、Hybrid Search 等前沿检索技术，具备三层 RAG 系统设计经验，复杂查询准确率提升 37%"]),
            bulletItem(["扎实的算法基础（ACM-ICPC 铜牌），擅长问题分析与系统设计，对大模型能力边界和应用场景有深入思考"]),
            bulletItem(["注重代码质量与系统安全，具备 DevOps 全链路能力，工程意识强"]),
            bulletItem(["求职方向：Agent 应用开发 / RAG 系统架构 / 大模型应用工程化"]),
        ]
    }]
});

Packer.toBuffer(doc).then(buffer => {
    fs.writeFileSync("D:/agentlearn/ai-engineer-training/projects/test2langchain/mianshi/简历_大模型应用开发工程师_润色.docx", buffer);
    console.log("Resume created successfully!");
});
