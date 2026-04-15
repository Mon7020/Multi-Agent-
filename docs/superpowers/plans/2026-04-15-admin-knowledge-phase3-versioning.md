# Admin Knowledge Phase 3 Versioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build immutable knowledge version history and a safe rollback workflow in the admin module while keeping current publish, visibility, role, and deleted state unchanged.

**Architecture:** Keep `registry.json` as the current-state source of truth and add `data/knowledge/history/<document_id>/manifest.json` plus snapshot files for immutable version history. Extend `knowledge_admin_service` to create snapshots on create, replace, and rollback; expose `/versions` and `/rollback` admin routes; then add a version-history panel inside the existing admin knowledge page.

**Tech Stack:** FastAPI, Pydantic, Vue 3, Vitest, Python `unittest`, filesystem JSON storage, existing RAG runtime, Conda `test3`

---

## File Structure

- Modify: `backend/app/services/knowledge_admin_service.py`
- Modify: `backend/app/api/admin/knowledge.py`
- Modify: `frontend/src/admin-api.js`
- Modify: `frontend/src/admin/pages/KnowledgeAdminPage.vue`
- Modify: `frontend/src/admin/__tests__/knowledge-admin-page.test.js`
- Create: `tests/admin/test_knowledge_admin_versioning_service.py`
- Create: `tests/admin/test_knowledge_admin_versioning_api.py`
- Modify: `README.md`
- Modify: `docs/admin-api.md`
- Modify: `docs/admin-admin-guide.md`
- Create: `docs/reports/2026-04-15-admin-knowledge-phase3-test-report.md`

### Task 1: Add Version Snapshot Storage

**Files:**
- Modify: `backend/app/services/knowledge_admin_service.py`
- Create: `tests/admin/test_knowledge_admin_versioning_service.py`

- [ ] **Step 1: Write the failing service test**

```python
def test_create_and_replace_append_immutable_versions(self):
    created = knowledge_admin_service.create_document(
        filename="alpha.txt",
        content=b"line-1\nline-2\nline-3",
        actor_id="admin-1",
        description="alpha doc",
        tags=["faq"],
        published=True,
        visible_to_frontend=True,
        allowed_roles=["user", "admin"],
    )
    replaced = knowledge_admin_service.replace_document(
        created["document_id"],
        filename="alpha-v2.txt",
        content=b"line-1\nline-2",
        actor_id="admin-2",
    )
    manifest = json.loads((self.history_dir / created["document_id"] / "manifest.json").read_text(encoding="utf-8"))
    self.assertEqual(manifest["latest_version_no"], 2)
    self.assertEqual([item["action"] for item in manifest["versions"]], ["create", "replace"])
    self.assertEqual(manifest["current_version_id"], replaced["current_version_id"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_admin_versioning_service.KnowledgeAdminVersioningServiceTest.test_create_and_replace_append_immutable_versions -v`

Expected: FAIL because `history_dir`, manifests, and `current_version_id` do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
class KnowledgeConflictError(ValueError):
    pass

def reconfigure(
    self,
    docs_dir: Optional[str] = None,
    metadata_path: Optional[str] = None,
    audit_storage_path: Optional[str] = None,
    trash_dir: Optional[str] = None,
    history_dir: Optional[str] = None,
) -> None:
    project_root = self._project_root()
    self.docs_dir = Path(docs_dir) if docs_dir else project_root / "data" / "docs"
    self.docs_dir.mkdir(parents=True, exist_ok=True)
    self.metadata_path = Path(metadata_path) if metadata_path else project_root / "data" / "knowledge" / "registry.json"
    self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
    self.trash_dir = Path(trash_dir) if trash_dir else self.metadata_path.parent / "trash"
    self.trash_dir.mkdir(parents=True, exist_ok=True)
    self.history_dir = Path(history_dir) if history_dir else self.metadata_path.parent / "history"
    self.history_dir.mkdir(parents=True, exist_ok=True)

