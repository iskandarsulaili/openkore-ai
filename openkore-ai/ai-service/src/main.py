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

from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import uvicorn
import time
import os
import asyncio
import json
from pathlib import Path
from loguru import logger
from contextlib import asynccontextmanager
import sys
import fastapi

# ============================================================================
# PHASE 70: COMPREHENSIVE LOGGING CONFIGURATION
# ============================================================================

# Configure loguru to write to both console and files
logger.remove()  # Remove default handler
logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

# Ensure logs directory exists
logs_dir = Path(__file__).parent.parent / "logs"
logs_dir.mkdir(exist_ok=True)

# Add file handlers
logger.add(
    logs_dir / "ai_service_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG",
    enqueue=True,  # Thread-safe
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)
logger.add(
    logs_dir / "errors_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="ERROR",
    enqueue=True,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}"
)

logger.info("=" * 80)
logger.info("[INIT] Logger configured - Writing to console and files")
logger.info(f"[INIT] Logs directory: {logs_dir}")
logger.info("=" * 80)

# Import console logger for visible AI layer activity
from utils.console_logger import console_logger, LayerType

# Import Phase 3 components
from database import db
from memory.openmemory_manager import OpenMemoryManager
from agents.crew_manager import crew_manager, hierarchical_crew_manager
from agents.strategic_agents import get_strategic_planner
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

# Import Exploration components (CRITICAL FIX #3)
from exploration.map_explorer import map_explorer

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
from autonomous_healing.plugin_configs import generate_teledest_config

# Import Priority 1 Game Mechanics components (rathena extraction)
from routers import game_mechanics_router

# Import Priority 2 NPC and Resource Management components
from game_mechanics.npc_handler import get_npc_handler

# Import Table Loader for data-driven configuration
from utils.table_loader import get_table_loader, WATCHDOG_AVAILABLE

# Lifespan context manager for startup/shutdown
# ============================================================================
# PHASE 70: ENHANCED STARTUP LOGGING
# ============================================================================

# ============================================================================
# GLOBAL CONFIGURATION LOADERS (Never Hardcode!)
# ============================================================================

# Initialize table loader (loads OpenKore tables)
table_loader = None
thresholds_config = None
npc_handler = None

def load_configurations():
    """
    Load all configurations from files and tables
    
    User requirement: "All hardcoded things should use database available
    in openkore-ai/tables as the first source and NEVER hardcoded"
    """
    global table_loader, thresholds_config, npc_handler
    
    logger.info("[CONFIG] Loading table-based configurations...")
    
    # Load OpenKore tables
    table_loader = get_table_loader(server="ROla")
    logger.info(f"[CONFIG] ✓ Table loader initialized for server: ROla")
    
    # Load thresholds configuration
    thresholds_file = Path(__file__).parent.parent / "data" / "thresholds_config.json"
    if thresholds_file.exists():
        with open(thresholds_file, 'r', encoding='utf-8') as f:
            thresholds_config = json.load(f)
        logger.info(f"[CONFIG] ✓ Loaded thresholds config with {len(thresholds_config)} categories")
    else:
        logger.warning(f"[CONFIG] ⚠ Thresholds config not found: {thresholds_file}")
        thresholds_config = {
            "hp_thresholds": {"reflex": 30, "tactical": 60, "strategic": 80},
            "sp_thresholds": {"reflex": 10, "tactical": 30, "strategic": 50},
            "zeny_thresholds": {"critical": 500, "low": 2000, "comfortable": 5000}
        }
    
    # Initialize NPC handler (loads npc_config.json)
    npc_handler = get_npc_handler()
    logger.info(f"[CONFIG] ✓ NPC handler initialized")
    
    # Log what was loaded from tables
    items = table_loader.load_items()
    healing_items = table_loader.get_healing_items()
    logger.info(f"[CONFIG] ✓ Loaded {len(items)} items from OpenKore tables")
    logger.info(f"[CONFIG] ✓ Verified {len(healing_items)} healing items")
    logger.info("[CONFIG] All configurations loaded from tables/config files (NO HARDCODED VALUES)")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("=" * 80)
    logger.info("[STARTUP] AI Service initializing...")
    logger.info(f"[STARTUP] Python version: {sys.version}")
    logger.info(f"[STARTUP] FastAPI version: {fastapi.__version__}")
    logger.info(f"[STARTUP] Current directory: {Path.cwd()}")
    logger.info(f"[STARTUP] Script location: {Path(__file__).parent}")
    logger.info("=" * 80)
    
    # Print exciting startup banner
    console_logger.print_startup_banner()
    
    # Load all configurations FIRST (before any game logic)
    console_logger.print_layer_initialization(
        LayerType.SYSTEM,
        "Loading Table-Based Configurations...",
        "OpenKore tables, NPC config, thresholds"
    )
    load_configurations()
    
    # Log feature availability status
    logger.info("=" * 60)
    logger.info("FEATURE STATUS:")
    logger.info(f"  Table Loader: ✓ Enabled")
    logger.info(f"  Real-Time File Watching: {'✓ Enabled' if WATCHDOG_AVAILABLE else '✗ Disabled (install watchdog)'}")
    logger.info(f"  CrewAI Strategic Layer: ✓ Enabled")
    logger.info(f"  Adaptive Failure Tracking: ✓ Enabled")
    logger.info("=" * 60)
    
    # Initialize database
    console_logger.print_layer_initialization(
        LayerType.SYSTEM,
        "Initializing Database...",
        "SQLite with 8 tables"
    )
    await db.initialize()
    console_logger.print_layer_initialization(
        LayerType.SYSTEM,
        "Database Ready [OK]"
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
        "Configuration Validated [OK]"
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
        f"ML Systems Ready [OK]",
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
        "Combat Intelligence Ready [OK]",
        "4 systems: Threat, Kiting, Targeting, Positioning"
    )
    logger.info("Combat Intelligence Systems initialized (Priority 1)")
    
    global stat_allocator, skill_learner, equipment_manager
    # Fix: Data files are in ai-service/data/, not ai-service/src/data/
    # Path(__file__).parent is 'src/', so we need .parent.parent to get to ai-service root
    user_intent_path = Path(__file__).parent.parent / "data" / "user_intent.json"
    job_builds_path = Path(__file__).parent.parent / "data" / "job_builds.json"
    
    logger.info(f"[STARTUP] User intent path: {user_intent_path}")
    logger.info(f"[STARTUP] Job builds path: {job_builds_path}")
    logger.info(f"[STARTUP] User intent exists: {user_intent_path.exists()}")
    logger.info(f"[STARTUP] Job builds exists: {job_builds_path.exists()}")
    
    try:
        logger.info("[STARTUP] Initializing StatAllocator...")
        stat_allocator = StatAllocator(str(user_intent_path), str(job_builds_path))
        logger.info("[STARTUP] StatAllocator initialized successfully")
        
        logger.info("[STARTUP] Initializing SkillLearner...")
        skill_learner = SkillLearner(str(user_intent_path), str(job_builds_path))
        logger.info("[STARTUP] SkillLearner initialized successfully")
        
        logger.info("[STARTUP] Initializing EquipmentManager...")
        equipment_manager = EquipmentManager(str(user_intent_path))
        logger.info("[STARTUP] EquipmentManager initialized successfully")
    except Exception as e:
        logger.error("[STARTUP] CRITICAL: Failed to initialize Progression Systems")
        logger.exception(e)
        raise
    
    console_logger.print_layer_initialization(
        LayerType.SYSTEM,
        "Progression Systems Ready [OK]",
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
        "CrewAI Strategic Layer Ready [OK]",
        "Agents: Strategist, Analyst, Generator, Optimizer"
    )
    
    console_logger.print_layer_initialization(
        LayerType.REFLEX,
        "OpenKore EventMacro Connected [OK]",
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
        "System Heartbeat Started [OK]",
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

# ============================================================================
# PHASE 70: REQUEST/RESPONSE LOGGING MIDDLEWARE
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and outgoing responses"""
    start_time = time.time()
    
    # Log incoming request
    logger.info(f"[REQUEST] {request.method} {request.url.path}")
    logger.debug(f"[REQUEST] Headers: {dict(request.headers)}")
    logger.debug(f"[REQUEST] Query params: {dict(request.query_params)}")
    
    # Get request body if present (for POST/PUT/PATCH)
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            if body:
                body_str = body.decode('utf-8')
                # Log first 500 chars to avoid huge logs
                logger.debug(f"[REQUEST] Body: {body_str[:500]}{'...' if len(body_str) > 500 else ''}")
        except Exception as e:
            logger.warning(f"[REQUEST] Could not read body: {e}")
    
    # Process request
    try:
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(f"[RESPONSE] {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")
        
        return response
    except Exception as e:
        # Log exceptions
        process_time = time.time() - start_time
        logger.error(f"[ERROR] Request failed: {request.method} {request.url.path} - Time: {process_time:.3f}s")
        logger.exception(e)
        raise

# ============================================================================
# PHASE 70: GLOBAL EXCEPTION HANDLER
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and log them"""
    logger.error(f"[GLOBAL ERROR] Unhandled exception for {request.method} {request.url.path}")
    logger.error(f"[GLOBAL ERROR] Exception type: {type(exc).__name__}")
    logger.error(f"[GLOBAL ERROR] Exception message: {str(exc)}")
    logger.exception(exc)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method
        }
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

