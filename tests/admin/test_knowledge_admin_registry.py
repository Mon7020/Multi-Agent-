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
