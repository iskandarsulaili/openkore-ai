"""
OpenKore AI Service - Python HTTP Server (Phase 8 Complete)
Port: 9902
Provides: LLM integration, Memory system, Database access, CrewAI agents, ML Pipeline, Game Lifecycle Autonomy, Social Interaction System
"""

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
from agents.crew_manager import crew_manager, hierarchical_crew_manager
from llm.provider_chain import llm_chain

# Import Phase 4 PDCA components
from pdca import planner, executor, checker, actor

# Import Phase 6 ML components
from ml.cold_start import cold_start_manager, ColdStartPhase
from ml.data_collector import data_collector, DataCollector, FeatureExtractor
from ml.model_trainer import model_trainer
from ml.online_learner import online_learner, OnlineLearner

# Import Phase 7 Lifecycle components
from lifecycle import character_creator, goal_generator, quest_automation
from lifecycle.progression_manager import ProgressionManager

# Import Phase 8 Social components
from social import personality_engine, ReputationManager, ChatGenerator, InteractionHandler
from social import reputation_manager as rep_mgr_module
from social import chat_generator as chat_gen_module
from social import interaction_handler as int_handler_module

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
    
    # Initialize ML systems (Phase 6)
    global data_collector, online_learner
    data_collector = DataCollector(db)
    online_learner = OnlineLearner(model_trainer, data_collector)
    await cold_start_manager.initialize(db)
    logger.info(f"ML Cold-Start initialized: Phase {cold_start_manager.current_phase}")
    
    # Initialize lifecycle systems (Phase 7)
    global progression_manager
    from lifecycle.progression_manager import progression_manager as pm_module
    progression_manager = ProgressionManager(db)
    logger.info("Game Lifecycle Autonomy initialized")
    
    # Initialize social systems (Phase 8)
    global reputation_manager, chat_generator, interaction_handler
    reputation_manager = ReputationManager(db)
    chat_generator = ChatGenerator(personality_engine)
    interaction_handler = InteractionHandler(personality_engine, reputation_manager, chat_generator)
    logger.info("Social Interaction System initialized")
    
    logger.success("All systems initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await db.close()
    logger.success("Shutdown complete")

app = FastAPI(
    title="OpenKore AI Service",
    version="1.0.0-phase8",
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
        "version": "1.0.0-phase8",
        "ml": {
            "cold_start_phase": cold_start_manager.current_phase if cold_start_manager.start_date else 0,
            "model_trained": cold_start_manager.model_trained,
            "training_samples": cold_start_manager.training_samples_collected
        }
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

@app.post("/api/v1/crew/analyze")
async def crew_analyze(
    character_level: int,
    job_class: str,
    monsters_count: int = 0,
    use_async: bool = False,
    hp: int = 1000,
    max_hp: int = 1000,
    weight: int = 0,
    max_weight: int = 100,
    zeny: int = 0
):
    """
    CrewAI agent analysis with full crewai 1.9.3+ features
    - Custom tools per agent
    - Memory system (short-term, long-term, entity)
    - Agent delegation
    - Task context passing
    - Optional async execution
    - Callbacks for progress tracking
    
    Backward compatible with legacy calls (simple parameters default to sensible values)
    """
    try:
        context = {
            'character': {
                'level': character_level,
                'job_class': job_class,
                'hp': hp,
                'max_hp': max_hp,
                'weight': weight,
                'max_weight': max_weight,
                'zeny': zeny,
                'position': {'map': 'prt_fild08'}
            },
            'monsters': [{'name': f'Monster{i}', 'is_aggressive': i % 2 == 0} for i in range(monsters_count)],
            'inventory': [],
            'session_duration': 30
        }
        
        insights = await crew_manager.consult_agents(context, async_execution=use_async)
        return insights
        
    except Exception as e:
        logger.error(f"Crew analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/crew/analyze_hierarchical")
async def crew_analyze_hierarchical(
    character_level: int,
    job_class: str,
    monsters_count: int = 0,
    hp: int = 1000,
    max_hp: int = 1000
):
    """
    Hierarchical CrewAI analysis - Strategic planner delegates to specialists
    Demonstrates hierarchical process and agent delegation
    """
    try:
        context = {
            'character': {
                'level': character_level,
                'job_class': job_class,
                'hp': hp,
                'max_hp': max_hp,
                'weight': 50,
                'max_weight': 100,
                'zeny': 10000,
                'position': {'map': 'prt_fild08'}
            },
            'monsters': [{'name': f'Monster{i}', 'is_aggressive': True} for i in range(monsters_count)],
            'inventory': [],
            'session_duration': 45
        }
        
        insights = await hierarchical_crew_manager.analyze_with_delegation(context)
        return insights
        
    except Exception as e:
        logger.error(f"Hierarchical crew analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/crew/tools")
async def crew_tools():
    """
    List all available CrewAI tools for agents
    """
    from agents.game_tools import GAME_TOOLS, COMBAT_TOOLS, RESOURCE_TOOLS, STRATEGIC_TOOLS
    
    return {
        "all_tools": [
            {
                "name": tool.name,
                "description": tool.description
            }
            for tool in GAME_TOOLS
        ],
        "tool_sets": {
            "combat": [t.name for t in COMBAT_TOOLS],
            "resource": [t.name for t in RESOURCE_TOOLS],
            "strategic": [t.name for t in STRATEGIC_TOOLS]
        },
        "total_tools": len(GAME_TOOLS)
    }

@app.get("/api/v1/crew/agents")
async def crew_agents():
    """
    Get information about CrewAI agents and their capabilities
    """
    return {
        "agents": [
            {
                "name": "Strategic Planner",
                "role": "Long-term strategy and goal setting",
                "tools": [t.name for t in STRATEGIC_TOOLS],
                "delegation": True,
                "features": ["memory", "verbose", "callbacks"]
            },
            {
                "name": "Combat Tactician",
                "role": "Combat optimization and monster targeting",
                "tools": [t.name for t in COMBAT_TOOLS],
                "delegation": False,
                "features": ["memory", "verbose", "callbacks"]
            },
            {
                "name": "Resource Manager",
                "role": "Inventory and economy management",
                "tools": [t.name for t in RESOURCE_TOOLS],
                "delegation": True,
                "features": ["memory", "verbose", "callbacks"]
            },
            {
                "name": "Performance Analyst",
                "role": "Performance monitoring and optimization",
                "tools": ["analyze_game_state"],
                "delegation": True,
                "features": ["memory", "verbose", "callbacks"]
            }
        ],
        "orchestration": {
            "default_process": "sequential",
            "hierarchical_available": True,
            "async_execution_available": True,
            "memory_enabled": True
        },
        "crewai_version": "1.9.3+"
    }

@app.post("/api/v1/pdca/plan")
async def pdca_plan(session_id: str, character_state: dict):
    """PDCA Plan Phase: Analyze and generate strategy"""
    try:
        # Analyze performance
        performance = await planner.analyze_performance(session_id)
        
        # Generate strategy using LLM
        strategy = await planner.generate_strategy(session_id, character_state, performance)
        
        # Generate macros
        macros = await planner.generate_macros(strategy, character_state)
        
        return {
            "performance": performance,
            "strategy": strategy,
            "macros_generated": len(macros),
            "macro_files": [m[0] for m in macros]
        }
    except Exception as e:
        logger.error(f"PDCA plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/pdca/do")
async def pdca_do(session_id: str, macro_files: List[tuple]):
    """PDCA Do Phase: Write and execute macros"""
    try:
        success = await executor.write_macros(macro_files)
        if success:
            await executor.start_execution(session_id)
            
        return {
            "status": "success" if success else "failed",
            "macros_written": len(macro_files) if success else 0
        }
    except Exception as e:
        logger.error(f"PDCA do error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/pdca/check")
async def pdca_check(session_id: str, game_state: dict):
    """PDCA Check Phase: Evaluate performance"""
    try:
        metrics = await checker.collect_metrics(session_id, game_state)
        evaluation = await checker.evaluate_performance(session_id, metrics)
        
        return {
            "current_metrics": metrics,
            "evaluation": evaluation
        }
    except Exception as e:
        logger.error(f"PDCA check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/pdca/act")
async def pdca_act(session_id: str, new_macros: List[tuple]):
    """PDCA Act Phase: Hot-reload improved macros"""
    try:
        success = await actor.apply_new_macros(new_macros)
        if success:
            result = await actor.notify_reload(session_id)
            return result
        else:
            return {"status": "failed", "message": "Macro reload failed"}
    except Exception as e:
        logger.error(f"PDCA act error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/pdca/cycle")
async def pdca_full_cycle(session_id: str, character_state: dict):
    """Execute complete PDCA cycle"""
    try:
        logger.info(f"Starting full PDCA cycle for session {session_id}")
        
        # Plan
        performance = await planner.analyze_performance(session_id)
        strategy = await planner.generate_strategy(session_id, character_state, performance)
        macros = await planner.generate_macros(strategy, character_state)
        
        # Do
        await executor.write_macros(macros)
        await executor.start_execution(session_id)
        
        # Act (immediate reload)
        await actor.apply_new_macros(macros)
        await actor.notify_reload(session_id)
        
        # Check will happen continuously during execution
        
        return {
            "status": "cycle_complete",
            "performance": performance,
            "strategy_provider": strategy.get('provider', 'unknown'),
            "macros_generated": len(macros),
            "timestamp": int(time.time())
        }
    except Exception as e:
        logger.error(f"PDCA cycle error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/ml/predict")
async def ml_predict(game_state: dict, request_type: str = "ml_prediction"):
    """ML prediction endpoint - Phase 6"""
    try:
        # Check cold-start phase
        if cold_start_manager.should_use_llm():
            # Use LLM during cold-start
            return {
                "action": {
                    "type": "defer_to_llm",
                    "reason": f"Cold-start phase {cold_start_manager.current_phase}: Using LLM",
                    "confidence": 0.7
                },
                "phase": cold_start_manager.current_phase,
                "model_available": False
            }
            
        # Extract features
        features = FeatureExtractor.extract_features(game_state, int(time.time()))
        
        # Make prediction
        prediction, confidence = await model_trainer.predict(features)
        
        # Convert prediction to action
        action_map = {0: 'attack', 1: 'skill', 2: 'move', 3: 'item', 4: 'none'}
        action_type = action_map.get(prediction, 'none')
        
        return {
            "action": {
                "type": action_type,
                "parameters": {},
                "reason": f"ML prediction (confidence: {confidence:.2f})",
                "confidence": confidence
            },
            "phase": cold_start_manager.current_phase,
            "model_available": model_trainer.model is not None
        }
        
    except Exception as e:
        logger.error(f"ML prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/ml/train")
async def ml_train(session_id: str, min_samples: int = 100):
    """Trigger model training - Phase 6"""
    try:
        X, y = await data_collector.collect_training_dataset(session_id, min_samples)
        
        if X is None:
            return {"status": "insufficient_data", "samples_available": 0}
            
        results = await model_trainer.train_model(X, y)
        await model_trainer.export_to_onnx()
        
        cold_start_manager.model_trained = True
        
        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        logger.error(f"ML training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/ml/status")
async def ml_status():
    """Get ML system status - Phase 6"""
    return {
        "cold_start_phase": cold_start_manager.current_phase,
        "start_date": cold_start_manager.start_date.isoformat() if cold_start_manager.start_date else None,
        "training_samples": cold_start_manager.training_samples_collected,
        "model_trained": cold_start_manager.model_trained,
        "should_use_llm": cold_start_manager.should_use_llm(),
        "phase_names": {
            1: "Pure LLM (Days 1-7)",
            2: "Simple Models (Days 8-14)",
            3: "Hybrid (Days 15-21)",
            4: "ML Primary (Days 22-30)"
        }
    }

@app.post("/api/v1/lifecycle/create_character")
async def create_character(playstyle: str = "random"):
    """Generate character creation plan"""
    try:
        job_path = await character_creator.select_job_path(playstyle)
        plan = await character_creator.generate_character_plan(job_path)
        return plan
    except Exception as e:
        logger.error(f"Character creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/lifecycle/update_state")
async def update_lifecycle_state(session_id: str, character_state: dict):
    """Update character lifecycle state"""
    try:
        await progression_manager.update_lifecycle_state(session_id, character_state)
        milestone = await progression_manager.get_next_milestone(character_state.get('level', 1))
        
        return {
            "stage": progression_manager.current_stage,
            "goal": progression_manager.current_goal,
            "next_milestone": milestone
        }
    except Exception as e:
        logger.error(f"Lifecycle update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/lifecycle/generate_goals")
async def generate_goals(character_state: dict, goal_type: str = "short"):
    """Generate autonomous goals"""
    try:
        if goal_type == "short":
            goals = await goal_generator.generate_short_term_goals(
                character_state,
                progression_manager.current_stage
            )
        else:
            goals = await goal_generator.generate_long_term_goals(character_state)
            
        return {"goals": goals, "count": len(goals)}
    except Exception as e:
        logger.error(f"Goal generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/lifecycle/quests")
async def get_available_quests(character_level: int, job_class: str):
    """Get available quests for character"""
    try:
        character_state = {"level": character_level, "job_class": job_class}
        quests = await quest_automation.detect_available_quests(character_state)
        
        return {
            "available_quests": [{"id": q.quest_id, "name": q.name, "steps": len(q.steps)} for q in quests],
            "count": len(quests)
        }
    except Exception as e:
        logger.error(f"Quest detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/social/chat")
async def social_chat(character_name: str, player_name: str, message: str,
                     message_type: str, my_level: int = 50, player_level: int = 50,
                     my_job: str = "Knight"):
    """Handle chat interaction"""
    try:
        context = {
            'my_level': my_level,
            'my_job': my_job,
            'player_level': player_level,
            'player_name': player_name,
            'message_type': message_type,
            'is_whisper': message_type == 'whisper',
            'is_party_member': message_type == 'party',
            'is_guild_member': message_type == 'guild'
        }
        
        result = await interaction_handler.handle_chat(character_name, player_name, message, message_type, context)
        return result if result else {"action": "no_response", "reason": "Personality check or reputation"}
    except Exception as e:
        logger.error(f"Chat handling error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/social/reputation")
async def get_reputation(character_name: str, player_name: str):
    """Get player reputation"""
    reputation = await reputation_manager.get_reputation(character_name, player_name)
    tier = reputation_manager.get_tier_name(reputation)
    
    return {
        "player_name": player_name,
        "reputation": reputation,
        "tier": tier
    }

@app.post("/api/v1/social/reputation/update")
async def update_reputation(character_name: str, player_name: str, change: int, reason: str):
    """Update player reputation"""
    new_rep = await reputation_manager.update_reputation(character_name, player_name, change, reason)
    return {
        "player_name": player_name,
        "new_reputation": new_rep,
        "tier": reputation_manager.get_tier_name(new_rep)
    }

@app.post("/api/v1/social/party_invite")
async def handle_party_invite(character_name: str, player_name: str, my_level: int = 50):
    """Handle party invitation"""
    context = {'my_level': my_level}
    result = await interaction_handler.handle_party_invite(character_name, player_name, context)
    return result if result else {"action": "decline_party"}

@app.post("/api/v1/social/trade")
async def handle_trade(character_name: str, player_name: str, trade_offer: dict):
    """Handle trade request"""
    result = await interaction_handler.handle_trade_request(character_name, player_name, trade_offer)
    return result

@app.post("/api/v1/social/friend_request")
async def handle_friend_request(character_name: str, player_name: str, context: dict = {}):
    """Handle friend request"""
    result = await interaction_handler.handle_friend_request(character_name, player_name, context)
    return result if result else {"action": "decline_friend"}

@app.post("/api/v1/social/marriage_proposal")
async def handle_marriage_proposal(character_name: str, player_name: str, context: dict = {}):
    """Handle marriage proposal"""
    result = await interaction_handler.handle_marriage_proposal(character_name, player_name, context)
    return result if result else {"action": "decline_marriage"}

@app.post("/api/v1/social/pvp_invite")
async def handle_pvp_invite(character_name: str, player_name: str, context: dict = {}):
    """Handle PvP invitation"""
    result = await interaction_handler.handle_pvp_invite(character_name, player_name, context)
    return result if result else {"action": "decline_pvp"}

@app.post("/api/v1/social/guild_invite")
async def handle_guild_invite(character_name: str, player_name: str, context: dict = {}):
    """Handle guild invitation"""
    result = await interaction_handler.handle_guild_invite(character_name, player_name, context)
    return result if result else {"action": "decline_guild"}

@app.get("/api/v1/social/personality")
async def get_personality():
    """Get current personality traits"""
    return {
        "traits": personality_engine.traits,
        "conversation_style": personality_engine.get_conversation_style(),
        "emoji_usage_rate": personality_engine.get_emoji_usage_rate()
    }

@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "OpenKore AI Service",
        "version": "1.0.0-phase8",
        "status": "online",
        "phase": "8 - Social Interaction System Complete",
        "features": [
            "SQLite Database (8 tables)",
            "OpenMemory SDK (synthetic embeddings)",
            "CrewAI Multi-Agent (4 agents with crewai 1.9.3+)",
            "CrewAI Custom Tools (10 game action tools)",
            "CrewAI Memory System (Entity, Short-term, Long-term)",
            "CrewAI Agent Delegation",
            "CrewAI Hierarchical Process",
            "CrewAI Task Context Passing",
            "CrewAI Async Execution",
            "LLM Provider Chain (DeepSeek→OpenAI→Anthropic)",
            "PDCA Cycle (Plan-Do-Check-Act)",
            "ML Pipeline (4-phase cold-start)",
            "Online Learning System",
            "ONNX Model Export",
            "Character Creation Automation",
            "Progression Management",
            "Autonomous Goal Generation",
            "Quest Automation Framework",
            "Personality Engine (8 traits)",
            "Player Reputation System (7 tiers)",
            "Human-Like Chat Generation",
            "Social Interaction Handler (7 categories)"
        ],
        "endpoints": [
            "/api/v1/health",
            "/api/v1/llm/query",
            "/api/v1/memory/query",
            "/api/v1/memory/add",
            "/api/v1/crew/analyze",
            "/api/v1/crew/analyze_hierarchical",
            "/api/v1/crew/tools",
            "/api/v1/crew/agents",
            "/api/v1/pdca/plan",
            "/api/v1/pdca/do",
            "/api/v1/pdca/check",
            "/api/v1/pdca/act",
            "/api/v1/pdca/cycle",
            "/api/v1/ml/predict",
            "/api/v1/ml/train",
            "/api/v1/ml/status",
            "/api/v1/lifecycle/create_character",
            "/api/v1/lifecycle/update_state",
            "/api/v1/lifecycle/generate_goals",
            "/api/v1/lifecycle/quests",
            "/api/v1/social/chat",
            "/api/v1/social/reputation",
            "/api/v1/social/reputation/update",
            "/api/v1/social/party_invite",
            "/api/v1/social/trade",
            "/api/v1/social/personality"
        ]
    }

if __name__ == "__main__":
    logger.info("OpenKore AI Service v1.0.0-phase8")
    logger.info("Starting HTTP server on http://127.0.0.1:9902")
    logger.info("Phase 8: Social Interaction System Complete")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=9902,
        log_level="info"
    )
