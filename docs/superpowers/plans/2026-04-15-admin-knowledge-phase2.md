# Admin Knowledge Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 2 admin knowledge-management workflow: stable document records, admin upload/replace/delete/restore flows, chunk-count metrics, and a proper admin UI while keeping the frontend knowledge center read-only.

**Architecture:** Keep the existing file-system-based knowledge storage and RAG runtime, but promote `knowledge_admin_service` into the single source of truth for knowledge records, file paths, access flags, deletion state, and chunk metrics. Route all admin write operations through the service, then make both the admin API and frontend read-only API consume the same document registry so visibility, identifiers, and metrics stay aligned.

**Tech Stack:** FastAPI, Pydantic, Python `unittest`, Vue 3, Axios, Vite, `vitest`, `@vue/test-utils`, existing RAG runtime helpers in `backend/app/services/rag_runtime.py`

**Repository Alignment Decisions:**
- Keep `backend/app/services/knowledge_admin_service.py` as the canonical place for registry migration, file storage moves, checksum computation, chunk metrics, and audit writes.
- Preserve a backward-compatible `update_document_access(...)` wrapper inside `knowledge_admin_service` until all existing callers and tests have switched to document-ID-based methods.
- Admin upload and replace endpoints should accept `multipart/form-data`, with `tags` and `allowed_roles` encoded as JSON strings in the form payload.
- Backend tests should patch `app.services.knowledge_admin_service.get_rag_tool` and `get_loaded_rag_tool` with a fake RAG tool rather than booting the real vector stack.

---

## Planned File Structure

### Backend

- Modify: `backend/app/services/knowledge_admin_service.py`
  - Upgrade the registry model, migrate legacy records, manage file lifecycle, and own chunk/checksum data
- Modify: `backend/app/api/admin/knowledge.py`
  - Add document list/detail/create/update/replace/delete/restore routes
- Modify: `backend/app/api/v1/knowledge_base.py`
  - Read frontend-visible documents from the knowledge registry by `document_id`

### Backend Tests

- Create: `tests/admin/test_knowledge_admin_registry.py`
  - Registry migration and default-record coverage
- Create: `tests/admin/test_knowledge_admin_phase2_api.py`
  - Admin upload/replace/delete/restore flows with a fake RAG tool
- Modify: `tests/admin/test_knowledge_visibility.py`
  - Frontend read-only filtering and document-ID behavior after the registry upgrade

### Frontend

- Modify: `frontend/src/admin-api.js`
  - Add knowledge create/detail/replace/delete/restore client helpers
- Modify: `frontend/src/api/index.js`
  - Reduce frontend knowledge API to read-only operations for documents
- Modify: `frontend/src/admin/pages/KnowledgeAdminPage.vue`
  - Replace the Phase 1 card grid with toolbar, table, details panel, and action dialogs
- Modify: `frontend/src/components/KnowledgeBasePanel.vue`
  - Keep frontend knowledge center read-only while displaying registry-backed metrics

### Frontend Tests

- Create: `frontend/src/admin/__tests__/knowledge-admin-page.test.js`
  - Page-level rendering, metrics, and role-based action availability

### Docs

- Modify: `README.md`
- Modify: `docs/admin-api.md`
- Modify: `docs/admin-admin-guide.md`
- Create: `docs/reports/2026-04-15-admin-knowledge-phase2-test-report.md`

---

### Task 1: Upgrade The Knowledge Registry To Stable Document Records

**Files:**
- Modify: `backend/app/services/knowledge_admin_service.py`
- Test: `tests/admin/test_knowledge_admin_registry.py`

- [ ] **Step 1: Write the failing test**

```python
import json
import shutil
import unittest
import uuid
from pathlib import Path

from app.services.knowledge_admin_service import knowledge_admin_service


TEST_TMP_ROOT = Path(__file__).resolve().parents[2] / ".pytest_cache" / "knowledge-admin-registry-tests"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


class KnowledgeAdminRegistryTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TEST_TMP_ROOT / uuid.uuid4().hex
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir = self.temp_dir / "docs"
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path = self.temp_dir / "knowledge-registry.json"
        knowledge_admin_service.reconfigure(
            docs_dir=str(self.docs_dir),
            metadata_path=str(self.metadata_path),
        )

    def tearDown(self):
        knowledge_admin_service.reconfigure()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_legacy_registry_is_upgraded_and_preserves_access_flags(self):
        (self.docs_dir / "alpha.txt").write_text("alpha", encoding="utf-8")
        self.metadata_path.write_text(
            json.dumps(
                {
                    "alpha.txt": {
                        "visible_to_frontend": False,
                        "published": True,
                        "allowed_roles": ["admin"],
                        "updated_at": "2026-04-15T10:00:00",
                    }
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        documents = knowledge_admin_service.list_documents()

        self.assertEqual(len(documents), 1)
        document = documents[0]
        self.assertTrue(document["document_id"].startswith("doc_"))
        self.assertEqual(document["filename"], "alpha.txt")
        self.assertEqual(document["allowed_roles"], ["admin"])
        self.assertEqual(document["published"], True)
        self.assertEqual(document["visible_to_frontend"], False)
        self.assertEqual(document["deleted"], False)
        self.assertEqual(document["chunk_count"], 0)

        saved = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["version"], 2)
        self.assertIn(document["document_id"], saved["documents"])

    def test_untracked_file_gets_default_registry_record(self):
        (self.docs_dir / "beta.txt").write_text("beta", encoding="utf-8")

        documents = knowledge_admin_service.list_documents()

        self.assertEqual(len(documents), 1)
        document = documents[0]
        self.assertEqual(document["filename"], "beta.txt")
        self.assertEqual(document["published"], True)
        self.assertEqual(document["visible_to_frontend"], True)
        self.assertEqual(
            document["allowed_roles"],
            ["user", "operator", "admin", "super_admin"],
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_admin_registry -v`
Expected: FAIL because `list_documents()` still returns filename-keyed records without `document_id`, registry versioning, or legacy migration.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/knowledge_admin_service.py
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


