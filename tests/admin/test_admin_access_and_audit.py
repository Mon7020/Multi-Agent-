import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import fakeredis
from fastapi.testclient import TestClient

from app.admin_main import app
from app.services.audit_log_service import AuditLogService
from app.services.auth_service import auth_service
from app.services.task_queue_service import TaskQueueService


TEST_TMP_ROOT = Path(__file__).resolve().parents[2] / ".pytest_cache" / "admin-access-tests"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


class AdminAccessAuditTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TEST_TMP_ROOT / uuid.uuid4().hex
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        db_path = self.temp_dir / "auth.sqlite3"
        auth_service.reconfigure(database_url=f"sqlite:///{db_path.as_posix()}")
        self.task_queue = TaskQueueService(
            redis_connection=fakeredis.FakeRedis(),
            queue_name=f"admin-access-{uuid.uuid4().hex}",
        )
        self.task_api_patcher = patch("app.api.admin.tasks.task_queue_service", self.task_queue)
        self.task_api_patcher.start()
        self.client = TestClient(app)
        self.user = auth_service.register("plain.user", "password123")
        self.admin = auth_service.register("admin.user", "password123")
        auth_service.update_user_role(self.admin["id"], "admin")
        self.user_headers = {
            "Authorization": f"Bearer {auth_service.create_token(self.user['id'], self.user['username'])['token']}"
        }
        self.admin_headers = {
            "Authorization": f"Bearer {auth_service.create_token(self.admin['id'], self.admin['username'])['token']}"
        }

    def tearDown(self):
        self.task_api_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_plain_user_cannot_open_admin_dashboard(self):
        response = self.client.get("/api/admin/dashboard/summary", headers=self.user_headers)
        self.assertEqual(response.status_code, 403)

    def test_admin_can_open_admin_dashboard(self):
        response = self.client.get("/api/admin/dashboard/summary", headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["current_user"]["role"], "admin")

    def test_admin_can_read_task_status(self):
        task = self.task_queue.enqueue(
            task_type="knowledge_reload",
            payload={},
            actor_id=self.admin["id"],
            idempotency_key=f"test-admin-task-status:{uuid.uuid4().hex}",
        )

        response = self.client.get(f"/api/admin/tasks/{task['task_id']}", headers=self.admin_headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["task_id"], task["task_id"])
        self.assertEqual(response.json()["status"], "queued")
        self.task_queue.claim_next()
        running = self.client.get(f"/api/admin/tasks/{task['task_id']}", headers=self.admin_headers)
        self.assertEqual(running.json()["status"], "running")
        self.assertNotIn("lease_token", running.json())

    def test_audit_log_service_appends_entries(self):
        log_path = self.temp_dir / "audit-log.jsonl"
        service = AuditLogService(storage_path=str(log_path))

        service.write(
            actor_id=self.admin["id"],
            module="dashboard",
            action="view",
            target_type="summary",
            target_id="root",
            result="success",
        )

        entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["module"], "dashboard")
        self.assertEqual(entries[0]["result"], "success")

    def test_retry_returns_conflict_when_another_reload_is_active(self):
        request = dict(task_type="knowledge_reload", payload={}, idempotency_key="knowledge_reload:latest", max_attempts=1)
        failed = self.task_queue.enqueue(**request)
        claimed = self.task_queue.claim_next()
        self.task_queue.fail(failed["task_id"], "unavailable", lease_token=claimed["lease_token"])
        active = self.task_queue.enqueue(**request)
        response = self.client.post(f"/api/admin/tasks/{failed['task_id']}/retry", headers=self.admin_headers)
        self.assertEqual(response.status_code, 409)
        self.assertIn(active["task_id"], response.json()["detail"])
        self.assertEqual(self.task_queue.rq_queue.job_ids, [active["task_id"]])


if __name__ == "__main__":
    unittest.main()
