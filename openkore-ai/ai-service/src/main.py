"""
OpenKore AI Service - Python HTTP Server (Phase 10 Complete + Critical Fixes)
Port: 9902
Provides: LLM integration, Memory system, Database access, CrewAI agents, ML Pipeline, Game Lifecycle Autonomy, Social Interaction System, Autonomous Self-Healing
"""

import warnings

# Suppress Pydantic V1 deprecation warnings from third-party dependencies (ChromaDB 1.1.1)
# Our code is fully Pydantic V2 compliant, but ChromaDB has deprecated patterns
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="pydantic._internal._config",
    message=".*Valid config keys have changed in V2.*"
)

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import uvicorn
import time
import os
import asyncio
from pathlib import Path
from loguru import logger
from contextlib import asynccontextmanager

# Import console logger for visible AI layer activity
from utils.console_logger import console_logger, LayerType

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

# Import Phase 11 Progression components
from progression.stat_allocator import StatAllocator
from progression.skill_learner import SkillLearner
from combat.equipment_manager import EquipmentManager

# Import Priority 1 Combat Intelligence systems (opkAI)
from combat.threat_assessor import ThreatAssessor
from combat.kiting_engine import KitingEngine
from combat.target_selector import TargetSelector
from combat.positioning_engine import PositioningEngine

# Import Phase 8 Social components
from social import personality_engine, ReputationManager, ChatGenerator, InteractionHandler
from social import reputation_manager as rep_mgr_module
from social import chat_generator as chat_gen_module
from social import interaction_handler as int_handler_module

# Import Phase 9 Macro Management components
from macro.coordinator import MacroManagementCoordinator
from routers import macro_router

# Import Phase 10 Autonomous Self-Healing components
from autonomous_healing import AutonomousHealingSystem