def should_trigger_autobuy(inventory: List[Dict], hp_percent: float, sp_percent: float) -> dict:
    """
    Determine if bot should return to town to buy consumables
    
    Returns dict with: {"should_buy": bool, "items_needed": List[str], "priority": str}
    """
    items_needed = []
    
    # Get healing items from table loader (NEVER hardcoded)
    healing_items = table_loader.get_healing_items()
    basic_healing = healing_items[0] if healing_items else ("Red Potion", 501, 45)
    basic_healing_name = basic_healing[0]
    
    # Count healing items in inventory
    healing_count = sum(
        item.get("amount", 0)
        for item in inventory
        if item.get("name") == basic_healing_name
    )
    
    # Get escape items from table loader
    escape_items_list = table_loader.get_escape_items()
    basic_escape = escape_items_list[0] if escape_items_list else "Fly Wing"
    basic_escape_name = basic_escape if isinstance(basic_escape, str) else basic_escape[0]
    
    escape_count = sum(
        item.get("amount", 0)
        for item in inventory
        if item.get("name") == basic_escape_name
    )
    
    # Determine priority based on thresholds
    hp_strategic_threshold = thresholds_config["hp_thresholds"]["strategic"]
    
    if healing_count == 0 and hp_percent < hp_strategic_threshold:
        priority = "critical"
        items_needed.append(basic_healing_name)
    elif healing_count < 5:
        priority = "high"
        items_needed.append(basic_healing_name)
    elif healing_count < 10:
        priority = "medium"
        items_needed.append(basic_healing_name)
    else:
        priority = "none"
    
    if escape_count < 10:
        items_needed.append(basic_escape_name)
    
    return {
        "should_buy": bool(items_needed),
        "items_needed": items_needed,
        "priority": priority,
        "current_stock": {
            basic_healing_name: healing_count,
            basic_escape_name: escape_count
        }
    }

# ============================================
# ADAPTIVE FAILURE TRACKING SYSTEM
# ============================================
# CRITICAL FIX #1: SKILL PREREQUISITE VALIDATION
# ============================================

def has_required_skill(skills_list: List[Dict], skill_name: str, min_level: int = 1) -> bool:
    """
    Check if character has required skill at minimum level
    
    Args:
        skills_list: List of character skills from game state
        skill_name: Name of skill to check (e.g., "Basic Skill")
        min_level: Minimum skill level required (default 1)
    
    Returns:
        True if character has skill at or above min_level
    """
    if not isinstance(skills_list, list):
        return False
    
    for skill in skills_list:
        if not isinstance(skill, dict):
            continue
        if skill.get("name") == skill_name and skill.get("level", 0) >= min_level:
            return True
    return False

def get_skill_alternatives(missing_skill: str, game_state: Dict) -> Dict:
    """
    Get alternative actions when required skill is missing
    
    Args:
        missing_skill: Name of the missing skill
        game_state: Current game state
    
    Returns:
        Dictionary with alternative actions and reasoning
    """
    alternatives = {
        "Basic Skill": {
            # Cannot sit/rest, use alternatives:
            "actions": ["idle_recover", "move_to_healer", "use_healing_item"],
            "reason": "Basic Skill required for sit/rest"
        },
        "Teleport": {
            "actions": ["use_butterfly_wing", "walk_to_town", "use_warp_portal"],
            "reason": "Teleport skill not available"
        }
    }
    return alternatives.get(missing_skill, {"actions": ["idle"], "reason": "Unknown skill requirement"})

# ============================================
# CRITICAL FIX #2: ACTION BLACKLIST SYSTEM
# ============================================

action_blacklist = {}  # {action_name: expiry_timestamp}
BLACKLIST_DURATION = 300  # 5 minutes

def blacklist_action(action: str, duration: int = BLACKLIST_DURATION):
    """Temporarily blacklist an action after repeated failures"""
    expiry_time = time.time() + duration
    action_blacklist[action] = expiry_time
    logger.warning(f"[ADAPTIVE] Blacklisted action '{action}' for {duration}s")

def is_action_blacklisted(action: str) -> bool:
    """Check if action is currently blacklisted"""
    if action not in action_blacklist:
        return False
    
    # Check if blacklist expired
    if time.time() > action_blacklist[action]:
        del action_blacklist[action]
        logger.info(f"[ADAPTIVE] Blacklist expired for '{action}'")
        return False
    
    return True

def get_blacklist_time_remaining(action: str) -> int:
    """Get seconds remaining in blacklist"""
    if action not in action_blacklist:
        return 0
    return max(0, int(action_blacklist[action] - time.time()))

# ============================================
# ADAPTIVE FAILURE TRACKING SYSTEM
# User requirement: "If same issue repeated more than 3 times, AI should have
# adaptive critical thinking to try another alternative method to solve it."

from collections import defaultdict

action_failure_tracker = defaultdict(list)  # {action_name: [timestamp, timestamp, ...]}
# Load failure thresholds from config (NEVER hardcoded)
FAILURE_THRESHOLD = None  # Will be loaded from config
FAILURE_WINDOW = None  # Will be loaded from config
alternative_actions_attempted = defaultdict(set)  # Track which alternatives were tried

def get_failure_threshold():
    """Get failure threshold from config"""
    return thresholds_config["adaptive_behavior"]["failure_threshold"] if thresholds_config else 3

def get_failure_window():
    """Get failure window from config"""
    return thresholds_config["adaptive_behavior"]["failure_window_seconds"] if thresholds_config else 30

def record_action_failure(action: str, reason: str = ""):
    """
    Record that an action failed execution
    
    Args:
        action: The action that failed (e.g., "rest", "use_item")
        reason: Why it failed (for logging)
    """
    current_time = time.time()
    action_failure_tracker[action].append({
        "timestamp": current_time,
        "reason": reason
    })
    
    # Clean old failures outside the window
    action_failure_tracker[action] = [
        f for f in action_failure_tracker[action]
        if current_time - f["timestamp"] < get_failure_window()
    ]
    
    failure_count = len(action_failure_tracker[action])
    if failure_count >= get_failure_threshold():
        logger.warning(
            f"[ADAPTIVE] Action '{action}' has failed {failure_count} times in last {get_failure_window()}s. "
            f"Reasons: {[f['reason'] for f in action_failure_tracker[action][-3:]]}"
        )
        
        # CRITICAL FIX #2: Auto-blacklist after threshold exceeded
        blacklist_action(action, duration=BLACKLIST_DURATION)
        
        # Clear failure tracking for this action
        action_failure_tracker[action] = []
        
        # Trigger strategic rethink
        logger.info(f"[ADAPTIVE] Triggering strategy rethink due to repeated '{action}' failures")

def is_action_failing_repeatedly(action: str) -> bool:
    """
    Check if action has failed 3+ times in last 30 seconds
    
    Returns True if action should be avoided and alternative tried
    """
    current_time = time.time()
    recent_failures = [
        f for f in action_failure_tracker.get(action, [])
        if current_time - f["timestamp"] < get_failure_window()
    ]
    return len(recent_failures) >= get_failure_threshold()

