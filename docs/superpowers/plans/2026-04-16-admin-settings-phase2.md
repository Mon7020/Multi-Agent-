# 后台系统设置增强 Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把后台系统设置模块从“只读摘要 + 基础参数入口”增强为正式可运营模块，支持运行参数治理、前台展示策略配置，并让前台页面消费正式策略配置。

**Architecture:** 后端继续以 `settings_admin_service` 为设置模块入口，但把前台展示策略的文件读写与默认值合并逻辑拆到独立 store。后台 API 继续挂在 `/api/admin/settings` 下，新增前台策略保存接口；用户前台复用 `/api/v1/knowledge-base/params` 返回正式的 `frontend_policy`，避免再开一条新的只读策略接口。

**Tech Stack:** FastAPI, Pydantic, unittest, Vue 3 `<script setup>`, Axios, Vitest, Vite

---

## File Structure

- Create: `backend/app/services/frontend_policy_store.py`
  - 负责默认前台展示策略、JSON 文件读写、白名单校验与默认值合并
- Modify: `backend/app/services/settings_admin_service.py`
  - 保持设置模块服务入口，接入前台策略 store，补运行参数校验、前台策略更新与审计
- Modify: `backend/app/api/admin/settings.py`
  - 新增前台策略保存接口，补 400 错误映射
- Modify: `backend/app/api/v1/knowledge_base.py`
  - 在前台只读参数接口中附带 `frontend_policy`
- Create: `tests/admin/test_settings_admin_service.py`
  - 覆盖前台策略加载、更新、非法字段、运行参数非法值与审计日志
- Modify: `tests/admin/test_settings_admin_api.py`
  - 覆盖新管理接口与 400/403 行为
- Modify: `tests/admin/test_knowledge_visibility.py`
  - 覆盖前台只读参数接口返回 `frontend_policy`
- Modify: `frontend/src/admin-api.js`
  - 增加 `settingsAdminApi.updateFrontendPolicy`
- Modify: `frontend/src/admin/pages/SettingsAdminPage.vue`
  - 升级为“运行参数 + 前台展示策略 + 权限说明”三段式设置页
- Create: `frontend/src/admin/__tests__/settings-admin-page.test.js`
  - 覆盖后台设置页加载、两个区块独立保存、错误互不污染
- Modify: `frontend/src/components/KnowledgeBasePanel.vue`
  - 消费 `frontend_policy.knowledge_base`
- Modify: `frontend/src/components/SettingsPanel.vue`
  - 消费 `frontend_policy.settings`
- Modify: `frontend/src/components/__tests__/knowledge-base-panel.test.js`
  - 覆盖知识库前台策略文案和指标显示开关
- Create: `frontend/src/components/__tests__/settings-panel.test.js`
  - 覆盖前台设置摘要策略消费
- Modify: `docs/admin-api.md`
  - 补后台设置新接口与前台只读参数响应
- Modify: `docs/admin-admin-guide.md`
  - 补后台设置模块操作说明和边界
- Modify: `README.md`
  - 更新系统设置模块能力说明
- Create: `docs/reports/2026-04-16-admin-settings-phase2-test-report.md`
  - 记录本阶段测试结果

> 以下命令默认在仓库根目录执行：`D:\agentlearn\ai-engineer-training\projects\test2langchain`

### Task 1: 实现前台展示策略存储与设置服务校验

**Files:**
- Create: `backend/app/services/frontend_policy_store.py`
- Modify: `backend/app/services/settings_admin_service.py`
- Create: `tests/admin/test_settings_admin_service.py`

- [ ] **Step 1: 写服务层失败测试**

在 `tests/admin/test_settings_admin_service.py` 写下面两组测试：

