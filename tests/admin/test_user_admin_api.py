import shutil
import unittest
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.admin_main import app
from app.services.auth_service import auth_service


TEST_TMP_ROOT = Path(__file__).resolve().parents[2] / ".pytest_cache" / "user-admin-tests"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


class UserAdminApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TEST_TMP_ROOT / uuid.uuid4().hex
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        db_path = self.temp_dir / "auth.sqlite3"
        auth_service.reconfigure(database_url=f"sqlite:///{db_path.as_posix()}")
        self.client = TestClient(app)
        self.admin = auth_service.register("root.admin", "password123")
        auth_service.update_user_role(self.admin["id"], "super_admin")
        self.target = auth_service.register("managed.user", "password123")
        token = auth_service.create_token(self.admin["id"], self.admin["username"])["token"]
        self.headers = {"Authorization": f"Bearer {token}"}

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_list_users_returns_role_and_status(self):
        response = self.client.get("/api/admin/users", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        users = response.json()["users"]
        target = next(item for item in users if item["user_id"] == self.target["id"])
        self.assertEqual(target["role"], "user")
        self.assertEqual(target["status"], "active")

    def test_update_role(self):
        response = self.client.patch(
            f"/api/admin/users/{self.target['id']}/role",
            json={"role": "operator"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], "operator")
        stored = auth_service.get_user_by_id(self.target["id"])
        self.assertEqual(stored["role"], "operator")


if __name__ == "__main__":
    unittest.main()
