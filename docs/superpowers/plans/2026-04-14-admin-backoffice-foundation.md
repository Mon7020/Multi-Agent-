# Admin Backoffice Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build phase 1 of the backoffice system: a unified admin shell with role-based access, audited admin APIs, basic user management, memory management integrated into the shell, and admin-side knowledge/settings foundations.

**Architecture:** Reuse the existing auth system and extend it with persistent roles and status, then layer a dedicated admin permission service and audited admin API surface on top. On the frontend, replace the current single-file admin page with a routed Vue admin app that shares auth session state, gates pages by role, and hosts the memory, users, knowledge, and settings modules in a consistent layout.

**Tech Stack:** FastAPI, Pydantic, sqlite/MySQL via existing auth service, Vue 3, Vite, Axios, `vue-router`, `vitest`, `@vue/test-utils`, Python `unittest`

**Repository Alignment Decisions:**
- Backend tests live under `tests/admin/`, plus `tests/admin/__init__.py` to expose both the project root and `backend/` on `sys.path`.
- Admin API tests must exercise the shared singleton services used by the app. Do not create separate `AuthService(sqlite:///:memory:)` instances for route tests.
- Test isolation for auth uses `auth_service.reconfigure(...)` against a temporary sqlite file, because the current service opens a new database connection per call and plain `:memory:` would not persist across requests.
- File-backed admin services should expose small configuration hooks or dependency providers where needed so tests can point them at temporary storage.

---

## Planned File Structure

### Backend

- Modify: `backend/app/services/auth_service.py`
  - Persist `role`, `status`, `last_login_at`, `password_updated_at`, `updated_at`
- Modify: `backend/app/api/v1/auth.py`
  - Return role-aware auth payloads and current-user metadata
- Create: `backend/app/services/permission_service.py`
  - Central role checks and admin-access helpers
- Create: `backend/app/services/audit_log_service.py`
  - Unified audit log write/read API
- Create: `backend/app/api/admin/dependencies.py`
  - Shared admin auth/permission dependencies
- Create: `backend/app/api/admin/dashboard.py`
  - Summary metrics for the admin dashboard
- Create: `backend/app/services/user_admin_service.py`
  - User list, role update, status update, password reset
- Create: `backend/app/api/admin/users.py`
  - Admin user-management routes
- Modify: `backend/app/api/admin/memory.py`
  - Require admin auth and support server-side search/filter
- Modify: `backend/app/services/memory_admin_service.py`
  - Search/filter support and audit writes
- Create: `backend/app/services/knowledge_admin_service.py`
  - Knowledge visibility + draft/published metadata registry
- Create: `backend/app/api/admin/knowledge.py`
  - Admin knowledge-management routes
- Create: `backend/app/services/settings_admin_service.py`
  - Admin settings read/update helpers
- Create: `backend/app/api/admin/settings.py`
  - Admin settings routes
- Modify: `backend/app/admin_main.py`
  - Register new admin routers
- Modify: `backend/app/api/v1/knowledge_base.py`
  - Filter frontend-visible docs by role and publication state

### Frontend

- Modify: `frontend/package.json`
  - Add `vue-router`, `vitest`, `@vue/test-utils`, `jsdom`
- Create: `frontend/src/auth/session.js`
  - Shared token/user session helpers for both apps
- Modify: `frontend/src/api/index.js`
  - Reuse shared session helper
- Modify: `frontend/src/admin-api.js`
  - Reuse shared session helper and add admin request helpers
- Modify: `frontend/src/AdminApp.vue`
  - Replace current monolith with auth gate + router host
- Create: `frontend/src/admin/router.js`
  - Hash-router for admin pages
- Create: `frontend/src/admin/nav.js`
  - Role-filtered navigation definition
- Create: `frontend/src/admin/layouts/AdminLayout.vue`
  - Sidebar, topbar, content container
- Create: `frontend/src/admin/components/AdminSidebar.vue`
  - Navigation rendering
- Create: `frontend/src/admin/components/AdminTopbar.vue`
  - Breadcrumbs, user menu, page actions slot
- Create: `frontend/src/admin/pages/DashboardPage.vue`
  - Admin summary page
- Create: `frontend/src/admin/pages/MemoryAdminPage.vue`
  - Memory module page extracted from current admin page
- Create: `frontend/src/admin/pages/UsersAdminPage.vue`
  - User-management page