def _default_manifest(self, document_id: str) -> Dict[str, Any]:
    return {"document_id": document_id, "current_version_id": None, "latest_version_no": 0, "versions": []}

def _append_version_snapshot(self, *, record: Dict[str, Any], actor_id: str, action: str, reason=None, source_version_id=None) -> Dict[str, Any]:
    manifest = self._load_manifest(record["document_id"])
    version_id = f"ver_{uuid4().hex}"
    version_no = int(manifest["latest_version_no"]) + 1
    snapshot_path = self._snapshot_file_path(record["document_id"], version_id, record["file_type"])
    snapshot_path.write_bytes(self._record_storage_path(record).read_bytes())
    snapshot = {
        "version_id": version_id,
        "version_no": version_no,
        "document_id": record["document_id"],
        "action": action,
        "source_version_id": source_version_id,
        "filename": record["filename"],
        "file_type": record["file_type"],
        "snapshot_storage_path": str(snapshot_path.resolve()),
        "size": record["size"],
        "checksum": record["checksum"],
        "chunk_count": record["chunk_count"],
        "description": record.get("description", ""),
        "tags": self._normalize_tags(record.get("tags", [])),
        "created_at": self._now_iso(),
        "created_by": actor_id,
        "reason": reason,
    }
    manifest["latest_version_no"] = version_no
    manifest["current_version_id"] = version_id
    manifest["versions"].append(snapshot)
    self._save_manifest(record["document_id"], manifest)
    return snapshot
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_admin_versioning_service.KnowledgeAdminVersioningServiceTest.test_create_and_replace_append_immutable_versions -v`

Expected: PASS with snapshot files under `history/<document_id>/`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/knowledge_admin_service.py tests/admin/test_knowledge_admin_versioning_service.py
git commit -m "feat: add knowledge document version snapshots"
```

### Task 2: Implement Safe Rollback Semantics

**Files:**
- Modify: `backend/app/services/knowledge_admin_service.py`
- Modify: `tests/admin/test_knowledge_admin_versioning_service.py`

- [ ] **Step 1: Write failing rollback tests**

```python
def test_rollback_creates_new_current_version_without_changing_operating_flags(self):
    created = knowledge_admin_service.create_document(filename="alpha.txt", content=b"line-1\nline-2\nline-3", actor_id="admin-1", description="alpha v1", tags=["faq"], published=True, visible_to_frontend=False, allowed_roles=["user", "admin"])
    knowledge_admin_service.replace_document(created["document_id"], filename="alpha-v2.txt", content=b"line-1\nline-2", actor_id="admin-2")
    knowledge_admin_service.update_document_metadata(created["document_id"], actor_id="admin-2", description="edited on v2", tags=["release"], visible_to_frontend=True, published=True, allowed_roles=["admin"])
    rolled = knowledge_admin_service.rollback_document(created["document_id"], target_version_id=created["current_version_id"], actor_id="admin-3", reason="restore stable")
    self.assertEqual(rolled["filename"], "alpha.txt")
    self.assertEqual(rolled["description"], "alpha v1")
    self.assertEqual(rolled["tags"], ["faq"])
    self.assertEqual(rolled["published"], True)
    self.assertEqual(rolled["visible_to_frontend"], True)
    self.assertEqual(rolled["allowed_roles"], ["admin"])

def test_deleted_document_cannot_be_rolled_back(self):
    created = knowledge_admin_service.create_document(filename="deleted.txt", content=b"line-1\nline-2", actor_id="admin-1")
    knowledge_admin_service.delete_document(created["document_id"], actor_id="admin-2")
    with self.assertRaisesRegex(KnowledgeConflictError, "restore the document before rollback"):
        knowledge_admin_service.rollback_document(created["document_id"], target_version_id=created["current_version_id"], actor_id="admin-3")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_admin_versioning_service.KnowledgeAdminVersioningServiceTest.test_rollback_creates_new_current_version_without_changing_operating_flags tests.admin.test_knowledge_admin_versioning_service.KnowledgeAdminVersioningServiceTest.test_deleted_document_cannot_be_rolled_back -v`

