const { Document, Packer, Paragraph, TextRun, LevelFormat, AlignmentType, BorderStyle } = require('docx');
const fs = require('fs');

function t(text, size = 21, bold = false, color = "000000", font = "Arial") {
    return new TextRun({ text, size, bold, color, font });
}
function p(children, spacing) {
    return new Paragraph({ children, spacing: spacing || { after: 4, line: 180, lineRule: "auto" } });
}
function divider() {
    return new Paragraph({
        children: [],
        border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "94A3B8", space: 2 } },
        spacing: { before: 60, after: 12, line: 180, lineRule: "auto" }
    });
}
function sectionTitle(text) {
    return new Paragraph({
        children: [new TextRun({ text, font: "黑体", size: 20, bold: true, color: "020617" })],
        border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "94A3B8", space: 2 } },
        spacing: { before: 60, after: 10, line: 180, lineRule: "auto" }
    });
}
function projectTitle(text) {
    return new Paragraph({
        children: [new TextRun({ text, size: 21, bold: true })],
        spacing: { before: 8, after: 2, line: 180, lineRule: "auto" }
    });
}
function metaLine(runs) {
    return new Paragraph({
        children: runs.map(r => {
            if (typeof r === 'string') return t(r, 18, false, "64748B");
            return t(r.text, r.size || 18, r.bold || false, r.color || "64748B");
        }),
        spacing: { after: 2, line: 180, lineRule: "auto" }
    });
}
function bi(text, size = 20) {
    return new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun({ text, size })],
        spacing: { after: 2, line: 180, lineRule: "auto" }
    });
}
function bi2(text, size = 19) {
    return new Paragraph({
        numbering: { reference: "bullets2", level: 0 },
        children: [new TextRun({ text, size })],
        spacing: { after: 2, line: 180, lineRule: "auto" }
    });
}

const doc = new Document({
    numbering: {
        config: [
            { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 240, hanging: 180 } } } }] },
            { reference: "bullets2", levels: [{ level: 0, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 420, hanging: 200 } } } }] },
        ]
    },
    sections: [{
        properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 400, right: 650, bottom: 400, left: 650 } } },
        children: [
            // === 姓名 & 基础信息 ===
            p([t("[您的姓名]", 28, true, "020617", "黑体")]),
            p([
                t("大模型应用开发工程师 · 实习  |  ", 20, true, "94A3B8", "黑体"),
                t("[学历] · [专业] · [毕业年份]  |  [电话]  |  [邮箱]  |  GitHub: [待补充]", 19, false, "64748B")
            ]),
            divider(),

            // === 教育背景 ===
            sectionTitle("教育背景"),
            p([t("[您的学校] · [专业] · [入学年份]-[毕业年份]  |  ACM-ICPC 铜牌（图论/DP/数据结构）", 20)]),

            // === 技术栈 ===
            sectionTitle("技术栈"),
            p([t("AI框架：LangChain 0.3 / AutoGen / LlamaIndex / LangGraph  |  LLM部署：vLLM / DeepSeek API / 理解 LoRA/GPTQ 原理", 19)]),
            p([t("后端：Python / FastAPI / Pydantic / asyncio  |  向量库：ChromaDB / Milvus  |  检索：BM25 / BGE-Reranker / 混合检索RRF融合", 19)]),
            p([t("Prompt工程：Few-shot / Chain-of-Thought / 结构化输出  |  DevOps：Docker / CI/CD  |  基础：Transformer / 注意力机制原理", 19)]),

            // === 项目经历 ===
            sectionTitle("项目经历"),

            // --- 项目1 ---
            projectTitle("MultiTaskQAAssistant — 智能客服系统"),
            metaLine([
                { text: "2026.03-2026.04", bold: true, size: 18 }, t("  |  独立负责（核心开发者）  |  Python · FastAPI · LangChain · DeepSeek · ChromaDB · Redis · Vue3", 18, false, "64748B")
            ]),
            bi("基于 LangChain + DeepSeek 构建，实现多轮对话、RAG 检索增强、Multi-Agent 技能协作"),
            bi("Supervisor-Agent 多智能体调度：LLM 意图识别 → 任务路由 → Skill 并行执行；asyncio.gather 效率提升 3.2x；可插拔框架新增业务仅需 ~200 行"),
            bi("三层 RAG + Self-RAG：查询理解 → BM25+向量混合检索+RRF+Rerank → 上下文拼接；LLM 自适应判断检索时机的 Self-RAG 策略，延迟降低 60%"),
            bi("Context+RAG 双向融合 + Few-shot Prompt：客户偏好注入检索查询，复杂查询准确率基线 45%→82%，输出随机性降低 40%"),
            bi("▌难点：长文档截断（父块-子块分块+重排解决）；多轮意图漂移（Session记忆窗口+历史摘要注入）；量化：500条测试集评估，准确率 85%+，P99<500ms，代码 10,500+ 行"),

            // --- 项目2 ---
            projectTitle("智能会议助手系统"),
            metaLine([
                { text: "2025.02-2025.04", bold: true, size: 18 }, t("  |  后端开发（团队3人）  |  省级三等奖  |  Python · FastAPI · LangChain · ChromaDB · WebSocket · Docker", 18, false, "64748B")
            ]),
            bi("AI 会议纪要生成（RAG+分层摘要策略）+ 智能发言稿生成（Few-shot结构化输出）+ 视频通话 WebSocket 信令"),
            bi("▌难点：长会议（>1h）截断问题 → 分层摘要（段落分割→逐段提取→融合生成），完整率 51%→84%"),
            bi("服务端架构：FastAPI + Redis 会话管理 + Docker Compose 部署 + GitHub Actions CI/CD；P99<800ms"),

            // === 自我评价 ===
            sectionTitle("自我评价"),
            bi("10,500+ 行生产代码实践，精通 LangChain / LangGraph / AutoGen，主导 Multi-Agent 调度架构设计"),
            bi("三层 RAG + Self-RAG + Context双向融合实战经验；基线 45%→82% 复杂查询准确率提升"),
            bi("ACM 竞赛算法基础；理解 Transformer 自注意力机制、RoPE、LoRA 微调原理"),
            bi("求职方向：Agent 应用开发 / RAG 系统架构 / 大模型应用工程化"),
        ]
    }]
});

Packer.toBuffer(doc).then(buffer => {
    fs.writeFileSync("D:/agentlearn/ai-engineer-training/projects/test2langchain/mianshi/简历_大模型应用开发工程师_最终版.docx", buffer);
    console.log("Resume v3 (one-page) created successfully!");
});