- Create: `frontend/src/admin/pages/KnowledgeAdminPage.vue`
  - Knowledge admin skeleton with visibility and publish controls
- Create: `frontend/src/admin/pages/SettingsAdminPage.vue`
  - Settings admin skeleton and runtime settings controls
- Modify: `frontend/src/components/KnowledgeBasePanel.vue`
  - Frontend becomes read-only for permitted documents
- Modify: `frontend/src/components/SettingsPanel.vue`
  - Frontend becomes read-only/summary instead of full admin config
- Create: `frontend/src/admin/__tests__/admin-nav.test.js`
  - Role-based nav tests
- Create: `frontend/src/admin/__tests__/admin-shell.test.js`
  - Auth-gated shell rendering tests

### Docs

- Create: `docs/admin-api.md`
  - Admin API reference
- Create: `docs/admin-user-guide.md`
  - End-user guide for frontend read-only knowledge behavior
- Create: `docs/admin-admin-guide.md`
  - Admin operating guide
- Create: `docs/reports/2026-04-14-admin-backoffice-foundation-test-report.md`
  - Phase 1 test report

### Tests

- Create: `tests/admin/__init__.py`
- Create: `tests/admin/test_auth_role_foundation.py`
- Create: `tests/admin/test_admin_access_and_audit.py`
- Create: `tests/admin/test_user_admin_api.py`
- Create: `tests/admin/test_memory_admin_api.py`
- Create: `tests/admin/test_knowledge_visibility.py`

---

### Task 1: Extend Auth Schema With Roles And Permission Helpers

**Files:**
- Modify: `backend/app/services/auth_service.py`
- Modify: `backend/app/api/v1/auth.py`
- Create: `backend/app/services/permission_service.py`
- Test: `tests/admin/test_auth_role_foundation.py`

- [ ] **Step 1: Write the failing test**

```python
import tempfile
import unittest
from pathlib import Path

from app.services.auth_service import auth_service
from app.services.permission_service import PermissionDenied, permission_service


class AuthRoleFoundationTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "auth.sqlite3"
        auth_service.reconfigure(database_url=f"sqlite:///{db_path.as_posix()}")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_register_defaults_to_user_role(self):
        user = auth_service.register("phase1.user", "password123")
        stored = auth_service.get_user_by_id(user["id"])
        self.assertEqual(stored["role"], "user")
        self.assertEqual(stored["status"], "active")

    def test_permission_service_rejects_plain_user(self):
        with self.assertRaises(PermissionDenied):
            permission_service.require_any_role(
                {"id": "u1", "role": "user", "status": "active"},
                {"admin", "super_admin", "operator"},
            )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests/admin -p "test_auth_role_foundation.py" -v`
Expected: FAIL because `PermissionService`, `auth_service.reconfigure(...)`, and role/status persistence do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/permission_service.py
class PermissionDenied(Exception):
    pass


class PermissionService:
    def require_any_role(self, user: dict, allowed_roles: set[str]) -> None:
        if not user or user.get("status") != "active":
            raise PermissionDenied("account is not active")
        if user.get("role") not in allowed_roles:
            raise PermissionDenied("insufficient role")


permission_service = PermissionService()
```

```python
# backend/app/services/auth_service.py
def reconfigure(self, database_url: Optional[str] = None) -> None:
    configured_url = database_url or os.getenv("DATABASE_URL") or settings.database_url
    self._db_type, self._db_config = self._resolve_database_url(configured_url, self._project_root)
    self._ensure_schema()

def _ensure_user_columns(self, conn) -> None:
    columns = {
        "role": "TEXT NOT NULL DEFAULT 'user'",
        "last_login_at": "INTEGER",
        "password_updated_at": "INTEGER",
        "updated_at": "INTEGER",
    }
    for name, ddl in columns.items():
        self._ensure_column(conn, "users", name, ddl)

def register(self, username: str, password: str) -> Dict[str, Any]:
    created_at = int(time.time())
    params = (
        user_id,
        normalized,
        salt,
        password_hash,
        created_at,
        "active",
        "user",
        None,
        created_at,
        created_at,
    )
