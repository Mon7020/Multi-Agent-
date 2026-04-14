from __future__ import annotations

from app.services.audit_log_service import audit_log_service
from app.services.auth_service import auth_service


class UserAdminService:
    def list_users(self, query: str = "", role: str = "", status: str = "") -> list[dict]:
        users = auth_service.list_users()
        if query:
            lowered = query.lower()
            users = [
                item
                for item in users
                if lowered in (item.get("username") or "").lower() or lowered in (item.get("id") or "").lower()
            ]
        if role:
            users = [item for item in users if item.get("role") == role]
        if status:
            users = [item for item in users if item.get("status") == status]
        return users

    def update_role(self, actor_id: str, user_id: str, role: str) -> dict:
        updated = auth_service.update_user_role(user_id, role)
        audit_log_service.write(
            actor_id=actor_id,
            module="users",
            action="update_role",
            target_type="user",
            target_id=user_id,
            result="success",
            extra={"role": role},
        )
        return updated


user_admin_service = UserAdminService()