# Import Priority 1 Game Mechanics components (rathena extraction)
from routers import game_mechanics_router

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting OpenKore AI Service...")
    
    # Print exciting startup banner
    console_logger.print_startup_banner()
    
    # Initialize database
    console_logger.print_layer_initialization(
        LayerType.SYSTEM,
        "Initializing Database...",
        "SQLite with 8 tables"
    )
    await db.initialize()
    console_logger.print_layer_initialization(
        LayerType.SYSTEM,
        "Database Ready ✓"
    )
    
    # Validate configuration and warn about missing items
    console_logger.print_layer_initialization(
        LayerType.SYSTEM,
        "Validating Configuration...",
        "Checking healing items, teleport config, survival setup"
    )
    from utils.startup_validator import validate_and_report
    try:
        validate_and_report()
    except RuntimeError as e:
        logger.error(f"Startup validation failed: {e}")
        raise
    console_logger.print_layer_initialization(
        LayerType.SYSTEM,
        "Configuration Validated ✓"
    )
    
    # Initialize memory manager
    global memory_manager
    memory_manager = OpenMemoryManager(db)
    
    # Initialize LLM provider chain
    await llm_chain.initialize()
    
    # Initialize ML systems (Phase 6)
    console_logger.print_layer_initialization(
        LayerType.SUBCONSCIOUS,
        "Initializing ML Systems...",
        "Pattern recognition, prediction models, online learning"
    )
    global data_collector, online_learner
    data_collector = DataCollector(db)
    online_learner = OnlineLearner(model_trainer, data_collector)
    await cold_start_manager.initialize(db)
    console_logger.print_layer_initialization(
        LayerType.SUBCONSCIOUS,
        f"ML Systems Ready ✓",
        f"Cold-start Phase {cold_start_manager.current_phase}, Model trained: {cold_start_manager.model_trained}"
    )
    logger.info(f"ML Cold-Start initialized: Phase {cold_start_manager.current_phase}")
    
    # Initialize progression systems (Phase 11)
    console_logger.print_layer_initialization(
        LayerType.SYSTEM,
        "Initializing Progression Systems...",
        "Autonomous stat allocation, skill learning, equipment management"
    )
    # Initialize combat intelligence systems (Priority 1)
    console_logger.print_layer_initialization(
        LayerType.REFLEX,
        "Initializing Combat Intelligence...",
        "Threat assessment, kiting, targeting, positioning"
    )
    global threat_assessor, target_selector
    threat_assessor = ThreatAssessor()
    target_selector = TargetSelector()
    console_logger.print_layer_initialization(
        LayerType.REFLEX,
        "Combat Intelligence Ready ✓",
        "4 systems: Threat, Kiting, Targeting, Positioning"
    )
    logger.info("Combat Intelligence Systems initialized (Priority 1)")
    
    global stat_allocator, skill_learner, equipment_manager
    user_intent_path = Path(__file__).parent / "data" / "user_intent.json"
    job_builds_path = Path(__file__).parent / "data" / "job_builds.json"
    
    stat_allocator = StatAllocator(str(user_intent_path), str(job_builds_path))
    skill_learner = SkillLearner(str(user_intent_path), str(job_builds_path))
    equipment_manager = EquipmentManager(str(user_intent_path))
    
    console_logger.print_layer_initialization(
        LayerType.SYSTEM,
        "Progression Systems Ready ✓",
        "95% autonomy enabled: Stats, Skills, Equipment"
    )
    logger.info("Autonomous Progression Systems initialized (Phase 11)")
    
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
    
    # Initialize macro management system (Phase 9)
    console_logger.print_layer_initialization(
        LayerType.CONSCIOUS,
        "Initializing CrewAI Strategic Layer...",
        "Multi-agent collaboration, macro generation, strategic planning"
    )
    global macro_coordinator
    macro_coordinator = MacroManagementCoordinator(
        openkore_url="http://127.0.0.1:8765",
        db_path="data/openkore-ai.db"
    )
    macro_router.set_coordinator(macro_coordinator)
    console_logger.print_layer_initialization(
        LayerType.CONSCIOUS,
        "CrewAI Strategic Layer Ready ✓",
        "Agents: Strategist, Analyst, Generator, Optimizer"
    )
    
    console_logger.print_layer_initialization(
        LayerType.REFLEX,
        "OpenKore EventMacro Connected ✓",
        "Ultra-fast trigger-based execution ready"
    )
    logger.info("Three-Layer Adaptive Macro System initialized")
    
    # Initialize autonomous self-healing system (Phase 10)
    global healing_system, healing_task
    try:
        # Use Path(__file__).parent to construct path relative to main.py location
        config_path = Path(__file__).parent / "autonomous_healing" / "config.yaml"
        healing_system = AutonomousHealingSystem(config_path=str(config_path))
        # Start healing system as background task
        healing_task = asyncio.create_task(healing_system.start())
        logger.info("Autonomous Self-Healing System initialized and running in background")
    except Exception as e:
        logger.warning(f"Autonomous Self-Healing System initialization failed (non-critical): {e}")
        healing_system = None
        healing_task = None
    
    logger.success("All systems initialized successfully")
    
    # Start system heartbeat background task
    global heartbeat_task
    heartbeat_task = asyncio.create_task(system_heartbeat())
    console_logger.print_layer_initialization(
        LayerType.SYSTEM,
        "System Heartbeat Started ✓",
        "Monitoring all three layers (30s interval)"
    )
    
    print("\n" + "═" * 63)
    print("✨ GODTIER AI SYSTEM FULLY OPERATIONAL - READY TO DOMINATE ✨")
    print("═" * 63 + "\n")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    
    # Shutdown heartbeat task
    if 'heartbeat_task' in globals() and heartbeat_task and not heartbeat_task.done():
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
    
    # Shutdown autonomous healing system
    if healing_system is not None:
        logger.info("Stopping Autonomous Self-Healing System...")
        try:
            await healing_system.stop()
            if healing_task and not healing_task.done():
                healing_task.cancel()
                try:
                    await healing_task
                except asyncio.CancelledError:
                    pass
            logger.info("Autonomous Self-Healing System stopped")
        except Exception as e:
            logger.error(f"Error stopping healing system: {e}")
    
    await db.close()
    logger.success("Shutdown complete")


async def system_heartbeat():
    """Background task to show system is alive and all layers are active"""
    await asyncio.sleep(30)  # Wait 30 seconds before first heartbeat
    
    while True:
        try:
            console_logger.print_heartbeat()
            await asyncio.sleep(30)  # Heartbeat every 30 seconds
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            await asyncio.sleep(30)

app = FastAPI(
    title="OpenKore AI Service",
    version="1.0.0-phase10",
    lifespan=lifespan
)

# Register macro router
app.include_router(macro_router.router)