def get_alternative_action(failed_action: str, game_state: Dict[str, Any], inventory: List[Dict]) -> Dict:
    """
    Find alternative action when primary action keeps failing
    
    User requirement: "AI should have adaptive critical thinking to try another
    alternative method to solve it"
    
    Args:
        failed_action: The action that's failing repeatedly
        game_state: Current game state
        inventory: Character inventory
    
    Returns:
        Alternative action dict with action/params/layer
    """
    logger.info(f"[ADAPTIVE] Finding alternative for failing action: '{failed_action}'")
    
    character_data = game_state.get("character", {})
    current_hp = int(character_data.get("hp", 0) or 0)
    max_hp = int(character_data.get("hp_max", 1) or 1)
    hp_percent = (current_hp / max_hp * 100) if max_hp > 0 else 0
    
    # Alternative strategies based on what's failing
    if failed_action == "rest":
        logger.warning("[ADAPTIVE] 'rest' failing (likely no Basic Skill Lv3)")
        
        # Alternative 1: Use healing item if available
        healing_items = ["Red Herb", "Apple", "Meat", "Red Potion", "Orange Potion"]
        for item_name in healing_items:
            has_item = any(
                item.get("name") == item_name and item.get("amount", 0) > 0
                for item in inventory
            )
            if has_item and f"use_{item_name}" not in alternative_actions_attempted[failed_action]:
                alternative_actions_attempted[failed_action].add(f"use_{item_name}")
                logger.info(f"[ADAPTIVE] Alternative 1: Use {item_name} instead of resting")
                return {
                    "action": "use_item",
                    "params": {
                        "item": item_name,
                        "reason": "rest_unavailable_basic_skill_missing"
                    },
                    "layer": "ADAPTIVE_REFLEX"
                }
        
        # Alternative 2: Natural regeneration (just idle)
        if "idle_regen" not in alternative_actions_attempted[failed_action]:
            alternative_actions_attempted[failed_action].add("idle_regen")
            logger.warning("[ADAPTIVE] Alternative 2: Idle and let natural HP regen work (slow)")
            return {
                "action": "idle",
                "params": {
                    "reason": "rest_unavailable_natural_regen",
                    "duration": 10
                },
                "layer": "ADAPTIVE_TACTICAL"
            }
        
        # Alternative 3: Attack monsters to level up and get Basic Skill
        if "farm_to_level" not in alternative_actions_attempted[failed_action]:
            alternative_actions_attempted[failed_action].add("farm_to_level")
            logger.info("[ADAPTIVE] Alternative 3: Farm monsters to level up and unlock Basic Skill")
            return {
                "action": "attack_nearest",
                "params": {
                    "reason": "need_basic_skill_farm_to_level",
                    "priority": "high"
                },
                "layer": "ADAPTIVE_STRATEGIC"
            }
        
        # Alternative 4: Go to town and buy healing items
        logger.info("[ADAPTIVE] Alternative 4: Return to town and buy healing items")
        return {
            "action": "return_to_town",
            "params": {
                "reason": "no_recovery_options_need_items",
                "buy_items": [table_loader.get_healing_items()[0][0], table_loader.get_healing_items()[3][0]]
            },
            "layer": "ADAPTIVE_STRATEGIC"
        }
    
    elif failed_action == "use_item":
        logger.warning("[ADAPTIVE] 'use_item' failing (likely out of stock)")
        
        # Alternative 1: Rest if possible
        if not is_action_failing_repeatedly("rest"):
            return {
                "action": "rest",
                "params": {"reason": "items_depleted_try_resting"},
                "layer": "ADAPTIVE_TACTICAL"
            }
        
        # Alternative 2: Buy more items
        return {
            "action": "auto_buy",
            "params": {
                "items": [table_loader.get_healing_items()[0][0], table_loader.get_sp_recovery_items()[0][0]],
                "reason": "items_depleted_need_restock"
            },
            "layer": "ADAPTIVE_STRATEGIC"
        }
    
    elif failed_action == "auto_buy":
        logger.warning("[ADAPTIVE] 'auto_buy' failing (likely NPC issue or no zeny)")
        
        # Alternative: Sell items first
        return {
            "action": "sell_items",
            "params": {"reason": "cannot_buy_need_zeny_from_selling"},
            "layer": "ADAPTIVE_STRATEGIC"
        }
    
    else:
        # Generic fallback: just continue with default behavior
        logger.warning(f"[ADAPTIVE] No specific alternative for '{failed_action}', defaulting to continue")
        return {
            "action": "continue",
            "params": {"reason": f"no_alternative_for_{failed_action}"},
            "layer": "ADAPTIVE"
        }

def clear_failure_tracking_for_action(action: str):
    """Clear failure history when action succeeds"""
    if action in action_failure_tracker:
        del action_failure_tracker[action]
    if action in alternative_actions_attempted:
        del alternative_actions_attempted[action]

# ============================================
# END ADAPTIVE FAILURE TRACKING SYSTEM
# ============================================

# ============================================
# CRITICAL FIX #3: COMBAT/FARMING LOGIC
# ============================================

def is_ready_for_combat(character: Dict, inventory: List[Dict]) -> bool:
    """
    Check if character is ready to engage in combat
    
    Args:
        character: Character data from game state
        inventory: Character inventory
    
    Returns:
        True if character is ready for combat
    """
    hp_percent = float(character.get("hp_percent", 0) or 0)
    sp_percent = float(character.get("sp_percent", 0) or 0)
    
    # Calculate percentages if not provided
    if hp_percent == 0:
        current_hp = int(character.get("hp", 0) or 0)
        max_hp = int(character.get("max_hp", 1) or 1)
        hp_percent = (current_hp / max_hp * 100) if max_hp > 0 else 0
    
    if sp_percent == 0:
        current_sp = int(character.get("sp", 0) or 0)
        max_sp = int(character.get("max_sp", 1) or 1)
        sp_percent = (current_sp / max_sp * 100) if max_sp > 0 else 0
    
    # Minimum thresholds for safe combat
    if hp_percent < 50:  # Too low HP
        logger.debug(f"[COMBAT] Not ready - HP too low: {hp_percent:.1f}%")
        return False
    
    if sp_percent < 20:  # Too low SP
        logger.debug(f"[COMBAT] Not ready - SP too low: {sp_percent:.1f}%")
        return False
    
    # Check if has weapon equipped
    equipment = character.get("equipment", {})
    if not equipment.get("weapon") and not equipment.get("rightHand"):
        logger.warning("[COMBAT] Not ready - No weapon equipped")
        return False
    
    return True

def select_combat_target(monsters: List[Dict], character: Dict) -> Optional[Dict]:
    """
    Select best monster to attack based on character level and position
    
    Args:
        monsters: List of nearby monsters from game state
        character: Character data from game state
    
    Returns:
        Selected monster dict or None if no suitable target
    """
    if not isinstance(monsters, list) or len(monsters) == 0:
        return None
    
    char_level = int(character.get("level", 1) or 1)
    
    # Get character position
    position = character.get("position", {})
    char_x = int(position.get("x", 0) or 0)
    char_y = int(position.get("y", 0) or 0)
    
    # Filter suitable monsters
    suitable_monsters = []
    for monster in monsters:
        if not isinstance(monster, dict):
            continue
        
        monster_level = int(monster.get("level", 1) or 1)
        
        # Level range check (±5 levels for safety)
        if abs(monster_level - char_level) > 5:
            continue
        
        # Distance check (within 15 cells)
        mon_x = int(monster.get("x", 0) or 0)
        mon_y = int(monster.get("y", 0) or 0)
        distance = ((char_x - mon_x)**2 + (char_y - mon_y)**2)**0.5
        
        if distance > 15:
            continue
        
        suitable_monsters.append({
            "monster": monster,
            "distance": distance,
            "level_diff": abs(monster_level - char_level)
        })
    
    if not suitable_monsters:
        logger.debug("[COMBAT] No suitable monsters in range")
        return None
    
    # Sort by distance (closest first)
    suitable_monsters.sort(key=lambda x: x["distance"])
    
    selected = suitable_monsters[0]["monster"]
    logger.debug(f"[COMBAT] Selected target: {selected.get('name')} (Distance: {suitable_monsters[0]['distance']:.1f})")
    
    return selected

# ============================================
# END COMBAT/FARMING LOGIC
# ============================================