```python
import json
import shutil
import unittest
import uuid
from pathlib import Path

from app.services.settings_admin_service import SettingsAdminValidationError, settings_admin_service
from app.services.rag_runtime import rag_params_manager


TEST_TMP_ROOT = Path(__file__).resolve().parents[2] / ".pytest_cache" / "settings-admin-service-tests"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


class SettingsAdminServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TEST_TMP_ROOT / uuid.uuid4().hex
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.policy_path = self.temp_dir / "frontend_policy.json"
        self.audit_path = self.temp_dir / "admin_audit.jsonl"
        self.original_params = rag_params_manager.get_params()
        settings_admin_service.reconfigure(
            frontend_policy_path=str(self.policy_path),
            audit_storage_path=str(self.audit_path),
        )

    def tearDown(self):
        rag_params_manager.update_params(self.original_params)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_summary_uses_default_frontend_policy_when_file_missing(self):
        summary = settings_admin_service.get_summary()
        self.assertIn("frontend_policy", summary)
        self.assertTrue(summary["frontend_policy"]["knowledge_base"]["show_document_metrics"])
        self.assertTrue(summary["frontend_policy"]["settings"]["show_summary"])

    def test_update_frontend_policy_persists_policy_and_writes_audit_log(self):
        updated = settings_admin_service.update_frontend_policy(
            {
                "knowledge_base": {
                    "intro_text": "这里只展示当前角色允许访问的知识文件。",
                    "empty_state_text": "暂无可展示文件。",
                    "readonly_notice": "前台只读。",
                    "show_document_metrics": False,
                },
                "settings": {
                    "show_summary": True,
                    "show_runtime_overview": False,
                    "show_permission_notice": True,
                    "readonly_notice": "请联系管理员调整系统配置。",
                },
            },
            actor_id="admin-1",
        )

        self.assertFalse(updated["knowledge_base"]["show_document_metrics"])
        on_disk = json.loads(self.policy_path.read_text(encoding="utf-8"))
        self.assertFalse(on_disk["knowledge_base"]["show_document_metrics"])
        entries = [json.loads(line) for line in self.audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(entries[-1]["action"], "update_frontend_policy")

    def test_update_runtime_params_rejects_invalid_overlap(self):
        with self.assertRaises(SettingsAdminValidationError):
            settings_admin_service.update_runtime_params(
                {
                    "chunk_size": 300,
                    "chunk_overlap": 300,
                    "top_k": 5,
                    "similarity_threshold": 0.3,
                    "enable_cache": True,
                    "enable_rerank": True,
                    "enable_hybrid": True,
                    "enable_self_rag": False,
                }
            )

    def test_update_frontend_policy_rejects_unknown_fields(self):
        with self.assertRaises(SettingsAdminValidationError):
            settings_admin_service.update_frontend_policy(
                {
                    "knowledge_base": {
                        "intro_text": "ok",
                        "empty_state_text": "ok",
                        "readonly_notice": "ok",
                        "show_document_metrics": True,
                        "unexpected_flag": True,
                    },
                    "settings": {
                        "show_summary": True,
                        "show_runtime_overview": True,
                        "show_permission_notice": True,
                        "readonly_notice": "ok",
                    },
                }
            )
```

- [ ] **Step 2: 运行服务层测试，确认当前失败**

Run:

```bash
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_settings_admin_service -v
```

Expected:

```text
ERROR: test_get_summary_uses_default_frontend_policy_when_file_missing
AttributeError: 'SettingsAdminService' object has no attribute 'reconfigure'
```

- [ ] **Step 3: 实现前台策略 store 与服务层校验**

创建 `backend/app/services/frontend_policy_store.py`：

```python
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict


DEFAULT_FRONTEND_POLICY = {
    "knowledge_base": {
        "intro_text": "这里只展示当前账号角色允许访问且已经发布的知识文件。",
        "empty_state_text": "当前角色暂无可访问的知识文件。",
        "readonly_notice": "知识文件的编辑、发布和访问规则统一在后台维护。",
        "show_document_metrics": True,
    },
    "settings": {
        "show_summary": True,
        "show_runtime_overview": True,
        "show_permission_notice": True,
        "readonly_notice": "前台只保留系统摘要，正式配置请在后台维护。",
    },
}


class FrontendPolicyStore:
    def __init__(self, storage_path: str) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        if not self.storage_path.exists():
            return deepcopy(DEFAULT_FRONTEND_POLICY)
        raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
        return self.merge_with_defaults(raw)

    def save(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        merged = self.merge_with_defaults(policy)
        self.storage_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        return merged

    def merge_with_defaults(self, policy: Dict[str, Any] | None) -> Dict[str, Any]:
        merged = deepcopy(DEFAULT_FRONTEND_POLICY)
        if not policy:
            return merged
        for group in ("knowledge_base", "settings"):
            merged[group].update((policy.get(group) or {}))
        return merged
```

把 `backend/app/services/settings_admin_service.py` 改成下面这个结构：

