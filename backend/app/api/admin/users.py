from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.admin.dependencies import require_admin_user
from app.services.user_admin_service import user_admin_service

router = APIRouter()


class UpdateUserRoleRequest(BaseModel):
    role: str = Field(..., min_length=4, max_length=32)


@router.get("/users")
async def list_users(
    q: str = "",
    role: str = "",
    status: str = "",
    user=Depends(require_admin_user("admin", "super_admin")),
):
    items = user_admin_service.list_users(query=q, role=role, status=status)
    return {
        "users": [
            {
                "user_id": item["id"],
                "username": item["username"],
                "role": item["role"],
                "status": item["status"],
                "created_at": item.get("created_at"),
            }
            for item in items
        ]
    }


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    request: UpdateUserRoleRequest,
    user=Depends(require_admin_user("super_admin")),
):
    updated = user_admin_service.update_role(user["id"], user_id, request.role)
    return {"user_id": updated["id"], "role": updated["role"]}
