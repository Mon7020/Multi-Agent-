from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.audit_log_service import AuditLogService


ALL_KNOWLEDGE_ROLES = ["user", "operator", "admin", "super_admin"]
ALLOWED_DOC_EXTENSIONS = {".txt", ".pdf", ".docx"}


class KnowledgeAdminService:
    def __init__(self) -> None:
        self.reconfigure()

    @staticmethod
    def _project_root() -> Path:
        return Path(__file__).resolve().parents[3]

    def reconfigure(
        self,
        docs_dir: Optional[str] = None,
        metadata_path: Optional[str] = None,
        audit_storage_path: Optional[str] = None,
    ) -> None:
        project_root = self._project_root()
        self.docs_dir = Path(docs_dir) if docs_dir else project_root / "data" / "docs"
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path = Path(metadata_path) if metadata_path else project_root / "data" / "knowledge" / "registry.json"
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        self.audit_log_service = AuditLogService(
            storage_path=audit_storage_path or str(project_root / "logs" / "admin_audit.jsonl")
        )

    @staticmethod
    def _safe_filename(filename: str) -> str:
        safe = Path(filename or "").name
        if not safe or safe != (filename or "").strip():
            raise ValueError("invalid filename")
        if Path(safe).suffix.lower() not in ALLOWED_DOC_EXTENSIONS:
            raise ValueError("unsupported document type")
        return safe

    @staticmethod
    def _normalize_roles(allowed_roles: Optional[List[str]]) -> List[str]:
        if allowed_roles is None:
            return ALL_KNOWLEDGE_ROLES.copy()
        normalized = [role for role in ALL_KNOWLEDGE_ROLES if role in allowed_roles]
        if not normalized:
            return []
        return normalized

    @staticmethod
    def _default_record() -> Dict[str, Any]:
        return {
            "visible_to_frontend": True,
            "published": True,
            "allowed_roles": ALL_KNOWLEDGE_ROLES.copy(),
            "updated_at": datetime.now().isoformat(),
        }

    def _load_registry(self) -> Dict[str, Dict[str, Any]]:
        if not self.metadata_path.exists():
            return {}
        try:
            return json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_registry(self, registry: Dict[str, Dict[str, Any]]) -> None:
        self.metadata_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")

    def _document_path(self, filename: str) -> Path:
        safe = self._safe_filename(filename)
        document_path = (self.docs_dir / safe).resolve()
        if not document_path.exists() or not document_path.is_file():
            raise FileNotFoundError(safe)
        return document_path

    def get_document_access(self, filename: str) -> Dict[str, Any]:
        document_path = self._document_path(filename)
        registry = self._load_registry()
        record = {**self._default_record(), **registry.get(document_path.name, {})}
        record["allowed_roles"] = self._normalize_roles(record.get("allowed_roles"))
        record["updated_at"] = record.get("updated_at") or datetime.now().isoformat()
        return record

    def _serialize_document(self, document_path: Path) -> Dict[str, Any]:
        access = self.get_document_access(document_path.name)
        stat = document_path.stat()
        return {
            "document_id": document_path.name,
            "filename": document_path.name,
            "file_type": document_path.suffix.lower(),
            "size": stat.st_size,
            "upload_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "update_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            **access,
        }

    def list_documents(self) -> List[Dict[str, Any]]:
        documents = []
        for document_path in sorted(self.docs_dir.iterdir(), key=lambda item: item.name.lower()):
            if not document_path.is_file() or document_path.suffix.lower() not in ALLOWED_DOC_EXTENSIONS:
                continue
            documents.append(self._serialize_document(document_path))
        return documents

    @staticmethod
    def can_role_access(record: Dict[str, Any], role: str) -> bool:
        return bool(record.get("visible_to_frontend") and record.get("published") and role in record.get("allowed_roles", []))

    def can_user_access_document(self, filename: str, role: str) -> bool:
        return self.can_role_access(self.get_document_access(filename), role)

    def update_document_access(
        self,
        filename: str,
        visible_to_frontend: Optional[bool] = None,
        published: Optional[bool] = None,
        allowed_roles: Optional[List[str]] = None,
        actor_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        document_path = self._document_path(filename)
        registry = self._load_registry()
        record = {**self._default_record(), **registry.get(document_path.name, {})}

        if visible_to_frontend is not None:
            record["visible_to_frontend"] = bool(visible_to_frontend)
        if published is not None:
            record["published"] = bool(published)
        if allowed_roles is not None:
            record["allowed_roles"] = self._normalize_roles(allowed_roles)

        record["updated_at"] = datetime.now().isoformat()
        registry[document_path.name] = record
        self._save_registry(registry)

        if actor_id:
            self.audit_log_service.write(
                actor_id=actor_id,
                module="knowledge",
                action="update_access",
                target_type="document",
                target_id=document_path.name,
                result="success",
                extra={
                    "visible_to_frontend": record["visible_to_frontend"],
                    "published": record["published"],
                    "allowed_roles": record["allowed_roles"],
                },
            )

        return self._serialize_document(document_path)


knowledge_admin_service = KnowledgeAdminService()
