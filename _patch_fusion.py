from pathlib import Path

path = Path(r"tools/rag/context_rag_fusion.py")
text = path.read_text(encoding="utf-8")

def replace_between(src: str, start: str, end: str, new_block: str) -> str:
    i = src.find(start)
    if i < 0:
        raise RuntimeError(f"start marker not found: {start}")
    j = src.find(end, i)
    if j < 0:
        raise RuntimeError(f"end marker not found: {end}")
    return src[:i] + new_block + src[j:]

short_block = '''    def _extract_short_term(self, context: SessionContext) -> str:\n        """Extract short-term context."""\n        if hasattr(context, "get_three_tier_context"):\n            tier_context = context.get_three_tier_context()\n            short_turns = tier_context.get("short_term_turns", [])\n            if short_turns:\n                parts = ["【当前对话】"]\n                for turn in short_turns[-5:]:\n                    role = "用户" if turn.get("role") == "user" else "助手"\n                    content = turn.get("content", "")\n                    content = content[:100] + "..." if len(content) > 100 else content\n                    parts.append(f"{role}: {content}")\n                return "\\n".join(parts)\n\n        recent_turns = [\n            {"role": t.role, "content": t.content}\n            for t in context.turn_history[-8:]\n        ]\n\n        if not recent_turns:\n            return ""\n\n        parts = ["【当前对话】"]\n        for turn in recent_turns[-5:]:\n            role = "用户" if turn["role"] == "user" else "助手"\n            content = turn["content"][:100] + "..." if len(turn["content"]) > 100 else turn["content"]\n            parts.append(f"{role}: {content}")\n\n        return "\\n".join(parts)\n\n'''

medium_block = '''    def _extract_medium_term(self, context: SessionContext) -> str:\n        """Extract medium-term compressed context."""\n        if hasattr(context, "get_three_tier_context"):\n            tier_context = context.get_three_tier_context()\n            medium_summary = tier_context.get("medium_term_summary", "")\n            if medium_summary:\n                return f"【历史摘要】\\n{medium_summary}"\n\n        metadata = context.metadata\n        discussed_products = metadata.get("discussed_products", [])\n\n        if not discussed_products:\n            return ""\n\n        parts = ["【历史讨论】"]\n        for product in discussed_products[-5:]:\n            parts.append(f"- {product}")\n\n        return "\\n".join(parts)\n\n'''

long_block = '''    def _extract_long_term(self, context: SessionContext) -> str:\n        """Extract long-term user profile context."""\n        if hasattr(context, "get_three_tier_context"):\n            tier_context = context.get_three_tier_context()\n            long_term_text = tier_context.get("long_term_text", "")\n            if long_term_text:\n                return f"【用户背景】\\n{long_term_text}"\n\n        metadata = context.metadata\n\n        parts = ["【用户背景】"]\n\n        if metadata.get("customer_type"):\n            parts.append(f"客户类型: {metadata['customer_type']}")\n\n        if metadata.get("total_spent", 0) > 0:\n            parts.append(f"累计消费: ￥{metadata['total_spent']:.2f}")\n\n        return "\\n".join(parts) if len(parts) > 1 else ""\n\n'''

strength_block = '''    def _calculate_context_strength(self, context: SessionContext) -> float:\n        """Calculate context strength with three-tier signals when available."""\n        score = 0.0\n\n        if hasattr(context, "get_three_tier_context"):\n            tier_context = context.get_three_tier_context()\n            stats = tier_context.get("stats", {})\n            if stats.get("short_term_turns", 0) > 3:\n                score += 0.3\n            if stats.get("compressed_memories", 0) > 0:\n                score += 0.2\n            if tier_context.get("long_term_text"):\n                score += 0.2\n            if tier_context.get("intent_continuity"):\n                score += 0.1\n\n        if len(context.turn_history) > 3:\n            score += 0.3\n\n        if context.metadata.get("customer_type"):\n            score += 0.2\n\n        if context.metadata.get("current_product"):\n            score += 0.2\n\n        if context.skill_context:\n            score += 0.2\n\n        if len(context.turn_history) > 10:\n            score += 0.1\n\n        return min(score, 1.0)\n\n'''

text = replace_between(
    text,
    "    def _extract_short_term(self, context: SessionContext) -> str:\n",
    "    def _extract_medium_term(self, context: SessionContext) -> str:\n",
    short_block,
)
text = replace_between(
    text,
    "    def _extract_medium_term(self, context: SessionContext) -> str:\n",
    "    def _extract_long_term(self, context: SessionContext) -> str:\n",
    medium_block,
)
text = replace_between(
    text,
    "    def _extract_long_term(self, context: SessionContext) -> str:\n",
    "    def _format_rag_context(\n",
    long_block,
)
text = replace_between(
    text,
    "    def _calculate_context_strength(self, context: SessionContext) -> float:\n",
    "    def _generate_context_summary(\n",
    strength_block,
)

path.write_text(text, encoding="utf-8")
print("patched")