```python
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from app.services.audit_log_service import AuditLogService
from app.services.frontend_policy_store import FrontendPolicyStore
from app.services.rag_runtime import get_loaded_rag_tool, rag_params_manager


class SettingsAdminValidationError(ValueError):
    pass


class SettingsAdminService:
    def __init__(self) -> None:
        self.reconfigure()

    def reconfigure(
        self,
        frontend_policy_path: Optional[str] = None,
        audit_storage_path: Optional[str] = None,
    ) -> None:
        project_root = Path(__file__).resolve().parents[3]
        self.frontend_policy_store = FrontendPolicyStore(
            frontend_policy_path or str(project_root / "data" / "settings" / "frontend_policy.json")
        )
        self.audit_log_service = AuditLogService(
            storage_path=audit_storage_path or str(project_root / "logs" / "admin_audit.jsonl")
        )

    def _validate_runtime_params(self, params: Dict[str, object]) -> None:
        if int(params["chunk_size"]) < 100:
            raise SettingsAdminValidationError("chunk_size must be >= 100")
        if int(params["chunk_overlap"]) < 0:
            raise SettingsAdminValidationError("chunk_overlap must be >= 0")
        if int(params["chunk_overlap"]) >= int(params["chunk_size"]):
            raise SettingsAdminValidationError("chunk_overlap must be smaller than chunk_size")
        if int(params["top_k"]) < 1:
            raise SettingsAdminValidationError("top_k must be >= 1")
        if not 0 <= float(params["similarity_threshold"]) <= 1:
            raise SettingsAdminValidationError("similarity_threshold must be between 0 and 1")

    def _validate_frontend_policy(self, payload: Dict[str, object]) -> Dict[str, object]:
        allowed = {
            "knowledge_base": {"intro_text", "empty_state_text", "readonly_notice", "show_document_metrics"},
            "settings": {"show_summary", "show_runtime_overview", "show_permission_notice", "readonly_notice"},
        }
        for group, allowed_fields in allowed.items():
            section = payload.get(group) or {}
            extra = set(section.keys()) - allowed_fields
            if extra:
                raise SettingsAdminValidationError(f"unsupported frontend policy fields: {sorted(extra)}")
        return self.frontend_policy_store.merge_with_defaults(payload)
```

同时补 `get_frontend_policy()`、`update_frontend_policy()`，并在 `update_runtime_params()` 开头调用 `_validate_runtime_params()`。

- [ ] **Step 4: 运行服务层测试，确认通过**

Run:

```bash
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_settings_admin_service -v
```

Expected:

```text
Ran 4 tests in 0.000s
OK
```

- [ ] **Step 5: 提交服务层改动**

```bash
git add backend/app/services/frontend_policy_store.py backend/app/services/settings_admin_service.py tests/admin/test_settings_admin_service.py
git commit -m "feat: add settings frontend policy store and validation"
```

### Task 2: 扩展后台设置 API 与 API 测试

**Files:**
- Modify: `backend/app/api/admin/settings.py`
- Modify: `tests/admin/test_settings_admin_api.py`

- [ ] **Step 1: 写 API 失败测试**

在 `tests/admin/test_settings_admin_api.py` 增加下面测试：

```python
    def test_admin_can_update_frontend_policy(self):
        response = self.client.post(
            "/api/admin/settings/frontend-policy",
            json={
                "knowledge_base": {
                    "intro_text": "只展示允许文件",
                    "empty_state_text": "暂无文件",
                    "readonly_notice": "前台只读",
                    "show_document_metrics": False,
                },
                "settings": {
                    "show_summary": True,
                    "show_runtime_overview": False,
                    "show_permission_notice": True,
                    "readonly_notice": "请联系管理员",
                },
            },
            headers=self.admin_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["policy"]["knowledge_base"]["show_document_metrics"])

    def test_invalid_runtime_settings_returns_400(self):
        response = self.client.post(
            "/api/admin/settings/runtime",
            json={**self.original_params, "chunk_size": 200, "chunk_overlap": 200},
            headers=self.admin_headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_frontend_policy_returns_400(self):
        response = self.client.post(
            "/api/admin/settings/frontend-policy",
            json={
                "knowledge_base": {
                    "intro_text": "ok",
                    "empty_state_text": "ok",
                    "readonly_notice": "ok",
                    "show_document_metrics": True,
                    "unexpected_flag": True,
                },
                "settings": {
                    "show_summary": True,
                    "show_runtime_overview": True,
                    "show_permission_notice": True,
                    "readonly_notice": "ok",
                },
            },
            headers=self.admin_headers,
        )
        self.assertEqual(response.status_code, 400)
```

- [ ] **Step 2: 运行 API 测试，确认当前失败**

Run:

```bash
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_settings_admin_api -v
```

Expected:

```text
FAIL: test_admin_can_update_frontend_policy
404 != 200
```

- [ ] **Step 3: 实现后台设置 API**

把 `backend/app/api/admin/settings.py` 改成下面结构：

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.admin.dependencies import require_admin_user
from app.services.settings_admin_service import SettingsAdminValidationError, settings_admin_service


class RuntimeSettingsRequest(BaseModel):
    chunk_size: int = Field(default=400)
    chunk_overlap: int = Field(default=50)
    top_k: int = Field(default=5)
    similarity_threshold: float = Field(default=0.3)
    enable_cache: bool = True
    enable_rerank: bool = True
    enable_hybrid: bool = True
    enable_self_rag: bool = False


class KnowledgeBasePolicyRequest(BaseModel):
    intro_text: str
    empty_state_text: str
    readonly_notice: str
    show_document_metrics: bool


class SettingsSummaryPolicyRequest(BaseModel):
    show_summary: bool
    show_runtime_overview: bool
    show_permission_notice: bool
    readonly_notice: str