# Register game mechanics router (Priority 1: rathena knowledge extraction)
app.include_router(game_mechanics_router.router)

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
        "version": "1.0.0-phase10",
        "ml": {
            "cold_start_phase": cold_start_manager.current_phase if cold_start_manager.start_date else 0,
            "model_trained": cold_start_manager.model_trained,
            "training_samples": cold_start_manager.training_samples_collected
        },
        "autonomous_healing": {
            "enabled": healing_system is not None,
            "running": healing_system.running if healing_system else False,
            "agents_active": len(healing_system.agents) if healing_system else 0
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

# ============================================================================
# PHASE 11: AUTONOMOUS PROGRESSION ENDPOINTS
# ============================================================================

@app.post("/api/v1/progression/stats/on_level_up")
async def handle_stat_level_up(current_level: int, current_stats: dict):
    """
    Called by GodTierAI when character levels up.
    Returns stat allocation plan for raiseStat.pl plugin.
    """
    try:
        result = stat_allocator.on_level_up(current_level, current_stats)
        return result
    except Exception as e:
        logger.error(f"Stat allocation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/progression/stats/update_performance")
async def update_stat_performance(death_count: int, avg_kill_time: float):
    """
    Update performance metrics for adaptive stat allocation.
    """
    try:
        stat_allocator.adjust_for_performance(death_count, avg_kill_time)
        return {
            "status": "success",
            "death_count": death_count,
            "avg_kill_time": avg_kill_time
        }
    except Exception as e:
        logger.error(f"Performance update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/progression/stats/recommendations")
async def get_stat_recommendations(current_stats: dict, free_points: int):
    """
    Get immediate stat allocation recommendations for available free points.
    """
    try:
        recommendations = stat_allocator.get_allocation_recommendations(
            current_stats, free_points
        )
        return {
            "free_points": free_points,
            "recommendations": recommendations
        }
    except Exception as e:
        logger.error(f"Stat recommendations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/progression/skills/on_job_level_up")
async def handle_skill_job_level_up(current_job_level: int, job: str, current_skills: dict):
    """
    Called by GodTierAI when job level increases.
    Returns skill learning plan for raiseSkill.pl plugin.
    """
    try:
        result = skill_learner.on_job_level_up(current_job_level, job, current_skills)
        return result
    except Exception as e:
        logger.error(f"Skill learning error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/progression/skills/update_combat_stats")
async def update_skill_combat_stats(combat_stats: dict):
    """
    Update combat statistics for adaptive skill learning.
    """
    try:
        skill_learner.update_combat_stats(combat_stats)
        return {
            "status": "success",
            "combat_stats": combat_stats
        }
    except Exception as e:
        logger.error(f"Combat stats update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/progression/skills/should_learn")
async def check_should_learn_skill(skill_name: str, combat_stats: dict):
    """
    Check if a specific skill should be learned based on performance.
    """
    try:
        should_learn, reason = skill_learner.should_learn_skill(skill_name, combat_stats)
        return {
            "skill": skill_name,
            "should_learn": should_learn,
            "reason": reason
        }
    except Exception as e:
        logger.error(f"Skill check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/progression/equipment/on_map_change")
async def handle_equipment_map_change(new_map: str, enemies: List[dict]):
    """
    Called when entering a new map.
    Analyzes enemies and recommends optimal equipment setup.
    """
    try:
        result = equipment_manager.on_map_change(new_map, enemies)
        return result
    except Exception as e:
        logger.error(f"Equipment map change error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/progression/equipment/on_combat_start")
async def handle_equipment_combat_start(enemy: dict):
    """
    Called when engaging an enemy.
    May switch equipment for specific enemy matchups.
    """
    try:
        result = equipment_manager.on_combat_start(enemy)
        return result
    except Exception as e:
        logger.error(f"Equipment combat start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/progression/equipment/on_taking_damage")
async def handle_equipment_damage(damage_type: str, damage_amount: int, enemy: dict):
    """
    Called when taking damage.
    May switch to defensive equipment if taking heavy damage.
    """
    try:
        result = equipment_manager.on_taking_damage(damage_type, damage_amount, enemy)
        return result
    except Exception as e:
        logger.error(f"Equipment damage handling error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/progression/equipment/situation/{situation}")
async def get_equipment_for_situation(situation: str):
    """
    Get equipment recommendations for specific situations.
    Situations: 'boss', 'mvp', 'farming', 'pvp', 'defense'
    """
    try:
        result = equipment_manager.get_equipment_for_situation(situation)
        return result
    except Exception as e:
        logger.error(f"Equipment situation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/progression/status")
async def get_progression_status():
    """
    Get current progression system status and configuration.
    """
    try:
        build_config = stat_allocator.get_current_build_config()
        
        return {
            "user_intent": stat_allocator.user_intent,
            "current_build": build_config.get('name', 'Unknown') if build_config else 'Not configured',
            "autonomy_level": stat_allocator.user_intent.get('autonomy_level', 0),
            "features_enabled": stat_allocator.user_intent.get('features_enabled', {}),
            "performance_metrics": {
                "stat_allocator": {
                    "death_count": stat_allocator.death_count,
                    "avg_kill_time": stat_allocator.avg_kill_time
                },
                "skill_learner": {
                    "combat_stats": skill_learner.combat_stats
                }
            }
        }
    except Exception as e:
        logger.error(f"Progression status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/progression/export_config")
async def export_progression_config(output_path: str):
    """
    Export progression configuration to OpenKore config files.
    Updates config.txt with statsAddAuto and skillsAddAuto settings.
    """
    try:
        stat_success = stat_allocator.export_config_file(output_path)
        skill_success = skill_learner.export_config_file(output_path)
        equipment_success = equipment_manager.export_equipment_config(
            output_path.replace('config.txt', 'equipAuto.txt')
        )
        
        return {
            "status": "success" if (stat_success and skill_success) else "partial",
            "stat_config_exported": stat_success,
            "skill_config_exported": skill_success,
            "equipment_config_exported": equipment_success,
            "output_path": output_path
        }
    except Exception as e:
        logger.error(f"Config export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# PRIORITY 1: COMBAT INTELLIGENCE ENDPOINTS (opkAI)
# ============================================================================

@app.post("/api/v1/combat/threat/assess")
async def assess_threat_endpoint(data: dict):
    """
    Assess threat before engaging enemy.
    Uses 9-factor analysis to calculate win probability.
    
    Request body:
    {
        "target": {id, level, hp, hp_max, element, race, size, ...},
        "character": {level, hp, sp, hp_max, sp_max, attack, matk, buffs, equipment, skills, ...},
        "nearby_enemies": [{...}, ...],
        "consumables": {potions: int, fly_wings: int}
    }
    """
    try:
        assessment = threat_assessor.assess_threat(
            data["target"],
            data["character"],
            data.get("nearby_enemies", []),
            data.get("consumables", {})
        )
        return assessment.to_dict()
    except Exception as e:
        logger.error(f"Threat assessment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/combat/kiting/update")
async def kiting_update(data: dict):
    """
    Update kiting state machine for ranged combat.
    
    Request body:
    {
        "job_class": str,
        "char_pos": [x, y],
        "enemy_pos": [x, y],
        "hp_percent": float,
        "enemy_targeting_us": bool (optional)
    }
    """
    try:
        job = data["job_class"]
        
        # Create job-specific kiting engine (lightweight, can create per request)
        kiting = KitingEngine(job)
        
        update = kiting.update(
            tuple(data["char_pos"]),
            tuple(data["enemy_pos"]),
            data["hp_percent"],
            data.get("enemy_targeting_us", True)
        )
        
        return update.to_dict()
    except Exception as e:
        logger.error(f"Kiting update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/combat/kiting/metrics")
async def kiting_metrics(job_class: str):
    """Get kiting metrics for job class"""
    try:
        kiting = KitingEngine(job_class)
        return {
            "job_class": job_class,
            "config": {
                "min_distance": kiting.config.min_distance,
                "optimal_distance": kiting.config.optimal_distance,
                "max_distance": kiting.config.max_distance,
                "emergency_distance": kiting.config.emergency_distance,
                "emergency_hp_threshold": kiting.config.emergency_hp_threshold
            },
            "metrics": kiting.get_metrics()
        }
    except Exception as e:
        logger.error(f"Kiting metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/combat/target/select")
async def select_target(data: dict):
    """
    Select best target using XP/zeny efficiency.
    
    Request body:
    {
        "monsters": [{id, name, level, hp, hp_max, pos, base_exp, element, ...}, ...],
        "character": {level, pos, attack, matk, element, ...},
        "quest_targets": [int, ...] (optional)
    }
    """
    try:
        best = target_selector.select_best_target(
            data["monsters"],
            data["character"],
            data.get("quest_targets")
        )
        
        if best is None:
            return {"status": "no_targets", "target": None}
        
        return {
            "status": "success",
            "target": best.to_dict()
        }
    except Exception as e:
        logger.error(f"Target selection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/combat/target/clear")
async def clear_target():
    """Clear current target (e.g., when target dies)"""
    try:
        target_selector.clear_target()
        return {"status": "success", "message": "Target cleared"}
    except Exception as e:
        logger.error(f"Clear target error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/combat/target/metrics")
async def target_metrics():
    """Get targeting metrics"""
    try:
        metrics = target_selector.get_metrics()
        return {
            "status": "success",
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"Target metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/combat/positioning/optimal")
async def find_optimal_position(data: dict):
    """
    Find optimal combat position using 5-factor scoring.
    
    Request body:
    {
        "char_pos": [x, y],
        "target_pos": [x, y],
        "skill_range": int,
        "enemies": [{pos: [x, y], ...}, ...],
        "map_data": {walkable: [[x, y], ...], walls: [[x, y], ...]},
        "hp_percent": float,
        "job_class": str,
        "aoe_range": int (optional)
    }
    """
    try:
        positioning = PositioningEngine()
        
        # Convert walkable/walls lists to sets of tuples
        map_data = data["map_data"]
        if "walkable" in map_data and isinstance(map_data["walkable"], list):
            map_data["walkable"] = set(tuple(pos) for pos in map_data["walkable"])
        if "walls" in map_data and isinstance(map_data["walls"], list):
            map_data["walls"] = set(tuple(pos) for pos in map_data["walls"])
        
        optimal = positioning.find_optimal_position(
            tuple(data["char_pos"]),
            tuple(data["target_pos"]),
            data["skill_range"],
            data["enemies"],
            map_data,
            data["hp_percent"],
            data["job_class"],
            data.get("aoe_range", 0)
        )
        
        return optimal.to_dict()
    except Exception as e:
        logger.error(f"Positioning error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/combat/status")
async def combat_intelligence_status():
    """Get combat intelligence systems status"""
    return {
        "status": "online",
        "systems": {
            "threat_assessor": {
                "initialized": threat_assessor is not None,
                "mvp_count": len(threat_assessor.mvp_ids) if threat_assessor else 0,
                "boss_count": len(threat_assessor.boss_ids) if threat_assessor else 0
            },
            "target_selector": {
                "initialized": target_selector is not None,
                "metrics": target_selector.get_metrics() if target_selector else {}
            },
            "kiting_engine": {
                "available_jobs": list(KitingEngine.KITING_CONFIGS.keys()),
                "total_configs": len(KitingEngine.KITING_CONFIGS)
            },
            "positioning_engine": {
                "available_strategies": [pt.value for pt in PositionType],
                "total_strategies": len(PositionType)
            }
        },
        "version": "1.0.0-priority1",
        "based_on": "opkAI combat intelligence"
    }

@app.get("/api/v1/social/personality")
async def get_personality():
    """Get current personality traits"""
    return {
        "traits": personality_engine.traits,
        "conversation_style": personality_engine.get_conversation_style(),
        "emoji_usage_rate": personality_engine.get_emoji_usage_rate()
    }

@app.get("/api/v1/healing/status")
async def healing_status():
    """Get autonomous healing system status"""
    if healing_system is None:
        return {
            "enabled": False,
            "status": "not_initialized",
            "message": "Autonomous healing system is not available"
        }
    
    return {
        "enabled": True,
        "running": healing_system.running,
        "agents": {
            "monitor": healing_system.agents.get('monitor') is not None,
            "analyzer": healing_system.agents.get('analyzer') is not None,
            "solver": healing_system.agents.get('solver') is not None,
            "validator": healing_system.agents.get('validator') is not None,
            "executor": healing_system.agents.get('executor') is not None,
            "learner": healing_system.agents.get('learner') is not None
        },
        "agents_count": len(healing_system.agents),
        "config": {
            "monitoring_enabled": healing_system.config['monitoring']['enabled'],
            "poll_interval": healing_system.config['monitoring']['poll_interval_seconds'],
            "execution_enabled": healing_system.config['execution']['enabled'],
            "safe_mode": healing_system.config['execution']['safe_mode'],
            "learning_enabled": healing_system.config['learning']['enabled']
        }
    }

@app.get("/api/v1/healing/knowledge")
async def healing_knowledge():
    """Get knowledge base statistics"""
    if healing_system is None or not hasattr(healing_system, 'knowledge_base'):
        raise HTTPException(status_code=503, detail="Healing system not available")
    
    try:
        stats = await healing_system.knowledge_base.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get knowledge base stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/healing/manual_fix")
async def trigger_manual_fix(issue_type: str, issue_description: str):
    """Manually trigger healing system to fix a specific issue"""
    if healing_system is None:
        raise HTTPException(status_code=503, detail="Healing system not available")
    
    if not healing_system.running:
        raise HTTPException(status_code=503, detail="Healing system is not running")
    
    try:
        # Create manual issue
        issue = {
            'type': issue_type,
            'description': issue_description,
            'severity': 'MANUAL',
            'timestamp': time.time()
        }
        
        # Process through healing system
        await healing_system._process_issue(issue)
        
        return {
            "status": "success",
            "message": f"Manual fix triggered for {issue_type}",
            "issue": issue
        }
    except Exception as e:
        logger.error(f"Manual fix failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "OpenKore AI Service",
        "version": "1.0.0-phase11-priority1",
        "status": "online",
        "phase": "Priority 1 Combat Intelligence + Phase 11 Complete",
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
            "Social Interaction Handler (7 categories)",
            "Three-Layer Adaptive Macro System",
            "MacroHotReload Integration",
            "ML-Based Macro Prediction",
            "CrewAI Macro Generation",
            "Autonomous Self-Healing System (6 agents)",
            "Real-time Log Monitoring",
            "Intelligent Issue Detection",
            "Root Cause Analysis",
            "Adaptive Solution Generation",
            "Safe Execution with Rollback",
            "Continuous Learning from Fixes",
            "User Intent Capture System",
            "Autonomous Stat Allocation (raiseStat integration)",
            "Autonomous Skill Learning (raiseSkill integration)",
            "Adaptive Equipment Management",
            "95% Autonomy Achievement",
            "Job Build System (6 jobs, multiple builds)",
            "Playstyle Configuration (4 styles)",
            "Performance-Based Adaptation",
            "Combat Intelligence (Priority 1 - opkAI)",
            "Threat Assessment System (9-factor)",
            "Kiting Engine (5-state machine)",
            "Enhanced Target Selection (XP/zeny efficiency)",
            "Positioning Engine (5-factor scoring)"
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
            "/api/v1/social/personality",
            "/api/v1/macro/process",
            "/api/v1/macro/inject",
            "/api/v1/macro/list",
            "/api/v1/macro/stats",
            "/api/v1/macro/health",
            "/api/v1/macro/train",
            "/api/v1/macro/optimize/{macro_name}",
            "/api/v1/macro/report/{session_id}",
            "/api/v1/healing/status",
            "/api/v1/healing/knowledge",
            "/api/v1/healing/manual_fix",
            "/api/v1/progression/stats/on_level_up",
            "/api/v1/progression/stats/update_performance",
            "/api/v1/progression/stats/recommendations",
            "/api/v1/progression/skills/on_job_level_up",
            "/api/v1/progression/skills/update_combat_stats",
            "/api/v1/progression/skills/should_learn",
            "/api/v1/progression/equipment/on_map_change",
            "/api/v1/progression/equipment/on_combat_start",
            "/api/v1/progression/equipment/on_taking_damage",
            "/api/v1/progression/equipment/situation/{situation}",
            "/api/v1/progression/status",
            "/api/v1/progression/export_config",
            "/api/v1/combat/threat/assess",
            "/api/v1/combat/kiting/update",
            "/api/v1/combat/kiting/metrics",
            "/api/v1/combat/target/select",
            "/api/v1/combat/target/clear",
            "/api/v1/combat/target/metrics",
            "/api/v1/combat/positioning/optimal",
            "/api/v1/combat/status"
        ]
    }

if __name__ == "__main__":
    logger.info("OpenKore AI Service v1.0.0-phase11-priority1")
    logger.info("Starting HTTP server on http://127.0.0.1:9902")
    logger.info("Priority 1: Combat Intelligence (opkAI) + Phase 11 Complete")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=9902,
        log_level="info"
    )