REGISTRY_VERSION = 2


class KnowledgeAdminService:
    @staticmethod
    def _now_iso() -> str:
        return datetime.now().isoformat()

    @staticmethod
    def _new_document_id() -> str:
        return f"doc_{uuid4().hex}"

    @staticmethod
    def _default_registry() -> Dict[str, Any]:
        return {"version": REGISTRY_VERSION, "documents": {}}

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
        now = self._now_iso()
        stat = file_path.stat()
        return {
            "document_id": document_id,
            "filename": filename,
            "file_type": file_path.suffix.lower(),
            "storage_name": file_path.name,
            "storage_path": str(file_path),
            "size": stat.st_size,
            "checksum": self._compute_checksum(file_path),
            "chunk_count": int(legacy.get("chunk_count", 0) or 0),
            "description": legacy.get("description", ""),
            "tags": legacy.get("tags", []),
            "published": bool(legacy.get("published", True)),
            "visible_to_frontend": bool(legacy.get("visible_to_frontend", True)),
            "allowed_roles": self._normalize_roles(legacy.get("allowed_roles")),
            "deleted": bool(legacy.get("deleted", False)),
            "created_at": legacy.get("created_at") or now,
            "created_by": legacy.get("created_by"),
            "updated_at": legacy.get("updated_at") or now,
            "updated_by": legacy.get("updated_by"),
            "deleted_at": legacy.get("deleted_at"),
            "deleted_by": legacy.get("deleted_by"),
        }

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

    def _load_registry(self) -> Dict[str, Any]:
        if not self.metadata_path.exists():
            return self._migrate_legacy_registry({})
        try:
            raw = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            raw = {}
        registry = self._normalize_registry(raw)
        return self._sync_registry_with_files(registry)

    def _sync_registry_with_files(self, registry: Dict[str, Any]) -> Dict[str, Any]:
        changed = False
        existing_by_storage = {
            Path(record["storage_path"]).name: document_id
            for document_id, record in registry["documents"].items()
            if not record.get("deleted")
        }
        for document_path in sorted(self.docs_dir.iterdir(), key=lambda item: item.name.lower()):
            if not document_path.is_file() or document_path.suffix.lower() not in ALLOWED_DOC_EXTENSIONS:
                continue
            if document_path.name in existing_by_storage:
                continue
            document_id = self._new_document_id()
            registry["documents"][document_id] = self._build_record(
                document_id=document_id,
                file_path=document_path,
                filename=document_path.name,
            )
            changed = True
        if changed:
            self._save_registry(registry)
        return registry

    def list_documents(
        self,
        *,
        keyword: Optional[str] = None,
        status: str = "active",
        published: Optional[bool] = None,
        visible_to_frontend: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        registry = self._load_registry()
        documents = list(registry["documents"].values())
        if status == "active":
            documents = [doc for doc in documents if not doc.get("deleted")]
        elif status == "deleted":
            documents = [doc for doc in documents if doc.get("deleted")]
        if published is not None:
            documents = [doc for doc in documents if doc.get("published") is published]
        if visible_to_frontend is not None:
            documents = [doc for doc in documents if doc.get("visible_to_frontend") is visible_to_frontend]
        if keyword:
            needle = keyword.strip().lower()
            documents = [
                doc
                for doc in documents
                if needle in doc["filename"].lower()
                or needle in doc.get("description", "").lower()
                or any(needle in tag.lower() for tag in doc.get("tags", []))
            ]
        return sorted(documents, key=lambda item: item["filename"].lower())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_admin_registry -v`
Expected: PASS with `2 tests` and `0 failures`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/knowledge_admin_service.py tests/admin/test_knowledge_admin_registry.py
git commit -m "feat: add knowledge registry v2 migration"
```

---

### Task 2: Add Admin Upload, Replace, Delete, And Restore APIs

**Files:**
- Modify: `backend/app/services/knowledge_admin_service.py`
- Modify: `backend/app/api/admin/knowledge.py`
- Test: `tests/admin/test_knowledge_admin_phase2_api.py`

- [ ] **Step 1: Write the failing test**

```python
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.admin_main import app as admin_app
from app.services.auth_service import auth_service
from app.services.knowledge_admin_service import knowledge_admin_service


TEST_TMP_ROOT = Path(__file__).resolve().parents[2] / ".pytest_cache" / "knowledge-admin-phase2-api-tests"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


class FakeRagTool:
    def __init__(self):
        self._db_available = True
        self.collection = self
        self.source_chunks = {}

    def get(self, include=None):
        metadatas = []
        for source, count in self.source_chunks.items():
            metadatas.extend([{"source_file": source}] * count)
        return {"metadatas": metadatas}

    def count(self):
        return sum(self.source_chunks.values())

    def delete_documents_by_source(self, source):
        return self.source_chunks.pop(source, 0)

    def load_document(self, source, chunk_size=400, chunk_overlap=50):
        line_count = max(1, len(Path(source).read_text(encoding="utf-8").splitlines()))
        return [{"metadata": {"source_file": source}, "page_content": f"chunk-{index}"} for index in range(line_count)]

    def add_documents_to_vector_db(self, documents):
        source = documents[0]["metadata"]["source_file"]
        self.source_chunks[source] = len(documents)
        return [f"{source}::{index}" for index, _ in enumerate(documents)]


class KnowledgeAdminPhase2ApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TEST_TMP_ROOT / uuid.uuid4().hex
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir = self.temp_dir / "docs"
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path = self.temp_dir / "knowledge-registry.json"
        self.audit_path = self.temp_dir / "admin-audit.jsonl"

        db_path = self.temp_dir / "auth.sqlite3"
        auth_service.reconfigure(database_url=f"sqlite:///{db_path.as_posix()}")
        knowledge_admin_service.reconfigure(
            docs_dir=str(self.docs_dir),
            metadata_path=str(self.metadata_path),
            audit_storage_path=str(self.audit_path),
        )

        self.client = TestClient(admin_app)
        self.admin = auth_service.register("knowledge.phase2.admin", "password123")
        auth_service.update_user_role(self.admin["id"], "admin")
        token = auth_service.create_token(self.admin["id"], self.admin["username"])["token"]
        self.headers = {"Authorization": f"Bearer {token}"}

        self.rag_tool = FakeRagTool()
        self.get_rag_tool_patcher = patch("app.services.knowledge_admin_service.get_rag_tool", return_value=self.rag_tool)
        self.get_loaded_rag_tool_patcher = patch(
            "app.services.knowledge_admin_service.get_loaded_rag_tool",
            return_value=self.rag_tool,
        )
        self.get_rag_tool_patcher.start()
        self.get_loaded_rag_tool_patcher.start()

    def tearDown(self):
        self.get_rag_tool_patcher.stop()
        self.get_loaded_rag_tool_patcher.stop()
        knowledge_admin_service.reconfigure()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_admin_can_create_replace_delete_and_restore_document(self):
        create_response = self.client.post(
            "/api/admin/knowledge/documents",
            headers=self.headers,
            files={"file": ("alpha.txt", b"line-1\nline-2\nline-3", "text/plain")},
            data={
                "description": "alpha doc",
                "tags": '["faq","release"]',
                "allowed_roles": '["user","admin","super_admin"]',
                "published": "true",
                "visible_to_frontend": "false",
            },
        )
        self.assertEqual(create_response.status_code, 200)
        created = create_response.json()
        self.assertTrue(created["document_id"].startswith("doc_"))
        self.assertEqual(created["chunk_count"], 3)
        self.assertEqual(created["tags"], ["faq", "release"])
        self.assertEqual(created["published"], True)

        replace_response = self.client.post(
            f"/api/admin/knowledge/documents/{created['document_id']}/replace",
            headers=self.headers,
            files={"file": ("alpha-v2.txt", b"line-1\nline-2", "text/plain")},
        )
        self.assertEqual(replace_response.status_code, 200)
        replaced = replace_response.json()
        self.assertEqual(replaced["document_id"], created["document_id"])
        self.assertEqual(replaced["filename"], "alpha-v2.txt")
        self.assertEqual(replaced["chunk_count"], 2)
        self.assertEqual(replaced["published"], True)

        delete_response = self.client.delete(
            f"/api/admin/knowledge/documents/{created['document_id']}",
            headers=self.headers,
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json()["deleted"], True)

        restore_response = self.client.post(
            f"/api/admin/knowledge/documents/{created['document_id']}/restore",
            headers=self.headers,
        )
        self.assertEqual(restore_response.status_code, 200)
        restored = restore_response.json()
        self.assertEqual(restored["document_id"], created["document_id"])
        self.assertEqual(restored["published"], False)
        self.assertEqual(restored["visible_to_frontend"], False)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_admin_phase2_api -v`
Expected: FAIL because `/api/admin/knowledge/documents` only supports list and patch, and `knowledge_admin_service` has no create/replace/delete/restore methods.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/knowledge_admin_service.py
from app.services.rag_runtime import get_loaded_rag_tool, get_rag_tool, rag_params_manager


class KnowledgeAdminService:
    def _trash_dir(self) -> Path:
        trash_dir = self.metadata_path.parent / "trash"
        trash_dir.mkdir(parents=True, exist_ok=True)
        return trash_dir

    def _get_record(self, document_id: str) -> Dict[str, Any]:
        registry = self._load_registry()
        try:
            return registry["documents"][document_id]
        except KeyError as exc:
            raise FileNotFoundError(document_id) from exc

    def create_document(
        self,
        *,
        filename: str,
        content: bytes,
        actor_id: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        published: bool = False,
        visible_to_frontend: bool = False,
        allowed_roles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        safe = self._safe_filename(filename)
        document_id = self._new_document_id()
        file_path = self.docs_dir / safe
        file_path.write_bytes(content)
        rag_tool = get_rag_tool()
        documents = rag_tool.load_document(
            str(file_path),
            chunk_size=rag_params_manager.get_chunk_size(),
            chunk_overlap=rag_params_manager.get_chunk_overlap(),
        )
        doc_ids = rag_tool.add_documents_to_vector_db(documents)

        registry = self._load_registry()
        record = self._build_record(document_id=document_id, file_path=file_path, filename=safe)
        record.update(
            {
                "description": description.strip(),
                "tags": tags or [],
                "published": bool(published),
                "visible_to_frontend": bool(visible_to_frontend),
                "allowed_roles": self._normalize_roles(allowed_roles),
                "created_by": actor_id,
                "updated_by": actor_id,
                "chunk_count": len(doc_ids),
            }
        )
        registry["documents"][document_id] = record
        self._save_registry(registry)
        self.audit_log_service.write(
            actor_id=actor_id,
            module="knowledge",
            action="create_document",
            target_type="document",
            target_id=document_id,
            result="success",
            extra={"filename": safe, "chunk_count": len(doc_ids)},
        )
        return record

    def replace_document(self, document_id: str, filename: str, content: bytes, actor_id: str) -> Dict[str, Any]:
        registry = self._load_registry()
        record = self._get_record(document_id)
        old_path = Path(record["storage_path"])
        safe = self._safe_filename(filename)
        new_path = self.docs_dir / safe
        old_chunk_count = int(record.get("chunk_count", 0))
        old_checksum = record.get("checksum")

        rag_tool = get_rag_tool()
        if old_path.exists():
            rag_tool.delete_documents_by_source(str(old_path))
            old_path.unlink()
        new_path.write_bytes(content)
        documents = rag_tool.load_document(
            str(new_path),
            chunk_size=rag_params_manager.get_chunk_size(),
            chunk_overlap=rag_params_manager.get_chunk_overlap(),
        )
        doc_ids = rag_tool.add_documents_to_vector_db(documents)

        updated = self._build_record(document_id=document_id, file_path=new_path, filename=safe, legacy=record)
        updated["chunk_count"] = len(doc_ids)
        updated["updated_at"] = self._now_iso()
        updated["updated_by"] = actor_id
        registry["documents"][document_id] = updated
        self._save_registry(registry)
        self.audit_log_service.write(
            actor_id=actor_id,
            module="knowledge",
            action="replace_document",
            target_type="document",
            target_id=document_id,
            result="success",
            extra={
                "old_checksum": old_checksum,
                "new_checksum": updated["checksum"],
                "old_chunk_count": old_chunk_count,
                "new_chunk_count": len(doc_ids),
            },
        )
        return updated

    def update_document_metadata(
        self,
        document_id: str,
        *,
        actor_id: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        visible_to_frontend: Optional[bool] = None,
        published: Optional[bool] = None,
        allowed_roles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        registry = self._load_registry()
        record = self._get_record(document_id)
        before = {
            "description": record.get("description", ""),
            "tags": record.get("tags", []),
            "visible_to_frontend": record.get("visible_to_frontend", True),
            "published": record.get("published", True),
            "allowed_roles": record.get("allowed_roles", []),
        }
        if description is not None:
            record["description"] = description.strip()
        if tags is not None:
            record["tags"] = [tag for tag in tags if tag]
        if visible_to_frontend is not None:
            record["visible_to_frontend"] = bool(visible_to_frontend)
        if published is not None:
            record["published"] = bool(published)
        if allowed_roles is not None:
            record["allowed_roles"] = self._normalize_roles(allowed_roles)
        record["updated_at"] = self._now_iso()
        record["updated_by"] = actor_id
        registry["documents"][document_id] = record
        self._save_registry(registry)
        self.audit_log_service.write(
            actor_id=actor_id,
            module="knowledge",
            action="update_document",
            target_type="document",
            target_id=document_id,
            result="success",
            extra={"before": before, "after": record},
        )
        return record
```

```python
# backend/app/api/admin/knowledge.py
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel


def _parse_list_field(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    parsed = json.loads(raw)
    if not isinstance(parsed, list):
        raise ValueError("field must be a JSON array")
    return [str(item).strip() for item in parsed if str(item).strip()]


class UpdateKnowledgeDocumentRequest(BaseModel):
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    visible_to_frontend: Optional[bool] = None
    published: Optional[bool] = None
    allowed_roles: Optional[List[str]] = None


@router.post("/knowledge/documents")
async def create_knowledge_document(
    file: UploadFile = File(...),
    description: str = Form(""),
    tags: str = Form("[]"),
    allowed_roles: str = Form("[]"),
    published: bool = Form(False),
    visible_to_frontend: bool = Form(False),
    user=Depends(require_admin_user("admin", "super_admin")),
):
    return knowledge_admin_service.create_document(
        filename=file.filename or "",
        content=await file.read(),
        actor_id=user["id"],
        description=description,
        tags=_parse_list_field(tags),
        published=published,
        visible_to_frontend=visible_to_frontend,
        allowed_roles=_parse_list_field(allowed_roles),
    )


@router.post("/knowledge/documents/{document_id}/replace")
async def replace_knowledge_document(
    document_id: str,
    file: UploadFile = File(...),
    user=Depends(require_admin_user("admin", "super_admin")),
):
    return knowledge_admin_service.replace_document(
        document_id=document_id,
        filename=file.filename or "",
        content=await file.read(),
        actor_id=user["id"],
    )


@router.patch("/knowledge/documents/{document_id}")
async def update_knowledge_document(
    document_id: str,
    request: UpdateKnowledgeDocumentRequest,
    user=Depends(require_admin_user("admin", "super_admin")),
):
    return knowledge_admin_service.update_document_metadata(
        document_id,
        actor_id=user["id"],
        description=request.description,
        tags=request.tags,
        visible_to_frontend=request.visible_to_frontend,
        published=request.published,
        allowed_roles=request.allowed_roles,
    )


@router.delete("/knowledge/documents/{document_id}")
async def delete_knowledge_document(
    document_id: str,
    user=Depends(require_admin_user("admin", "super_admin")),
):
    return knowledge_admin_service.delete_document(document_id, actor_id=user["id"])


@router.post("/knowledge/documents/{document_id}/restore")
async def restore_knowledge_document(
    document_id: str,
    user=Depends(require_admin_user("admin", "super_admin")),
):
    return knowledge_admin_service.restore_document(document_id, actor_id=user["id"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_admin_phase2_api -v`
Expected: PASS with `1 test` and `0 failures`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/knowledge_admin_service.py backend/app/api/admin/knowledge.py tests/admin/test_knowledge_admin_phase2_api.py
git commit -m "feat: add admin knowledge phase2 api flows"
```

---

### Task 3: Move Frontend Read-Only Knowledge Endpoints To Registry-Backed Document IDs

**Files:**
- Modify: `backend/app/api/v1/knowledge_base.py`
- Modify: `tests/admin/test_knowledge_visibility.py`

- [ ] **Step 1: Write the failing test**

```python
def test_frontend_list_uses_document_ids_and_metrics(self):
    admin_docs = self.admin_client.get(
        "/api/admin/knowledge/documents",
        headers=self.admin_headers,
    ).json()["documents"]
    alpha_doc = next(doc for doc in admin_docs if doc["filename"] == "alpha.txt")

    response = self.user_client.get("/api/v1/knowledge-base", headers=self.user_headers)

    self.assertEqual(response.status_code, 200)
    self.assertEqual(len(response.json()["documents"]), 1)
    payload = response.json()["documents"][0]
    self.assertEqual(payload["id"], alpha_doc["document_id"])
    self.assertEqual(payload["filename"], "alpha.txt")
    self.assertIn("chunk_count", payload)


def test_deleted_document_is_hidden_from_frontend(self):
    admin_docs = self.admin_client.get(
        "/api/admin/knowledge/documents",
        headers=self.admin_headers,
    ).json()["documents"]
    alpha_doc = next(doc for doc in admin_docs if doc["filename"] == "alpha.txt")

    delete_response = self.admin_client.delete(
        f"/api/admin/knowledge/documents/{alpha_doc['document_id']}",
        headers=self.admin_headers,
    )
    self.assertEqual(delete_response.status_code, 200)

    user_response = self.user_client.get("/api/v1/knowledge-base", headers=self.user_headers)
    self.assertEqual(user_response.status_code, 200)
    self.assertEqual(user_response.json()["documents"], [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_visibility -v`
Expected: FAIL because the frontend API still lists raw files by filename and detail routes still resolve the file path directly from the URL parameter.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/api/v1/knowledge_base.py
@router.get("/knowledge-base", response_model=DocumentListResponse)
async def list_documents(current_user=Depends(require_authenticated_user())):
    documents = knowledge_admin_service.list_frontend_documents(current_user["role"])
    payload = [
        DocumentInfo(
            id=document["document_id"],
            filename=document["filename"],
            file_path=document["storage_path"],
            file_type=document["file_type"],
            chunk_count=document.get("chunk_count", 0),
            size=document["size"],
            upload_time=document["created_at"],
            update_time=document["updated_at"],
        )
        for document in documents
    ]
    return DocumentListResponse(documents=payload, total=len(payload))


@router.get("/knowledge-base/{document_id}", response_model=DocumentContentResponse)
async def get_document(document_id: str, current_user=Depends(require_authenticated_user())):
    record = knowledge_admin_service.get_frontend_document(
        document_id=document_id,
        role=current_user["role"],
    )
    file_path = Path(record["storage_path"])
    content = _read_document_content(file_path)
    return DocumentContentResponse(
        id=record["document_id"],
        filename=record["filename"],
        content=content,
        chunks=[],
    )
```

```python
# backend/app/services/knowledge_admin_service.py
def list_frontend_documents(self, role: str) -> List[Dict[str, Any]]:
    return [
        document
        for document in self.list_documents(status="active")
        if self.can_role_access(document, role)
    ]


def get_document(self, document_id: str, include_deleted: bool = False) -> Dict[str, Any]:
    record = self._get_record(document_id)
    if record.get("deleted") and not include_deleted:
        raise FileNotFoundError(document_id)
    return record


def get_frontend_document(self, document_id: str, role: str) -> Dict[str, Any]:
    record = self.get_document(document_id, include_deleted=False)
    if not self.can_role_access(record, role):
        raise FileNotFoundError(document_id)
    return record
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_visibility -v`
Expected: PASS with all visibility tests green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/knowledge_base.py backend/app/services/knowledge_admin_service.py tests/admin/test_knowledge_visibility.py
git commit -m "feat: align frontend knowledge reads with document registry"
```

---

### Task 4: Expand Frontend API Clients And Add Page-Level Knowledge Admin Tests

**Files:**
- Modify: `frontend/src/admin-api.js`
- Modify: `frontend/src/api/index.js`
- Create: `frontend/src/admin/__tests__/knowledge-admin-page.test.js`

- [ ] **Step 1: Write the failing test**

```javascript
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import KnowledgeAdminPage from '../pages/KnowledgeAdminPage.vue'
import { knowledgeAdminApi } from '../../admin-api.js'
import { getAuthUser } from '../../auth/session.js'

vi.mock('../../admin-api.js', () => ({
  knowledgeAdminApi: {
    listDocuments: vi.fn(),
    getDocument: vi.fn(),
    createDocument: vi.fn(),
    updateDocument: vi.fn(),
    replaceDocument: vi.fn(),
    deleteDocument: vi.fn(),
    restoreDocument: vi.fn()
  }
}))

vi.mock('../../auth/session.js', () => ({
  getAuthUser: vi.fn()
}))

describe('KnowledgeAdminPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders document metrics and keeps operator in read-only mode', async () => {
    getAuthUser.mockReturnValue({ role: 'operator' })
    knowledgeAdminApi.listDocuments.mockResolvedValue({
      data: {
        documents: [
          {
            document_id: 'doc_alpha',
            filename: 'alpha.txt',
            file_type: '.txt',
            size: 1024,
            chunk_count: 4,
            description: 'alpha doc',
            tags: ['faq'],
            published: true,
            visible_to_frontend: true,
            allowed_roles: ['user', 'admin'],
            deleted: false,
            updated_at: '2026-04-15T12:00:00'
          }
        ],
        total: 1
      }
    })

    const wrapper = mount(KnowledgeAdminPage)
    await flushPromises()

    expect(wrapper.text()).toContain('alpha.txt')
    expect(wrapper.text()).toContain('4 个分块')
    expect(wrapper.text()).toContain('运营只读')
    expect(wrapper.find('[data-testid="knowledge-upload-trigger"]').attributes('disabled')).toBeDefined()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test:admin -- src/admin/__tests__/knowledge-admin-page.test.js`
Expected: FAIL because `knowledgeAdminApi` has no Phase 2 client methods and `KnowledgeAdminPage.vue` does not render table metrics or read-only operator markers.

- [ ] **Step 3: Write minimal implementation**

```javascript
// frontend/src/admin-api.js
function buildKnowledgeFormData(payload) {
  const formData = new FormData()
  formData.append('file', payload.file)
  formData.append('description', payload.description || '')
  formData.append('tags', JSON.stringify(payload.tags || []))
  formData.append('allowed_roles', JSON.stringify(payload.allowed_roles || []))
  formData.append('published', JSON.stringify(Boolean(payload.published)))
  formData.append('visible_to_frontend', JSON.stringify(Boolean(payload.visible_to_frontend)))
  return formData
}

export const knowledgeAdminApi = {
  listDocuments(params = {}) {
    return adminApi.get('/knowledge/documents', { params })
  },

  getDocument(documentId) {
    return adminApi.get(`/knowledge/documents/${encodeURIComponent(documentId)}`)
  },

  createDocument(payload) {
    return adminApi.post('/knowledge/documents', buildKnowledgeFormData(payload), {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  updateDocument(documentId, payload) {
    return adminApi.patch(`/knowledge/documents/${encodeURIComponent(documentId)}`, payload)
  },

  replaceDocument(documentId, file) {
    const formData = new FormData()
    formData.append('file', file)
    return adminApi.post(`/knowledge/documents/${encodeURIComponent(documentId)}/replace`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  deleteDocument(documentId) {
    return adminApi.delete(`/knowledge/documents/${encodeURIComponent(documentId)}`)
  },

  restoreDocument(documentId) {
    return adminApi.post(`/knowledge/documents/${encodeURIComponent(documentId)}/restore`)
  }
}
```

```javascript
// frontend/src/api/index.js
export const knowledgeBaseApi = {
  getDocuments() {
    return api.get('/knowledge-base')
  },

  getDocument(docId) {
    return api.get(`/knowledge-base/${encodeDocId(docId)}`)
  },

  getParams() {
    return api.get('/knowledge-base/params')
  },

  updateParams(params) {
    return api.post('/knowledge-base/params', params)
  },

  reloadKnowledgeBase() {
    return api.post('/knowledge-base/reload')
  },

  clearCache() {
    return api.post('/knowledge-base/clear-cache')
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm run test:admin -- src/admin/__tests__/knowledge-admin-page.test.js`
Expected: PASS with `1 test` and `0 failures`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/admin-api.js frontend/src/api/index.js frontend/src/admin/__tests__/knowledge-admin-page.test.js
git commit -m "test: add knowledge admin page contract coverage"
```

---

### Task 5: Rebuild The Admin Knowledge Page Around Table, Metrics, And Actions

**Files:**
- Modify: `frontend/src/admin/pages/KnowledgeAdminPage.vue`
- Modify: `frontend/src/components/KnowledgeBasePanel.vue`
- Test: `frontend/src/admin/__tests__/knowledge-admin-page.test.js`

- [ ] **Step 1: Extend the failing test for admin actions and deleted-state filtering**

```javascript
it('lets admin filter deleted documents and exposes action buttons', async () => {
  getAuthUser.mockReturnValue({ role: 'admin' })
  knowledgeAdminApi.listDocuments.mockResolvedValue({
    data: {
      documents: [
        {
          document_id: 'doc_deleted',
          filename: 'deleted.txt',
          file_type: '.txt',
          size: 256,
          chunk_count: 1,
          description: 'deleted doc',
          tags: ['archive'],
          published: false,
          visible_to_frontend: false,
          allowed_roles: ['admin'],
          deleted: true,
          updated_at: '2026-04-15T12:30:00'
        }
      ],
      total: 1
    }
  })

  const wrapper = mount(KnowledgeAdminPage)
  await flushPromises()

  expect(wrapper.find('[data-testid="knowledge-status-filter"]').exists()).toBe(true)
  expect(wrapper.find('[data-testid="knowledge-upload-trigger"]').attributes('disabled')).toBeUndefined()
  expect(wrapper.text()).toContain('已删除')
  expect(wrapper.text()).toContain('恢复文档')
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test:admin -- src/admin/__tests__/knowledge-admin-page.test.js`
Expected: FAIL because the page still renders the old card layout without toolbar filters, upload entry, deleted-state markers, or restore actions.

- [ ] **Step 3: Write minimal implementation**

```vue
<!-- frontend/src/admin/pages/KnowledgeAdminPage.vue -->
<template>
  <section class="knowledge-admin-page">
    <header class="page-hero">
      <div>
        <p class="eyebrow">知识库管理</p>
        <h3>上传、替换、删除并审查知识文件指标</h3>
        <p>后台统一维护知识文件的元数据、显隐范围、发布状态与分块指标。</p>
      </div>
      <button
        data-testid="knowledge-upload-trigger"
        class="solid-btn"
        :disabled="isOperator || uploading"
        @click="openCreatePanel"
      >
        {{ uploading ? '上传中…' : '上传知识文件' }}
      </button>
    </header>

    <div class="toolbar">
      <input v-model.trim="filters.keyword" class="search-input" placeholder="搜索文件名、标签或描述" @change="loadDocuments" />
      <select v-model="filters.status" data-testid="knowledge-status-filter" @change="loadDocuments">
        <option value="active">有效文档</option>
        <option value="deleted">已删除</option>
        <option value="all">全部文档</option>
      </select>
      <button class="ghost-btn" @click="loadDocuments" :disabled="loading">刷新列表</button>
    </div>

    <table class="knowledge-table">
      <thead>
        <tr>
          <th>文件名</th>
          <th>标签</th>
          <th>大小</th>
          <th>分块数量</th>
          <th>状态</th>
          <th>更新时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="doc in documents" :key="doc.document_id" @click="selectDocument(doc)">
          <td>{{ doc.filename }}</td>
          <td>{{ doc.tags?.join('、') || '未设置' }}</td>
          <td>{{ formatFileSize(doc.size) }}</td>
          <td>{{ doc.chunk_count || 0 }} 个分块</td>
          <td>
            <span class="status-pill" :class="{ deleted: doc.deleted, published: doc.published }">
              {{ doc.deleted ? '已删除' : doc.published ? '已发布' : '草稿' }}
            </span>
          </td>
          <td>{{ formatDate(doc.updated_at) }}</td>
          <td>{{ isOperator ? '运营只读' : doc.deleted ? '恢复文档' : '编辑文档' }}</td>
        </tr>
      </tbody>
    </table>

    <aside v-if="selectedDocument" class="detail-panel">
      <h4>{{ selectedDocument.filename }}</h4>
      <p>{{ selectedDocument.chunk_count || 0 }} 个分块 · {{ selectedDocument.document_id }}</p>
      <p>{{ selectedDocument.description || '暂无描述' }}</p>
      <div class="actions">
        <button class="ghost-btn" :disabled="isOperator || selectedDocument.deleted" @click="replaceCurrent">替换文件</button>
        <button
          v-if="!selectedDocument.deleted"
          class="danger-btn"
          :disabled="isOperator"
          @click="deleteCurrent"
        >
          删除文档
        </button>
        <button
          v-else
          class="solid-btn"
          :disabled="isOperator"
          @click="restoreCurrent"
        >
          恢复文档
        </button>
      </div>
    </aside>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import { knowledgeAdminApi } from '../../admin-api.js'
import { getAuthUser } from '../../auth/session.js'

const documents = ref([])
const selectedDocument = ref(null)
const loading = ref(false)
const uploading = ref(false)
const replacing = ref(false)
const deleting = ref(false)
const restoring = ref(false)
const filters = ref({ keyword: '', status: 'active' })
const isOperator = computed(() => (getAuthUser()?.role || '') === 'operator')

async function loadDocuments() {
  loading.value = true
  try {
    const response = await knowledgeAdminApi.listDocuments({
      keyword: filters.value.keyword || undefined,
      status: filters.value.status
    })
    documents.value = response.data.documents || []
    selectedDocument.value = documents.value[0] || null
  } finally {
    loading.value = false
  }
}

async function openCreatePanel() {
  const chooser = document.createElement('input')
  chooser.type = 'file'
  chooser.accept = '.txt,.pdf,.docx'
  chooser.onchange = async () => {
    const file = chooser.files?.[0]
    if (!file) return
    uploading.value = true
    try {
      await knowledgeAdminApi.createDocument({
        file,
        description: '',
        tags: [],
        published: false,
        visible_to_frontend: false,
        allowed_roles: ['user', 'operator', 'admin', 'super_admin']
      })
      await loadDocuments()
    } finally {
      uploading.value = false
    }
  }
  chooser.click()
}

function selectDocument(document) { selectedDocument.value = document }

async function replaceCurrent() {
  if (!selectedDocument.value) return
  const chooser = document.createElement('input')
  chooser.type = 'file'
  chooser.accept = '.txt,.pdf,.docx'
  chooser.onchange = async () => {
    const file = chooser.files?.[0]
    if (!file) return
    replacing.value = true
    try {
      const response = await knowledgeAdminApi.replaceDocument(selectedDocument.value.document_id, file)
      selectedDocument.value = response.data
      await loadDocuments()
    } finally {
      replacing.value = false
    }
  }
  chooser.click()
}

async function deleteCurrent() {
  if (!selectedDocument.value) return
  if (!window.confirm(`确认删除 ${selectedDocument.value.filename} 吗？`)) return
  deleting.value = true
  try {
    const response = await knowledgeAdminApi.deleteDocument(selectedDocument.value.document_id)
    selectedDocument.value = response.data
    await loadDocuments()
  } finally {
    deleting.value = false
  }
}

async function restoreCurrent() {
  if (!selectedDocument.value) return
  if (!window.confirm(`确认恢复 ${selectedDocument.value.filename} 吗？恢复后默认不会前台可见。`)) return
  restoring.value = true
  try {
    const response = await knowledgeAdminApi.restoreDocument(selectedDocument.value.document_id)
    selectedDocument.value = response.data
    await loadDocuments()
  } finally {
    restoring.value = false
  }
}

function formatDate(value) { return value ? new Date(value).toLocaleString('zh-CN') : '未知时间' }
function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

onMounted(loadDocuments)
</script>
```

```vue
<!-- frontend/src/components/KnowledgeBasePanel.vue -->
<button
  v-for="doc in documents"
  :key="doc.id"
  :class="['doc-item', { active: selectedDoc?.id === doc.id }]"
  @click="selectDocument(doc)"
>
  <div>
    <strong>{{ doc.filename }}</strong>
    <p>{{ formatFileSize(doc.size) }} · {{ doc.chunk_count || 0 }} 个分块</p>
  </div>
  <span>{{ formatDate(doc.update_time) }}</span>
</button>
```

- [ ] **Step 4: Run the frontend tests and build**

Run: `npm run test:admin -- src/admin/__tests__/knowledge-admin-page.test.js`
Expected: PASS with the new admin page expectations.

Run: `npm run build`
Expected: PASS and produce `dist/admin.html` plus bundled assets without unresolved imports.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/admin/pages/KnowledgeAdminPage.vue frontend/src/components/KnowledgeBasePanel.vue frontend/src/admin/__tests__/knowledge-admin-page.test.js
git commit -m "feat: rebuild admin knowledge management page"
```

---

### Task 6: Update Documentation And Run Full Phase 2 Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/admin-api.md`
- Modify: `docs/admin-admin-guide.md`
- Create: `docs/reports/2026-04-15-admin-knowledge-phase2-test-report.md`

- [ ] **Step 1: Update the documentation**

```markdown
<!-- README.md -->
## 当前阶段

2026-04-15 的 Phase 2 已完成以下知识库后台能力：

- 后台上传知识文件
- 后台替换已存在知识文件
- 后台软删除与恢复知识文件
- 后台知识文件指标：文件大小、分块数量、校验值、更新时间
- 前台只读知识库按 `document_id` 与统一主记录读取
```

```markdown
<!-- docs/admin-api.md -->
## 后台知识库管理

### `GET /api/admin/knowledge/documents`
支持 `keyword`、`status`、`published`、`visible_to_frontend`

### `POST /api/admin/knowledge/documents`
上传知识文件并创建主记录

### `POST /api/admin/knowledge/documents/{document_id}/replace`
替换知识文件，保留原 `document_id`

### `DELETE /api/admin/knowledge/documents/{document_id}`
软删除知识文件

### `POST /api/admin/knowledge/documents/{document_id}/restore`
恢复知识文件，恢复后默认未发布且前台隐藏
```

```markdown
<!-- docs/reports/2026-04-15-admin-knowledge-phase2-test-report.md -->
# 2026-04-15 后台知识库 Phase 2 测试报告

## 覆盖范围

- 知识文件主记录迁移
- 后台上传 / 替换 / 删除 / 恢复
- 前台只读知识库的文档 ID 与可见性过滤
- 知识库后台页面指标与角色限制
```

- [ ] **Step 2: Run backend verification**

Run:

```bash
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_auth_role_foundation tests.admin.test_admin_access_and_audit tests.admin.test_user_admin_api tests.admin.test_memory_admin_api tests.admin.test_knowledge_visibility tests.admin.test_settings_admin_api tests.admin.test_knowledge_admin_registry tests.admin.test_knowledge_admin_phase2_api tests.test_memory_admin_localization -v
```

Expected: PASS with all admin backend tests green, including the two new knowledge Phase 2 suites.

- [ ] **Step 3: Run frontend verification**

Run:

```bash
npm run test:admin
npm run build
```

Expected:

- `vitest` reports all admin tests passing, including `knowledge-admin-page.test.js`
- Vite build succeeds without unresolved imports

- [ ] **Step 4: Commit**

```bash
git add README.md docs/admin-api.md docs/admin-admin-guide.md docs/reports/2026-04-15-admin-knowledge-phase2-test-report.md
git commit -m "docs: document admin knowledge phase2"
```
```
```
