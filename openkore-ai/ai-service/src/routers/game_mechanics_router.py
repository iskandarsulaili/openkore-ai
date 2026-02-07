"""
Game Mechanics Router for OpenKore AI Service.

Provides API endpoints for status effects and skill tree intelligence
extracted from rathena-AI-world.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from game_mechanics import (
    StatusEffectHandler,
    StatusChange,
    SkillTreeDatabase
)

# Create router
router = APIRouter(prefix="/api/v1/game_mechanics", tags=["game_mechanics"])

# Initialize game mechanics systems
status_handler = StatusEffectHandler()
skill_tree_db = SkillTreeDatabase()


# ================================================================
# REQUEST/RESPONSE MODELS
# ================================================================

class StatusUpdateRequest(BaseModel):
    """Request to update character status effects."""
    char_id: int = Field(..., description="Character ID")
    status_effects: List[int] = Field(..., description="List of active status effect IDs")


class StatusQueryRequest(BaseModel):
    """Request to query character status."""
    char_id: int = Field(..., description="Character ID")
    job: Optional[str] = Field(None, description="Character job class")


class SkillPathRequest(BaseModel):
    """Request for skill learning path."""
    job: str = Field(..., description="Job class name")
    current_skills: Dict[str, int] = Field(..., description="Current skills and levels")
    base_level: int = Field(..., description="Character base level")
    job_level: int = Field(..., description="Character job level")
    target_skill: Optional[str] = Field(None, description="Target skill to learn")


# ================================================================
# STATUS EFFECT ENDPOINTS
# ================================================================

@router.post("/status/update")
async def update_status(request: StatusUpdateRequest):
    """
    Update character's active status effects.
    
    The AI service will analyze these statuses to make intelligent decisions
    about what actions the character can perform.
    """
    try:
        status_handler.update_status(request.char_id, request.status_effects)
        
        # Get comprehensive status analysis
        summary = status_handler.get_status_summary(request.char_id)
        
        return {
            "success": True,
            "char_id": request.char_id,
            "status_count": len(request.status_effects),
            "analysis": summary
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/status/analyze")
async def analyze_status(request: StatusQueryRequest):
    """
    Analyze character's current status and provide recommendations.
    
    Returns detailed information about:
    - Active buffs and debuffs
    - Action capabilities (can move, attack, cast, etc.)
    - Recommended actions (cure, buff, etc.)
    """
    try:
        char_id = request.char_id
        job = request.job or "novice"
        
        # Get comprehensive analysis
        summary = status_handler.get_status_summary(char_id)
        
        # Get specific recommendations
        active_buffs = status_handler.get_active_buffs(char_id)
        active_debuffs = status_handler.get_active_debuffs(char_id)
        missing_buffs = status_handler.get_missing_buffs(char_id, job)
        
        # Get action recommendation
        recommended_action = status_handler.recommend_action(char_id, job)
        
        return {
            "success": True,
            "char_id": char_id,
            "summary": summary,
            "active_buffs": [sc.value for sc in active_buffs],
            "active_debuffs": [sc.value for sc in active_debuffs],
            "missing_buffs": [sc.value for sc in missing_buffs],
            "missing_buff_names": [
                status_handler.db.get_effect(sc).name 
                for sc in missing_buffs 
                if status_handler.db.get_effect(sc)
            ],
            "recommended_action": recommended_action,
            "should_cure": summary["should_cure"],
            "cure_priority": summary["cure_priority"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status/check_action/{char_id}/{action}")
async def check_action(char_id: int, action: str):
    """
    Check if character can perform a specific action.
    
    Actions: move, attack, cast, item
    """
    try:
        can_act = status_handler.can_act(char_id, action)
        
        return {
            "success": True,
            "char_id": char_id,
            "action": action,
            "can_perform": can_act,
            "reason": "OK" if can_act else "Prevented by status effect"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status/buffs_needed/{char_id}/{job}")
async def get_buffs_needed(char_id: int, job: str):
    """
    Get list of important buffs that are missing for this job.
    
    Returns prioritized list of buffs that should be applied.
    """
    try:
        missing_buffs = status_handler.get_missing_buffs(char_id, job)
        
        buff_details = []
        for sc in missing_buffs:
            effect = status_handler.db.get_effect(sc)
            if effect:
                buff_details.append({
                    "sc_id": sc.value,
                    "name": effect.name,
                    "priority": effect.priority,
                    "description": f"{effect.name} - Priority: {effect.priority}"
                })
        
        return {
            "success": True,
            "char_id": char_id,
            "job": job,
            "missing_buffs": buff_details,
            "total_missing": len(missing_buffs)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ================================================================
# SKILL TREE ENDPOINTS
# ================================================================

@router.post("/skills/next")
async def get_next_skill(request: SkillPathRequest):
    """
    Get the next skill that should be learned.
    
    Uses job class, current skills, and character levels to determine
    the optimal next skill to learn based on prerequisites and importance.
    """
    try:
        next_skill = skill_tree_db.get_next_skill(
            request.job,
            request.current_skills,
            request.base_level,
            request.job_level
        )
        
        if next_skill:
            current_level = request.current_skills.get(next_skill.name, 0)
            return {
                "success": True,
                "has_next_skill": True,
                "skill_name": next_skill.name,
                "skill_id": next_skill.skill_id,
                "current_level": current_level,
                "max_level": next_skill.max_level,
                "next_level": current_level + 1,
                "description": next_skill.description,
                "skill_type": next_skill.skill_type,
                "min_base_level": next_skill.min_base_level,
                "min_job_level": next_skill.min_job_level
            }
        else:
            return {
                "success": True,
                "has_next_skill": False,
                "message": "Skill tree complete or no learnable skills available"
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/skills/path")
async def get_skill_path(request: SkillPathRequest):
    """
    Get the complete learning path to reach a target skill.
    
    Returns ordered list of skills that must be learned (including prerequisites)
    to reach the target skill.
    """
    try:
        if not request.target_skill:
            raise HTTPException(status_code=400, detail="target_skill is required")
        
        path = skill_tree_db.get_skill_path(request.job, request.target_skill)
        
        if not path:
            return {
                "success": False,
                "message": f"Skill '{request.target_skill}' not found for job '{request.job}'"
            }
        
        # Get detailed information for each skill in path
        path_details = []
        total_points = 0
        
        for skill_name in path:
            skill = skill_tree_db.get_skill_by_name(skill_name)
            if skill:
                current_level = request.current_skills.get(skill_name, 0)
                needed_level = skill.max_level
                
                # Check if this is a prerequisite, find required level
                for req in skill_tree_db.get_skill_by_name(request.target_skill).requires:
                    if req.skill_name == skill_name:
                        needed_level = req.level
                        break
                
                points_needed = max(0, needed_level - current_level)
                total_points += points_needed
                
                path_details.append({
                    "skill_name": skill_name,
                    "skill_id": skill.skill_id,
                    "current_level": current_level,
                    "needed_level": needed_level,
                    "max_level": skill.max_level,
                    "points_needed": points_needed,
                    "already_learned": current_level >= needed_level
                })
        
        return {
            "success": True,
            "target_skill": request.target_skill,
            "path": path_details,
            "total_steps": len(path),
            "total_points_needed": total_points
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/skills/tree/{job}")
async def get_skill_tree(job: str):
    """
    Get complete skill tree for a job class.
    
    Returns all available skills for the job, including prerequisites
    and level requirements.
    """
    try:
        tree = skill_tree_db.get_skill_tree(job)
        
        if not tree:
            return {
                "success": False,
                "message": f"No skill tree found for job '{job}'"
            }
        
        skills = []
        for skill in tree:
            skills.append({
                "skill_id": skill.skill_id,
                "name": skill.name,
                "max_level": skill.max_level,
                "min_base_level": skill.min_base_level,
                "min_job_level": skill.min_job_level,
                "description": skill.description,
                "skill_type": skill.skill_type,
                "target_type": skill.target_type,
                "prerequisites": [
                    {"skill": req.skill_name, "level": req.level}
                    for req in skill.requires
                ],
                "job_specific": skill.job_specific if hasattr(skill, 'job_specific') else None
            })
        
        return {
            "success": True,
            "job": job,
            "skills": skills,
            "total_skills": len(skills)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/skills/info/{skill_name}")
async def get_skill_info(skill_name: str):
    """Get detailed information about a specific skill."""
    try:
        skill = skill_tree_db.get_skill_by_name(skill_name)
        
        if not skill:
            return {
                "success": False,
                "message": f"Skill '{skill_name}' not found"
            }
        
        return {
            "success": True,
            "skill_id": skill.skill_id,
            "name": skill.name,
            "max_level": skill.max_level,
            "min_base_level": skill.min_base_level,
            "min_job_level": skill.min_job_level,
            "description": skill.description,
            "skill_type": skill.skill_type,
            "target_type": skill.target_type,
            "prerequisites": [
                {"skill": req.skill_name, "level": req.level}
                for req in skill.requires
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ================================================================
# HEALTH CHECK
# ================================================================

@router.get("/health")
async def health_check():
    """Check game mechanics system health."""
    return {
        "status": "healthy",
        "systems": {
            "status_handler": "initialized",
            "skill_tree_db": "initialized"
        },
        "stats": {
            "tracked_characters": len(status_handler.active_effects),
            "skill_trees_loaded": len(skill_tree_db.trees),
            "total_skills": len(skill_tree_db.skill_by_id)
        }
    }