class FrontendPolicyRequest(BaseModel):
    knowledge_base: KnowledgeBasePolicyRequest
    settings: SettingsSummaryPolicyRequest


def _raise_bad_request(exc: Exception) -> None:
    if isinstance(exc, SettingsAdminValidationError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise exc


@router.post("/settings/frontend-policy")
async def update_frontend_policy(
    request: FrontendPolicyRequest,
    user=Depends(require_admin_user("admin", "super_admin")),
):
    try:
        policy = settings_admin_service.update_frontend_policy(request.model_dump(), actor_id=user["id"])
    except Exception as exc:
        _raise_bad_request(exc)
    return {"success": True, "policy": policy}
```

同时在 `update_runtime_settings()` 中把 `SettingsAdminValidationError` 映射到 `400`。

- [ ] **Step 4: 运行 API 测试，确认通过**

Run:

```bash
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_settings_admin_api -v
```

Expected:

```text
Ran 6 tests in 0.000s
OK
```

- [ ] **Step 5: 提交 API 改动**

```bash
git add backend/app/api/admin/settings.py tests/admin/test_settings_admin_api.py
git commit -m "feat: add admin settings frontend policy api"
```

### Task 3: 重构后台设置页并补后台前端测试

**Files:**
- Modify: `frontend/src/admin-api.js`
- Modify: `frontend/src/admin/pages/SettingsAdminPage.vue`
- Create: `frontend/src/admin/__tests__/settings-admin-page.test.js`

- [ ] **Step 1: 写后台设置页失败测试**

创建 `frontend/src/admin/__tests__/settings-admin-page.test.js`：

```javascript
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import SettingsAdminPage from '../pages/SettingsAdminPage.vue'
import { settingsAdminApi } from '../../admin-api.js'

vi.mock('../../admin-api.js', () => ({
  settingsAdminApi: {
    getSummary: vi.fn(),
    updateRuntime: vi.fn(),
    updateFrontendPolicy: vi.fn()
  }
}))

describe('SettingsAdminPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    settingsAdminApi.getSummary.mockResolvedValue({
      data: {
        runtime_params: {
          chunk_size: 400,
          chunk_overlap: 50,
          top_k: 5,
          similarity_threshold: 0.3,
          enable_cache: true,
          enable_rerank: true,
          enable_hybrid: true,
          enable_self_rag: false
        },
        frontend_policy: {
          knowledge_base: {
            intro_text: '只展示允许文件',
            empty_state_text: '暂无文件',
            readonly_notice: '前台只读',
            show_document_metrics: true
          },
          settings: {
            show_summary: true,
            show_runtime_overview: true,
            show_permission_notice: true,
            readonly_notice: '请联系管理员'
          }
        },
        permission_model: {
          roles: {
            admin: { label: '管理员', capabilities: ['系统设置'] }
          }
        }
      }
    })
  })

  it('loads runtime params and frontend policy sections', async () => {
    const wrapper = mount(SettingsAdminPage)
    await flushPromises()

    expect(settingsAdminApi.getSummary).toHaveBeenCalledTimes(1)
    expect(wrapper.find('[data-testid="frontend-policy-form"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="runtime-form"]').exists()).toBe(true)
  })

  it('saves frontend policy without touching runtime api', async () => {
    settingsAdminApi.updateFrontendPolicy.mockResolvedValue({
      data: {
        policy: {
          knowledge_base: {
            intro_text: '只展示允许文件',
            empty_state_text: '暂无文件',
            readonly_notice: '前台只读',
            show_document_metrics: false
          },
          settings: {
            show_summary: true,
            show_runtime_overview: false,
            show_permission_notice: true,
            readonly_notice: '请联系管理员'
          }
        }
      }
    })

    const wrapper = mount(SettingsAdminPage)
    await flushPromises()

    await wrapper.get('[data-testid="policy-show-runtime-overview"]').setValue(false)
    await wrapper.get('[data-testid="policy-show-document-metrics"]').setValue(false)
    await wrapper.get('[data-testid="save-frontend-policy-btn"]').trigger('click')
    await flushPromises()

    expect(settingsAdminApi.updateFrontendPolicy).toHaveBeenCalledTimes(1)
    expect(settingsAdminApi.updateRuntime).not.toHaveBeenCalled()
  })

  it('keeps runtime and policy error states isolated', async () => {
    settingsAdminApi.updateRuntime.mockRejectedValueOnce(new Error('runtime failed'))
    settingsAdminApi.updateFrontendPolicy.mockResolvedValue({
      data: {
        policy: {
          knowledge_base: {
            intro_text: '只展示允许文件',
            empty_state_text: '暂无文件',
            readonly_notice: '前台只读',
            show_document_metrics: true
          },
          settings: {
            show_summary: true,
            show_runtime_overview: true,
            show_permission_notice: true,
            readonly_notice: '请联系管理员'
          }
        }
      }
    })

    const wrapper = mount(SettingsAdminPage)
    await flushPromises()

    await wrapper.get('[data-testid="save-runtime-btn"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="runtime-error"]').text()).toContain('runtime failed')

    await wrapper.get('[data-testid="save-frontend-policy-btn"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="frontend-policy-error"]').exists()).toBe(false)
  })
})
```

- [ ] **Step 2: 运行后台设置页测试，确认当前失败**

Run in `frontend`:

```bash
npm run test:admin -- src/admin/__tests__/settings-admin-page.test.js
```

Expected:

```text
FAIL  src/admin/__tests__/settings-admin-page.test.js
TypeError: settingsAdminApi.updateFrontendPolicy is not a function
```

- [ ] **Step 3: 实现后台设置页**

先在 `frontend/src/admin-api.js` 追加客户端方法：

```javascript
export const settingsAdminApi = {
  getSummary() {
    return adminApi.get('/settings/summary')
  },

  updateRuntime(payload) {
    return adminApi.post('/settings/runtime', payload)
  },

  updateFrontendPolicy(payload) {
    return adminApi.post('/settings/frontend-policy', payload)
  }
}
```

再把 `frontend/src/admin/pages/SettingsAdminPage.vue` 重构成双表单结构，至少包含下面这些状态：

```javascript
const runtimeParams = ref({
  chunk_size: 400,
  chunk_overlap: 50,
  top_k: 5,
  similarity_threshold: 0.3,
  enable_cache: true,
  enable_rerank: true,
  enable_hybrid: true,
  enable_self_rag: false
})
const frontendPolicy = ref({
  knowledge_base: {
    intro_text: '',
    empty_state_text: '',
    readonly_notice: '',
    show_document_metrics: true
  },
  settings: {
    show_summary: true,
    show_runtime_overview: true,
    show_permission_notice: true,
    readonly_notice: ''
  }
})

