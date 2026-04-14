import shutil
import unittest
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_main import app as admin_app
from app.api.v1 import auth, knowledge_base
from app.services.auth_service import auth_service
from app.services.knowledge_admin_service import knowledge_admin_service


TEST_TMP_ROOT = Path(__file__).resolve().parents[2] / ".pytest_cache" / "knowledge-admin-tests"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
user_app = FastAPI()
user_app.include_router(auth.router, prefix="/api/v1")
user_app.include_router(knowledge_base.router, prefix="/api/v1")


class KnowledgeVisibilityTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TEST_TMP_ROOT / uuid.uuid4().hex
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir = self.temp_dir / "docs"
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path = self.temp_dir / "knowledge-registry.json"

        db_path = self.temp_dir / "auth.sqlite3"
        auth_service.reconfigure(database_url=f"sqlite:///{db_path.as_posix()}")
        knowledge_admin_service.reconfigure(docs_dir=str(self.docs_dir), metadata_path=str(self.metadata_path))

        self.admin_client = TestClient(admin_app)
        self.user_client = TestClient(user_app)
        self.admin = auth_service.register("knowledge.admin", "password123")
        auth_service.update_user_role(self.admin["id"], "admin")
        self.operator = auth_service.register("knowledge.operator", "password123")
        auth_service.update_user_role(self.operator["id"], "operator")
        self.user = auth_service.register("knowledge.user", "password123")

        self.admin_headers = {
            "Authorization": f"Bearer {auth_service.create_token(self.admin['id'], self.admin['username'])['token']}"
        }
        self.operator_headers = {
            "Authorization": f"Bearer {auth_service.create_token(self.operator['id'], self.operator['username'])['token']}"
        }
        self.user_headers = {
            "Authorization": f"Bearer {auth_service.create_token(self.user['id'], self.user['username'])['token']}"
        }

        (self.docs_dir / "alpha.txt").write_text("alpha", encoding="utf-8")
        (self.docs_dir / "operator.txt").write_text("operator", encoding="utf-8")
        (self.docs_dir / "hidden.txt").write_text("hidden", encoding="utf-8")

        knowledge_admin_service.update_document_access(
            "alpha.txt",
            visible_to_frontend=True,
            published=True,
            allowed_roles=["user", "operator", "admin", "super_admin"],
        )
        knowledge_admin_service.update_document_access(
            "operator.txt",
            visible_to_frontend=True,
            published=True,
            allowed_roles=["operator", "admin", "super_admin"],
        )
        knowledge_admin_service.update_document_access(
            "hidden.txt",
            visible_to_frontend=False,
            published=True,
            allowed_roles=["user", "operator", "admin", "super_admin"],
        )

    def tearDown(self):
        knowledge_admin_service.reconfigure()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_frontend_user_only_sees_role_allowed_published_documents(self):
        user_response = self.user_client.get("/api/v1/knowledge-base", headers=self.user_headers)
        operator_response = self.user_client.get("/api/v1/knowledge-base", headers=self.operator_headers)

        self.assertEqual(user_response.status_code, 200)
        self.assertEqual(operator_response.status_code, 200)
        self.assertEqual([doc["filename"] for doc in user_response.json()["documents"]], ["alpha.txt"])
        self.assertEqual(
            [doc["filename"] for doc in operator_response.json()["documents"]],
            ["alpha.txt", "operator.txt"],
        )

    def test_admin_can_hide_document_from_frontend(self):
        response = self.admin_client.patch(
            "/api/admin/knowledge/documents/alpha.txt",
            json={"visible_to_frontend": False},
            headers=self.admin_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["visible_to_frontend"], False)

        user_response = self.user_client.get("/api/v1/knowledge-base", headers=self.user_headers)
        self.assertEqual([doc["filename"] for doc in user_response.json()["documents"]], [])

    def test_operator_cannot_update_document_visibility(self):
        response = self.admin_client.patch(
            "/api/admin/knowledge/documents/alpha.txt",
            json={"published": False},
            headers=self.operator_headers,
        )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
