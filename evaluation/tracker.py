"""
评测轨迹记录器
记录完整的对话轨迹和评测结果
"""

import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

from core.logger import LoggerManager
from evaluation.metrics import EvaluationReport

logger = LoggerManager.get_logger("tracker")


class EvaluationTracker:
    """
    评测轨迹记录器

    功能：
    1. 记录每轮对话的完整轨迹
    2. 存储评测报告
    3. 生成会话统计
    4. 导出分析报告
    """

    def __init__(self, storage_path: str = None):
        if storage_path is None:
            project_root = os.path.dirname(os.path.dirname(__file__))
            storage_path = os.path.join(project_root, "evaluation_data")

        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # 内存中的记录
        self._session_records: Dict[str, List[Dict]] = {}
        self._evaluation_reports: Dict[str, EvaluationReport] = {}

        logger.info(f"[EvaluationTracker] 初始化完成，存储路径: {storage_path}")

    def record_turn(
        self,
        session_id: str,
        turn_data: Dict[str, Any]
    ) -> None:
        """
        记录单轮对话

        Args:
            session_id: 会话 ID
            turn_data: 包含 role, content, agent_name, intent, rag_results, evaluation_score 等
        """
        if session_id not in self._session_records:
            self._session_records[session_id] = []

        turn_record = {
            "turn_index": len(self._session_records[session_id]),
            "timestamp": datetime.now().isoformat(),
            **turn_data
        }

        self._session_records[session_id].append(turn_record)

        logger.debug(f"[EvaluationTracker] 记录对话轮次: session={session_id}, turn={turn_record['turn_index']}")

    def record_evaluation(self, report: EvaluationReport) -> None:
        """
        记录评测报告

        Args:
            report: EvaluationReport 实例
        """
        self._evaluation_reports[report.session_id] = report

        # 持久化到文件
        self._persist_report(report)

        logger.info(
            f"[EvaluationTracker] 记录评测报告: session={report.session_id}, "
            f"总分={report.overall_score:.3f}"
        )

    def _persist_report(self, report: EvaluationReport) -> None:
        """持久化报告到文件"""
        try:
            file_path = self.storage_path / f"{report.session_id}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[EvaluationTracker] 持久化报告失败: {e}")

    def get_session_record(self, session_id: str) -> Optional[List[Dict]]:
        """获取会话记录"""
        return self._session_records.get(session_id)

    def get_evaluation_report(self, session_id: str) -> Optional[EvaluationReport]:
        """获取评测报告"""
        # 先从内存中查找
        if session_id in self._evaluation_reports:
            return self._evaluation_reports[session_id]

        # 从文件加载
        file_path = self.storage_path / f"{session_id}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return EvaluationReport.from_dict(data)
            except Exception as e:
                logger.error(f"[EvaluationTracker] 加载报告失败: {e}")

        return None

    def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话统计信息

        Args:
            session_id: 会话 ID

        Returns:
            统计信息字典
        """
        record = self.get_session_record(session_id)
        if not record:
            return {}

        total_turns = len(record)
        user_turns = sum(1 for t in record if t.get("role") == "user")
        assistant_turns = total_turns - user_turns

        # Skill 使用统计
        skill_usage = {}
        for turn in record:
            agent = turn.get("agent_name")
            if agent and agent != "supervisor":
                skill_usage[agent] = skill_usage.get(agent, 0) + 1

        # 评估分数统计
        eval_scores = [t.get("evaluation_score", 0) for t in record if t.get("evaluation_score")]
        avg_score = sum(eval_scores) / len(eval_scores) if eval_scores else 0.0

        # 意图分布
        intent_distribution = {}
        for turn in record:
            intent = turn.get("intent")
            if intent:
                intent_distribution[intent] = intent_distribution.get(intent, 0) + 1

        return {
            "session_id": session_id,
            "total_turns": total_turns,
            "user_turns": user_turns,
            "assistant_turns": assistant_turns,
            "skill_usage": skill_usage,
            "avg_evaluation_score": round(avg_score, 3),
            "intent_distribution": intent_distribution,
            "first_turn_time": record[0].get("timestamp") if record else None,
            "last_turn_time": record[-1].get("timestamp") if record else None
        }

    def get_all_sessions_summary(self) -> List[Dict[str, Any]]:
        """获取所有会话摘要"""
        summaries = []
        for session_id in self._session_records.keys():
            summary = self.get_session_statistics(session_id)
            if summary:
                summaries.append(summary)
        return summaries

    def get_global_statistics(self) -> Dict[str, Any]:
        """
        获取全局统计信息

        跨会话聚合统计
        """
        all_sessions = list(self._session_records.keys())

        if not all_sessions:
            return {
                "total_sessions": 0,
                "total_turns": 0,
                "avg_turns_per_session": 0,
                "avg_evaluation_score": 0.0
            }

        total_turns = sum(len(record) for record in self._session_records.values())
        all_scores = []
        all_skills = {}
        all_intents = {}

        for session_id, record in self._session_records.items():
            # 收集评估分数
            scores = [t.get("evaluation_score", 0) for t in record if t.get("evaluation_score")]
            all_scores.extend(scores)

            # 收集 Skill 使用
            for turn in record:
                agent = turn.get("agent_name")
                if agent and agent != "supervisor":
                    all_skills[agent] = all_skills.get(agent, 0) + 1

                # 收集意图
                intent = turn.get("intent")
                if intent:
                    all_intents[intent] = all_intents.get(intent, 0) + 1

        return {
            "total_sessions": len(all_sessions),
            "total_turns": total_turns,
            "avg_turns_per_session": round(total_turns / len(all_sessions), 2),
            "avg_evaluation_score": round(sum(all_scores) / len(all_scores), 3) if all_scores else 0.0,
            "total_evaluations": len(all_scores),
            "skill_usage": all_skills,
            "intent_distribution": all_intents,
            "top_skills": sorted(all_skills.items(), key=lambda x: x[1], reverse=True)[:5],
            "top_intents": sorted(all_intents.items(), key=lambda x: x[1], reverse=True)[:5]
        }

    def clear_session(self, session_id: str) -> bool:
        """清空会话记录"""
        if session_id in self._session_records:
            del self._session_records[session_id]
            logger.info(f"[EvaluationTracker] 清空会话记录: {session_id}")
            return True
        return False

    def export_session_report(self, session_id: str, output_path: str = None) -> str:
        """
        导出会话报告为 Markdown

        Args:
            session_id: 会话 ID
            output_path: 输出文件路径

        Returns:
            报告内容
        """
        record = self.get_session_record(session_id)
        report = self.get_evaluation_report(session_id)

        if not record:
            return f"会话 {session_id} 不存在"

        stats = self.get_session_statistics(session_id)

        lines = [
            f"# 会话评测报告",
            f"",
            f"**会话 ID**: {session_id}",
            f"**统计时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"## 基本统计",
            f"",
            f"- 总轮次: {stats.get('total_turns', 0)}",
            f"- 用户轮次: {stats.get('user_turns', 0)}",
            f"- 助手轮次: {stats.get('assistant_turns', 0)}",
            f"- 平均评分: {stats.get('avg_evaluation_score', 0.0):.3f}",
            f"",
            f"## Skill 使用统计",
            f"",
        ]

        for skill, count in stats.get("skill_usage", {}).items():
            lines.append(f"- {skill}: {count} 次")

        lines.extend([
            f"",
            f"## 意图分布",
            f"",
        ])

        for intent, count in stats.get("intent_distribution", {}).items():
            lines.append(f"- {intent}: {count} 次")

        if report:
            lines.extend([
                f"",
                f"## 评测结果",
                f"",
                f"- 总体评分: {report.overall_score:.3f} ({report.grade})",
                f"",
                f"### 指标得分",
                f"",
            ])

            for metric_name, metric_result in report.metrics.items():
                status = "✓" if metric_result.is_passed() else "✗"
                lines.append(
                    f"- {status} {metric_name}: {metric_result.value:.3f} "
                    f"(阈值: {metric_result.threshold})"
                )

        lines.extend([
            f"",
            f"## 对话详情",
            f"",
        ])

        for turn in record:
            role = turn.get("role", "unknown")
            content = turn.get("content", "")[:200]
            agent = turn.get("agent_name", "")
            timestamp = turn.get("timestamp", "")

            lines.append(f"### [{role.upper()}] {timestamp}")

            if agent:
                lines.append(f"**Agent**: {agent}")

            lines.append(f"\n{content}\n")

        content = "\n".join(lines)

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

        return content


# 全局单例
evaluation_tracker = EvaluationTracker()
