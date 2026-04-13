from pathlib import Path
import re

p = Path(r"tools/rag/context_rag_fusion.py")
s = p.read_text(encoding="utf-8")

s = s.replace(
    '                    "context_strength": context_strength\n                }',
    '                    "context_strength": context_strength,\n'
    '                    "retrieval_result": {\n'
    '                        "success": rag_result.get("success", bool(documents)),\n'
    '                        "documents": documents,\n'
    '                    },\n'
    '                    "three_tier_context": (\n'
    '                        session_context.get_three_tier_context()\n'
    '                        if hasattr(session_context, "get_three_tier_context")\n'
    '                        else {}\n'
    '                    ),\n'
    '                }'
)

pattern = r'def _extract_short_term\(self, context: SessionContext\) -> str:\n(?:    .*\n)*?def _extract_medium_term\(self, context: SessionContext\) -> str:\n'
repl = '''def _extract_short_term(self, context: SessionContext) -> str:
        """Extract short-term context."""
        if hasattr(context, "get_three_tier_context"):
            tier_context = context.get_three_tier_context()
            short_turns = tier_context.get("short_term_turns", [])
            if short_turns:
                parts = ["【当前对话】"]
                for turn in short_turns[-5:]:
                    role = "用户" if turn.get("role") == "user" else "助手"
                    content = turn.get("content", "")
                    content = content[:100] + "..." if len(content) > 100 else content
                    parts.append(f"{role}: {content}")
                return "\\n".join(parts)

        recent_turns = [
            {"role": t.role, "content": t.content}
            for t in context.turn_history[-8:]
        ]

        if not recent_turns:
            return ""

        parts = ["【当前对话】"]
        for turn in recent_turns[-5:]:
            role = "用户" if turn["role"] == "user" else "助手"
            content = turn["content"][:100] + "..." if len(turn["content"]) > 100 else turn["content"]
            parts.append(f"{role}: {content}")

        return "\\n".join(parts)

    def _extract_medium_term(self, context: SessionContext) -> str:
'''
s2, n = re.subn(pattern, repl, s, flags=re.M)
if n != 1:
    raise RuntimeError(f"short-term replace failed: {n}")
s = s2

pattern = r'def _extract_medium_term\(self, context: SessionContext\) -> str:\n(?:    .*\n)*?def _extract_long_term\(self, context: SessionContext\) -> str:\n'
repl = '''def _extract_medium_term(self, context: SessionContext) -> str:
        """Extract medium-term compressed context."""
        if hasattr(context, "get_three_tier_context"):
            tier_context = context.get_three_tier_context()
            medium_summary = tier_context.get("medium_term_summary", "")
            if medium_summary:
                return f"【历史摘要】\\n{medium_summary}"

        metadata = context.metadata
        discussed_products = metadata.get("discussed_products", [])

        if not discussed_products:
            return ""

        parts = ["【历史讨论】"]
        for product in discussed_products[-5:]:
            parts.append(f"- {product}")

        return "\\n".join(parts)

    def _extract_long_term(self, context: SessionContext) -> str:
'''
s2, n = re.subn(pattern, repl, s, flags=re.M)
if n != 1:
    raise RuntimeError(f"medium-term replace failed: {n}")
s = s2

pattern = r'def _extract_long_term\(self, context: SessionContext\) -> str:\n(?:    .*\n)*?def _format_rag_context\(\n'
repl = '''def _extract_long_term(self, context: SessionContext) -> str:
        """Extract long-term user profile context."""
        if hasattr(context, "get_three_tier_context"):
            tier_context = context.get_three_tier_context()
            long_term_text = tier_context.get("long_term_text", "")
            if long_term_text:
                return f"【用户背景】\\n{long_term_text}"

        metadata = context.metadata

        parts = ["【用户背景】"]

        if metadata.get("customer_type"):
            parts.append(f"客户类型: {metadata['customer_type']}")

        if metadata.get("total_spent", 0) > 0:
            parts.append(f"累计消费: ￥{metadata['total_spent']:.2f}")

        return "\\n".join(parts) if len(parts) > 1 else ""

    def _format_rag_context(
'''
s2, n = re.subn(pattern, repl, s, flags=re.M)
if n != 1:
    raise RuntimeError(f"long-term replace failed: {n}")
s = s2

pattern = r'def _calculate_context_strength\(self, context: SessionContext\) -> float:\n(?:    .*\n)*?return min\(score, 1\.0\)\n'
repl = '''def _calculate_context_strength(self, context: SessionContext) -> float:
        """Calculate context strength with three-tier signals when available."""
        score = 0.0

        if hasattr(context, "get_three_tier_context"):
            tier_context = context.get_three_tier_context()
            stats = tier_context.get("stats", {})
            if stats.get("short_term_turns", 0) > 3:
                score += 0.3
            if stats.get("compressed_memories", 0) > 0:
                score += 0.2
            if tier_context.get("long_term_text"):
                score += 0.2
            if tier_context.get("intent_continuity"):
                score += 0.1

        if len(context.turn_history) > 3:
            score += 0.3

        if context.metadata.get("customer_type"):
            score += 0.2

        if context.metadata.get("current_product"):
            score += 0.2

        if context.skill_context:
            score += 0.2

        if len(context.turn_history) > 10:
            score += 0.1

        return min(score, 1.0)
'''
s2, n = re.subn(pattern, repl, s, flags=re.M)
if n != 1:
    raise RuntimeError(f"strength replace failed: {n}")
s = s2

p.write_text(s, encoding="utf-8")