const runtimeErrorMessage = ref('')
const frontendPolicyErrorMessage = ref('')
const runtimeSuccessMessage = ref('')
const frontendPolicySuccessMessage = ref('')
const savingRuntime = ref(false)
const savingFrontendPolicy = ref(false)
```

并补两个独立保存函数：

```javascript
async function saveRuntime() {
  savingRuntime.value = true
  runtimeErrorMessage.value = ''
  runtimeSuccessMessage.value = ''
  try {
    const response = await settingsAdminApi.updateRuntime(runtimeParams.value)
    runtimeParams.value = {
      chunk_size: response.data.params.chunk_size,
      chunk_overlap: response.data.params.chunk_overlap,
      top_k: response.data.params.top_k,
      similarity_threshold: response.data.params.similarity_threshold,
      enable_cache: response.data.params.enable_cache,
      enable_rerank: response.data.params.enable_rerank,
      enable_hybrid: response.data.params.enable_hybrid,
      enable_self_rag: response.data.params.enable_self_rag
    }
    runtimeSuccessMessage.value = '运行参数已保存'
  } catch (error) {
    runtimeErrorMessage.value = error.response?.data?.detail || error.message || '保存运行参数失败'
  } finally {
    savingRuntime.value = false
  }
}

async function saveFrontendPolicy() {
  savingFrontendPolicy.value = true
  frontendPolicyErrorMessage.value = ''
  frontendPolicySuccessMessage.value = ''
  try {
    const response = await settingsAdminApi.updateFrontendPolicy(frontendPolicy.value)
    frontendPolicy.value = response.data.policy
    frontendPolicySuccessMessage.value = '前台展示策略已保存'
  } catch (error) {
    frontendPolicyErrorMessage.value = error.response?.data?.detail || error.message || '保存前台展示策略失败'
  } finally {
    savingFrontendPolicy.value = false
  }
}
```

模板中加入这些 `data-testid`：

```html
<form data-testid="runtime-form">
  <input data-testid="runtime-chunk-size" type="number" v-model.number="runtimeParams.chunk_size" />
  <input data-testid="runtime-chunk-overlap" type="number" v-model.number="runtimeParams.chunk_overlap" />
  <input data-testid="runtime-top-k" type="number" v-model.number="runtimeParams.top_k" />
</form>
<button data-testid="save-runtime-btn">保存运行参数</button>
<p v-if="runtimeErrorMessage" data-testid="runtime-error">{{ runtimeErrorMessage }}</p>

<form data-testid="frontend-policy-form">
  <textarea data-testid="policy-intro-text" v-model="frontendPolicy.knowledge_base.intro_text"></textarea>
  <textarea data-testid="policy-empty-state-text" v-model="frontendPolicy.knowledge_base.empty_state_text"></textarea>
