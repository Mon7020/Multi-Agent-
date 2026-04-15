from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.admin.dependencies import require_admin_user
from app.services.settings_admin_service import settings_admin_service

router = APIRouter()


class RuntimeSettingsRequest(BaseModel):
    chunk_size: int = 400
    chunk_overlap: int = 50
    top_k: int = 5
    similarity_threshold: float = 0.3
    enable_cache: bool = True
    enable_rerank: bool = True
    enable_hybrid: bool = True
    enable_self_rag: bool = False


@router.get("/settings/summary")
async def get_settings_summary(user=Depends(require_admin_user("admin", "super_admin"))):
    del user
    return settings_admin_service.get_summary()


@router.post("/settings/runtime")
async def update_runtime_settings(
    request: RuntimeSettingsRequest,
    user=Depends(require_admin_user("admin", "super_admin")),
):
    params = settings_admin_service.update_runtime_params(request.model_dump(), actor_id=user["id"])
    return {"success": True, "params": params}