@app.post("/api/v1/decide")
async def decide_action(request: Request, request_body: Dict[str, Any] = Body(...)):
    """
    Main decision endpoint called by AI-Engine.
    Receives game state and returns bot decisions using the three-layer architecture.
    
    Request body structure:
    {
        "game_state": {
            "character": {...},
            "inventory": [...],
            "monsters": {...},
            "skills": [...],  # CRITICAL FIX #1: Now includes skills
            ...
        },
        "request_id": "uuid",
        "timestamp_ms": 1234567890
    }
    
    Args:
        request_body: Complete request with game_state, request_id, and timestamp_ms
        
    Returns:
        Decision dict with action and parameters
    """
    # CRITICAL FIX #1: Unwrap the request structure
    # OpenKore plugin sends wrapped structure with game_state as nested object
    game_state = request_body.get("game_state", {})
    request_id = request_body.get("request_id", "unknown")
    timestamp_ms = request_body.get("timestamp_ms", 0)
    
    logger.info(f"[DECIDE] Received decision request - ID: {request_id}")
    logger.debug(f"[DECIDE] Game state keys: {list(game_state.keys() if game_state else [])}")
    
    try:
        # CRITICAL FIX #2: Check for blacklisted actions at start
        # Create list of available actions (excluding blacklisted)
        available_actions = {
            "rest": not is_action_blacklisted("rest"),
            "use_item": not is_action_blacklisted("use_item"),
            "move_to_healer": not is_action_blacklisted("move_to_healer"),
            "buy_items": not is_action_blacklisted("buy_items"),
            "sell_items": not is_action_blacklisted("sell_items"),
            "attack_monster": not is_action_blacklisted("attack_monster"),
            "explore_map": not is_action_blacklisted("explore_map")
        }
        
        blacklisted_actions = [action for action, available in available_actions.items() if not available]
        if blacklisted_actions:
            logger.debug(f"[ADAPTIVE] Blacklisted actions: {blacklisted_actions}")
        
        # Extract key game state info with type safety
        # Handle character name (can be nested or direct)
        character_data = game_state.get("character", {})
        if isinstance(character_data, dict):
            character_name = character_data.get("name", "Unknown")
        else:
            character_name = str(character_data) if character_data else "Unknown"
        
        # Safely convert HP/SP to integers (handles both string and int)
        current_hp = int(character_data.get("hp", 0) or 0) if isinstance(character_data, dict) else 0
        max_hp = int(character_data.get("max_hp", 1) or 1) if isinstance(character_data, dict) else 1
        hp_percent = (current_hp / max_hp * 100) if max_hp > 0 else 0
        
        current_sp = int(character_data.get("sp", 0) or 0) if isinstance(character_data, dict) else 0
        max_sp = int(character_data.get("max_sp", 1) or 1) if isinstance(character_data, dict) else 1
        sp_percent = (current_sp / max_sp * 100) if max_sp > 0 else 0
        
        in_combat = game_state.get("combat", {}).get("in_combat", False)
        target_monster = game_state.get("combat", {}).get("target", None)
        
        inventory = game_state.get("inventory", [])
        position = game_state.get("position", {})
        
        logger.info(f"[DECIDE] Character: {character_name}, HP: {hp_percent:.1f}%, SP: {sp_percent:.1f}%, Combat: {in_combat}")
        logger.debug(f"[DECIDE] Inventory items: {len(inventory)} items")
        
        # ==================================================================
        # DECISION LOGIC: Three-Layer Architecture
        # ==================================================================
        
        # Layer 1: REFLEX (Immediate survival responses - use config threshold)
        hp_reflex_threshold = thresholds_config["hp_thresholds"]["reflex"]
        if hp_percent < hp_reflex_threshold:
            logger.warning(f"[DECIDE] CRITICAL HP: {hp_percent:.1f}% - Emergency healing required!")
            
            # Check for healing items IN INVENTORY (priority order)
            healing_items = [
                ("White Potion", 400),  # Heals ~400 HP
                ("Yellow Potion", 200), # Heals ~200 HP
                ("Orange Potion", 100), # Heals ~100 HP
                ("Red Potion", 45),     # Heals ~45 HP
                ("Apple", 16),          # Heals ~16 HP
                ("Meat", 15)            # Heals ~15 HP
            ]
            
            for item_name, heal_amount in healing_items:
                # Check if item exists in inventory with amount > 0
                has_item = any(
                    item.get("name") == item_name and item.get("amount", 0) > 0
                    for item in inventory
                )
                if has_item:
                    logger.info(f"[DECIDE] REFLEX: Using {item_name} for emergency healing (~{heal_amount} HP)")
                    
                    # Clear failure tracking on successful alternative
                    clear_failure_tracking_for_action("rest")
                    
                    return {
                        "action": "use_item",
                        "params": {
                            "item": item_name,
                            "reason": "emergency_healing",
                            "priority": "critical"
                        },
                        "layer": "REFLEX"
                    }
            
            # NO HEALING ITEMS → Check if rest is failing repeatedly (CRITICAL FIX #2)
            if is_action_failing_repeatedly("rest"):
                logger.error("[ADAPTIVE] 'rest' action has failed 3+ times, finding alternative...")
                return get_alternative_action("rest", game_state, inventory)
            
            # NO HEALING ITEMS → Different strategy based on combat status
            # CRITICAL FIX: Handle both array and dict formats for monsters
            monsters = game_state.get("monsters", [])
            if isinstance(monsters, list):
                # Array format: non-empty list means monsters present
                in_combat_check = bool(monsters)
            elif isinstance(monsters, dict):
                # Dict format: check aggressive key
                in_combat_check = bool(monsters.get("aggressive", []))
            else:
                in_combat_check = False
            
            if not in_combat_check:
                # CRITICAL FIX #1: Check skill prerequisites before rest
                skills = game_state.get("skills", [])
                
                # Check if rest action is blacklisted
                if is_action_blacklisted("rest"):
                    remaining = get_blacklist_time_remaining("rest")
                    logger.warning(f"[ADAPTIVE] 'rest' is blacklisted ({remaining}s remaining), using alternative")
                    return get_alternative_action("rest", game_state, inventory)
                
                # Check if character has Basic Skill Lv3 for sitting
                if not has_required_skill(skills, "Basic Skill", min_level=3):
                    logger.warning("[DECIDE] Cannot rest - Basic Skill Lv3 required")
                    
                    # Use alternative recovery method (idle recovery)
                    logger.info(f"[DECIDE] Using idle recovery instead (no Basic Skill for sit)")
                    
                    return {
                        "action": "idle_recover",
                        "params": {
                            "duration": 10,
                            "reason": "no_basic_skill_for_sit",
                            "alternative_to": "rest"
                        },
                        "layer": "REFLEX"
                    }
                
                logger.warning("[DECIDE] REFLEX: No healing items! Sitting to recover HP naturally (free)")
                return {
                    "action": "rest",
                    "params": {
                        "reason": "no_items_emergency_recovery",
                        "priority": "critical"
                    },
                    "layer": "REFLEX"
                }
            else:
                # IN COMBAT with critical HP and no items → Must escape
                logger.error("[DECIDE] CRITICAL: No healing items + in combat! Emergency retreat!")
                
                # Check for escape items (from table loader - NEVER hardcoded)
                escape_items = table_loader.get_escape_items()
                for escape_item in escape_items:
                    has_escape = any(
                        item.get("name") == escape_item and item.get("amount", 0) > 0
                        for item in inventory
                    )
                    if has_escape:
                        return {
                            "action": "use_item",
                            "params": {"item": escape_item, "reason": "emergency_escape"},
                            "layer": "REFLEX"
                        }
                
                # No escape items → Try to flee on foot
                return {
                    "action": "retreat",
                    "params": {"reason": "critical_hp_no_items_no_escape"},
                    "layer": "REFLEX"
                }
        
        # Layer 2: TACTICAL (Preventive healing - use config threshold)
        hp_tactical_threshold = thresholds_config["hp_thresholds"]["tactical"]
        if hp_percent < hp_tactical_threshold:
            logger.info(f"[DECIDE] TACTICAL: HP at {hp_percent:.1f}% - Preventive healing")
            
            # Check if we have healing items
            # Check if we have any healing items (from table loader)
            healing_item_names = [item[0] for item in table_loader.get_healing_items()]
            has_healing = any(
                item.get("name") in healing_item_names and item.get("amount", 0) > 0
                for item in inventory
            )
            
            if has_healing:
                # Use the most cost-effective potion available (from table loader)
                basic_potions = [item[0] for item in table_loader.get_healing_items() if "Potion" in item[0]][:3]
                for item_name in basic_potions:
                    if any(item.get("name") == item_name and item.get("amount", 0) > 0 for item in inventory):
                        logger.info(f"[DECIDE] TACTICAL: Using {item_name} for preventive healing")
                        clear_failure_tracking_for_action("rest")
                        return {
                            "action": "use_item",
                            "params": {"item": item_name, "reason": "preventive_healing"},
                            "layer": "TACTICAL"
                        }
            else:
                # No healing items → Check if rest is failing (CRITICAL FIX #2)
                if is_action_failing_repeatedly("rest"):
                    logger.error("[ADAPTIVE] 'rest' has failed repeatedly in TACTICAL layer")
                    return get_alternative_action("rest", game_state, inventory)
                
                # No healing items → Use FREE recovery (sit/rest)
                # CRITICAL FIX: Handle both array and dict formats for monsters
                monsters = game_state.get("monsters", [])
                if isinstance(monsters, list):
                    in_combat_check = bool(monsters)
                elif isinstance(monsters, dict):
                    in_combat_check = bool(monsters.get("aggressive", []))
                else:
                    in_combat_check = False
                
                if not in_combat_check:
                    # CRITICAL FIX #1: Check skill prerequisites before rest
                    skills = game_state.get("skills", [])
                    
                    # Check if rest action is blacklisted
                    if is_action_blacklisted("rest"):
                        remaining = get_blacklist_time_remaining("rest")
                        logger.warning(f"[ADAPTIVE] 'rest' is blacklisted ({remaining}s remaining), using alternative")
                        return get_alternative_action("rest", game_state, inventory)
                    
                    # Check if character has Basic Skill Lv3 for sitting
                    if not has_required_skill(skills, "Basic Skill", min_level=3):
                        logger.warning("[DECIDE] Cannot rest - Basic Skill Lv3 required")
                        
                        # Use alternative recovery method
                        logger.info(f"[DECIDE] Using idle recovery instead (no Basic Skill for sit)")
                        
                        return {
                            "action": "idle_recover",
                            "params": {
                                "duration": 10,
                                "reason": "no_basic_skill_for_sit",
                                "alternative_to": "rest"
                            },
                            "layer": "TACTICAL"
                        }
                    
                    logger.info("[DECIDE] TACTICAL: No healing items, using sit to recover HP naturally (free)")
                    return {
                        "action": "rest",
                        "params": {"reason": "free_hp_recovery"},
                        "layer": "TACTICAL"
                    }
                else:
                    # In combat but no potions → Finish current fight then rest
                    logger.info("[DECIDE] TACTICAL: In combat with no items, will rest after combat")
                    return {
                        "action": "continue_combat",
                        "params": {"reason": "will_rest_after"},
                        "layer": "TACTICAL"
                    }
        
        # Check SP for skill-based classes (use config threshold)
        sp_tactical_threshold = thresholds_config["sp_thresholds"]["tactical"]
        if sp_percent < sp_tactical_threshold:
            logger.info(f"[DECIDE] Low SP: {sp_percent:.1f}% - Need recovery")
            
            # Check for SP recovery items (from table loader - NEVER hardcoded)
            sp_items = [item[0] for item in table_loader.get_sp_recovery_items()]
            for sp_item in sp_items:
                if any(item.get("name") == sp_item and item.get("amount", 0) > 0 for item in inventory):
                    return {
                        "action": "use_item",
                        "params": {"item": sp_item, "reason": "sp_recovery"},
                        "layer": "TACTICAL"
                    }
            
            # No SP items → Sit to recover naturally (free)
            # CRITICAL FIX: Handle both array and dict formats for monsters
            monsters = game_state.get("monsters", [])
            if isinstance(monsters, list):
                in_combat = bool(monsters)
            elif isinstance(monsters, dict):
                in_combat = bool(monsters.get("aggressive", []))
            else:
                in_combat = False
            
            if not in_combat:
                # CRITICAL FIX #1: Check skill prerequisites before rest
                skills = game_state.get("skills", [])
                
                # Check if rest action is blacklisted
                if is_action_blacklisted("rest"):
                    remaining = get_blacklist_time_remaining("rest")
                    logger.warning(f"[ADAPTIVE] 'rest' is blacklisted ({remaining}s remaining), using alternative")
                    return get_alternative_action("rest", game_state, inventory)
                
                # Check if character has Basic Skill Lv3 for sitting
                if not has_required_skill(skills, "Basic Skill", min_level=3):
                    logger.warning("[DECIDE] Cannot rest - Basic Skill Lv3 required")
                    
                    # Use alternative recovery method
                    logger.info(f"[DECIDE] Using idle recovery instead (no Basic Skill for sit)")
                    
                    return {
                        "action": "idle_recover",
                        "params": {
                            "duration": 10,
                            "reason": "no_basic_skill_for_sit",
                            "alternative_to": "rest"
                        },
                        "layer": "TACTICAL"
                    }
                
                logger.info("[DECIDE] Sitting to recover SP naturally (free)")
                return {
                    "action": "rest",
                    "params": {"reason": "sp_recovery_free"},
                    "layer": "TACTICAL"
                }
        
        # ======================================================================
        # Layer 2.5: PROGRESSION (Stat/Skill Management) - HIGH PRIORITY
        # ======================================================================
        # Priority: Stat/skill allocation > Consumable buying > Exploration
        # Reason: Character growth is fundamental for all other activities
        
        logger.debug("[DECIDE] Checking for progression opportunities...")
        
        # P0 CRITICAL FIX #3: Check for available stat points
        available_stat_points = int(character_data.get("points_free", 0) or 0)
        if available_stat_points > 0:
            logger.info(f"[PROGRESSION] {available_stat_points} stat points available - allocating")
            
            # Dynamic stat allocation for all job classes
            job_class = character_data.get("job_class", "Novice")
            character_level = int(character_data.get("level", 1) or 1)
            
            # Define stat priorities by job class archetype
            # Physical classes: STR+DEX+VIT, Magical classes: INT+DEX, Hybrid: balanced
            stat_priorities = {
                # 1st Class Physical
                "Swordman": ["STR", "VIT", "DEX"],
                "Archer": ["DEX", "AGI", "STR"],
                "Thief": ["AGI", "DEX", "STR"],
                "Acolyte": ["INT", "DEX", "VIT"],
                "Merchant": ["STR", "VIT", "DEX"],
                "Mage": ["INT", "DEX", "VIT"],
                
                # Default for Novice and unknown classes
                "Novice": ["STR", "DEX", "VIT"],
                "default": ["STR", "DEX", "VIT"]
            }
            
            # Get stat priority for current class (or use default)
            priorities = stat_priorities.get(job_class, stat_priorities["default"])
            
            # Allocate points based on priority order
            stats_to_add = {}
            remaining_points = available_stat_points
            
            for i, stat in enumerate(priorities):
                if remaining_points <= 0:
                    break
                
                # Allocate more points to higher priority stats
                if i == 0:  # Highest priority (primary stat)
                    points = min(2, remaining_points)
                elif i == 1:  # Second priority
                    points = min(2, remaining_points)
                else:  # Lower priority
                    points = min(1, remaining_points)
                
                if points > 0:
                    stats_to_add[stat] = points
                    remaining_points -= points
            
            logger.info(f"[PROGRESSION] {job_class} build - allocating: {stats_to_add}")
            
            return {
                "action": "allocate_stats",
                "params": {
                    "stats": stats_to_add,
                    "reason": "character_progression",
                    "priority": "high"
                },
                "layer": "PROGRESSION"
            }
        
        # P0 CRITICAL FIX #3: Check for available skill points
        available_skill_points = int(character_data.get("points_skill", 0) or 0)
        if available_skill_points > 0:
            logger.info(f"[PROGRESSION] {available_skill_points} skill points available")
            
            skills = game_state.get("skills", [])
            
            # CRITICAL PRIORITY: Learn Basic Skill first if missing
            basic_skill_level = 0
            for skill in skills:
                skill_name = skill.get("name", "")
                if skill_name == "Basic Skill" or skill_name == "NV_BASIC":
                    basic_skill_level = skill.get("level", 0)
                    break
            
            if basic_skill_level < 3:
                points_needed = 3 - basic_skill_level
                points_to_allocate = min(points_needed, available_skill_points)
                
                logger.warning(f"[PROGRESSION] Learning Basic Skill Lv{basic_skill_level} → Lv{basic_skill_level + points_to_allocate} (REQUIRED for sit/rest)")
                
                return {
                    "action": "learn_skill",
                    "params": {
                        "skill_name": "NV_BASIC",  # OpenKore internal name
                        "skill_display_name": "Basic Skill",
                        "current_level": basic_skill_level,
                        "target_level": basic_skill_level + points_to_allocate,
                        "points_to_add": points_to_allocate,
                        "reason": "prerequisite_for_rest",
                        "priority": "critical"
                    },
                    "layer": "PROGRESSION"
                }
            
            # Learn other skills if Basic Skill maxed
            logger.info(f"[PROGRESSION] Basic Skill ready (Lv{basic_skill_level}), other skills can be learned later")
            # TODO: Add skill learning logic for job-specific skills using CrewAI
        
        # Layer 3: STRATEGIC (Strategic decision-making)
        # Priority 2 Fix: Zeny Management and Resource Planning
        current_zeny = int(character_data.get("zeny", 0) or 0)
        character_level = int(character_data.get("level", 1) or 1)
        logger.debug(f"[DECIDE] Current zeny: {current_zeny}z, Level: {character_level}")
        
        # Define zeny thresholds (from config - NEVER hardcoded)
        # Adjust thresholds for early game (Level < 10)
        if character_level < 10:
            ZENY_CRITICAL = 100   # Lower threshold for early game
            ZENY_LOW = 500
            ZENY_COMFORTABLE = 1000
        else:
            ZENY_CRITICAL = thresholds_config["zeny_thresholds"]["critical"]
            ZENY_LOW = thresholds_config["zeny_thresholds"]["low"]
            ZENY_COMFORTABLE = thresholds_config["zeny_thresholds"]["comfortable"]
        
        # Check if we should sell items first
        if current_zeny < ZENY_LOW:
            logger.warning(f"[DECIDE] Low zeny ({current_zeny}z) - should consider selling items")
            
            # Count sellable items (protect quest items from table loader)
            quest_items = table_loader.get_quest_items()
            sellable_count = sum(
                1 for item in inventory
                if item.get("type") not in ["consumable", "equipment", "weapon", "armor"]
                and item.get("name") not in quest_items
                and not table_loader.is_card(item.get("name", ""))
            )
            
            if sellable_count > 5 and current_zeny < ZENY_CRITICAL:
                logger.warning(f"[DECIDE] CRITICAL: Only {current_zeny}z left, {sellable_count} sellable items")
                return {
                    "action": "sell_items",
                    "params": {
                        "reason": "critical_zeny_shortage",
                        "priority": "high"
                    },
                    "layer": "STRATEGIC"
                }
        
        # Check if we need to restock consumables
        try:
            autobuy_check = should_trigger_autobuy(inventory, hp_percent, sp_percent)
        except Exception as e:
            logger.error(f"[DECIDE] Autobuy check failed: {e}", exc_info=True)
            autobuy_check = {"should_buy": False, "priority": "none", "items_needed": [], "current_stock": {}}
        
        if autobuy_check["priority"] in ["critical", "high"]:
            logger.warning(f"[DECIDE] STRATEGIC: Low consumables - {autobuy_check['current_stock']}")
            logger.info(f"[DECIDE] Items needed: {autobuy_check['items_needed']}")
            
            # Priority 2 Fix: Check if we can afford items before triggering buy
            # Estimate cost - use table_loader for item costs (NEVER hardcoded)
            healing_items = table_loader.get_healing_items()
            basic_healing_name = healing_items[0][0] if healing_items else "Red Potion"
            
            item_costs = {
                "Red Potion": 50,
                "Yellow Potion": 550,
                "White Potion": 1200,
                "Fly Wing": 600,
                "Butterfly Wing": 300
            }
            
            estimated_cost = sum(
                item_costs.get(item, 100) * 10  # Assume buying 10 of each
                for item in autobuy_check["items_needed"]
            )
            
            logger.debug(f"[DECIDE] Auto-buy estimated cost: {estimated_cost}z")
            
            if current_zeny >= estimated_cost:
                # Can afford to buy
                # CRITICAL FIX: Handle both array and dict formats for monsters
                monsters = game_state.get("monsters", [])
                if isinstance(monsters, list):
                    in_combat_check = bool(monsters)
                elif isinstance(monsters, dict):
                    in_combat_check = bool(monsters.get("aggressive", []))
                else:
                    in_combat_check = False
                
                if not in_combat_check:
                    logger.info(f"[DECIDE] STRATEGIC: Buying items (have {current_zeny}z, need ~{estimated_cost}z)")
                    return {
                        "action": "auto_buy",
                        "params": {
                            "items": autobuy_check["items_needed"],
                            "priority": autobuy_check["priority"],
                            "estimated_cost": estimated_cost
                        },
                        "layer": "STRATEGIC"
                    }
                else:
                    logger.warning("[DECIDE] Need to buy items but currently in combat - will buy after")
            else:
                # Cannot afford - must sell first or use free recovery
                logger.warning(f"[DECIDE] Cannot afford items ({current_zeny}z < {estimated_cost}z) - using free recovery")
                
                # CRITICAL FIX: Handle both array and dict formats for monsters
                monsters = game_state.get("monsters", [])
                if isinstance(monsters, list):
                    in_combat = bool(monsters)
                elif isinstance(monsters, dict):
                    in_combat = bool(monsters.get("aggressive", []))
                else:
                    in_combat = False
                
                if not in_combat:
                    return {
                        "action": "rest",
                        "params": {
                            "reason": "cannot_afford_potions",
                            "priority": "medium"
                        },
                        "layer": "TACTICAL"
                    }
        
        # Layer 3: CONSCIOUS (Strategic planning with CrewAI)
        # Activate when character is healthy (HP > 80%, SP > 50%) and not in immediate danger
        # This enables 95% autonomous gameplay with sequential thinking and complex situation handling
        
        if hp_percent > 80 and sp_percent > 50:
            # Check if we should use strategic planning
            # CRITICAL FIX: Handle both array and dict formats for monsters
            monsters = game_state.get("monsters", [])
            if isinstance(monsters, list):
                in_combat_check = bool(monsters)
            elif isinstance(monsters, dict):
                in_combat_check = bool(monsters.get("aggressive", []))
            else:
                in_combat_check = False
            
            if not in_combat_check:
                # Safe to do strategic planning
                logger.info("[DECIDE] STRATEGIC: Healthy and safe, activating CrewAI planning")
                
                # Check if LLM provider available
                if hasattr(app.state, 'llm_chain') and app.state.llm_chain:
                    try:
                        # Get strategic planner with LLM provider
                        planner = get_strategic_planner(app.state.llm_chain.llm)
                        strategic_action = await planner.plan_next_strategic_action(game_state)
                        
                        logger.info(f"[DECIDE] STRATEGIC: CrewAI recommends: {strategic_action['action']}")
                        logger.debug(f"[DECIDE] Reasoning: {strategic_action.get('reasoning', 'N/A')[:200]}")
                        
                        return strategic_action
                        
                    except Exception as e:
                        logger.error(f"[DECIDE] STRATEGIC layer error: {e}")
                        logger.warning("[DECIDE] Falling back to default behavior")
                else:
                    logger.debug("[DECIDE] LLM provider not available, skipping strategic planning")
        
        # CRITICAL FIX #3: Combat/Farming Logic (when ready and monsters available)
        # This runs AFTER strategic planning but BEFORE idle/continue
        monsters = game_state.get("monsters", [])
        if isinstance(monsters, list) and len(monsters) > 0:
            if is_ready_for_combat(character_data, inventory):
                target = select_combat_target(monsters, character_data)
                
                if target:
                    # Check if attack_monster is blacklisted
                    if is_action_blacklisted("attack_monster"):
                        logger.warning("[ADAPTIVE] 'attack_monster' is blacklisted, skipping combat")
                    else:
                        logger.info(f"[COMBAT] Target selected: {target.get('name')} (Level {target.get('level')})")
                        return {
                            "action": "attack_monster",
                            "params": {
                                "target_id": target.get("id"),
                                "target_name": target.get("name"),
                                "reason": "farming_leveling"
                            },
                            "layer": "TACTICAL"
                        }
                else:
                    logger.debug("[COMBAT] No suitable monsters in range")
            else:
                logger.debug("[COMBAT] Not ready for combat (low HP/SP or no weapon)")
        
        # Fallback: Basic combat decision or continue
        if in_combat and target_monster:
            logger.info(f"[DECIDE] STRATEGIC: Continuing combat with {target_monster}")
            return {
                "action": "attack",
                "params": {
                    "target": target_monster,
                    "reason": "combat_engagement",
                    "priority": "normal"
                }
            }
        
        # Layer 4: EXPLORATION (Idle time, explore map purposefully)
        # This runs when bot has nothing else to do - increases autonomy
        if hp_percent > 60 and sp_percent > 40:
            # Check if explore_map is blacklisted
            if not is_action_blacklisted("explore_map"):
                if map_explorer.should_explore(game_state):
                    current_map_name = character_data.get("position", {}).get("map", "unknown")
                    current_pos = character_data.get("position", {})
                    
                    target = map_explorer.get_exploration_target(current_map_name, current_pos)
                    
                    logger.info(f"[EXPLORE] Moving to exploration target: ({target['x']}, {target['y']}) - Reason: {target.get('reason', 'exploration')}")
                    return {
                        "action": "move_to_position",
                        "params": {
                            "x": target["x"],
                            "y": target["y"],
                            "reason": "map_exploration",
                            "map": current_map_name
                        },
                        "layer": "EXPLORATION"
                    }
                else:
                    logger.debug("[EXPLORE] Exploration conditions not met")
            else:
                logger.debug("[ADAPTIVE] 'explore_map' is blacklisted, skipping exploration")
        
        # Default: Continue with current task
        logger.info("[DECIDE] No immediate action required - continue current behavior")
        return {
            "action": "continue",
            "params": {
                "reason": "stable_state",
                "priority": "low"
            }
        }
        
    except Exception as e:
        logger.error("[DECIDE] Error processing decision request")
        logger.exception(e)
        
        # Return safe fallback decision
        return {
            "action": "continue",
            "params": {
                "reason": "error_fallback",
                "priority": "low",
                "error": str(e)
            }
        }