</form>
<input data-testid="policy-show-document-metrics" type="checkbox" v-model="frontendPolicy.knowledge_base.show_document_metrics" />
<input data-testid="policy-show-runtime-overview" type="checkbox" v-model="frontendPolicy.settings.show_runtime_overview" />
<button data-testid="save-frontend-policy-btn">保存前台策略</button>
<p v-if="frontendPolicyErrorMessage" data-testid="frontend-policy-error">{{ frontendPolicyErrorMessage }}</p>
```

- [ ] **Step 4: 运行后台设置页测试，确认通过**

Run in `frontend`:

```bash
npm run test:admin -- src/admin/__tests__/settings-admin-page.test.js
```

Expected:

```text
Test Files  1 passed
Tests       3 passed
```

- [ ] **Step 5: 提交后台设置页改动**

```bash
git add frontend/src/admin-api.js frontend/src/admin/pages/SettingsAdminPage.vue frontend/src/admin/__tests__/settings-admin-page.test.js
git commit -m "feat: add admin settings policy management ui"
```

### Task 4: 让用户前台消费正式展示策略

**Files:**
- Modify: `backend/app/api/v1/knowledge_base.py`
- Modify: `tests/admin/test_knowledge_visibility.py`
- Modify: `frontend/src/components/KnowledgeBasePanel.vue`
- Modify: `frontend/src/components/SettingsPanel.vue`
- Modify: `frontend/src/components/__tests__/knowledge-base-panel.test.js`
- Create: `frontend/src/components/__tests__/settings-panel.test.js`

- [ ] **Step 1: 写前台策略失败测试**

先在 `tests/admin/test_knowledge_visibility.py` 追加下面测试：

```python
    def test_frontend_params_response_includes_frontend_policy(self):
        response = self.user_client.get("/api/v1/knowledge-base/params", headers=self.user_headers)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("frontend_policy", payload)
        self.assertIn("knowledge_base", payload["frontend_policy"])
        self.assertIn("settings", payload["frontend_policy"])
```

再修改 `frontend/src/components/__tests__/knowledge-base-panel.test.js`：

```javascript
vi.mock('../../api/index.js', () => ({
  knowledgeBaseApi: {
    getDocuments: vi.fn(),
    getDocument: vi.fn(),
    getParams: vi.fn()
  }
}))

    knowledgeBaseApi.getParams.mockResolvedValue({
      data: {
        params: {},
        cache_stats: {},
        metrics: {},
        frontend_policy: {
          knowledge_base: {
            intro_text: '只展示允许文件',
            empty_state_text: '暂无文件',
            readonly_notice: '前台只读',
            show_document_metrics: false
          },
          settings: {
            show_summary: true,
            show_runtime_overview: true,
            show_permission_notice: true,
            readonly_notice: '请联系管理员'
          }
        }
      }
    })

    expect(wrapper.text()).toContain('只展示允许文件')
    expect(wrapper.text()).not.toContain('文件类型')
```

创建 `frontend/src/components/__tests__/settings-panel.test.js`：

```javascript
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import SettingsPanel from '../SettingsPanel.vue'
import { authApi, healthApi, knowledgeBaseApi } from '../../api/index.js'

vi.mock('../../api/index.js', () => ({
  authApi: { me: vi.fn() },
  healthApi: { check: vi.fn() },
  knowledgeBaseApi: { getParams: vi.fn() },
  clearAuthSession: vi.fn(),
  getAuthToken: vi.fn(),
  getAuthUser: vi.fn(() => ({ user_id: 'u1', username: 'demo', role: 'user', status: 'active' })),
  setAuthSession: vi.fn(),
  updateAuthUser: vi.fn((value) => value)
}))

describe('SettingsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    authApi.me.mockResolvedValue({ data: { user_id: 'u1', username: 'demo', role: 'user', status: 'active' } })
    healthApi.check.mockResolvedValue({ data: { status: 'ok', version: 'test' } })
    knowledgeBaseApi.getParams.mockResolvedValue({
      data: {
        params: { chunk_size: 400, top_k: 5 },
        cache_stats: {},
        metrics: {},
        frontend_policy: {
          knowledge_base: {
            intro_text: '只展示允许文件',
            empty_state_text: '暂无文件',
            readonly_notice: '前台只读',
            show_document_metrics: true
          },
          settings: {
            show_summary: true,
            show_runtime_overview: false,
            show_permission_notice: false,
            readonly_notice: '设置只读展示'
          }
        }
      }
    })
  })

  it('uses frontend policy to hide runtime overview and show readonly notice', async () => {
    const wrapper = mount(SettingsPanel)
    await flushPromises()

    expect(wrapper.text()).toContain('设置只读展示')
    expect(wrapper.text()).not.toContain('分块大小')
  })
})
```

- [ ] **Step 2: 运行前台与公共接口测试，确认当前失败**

Run backend:

```bash
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_visibility -v
```

Expected:

```text
FAIL: test_frontend_params_response_includes_frontend_policy
AssertionError: 'frontend_policy' not found in response payload
```

Run frontend in `frontend`:

```bash
npm run test:admin -- src/components/__tests__/knowledge-base-panel.test.js src/components/__tests__/settings-panel.test.js
```

Expected:

```text
FAIL  src/components/__tests__/knowledge-base-panel.test.js
TypeError: knowledgeBaseApi.getParams is not a function
```

- [ ] **Step 3: 实现前台策略消费**

在 `backend/app/api/v1/knowledge_base.py` 里扩展响应模型和返回值：

```python
class RAGParamsResponse(BaseModel):
    params: RAGParams
    cache_stats: dict
    metrics: dict
    frontend_policy: dict