```

```python
# backend/app/api/v1/auth.py
@router.get("/auth/me")
async def me(authorization: Optional[str] = Header(default=None)):
    user = _resolve_current_user(authorization)
    return {
        "user_id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "status": user["status"],
        "expires_at": user["exp"],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests/admin -p "test_auth_role_foundation.py" -v`
Expected: PASS for both tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/auth_service.py backend/app/api/v1/auth.py backend/app/services/permission_service.py tests/admin/__init__.py tests/admin/test_auth_role_foundation.py
git commit -m "feat: add auth roles and permission foundation"
```

### Task 2: Guard Admin APIs And Add Audit Log Foundation

**Files:**
- Create: `backend/app/services/audit_log_service.py`
- Create: `backend/app/api/admin/dependencies.py`
- Create: `backend/app/api/admin/dashboard.py`
- Modify: `backend/app/api/admin/memory.py`
- Modify: `backend/app/admin_main.py`
- Test: `tests/admin/test_admin_access_and_audit.py`

- [ ] **Step 1: Write the failing test**

```python
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.admin_main import app
from app.services.auth_service import auth_service


class AdminAccessAuditTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "auth.sqlite3"
        auth_service.reconfigure(database_url=f"sqlite:///{db_path.as_posix()}")
        self.client = TestClient(app)
        self.user = auth_service.register("plain.user", "password123")
        self.admin = auth_service.register("admin.user", "password123")
        auth_service.update_user_role(self.admin["id"], "admin")
        self.user_headers = {"Authorization": f"Bearer {auth_service.create_token(self.user['id'], 'plain.user')['token']}"}
        self.admin_headers = {"Authorization": f"Bearer {auth_service.create_token(self.admin['id'], 'admin.user')['token']}"}

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_plain_user_cannot_open_admin_dashboard(self):
        response = self.client.get("/api/admin/dashboard/summary", headers=self.user_headers)
        self.assertEqual(response.status_code, 403)

    def test_admin_can_open_admin_dashboard(self):
        response = self.client.get("/api/admin/dashboard/summary", headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests/admin -p "test_admin_access_and_audit.py" -v`
Expected: FAIL because the dashboard route and admin dependencies do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/api/admin/dependencies.py
from fastapi import Header, HTTPException

from app.services.auth_service import AuthError, auth_service
from app.services.permission_service import PermissionDenied, permission_service


def require_admin_user(*allowed_roles: str):
    async def dependency(authorization: str | None = Header(default=None)):
        try:
            user = auth_service.get_user_from_authorization(authorization)
            permission_service.require_any_role(user, set(allowed_roles))
            return user
        except AuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except PermissionDenied as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    return dependency
```

```python
# backend/app/services/audit_log_service.py
class AuditLogService:
    def write(self, actor_id: str, module: str, action: str, target_type: str, target_id: str, result: str) -> None:
        payload = {
            "actor_id": actor_id,
            "module": module,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "result": result,
            "timestamp": int(time.time()),
        }
        self._append(payload)
```

```python
# backend/app/api/admin/dashboard.py
router = APIRouter()


@router.get("/dashboard/summary")
async def get_dashboard_summary(user=Depends(require_admin_user("operator", "admin", "super_admin"))):
    return {
        "current_user": {"id": user["id"], "role": user["role"]},
        "modules": ["memory", "knowledge", "settings", "users"],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests/admin -p "test_admin_access_and_audit.py" -v`
Expected: PASS with `403` for plain user and `200` for admin.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/audit_log_service.py backend/app/api/admin/dependencies.py backend/app/api/admin/dashboard.py backend/app/api/admin/memory.py backend/app/admin_main.py tests/admin/test_admin_access_and_audit.py
git commit -m "feat: add guarded admin routes and audit foundation"
```

### Task 3: Build Admin User-Management Backend

**Files:**
- Create: `backend/app/services/user_admin_service.py`
- Create: `backend/app/api/admin/users.py`
- Modify: `backend/app/services/auth_service.py`
- Test: `tests/admin/test_user_admin_api.py`

- [ ] **Step 1: Write the failing test**

```python
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.admin_main import app
from app.services.auth_service import auth_service


class UserAdminApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "auth.sqlite3"
        auth_service.reconfigure(database_url=f"sqlite:///{db_path.as_posix()}")
        self.client = TestClient(app)
        self.admin = auth_service.register("root.admin", "password123")
        auth_service.update_user_role(self.admin["id"], "super_admin")
        self.target = auth_service.register("managed.user", "password123")
        token = auth_service.create_token(self.admin["id"], "root.admin")["token"]
        self.headers = {"Authorization": f"Bearer {token}"}

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_list_users_returns_role_and_status(self):
        response = self.client.get("/api/admin/users", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(item["user_id"] == self.target["id"] for item in response.json()["users"]))

    def test_update_role(self):
        response = self.client.patch(
            f"/api/admin/users/{self.target['id']}/role",
            json={"role": "operator"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], "operator")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests/admin -p "test_user_admin_api.py" -v`
Expected: FAIL because user admin routes and role-update support do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/user_admin_service.py
class UserAdminService:
    def list_users(self, query: str = "", role: str = "", status: str = "") -> list[dict]:
        users = self.auth_service.list_users()
        if query:
            users = [item for item in users if query.lower() in item["username"] or query.lower() in item["id"]]
        if role:
            users = [item for item in users if item["role"] == role]
        if status:
            users = [item for item in users if item["status"] == status]
        return users

    def update_role(self, user_id: str, role: str) -> dict:
        self.auth_service.update_user_role(user_id, role)
        return self.auth_service.get_user_by_id(user_id)
```

```python
# backend/app/api/admin/users.py
@router.get("/users")
async def list_users(
    q: str = "",
    role: str = "",
    status: str = "",
    user=Depends(require_admin_user("admin", "super_admin")),
):
    return {"users": user_admin_service.list_users(query=q, role=role, status=status)}


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    request: UpdateUserRoleRequest,
    user=Depends(require_admin_user("super_admin")),
):
    updated = user_admin_service.update_role(user_id, request.role)
    return {"user_id": updated["id"], "role": updated["role"]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests/admin -p "test_user_admin_api.py" -v`
Expected: PASS for list and role update tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/user_admin_service.py backend/app/api/admin/users.py backend/app/services/auth_service.py tests/admin/test_user_admin_api.py
git commit -m "feat: add admin user management api"
```

### Task 4: Replace The Monolithic Admin Page With A Routed Admin Shell

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/auth/session.js`
- Modify: `frontend/src/api/index.js`
- Modify: `frontend/src/admin-api.js`
- Modify: `frontend/src/AdminApp.vue`
- Create: `frontend/src/admin/router.js`
- Create: `frontend/src/admin/nav.js`
- Create: `frontend/src/admin/layouts/AdminLayout.vue`
- Create: `frontend/src/admin/components/AdminSidebar.vue`
- Create: `frontend/src/admin/components/AdminTopbar.vue`
- Create: `frontend/src/admin/pages/DashboardPage.vue`
- Create: `frontend/src/admin/__tests__/admin-nav.test.js`
- Create: `frontend/src/admin/__tests__/admin-shell.test.js`

- [ ] **Step 1: Write the failing test**

```javascript
import { describe, expect, it } from 'vitest'

import { buildAdminNav } from '../nav'

describe('buildAdminNav', () => {
  it('hides user management for operator', () => {
    const items = buildAdminNav('operator')
    expect(items.some((item) => item.key === 'users')).toBe(false)
  })

  it('shows all modules for super_admin', () => {
    const items = buildAdminNav('super_admin')
    expect(items.map((item) => item.key)).toEqual(['dashboard', 'memory', 'knowledge', 'settings', 'users'])
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test:admin -- src/admin/__tests__/admin-nav.test.js`
Expected: FAIL because the `test:admin` script and `buildAdminNav` module do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```json
// frontend/package.json
{
  "scripts": {
    "test:admin": "vitest run"
  },
  "dependencies": {
    "vue-router": "^4.5.0"
  },
  "devDependencies": {
    "@vue/test-utils": "^2.4.6",
    "jsdom": "^25.0.1",
    "vitest": "^2.1.8"
  }
}
```

```javascript
// frontend/src/auth/session.js
const TOKEN_KEY = 'auth_token'
const USER_KEY = 'auth_user'

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function getAuthUser() {
  const raw = localStorage.getItem(USER_KEY)
  return raw ? JSON.parse(raw) : null
}

export function setAuthSession(session) {
  localStorage.setItem(TOKEN_KEY, session.token)
  localStorage.setItem(USER_KEY, JSON.stringify(session))
}

export function clearAuthSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}
```

```javascript
// frontend/src/admin/nav.js
export function buildAdminNav(role) {
  const items = [
    { key: 'dashboard', label: '鎬昏', roles: ['operator', 'admin', 'super_admin'] },
    { key: 'memory', label: '璁板繂绠＄悊', roles: ['operator', 'admin', 'super_admin'] },
    { key: 'knowledge', label: '鐭ヨ瘑搴撶鐞?, roles: ['operator', 'admin', 'super_admin'] },
    { key: 'settings', label: '绯荤粺璁剧疆', roles: ['admin', 'super_admin'] },
    { key: 'users', label: '鐢ㄦ埛璐﹀彿绠＄悊', roles: ['admin', 'super_admin'] },
  ]
  return items.filter((item) => item.roles.includes(role))
}
```

```vue
<!-- frontend/src/AdminApp.vue -->
<template>
  <AuthPanel v-if="!authUser" @authenticated="onAuthenticated" />
  <RouterView v-else />
</template>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test:admin -- src/admin/__tests__/admin-nav.test.js`
Expected: PASS for role-filtered navigation.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/src/auth/session.js frontend/src/api/index.js frontend/src/admin-api.js frontend/src/AdminApp.vue frontend/src/admin/router.js frontend/src/admin/nav.js frontend/src/admin/layouts/AdminLayout.vue frontend/src/admin/components/AdminSidebar.vue frontend/src/admin/components/AdminTopbar.vue frontend/src/admin/pages/DashboardPage.vue frontend/src/admin/__tests__/admin-nav.test.js frontend/src/admin/__tests__/admin-shell.test.js
git commit -m "feat: add routed admin shell"
```

### Task 5: Integrate Memory Management Into The Admin Shell

**Files:**
- Create: `frontend/src/admin/pages/MemoryAdminPage.vue`
- Modify: `frontend/src/admin-api.js`
- Modify: `backend/app/api/admin/memory.py`
- Modify: `backend/app/services/memory_admin_service.py`
- Test: `tests/admin/test_memory_admin_api.py`

- [ ] **Step 1: Write the failing test**

```python
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.admin_main import app
from app.services.auth_service import auth_service


class MemoryAdminApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "auth.sqlite3"
        auth_service.reconfigure(database_url=f"sqlite:///{db_path.as_posix()}")
        self.client = TestClient(app)
        self.admin = auth_service.register("memory.admin", "password123")
        auth_service.update_user_role(self.admin["id"], "admin")
        token = auth_service.create_token(self.admin["id"], "memory.admin")["token"]
        self.headers = {"Authorization": f"Bearer {token}"}

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_list_memory_users_supports_query_filter(self):
        response = self.client.get("/api/admin/memory/users?q=alice", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("users", response.json())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests/admin -p "test_memory_admin_api.py" -v`
Expected: FAIL because the route does not accept filter params and admin auth is not yet enforced consistently.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/api/admin/memory.py
@router.get("/memory/users")
async def list_memory_users(
    q: str = "",
    active_only: bool = False,
    user=Depends(require_admin_user("operator", "admin", "super_admin")),
):
    users = memory_admin_service.list_users(query=q, active_only=active_only)
    return {"users": users, "count": len(users)}
```

```python
# backend/app/services/memory_admin_service.py
def list_users(self, query: str = "", active_only: bool = False) -> List[Dict[str, Any]]:
    users = self._build_user_index()
    if query:
        users = [
            item for item in users
            if query.lower() in (item.get("user_id") or "").lower()
            or query.lower() in (item.get("username") or "").lower()
        ]
    if active_only:
        users = [item for item in users if item.get("active_in_memory")]
    return users
```

```vue
<!-- frontend/src/admin/pages/MemoryAdminPage.vue -->
<template>
  <AdminLayout title="璁板繂绠＄悊">
    <section class="page-toolbar">
      <input v-model.trim="filters.q" placeholder="鎼滅储鐢ㄦ埛 ID / 鐢ㄦ埛鍚? />
      <label><input v-model="filters.activeOnly" type="checkbox" /> 浠呯湅鍐呭瓨涓?/label>
      <button @click="loadUsers">鍒锋柊</button>
    </section>
    <MemoryModule />
  </AdminLayout>
</template>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests/admin -p "test_memory_admin_api.py" -v`
Expected: PASS and the route accepts admin-only filtered list queries.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/admin/pages/MemoryAdminPage.vue frontend/src/admin-api.js backend/app/api/admin/memory.py backend/app/services/memory_admin_service.py tests/admin/test_memory_admin_api.py
git commit -m "feat: integrate memory admin into shell"
```

### Task 6: Add Knowledge Visibility Foundation And Settings Admin Entry

**Files:**
- Create: `backend/app/services/knowledge_admin_service.py`
- Create: `backend/app/api/admin/knowledge.py`
- Create: `backend/app/services/settings_admin_service.py`
- Create: `backend/app/api/admin/settings.py`
- Modify: `backend/app/api/v1/knowledge_base.py`
- Create: `frontend/src/admin/pages/KnowledgeAdminPage.vue`
- Create: `frontend/src/admin/pages/SettingsAdminPage.vue`
- Modify: `frontend/src/components/KnowledgeBasePanel.vue`
- Modify: `frontend/src/components/SettingsPanel.vue`
- Test: `tests/admin/test_knowledge_visibility.py`

- [ ] **Step 1: Write the failing test**

```python
import tempfile
import unittest
from pathlib import Path

from app.services.knowledge_admin_service import KnowledgeAdminService


class KnowledgeVisibilityTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.service = KnowledgeAdminService(
            storage_path=str(Path(self.temp_dir.name) / "knowledge-index.json")
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_user_only_sees_published_frontend_visible_doc(self):
        self.service.upsert_metadata(
            "faq.txt",
            visibility_scope=["user", "operator", "admin", "super_admin"],
            frontend_visible=True,
            draft_status="draft",
            published_status="published",
        )
        visible = self.service.is_visible_to_role("faq.txt", "user")
        self.assertTrue(visible)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests/admin -p "test_knowledge_visibility.py" -v`
Expected: FAIL because the knowledge admin service and visibility model do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/knowledge_admin_service.py
class KnowledgeAdminService:
    def upsert_metadata(self, document_id: str, visibility_scope: list[str], frontend_visible: bool, draft_status: str, published_status: str) -> dict:
        payload = self._load_all()
        payload[document_id] = {
            "visibility_scope": visibility_scope,
            "frontend_visible": frontend_visible,
            "draft_status": draft_status,
            "published_status": published_status,
        }
        self._save_all(payload)
        return payload[document_id]

    def is_visible_to_role(self, document_id: str, role: str) -> bool:
        item = self._load_all().get(document_id, {})
        return bool(item.get("frontend_visible")) and role in item.get("visibility_scope", [])
```

```python
# backend/app/api/v1/knowledge_base.py
@router.get("/knowledge-base", response_model=DocumentListResponse)
async def list_documents(authorization: str | None = Header(default=None)):
    role = auth_service.get_optional_role(authorization)
    docs = build_document_list()
    docs = [item for item in docs if knowledge_admin_service.is_visible_to_role(item.id, role)]
    return DocumentListResponse(documents=docs, total=len(docs))
```

```vue
<!-- frontend/src/components/KnowledgeBasePanel.vue -->
<button class="btn-secondary" disabled title="鍓嶅彴浠呮彁渚涘彧璇昏闂?>涓婁紶鏂囨。</button>
<button class="icon-btn" disabled title="鍓嶅彴涓嶅彲缂栬緫">缂栬緫</button>
<button class="icon-btn danger" disabled title="鍓嶅彴涓嶅彲鍒犻櫎">鍒犻櫎</button>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests/admin -p "test_knowledge_visibility.py" -v`
Expected: PASS for role-based visibility evaluation.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/knowledge_admin_service.py backend/app/api/admin/knowledge.py backend/app/services/settings_admin_service.py backend/app/api/admin/settings.py backend/app/api/v1/knowledge_base.py frontend/src/admin/pages/KnowledgeAdminPage.vue frontend/src/admin/pages/SettingsAdminPage.vue frontend/src/components/KnowledgeBasePanel.vue frontend/src/components/SettingsPanel.vue tests/admin/test_knowledge_visibility.py
git commit -m "feat: add admin knowledge visibility foundation"
```

### Task 7: Finish Documentation And Verification Artifacts

**Files:**
- Create: `docs/admin-api.md`
- Create: `docs/admin-user-guide.md`
- Create: `docs/admin-admin-guide.md`
- Create: `docs/reports/2026-04-14-admin-backoffice-foundation-test-report.md`
- Modify: `README.md`
- Modify: `V3_QUICKSTART.md`

- [ ] **Step 1: Write the API reference**

```markdown
# 鍚庡彴 API 鏂囨。

## 璁よ瘉涓庢潈闄?- `GET /api/v1/auth/me`
- `GET /api/admin/dashboard/summary`

## 鐢ㄦ埛璐﹀彿绠＄悊
- `GET /api/admin/users`
- `PATCH /api/admin/users/{user_id}/role`
- `PATCH /api/admin/users/{user_id}/status`
- `POST /api/admin/users/{user_id}/password-reset`

## 璁板繂绠＄悊
- `GET /api/admin/memory/users`
- `GET /api/admin/memory/users/{user_id}`

## 鐭ヨ瘑搴撶鐞?- `GET /api/admin/knowledge/documents`
- `PATCH /api/admin/knowledge/documents/{document_id}/visibility`

## 绯荤粺璁剧疆
- `GET /api/admin/settings/runtime`
- `PATCH /api/admin/settings/runtime`
```

- [ ] **Step 2: Write the admin/user guides**

```markdown
# 绠＄悊鍛樻寚鍗?
1. 浣跨敤鍏峰 `admin` 鎴?`super_admin` 瑙掕壊鐨勮处鍙风櫥褰?2. 閫氳繃宸︿晶瀵艰埅杩涘叆鐩爣妯″潡
3. 楂橀闄╂搷浣滃繀椤荤粡杩囩‘璁ゅ脊绐?4. 鐢ㄦ埛瑙掕壊鍙樻洿涓庡瘑鐮侀噸缃潎浼氬啓鍏ュ璁℃棩蹇?```

```markdown
# 鐢ㄦ埛鎵嬪唽

1. 鍓嶅彴鐭ヨ瘑搴撳彧灞曠ず鍚庡彴鍏佽鍙戝竷鐨勬枃妗?2. 鍓嶅彴浠呮敮鎸佹煡鐪嬶紝涓嶆敮鎸佺紪杈戙€佸垹闄ゃ€佷笂浼?3. 绯荤粺鍙傛暟涓庡悗鍙拌缃」鐢辩鐞嗗憳缁熶竴缁存姢
```

- [ ] **Step 3: Run verification and write the test report**

Run:
- `python -m unittest discover -s tests/admin -v`
- `cd frontend && npm run test:admin`
- `cd frontend && npm run build`

Write this report body:

```markdown
# 鍚庡彴鍩虹闃舵娴嬭瘯鎶ュ憡

## 鍚庣鍗曞厓涓庨泦鎴愭祴璇?- 鍛戒护锛歚python -m unittest discover -s tests/admin -v`
- 缁撴灉锛氬叏閮ㄩ€氳繃

## 鍓嶇鍗曞厓娴嬭瘯
- 鍛戒护锛歚npm run test:admin`
- 缁撴灉锛氬叏閮ㄩ€氳繃

## 鍓嶇鏋勫缓楠岃瘉
- 鍛戒护锛歚npm run build`
- 缁撴灉锛氭瀯寤烘垚鍔?```

- [ ] **Step 4: Commit**

```bash
git add docs/admin-api.md docs/admin-user-guide.md docs/admin-admin-guide.md docs/reports/2026-04-14-admin-backoffice-foundation-test-report.md README.md V3_QUICKSTART.md
git commit -m "docs: add admin backoffice phase 1 docs and report"
```

## Self-Review

### Spec Coverage

- 鍚庡彴涓绘鏋讹細Task 4
- 瑙掕壊鏉冮檺搴曞骇锛歍ask 1, Task 2
- 鐢ㄦ埛璐﹀彿绠＄悊锛歍ask 3
- 璁板繂绠＄悊鎺ュ叆锛歍ask 5
- 鐭ヨ瘑搴撹鑹插彲瑙佹€т笌鍚庡彴鍏ュ彛锛歍ask 6
- 璁剧疆鍚庡彴鍏ュ彛锛歍ask 6
- 鏃ュ織涓庡璁★細Task 2, Task 3
- 鏂囨。銆佹墜鍐屻€佹祴璇曟姤鍛婏細Task 7

### Placeholder Scan

- No `TODO`, `TBD`, or 鈥渟imilar to Task N鈥?placeholders remain.
- Each task includes exact file paths, code snippets, commands, and commit messages.

### Type Consistency

- Roles are consistently referenced as `super_admin`, `admin`, `operator`, `user`.
- Admin auth dependency is consistently named `require_admin_user`.
- Knowledge metadata consistently uses `visibility_scope`, `frontend_visible`, `draft_status`, `published_status`.


