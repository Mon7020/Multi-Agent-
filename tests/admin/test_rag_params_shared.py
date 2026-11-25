import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.services.rag_runtime import rag_params_manager
from app.services.settings_admin_service import SettingsAdminValidationError, SettingsAdminService


def test_settings_are_visible_in_another_process_and_invalid_update_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv('RAG_PARAMS_DB', str(tmp_path / 'params.sqlite3'))
    initial = rag_params_manager.get_params()
    updated = {**initial, 'top_k': 7, 'enable_self_rag': True}
    service = SettingsAdminService()
    service.update_runtime_params(updated)
    version = rag_params_manager.get_version()
    with pytest.raises(SettingsAdminValidationError):
        service.update_runtime_params({**updated, 'top_k': 0})
    assert rag_params_manager.get_version() == version

    root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join((str(root / 'backend'), str(root)))
    output = subprocess.check_output(
        [sys.executable, '-c', 'import json; from app.services.rag_runtime import rag_params_manager as m; print(json.dumps([m.get_params(), m.get_version()]))'],
        cwd=str(root), env=env, text=True,
    )
    params, child_version = json.loads(output.strip().splitlines()[-1])
    assert params['top_k'] == 7
    assert params['enable_self_rag'] is True
    assert child_version == version


@pytest.mark.asyncio
async def test_retrieval_uses_shared_settings(tmp_path, monkeypatch):
    from app.services.chat_service_v3 import ChatServiceV3

    monkeypatch.setenv('RAG_PARAMS_DB', str(tmp_path / 'params.sqlite3'))
    rag_params_manager.update_params({'top_k': 7, 'enable_self_rag': False})
    calls = []

    class Rag:
        def retrieve(self, **kwargs):
            calls.append(kwargs)
            return {'success': True, 'documents': []}

    service = ChatServiceV3.__new__(ChatServiceV3)
    service.rag_tool = Rag()
    service.llm = None
    from types import SimpleNamespace
    monkeypatch.setattr(service, '_build_rag_chat_history', lambda context: [], raising=False)
    await service._retrieve_with_rag('question', SimpleNamespace(turn_history=[]), {'user_role': 'user'}, 'trace')
    assert calls[0]['top_k'] == 7
    assert calls[0]['enable_self_rag'] is False
