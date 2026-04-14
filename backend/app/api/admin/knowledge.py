from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.admin.dependencies import require_admin_user
from app.services.knowledge_admin_service import knowledge_admin_service

router = APIRouter()


class UpdateKnowledgeAccessRequest(BaseModel):
    visible_to_frontend: Optional[bool] = None
    published: Optional[bool] = None
    allowed_roles: Optional[List[str]] = None


@router.get("/knowledge/documents")
async def list_knowledge_documents(user=Depends(require_admin_user("operator", "admin", "super_admin"))):
    del user
    return {"documents": knowledge_admin_service.list_documents()}


@router.patch("/knowledge/documents/{document_id}")
async def update_knowledge_document(
    document_id: str,
    request: UpdateKnowledgeAccessRequest,
    user=Depends(require_admin_user("admin", "super_admin")),
):
    try:
        return knowledge_admin_service.update_document_access(
            document_id,
            visible_to_frontend=request.visible_to_frontend,
            published=request.published,
            allowed_roles=request.allowed_roles,
            actor_id=user["id"],
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="document not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