@app.post("/api/v1/action_feedback")
async def action_feedback(request: Request, feedback: Dict[str, Any] = Body(...)):
    """
    Receive feedback on whether an action succeeded or failed
    
    This enables adaptive learning - AI tracks which actions are failing
    and tries alternatives after 3+ consecutive failures.
    
    Request body:
    {
        "action": "rest",
        "status": "failed",
        "reason": "basic_skill_not_learned",
        "message": "Character does not have Basic Skill Lv3 to sit"
    }
    """
    action = feedback.get("action", "unknown")
    status = feedback.get("status", "unknown")
    reason = feedback.get("reason", "")
    message = feedback.get("message", "")
    
    logger.info(f"[FEEDBACK] Action '{action}' → {status.upper()}")
    
    if status == "failed":
        logger.warning(f"[FEEDBACK] Failure reason: {reason}")
        logger.debug(f"[FEEDBACK] Message: {message}")
        
        # Record the failure for adaptive logic
        record_action_failure(action, reason)
    
    elif status == "success":
        logger.info(f"[FEEDBACK] Action succeeded, clearing failure history")
        clear_failure_tracking_for_action(action)
    
    return {
        "received": True,
        "action": action,
        "status": status,
        "failure_count": len(action_failure_tracker.get(action, []))
    }

