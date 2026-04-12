"""
技能管理 API
"""
from fastapi import APIRouter, HTTPException

from app.schemas import SkillsListResponse, SkillInfo

router = APIRouter()


@router.get("/skills", response_model=SkillsListResponse)
async def list_skills():
    """获取所有技能列表"""
    from app.services.chat_service import chat_service

    skills_info = []
    for skill_name in chat_service.skill_manager.list_skills():
        skill = chat_service.skill_manager.get(skill_name)
        if skill:
            skills_info.append(SkillInfo(
                name=skill.name,
                description=skill.description,
                skill_type=skill.skill_type.value,
                enabled=True
            ))

    return SkillsListResponse(skills=skills_info, count=len(skills_info))


@router.get("/skills/{skill_name}")
async def get_skill(skill_name: str):
    """获取指定技能详情"""
    from app.services.chat_service import chat_service

    skill = chat_service.skill_manager.get(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"技能 '{skill_name}' 不存在")

    return {
        "name": skill.name,
        "description": skill.description,
        "skill_type": skill.skill_type.value,
        "enabled": True,
        "prompt": skill.get_prompt()
    }


@router.get("/skills/stats")
async def get_stats():
    """获取技能统计信息"""
    from app.services.chat_service import chat_service
    return chat_service.skill_manager.get_statistics()
