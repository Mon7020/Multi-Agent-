from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.services.audit_log_service import AuditLogService


ALL_KNOWLEDGE_ROLES = ["user", "operator", "admin", "super_admin"]
ALLOWED_DOC_EXTENSIONS = {".txt", ".pdf", ".docx"}
REGISTRY_VERSION = 2


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
    def _now_iso() -> str:
        return datetime.now().isoformat()

    @staticmethod
    def _new_document_id() -> str:
        return f"doc_{uuid4().hex}"

    @staticmethod
    def _default_registry() -> Dict[str, Any]:
        return {"version": REGISTRY_VERSION, "documents": {}}

    @staticmethod
    def _default_record() -> Dict[str, Any]:
        return {
            "description": "",
            "tags": [],
            "visible_to_frontend": True,
            "published": True,
            "allowed_roles": ALL_KNOWLEDGE_ROLES.copy(),
            "deleted": False,
            "created_at": None,
            "created_by": None,
            "updated_at": None,
            "updated_by": None,
            "deleted_at": None,
            "deleted_by": None,
            "chunk_count": 0,
        }

    def _compute_checksum(self, file_path: Path) -> str:
        digest = hashlib.sha256()
        digest.update(file_path.read_bytes())
        return digest.hexdigest()

    def _build_record(
        self,
        *,
        document_id: str,
        file_path: Path,
        filename: str,
        legacy: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        legacy = legacy or {}
        stat = file_path.stat()
        created_at = legacy.get("created_at") or datetime.fromtimestamp(stat.st_ctime).isoformat()
        updated_at = legacy.get("updated_at") or datetime.fromtimestamp(stat.st_mtime).isoformat()
        return {
            "document_id": document_id,
            "filename": filename,
            "file_type": file_path.suffix.lower(),
            "storage_name": file_path.name,
            "storage_path": str(file_path.resolve()),
            "size": stat.st_size,
            "checksum": self._compute_checksum(file_path),
            "chunk_count": int(legacy.get("chunk_count", 0) or 0),
            "description": legacy.get("description", ""),
            "tags": list(legacy.get("tags", [])),
            "published": bool(legacy.get("published", True)),
            "visible_to_frontend": bool(legacy.get("visible_to_frontend", True)),
            "allowed_roles": self._normalize_roles(legacy.get("allowed_roles")),
            "deleted": bool(legacy.get("deleted", False)),
            "created_at": created_at,
            "created_by": legacy.get("created_by"),
            "updated_at": updated_at,
            "updated_by": legacy.get("updated_by"),
            "deleted_at": legacy.get("deleted_at"),
            "deleted_by": legacy.get("deleted_by"),
        }

    def _load_raw_registry(self) -> Dict[str, Any]:
        if not self.metadata_path.exists():
            return {}
        try:
            return json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_registry(self, registry: Dict[str, Any]) -> None:
        self.metadata_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")

    def _normalize_registry(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        if raw.get("version") == REGISTRY_VERSION and isinstance(raw.get("documents"), dict):
            return raw
        return self._migrate_legacy_registry(raw)

    def _migrate_legacy_registry(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        registry = self._default_registry()
        for document_path in sorted(self.docs_dir.iterdir(), key=lambda item: item.name.lower()):
            if not document_path.is_file() or document_path.suffix.lower() not in ALLOWED_DOC_EXTENSIONS:
                continue
            legacy = raw.get(document_path.name, {}) if isinstance(raw, dict) else {}
            document_id = legacy.get("document_id") or self._new_document_id()
            registry["documents"][document_id] = self._build_record(
                document_id=document_id,
                file_path=document_path,
                filename=document_path.name,
                legacy=legacy,
            )
        self._save_registry(registry)
        return registry

    def _sync_registry_with_files(self, registry: Dict[str, Any]) -> Dict[str, Any]:
        changed = False
        documents = registry.setdefault("documents", {})
        by_storage_name = {
            Path(record.get("storage_name") or record.get("filename") or "").name: document_id
            for document_id, record in documents.items()
            if not record.get("deleted")
        }

        for document_path in sorted(self.docs_dir.iterdir(), key=lambda item: item.name.lower()):
            if not document_path.is_file() or document_path.suffix.lower() not in ALLOWED_DOC_EXTENSIONS:
                continue

            document_id = by_storage_name.get(document_path.name)
            if document_id:
                record = documents[document_id]
                refreshed = self._build_record(
                    document_id=document_id,
                    file_path=document_path,
                    filename=record.get("filename") or document_path.name,
                    legacy=record,
                )
                if refreshed != record:
                    documents[document_id] = refreshed
                    changed = True
                continue

            new_document_id = self._new_document_id()
            documents[new_document_id] = self._build_record(
                document_id=new_document_id,
                file_path=document_path,
                filename=document_path.name,
            )
            changed = True

        if changed:
            self._save_registry(registry)
        return registry

    def _load_registry(self) -> Dict[str, Any]:
        raw = self._load_raw_registry()
        registry = self._normalize_registry(raw)
        return self._sync_registry_with_files(registry)

    def _document_path(self, filename: str) -> Path:
        safe = self._safe_filename(filename)
        document_path = (self.docs_dir / safe).resolve()
        if not document_path.exists() or not document_path.is_file():
            raise FileNotFoundError(safe)
        return document_path

    def _find_document_id_by_filename(self, filename: str, registry: Dict[str, Any]) -> Optional[str]:
        safe = self._safe_filename(filename)
        for document_id, record in registry.get("documents", {}).items():
            if record.get("filename") == safe or record.get("storage_name") == safe:
                return document_id
        return None

    def _record_from_filename(self, filename: str, registry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        safe = self._safe_filename(filename)
        registry = registry or self._load_registry()
        document_id = self._find_document_id_by_filename(safe, registry)
        if document_id is None:
            document_path = self._document_path(safe)
            document_id = self._new_document_id()
            registry["documents"][document_id] = self._build_record(
                document_id=document_id,
                file_path=document_path,
                filename=safe,
            )
            self._save_registry(registry)
        return registry["documents"][document_id]

    def get_document_access(self, filename: str) -> Dict[str, Any]:
        registry = self._load_registry()
        record = self._record_from_filename(filename, registry=registry)
        return {**self._default_record(), **record}

    def _serialize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            **record,
            "upload_time": record.get("created_at"),
            "update_time": record.get("updated_at"),
        }

    def list_documents(
        self,
        *,
        keyword: Optional[str] = None,
        status: str = "active",
        published: Optional[bool] = None,
        visible_to_frontend: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        registry = self._load_registry()
        documents = list(registry.get("documents", {}).values())

        if status == "active":
            documents = [document for document in documents if not document.get("deleted")]
        elif status == "deleted":
            documents = [document for document in documents if document.get("deleted")]

        if published is not None:
            documents = [document for document in documents if document.get("published") is published]

        if visible_to_frontend is not None:
            documents = [
                document for document in documents if document.get("visible_to_frontend") is visible_to_frontend
            ]

        if keyword:
            needle = keyword.strip().lower()
            documents = [
                document
                for document in documents
                if needle in str(document.get("filename", "")).lower()
                or needle in str(document.get("description", "")).lower()
                or any(needle in str(tag).lower() for tag in document.get("tags", []))
            ]

        documents.sort(key=lambda item: str(item.get("filename", "")).lower())
        return [self._serialize_record(document) for document in documents]

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
        record = self._record_from_filename(document_path.name, registry=registry)

        if visible_to_frontend is not None:
            record["visible_to_frontend"] = bool(visible_to_frontend)
        if published is not None:
            record["published"] = bool(published)
        if allowed_roles is not None:
            record["allowed_roles"] = self._normalize_roles(allowed_roles)

        record["updated_at"] = self._now_iso()
        document_id = record["document_id"]
        registry["documents"][document_id] = record
        self._save_registry(registry)

        if actor_id:
            self.audit_log_service.write(
                actor_id=actor_id,
                module="knowledge",
                action="update_access",
                target_type="document",
                target_id=document_id,
                result="success",
                extra={
                    "filename": record["filename"],
                    "visible_to_frontend": record["visible_to_frontend"],
                    "published": record["published"],
                    "allowed_roles": record["allowed_roles"],
                },
            )

        return self._serialize_record(record)


knowledge_admin_service = KnowledgeAdminService()