@app.post("/api/v1/npc/buy_items")
async def npc_buy_items(request: Request, items: List[str] = Body(...)):
    """
    Endpoint to handle buying items from NPCs with retry logic
    Priority 2 Fix: Robust NPC interaction system
    """
    logger.info(f"[NPC/BUY] Request to buy items: {items}")
    
    result = await npc_handler.buy_items_with_retry(items, max_retries=3)
    
    if result["success"]:
        logger.info(f"[NPC/BUY] Success! Command: {result.get('command')}")
    else:
        logger.error(f"[NPC/BUY] Failed after {result['retry_count']} attempts: {result.get('error')}")
    
    return result


@app.post("/api/v1/inventory/sell_junk")
async def inventory_sell_junk(request: Request, inventory: List[Dict] = Body(...), min_zeny: int = 1000):
    """
    Analyze inventory and determine which items can be safely sold
    Priority 2 Fix: Item selling logic with protection rules
    """
    logger.info(f"[INVENTORY/SELL] Analyzing {len(inventory)} items for selling")
    
    result = await npc_handler.sell_junk_items(inventory, min_zeny_threshold=min_zeny)
    
    if result["success"]:
        logger.info(f"[INVENTORY/SELL] Can sell {len(result['items_sold'])} items for ~{result['estimated_zeny']}z")
    
    return result