@router.get("/knowledge-base/params", response_model=RAGParamsResponse)
async def get_rag_params(current_user=Depends(require_authenticated_user())):
    del current_user
    runtime_params = rag_params_manager.get_params()
    frontend_policy = settings_admin_service.get_frontend_policy()
    params = RAGParams(
        chunk_size=runtime_params["chunk_size"],
        chunk_overlap=runtime_params["chunk_overlap"],
        top_k=runtime_params["top_k"],
        similarity_threshold=runtime_params["similarity_threshold"],
        enable_cache=runtime_params["enable_cache"],
        enable_rerank=runtime_params["enable_rerank"],
        enable_hybrid=runtime_params.get("enable_hybrid", True),
        enable_self_rag=runtime_params["enable_self_rag"],
    )
    return RAGParamsResponse(
        params=params,
        cache_stats=cache_stats,
        metrics=metrics,
        frontend_policy=frontend_policy,
    )
```

把 `frontend/src/components/KnowledgeBasePanel.vue` 改成并行读取文档与前台策略：

```javascript
const knowledgePolicy = ref({
  intro_text: '这里只展示当前账号角色允许访问且已经发布的知识文件。',
  empty_state_text: '当前角色暂无可访问的知识文件。',
  readonly_notice: '知识文件的编辑、发布和访问规则统一在后台维护。',
  show_document_metrics: true
})

async function loadDocuments() {
  loading.value = true
  clearError()
  try {
    const [documentsResponse, paramsResponse] = await Promise.all([
      knowledgeBaseApi.getDocuments(),
      knowledgeBaseApi.getParams()
    ])
    documents.value = documentsResponse.data.documents || []
    knowledgePolicy.value = paramsResponse.data.frontend_policy?.knowledge_base || knowledgePolicy.value
    if (documents.value.length > 0) {
      const stillSelected = documents.value.find((doc) => doc.id === selectedDoc.value?.id)
      await selectDocument(stillSelected || documents.value[0])
    } else {
      selectedDoc.value = null
      selectedContent.value = ''
    }
  } catch (error) {
    setError(error.response?.data?.detail || error.message || '加载知识文件失败')
  } finally {
    loading.value = false
  }
}
```

模板里把静态文案替换为：

```html
<h3>前台只读知识库</h3>
<p>{{ knowledgePolicy.intro_text }}</p>
<p class="readonly-note">{{ knowledgePolicy.readonly_notice }}</p>
<div v-else-if="documents.length === 0" class="empty-inline">{{ knowledgePolicy.empty_state_text }}</div>
<div v-if="selectedDoc && knowledgePolicy.show_document_metrics" class="metric-strip">
  <span class="metric-pill">文件类型：{{ selectedDoc.file_type }}</span>
  <span class="metric-pill">分块数量：{{ selectedDoc.chunk_count || 0 }}</span>
  <span class="metric-pill">文档 ID：{{ selectedDoc.id }}</span>
</div>
```

把 `frontend/src/components/SettingsPanel.vue` 改成消费 `frontend_policy.settings`：

```javascript
const settingsPolicy = ref({
  show_summary: true,
  show_runtime_overview: true,
  show_permission_notice: true,
  readonly_notice: '前台只保留系统摘要，正式配置请在后台维护。'
})

async function loadSummary() {
  const [meResponse, paramsResponse, healthResponse] = await Promise.all([
    authApi.me(),
    knowledgeBaseApi.getParams(),
    healthApi.check()
  ])
  currentUser.value = updateAuthUser(meResponse.data)
  runtimeParams.value = paramsResponse.data.params || {}
  settingsPolicy.value = paramsResponse.data.frontend_policy?.settings || settingsPolicy.value
  backendHealth.value = healthResponse.data.status || 'unknown'
  backendVersion.value = healthResponse.data.version || 'N/A'
  settingsPolicy.value = paramsResponse.data.frontend_policy?.settings || settingsPolicy.value
}
```

并用策略控制模板：

```html
<article v-if="settingsPolicy.show_summary" class="panel">
  <header>
    <p class="label">账号状态</p>
    <h4>{{ currentUser?.username || '未登录' }}</h4>
  </header>
</article>

<article v-if="settingsPolicy.show_runtime_overview" class="panel">
  <header>
    <p class="label">运行参数</p>
    <h4>只读查看当前配置</h4>
  </header>