Expected: FAIL because `rollback_document` does not exist or does not preserve current operating flags.

- [ ] **Step 3: Write minimal rollback implementation**

```python
def rollback_document(self, document_id: str, target_version_id: str, *, actor_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    registry = self._load_registry()
    document_id, current = self._resolve_record(document_id, registry)
    if current.get("deleted"):
        raise KnowledgeConflictError("restore the document before rollback")
    target = self.get_document_version(document_id, target_version_id)
    snapshot_path = Path(target["snapshot_storage_path"])
    if not snapshot_path.exists():
        raise KnowledgeConflictError("snapshot file is unavailable for rollback")
    active_path = self._record_storage_path(current)
    previous_bytes = active_path.read_bytes()
    previous_source = str(active_path.resolve())
    try:
        self._delete_chunks(previous_source)
        active_path.write_bytes(snapshot_path.read_bytes())
        chunk_count = self._index_file(active_path)
    except Exception:
        active_path.write_bytes(previous_bytes)
        self._index_file(active_path)
        raise
    rolled = self._build_record(document_id=document_id, file_path=active_path, filename=target["filename"], legacy=current)
    rolled.update({
        "description": target.get("description", ""),
        "tags": self._normalize_tags(target.get("tags", [])),
        "published": current["published"],
        "visible_to_frontend": current["visible_to_frontend"],
        "allowed_roles": self._normalize_roles(current.get("allowed_roles")),
        "deleted": current["deleted"],
        "updated_at": self._now_iso(),
        "updated_by": actor_id,
        "chunk_count": chunk_count,
    })
    snapshot = self._append_version_snapshot(record=rolled, actor_id=actor_id, action="rollback", reason=reason, source_version_id=target_version_id)
    rolled["current_version_id"] = snapshot["version_id"]
    registry["documents"][document_id] = rolled
    self._save_registry(registry)
    self.audit_log_service.write(actor_id=actor_id, module="knowledge", action="knowledge.version.rollback", target_type="document", target_id=document_id, result="success", extra={"target_version_id": target_version_id, "new_version_id": snapshot["version_id"], "reason": reason, "old_checksum": current["checksum"], "new_checksum": rolled["checksum"], "old_chunk_count": current["chunk_count"], "new_chunk_count": rolled["chunk_count"]})
    return self._serialize_record(rolled)
```

- [ ] **Step 4: Run the full service file**

Run: `D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_admin_versioning_service -v`

Expected: PASS with rollback generating a new version and leaving `published`, `visible_to_frontend`, `allowed_roles`, and `deleted` unchanged.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/knowledge_admin_service.py tests/admin/test_knowledge_admin_versioning_service.py
git commit -m "feat: add safe knowledge document rollback"
```

### Task 3: Expose Version History and Rollback APIs

**Files:**
- Modify: `backend/app/api/admin/knowledge.py`
- Create: `tests/admin/test_knowledge_admin_versioning_api.py`

- [ ] **Step 1: Write the failing API test**

```python
def test_operator_can_list_versions_and_admin_can_rollback(self):
    created = knowledge_admin_service.create_document(filename="alpha.txt", content=b"line-1\nline-2\nline-3", actor_id=self.admin["id"], description="alpha v1", tags=["faq"], published=True, visible_to_frontend=False, allowed_roles=["user", "admin"])
    knowledge_admin_service.replace_document(created["document_id"], filename="alpha-v2.txt", content=b"line-1\nline-2", actor_id=self.admin["id"])
    versions_response = self.client.get(f"/api/admin/knowledge/documents/{created['document_id']}/versions", headers=self.operator_headers)
    self.assertEqual(versions_response.status_code, 200)
    detail_response = self.client.get(f"/api/admin/knowledge/documents/{created['document_id']}/versions/{created['current_version_id']}", headers=self.operator_headers)
    self.assertEqual(detail_response.status_code, 200)
    rollback_response = self.client.post(f"/api/admin/knowledge/documents/{created['document_id']}/rollback", json={"target_version_id": created["current_version_id"], "reason": "restore stable"}, headers=self.admin_headers)
    self.assertEqual(rollback_response.status_code, 200)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_admin_versioning_api.KnowledgeAdminVersioningApiTest.test_operator_can_list_versions_and_admin_can_rollback -v`

Expected: FAIL with `404 Not Found` for the new routes.

- [ ] **Step 3: Write minimal route implementation**

```python
class RollbackKnowledgeDocumentRequest(BaseModel):
    target_version_id: str
    reason: Optional[str] = None