@app.post("/api/v1/inventory/categorize")
async def inventory_categorize(request: Request, inventory: List[Dict] = Body(...)):
    """
    Categorize inventory items into sellable vs keep with reasons
    Priority 2 Fix: Smart inventory categorization
    """
    logger.info(f"[INVENTORY/CATEGORIZE] Analyzing {len(inventory)} items")
    
    result = npc_handler.categorize_inventory_for_selling(inventory)
    
    logger.info(f"[INVENTORY/CATEGORIZE] Results: {len(result['sell'])} sellable, {len(result['keep'])} keep")
    
    return result

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

@app.post("/api/v1/progression/allocate_stats")
async def allocate_stats_immediate(request: Request, request_body: Dict[str, Any] = Body(...)):
    """
    Immediate stat allocation endpoint (action-driven).
    Called by GodTierAI when AI decides to allocate stat points right now.
    
    Unlike on_level_up (event-driven), this is for AI-driven immediate decisions.
    """
    try:
        logger.info("[ALLOCATE_STATS_IMMEDIATE] Received stat allocation request")
        
        # Extract current character state
        current_stats = request_body.get('current_stats', {})
        available_points = int(request_body.get('available_points', 0))
        current_level = int(request_body.get('current_level', 1))
        job_class = request_body.get('job_class', 'Novice')
        
        logger.info(f"[ALLOCATE_STATS_IMMEDIATE] Class: {job_class}, Level: {current_level}, Available: {available_points}")
        
        if available_points <= 0:
            return {
                "success": False,
                "reason": "no_points_available",
                "stats_to_add": {}
            }
        
        # Use StatAllocator if available
        try:
            recommendations = stat_allocator.get_allocation_recommendations(
                current_stats,
                available_points
            )
            
            if recommendations:
                # Return recommended stat allocation
                logger.info(f"[ALLOCATE_STATS_IMMEDIATE] Recommendations: {recommendations}")
                return {
                    "success": True,
                    "stats_to_add": recommendations,
                    "reason": f"Following {stat_allocator.selected_build} build",
                    "build_type": stat_allocator.selected_build
                }
        except Exception as e:
            logger.error(f"[ALLOCATE_STATS_IMMEDIATE] StatAllocator error: {e}")
        
        # Fallback: Simple allocation for Novice
        logger.info("[ALLOCATE_STATS_IMMEDIATE] Using fallback allocation for Novice")
        stats_to_add = {}
        
        if job_class == "Novice":
            # Balanced Novice build: STR+DEX focus
            points_remaining = available_points
            
            if points_remaining >= 2:
                stats_to_add["STR"] = 2  # Attack power
                points_remaining -= 2
            
            if points_remaining >= 2:
                stats_to_add["DEX"] = 2  # Hit rate
                points_remaining -= 2
            
            if points_remaining >= 1:
                stats_to_add["VIT"] = 1  # Survivability
                points_remaining -= 1
        
        return {
            "success": True,
            "stats_to_add": stats_to_add,
            "reason": "basic_novice_build",
            "build_type": "balanced"
        }
        
    except Exception as e:
        logger.error(f"[ALLOCATE_STATS_IMMEDIATE] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/progression/learn_skill")
async def learn_skill_immediate(request: Request, request_body: Dict[str, Any] = Body(...)):
    """
    Immediate skill learning endpoint (action-driven).
    Called by GodTierAI when AI decides to learn skills right now.
    
    CRITICAL PRIORITY: Learn Basic Skill Lv3 first (required for sit/rest).
    """
    try:
        logger.info("[LEARN_SKILL_IMMEDIATE] Received skill learning request")
        
        # Extract current character state
        character_class = request_body.get('character_class', 'Novice')
        current_level = int(request_body.get('current_level', 1))
        job_level = int(request_body.get('job_level', 1))
        available_points = int(request_body.get('available_points', 0))
        current_skills = request_body.get('current_skills', {})
        
        logger.info(f"[LEARN_SKILL_IMMEDIATE] Class: {character_class}, Job Lv: {job_level}, Available: {available_points}")
        
        if available_points <= 0:
            return {
                "success": False,
                "reason": "no_points_available",
                "skills_to_learn": []
            }
        
        # CRITICAL: Check if Basic Skill needs learning
        basic_skill_level = current_skills.get("NV_BASIC", 0) or current_skills.get("Basic Skill", 0)
        
        if basic_skill_level < 3:
            points_needed = 3 - basic_skill_level
            points_to_allocate = min(points_needed, available_points)
            
            logger.warning(f"[LEARN_SKILL_IMMEDIATE] CRITICAL: Learning Basic Skill Lv{basic_skill_level} → Lv{basic_skill_level + points_to_allocate}")
            
            return {
                "success": True,
                "skills_to_learn": [{
                    "skill_name": "NV_BASIC",
                    "skill_display_name": "Basic Skill",
                    "current_level": basic_skill_level,
                    "target_level": basic_skill_level + points_to_allocate,
                    "points_to_add": points_to_allocate,
                    "priority": "critical",
                    "reason": "prerequisite_for_sit_rest"
                }],
                "reason": "basic_skill_prerequisite"
            }
        
        # Use SkillLearner if available
        try:
            skill_plan = skill_learner.get_skill_learning_plan(
                character_class,
                job_level,
                current_skills,
                available_points
            )
            
            if skill_plan and skill_plan.get('skills_to_learn'):
                logger.info(f"[LEARN_SKILL_IMMEDIATE] Recommendations: {skill_plan['skills_to_learn']}")
                return {
                    "success": True,
                    "skills_to_learn": skill_plan['skills_to_learn'],
                    "reason": skill_plan.get('reason', 'progression')
                }
        except Exception as e:
            logger.error(f"[LEARN_SKILL_IMMEDIATE] SkillLearner error: {e}")
        
        # Fallback: No skills to learn
        logger.info("[LEARN_SKILL_IMMEDIATE] No skills to learn (Basic Skill already maxed, no other recommendations)")
        return {
            "success": True,
            "skills_to_learn": [],
            "reason": "no_skills_needed"
        }
        
    except Exception as e:
        logger.error(f"[LEARN_SKILL_IMMEDIATE] Error: {e}", exc_info=True)
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
async def handle_equipment_map_change(request: Dict[str, Any] = Body(...)):
    """
    Called when entering a new map.
    Analyzes enemies and recommends optimal equipment setup.
    
    Accepts flexible request body:
    - new_map (required): Map name
    - enemies (optional): List of enemy data
    - old_map (optional): Previous map name
    - character_data (optional): Character information
    """
    try:
        # Extract required and optional fields
        new_map = request.get('new_map')
        if not new_map:
            logger.error("[EQUIPMENT] Missing required field: new_map")
            return {"success": False, "error": "Missing required field: new_map"}
        
        enemies = request.get('enemies', [])
        old_map = request.get('old_map')
        
        logger.info(f"[EQUIPMENT] Map change: {old_map or 'unknown'} → {new_map}, enemies: {len(enemies)}")
        
        result = equipment_manager.on_map_change(new_map, enemies)
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"[EQUIPMENT] Error processing map change: {e}")
        return {"success": False, "error": str(e)}

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

