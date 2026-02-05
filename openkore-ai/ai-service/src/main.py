"""
OpenKore AI Service - Python HTTP Server (Phase 3 Complete)
Port: 9902
Provides: LLM integration, Memory system, Database access, CrewAI agents
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import uvicorn
import time
import os
from loguru import logger
from contextlib import asynccontextmanager

# Import Phase 3 components
from database import db
from memory.openmemory_manager import OpenMemoryManager
from agents.crew_manager import crew_manager
from llm.provider_chain import llm_chain

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting OpenKore AI Service...")
    
    # Initialize database
    await db.initialize()
    
    # Initialize memory manager
    global memory_manager
    memory_manager = OpenMemoryManager(db)
    
    # Initialize LLM provider chain
    await llm_chain.initialize()
    
    logger.success("All systems initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await db.close()
    logger.success("Shutdown complete")

app = FastAPI(
    title="OpenKore AI Service",
    version="1.0.0-phase3",
    lifespan=lifespan
)

# Startup time
START_TIME = time.time()

# Models
class GameState(BaseModel):
    character: Dict[str, Any]
    monsters: List[Dict[str, Any]] = []
    inventory: List[Dict[str, Any]] = []
    nearby_players: List[Dict[str, Any]] = []
    party_members: Dict[str, str] = {}
    timestamp_ms: int

class Action(BaseModel):
    type: str
    parameters: Dict[str, str]
    reason: str
    confidence: float

class LLMRequest(BaseModel):
    prompt: str
    game_state: GameState
    context: Optional[str] = None
    request_id: str

class LLMResponse(BaseModel):
    response: str
    action: Optional[Action] = None
    latency_ms: int
    provider: str
    request_id: str
    crew_insights: Optional[Dict[str, Any]] = None

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    uptime_seconds = int(time.time() - START_TIME)
    
    # Check component health
    db_healthy = db.conn is not None
    llm_healthy = any(p.available for p in llm_chain.providers)
    
    return {
        "status": "healthy" if (db_healthy and llm_healthy) else "degraded",
        "components": {
            "database": db_healthy,
            "llm_deepseek": llm_chain.providers[0].available if len(llm_chain.providers) > 0 else False,
            "llm_openai": llm_chain.providers[1].available if len(llm_chain.providers) > 1 else False,
            "llm_anthropic": llm_chain.providers[2].available if len(llm_chain.providers) > 2 else False,
            "openmemory": True,
            "crewai": True
        },
        "uptime_seconds": uptime_seconds,
        "version": "1.0.0-phase3"
    }

@app.post("/api/v1/llm/query")
async def llm_query(request: LLMRequest):
    """
    Query LLM for strategic decisions
    Phase 3: Full implementation with DeepSeek/OpenAI/Anthropic chain
    """
    start_time_ms = int(time.time() * 1000)
    
    try:
        # Create session if needed
        session_id = request.request_id.split('_')[0]
        character_name = request.game_state.character.get('name', 'Unknown')
        
        try:
            await db.create_session(session_id, character_name)
        except Exception:
            pass  # Session might already exist
        
        # Consult CrewAI agents for multi-perspective analysis
        crew_insights = await crew_manager.consult_agents({
            'character': request.game_state.character,
            'monsters': request.game_state.monsters,
            'inventory': request.game_state.inventory
        })
        
        # Build enriched prompt
        enriched_prompt = f"""
{request.prompt}

Context: {request.context}

Character Status:
- Name: {character_name}
- Level: {request.game_state.character.get('level', 'Unknown')}
- HP: {request.game_state.character.get('hp', 0)}/{request.game_state.character.get('max_hp', 0)}
- Job: {request.game_state.character.get('job_class', 'Unknown')}

CrewAI Agent Insights:
{crew_insights['aggregated_recommendations'][:3] if crew_insights else 'None'}

Provide strategic advice for this situation.
"""
        
        # Query LLM provider chain
        llm_result = await llm_chain.query(enriched_prompt, {
            'game_state': request.game_state.dict(),
            'context': request.context
        })
        
        if not llm_result:
            raise HTTPException(status_code=503, detail="All LLM providers failed")
        
        # Store memory
        await memory_manager.add_episodic(
            session_id,
            f"LLM Query: {request.prompt} -> {llm_result['response'][:100]}",
            importance=0.7
        )
        
        # Generate action from LLM response
        action = Action(
            type="strategic_plan",
            parameters={"plan": llm_result['response'][:200]},
            reason=f"Strategic advice from {llm_result['provider']}",
            confidence=0.8
        )
        
        latency_ms = int(time.time() * 1000) - start_time_ms
        
        return LLMResponse(
            response=llm_result['response'],
            action=action,
            latency_ms=latency_ms,
            provider=llm_result['provider'],
            request_id=request.request_id,
            crew_insights=crew_insights
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LLM query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/memory/query")
async def memory_query(session_id: str, query: str, sector: Optional[str] = None, limit: int = 10):
    """
    Query OpenMemory system
    Phase 3: Full implementation with synthetic embeddings
    """
    try:
        results = await memory_manager.query_similar(session_id, query, sector, limit)
        
        return {
            "results": results,
            "count": len(results),
            "query": query,
            "sector": sector
        }
        
    except Exception as e:
        logger.error(f"Memory query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/memory/add")
async def memory_add(session_id: str, sector: str, content: str, importance: float = 0.5):
    """Add memory to OpenMemory system"""
    try:
        await memory_manager.add_memory(session_id, sector, content, importance)
        return {"status": "success", "message": f"Added {sector} memory"}
    except Exception as e:
        logger.error(f"Memory add error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/crew/analyze")
async def crew_analyze(character_level: int, job_class: str, monsters_count: int = 0):
    """Get CrewAI agent analysis"""
    try:
        context = {
            'character': {
                'level': character_level,
                'job_class': job_class,
                'hp': 1000,
                'max_hp': 1000
            },
            'monsters': [{'name': f'Monster{i}', 'is_aggressive': False} for i in range(monsters_count)]
        }
        
        insights = await crew_manager.consult_agents(context)
        return insights
        
    except Exception as e:
        logger.error(f"Crew analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "OpenKore AI Service",
        "version": "1.0.0-phase3",
        "status": "online",
        "phase": "3 - Python AI Service Foundation Complete",
        "features": [
            "SQLite Database (8 tables)",
            "OpenMemory SDK (synthetic embeddings)",
            "CrewAI Multi-Agent (4 agents)",
            "LLM Provider Chain (DeepSeek→OpenAI→Anthropic)"
        ],
        "endpoints": [
            "/api/v1/health",
            "/api/v1/llm/query",
            "/api/v1/memory/query",
            "/api/v1/memory/add",
            "/api/v1/crew/analyze"
        ]
    }

if __name__ == "__main__":
    logger.info("OpenKore AI Service v1.0.0-phase3")
    logger.info("Starting HTTP server on http://127.0.0.1:9902")
    logger.info("Phase 3: Python AI Service Foundation Complete")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=9902,
        log_level="info"
    )