def _raise_knowledge_http_error(exc: Exception) -> None:
    if isinstance(exc, FileNotFoundError):
        raise HTTPException(status_code=404, detail="document or version not found") from exc
    if isinstance(exc, FileExistsError):
        raise HTTPException(status_code=409, detail="document already exists") from exc
    if isinstance(exc, KnowledgeConflictError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise exc

@router.get("/knowledge/documents/{document_id}/versions")
async def list_knowledge_document_versions(
    document_id: str,
    user=Depends(require_admin_user("operator", "admin", "super_admin")),
):
    del user
    return knowledge_admin_service.list_document_versions(document_id)

@router.get("/knowledge/documents/{document_id}/versions/{version_id}")
async def get_knowledge_document_version(
    document_id: str,
    version_id: str,
    user=Depends(require_admin_user("operator", "admin", "super_admin")),
):
    del user
    return knowledge_admin_service.get_document_version(document_id, version_id)

@router.post("/knowledge/documents/{document_id}/rollback")
async def rollback_knowledge_document(document_id: str, request: RollbackKnowledgeDocumentRequest, user=Depends(require_admin_user("admin", "super_admin"))):
    rolled = knowledge_admin_service.rollback_document(document_id, target_version_id=request.target_version_id, actor_id=user["id"], reason=request.reason)
    return {**rolled, "target_version_id": request.target_version_id, "new_version_id": rolled["current_version_id"]}
```

- [ ] **Step 4: Run the full API file**

Run: `D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_admin_versioning_api -v`

Expected: PASS with operator read-only access and admin rollback access.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/admin/knowledge.py tests/admin/test_knowledge_admin_versioning_api.py
git commit -m "feat: expose admin knowledge version history api"
```

### Task 4: Add Version History and Rollback to the Admin Page

**Files:**
- Modify: `frontend/src/admin-api.js`
- Modify: `frontend/src/admin/pages/KnowledgeAdminPage.vue`
- Modify: `frontend/src/admin/__tests__/knowledge-admin-page.test.js`

- [ ] **Step 1: Write the failing page tests**

```javascript
it('loads version history and shows the selected version preview', async () => {
  knowledgeAdminApi.listDocuments.mockResolvedValue({ data: { documents: [makeDocument()], total: 1 } })
  knowledgeAdminApi.listDocumentVersions.mockResolvedValue({
    data: {
      document_id: 'doc_alpha',
      current_version_id: 'ver_current',
      versions: [
        { version_id: 'ver_current', version_no: 2, action: 'replace', filename: 'alpha-v2.txt', description: 'release doc', tags: ['release'], checksum: 'abc123', chunk_count: 2, created_at: '2026-04-15T12:05:00', created_by: 'admin-2', is_current: true },
        { version_id: 'ver_v1', version_no: 1, action: 'create', filename: 'alpha.txt', description: 'alpha doc', tags: ['faq'], checksum: 'def456', chunk_count: 4, created_at: '2026-04-15T12:00:00', created_by: 'admin-1', is_current: false }
      ]
    }
  })
  const wrapper = mount(KnowledgeAdminPage)
  await flushPromises()
  expect(wrapper.text()).toContain('版本历史')
  expect(wrapper.text()).toContain('当前版本')
  expect(wrapper.text()).toContain('release doc')
})

it('rolls back a version and refreshes current metrics', async () => {
  knowledgeAdminApi.listDocuments.mockResolvedValueOnce({ data: { documents: [makeDocument({ filename: 'alpha-v2.txt', chunk_count: 2, size: 2048 })], total: 1 } }).mockResolvedValueOnce({ data: { documents: [makeDocument({ filename: 'alpha.txt', chunk_count: 4, size: 1024 })], total: 1 } })
  knowledgeAdminApi.listDocumentVersions.mockResolvedValueOnce({ data: { document_id: 'doc_alpha', current_version_id: 'ver_current', versions: [{ version_id: 'ver_current', version_no: 2, action: 'replace', filename: 'alpha-v2.txt', description: 'release doc', tags: ['release'], checksum: 'abc123', chunk_count: 2, created_at: '2026-04-15T12:05:00', created_by: 'admin-2', is_current: true }, { version_id: 'ver_v1', version_no: 1, action: 'create', filename: 'alpha.txt', description: 'alpha doc', tags: ['faq'], checksum: 'def456', chunk_count: 4, created_at: '2026-04-15T12:00:00', created_by: 'admin-1', is_current: false }] } }).mockResolvedValueOnce({ data: { document_id: 'doc_alpha', current_version_id: 'ver_rollback', versions: [{ version_id: 'ver_rollback', version_no: 3, action: 'rollback', source_version_id: 'ver_v1', filename: 'alpha.txt', description: 'alpha doc', tags: ['faq'], checksum: 'xyz999', chunk_count: 4, created_at: '2026-04-15T12:10:00', created_by: 'admin-3', is_current: true }] } })
  knowledgeAdminApi.rollbackDocument.mockResolvedValue({ data: { document_id: 'doc_alpha', target_version_id: 'ver_v1', new_version_id: 'ver_rollback', current_version_id: 'ver_rollback', filename: 'alpha.txt', chunk_count: 4 } })
  const wrapper = mount(KnowledgeAdminPage)
  await flushPromises()
  await wrapper.get('[data-testid="knowledge-version-row-ver_v1"]').trigger('click')
  await wrapper.get('[data-testid="knowledge-version-rollback"]').trigger('click')
  await flushPromises()
  expect(knowledgeAdminApi.rollbackDocument).toHaveBeenCalledWith('doc_alpha', { target_version_id: 'ver_v1', reason: '' })
  expect(wrapper.text()).toContain('已基于版本 ver_v1 生成新版本 ver_rollback')
  expect(wrapper.text()).toContain('4 个分块')
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test:admin -- src/admin/__tests__/knowledge-admin-page.test.js`

Expected: FAIL because the page and client have no version-history or rollback methods.

- [ ] **Step 3: Write minimal client and page implementation**

```javascript
// frontend/src/admin-api.js
listDocumentVersions(documentId) {
  return adminApi.get(`/knowledge/documents/${encodeURIComponent(documentId)}/versions`)
},
getDocumentVersion(documentId, versionId) {
  return adminApi.get(`/knowledge/documents/${encodeURIComponent(documentId)}/versions/${encodeURIComponent(versionId)}`)
},
rollbackDocument(documentId, payload) {
  return adminApi.post(`/knowledge/documents/${encodeURIComponent(documentId)}/rollback`, payload)
}
```

```vue
<script setup>
const versions = ref([])
const selectedVersion = ref(null)
const versionsLoading = ref(false)
const rollbacking = ref(false)

watch(() => selectedDocument.value?.document_id, async (documentId) => {
  if (!documentId) {
    versions.value = []
    selectedVersion.value = null
    return
  }
  const response = await knowledgeAdminApi.listDocumentVersions(documentId)
  versions.value = response.data.versions || []
  selectedVersion.value = versions.value[0] || null
}, { immediate: true })

async function rollbackSelectedVersion() {
  if (!selectedDocument.value || !selectedVersion.value || isOperator.value || selectedDocument.value.deleted) return
  const confirmed = window.confirm(`确认回滚到版本 ${selectedVersion.value.version_id} 吗？会回滚文件内容、文件名、描述和标签，不会修改发布、显隐、角色和删除状态。`)
  if (!confirmed) return
  const response = await knowledgeAdminApi.rollbackDocument(selectedDocument.value.document_id, { target_version_id: selectedVersion.value.version_id, reason: '' })
  setSuccess(`已基于版本 ${response.data.target_version_id} 生成新版本 ${response.data.new_version_id}`)
  await loadDocuments(response.data.document_id)
  const versionsResponse = await knowledgeAdminApi.listDocumentVersions(response.data.document_id)
  versions.value = versionsResponse.data.versions || []
  selectedVersion.value = versions.value.find((item) => item.version_id === response.data.new_version_id) || versions.value[0] || null
}
</script>
```

- [ ] **Step 4: Run targeted and full frontend verification**

Run: `npm run test:admin -- src/admin/__tests__/knowledge-admin-page.test.js`

Expected: PASS with history and rollback cases green.

Run: `npm run test:admin`

Expected: PASS with all admin frontend tests green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/admin-api.js frontend/src/admin/pages/KnowledgeAdminPage.vue frontend/src/admin/__tests__/knowledge-admin-page.test.js
git commit -m "feat: add knowledge version history to admin page"
```

### Task 5: Update Docs and Run Full Regression

**Files:**
- Modify: `README.md`
- Modify: `docs/admin-api.md`
- Modify: `docs/admin-admin-guide.md`
- Create: `docs/reports/2026-04-15-admin-knowledge-phase3-test-report.md`

- [ ] **Step 1: Update markdown docs**

```md
## 后台知识库 Phase 3

- 历史目录：`data/knowledge/history/`
- 新增接口：
  - `GET /api/admin/knowledge/documents/{document_id}/versions`
  - `GET /api/admin/knowledge/documents/{document_id}/versions/{version_id}`
  - `POST /api/admin/knowledge/documents/{document_id}/rollback`
- 回滚范围：
  - 会回滚：文件内容、文件名、描述、标签
  - 不会回滚：`published`、`visible_to_frontend`、`allowed_roles`、`deleted`
```

- [ ] **Step 2: Run new targeted verification**

Run: `D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_admin_versioning_service tests.admin.test_knowledge_admin_versioning_api -v`

Expected: PASS with all new Phase 3 backend tests green.

Run: `npm run test:admin -- src/admin/__tests__/knowledge-admin-page.test.js`

Expected: PASS with the new versioning UI tests green.

- [ ] **Step 3: Run full regression and write the report**

Run: `D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_admin_registry tests.admin.test_knowledge_admin_phase2_api tests.admin.test_knowledge_visibility tests.admin.test_knowledge_admin_versioning_service tests.admin.test_knowledge_admin_versioning_api -v`

Expected: PASS with all admin knowledge backend suites green.

Run: `npm run test:admin`

Expected: PASS with all admin frontend tests green.

Run: `npm run build`

Expected: PASS with Vite build succeeding.

```md
# 2026-04-15 Admin Knowledge Phase 3 Test Report

- Branch: `feature/admin-knowledge-phase2`
- Focus: immutable version history + safe rollback
- Backend:
  - `tests.admin.test_knowledge_admin_versioning_service`
  - `tests.admin.test_knowledge_admin_versioning_api`
  - existing Phase 2 knowledge suites
- Frontend:
  - `src/admin/__tests__/knowledge-admin-page.test.js`
  - `npm run test:admin`
  - `npm run build`
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/admin-api.md docs/admin-admin-guide.md docs/reports/2026-04-15-admin-knowledge-phase3-test-report.md
git commit -m "docs: document admin knowledge phase3 versioning"
```