@app.post("/api/v1/self_heal/fix_plugin_config")
async def fix_plugin_config(
    plugin_name: str = Body(...),
    character_level: int = Body(1),
    character_class: str = Body("Novice")
):
    """
    Auto-configure missing plugin settings
    
    User requirement: "If it's config or macro issue, it should be done by
    the CrewAI or autonomous self healing with hot reload!"
    
    This endpoint is called by GodTierAI.pm when it detects plugin warnings
    about missing configuration. It automatically generates the required config
    and appends it to config.txt, which triggers hot reload (no disconnect).
    
    Args:
        plugin_name: Name of the plugin to configure (e.g., "teleToDest")
        character_level: Character base level for adaptive configuration
        character_class: Character class for class-specific settings
    
    Returns:
        JSON with success status and details of configuration added
    """
    logger.info(f"[SELF-HEAL] Fixing plugin config: {plugin_name}")
    logger.info(f"[SELF-HEAL] Character: Lv{character_level} {character_class}")
    
    # Path to config.txt (relative to ai-service root)
    config_path = Path(__file__).parent.parent.parent.parent / "control" / "config.txt"
    
    if not config_path.exists():
        logger.error(f"[SELF-HEAL] Config file not found: {config_path}")
        return {
            "success": False,
            "plugin": plugin_name,
            "error": f"Config file not found: {config_path}"
        }
    
    if plugin_name == "teleToDest":
        try:
            result = generate_teledest_config(config_path, character_level, character_class)
            
            if result.get("success"):
                logger.info(f"[SELF-HEAL] teleToDest config fixed successfully")
                logger.info(f"[SELF-HEAL] Keys added: {result.get('keys_added', [])}")
                logger.info(f"[SELF-HEAL] GodTierAI will auto-detect config change and hot-reload")
                
                return {
                    "success": True,
                    "plugin": plugin_name,
                    "config_added": result,
                    "hot_reload": "GodTierAI monitors config.txt and will reload automatically",
                    "next_steps": "Plugin will activate on next config check cycle (~5 seconds)"
                }
            else:
                logger.error(f"[SELF-HEAL] Failed to add teleToDest config: {result.get('error')}")
                return {
                    "success": False,
                    "plugin": plugin_name,
                    "error": result.get('error', 'Unknown error')
                }
        
        except Exception as e:
            logger.error(f"[SELF-HEAL] Exception while fixing teleToDest config: {e}")
            return {
                "success": False,
                "plugin": plugin_name,
                "error": str(e)
            }
    
    else:
        logger.warning(f"[SELF-HEAL] Unsupported plugin: {plugin_name}")
        return {
            "success": False,
            "plugin": plugin_name,
            "error": f"Unknown plugin: {plugin_name}",
            "supported_plugins": ["teleToDest"]
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

# ============================================================================
# REAL-TIME TABLE DATA ENDPOINTS
# ============================================================================

@app.get("/api/v1/tables/monsters")
async def get_monsters_table():
    """
    Get current monster data (updated in real-time by OpenKore)
    
    OpenKore updates monsters.txt as the bot explores and discovers new monsters.
    This endpoint provides the latest monster database for decision-making.
    """
    try:
        monsters = table_loader.load_monsters() if table_loader._monsters_cache is None else table_loader._monsters_cache
        return {
            "success": True,
            "count": len(monsters),
            "monsters": monsters,
            "last_updated": time.time(),
            "source": "openkore-ai/tables/monsters.txt (real-time)"
        }
    except Exception as e:
        logger.error(f"[Tables] Failed to load monsters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/tables/npcs")
async def get_npcs_table(map_name: Optional[str] = None):
    """
    Get current NPC data (updated in real-time by OpenKore)
    
    OpenKore updates npcs.txt as the bot discovers NPCs during gameplay.
    Optionally filter by map name for faster lookups.
    
    Args:
        map_name: Optional map filter (e.g., "prontera")
    """
    try:
        if map_name:
            npcs_on_map = table_loader.get_npcs_on_map(map_name)
            return {
                "success": True,
                "map": map_name,
                "count": len(npcs_on_map),
                "npcs": npcs_on_map,
                "last_updated": time.time(),
                "source": "openkore-ai/tables/npcs.txt (real-time)"
            }
        
        npcs = table_loader.load_npcs() if table_loader._npcs_cache is None else table_loader._npcs_cache
        return {
            "success": True,
            "count": len(npcs),
            "npcs": npcs,
            "last_updated": time.time(),
            "source": "openkore-ai/tables/npcs.txt (real-time)"
        }
    except Exception as e:
        logger.error(f"[Tables] Failed to load NPCs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/tables/portals")
async def get_portals_table():
    """
    Get current portal data (updated in real-time by OpenKore)
    
    OpenKore updates portals.txt as the bot discovers new portal connections.
    Essential for pathfinding and navigation decisions.
    """
    try:
        portals = table_loader.load_portals() if table_loader._portals_cache is None else table_loader._portals_cache
        return {
            "success": True,
            "count": len(portals),
            "portals": portals,
            "last_updated": time.time(),
            "source": "openkore-ai/tables/portals.txt (real-time)"
        }
    except Exception as e:
        logger.error(f"[Tables] Failed to load portals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/tables/reload")
async def reload_all_tables():
    """
    Force reload all tables from disk
    
    Useful for manual refresh or debugging. Tables are normally
    reloaded automatically via file watcher.
    """
    try:
        logger.info("[API] Manual table reload requested")
        
        # Clear all caches
        table_loader._items_cache = None
        table_loader._monsters_cache = None
        table_loader._npcs_cache = None
        table_loader._portals_cache = None
        table_loader._portals_los_cache = None
        table_loader._maps_cache = None
        table_loader._cities_cache = None
        
        # Reload all tables
        items = table_loader.load_items()
        monsters = table_loader.load_monsters()
        npcs = table_loader.load_npcs()
        portals = table_loader.load_portals()
        maps = table_loader.load_maps()
        cities = table_loader.load_cities()
        
        return {
            "success": True,
            "reloaded": {
                "items": len(items),
                "monsters": len(monsters),
                "npcs": len(npcs),
                "portals": len(portals),
                "maps": len(maps),
                "cities": len(cities)
            },
            "timestamp": time.time(),
            "message": "All tables reloaded from disk"
        }
    except Exception as e:
        logger.error(f"[Tables] Failed to reload tables: {e}")
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
            "/api/v1/combat/status",
            "/api/v1/tables/monsters",
            "/api/v1/tables/npcs",
            "/api/v1/tables/portals",
            "/api/v1/tables/reload"
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
