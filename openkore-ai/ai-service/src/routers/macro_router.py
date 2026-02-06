"""
Macro Management REST API Router
Provides endpoints for the Three-Layer Adaptive Macro System
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Router instance
router = APIRouter(prefix="/api/v1/macro", tags=["macro"])

# Global coordinator instance (will be injected from main.py)
_coordinator = None


def set_coordinator(coordinator):
    """Set the MacroManagementCoordinator instance"""
    global _coordinator
    _coordinator = coordinator
    logger.info("MacroManagementCoordinator registered with router")


# Request/Response Models
class GameStateRequest(BaseModel):
    """Game state input for macro processing"""
    session_id: str = Field(..., description="Session identifier")
    character: Dict[str, Any] = Field(..., description="Character state")
    position: Dict[str, Any] = Field(default={}, description="Position data")
    nearby: Dict[str, Any] = Field(default={}, description="Nearby entities")
    inventory: Dict[str, Any] = Field(default={}, description="Inventory state")
    timestamp_ms: int = Field(..., description="Timestamp in milliseconds")


class MacroInjectRequest(BaseModel):
    """Manual macro injection request"""
    name: str = Field(..., description="Macro name")
    definition: str = Field(..., description="Macro definition text")
    priority: int = Field(default=50, ge=1, le=100, description="Macro priority")


class ProcessingResponse(BaseModel):
    """Response from macro processing"""
    layer: int = Field(..., description="Layer that handled the request (1=Conscious, 2=Subconscious, 3=Reflex)")
    action: str = Field(..., description="Action taken")
    session_id: str
    timestamp_ms: int
    details: Dict[str, Any] = Field(default={})


# Endpoints

@router.post("/process", response_model=ProcessingResponse)
async def process_game_state(request: GameStateRequest):
    """
    Main entry point: Process game state through three-layer system
    
    The coordinator will route through:
    - Layer 3 (Reflex): If emergency condition detected
    - Layer 2 (Subconscious): If ML model confident (>85%)
    - Layer 1 (Conscious): If strategic reasoning needed
    """
    if not _coordinator:
        raise HTTPException(status_code=503, detail="MacroManagementCoordinator not initialized")
    
    try:
        logger.info(f"Processing game state for session: {request.session_id}")
        
        game_state = {
            'character': request.character,
            'position': request.position,
            'nearby': request.nearby,
            'inventory': request.inventory
        }
        
        result = await _coordinator.process_game_state(game_state, request.session_id)
        
        return ProcessingResponse(
            layer=result.get('layer', 1),
            action=result.get('action', 'processed'),
            session_id=request.session_id,
            timestamp_ms=request.timestamp_ms,
            details=result
        )
        
    except Exception as e:
        logger.error(f"Error processing game state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/inject")
async def inject_macro(request: MacroInjectRequest):
    """
    Manually inject a macro (for testing or manual intervention)
    """
    if not _coordinator:
        raise HTTPException(status_code=503, detail="MacroManagementCoordinator not initialized")
    
    try:
        from ..macro.deployment_service import MacroDefinition
        
        macro_def = MacroDefinition(
            name=request.name,
            definition=request.definition,
            priority=request.priority
        )
        
        result = await _coordinator.deployment.inject_macro(macro_def)
        
        return {
            "status": "success",
            "macro_name": request.name,
            "deployment": result
        }
        
    except Exception as e:
        logger.error(f"Error injecting macro: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_macros():
    """
    List currently active macros
    """
    if not _coordinator:
        raise HTTPException(status_code=503, detail="MacroManagementCoordinator not initialized")
    
    try:
        macros = await _coordinator.deployment.list_macros()
        
        return {
            "macros": macros,
            "count": len(macros)
        }
        
    except Exception as e:
        logger.error(f"Error listing macros: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{macro_name}")
async def delete_macro(macro_name: str):
    """
    Delete a specific macro
    """
    if not _coordinator:
        raise HTTPException(status_code=503, detail="MacroManagementCoordinator not initialized")
    
    try:
        result = await _coordinator.deployment.delete_macro(macro_name)
        
        return {
            "status": "success",
            "macro_name": macro_name,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error deleting macro: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_statistics():
    """
    Get comprehensive system statistics
    """
    if not _coordinator:
        raise HTTPException(status_code=503, detail="MacroManagementCoordinator not initialized")
    
    try:
        stats = _coordinator.get_system_statistics()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check for macro system components
    """
    if not _coordinator:
        raise HTTPException(status_code=503, detail="MacroManagementCoordinator not initialized")
    
    try:
        health = await _coordinator.health_check()
        
        return {
            "status": "healthy" if all(health.values()) else "degraded",
            "components": health
        }
        
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train")
async def train_ml_model(min_samples: int = 100):
    """
    Trigger ML model training from collected data
    """
    if not _coordinator:
        raise HTTPException(status_code=503, detail="MacroManagementCoordinator not initialized")
    
    try:
        logger.info(f"Starting ML model training (min_samples={min_samples})")
        
        result = await _coordinator.train_ml_model(min_samples=min_samples)
        
        return result
        
    except Exception as e:
        logger.error(f"Error training ML model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize/{macro_name}")
async def optimize_macro(macro_name: str, performance_data: Dict[str, Any]):
    """
    Optimize an existing macro based on performance data
    """
    if not _coordinator:
        raise HTTPException(status_code=503, detail="MacroManagementCoordinator not initialized")
    
    try:
        # Get current macro definition
        macros = await _coordinator.deployment.list_macros()
        macro = next((m for m in macros if m.get('name') == macro_name), None)
        
        if not macro:
            raise HTTPException(status_code=404, detail=f"Macro '{macro_name}' not found")
        
        result = await _coordinator.optimize_existing_macro(
            macro_name,
            macro.get('definition', ''),
            performance_data
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing macro: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/{session_id}")
async def generate_performance_report(session_id: str):
    """
    Generate performance report for a session
    """
    if not _coordinator:
        raise HTTPException(status_code=503, detail="MacroManagementCoordinator not initialized")
    
    try:
        # Get session data from database
        # (This would need to be implemented in the coordinator)
        session_data = {}  # Placeholder
        
        report = await _coordinator.generate_performance_report(session_id, session_data)
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