</article>

<article v-if="settingsPolicy.show_permission_notice" class="panel full">
  <header>
    <p class="label">使用说明</p>
    <h4>后台接管的能力</h4>
  </header>
</article>

<p class="readonly-notice">{{ settingsPolicy.readonly_notice }}</p>
```

- [ ] **Step 4: 运行前台与公共接口测试，确认通过**

Run backend:

```bash
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_visibility -v
```

Expected:

```text
Ran 6 tests in 0.000s
OK
```

Run frontend in `frontend`:

```bash
npm run test:admin -- src/components/__tests__/knowledge-base-panel.test.js src/components/__tests__/settings-panel.test.js
```

Expected:

```text
Test Files  2 passed
Tests       2 passed
```

- [ ] **Step 5: 提交前台策略消费改动**

```bash
git add backend/app/api/v1/knowledge_base.py tests/admin/test_knowledge_visibility.py frontend/src/components/KnowledgeBasePanel.vue frontend/src/components/SettingsPanel.vue frontend/src/components/__tests__/knowledge-base-panel.test.js frontend/src/components/__tests__/settings-panel.test.js
git commit -m "feat: apply frontend settings policy to user panels"
```

### Task 5: 更新文档并执行全量回归

**Files:**
- Modify: `docs/admin-api.md`
- Modify: `docs/admin-admin-guide.md`
- Modify: `README.md`
- Create: `docs/reports/2026-04-16-admin-settings-phase2-test-report.md`

- [ ] **Step 1: 更新文档**

把 `docs/admin-api.md` 补成至少包含以下内容：

```md
### `POST /api/admin/settings/frontend-policy`

权限：

- `admin`
- `super_admin`

说明：

- 更新系统级前台展示策略
- 不修改知识库单文件访问规则
- 不修改用户个人偏好
```

把 `docs/admin-admin-guide.md` 的“系统设置”章节补成至少包含：

```md
- 系统设置只维护运行参数和前台展示策略
- 用户个人偏好仍在记忆管理中维护
- 知识库访问规则仍在知识库模块中维护
- 前台知识库始终只读
```

把 `README.md` 的后台模块说明更新为：

```md
- 系统设置：运行参数治理、前台展示策略、权限模型只读说明
```

再创建 `docs/reports/2026-04-16-admin-settings-phase2-test-report.md`，记录本阶段：

```md
# 2026-04-16 后台系统设置 Phase 2 测试报告

- 后台设置服务层校验
- 后台设置 API
- 后台设置页交互
- 前台知识库与前台设置摘要的策略消费
- 构建验证
```

- [ ] **Step 2: 运行后端设置相关回归**

Run:

```bash
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_settings_admin_service tests.admin.test_settings_admin_api tests.admin.test_knowledge_visibility -v
```

Expected:

```text
Ran 13 tests in 0.000s
OK
```

- [ ] **Step 3: 运行前端相关回归**

Run in `frontend`:

```bash
npm run test:admin -- src/admin/__tests__/settings-admin-page.test.js src/admin/__tests__/knowledge-admin-page.test.js src/admin/__tests__/admin-nav.test.js src/admin/__tests__/admin-shell.test.js src/components/__tests__/knowledge-base-panel.test.js src/components/__tests__/settings-panel.test.js
```

Expected:

```text
Test Files  6 passed
Tests       28 passed
```

- [ ] **Step 4: 运行前端构建**

Run in `frontend`:

```bash
npm run build
```

Expected:

```text
✓ built in 1.50s
```

- [ ] **Step 5: 提交文档与测试报告**

```bash
git add docs/admin-api.md docs/admin-admin-guide.md README.md docs/reports/2026-04-16-admin-settings-phase2-test-report.md
git commit -m "docs: add admin settings phase2 report and guides"
```

## Self-Review

### Spec coverage

- 运行参数治理：Task 1、Task 2、Task 3
- 前台展示策略正式配置：Task 1、Task 2
- 后台设置页三段式结构：Task 3
- 前台消费正式策略：Task 4
- 文档与回归：Task 5

没有遗漏 spec 中的核心要求。

### Placeholder scan

- 未使用 `TODO`、`TBD`、`implement later`
- 每个任务都给了文件路径、测试代码、命令和提交点

### Type consistency

- 服务层异常名统一为 `SettingsAdminValidationError`
- 前台策略 API 客户端统一为 `settingsAdminApi.updateFrontendPolicy`
- 前台策略字段统一使用：
  - `knowledge_base.intro_text`
  - `knowledge_base.empty_state_text`
  - `knowledge_base.readonly_notice`
  - `knowledge_base.show_document_metrics`
  - `settings.show_summary`
  - `settings.show_runtime_overview`
  - `settings.show_permission_notice`
  - `settings.readonly_notice`
