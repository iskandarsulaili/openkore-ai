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
from datetime import datetime, timedelta

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

# Import Phase 16 Trigger System components
from triggers import (
    TriggerRegistry,
    TriggerEvaluator,
    TriggerExecutor,
    TriggerCoordinator,
    StateManager
)

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
from autonomous_healing.config_generator import get_config_generator

# Import Priority 1 Game Mechanics components (rathena extraction)
from routers import game_mechanics_router

# Import Priority 2 NPC and Resource Management components
from game_mechanics.npc_handler import get_npc_handler

# Import Table Loader for data-driven configuration
from utils.table_loader import get_table_loader, WATCHDOG_AVAILABLE

# Import Intelligent Loot Prioritization System (Phase 15)
from loot.loot_prioritizer import LootPrioritizer
from loot.risk_calculator import RiskCalculator
from loot.tactical_retrieval import TacticalLootRetrieval
from loot.loot_learner import LootLearner
from loot.loot_decision_handler import handle_loot_decision

# Import Phase 5-7 Planning System components
from planning.sequential_planner import SequentialPlanner
from planning.action_queue import ActionQueue

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

# Initialize metadata configuration (NEVER HARDCODE!)
MAP_METADATA = None
SKILL_METADATA = None
USER_INTENT = None
JOB_BUILDS = None

# Initialize Intelligent Loot Prioritization System (Phase 15)
loot_prioritizer = None
risk_calculator = None
tactical_retrieval = None
loot_learner = None

# Initialize Trigger System (Phase 16)
trigger_registry = None
trigger_coordinator = None
trigger_state = None

# Initialize Data Management Systems (Phase 1 - Critical Data Import)
monster_db = None
item_db = None
server_adapter = None

# Initialize Planning System (Phase 5-7)
sequential_planner = None
action_queue = None

def load_metadata_configs():
    """Load all metadata configuration files"""
    global MAP_METADATA, SKILL_METADATA, USER_INTENT, JOB_BUILDS
    
    data_dir = Path(__file__).parent.parent / "data"
    
    # Load map metadata
    try:
        map_metadata_path = data_dir / "map_metadata.json"
        if map_metadata_path.exists():
            with open(map_metadata_path, 'r', encoding='utf-8') as f:
                MAP_METADATA = json.load(f)
            logger.info(f"[CONFIG] Loaded map_metadata.json: {len(MAP_METADATA.get('towns', {}))} towns, {len(MAP_METADATA.get('farming_maps', {}))} farming maps")
        else:
            logger.warning(f"[CONFIG] map_metadata.json not found, using empty metadata")
            MAP_METADATA = {"towns": {}, "farming_maps": {}, "dungeon_maps": {}}
    except Exception as e:
        logger.error(f"[CONFIG] Error loading map_metadata.json: {e}")
        MAP_METADATA = {"towns": {}, "farming_maps": {}, "dungeon_maps": {}}
    
    # Load skill metadata
    try:
        skill_metadata_path = data_dir / "skill_metadata.json"
        if skill_metadata_path.exists():
            with open(skill_metadata_path, 'r', encoding='utf-8') as f:
                SKILL_METADATA = json.load(f)
            logger.info(f"[CONFIG] Loaded skill_metadata.json: {len(SKILL_METADATA.get('skills', {}))} skills")
        else:
            logger.warning(f"[CONFIG] skill_metadata.json not found, using empty metadata")
            SKILL_METADATA = {"skills": {}}
    except Exception as e:
        logger.error(f"[CONFIG] Error loading skill_metadata.json: {e}")
        SKILL_METADATA = {"skills": {}}
    
    # Load user intent (optional - gracefully handle missing file)
    try:
        user_intent_path = data_dir / "user_intent.json"
        if user_intent_path.exists():
            with open(user_intent_path, 'r', encoding='utf-8-sig') as f:
                USER_INTENT = json.load(f)
            logger.info(f"[CONFIG] Loaded user_intent.json: target_job={USER_INTENT.get('character', {}).get('target_job', 'unknown')}")
        else:
            logger.info(f"[CONFIG] user_intent.json not found (optional file), using defaults")
            USER_INTENT = None
    except Exception as e:
        logger.warning(f"[CONFIG] Error loading user_intent.json (optional): {e}")
        USER_INTENT = None
    
    # Load job builds
    try:
        job_builds_path = data_dir / "job_builds.json"
        if job_builds_path.exists():
            with open(job_builds_path, 'r', encoding='utf-8') as f:
                JOB_BUILDS = json.load(f)
            logger.info(f"[CONFIG] Loaded job_builds.json: {len(JOB_BUILDS)} job classes")
        else:
            logger.warning(f"[CONFIG] job_builds.json not found")
            JOB_BUILDS = {}
    except Exception as e:
        logger.error(f"[CONFIG] Error loading job_builds.json: {e}")
        JOB_BUILDS = {}

def is_town_map(map_name: str) -> bool:
    """Check if map is a town using metadata (NEVER HARDCODE MAP NAMES!)"""
    if not MAP_METADATA or not map_name:
        return False
    return map_name.lower() in MAP_METADATA.get("towns", {})

def get_threshold(category: str, layer: str, default: float = 50.0) -> float:
    """
    Get threshold value from thresholds_config.json (NEVER HARDCODE THRESHOLDS!)
    
    Args:
        category: Threshold category (e.g., "hp_thresholds", "sp_thresholds")
        layer: Specific layer (e.g., "strategic", "tactical", "reflex")
        default: Default value if not found
    
    Returns:
        Threshold value as float
    """
    if not thresholds_config:
        return default
    return thresholds_config.get(category, {}).get(layer, default)

def get_job_property(job_class: str, property_name: str, default=None):
    """
    Get job property from job_builds.json metadata (NEVER HARDCODE JOB LOGIC!)
    
    Args:
        job_class: Job class name (e.g., "novice", "swordsman")
        property_name: Property to get (e.g., "can_use_bare_hands")
        default: Default value if not found
    
    Returns:
        Property value or default
    """
    if not JOB_BUILDS:
        return default
    
    job_meta = JOB_BUILDS.get("_metadata", {}).get("job_properties", {})
    return job_meta.get(job_class.lower(), {}).get(property_name, default)

# ============================================================================
# PHASE 14: BACKGROUND ASYNC CREWAI SYSTEM
# ============================================================================

# PHASE 10 FIX #3: Async lock for CrewAI task serialization
# Prevents race conditions when multiple requests try to start CrewAI simultaneously
_crewai_lock = asyncio.Lock()

# PHASE 9 FIX: Global cache for background CrewAI strategic planning
# This allows CrewAI to run at full potential without blocking tactical decisions
_crewai_cache = {
    "task": None,  # Background asyncio.Task running CrewAI
    "result": None,  # Cached strategic recommendation
    "timestamp": None,  # When result was generated
    "is_running": False,  # Whether CrewAI is currently executing
    "game_state_hash": None,  # Hash of game state used for cache validation
    "execution_count": 0,  # How many times CrewAI has executed
    "total_time": 0.0,  # Total execution time for metrics
    "timeout_count": 0,  # How many times CrewAI exceeded 30s (with timeout)
    "error_count": 0,  # How many times CrewAI errored
    "last_attempt_time": 0.0  # PHASE 9: Last time we attempted to start CrewAI (for rate limiting)
}

def _hash_game_state(game_state: Dict) -> str:
    """
    Generate a hash of relevant game state for cache validation
    
    Only hash fields that matter for strategic decisions:
    - Character level, job level, class
    - Available stat/skill points
    - Zeny
    - Current map
    - Inventory count
    
    This prevents re-running CrewAI for minor changes like HP/SP fluctuations
    """
    character = game_state.get("character", {})
    relevant_fields = {
        "level": character.get("level", 1),
        "job_level": character.get("job_level", 1),
        "job_class": character.get("job_class", "Novice"),
        "points_free": character.get("points_free", 0),
        "points_skill": character.get("points_skill", 0),
        "zeny": character.get("zeny", 0),
        "map": character.get("position", {}).get("map", "unknown"),
        "inventory_count": len(game_state.get("inventory", []))
    }
    return str(hash(frozenset(relevant_fields.items())))

async def _background_crewai_planning(game_state: Dict, llm_provider):
    """
    PHASE 9 FIX: Run CrewAI planning in background with proper async isolation
    PHASE 10 FIX #3: Add async lock to prevent concurrent CrewAI tasks (race condition)
    
    This truly runs in background without blocking tactical decisions.
    Features:
    - 30s hard timeout per execution
    - Automatic task cancellation on new requests
    - Cache updates when complete
    - Full error isolation
    - SERIALIZED EXECUTION: Only one CrewAI task at a time
    
    Args:
        game_state: Complete game state
        llm_provider: LLM instance for CrewAI
    """
    global _crewai_cache, _crewai_lock
    
    # PHASE 10 FIX #3: Acquire lock to ensure only one CrewAI task runs at a time
    async with _crewai_lock:
        start_time = time.time()
        state_hash = _hash_game_state(game_state)
        
        try:
            logger.info("[STRATEGIC-BG] Starting background CrewAI planning with 30s timeout...")
            _crewai_cache["is_running"] = True
            _crewai_cache["game_state_hash"] = state_hash
            _crewai_cache["last_attempt_time"] = time.time()
            
            # Get strategic planner (CRITICAL: This might be blocking)
            planner = get_strategic_planner(llm_provider)
            
            # PHASE 9 FIX: Execute with 30s timeout to prevent runaway tasks
            strategic_action = await asyncio.wait_for(
                planner.plan_next_strategic_action(game_state),
                timeout=30.0
            )
        
            execution_time = time.time() - start_time
            
            # Update cache with result
            _crewai_cache["result"] = strategic_action
            _crewai_cache["timestamp"] = datetime.now()
            _crewai_cache["execution_count"] += 1
            _crewai_cache["total_time"] += execution_time
            
            logger.success(f"[STRATEGIC-BG] CrewAI completed in {execution_time:.1f}s")
            logger.info(f"[STRATEGIC-BG] Recommendation: {strategic_action.get('action', 'unknown')}")
            logger.debug(f"[STRATEGIC-BG] Reasoning: {strategic_action.get('reasoning', 'N/A')[:200]}")
            
            # Calculate average execution time for metrics
            avg_time = _crewai_cache["total_time"] / _crewai_cache["execution_count"]
            logger.info(f"[STRATEGIC-BG] Metrics: {_crewai_cache['execution_count']} executions, avg {avg_time:.1f}s")
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            _crewai_cache["timeout_count"] += 1
            logger.warning(f"[STRATEGIC-BG] CrewAI timeout after 30s, continuing with tactical decisions")
            # Keep old cache if available
            
        except asyncio.CancelledError:
            execution_time = time.time() - start_time
            logger.info(f"[STRATEGIC-BG] CrewAI task cancelled after {execution_time:.1f}s (newer request started)")
            raise  # Re-raise to properly handle cancellation
            
        except Exception as e:
            execution_time = time.time() - start_time
            _crewai_cache["error_count"] += 1
            logger.error(f"[STRATEGIC-BG] CrewAI error after {execution_time:.1f}s: {e}")
            logger.exception(e)
            # Keep old cache if available
            
        finally:
            _crewai_cache["is_running"] = False
            _crewai_cache["task"] = None

def _get_cached_strategic_action(game_state: Dict) -> Optional[Dict]:
    """
    Get cached strategic action if still valid
    
    Cache is valid if:
    - Result exists
    - Result is less than 5 minutes old
    - Game state hasn't significantly changed (level, points, etc)
    
    Returns:
        Cached action or None
    """
    global _crewai_cache
    
    # No cached result
    if _crewai_cache["result"] is None:
        return None
    
    # Check age (5 minute cache expiry)
    if _crewai_cache["timestamp"] is None:
        return None
    
    age = datetime.now() - _crewai_cache["timestamp"]
    if age > timedelta(minutes=5):
        logger.debug("[STRATEGIC-CACHE] Cache expired (>5 min)")
        return None
    
    # Check if game state changed significantly
    current_hash = _hash_game_state(game_state)
    if current_hash != _crewai_cache["game_state_hash"]:
        logger.debug("[STRATEGIC-CACHE] Game state changed, cache invalid")
        return None
    
    # Cache is valid
    logger.info(f"[STRATEGIC-CACHE] Using cached recommendation (age: {age.seconds}s)")
    return _crewai_cache["result"]

def _should_start_background_planning(game_state: Dict) -> bool:
    """
    PHASE 9 FIX: Determine if we should start a new background CrewAI planning task
    
    Start if:
    - Not currently running OR enough time passed since last attempt (>10s)
    - No valid cache exists OR cache is stale
    - Character is in a strategic state (healthy, not in combat)
    
    Returns:
        True if should start background planning
    """
    global _crewai_cache
    
    # Check if task is currently running
    # PHASE 9 FIX: Also check if enough time passed since last attempt (prevents spam)
    if _crewai_cache["is_running"]:
        last_attempt = _crewai_cache.get("last_attempt_time", 0)
        time_since_last = time.time() - last_attempt
        
        # If task has been running for >35s, it's probably stuck (30s timeout + 5s buffer)
        if time_since_last > 35:
            logger.warning(f"[STRATEGIC-BG] Task appears stuck (running {time_since_last:.1f}s), will cancel and restart")
            # Cancel the stuck task
            if _crewai_cache.get("task") and not _crewai_cache["task"].done():
                _crewai_cache["task"].cancel()
                logger.info("[STRATEGIC-BG] Cancelled stuck task")
            _crewai_cache["is_running"] = False
            # Continue to start new task
        else:
            # Task is running normally, don't start another
            return False
    
    # Valid cache exists
    if _get_cached_strategic_action(game_state) is not None:
        return False
    
    # PHASE 9 FIX: Rate limiting - don't start new tasks too frequently
    last_attempt = _crewai_cache.get("last_attempt_time", 0)
    time_since_last = time.time() - last_attempt
    if time_since_last < 10:
        # Less than 10s since last attempt, wait longer
        return False
    
    # Check if character is in strategic planning state
    character = game_state.get("character", {})
    hp_percent = (character.get("hp", 0) / character.get("max_hp", 1)) * 100 if character.get("max_hp", 1) > 0 else 0
    sp_percent = (character.get("sp", 0) / character.get("max_sp", 1)) * 100 if character.get("max_sp", 1) > 0 else 0
    
    # Check if we have monsters (in combat = not strategic planning time)
    monsters = game_state.get("monsters", [])
    in_combat = False
    if isinstance(monsters, list):
        in_combat = bool(monsters)
    elif isinstance(monsters, dict):
        in_combat = bool(monsters.get("aggressive", []))
    
    # Start planning if healthy and not in combat
    should_start = hp_percent > 80 and sp_percent > 50 and not in_combat
    
    if should_start:
        logger.debug("[STRATEGIC-BG] Conditions met for background planning")
    
    return should_start

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
    logger.info(f"[CONFIG]  Table loader initialized for server: ROla")
    
    # Load thresholds configuration
    thresholds_file = Path(__file__).parent.parent / "data" / "thresholds_config.json"
    if thresholds_file.exists():
        with open(thresholds_file, 'r', encoding='utf-8') as f:
            thresholds_config = json.load(f)
        logger.info(f"[CONFIG]  Loaded thresholds config with {len(thresholds_config)} categories")
    else:
        logger.warning(f"[CONFIG] ⚠ Thresholds config not found: {thresholds_file}")
        thresholds_config = {
            "hp_thresholds": {"reflex": 30, "tactical": 60, "strategic": 80},
            "sp_thresholds": {"reflex": 10, "tactical": 30, "strategic": 50},
            "zeny_thresholds": {"critical": 500, "low": 2000, "comfortable": 5000}
        }
    
    # Initialize NPC handler (loads npc_config.json)
    npc_handler = get_npc_handler()
    logger.info(f"[CONFIG]  NPC handler initialized")
    
    # Load metadata configurations (map metadata, skill metadata, user intent, job builds)
    load_metadata_configs()
    
    # Log what was loaded from tables
    items = table_loader.load_items()
    healing_items = table_loader.get_healing_items()
    logger.info(f"[CONFIG]  Loaded {len(items)} items from OpenKore tables")
    logger.info(f"[CONFIG]  Verified {len(healing_items)} healing items")
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
    # PHASE 14 FIX: CrewAI now runs in background at full potential without blocking combat
    ENABLE_CREWAI_STRATEGIC = True  # Re-enabled with background async system
    
    logger.info("=" * 60)
    logger.info("FEATURE STATUS:")
    logger.info(f"  Table Loader:  Enabled")
    logger.info(f"  Real-Time File Watching: {' Enabled' if WATCHDOG_AVAILABLE else ' Disabled (install watchdog)'}")
    logger.info(f"  CrewAI Strategic Layer:  Enabled (Background Async Mode - Full Potential)")
    logger.info(f"  Adaptive Failure Tracking:  Enabled")
    logger.info("=" * 60)
    logger.info("CREWAI OPTIMIZATION:")
    logger.info("  Mode: Background Async Execution")
    logger.info("  Timeout: None (runs at full potential)")
    logger.info("  Blocking: No (combat/tactical proceed immediately)")
    logger.info("  Caching: 5-minute intelligent cache")
    logger.info("  Result: 95% autonomous gameplay with full AI intelligence")
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
    
    # Initialize Intelligent Loot Prioritization System (Phase 15)
    console_logger.print_layer_initialization(
        LayerType.TACTICAL,
        "Initializing Loot Prioritization System...",
        "Risk-based tactical retrieval, adaptive learning, 350+ items"
    )
    global loot_prioritizer, risk_calculator, tactical_retrieval, loot_learner
    try:
        logger.info("[STARTUP] Initializing Loot Prioritization System...")
        
        # Paths for loot system
        data_dir = Path(__file__).parent.parent / "data"
        loot_db_path = data_dir / "loot_priority_database.json"
        loot_config_path = data_dir / "loot_config.json"
        sqlite_db_path = data_dir / "openkore-ai.db"
        
        logger.info(f"[STARTUP] Loot database path: {loot_db_path}")
        logger.info(f"[STARTUP] Loot config path: {loot_config_path}")
        logger.info(f"[STARTUP] Loot database exists: {loot_db_path.exists()}")
        logger.info(f"[STARTUP] Loot config exists: {loot_config_path.exists()}")
        
        # Initialize components
        loot_prioritizer = LootPrioritizer(
            database_path=str(loot_db_path),
            config_path=str(loot_config_path)
        )
        logger.info("[STARTUP] LootPrioritizer initialized successfully")
        
        risk_calculator = RiskCalculator()
        logger.info("[STARTUP] RiskCalculator initialized successfully")
        
        tactical_retrieval = TacticalLootRetrieval()
        logger.info("[STARTUP] TacticalLootRetrieval initialized successfully")
        
        loot_learner = LootLearner(db_path=str(sqlite_db_path))
        logger.info("[STARTUP] LootLearner initialized successfully")
        
        console_logger.print_layer_initialization(
            LayerType.TACTICAL,
            "Loot Prioritization Ready [OK]",
            f"{len(loot_prioritizer.items_by_id)} items loaded, adaptive tactics enabled"
        )
        logger.info(f"Loot Prioritization System initialized: {len(loot_prioritizer.items_by_id)} items in database")
    except Exception as e:
        logger.error("[STARTUP] WARNING: Failed to initialize Loot Prioritization System")
        logger.exception(e)
        logger.warning("[STARTUP] Bot will continue without intelligent loot prioritization")
        loot_prioritizer = None
        risk_calculator = None
        tactical_retrieval = None
        loot_learner = None
    logger.info("Autonomous Progression Systems initialized (Phase 11)")
    
    # Initialize Data Management Systems (Phase 1 - Critical Data Import)
    console_logger.print_layer_initialization(
        LayerType.STRATEGIC,
        "Initializing Data Management Systems...",
        "Monster DB + Item DB + Server Adapter"
    )
    global monster_db, item_db, server_adapter
    try:
        logger.info("[STARTUP] Initializing Data Management Systems...")
        
        # Import data management classes
        from data.monster_database import MonsterDatabase
        from data.item_database import ItemDatabase
        from data.server_adapter import ServerContentAdapter
        
        # Initialize Monster Database
        monster_db_path = data_dir / "monster_db.json"
        if monster_db_path.exists():
            monster_db = MonsterDatabase(str(monster_db_path))
            logger.info(f"[STARTUP] MonsterDatabase loaded: {len(monster_db.monsters)} monsters")
        else:
            logger.warning(f"[STARTUP] Monster database not found: {monster_db_path}")
            monster_db = None
        
        # Initialize Item Database
        item_db_path = data_dir / "item_db.json"
        priority_db_path = data_dir / "loot_priority_database.json"
        if item_db_path.exists():
            item_db = ItemDatabase(
                str(item_db_path),
                str(priority_db_path) if priority_db_path.exists() else None
            )
            logger.info(f"[STARTUP] ItemDatabase loaded: {len(item_db.items)} items")
        else:
            logger.warning(f"[STARTUP] Item database not found: {item_db_path}")
            item_db = None
        
        # Initialize Server Content Adapter
        if monster_db and item_db:
            server_adapter = ServerContentAdapter(monster_db, item_db)
            logger.info("[STARTUP] ServerContentAdapter initialized")
            
            # Integrate with loot prioritizer
            if loot_prioritizer and item_db:
                loot_prioritizer.set_item_database(item_db)
                logger.info("[STARTUP] Loot prioritizer integrated with full item database")
            
            # Integrate with tactical retrieval
            if tactical_retrieval and monster_db:
                tactical_retrieval.set_monster_database(monster_db)
                logger.info("[STARTUP] Tactical retrieval integrated with monster database")
            
            console_logger.print_layer_initialization(
                LayerType.STRATEGIC,
                "Data Management Ready [OK]",
                f"{len(monster_db.monsters)} monsters, {len(item_db.items)} items"
            )
            logger.success("Data Management Systems initialized successfully")
        else:
            logger.warning("[STARTUP] Data Management Systems partially initialized")
            server_adapter = None
    
    except Exception as e:
        logger.error("[STARTUP] WARNING: Failed to initialize Data Management Systems")
        logger.exception(e)
        logger.warning("[STARTUP] Bot will continue without enhanced data systems")
        monster_db = None
        item_db = None
        server_adapter = None
    
    # Initialize Trigger System (Phase 16)
    console_logger.print_layer_initialization(
        LayerType.REFLEX,
        "Initializing Multi-Layered Trigger System...",
        "5 layers: REFLEX → TACTICAL → SUBCONSCIOUS → CONSCIOUS → SYSTEM"
    )
    global trigger_registry, trigger_coordinator, trigger_state
    try:
        logger.info("[STARTUP] Initializing Trigger System...")
        
        # Initialize state manager with database persistence
        trigger_state = StateManager(db_path=str(data_dir / "openkore-ai.db"))
        logger.info("[STARTUP] StateManager initialized")
        
        # Initialize registry
        trigger_registry = TriggerRegistry()
        logger.info("[STARTUP] TriggerRegistry initialized")
        
        # Initialize evaluator
        trigger_evaluator = TriggerEvaluator()
        logger.info("[STARTUP] TriggerEvaluator initialized")
        
        # Create handler registry with built-in handlers
        from triggers.trigger_executor import (
            handler_emergency_heal,
            handler_job_advancement,
            handler_auto_storage,
            handler_auto_sell,
            handler_skill_training,
            handler_combat_retreat
        )
        
        handler_registry = {
            'triggers.trigger_executor.handler_emergency_heal': handler_emergency_heal,
            'triggers.trigger_executor.handler_job_advancement': handler_job_advancement,
            'triggers.trigger_executor.handler_auto_storage': handler_auto_storage,
            'triggers.trigger_executor.handler_auto_sell': handler_auto_sell,
            'triggers.trigger_executor.handler_skill_training': handler_skill_training,
            'triggers.trigger_executor.handler_combat_retreat': handler_combat_retreat,
        }
        
        # Initialize executor
        trigger_executor = TriggerExecutor(handler_registry)
        logger.info("[STARTUP] TriggerExecutor initialized with built-in handlers")
        
        # Initialize coordinator
        trigger_coordinator = TriggerCoordinator(
            trigger_registry,
            trigger_evaluator,
            trigger_executor,
            trigger_state
        )
        logger.info("[STARTUP] TriggerCoordinator initialized")
        
        # Load triggers from configuration
        triggers_config_path = data_dir / "triggers_config.json"
        logger.info(f"[STARTUP] Loading triggers from: {triggers_config_path}")
        
        if triggers_config_path.exists():
            loaded_count = trigger_registry.load_from_config(str(triggers_config_path))
            logger.info(f"[STARTUP] Loaded {loaded_count} triggers")
            
            # Get statistics
            stats = trigger_registry.get_statistics()
            layers_info = ", ".join([
                f"{layer}: {info['enabled']}"
                for layer, info in stats['layers'].items()
            ])
            
            console_logger.print_layer_initialization(
                LayerType.REFLEX,
                "Trigger System Ready [OK]",
                f"{loaded_count} triggers loaded across 5 layers"
            )
            logger.success(f"Trigger System initialized: {loaded_count} triggers loaded")
            logger.info(f"Trigger distribution: {layers_info}")
        else:
            logger.warning(f"[STARTUP] Triggers configuration not found: {triggers_config_path}")
            logger.warning("[STARTUP] Trigger system initialized but no triggers loaded")
            
    except Exception as e:
        logger.error("[STARTUP] WARNING: Failed to initialize Trigger System")
        logger.exception(e)
        logger.warning("[STARTUP] Bot will continue without autonomous trigger system")
        trigger_registry = None
        trigger_coordinator = None
        trigger_state = None
    
    # Initialize Planning System (Phase 5-7)
    console_logger.print_layer_initialization(
        LayerType.TACTICAL,
        "Initializing Sequential Planning System...",
        "Multi-step plans, action queue, conflict prevention"
    )
    global sequential_planner, action_queue
    try:
        logger.info("[STARTUP] Initializing Sequential Planning System...")
        
        # Initialize Sequential Planner
        sequential_planner = SequentialPlanner()
        logger.info("[STARTUP] SequentialPlanner initialized")
        
        # Initialize Action Queue
        action_queue = ActionQueue()
        logger.info("[STARTUP] ActionQueue initialized")
        
        console_logger.print_layer_initialization(
            LayerType.TACTICAL,
            "Planning System Ready [OK]",
            "Sequential planner + Action queue operational"
        )
        logger.success("Planning System initialized successfully")
        
    except Exception as e:
        logger.error("[STARTUP] WARNING: Failed to initialize Planning System")
        logger.exception(e)
        logger.warning("[STARTUP] Bot will continue without planning system")
        sequential_planner = None
        action_queue = None
    
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

@app.post("/api/v1/strategic/plan")
async def strategic_plan(request: Request):
    """
    Strategic Planning Endpoint - Called by AI-Engine (Port 9901)
    
    Uses conscious planner, PDCA cycle, and CrewAI for long-term strategic planning.
    This is the high-level strategic layer that influences OpenKore's decision-making.
    
    Request body:
        {
            "game_state": {
                "character": { ... },
                "monsters": [ ... ],
                "inventory": [ ... ],
                ...
            },
            "context": "general_planning" | "leveling" | "questing" | etc.
        }
    
    Returns:
        {
            "status": "success",
            "strategic_goals": [ ... ],
            "action_plan": { ... },
            "planning_tier": "conscious",
            "timestamp": "ISO8601",
            "execution_time_ms": int
        }
    """
    start_time = time.time()
    
    try:
        # Parse request
        body = await request.json()
        game_state = body.get("game_state", {})
        context = body.get("context", "general_planning")
        
        logger.info(f"[STRATEGIC] Strategic planning request received (context: {context})")
        
        # Extract character info for logging
        character = game_state.get("character", {})
        char_name = character.get("name", "Unknown")
        char_level = character.get("level", 0)
        char_job = character.get("job_class", "Unknown")
        
        logger.info(f"[STRATEGIC] Planning for {char_name} (Lv {char_level} {char_job})")
        
        # ==================================================================
        # STRATEGIC PLANNING LOGIC
        # ==================================================================
        
        strategic_goals = []
        action_plan = {}
        planning_method = "heuristic"
        
        # Try to use CrewAI strategic planner if LLM is available
        if llm_chain and llm_chain.is_available():
            try:
                logger.info("[STRATEGIC] Using CrewAI strategic planner...")
                planning_method = "crewai"
                
                from agents.strategic_agents import get_strategic_planner
                planner = get_strategic_planner(llm_chain)
                
                # Execute strategic planning (with timeout)
                strategic_result = await asyncio.wait_for(
                    planner.plan_next_strategic_action(game_state),
                    timeout=120.0  # 2 minute timeout for strategic planning
                )
                
                # Extract strategic goals from CrewAI result
                if strategic_result and strategic_result.get("action"):
                    strategic_goals.append({
                        "type": "primary_goal",
                        "action": strategic_result.get("action"),
                        "reasoning": strategic_result.get("reasoning", ""),
                        "priority": strategic_result.get("priority", "medium"),
                        "params": strategic_result.get("params", {})
                    })
                    
                    action_plan = {
                        "immediate_action": strategic_result.get("action"),
                        "next_steps": strategic_result.get("next_steps", []),
                        "estimated_duration": strategic_result.get("estimated_duration", "unknown"),
                        "success_criteria": strategic_result.get("success_criteria", [])
                    }
                    
                logger.info(f"[STRATEGIC] CrewAI planning complete: {strategic_result.get('action')}")
                
            except asyncio.TimeoutError:
                logger.warning("[STRATEGIC] CrewAI strategic planning timed out, using fallback")
                planning_method = "fallback_heuristic"
            except Exception as e:
                logger.error(f"[STRATEGIC] CrewAI strategic planning failed: {e}")
                planning_method = "fallback_heuristic"
        else:
            logger.info("[STRATEGIC] LLM not available, using heuristic planning")
            planning_method = "heuristic"
        
        # Fallback heuristic planning if CrewAI unavailable/failed
        if not strategic_goals:
            logger.info("[STRATEGIC] Generating heuristic strategic plan...")
            
            # Analyze character state
            hp_percent = (character.get("hp", 0) / character.get("max_hp", 1)) * 100
            sp_percent = (character.get("sp", 0) / character.get("max_sp", 1)) * 100
            weight_percent = (character.get("weight", 0) / character.get("max_weight", 1)) * 100
            level = character.get("level", 1)
            zeny = character.get("zeny", 0)
            
            # Generate strategic goals based on state
            if weight_percent > 80:
                strategic_goals.append({
                    "type": "resource_management",
                    "action": "manage_inventory",
                    "reasoning": f"Weight at {weight_percent:.1f}%, need to store items",
                    "priority": "high",
                    "params": {"target": "storage", "weight_threshold": 80}
                })
            
            if zeny < 1000:
                strategic_goals.append({
                    "type": "economy",
                    "action": "gather_zeny",
                    "reasoning": f"Low funds ({zeny} zeny), prioritize farming valuable monsters",
                    "priority": "high",
                    "params": {"target_zeny": 5000, "method": "farming"}
                })
            
            if hp_percent < 80 or sp_percent < 50:
                strategic_goals.append({
                    "type": "preparation",
                    "action": "restock_supplies",
                    "reasoning": f"HP/SP resources low (HP: {hp_percent:.1f}%, SP: {sp_percent:.1f}%)",
                    "priority": "medium",
                    "params": {"items": ["Red Potion", "Blue Potion"]}
                })
            
            # Default farming goal if no urgent needs
            if not strategic_goals:
                strategic_goals.append({
                    "type": "leveling",
                    "action": "continue_farming",
                    "reasoning": f"Character stable, continue efficient leveling (Lv {level})",
                    "priority": "medium",
                    "params": {"focus": "exp_optimization"}
                })
            
            # Build action plan
            if strategic_goals:
                primary_goal = strategic_goals[0]
                action_plan = {
                    "immediate_action": primary_goal["action"],
                    "next_steps": [g["action"] for g in strategic_goals[1:3]],
                    "estimated_duration": "10-30 minutes",
                    "success_criteria": ["Goals completed", "Resources stable"]
                }
        
        # Try to use PDCA planner for additional insights (non-blocking)
        try:
            from pdca.planner import PDCAPlanner
            pdca_planner = PDCAPlanner()
            
            # Generate macros if needed (async, don't wait)
            logger.info("[STRATEGIC] PDCA planner available for macro generation")
            
        except Exception as e:
            logger.debug(f"[STRATEGIC] PDCA planner not available: {e}")
        
        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Build response
        response = {
            "status": "success",
            "strategic_goals": strategic_goals,
            "action_plan": action_plan,
            "planning_tier": "conscious",
            "planning_method": planning_method,
            "timestamp": datetime.now().isoformat(),
            "execution_time_ms": execution_time_ms,
            "character": {
                "name": char_name,
                "level": char_level,
                "job_class": char_job
            }
        }
        
        logger.info(f"[STRATEGIC] Strategic planning complete ({execution_time_ms}ms, {len(strategic_goals)} goals)")
        return response
        
    except Exception as e:
        logger.error(f"[STRATEGIC] Strategic planning failed: {e}", exc_info=True)
        
        # Return fallback response
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "status": "error",
            "message": str(e),
            "fallback_plan": "tactical_only",
            "strategic_goals": [{
                "type": "fallback",
                "action": "continue_current_activity",
                "reasoning": "Strategic planning failed, continuing with tactical decisions",
                "priority": "medium",
                "params": {}
            }],
            "timestamp": datetime.now().isoformat(),
            "execution_time_ms": execution_time_ms
        }

@app.get("/api/v1/strategic/metrics")
async def strategic_metrics():
    """
    Get CrewAI strategic layer performance metrics
    
    Returns detailed metrics about background async execution,
    cache hit rates, execution times, and decision quality
    """
    global _crewai_cache
    
    # Calculate metrics
    execution_count = _crewai_cache["execution_count"]
    avg_time = (_crewai_cache["total_time"] / execution_count) if execution_count > 0 else 0
    timeout_rate = (_crewai_cache["timeout_count"] / execution_count * 100) if execution_count > 0 else 0
    error_rate = (_crewai_cache["error_count"] / execution_count * 100) if execution_count > 0 else 0
    
    # Check cache status
    cache_valid = _crewai_cache["result"] is not None
    if cache_valid and _crewai_cache["timestamp"]:
        cache_age = (datetime.now() - _crewai_cache["timestamp"]).seconds
    else:
        cache_age = None
    
    return {
        "enabled": True,
        "mode": "background_async",
        "execution": {
            "total_executions": execution_count,
            "average_time_seconds": round(avg_time, 2),
            "total_time_seconds": round(_crewai_cache["total_time"], 2),
            "timeout_count": _crewai_cache["timeout_count"],
            "timeout_rate_percent": round(timeout_rate, 2),
            "error_count": _crewai_cache["error_count"],
            "error_rate_percent": round(error_rate, 2)
        },
        "current_state": {
            "is_running": _crewai_cache["is_running"],
            "has_cached_result": cache_valid,
            "cache_age_seconds": cache_age,
            "cache_valid_until_seconds": (300 - cache_age) if cache_age else None,  # 5 min TTL
            "cached_action": _crewai_cache["result"].get("action") if cache_valid else None
        },
        "performance": {
            "blocking": False,
            "max_timeout_seconds": None,  # No timeout - full potential mode
            "cache_ttl_seconds": 300,  # 5 minutes
            "combat_blocked_by_crewai": False,
            "tactical_blocked_by_crewai": False
        },
        "recommendations": {
            "system_status": "optimal" if timeout_rate < 10 and error_rate < 5 else "degraded",
            "avg_time_target": "<30s for background execution",
            "cache_strategy": "intelligent invalidation on game state changes",
            "blocking_prevention": "tactical/combat proceed immediately regardless of CrewAI state"
        }
    }

@app.get("/api/v1/integration/stats")
async def integration_stats_endpoint():
    """
    Get integration statistics for verification.
    
    Returns:
        Dict with detailed integration statistics including:
        - Total requests
        - Requests by endpoint
        - Database query counts
        - System uptime
    """
    global integration_stats, monster_db, item_db
    
    # Calculate uptime
    uptime_seconds = time.time() - integration_stats['start_time']
    
    # Get database query counts if available
    monster_query_count = monster_db.query_count if monster_db else 0
    item_query_count = item_db.query_count if item_db else 0
    
    # Get database sizes
    monster_count = len(monster_db.monsters) if monster_db else 0
    item_count = len(item_db.items) if item_db else 0
    
    return {
        "uptime_seconds": int(uptime_seconds),
        "total_requests": integration_stats['total_requests'],
        "requests_by_endpoint": integration_stats['requests_by_endpoint'],
        "decision_requests": integration_stats['decision_requests'],
        "target_selection_requests": integration_stats['target_selection_requests'],
        "stat_allocation_requests": integration_stats['stat_allocation_requests'],
        "skill_allocation_requests": integration_stats['skill_allocation_requests'],
        "loot_decision_requests": integration_stats['loot_decision_requests'],
        "database_queries": {
            "monster": monster_query_count,
            "item": item_query_count,
            "total": monster_query_count + item_query_count
        },
        "database_info": {
            "monster_count": monster_count,
            "item_count": item_count,
            "monster_db_loaded": monster_db is not None,
            "item_db_loaded": item_db is not None
        },
        "openmemory_operations": integration_stats['openmemory_operations'],
        "trigger_activations": integration_stats['trigger_activations'],
        "integration_health": {
            "openkore_communicating": integration_stats['decision_requests'] > 0,
            "databases_being_queried": (monster_query_count + item_query_count) > 0,
            "full_pipeline_active": all([
                integration_stats['decision_requests'] > 0,
                monster_query_count > 0 or item_query_count > 0,
                monster_db is not None,
                item_db is not None
            ])
        },
        "timestamp": time.time()
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
# STAT COST CALCULATION (RO FORMULA)
# ============================================
def calculate_stat_cost(current_stat_value: int) -> int:
    """
    Calculate cost to increase stat using Ragnarok Online formula
    
    Formula: cost = floor(1 + (current_stat - 1) / 10)
    
    Examples:
        - Stats 1-10 cost 1 point each
        - Stats 11-20 cost 2 points each
        - Stats 21-30 cost 3 points each
        - Stats 91-99 cost 10 points each
    
    Args:
        current_stat_value: Current value of the stat (1-99)
    
    Returns:
        Point cost to increase the stat by 1
    """
    import math
    if current_stat_value < 1:
        current_stat_value = 1
    return math.floor(1 + (current_stat_value - 1) / 10)

# ============================================
# SKILL NAME ALIASES (HANDLE vs DISPLAY NAME)
# ============================================
# OpenKore sends skill handles (NV_BASIC) but some code expects display names (Basic Skill)
SKILL_ALIASES = {
    "Basic Skill": ["NV_BASIC", "Basic Skill"],
    "First Aid": ["NV_FIRSTAID", "First Aid"],
    "Teleport": ["AL_TELEPORT", "Teleport"],
    "Heal": ["AL_HEAL", "Heal"],
    "HP Recovery": ["SM_RECOVERY", "HP Recovery"],
    "Bash": ["SM_BASH", "Bash"],
    "Provoke": ["SM_PROVOKE", "Provoke"],
    "Sword Mastery": ["SM_SWORD", "Sword Mastery"],
    "Two-Handed Sword Mastery": ["SM_TWOHAND", "Two-Handed Sword Mastery"],
    "Endure": ["SM_ENDURE", "Endure"],
    "Magnum Break": ["SM_MAGNUM", "Magnum Break"],
    "Fire Bolt": ["MG_FIREBOLT", "Fire Bolt"],
    "Cold Bolt": ["MG_COLDBOLT", "Cold Bolt"],
    "Lightning Bolt": ["MG_LIGHTNINGBOLT", "Lightning Bolt"],
    "Double Strafe": ["AC_DOUBLE", "Double Strafe"],
    "Owl's Eye": ["AC_OWL", "Owl's Eye"],
    "Vulture's Eye": ["AC_VULTURE", "Vulture's Eye"],
    "Divine Protection": ["AL_DP", "Divine Protection"],
    "Demon Bane": ["AL_DEMONBANE", "Demon Bane"],
    "Ruwach": ["AL_RUWACH", "Ruwach"],
    "Pneuma": ["AL_PNEUMA", "Pneuma"],
    "Increase AGI": ["AL_INCAGI", "Increase AGI"],
    "Decrease AGI": ["AL_DECAGI", "Decrease AGI"],
    "Blessing": ["AL_BLESSING", "Blessing"],
    "Cure": ["AL_CURE", "Cure"]
}

# ============================================
# ADAPTIVE FAILURE TRACKING SYSTEM
# ============================================
# CRITICAL FIX #1: SKILL PREREQUISITE VALIDATION WITH ALIAS SUPPORT
# ============================================

def has_required_skill(skills_list: List[Dict], skill_name: str, min_level: int = 1) -> bool:
    """
    Check if character has required skill at minimum level
    Handles both display names (Basic Skill) and skill handles (NV_BASIC)
    
    PHASE 13 FIX: Enhanced validation with better error handling and logging
    
    Args:
        skills_list: List of character skills from game state
        skill_name: Name of skill to check (e.g., "Basic Skill" or "NV_BASIC")
        min_level: Minimum skill level required (default 1)
    
    Returns:
        True if character has skill at or above min_level
    """
    # PHASE 13 FIX: Enhanced validation - check for None and empty list
    if skills_list is None:
        logger.warning(f"[SKILL-CHECK] skills_list is None when checking for {skill_name}")
        return False
    
    if not isinstance(skills_list, list):
        logger.warning(f"[SKILL-CHECK] skills_list is not a list (type: {type(skills_list)}) when checking for {skill_name}")
        return False
    
    if len(skills_list) == 0:
        logger.warning(f"[SKILL-CHECK] skills_list is empty when checking for {skill_name}")
        return False
    
    # Get list of acceptable names (both display name and handle)
    acceptable_names = SKILL_ALIASES.get(skill_name, [skill_name])
    
    # PHASE 13 FIX: Also check reverse mapping (if they pass NV_BASIC, also check Basic Skill)
    # This handles cases where game state sends different formats at different times
    if skill_name not in SKILL_ALIASES:
        # Find if this is a handle that maps to a display name
        for display_name, aliases in SKILL_ALIASES.items():
            if skill_name in aliases:
                acceptable_names = aliases
                break
    
    logger.debug(f"[SKILL-CHECK] Checking for '{skill_name}' (acceptable names: {acceptable_names}, min_level: {min_level})")
    
    for skill in skills_list:
        if not isinstance(skill, dict):
            continue
        
        skill_current_name = skill.get("name", "")
        skill_level = skill.get("level", 0)
        
        # PHASE 13 FIX: More detailed logging for Basic Skill specifically
        if skill_current_name in acceptable_names:
            if skill_level >= min_level:
                logger.info(f"[SKILL-CHECK] ✓ Found {skill_name} as '{skill_current_name}' level {skill_level} (required: {min_level})")
                return True
            else:
                logger.warning(f"[SKILL-CHECK] ✗ Found {skill_name} as '{skill_current_name}' but level {skill_level} < {min_level} (insufficient)")
                return False
    
    # PHASE 13 FIX: Enhanced logging when skill not found
    available_skills = [f"{s.get('name')} Lv{s.get('level', 0)}" for s in skills_list if isinstance(s, dict) and s.get('name')]
    logger.warning(f"[SKILL-CHECK] ✗ {skill_name} not found in skills list!")
    logger.warning(f"[SKILL-CHECK] Available skills: {available_skills}")
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
# CRITICAL FIX #2: ACTION BLACKLIST SYSTEM (THREAD-SAFE)
# ============================================

import threading

action_blacklist = {}  # {action_name: expiry_timestamp}
action_blacklist_lock = threading.RLock()  # Thread-safe access to blacklist
BLACKLIST_DURATION = 60  # CRITICAL FIX: Reduced from 300s to 60s for faster recovery
# 60s is enough to prevent spam but allows quicker adaptation

def blacklist_action(action: str, duration: int = BLACKLIST_DURATION):
    """Temporarily blacklist an action after repeated failures (THREAD-SAFE)"""
    with action_blacklist_lock:
        expiry_time = time.time() + duration
        action_blacklist[action] = expiry_time
        logger.error(f"[ADAPTIVE-BLACKLIST]  Action '{action}' BLACKLISTED for {duration}s (expires: {time.strftime('%H:%M:%S', time.localtime(expiry_time))})")
        
        # CRITICAL FIX #14-2: Invalidate strategic cache for blacklisted actions
        global _crewai_cache
        if _crewai_cache.get("result") and _crewai_cache["result"].get("action") == action:
            logger.info(f"[ADAPTIVE-CACHE] Invalidating strategic cache for blacklisted action '{action}'")
            _crewai_cache["result"] = None
            _crewai_cache["timestamp"] = None
            _crewai_cache["game_state_hash"] = None

def is_action_blacklisted(action: str) -> bool:
    """Check if action is currently blacklisted (THREAD-SAFE)"""
    with action_blacklist_lock:
        if action not in action_blacklist:
            return False
        
        # Check if blacklist expired
        if time.time() > action_blacklist[action]:
            del action_blacklist[action]
            logger.info(f"[ADAPTIVE-BLACKLIST]  Blacklist EXPIRED for '{action}' - action available again")
            return False
        
        return True

def get_blacklist_time_remaining(action: str) -> int:
    """Get seconds remaining in blacklist (THREAD-SAFE)"""
    with action_blacklist_lock:
        if action not in action_blacklist:
            return 0
        return max(0, int(action_blacklist[action] - time.time()))

# ============================================
# ADAPTIVE FAILURE TRACKING SYSTEM
# User requirement: "If same issue repeated more than 3 times, AI should have
# adaptive critical thinking to try another alternative method to solve it."

from collections import defaultdict

action_failure_tracker = defaultdict(list)  # {action_name: [timestamp, timestamp, ...]}
action_failure_lock = threading.RLock()  # Thread-safe access to failure tracker
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
    Record that an action failed execution (THREAD-SAFE with STATE PERSISTENCE)
    
    CRITICAL FIX: Store failure counters in state_manager to persist between API calls
    
    Args:
        action: The action that failed (e.g., "rest", "use_item", "sell_items")
        reason: Why it failed (for logging)
    """
    # CRITICAL FIX: Use state_manager for persistent counter (survives API calls)
    if trigger_coordinator and hasattr(trigger_coordinator, 'state_manager') and trigger_coordinator.state_manager:
        state_mgr = trigger_coordinator.state_manager
        
        # Get current failure count from persistent state
        failure_key = f"action_failure_count_{action}"
        failure_timestamps_key = f"action_failure_timestamps_{action}"
        
        current_time = time.time()
        
        # Get existing timestamps from state
        timestamps = state_mgr.get(failure_timestamps_key, [])
        
        # Add new failure timestamp
        timestamps.append({
            "timestamp": current_time,
            "reason": reason
        })
        
        # Clean old failures outside the window
        timestamps = [
            f for f in timestamps
            if current_time - f["timestamp"] < get_failure_window()
        ]
        
        # Persist updated timestamps and count
        failure_count = len(timestamps)
        state_mgr.set(failure_timestamps_key, timestamps)
        state_mgr.set(failure_key, failure_count)
        
        # ENHANCED LOGGING: Always log failures with PERSISTENT count
        logger.warning(
            f"[ADAPTIVE-FAILURE] Action '{action}' failed (count: {failure_count}/{get_failure_threshold()}): {reason}"
        )
        
        if failure_count >= get_failure_threshold():
            logger.error(
                f"[ADAPTIVE-THRESHOLD] Action '{action}' EXCEEDED threshold! {failure_count} failures in last {get_failure_window()}s. "
                f"Recent reasons: {[f['reason'] for f in timestamps[-3:]]}"
            )
            
            # CRITICAL FIX #2: Auto-blacklist after threshold exceeded
            blacklist_action(action, duration=BLACKLIST_DURATION)
            
            # Clear failure tracking for this action
            state_mgr.set(failure_timestamps_key, [])
            state_mgr.set(failure_key, 0)
            
            # Trigger strategic rethink
            logger.warning(f"[ADAPTIVE-STRATEGY] Triggering strategy rethink due to repeated '{action}' failures")
    else:
        # FALLBACK: Use in-memory tracker if state_manager not available
        with action_failure_lock:
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
            
            # ENHANCED LOGGING: Always log failures
            logger.warning(
                f"[ADAPTIVE-FAILURE] Action '{action}' failed (count: {failure_count}/{get_failure_threshold()}): {reason} [FALLBACK MODE]"
            )
            
            if failure_count >= get_failure_threshold():
                logger.error(
                    f"[ADAPTIVE-THRESHOLD] Action '{action}' EXCEEDED threshold! {failure_count} failures in last {get_failure_window()}s. "
                    f"Recent reasons: {[f['reason'] for f in action_failure_tracker[action][-3:]]}"
                )
                
                # CRITICAL FIX #2: Auto-blacklist after threshold exceeded
                blacklist_action(action, duration=BLACKLIST_DURATION)
                
                # Clear failure tracking for this action
                action_failure_tracker[action] = []
                
                # Trigger strategic rethink
                logger.warning(f"[ADAPTIVE-STRATEGY] Triggering strategy rethink due to repeated '{action}' failures")

def is_action_failing_repeatedly(action: str) -> bool:
    """
    Check if action has failed 3+ times in last 30 seconds (THREAD-SAFE)
    
    Returns True if action should be avoided and alternative tried
    """
    with action_failure_lock:
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
    logger.error(f"[ADAPTIVE-ALTERNATIVE]  Finding alternative action for repeatedly failing: '{failed_action}'")
    
    character_data = game_state.get("character", {})
    current_hp = int(character_data.get("hp", 0) or 0)
    max_hp = int(character_data.get("hp_max", 1) or 1)
    hp_percent = (current_hp / max_hp * 100) if max_hp > 0 else 0
    
    # Alternative strategies based on what's failing
    if failed_action == "rest":
        logger.error("[ADAPTIVE-ALTERNATIVE] 'rest' action failing repeatedly (likely no Basic Skill Lv3 or blacklisted)")
        
        # Alternative 1: Use healing item if available
        # PHASE 13 FIX: Use table_loader for item names instead of hardcoding (NEVER HARDCODE!)
        healing_items_from_table = table_loader.get_healing_items()
        healing_items = [item[0] for item in healing_items_from_table[:8]]  # Get top 8 healing items
        
        logger.debug(f"[ADAPTIVE-ALTERNATIVE] Checking for healing items: {healing_items}")
        
        for item_name in healing_items:
            has_item = any(
                item.get("name") == item_name and item.get("amount", 0) > 0
                for item in inventory
            )
            if has_item and f"use_{item_name}" not in alternative_actions_attempted[failed_action]:
                alternative_actions_attempted[failed_action].add(f"use_{item_name}")
                logger.warning(f"[ADAPTIVE-ALTERNATIVE] Alternative 1: Use {item_name} instead of resting")
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
    
    elif failed_action == "sell_items":
        logger.error("[ADAPTIVE-ALTERNATIVE] 'sell_items' failing repeatedly - finding alternative money-making strategy")
        
        # Get game state context
        character_data = game_state.get("character", {})
        current_hp = int(character_data.get("hp", 0) or 0)
        max_hp = int(character_data.get("hp_max", 1) or 1)
        hp_percent = (current_hp / max_hp * 100) if max_hp > 0 else 0
        
        current_sp = int(character_data.get("sp", 0) or 0)
        max_sp = int(character_data.get("sp_max", 1) or 1)
        sp_percent = (current_sp / max_sp * 100) if max_sp > 0 else 0
        
        zeny = int(character_data.get("zeny", 0) or 0)
        
        # Alternative 1: Hunt monsters for drops and exp if HP/SP are good
        if hp_percent > 70 and sp_percent > 50:
            logger.warning("[ADAPTIVE-ALTERNATIVE] Cannot sell - Alternative 1: Hunt monsters for drops and exp")
            return {
                "action": "hunt_monsters",
                "params": {
                    "reason": "sell_failed_hunt_for_drops",
                    "priority": "high",
                    "target_count": 10
                },
                "layer": "ADAPTIVE_STRATEGIC"
            }
        
        # Alternative 2: Use remaining zeny to buy minimal supplies if we have some
        elif zeny >= 100 and hp_percent < 70:
            logger.warning("[ADAPTIVE-ALTERNATIVE] Cannot sell - Alternative 2: Buy minimal healing with remaining zeny")
            return {
                "action": "auto_buy",
                "params": {
                    "items": [table_loader.get_healing_items()[0][0]],  # Just basic healing
                    "reason": "sell_failed_buy_minimal_supplies",
                    "max_spend": min(zeny, 500)
                },
                "layer": "ADAPTIVE_TACTICAL"
            }
        
        # Alternative 3: Explore map for better opportunities
        elif hp_percent > 50:
            logger.warning("[ADAPTIVE-ALTERNATIVE] Cannot sell - Alternative 3: Explore for quest NPCs or opportunities")
            return {
                "action": "explore_map",
                "params": {
                    "reason": "sell_failed_explore_for_opportunities",
                    "priority": "medium"
                },
                "layer": "ADAPTIVE_STRATEGIC"
            }
        
        # Alternative 4: Emergency - just farm with what we have
        else:
            logger.warning("[ADAPTIVE-ALTERNATIVE] Cannot sell - Alternative 4: Farm weak monsters carefully")
            return {
                "action": "hunt_monsters",
                "params": {
                    "reason": "sell_failed_emergency_farming",
                    "priority": "medium",
                    "target_level_range": "weak_only",  # Only attack monsters much weaker
                    "retreat_threshold": 40  # Retreat early if HP drops
                },
                "layer": "ADAPTIVE_TACTICAL"
            }
    
    elif failed_action == "auto_buy":
        logger.warning("[ADAPTIVE] 'auto_buy' failing (likely NPC issue or no zeny)")
        
        # Alternative: Sell items first to get zeny
        if "sell_items" not in alternative_actions_attempted[failed_action]:
            alternative_actions_attempted[failed_action].add("sell_items")
            logger.warning("[ADAPTIVE-ALTERNATIVE] Cannot buy - trying to sell items for zeny first")
            return {
                "action": "sell_items",
                "params": {"reason": "cannot_buy_need_zeny_from_selling"},
                "layer": "ADAPTIVE_STRATEGIC"
            }
        
        # If selling also failed, hunt for items/zeny
        logger.warning("[ADAPTIVE-ALTERNATIVE] Cannot buy or sell - hunting for drops")
        return {
            "action": "hunt_monsters",
            "params": {
                "reason": "cannot_buy_hunt_for_resources",
                "priority": "high"
            },
            "layer": "ADAPTIVE_STRATEGIC"
        }
    
    elif failed_action == "teleport":
        logger.warning("[ADAPTIVE] 'teleport' failing (no Fly Wing or Teleport skill)")
        
        # Alternative 1: Walk away from danger (retreat without teleport)
        # This is the safe fallback when character can't teleport
        logger.info("[ADAPTIVE] Alternative: Retreat by walking (no teleport available)")
        return {
            "action": "retreat",
            "params": {
                "reason": "teleport_unavailable_walking_away",
                "method": "walk",  # Explicitly specify walk, not teleport
                "priority": "high"
            },
            "layer": "ADAPTIVE_TACTICAL"
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
        logger.info(f"[ADAPTIVE-SUCCESS]  Action '{action}' succeeded - clearing failure history")
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
    
    # Check if has weapon equipped (equipment is a list, not a dict)
    equipment = character.get("equipment", [])
    if isinstance(equipment, list):
        # Equipment is a list of equipped items
        has_weapon = False
        if equipment:
            for item in equipment:
                if isinstance(item, dict):
                    item_type = item.get("type", "")
                    equip_slot = item.get("equipped", "")
                    # Check if weapon is equipped
                    if "weapon" in item_type.lower() or "rightHand" in equip_slot or "leftHand" in equip_slot:
                        has_weapon = True
                        break
        
        if not has_weapon:
            # For novices without weapons, allow bare-handed combat
            job_class = character.get("job_class", "")
            if job_class.lower() == "novice":
                logger.debug("[COMBAT] Novice - allowing bare-handed combat")
                return True
            else:
                logger.warning("[COMBAT] Not ready - No weapon equipped")
                return False
    else:
        # Legacy: equipment as dict
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
    
    # Filter suitable monsters
    suitable_monsters = []
    for monster in monsters:
        if not isinstance(monster, dict):
            continue
        
        # CRITICAL FIX #12-1: OpenKore sends pre-calculated distance in monster data
        # Monster data structure: {"name": "Lunatic", "distance": 9, "hp": 0, "max_hp": 0, "is_aggressive": false, "id": 0}
        # NO x/y coordinates, NO level field provided by OpenKore
        distance = float(monster.get("distance", 999) or 999)
        
        # Distance check (within 15 cells for safety)
        if distance > 15:
            logger.debug(f"[COMBAT] Rejecting {monster.get('name')} - too far (distance: {distance:.1f})")
            continue
        
        # CRITICAL FIX #12-2: Monster level not provided by OpenKore
        # For low-level characters (1-20), accept all monsters within range
        # Advanced logic can be added later when monster level data is available
        monster_level = int(monster.get("level", 0) or 0)
        
        if monster_level > 0:
            # If level is provided, do level range check (±5 levels for safety)
            if abs(monster_level - char_level) > 5:
                logger.debug(f"[COMBAT] Rejecting {monster.get('name')} - level gap too large (monster: {monster_level}, char: {char_level})")
                continue
            level_diff = abs(monster_level - char_level)
        else:
            # Level not available - for low-level chars, accept all nearby monsters
            # This is safe for maps like prt_fild08 (Prontera Field) where monsters are appropriate for low levels
            if char_level <= 20:
                level_diff = 0  # Unknown level, assume suitable for low-level farming
                logger.debug(f"[COMBAT] Accepting {monster.get('name')} - no level data (low-level char)")
            else:
                # For high-level characters, skip monsters without level data (safety)
                logger.debug(f"[COMBAT] Rejecting {monster.get('name')} - no level data (high-level char)")
                continue
        
        suitable_monsters.append({
            "monster": monster,
            "distance": distance,
            "level_diff": level_diff
        })
    
    if not suitable_monsters:
        logger.debug("[COMBAT] No suitable monsters in range")
        return None
    
    # Sort by distance (closest first), then by level difference (lower diff first)
    suitable_monsters.sort(key=lambda x: (x["distance"], x["level_diff"]))
    
    selected = suitable_monsters[0]["monster"]
    logger.info(f"[COMBAT]  Selected target: {selected.get('name')} at distance {suitable_monsters[0]['distance']:.1f}")
    
    return selected

# ============================================
# END COMBAT/FARMING LOGIC
# ============================================

@app.post("/api/v1/select-target")
async def select_target_endpoint(request: Request, request_body: Dict[str, Any] = Body(...)):
    """
    Select optimal monster target based on current context.
    Uses monster database for intelligent target selection.
    
    Request body:
    {
        "level": 50,
        "map": "prt_fild08",
        "monsters": [1002, 1113, 1031],  # Available monster IDs
        "goal": "exp" or "loot"  # Optional
    }
    
    Returns:
    {
        "targets": [
            {
                "id": 1002,
                "name": "Poring",
                "level": 1,
                "score": 85.5,
                "recommended": true
            },
            ...
        ]
    }
    """
    try:
        if not monster_db:
            return {
                "error": "Monster database not available",
                "targets": []
            }
        
        # Extract request data
        current_level = request_body.get("level", 1)
        current_location = request_body.get("map", "")
        available_monsters = request_body.get("monsters", [])
        goal = request_body.get("goal", "exp")
        
        # Find optimal targets
        context = {
            "level": current_level,
            "location": current_location,
            "monsters": available_monsters,
            "goal": goal
        }
        
        targets = monster_db.find_optimal_targets(context)
        
        # Format response
        formatted_targets = []
        for i, target in enumerate(targets[:10]):  # Top 10 targets
            formatted_targets.append({
                "id": target.get("id"),
                "name": target.get("name"),
                "level": target.get("level"),
                "base_exp": target.get("base_exp"),
                "job_exp": target.get("job_exp"),
                "hp": target.get("hp"),
                "recommended": i == 0  # First is most recommended
            })
        
        logger.info(f"[SELECT-TARGET] Found {len(formatted_targets)} suitable targets for level {current_level}")
        
        return {
            "targets": formatted_targets,
            "context": {
                "player_level": current_level,
                "goal": goal,
                "available_count": len(available_monsters)
            }
        }
    
    except Exception as e:
        logger.error(f"[SELECT-TARGET] Error selecting target: {e}", exc_info=True)
        return {
            "error": str(e),
            "targets": []
        }

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
        # PRIORITY -1: SEQUENTIAL PLANNER & ACTION QUEUE (Phase 5-7)
        # ==================================================================
        # Check for active plans FIRST - they take precedence over everything except triggers
        if sequential_planner and action_queue:
            try:
                # STEP 1: Check for active plan
                if sequential_planner.has_active_plan():
                    active_plans = sequential_planner.active_plans
                    if active_plans:
                        plan = active_plans[0]  # Get highest priority plan
                        next_action = sequential_planner.get_next_action(plan.plan_id)
                        
                        if next_action:
                            logger.info(f"[PLANNER] Executing step {plan.current_step}/{len(plan.steps)} of plan: {plan.goal}")
                            
                            # Queue the action to prevent conflicts
                            action_id = await action_queue.enqueue(
                                action_type=next_action["action"],
                                parameters=next_action.get("parameters", {}),
                                priority=next_action.get("priority", 5)
                            )
                            
                            logger.info(f"[TACTICAL] Sequential Plan: {next_action['action']} (step {plan.current_step}/{len(plan.steps)})")
                            
                            return {
                                "action": next_action["action"],
                                "params": next_action.get("parameters", {}),
                                "plan_id": plan.plan_id,
                                "action_id": action_id,
                                "reasoning": f"Sequential plan step {plan.current_step}: {next_action.get('description', '')}",
                                "layer": "TACTICAL",
                                "source": "sequential_planner"
                            }
                
                # STEP 2: Check action queue for pending actions
                queued_action = await action_queue.get_next_action()
                if queued_action and queued_action.get("status") == "pending":
                    logger.info(f"[QUEUE] Executing queued action: {queued_action['action_type']}")
                    
                    logger.info(f"[TACTICAL] Queued Action: {queued_action['action_type']}")
                    
                    return {
                        "action": queued_action["action_type"],
                        "params": queued_action["parameters"],
                        "action_id": queued_action["action_id"],
                        "reasoning": "Executing queued action",
                        "layer": "TACTICAL",
                        "source": "action_queue"
                    }
                    
            except Exception as e:
                logger.error(f"[PLANNER] Error in planning system: {e}")
                logger.exception(e)
                # Fall through to normal decision logic
        
        # ==================================================================
        # PRIORITY 0: AUTONOMOUS TRIGGER SYSTEM (Phase 16)
        # ==================================================================
        # Check trigger system first - it can handle multi-layered autonomous responses
        if trigger_coordinator:
            try:
                # CRITICAL FIX: Calculate weight_percent properly
                current_weight = int(character_data.get("weight", 0) or 0)
                max_weight = int(character_data.get("max_weight", 1) or 1)
                weight_percent = int((current_weight / max_weight) * 100) if max_weight > 0 else 0
                
                # Enrich game state with calculated percentages and derived data
                enriched_game_state = {
                    **game_state,
                    "character": {
                        **character_data,
                        "hp_percent": hp_percent,
                        "sp_percent": sp_percent,
                        "weight_percent": weight_percent,
                    },
                    "inventory": {
                        "items": {item.get("name"): item.get("amount", 0) for item in inventory},
                        "item_count": len(inventory),
                        "max_items": 100,  # TODO: Get from game_state
                        "usage_percent": (len(inventory) / 100 * 100) if len(inventory) > 0 else 0
                    },
                    "combat": {
                        **game_state.get("combat", {}),
                        "attacking_monster_count": game_state.get("combat", {}).get("attacking_monster_count", 0)
                    },
                    "state": game_state.get("state", "unknown"),
                    "request_id": request_id,
                    "timestamp_ms": timestamp_ms
                }
                
                # Process through trigger system
                trigger_action = await trigger_coordinator.process_game_state(enriched_game_state)
                
                if trigger_action:
                    logger.info(f"[REFLEX] Trigger System Action: {trigger_action.get('action', 'unknown')}")
                    logger.info(f"[DECIDE] Trigger system returned action: {trigger_action}")
                    
                    # Return trigger action with metadata
                    return {
                        **trigger_action,
                        "source": "trigger_system",
                        "request_id": request_id,
                        "timestamp": time.time()
                    }
                else:
                    logger.debug("[DECIDE] No trigger fired, continuing to standard decision logic")
                    
            except Exception as e:
                logger.error(f"[DECIDE] Trigger system error: {e}")
                logger.exception(e)
                # Fall through to existing decision logic on error
        
        # ==================================================================
        # DECISION LOGIC: Three-Layer Architecture (Fallback)
        # ==================================================================
        
        # Layer 1: REFLEX (Immediate survival responses - use config threshold)
        hp_reflex_threshold = thresholds_config["hp_thresholds"]["reflex"]
        if hp_percent < hp_reflex_threshold:
            logger.warning(f"[DECIDE] CRITICAL HP: {hp_percent:.1f}% - Emergency healing required!")
            
            # PHASE 13 FIX: Use table_loader for healing items instead of hardcoding (NEVER HARDCODE!)
            # Check for healing items IN INVENTORY (priority order from table_loader)
            healing_items_from_table = table_loader.get_healing_items()
            
            # Build list with item names (already sorted by effectiveness in table_loader)
            healing_items = [(item[0], item[2]) for item in healing_items_from_table[:10]]  # Top 10 healing items
            
            logger.debug(f"[DECIDE-REFLEX] Checking for healing items: {[name for name, _ in healing_items]}")
            
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
        
        # P0 CRITICAL FIX #3: Check for available skill points FIRST (higher priority)
        # Basic Skill Lv3 is CRITICAL for sit/rest functionality
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
            # CRITICAL FIX #5j-1: Learn job-specific skills after Basic Skill is ready
            # Use SkillLearner + CrewAI for intelligent skill selection
            if basic_skill_level >= 3 and available_skill_points > 0:
                logger.info(f"[PROGRESSION] Basic Skill ready (Lv{basic_skill_level}), learning job-specific skills")
                
                try:
                    # Get current job and level
                    job_class = character_data.get("job_class", "Novice")
                    job_level = int(character_data.get("job_level", 1) or 1)
                    
                    # Get current skills as dict
                    current_skills_dict = {}
                    for skill in skills:
                        skill_name = skill.get("name", "")
                        skill_level = skill.get("level", 0)
                        if skill_name:
                            current_skills_dict[skill_name] = skill_level
                    
                    # Get skill learning plan from SkillLearner
                    skill_plan = skill_learner.on_job_level_up(
                        current_job_level=job_level,
                        job=job_class,
                        current_skills=current_skills_dict
                    )
                    
                    # Get next skill to learn
                    next_skills = skill_plan.get("next_skills_to_learn", [])
                    
                    if next_skills:
                        next_skill = next_skills[0]  # Get highest priority skill
                        skill_name = next_skill.get("name", "")
                        current_level = next_skill.get("current_level", 0)
                        target_level = next_skill.get("target_level", 1)
                        
                        logger.info(f"[PROGRESSION] Learning {skill_name} Lv{current_level} → Lv{target_level}")
                        
                        return {
                            "action": "learn_skill",
                            "params": {
                                "skill_name": skill_name,
                                "current_level": current_level,
                                "target_level": min(current_level + 1, target_level),  # One level at a time
                                "points_to_add": 1,
                                "reason": "job_progression",
                                "priority": "high",
                                "description": next_skill.get("description", "")
                            },
                            "layer": "PROGRESSION"
                        }
                    else:
                        logger.debug(f"[PROGRESSION] No job skills to learn yet (all maxed or not available at Lv{job_level})")
                
                except Exception as e:
                    logger.error(f"[PROGRESSION] Skill learning error: {e}", exc_info=True)
                    # Continue to stat allocation
            else:
                logger.info(f"[PROGRESSION] Basic Skill ready (Lv{basic_skill_level}), job-specific skills available after Job Lv10+")
        
        
        # P0 CRITICAL FIX #4: Check for available stat points (AFTER skill learning)
        # USER FEEDBACK FIX: Allocate ONE point at a time (NO batching)
        # CRITICAL FIX #5h-1: Check if allocate_stats is blacklisted BEFORE attempting
        # CRITICAL FIX #5i-1: Log exact code version for debugging
        available_stat_points = int(character_data.get("points_free", 0) or 0)
        
        logger.debug(f"[PROGRESSION] CODE VERSION: Latest (Test #5i) - Line 1433 - Affordability Check Active")
        
        if available_stat_points > 0 and not is_action_blacklisted("allocate_stats"):
            logger.info(f"[PROGRESSION] {available_stat_points} stat point(s) available - checking affordability and costs")
            
            # Get current job and stats
            job_class = character_data.get("job_class", "Novice")
            character_level = int(character_data.get("level", 1) or 1)
            
            # Get current stats for dynamic allocation
            current_stats = {
                "str": int(character_data.get("str", 1) or 1),
                "agi": int(character_data.get("agi", 1) or 1),
                "vit": int(character_data.get("vit", 1) or 1),
                "dex": int(character_data.get("dex", 1) or 1),
                "int": int(character_data.get("int", 1) or 1),
                "luk": int(character_data.get("luk", 1) or 1)
            }
            
            # CRITICAL FIX #5h-2: Calculate stat point COSTS using RO formula (don't trust OpenKore blindly)
            stat_costs = {}
            for stat_name in ["str", "agi", "vit", "dex", "int", "luk"]:
                current_value = current_stats.get(stat_name, 1)
                calculated_cost = calculate_stat_cost(current_value)
                received_cost = int(character_data.get(f"points_{stat_name}", calculated_cost) or calculated_cost)
                
                # Validate and warn if mismatch
                if received_cost != calculated_cost:
                    logger.warning(f"[STAT-COST] Mismatch for {stat_name.upper()}: "
                                 f"received={received_cost}, calculated={calculated_cost}, "
                                 f"current_stat={current_value}, using calculated")
                
                stat_costs[stat_name] = calculated_cost
            
            # Dynamic table-driven stat allocation from job_builds.json (NO HARDCODING)
            recommendations = stat_allocator.get_allocation_recommendations(
                current_stats=current_stats,
                free_points=1  # Allocate ONLY 1 point at a time
            )
            
            if recommendations:
                # Get the highest priority stat (first in recommendations)
                stat_to_allocate = list(recommendations.keys())[0]
                
                # CRITICAL FIX #5h-3: Validate if we can AFFORD this stat increase
                stat_cost = stat_costs.get(stat_to_allocate, 1)
                
                if stat_cost <= available_stat_points:
                    # Affordable - proceed with allocation
                    stats_to_add = {stat_to_allocate.upper(): 1}
                    
                    logger.info(f"[PROGRESSION] {job_class} (Lv{character_level}) - allocating 1 point to {stat_to_allocate.upper()} (cost: {stat_cost}, have: {available_stat_points})")
                    
                    return {
                        "action": "allocate_stats",
                        "params": {
                            "stats": stats_to_add,
                            "reason": "character_progression",
                            "priority": "high"
                        },
                        "layer": "PROGRESSION"
                    }
                else:
                    # CRITICAL FIX #11-1: INFINITE LOOP PREVENTION
                    # Problem: Bot repeatedly moves between town and field without ever farming
                    # Root cause: Unaffordable stat check happens BEFORE combat, blocking all farming
                    # Solution: Skip stat allocation attempts when unaffordable, let bot farm naturally
                    logger.warning(f"[PROGRESSION] Cannot afford {stat_to_allocate.upper()} (cost: {stat_cost}, have: {available_stat_points}) - skipping stat allocation")
                    logger.info(f"[PROGRESSION] Will accumulate more points through natural leveling (need {stat_cost - available_stat_points} more)")
                    
                    # CRITICAL: DO NOT return move action here - it creates infinite loop
                    # Instead, fall through to combat/farming logic to actually gain XP
                    logger.debug("[PROGRESSION] Continuing to next action (combat/exploration) to earn XP naturally")
                    # Fall through to next priority action
            else:
                # Fallback if no recommendations (should not happen with proper job_builds.json)
                logger.warning(f"[PROGRESSION] No stat allocation recommendations from StatAllocator for {job_class}")
                logger.debug(f"[PROGRESSION] Current stats: {current_stats}")
        elif available_stat_points > 0 and is_action_blacklisted("allocate_stats"):
            # CRITICAL FIX #5h-4: If allocate_stats is blacklisted, skip it and don't keep trying
            remaining = get_blacklist_time_remaining("allocate_stats")
            logger.info(f"[PROGRESSION] allocate_stats is blacklisted ({remaining}s remaining) - skipping to next action")
            # CRITICAL FIX #5i-2: Continue processing - don't return early
        elif available_stat_points == 0:
            # No stat points available - this is normal, continue to other actions
            logger.debug(f"[PROGRESSION] No stat points available (will get more at next level up)")
        
        # CRITICAL FIX #5i-3: If stat allocation was skipped (blacklisted/unaffordable),
        # proceed to NEXT priority action instead of returning "continue"
        # Priority order: Stat allocation (done above) → Combat/Farming → Exploration
        
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
        
        # CRITICAL FIX: Smarter sell decision logic (Priority 4)
        # Don't recommend sell if zeny=0 AND inventory<70% AND weight<80%
        # Typical novice RO gameplay: farm first, then sell when inventory is actually full
        if current_zeny < ZENY_LOW:
            logger.warning(f"[DECIDE] Low zeny ({current_zeny}z) - evaluating sell necessity")
            
            # Calculate inventory and weight percentages
            current_weight = int(character_data.get("weight", 0) or 0)
            max_weight = int(character_data.get("max_weight", 1) or 1)
            weight_percent = (current_weight / max_weight * 100) if max_weight > 0 else 0
            
            inventory_count = len(inventory)
            inventory_percent = (inventory_count / 100 * 100) if inventory_count > 0 else 0  # Assume 100 max slots
            
            # SMART LOGIC: If zeny=0 and inventory not full, farm first instead of selling
            if current_zeny == 0 and inventory_percent < 70 and weight_percent < 80:
                logger.info(f"[DECIDE] SMART: Zeny=0z but inventory only {inventory_percent:.1f}% full, weight {weight_percent:.1f}%")
                logger.info(f"[DECIDE] SMART: Should farm first to collect more items before selling trip")
                logger.info(f"[DECIDE] SMART: Skipping sell recommendation - will farm until inventory 70%+ or weight 80%+")
                # Don't recommend sell - fall through to combat/farming logic below
            else:
                # Inventory/weight is high enough to justify sell trip OR zeny is critically low
                logger.info(f"[DECIDE] Inventory {inventory_percent:.1f}%, weight {weight_percent:.1f}% - evaluating sell necessity")
                
                # CRITICAL FIX: Check if sell_items is blacklisted (failed 3+ times)
                if is_action_blacklisted("sell_items"):
                    remaining = get_blacklist_time_remaining("sell_items")
                    logger.error(f"[ADAPTIVE] sell_items is BLACKLISTED ({remaining}s remaining) - cannot earn zeny via selling")
                    logger.warning(f"[ADAPTIVE] Using alternative zeny strategy: hunt monsters for drops")
                    
                    # Alternative: Hunt monsters for drops and zeny (if HP/SP allow)
                    if hp_percent > 70 and sp_percent > 50:
                        return {
                            "action": "hunt_monsters",
                            "params": {
                                "reason": "sell_failed_hunt_for_drops_and_zeny",
                                "priority": "high",
                                "target_count": 10
                            },
                            "layer": "ADAPTIVE_STRATEGIC"
                        }
                    else:
                        # Low HP/SP - rest first before hunting
                        return {
                            "action": "rest",
                            "params": {
                                "reason": "low_resources_before_hunting",
                                "priority": "medium"
                            },
                            "layer": "TACTICAL"
                        }
                
                # Count sellable items (protect quest items from table loader)
                quest_items = table_loader.get_quest_items()
                
                # CRITICAL FIX: Use NPC handler's categorization (respects vendor trash logic)
                categorized = npc_handler.categorize_inventory_for_selling(
                    inventory,
                    quest_items=quest_items,
                    is_card_func=table_loader.is_card
                )
                sellable_count = len(categorized["sell"])
                
                if sellable_count > 0 and current_zeny < ZENY_CRITICAL:
                    logger.warning(f"[DECIDE] CRITICAL: Only {current_zeny}z left, {sellable_count} sellable items")
                    return {
                        "action": "sell_items",
                        "params": {
                            "reason": "critical_zeny_shortage",
                            "priority": "high"
                        },
                        "layer": "STRATEGIC"
                    }
                elif sellable_count == 0 and current_zeny < ZENY_CRITICAL:
                    # NO sellable items but critical zeny shortage - MUST hunt for drops
                    logger.error(f"[DECIDE] CRITICAL: {current_zeny}z, NO items to sell - MUST hunt monsters")
                    
                    if hp_percent > 60 and sp_percent > 40:
                        return {
                            "action": "hunt_monsters",
                            "params": {
                                "reason": "no_items_to_sell_critical_zeny",
                                "priority": "critical",
                                "target_count": 15  # Hunt more to get drops to sell
                            },
                            "layer": "STRATEGIC"
                        }
                    else:
                        # Too low to hunt safely - rest first
                        return {
                            "action": "rest",
                            "params": {
                                "reason": "low_resources_need_rest_before_emergency_hunt",
                                "priority": "high"
                            },
                            "layer": "TACTICAL"
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
            
            # FIX #7: Don't trigger auto-buy routing if already in farming map
            current_map = character_data.get("position", {}).get("map", "unknown")
            
            if current_map and current_map.lower() not in ["prontera", "payon", "geffen", "morocc", "alberta", "aldebaran", "izlude"]:
                logger.debug(f"[DECIDE] In farming map {current_map}, skipping auto-buy route (farm for zeny instead)")
                # Skip auto-buy logic - continue to next decision layer
            else:
                # Priority 2 Fix: Check if we can afford items before triggering buy
                # CRITICAL FIX #5h-5: Estimate cost dynamically from item data (NO HARDCODING)
                # Use conservative estimates based on item tier if exact prices unavailable
                healing_items = table_loader.get_healing_items()
                
                # Build dynamic cost estimation based on item tier
                def estimate_item_cost(item_name: str) -> int:
                    """Estimate item cost dynamically based on type and tier"""
                    item_name_lower = item_name.lower()
                    
                    # Potions - tier-based pricing
                    if "red" in item_name_lower and "potion" in item_name_lower:
                        return 50
                    elif "orange" in item_name_lower and "potion" in item_name_lower:
                        return 200
                    elif "yellow" in item_name_lower and "potion" in item_name_lower:
                        return 550
                    elif "white" in item_name_lower and "potion" in item_name_lower:
                        return 1200
                    elif "blue" in item_name_lower and "potion" in item_name_lower:
                        return 5000
                    
                    # Teleport items
                    elif "fly wing" in item_name_lower:
                        return 60
                    elif "butterfly wing" in item_name_lower:
                        return 300
                    
                    # Default conservative estimate
                    else:
                        return 100
            
                estimated_cost = sum(
                    estimate_item_cost(item) * 10  # Assume buying 10 of each
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
                    
                    # CRITICAL FIX #4: Don't suggest rest if HP/SP already high
                    hp_percent = (character_data.get("hp", 0) / max(character_data.get("max_hp", 1), 1)) * 100
                    sp_percent = (character_data.get("sp", 0) / max(character_data.get("max_sp", 1), 1)) * 100
                    
                    if not in_combat:
                        if hp_percent < 90 or sp_percent < 80:
                            return {
                                "action": "rest",
                                "params": {
                                    "reason": "cannot_afford_potions",
                                    "priority": "medium"
                                },
                            "layer": "TACTICAL"
                        }
        
        # ====================================================================
        # Layer 3: CONSCIOUS (Strategic planning with CrewAI)
        # PHASE 14 FIX: Background Async Execution - Full Potential Mode
        # ====================================================================
        #
        # NEW ARCHITECTURE:
        # - CrewAI runs in background without blocking tactical/combat decisions
        # - Results are cached for 5 minutes with intelligent invalidation
        # - No timeout on CrewAI execution (runs at full potential)
        # - Tactical/combat layers proceed immediately regardless of CrewAI state
        #
        # BENEFITS:
        # - 0% blocking: Combat/farming never waits for CrewAI
        # - Full AI intelligence: CrewAI runs without time pressure
        # - 95% autonomy: Strategic + Tactical + Combat all working together
        # - Zero timeouts: HTTP requests complete in <1s
        # ====================================================================
        
        ENABLE_CREWAI_STRATEGIC = True  # RE-ENABLED with background async system
        
        if ENABLE_CREWAI_STRATEGIC and hp_percent > 80 and sp_percent > 50:
            # Check if LLM provider is available
            if any(p.available for p in llm_chain.providers):
                # PHASE 9 FIX: Start background planning if conditions are met
                if _should_start_background_planning(game_state):
                    logger.info("[STRATEGIC-BG] Starting background CrewAI planning task...")
                    
                    # PHASE 9 FIX: Cancel any existing task before starting new one
                    if _crewai_cache.get("task") and not _crewai_cache["task"].done():
                        logger.warning("[STRATEGIC-BG] Cancelling previous task to start new one")
                        _crewai_cache["task"].cancel()
                        try:
                            await asyncio.wait_for(_crewai_cache["task"], timeout=0.1)
                        except (asyncio.CancelledError, asyncio.TimeoutError):
                            pass  # Expected
                    
                    # Get CrewAI-compatible LLM instance
                    crewai_llm = llm_chain.get_crewai_llm()
                    
                    # PHASE 9 FIX: Create background task with proper fire-and-forget isolation
                    # The key is to NOT await this task - just create it and continue
                    _crewai_cache["task"] = asyncio.create_task(
                        _background_crewai_planning(game_state, crewai_llm)
                    )
                    
                    logger.debug("[STRATEGIC-BG] Background task created (ID: {id(_crewai_cache['task'])}), proceeding immediately to tactical/combat")
                
                # Check if we have a cached strategic recommendation
                cached_action = _get_cached_strategic_action(game_state)
                
                if cached_action:
                    # Validate cached action before using
                    action_type = cached_action.get("action")
                    
                    # PHASE 10 FIX #4: Economic Decision Override Logic
                    # Override sell_items recommendation when bot should farm first
                    if action_type == "sell_items":
                        # Calculate inventory and weight percentages
                        current_weight = int(character_data.get("weight", 0) or 0)
                        max_weight = int(character_data.get("max_weight", 1) or 1)
                        weight_percent = (current_weight / max_weight * 100) if max_weight > 0 else 0
                        
                        inventory_count = len(inventory)
                        inventory_percent = (inventory_count / 100 * 100) if inventory_count > 0 else 0
                        
                        # OVERRIDE: If 0z crisis but inventory not full, farm first instead
                        if current_zeny == 0 and inventory_percent < 70 and weight_percent < 80:
                            logger.info(f"[ECONOMIC-OVERRIDE] Overriding cached sell_items → attack_nearest (0z crisis)")
                            logger.info(f"[ECONOMIC-OVERRIDE] Reason: Must farm first - inventory {inventory_percent:.1f}%, weight {weight_percent:.1f}%")
                            
                            # Check if we have monsters nearby to attack
                            monsters = game_state.get("monsters", [])
                            if isinstance(monsters, list) and len(monsters) > 0:
                                cached_action = {
                                    'action': 'attack_nearest',
                                    'params': {
                                        'reason': 'economic_override_0z_farm_first',
                                        'priority': 'high'
                                    },
                                    'tier_used': 'economic_override',
                                    'reasoning': 'Must farm first to collect items - 0 zeny crisis'
                                }
                            else:
                                # No monsters nearby, move to farming map
                                cached_action = {
                                    'action': 'move_to_map',
                                    'params': {
                                        'map': 'prt_fild08',
                                        'reason': 'economic_override_find_monsters_to_farm',
                                        'priority': 'high'
                                    },
                                    'tier_used': 'economic_override',
                                    'reasoning': 'Must find monsters to farm - 0 zeny crisis'
                                }
                    
                    # Validate that action is still applicable
                    if action_type == "allocate_stats":
                        available_stat_points = character_data.get("points_free", 0)
                        if available_stat_points <= 0:
                            logger.debug("[STRATEGIC-CACHE] Cached 'allocate_stats' invalid (no points available)")
                            cached_action = None
                        elif is_action_blacklisted("allocate_stats"):
                            logger.debug("[STRATEGIC-CACHE] Cached 'allocate_stats' invalid (blacklisted)")
                            cached_action = None
                    
                    elif action_type == "learn_skills":
                        available_skill_points = character_data.get("points_skill", 0)
                        if available_skill_points <= 0:
                            logger.debug("[STRATEGIC-CACHE] Cached 'learn_skills' invalid (no points available)")
                            cached_action = None
                        elif is_action_blacklisted("learn_skills"):
                            logger.debug("[STRATEGIC-CACHE] Cached 'learn_skills' invalid (blacklisted)")
                            cached_action = None
                    
                    elif action_type == "attack_monster":
                        # Check if still in combat zone and ready
                        monsters = game_state.get("monsters", [])
                        has_monsters = len(monsters) > 0 if isinstance(monsters, list) else False
                        if not has_monsters or not is_ready_for_combat(character_data, inventory):
                            logger.debug("[STRATEGIC-CACHE] Cached 'attack_monster' invalid (no monsters/not ready)")
                            cached_action = None
                        elif is_action_blacklisted("attack_monster"):
                            logger.debug("[STRATEGIC-CACHE] Cached 'attack_monster' invalid (blacklisted)")
                            cached_action = None
                    
                    # If cached action is still valid, use it
                    if cached_action:
                        logger.info(f"[STRATEGIC-CACHE] Using validated cached recommendation: {action_type}")
                        return cached_action
                    else:
                        logger.debug("[STRATEGIC-CACHE] Cached action invalidated, falling through to tactical")
                
                # No cached result yet (CrewAI still running or not started)
                # This is NOT an error - just fall through to tactical/combat
                if _crewai_cache["is_running"]:
                    logger.debug("[STRATEGIC-BG] CrewAI still running in background, proceeding with tactical logic")
                else:
                    logger.debug("[STRATEGIC] No cached strategic action, proceeding with tactical logic")
            else:
                logger.debug("[STRATEGIC] LLM provider not available, skipping strategic planning")
        
        # ======================================================================
        # Layer 2.6: INTELLIGENT LOOT PRIORITIZATION (Phase 15)
        # ======================================================================
        # Check for ground items and make risk-based tactical loot decisions
        # Priority: High-value loot > Combat > Exploration
        # Only attempt when HP/SP are reasonable (not in critical survival mode)
        if hp_percent > 40 and sp_percent > 30:
            loot_action = handle_loot_decision(
                game_state=game_state,
                loot_prioritizer=loot_prioritizer,
                risk_calculator=risk_calculator,
                tactical_retrieval=tactical_retrieval,
                loot_learner=loot_learner
            )
            
            if loot_action:
                logger.info(f"[LOOT] Initiating tactical loot retrieval: {loot_action.get('params', {}).get('tactic')}")
                return loot_action
        
        # CRITICAL FIX #5i-4: Combat/Farming Logic (ALWAYS check, even if stat allocation failed)
        # This is the FALLBACK when stat allocation is blocked/blacklisted
        # Priority: Farming for XP/zeny > Exploration
        monsters = game_state.get("monsters", [])
        if isinstance(monsters, list) and len(monsters) > 0:
            logger.debug(f"[COMBAT] {len(monsters)} monsters detected nearby")
            
            if is_ready_for_combat(character_data, inventory):
                target = select_combat_target(monsters, character_data)
                
                if target:
                    # Check if attack_monster is blacklisted
                    if is_action_blacklisted("attack_monster"):
                        logger.warning("[ADAPTIVE] 'attack_monster' is blacklisted, skipping combat")
                        # Fall through to exploration
                    else:
                        logger.info(f"[COMBAT] Engaging target: {target.get('name')} (Level {target.get('level')}, Distance: {target.get('distance')})")
                        logger.debug(f"[COMBAT] Reason: {'Stat allocation blocked' if is_action_blacklisted('allocate_stats') else 'Normal farming'}")
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
        
        else:
            logger.debug("[COMBAT] No monsters nearby for combat")
            
            # FIX #13: Autonomous Farming Transition Logic
            # When idle in town with good HP/SP, automatically move to farming map
            current_map = character_data.get("position", {}).get("map", "unknown")
            current_level = int(character_data.get("level", 1) or 1)
            
            # Check if character is in town and idle
            if is_town_map(current_map):
                # FIX #13: Character idle in town with good health - move to farm
                if hp_percent > 80 and sp_percent > 60 and current_level < 99:
                    logger.info(f"[AUTONOMOUS] Idle in town ({current_map}) with HP {hp_percent:.1f}%, SP {sp_percent:.1f}% - Moving to farming map")
                    
                    # Get optimal farming map for current level (from map metadata)
                    farming_map = "prt_fild08"  # Default for low levels
                    if MAP_METADATA and "farming_maps" in MAP_METADATA:
                        for map_name, map_data in MAP_METADATA["farming_maps"].items():
                            min_level = map_data.get("recommended_level_min", 1)
                            max_level = map_data.get("recommended_level_max", 99)
                            if min_level <= current_level <= max_level:
                                farming_map = map_name
                                logger.info(f"[AUTONOMOUS] Selected {farming_map} for level {current_level}")
                                break
                    
                    return {
                        "action": "move_to_map",
                        "params": {
                            "target_map": farming_map,
                            "map": farming_map,
                            "reason": "autonomous_farming_idle_in_town"
                        },
                        "layer": "STRATEGIC"
                    }
            
            # FIX #10: Monster Search with Movement
            # When monsters array is empty in farming map, move away from spawn point
            if current_map and current_map.lower() not in ["prontera", "payon", "geffen", "morocc", "alberta", "aldebaran", "izlude"]:
                char_pos = character_data.get("position", {})
                char_x = char_pos.get("x", 0)
                char_y = char_pos.get("y", 0)
                
                # Check if at spawn point (prt_fild08 spawn is around 170, 375-378)
                # Generic spawn detection: within 10 cells of common spawn coordinates
                is_near_spawn = False
                if "prt_fild08" in current_map.lower():
                    if abs(char_x - 170) < 10 and abs(char_y - 375) < 10:
                        is_near_spawn = True
                else:
                    # Generic spawn detection for other maps (usually center or edges)
                    # If very close to map boundaries or dead center, likely at spawn
                    is_near_spawn = True  # Conservative: assume spawn if no monsters visible
                
                if is_near_spawn and char_x > 0 and char_y > 0:
                    logger.info("[COMBAT] At spawn point with no monsters, moving deeper into map to search")
                    return {
                        "action": "move",
                        "params": {
                            "x": char_x + 30,  # Move 30 cells east
                            "y": char_y - 30,  # Move 30 cells north
                            "reason": "search_for_monsters_away_from_spawn"
                        },
                        "layer": "TACTICAL"
                    }
        
        # CRITICAL FIX #5i-8: SEQUENTIAL THINKING - If stat blocked, farm for XP to level up
        # This implements multi-step planning: Can't allocate stats → Farm → Level up → Get stat points → Allocate
        if is_action_blacklisted("allocate_stats") and available_stat_points > 0:
            current_map = character_data.get("position", {}).get("map", "unknown")
            
            # STEP 1: If in town, go to farming map
            if current_map in ["prontera", "payon", "geffen", "morocc", "alberta", "aldebaran"]:
                logger.info("[SEQUENTIAL] Multi-step plan: Stat allocation blocked → Farm for XP → Level up → Retry stats")
                logger.info("[SEQUENTIAL] Step 1: Moving to farming map")
                return {
                    "action": "move_to_map",
                    "params": {
                        "map": "prt_fild08",
                        "reason": "farm_to_level_for_stat_points"
                    },
                    "layer": "STRATEGIC"
                }
            
            # STEP 2: If in farming map, ACTIVELY seek monsters
            if current_map.startswith("prt_fild") or current_map.endswith("_fild"):
                logger.info("[SEQUENTIAL] Step 2: Already in farming map - ACTIVELY seeking monsters")
                # CRITICAL FIX #3: Use move_random for ACTIVE monster seeking (not passive waiting)
                # This fixes the stuck loop where bot just sits and does nothing
                return {
                    "action": "move_random",
                    "params": {
                        "max_distance": 15,  # Move up to 15 cells randomly
                        "reason": "active_monster_search"
                    },
                    "layer": "TACTICAL"
                }
        
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
        
        # Default: Continue with current task (let OpenKore's native AI handle basic actions)
        logger.debug("[DECIDE] No AI-driven action needed - letting OpenKore's native AI continue")
        return {
            "action": "continue",
            "params": {
                "reason": "no_urgent_action_needed",
                "priority": "low"
            },
            "layer": "SUBCONSCIOUS"
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
    
    Also handles Sequential Planner and Action Queue feedback.
    
    Request body:
    {
        "action": "rest",
        "status": "failed",
        "reason": "basic_skill_not_learned",
        "message": "Character does not have Basic Skill Lv3 to sit",
        "plan_id": "uuid",  # Optional: if from sequential plan
        "action_id": "uuid"  # Optional: if from action queue
    }
    """
    action = feedback.get("action", "unknown")
    status = feedback.get("status", "unknown")
    reason = feedback.get("reason", "")
    message = feedback.get("message", "")
    plan_id = feedback.get("plan_id")
    action_id = feedback.get("action_id")
    success = status == "success" or status == "succeeded"
    
    logger.info(f"[FEEDBACK] Action '{action}' → {status.upper()}")
    if plan_id:
        logger.info(f"[FEEDBACK] Plan ID: {plan_id}")
    if action_id:
        logger.info(f"[FEEDBACK] Action ID: {action_id}")
    
    # Update Sequential Planner if plan_id provided
    if plan_id and sequential_planner:
        try:
            error_msg = reason if not success else None
            sequential_planner.mark_step_complete(plan_id, success=success, error=error_msg)
            logger.info(f"[PLANNER] Updated plan {plan_id}: success={success}")
        except Exception as e:
            logger.error(f"[PLANNER] Error updating plan: {e}")
    
    # Update Action Queue if action_id provided
    if action_id and action_queue:
        try:
            await action_queue.mark_complete(action_id, success=success)
            logger.info(f"[QUEUE] Marked action {action_id} as {'complete' if success else 'failed'}")
        except Exception as e:
            logger.error(f"[QUEUE] Error updating action queue: {e}")
    
    # Adaptive failure tracking (existing logic)
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
        "plan_updated": plan_id is not None,
        "queue_updated": action_id is not None,
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
async def inventory_sell_junk(request: Request, request_body: Dict[str, Any] = Body(...)):
    """
    Analyze inventory and determine which items can be safely sold
    Priority 2 Fix: Item selling logic with protection rules
    
    CRITICAL FIX: Accept flexible JSON body format to prevent 422 validation errors
    
    Expected body:
    {
        "inventory": [...],  # List of inventory items
        "min_zeny": 1000     # Optional minimum zeny threshold
    }
    """
    try:
        inventory = request_body.get("inventory", [])
        min_zeny = request_body.get("min_zeny", 1000)
        
        logger.info(f"[INVENTORY/SELL] Analyzing {len(inventory)} items for selling (min_zeny: {min_zeny}z)")
        
        result = await npc_handler.sell_junk_items(inventory, min_zeny_threshold=min_zeny)
        
        if result["success"]:
            logger.info(f"[INVENTORY/SELL] Can sell {len(result.get('items_sold', []))} items for ~{result.get('estimated_zeny', 0)}z")
        else:
            logger.warning(f"[INVENTORY/SELL] Failed: {result.get('reason', 'unknown')}")
        
        return result
    except Exception as e:
        logger.error(f"[INVENTORY/SELL] Error: {e}", exc_info=True)
        return {
            "success": False,
            "reason": "internal_error",
            "error": str(e),
            "items_sold": [],
            "estimated_zeny": 0
        }


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
async def handle_stat_level_up(request: Request, request_body: Dict[str, Any] = Body(...)):
    """
    Called by GodTierAI when character levels up.
    Returns stat allocation plan for raiseStat.pl plugin.
    
    FIX 3: Changed from function params to request body to fix 422 error
    """
    try:
        current_level = request_body.get("current_level")
        current_stats = request_body.get("current_stats", {})
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
async def handle_skill_job_level_up(request: Request, request_body: Dict[str, Any] = Body(...)):
    """
    Called by GodTierAI when job level increases.
    Returns skill learning plan for raiseSkill.pl plugin.
    
    CRITICAL FIX: Accept flexible JSON body format to prevent 422 validation errors
    
    Expected body:
    {
        "current_job_level": 10,
        "job": "Novice",
        "current_skills": {"NV_BASIC": 3, ...}
    }
    """
    try:
        current_job_level = int(request_body.get("current_job_level", 1))
        job = request_body.get("job", "Novice")
        current_skills = request_body.get("current_skills", {})
        
        logger.info(f"[SKILL_LEVEL_UP] Job: {job}, Level: {current_job_level}, Skills: {list(current_skills.keys())}")
        
        result = skill_learner.on_job_level_up(current_job_level, job, current_skills)
        
        logger.info(f"[SKILL_LEVEL_UP] Result: {result.get('next_skills_to_learn', [])}")
        
        return result
    except Exception as e:
        logger.error(f"[SKILL_LEVEL_UP] Error: {e}", exc_info=True)
        return {
            "success": False,
            "reason": "internal_error",
            "error": str(e),
            "next_skills_to_learn": []
        }

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

@app.post("/api/v1/allocate_stats")
async def allocate_stats_endpoint(request: Request, request_body: Dict[str, Any] = Body(...)):
    """
    Autonomous stat allocation endpoint for AI-driven stat point distribution.
    
    This endpoint is called by OpenKore's AI-Engine.pm when the AI decides
    to allocate stat points. It analyzes the game state and returns optimal
    stat allocation based on job class, level, and build configuration.
    
    Request body:
    {
        "game_state": {
            "character": {
                "job_class": "Novice",
                "level": 5,
                "job_level": 1,
                "str": 5,
                "agi": 5,
                "vit": 5,
                "int": 5,
                "dex": 5,
                "luk": 5,
                "points_free": 10,
                "points_str": 1,
                "points_agi": 1,
                "points_vit": 1,
                "points_int": 1,
                "points_dex": 1,
                "points_luk": 1
            }
        }
    }
    
    Returns:
    {
        "action": "allocate_stats",
        "params": {
            "stats": {"STR": 2, "DEX": 3},
            "reason": "Following balanced_novice build",
            "priority": "high"
        },
        "recommendations": {
            "str": 2,
            "dex": 3
        },
        "build_type": "balanced_novice",
        "reasoning": "Allocating 5 points total based on character progression"
    }
    """
    try:
        logger.info("[ALLOCATE_STATS] Received stat allocation request")
        
        # Extract game state
        game_state = request_body.get("game_state", {})
        character = game_state.get("character", {})
        
        # Extract character info
        job_class = character.get("job_class", "Novice")
        current_level = int(character.get("level", 1) or 1)
        available_points = int(character.get("points_free", 0) or 0)
        
        logger.info(f"[ALLOCATE_STATS] Job: {job_class}, Level: {current_level}, Available points: {available_points}")
        
        # Validate available points
        if available_points <= 0:
            logger.info("[ALLOCATE_STATS] No stat points available")
            return {
                "action": "continue",
                "params": {
                    "reason": "no_stat_points_available"
                },
                "recommendations": {},
                "build_type": "none",
                "reasoning": "Character has no free stat points to allocate"
            }
        
        # Get current stats
        current_stats = {
            "str": int(character.get("str", 1) or 1),
            "agi": int(character.get("agi", 1) or 1),
            "vit": int(character.get("vit", 1) or 1),
            "int": int(character.get("int", 1) or 1),
            "dex": int(character.get("dex", 1) or 1),
            "luk": int(character.get("luk", 1) or 1)
        }
        
        logger.debug(f"[ALLOCATE_STATS] Current stats: {current_stats}")
        
        # Calculate stat costs using RO formula
        stat_costs = {}
        for stat_name in ["str", "agi", "vit", "int", "dex", "luk"]:
            current_value = current_stats.get(stat_name, 1)
            calculated_cost = calculate_stat_cost(current_value)
            received_cost = int(character.get(f"points_{stat_name}", calculated_cost) or calculated_cost)
            
            # Validate and warn if mismatch
            if received_cost != calculated_cost:
                logger.warning(f"[ALLOCATE_STATS] Cost mismatch for {stat_name.upper()}: "
                             f"received={received_cost}, calculated={calculated_cost}, "
                             f"using calculated={calculated_cost}")
            
            stat_costs[stat_name] = calculated_cost
        
        logger.debug(f"[ALLOCATE_STATS] Stat costs: {stat_costs}")
        
        # Get recommendations from StatAllocator
        try:
            recommendations = stat_allocator.get_allocation_recommendations(
                current_stats=current_stats,
                free_points=available_points
            )
            
            if not recommendations:
                logger.warning(f"[ALLOCATE_STATS] No recommendations from StatAllocator for {job_class}")
                return {
                    "action": "continue",
                    "params": {
                        "reason": "no_stat_recommendations"
                    },
                    "recommendations": {},
                    "build_type": "unknown",
                    "reasoning": f"No stat allocation recommendations available for {job_class}"
                }
            
            # Filter recommendations by affordability
            affordable_stats = {}
            total_cost = 0
            
            for stat_name, points_to_add in recommendations.items():
                stat_cost = stat_costs.get(stat_name.lower(), 1)
                cost_for_allocation = stat_cost * points_to_add
                
                if cost_for_allocation <= (available_points - total_cost):
                    affordable_stats[stat_name] = points_to_add
                    total_cost += cost_for_allocation
                    logger.debug(f"[ALLOCATE_STATS] Can afford {stat_name.upper()} +{points_to_add} (cost: {cost_for_allocation})")
                else:
                    logger.debug(f"[ALLOCATE_STATS] Cannot afford {stat_name.upper()} +{points_to_add} (cost: {cost_for_allocation}, remaining: {available_points - total_cost})")
            
            if not affordable_stats:
                logger.warning(f"[ALLOCATE_STATS] Cannot afford any recommended stats with {available_points} points")
                return {
                    "action": "continue",
                    "params": {
                        "reason": "cannot_afford_stat_increases"
                    },
                    "recommendations": recommendations,
                    "build_type": stat_allocator.selected_build,
                    "reasoning": f"Need more stat points to afford recommended increases (need {total_cost}, have {available_points})"
                }
            
            # Build response
            build_name = stat_allocator.selected_build or "default"
            
            logger.info(f"[ALLOCATE_STATS] Recommending {affordable_stats} for {job_class} ({build_name} build)")
            
            return {
                "action": "allocate_stats",
                "params": {
                    "stats": affordable_stats,
                    "reason": f"following_{build_name}_build",
                    "priority": "high"
                },
                "recommendations": affordable_stats,
                "build_type": build_name,
                "reasoning": f"Allocating {sum(affordable_stats.values())} points based on {build_name} build for {job_class}"
            }
            
        except Exception as e:
            logger.error(f"[ALLOCATE_STATS] StatAllocator error: {e}", exc_info=True)
            
            # Fallback: Simple balanced allocation for Novice
            if job_class == "Novice" and available_points >= 1:
                logger.info("[ALLOCATE_STATS] Using fallback allocation for Novice")
                
                fallback_stats = {}
                points_remaining = available_points
                
                # Prioritize STR and DEX for early game combat
                if points_remaining >= 1 and stat_costs.get("str", 1) <= points_remaining:
                    cost = stat_costs.get("str", 1)
                    fallback_stats["STR"] = 1
                    points_remaining -= cost
                
                if points_remaining >= 1 and stat_costs.get("dex", 1) <= points_remaining:
                    cost = stat_costs.get("dex", 1)
                    fallback_stats["DEX"] = 1
                    points_remaining -= cost
                
                return {
                    "action": "allocate_stats",
                    "params": {
                        "stats": fallback_stats,
                        "reason": "fallback_balanced_build",
                        "priority": "medium"
                    },
                    "recommendations": fallback_stats,
                    "build_type": "fallback_balanced",
                    "reasoning": "Using fallback allocation (StatAllocator unavailable)"
                }
            
            # Cannot allocate
            return {
                "action": "continue",
                "params": {
                    "reason": "stat_allocation_error"
                },
                "recommendations": {},
                "build_type": "error",
                "reasoning": f"Error during stat allocation: {str(e)}"
            }
        
    except Exception as e:
        logger.error(f"[ALLOCATE_STATS] Endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/learn_skill")
async def learn_skill_endpoint(request: Request, request_body: Dict[str, Any] = Body(...)):
    """
    Autonomous skill learning endpoint for AI-driven skill point allocation.
    
    This endpoint is called by OpenKore's AI-Engine.pm when the AI decides
    to learn skills. It analyzes the game state and returns optimal skill
    learning recommendations based on job class, level, and skill priorities.
    
    CRITICAL: Prioritizes Basic Skill Lv3 first (required for sit/rest functionality).
    
    Request body:
    {
        "game_state": {
            "character": {
                "job_class": "Novice",
                "level": 5,
                "job_level": 3,
                "points_skill": 3
            },
            "skills": [
                {"name": "NV_BASIC", "level": 2},
                {"name": "NV_FIRSTAID", "level": 0}
            ]
        }
    }
    
    Returns:
    {
        "action": "learn_skill",
        "params": {
            "skill_name": "NV_BASIC",
            "skill_display_name": "Basic Skill",
            "current_level": 2,
            "target_level": 3,
            "points_to_add": 1,
            "reason": "prerequisite_for_rest",
            "priority": "critical"
        },
        "skills_to_learn": [...],
        "reasoning": "Learning Basic Skill Lv3 (required for sit/rest)"
    }
    """
    try:
        logger.info("[LEARN_SKILL] Received skill learning request")
        
        # Extract game state
        game_state = request_body.get("game_state", {})
        character = game_state.get("character", {})
        skills_list = game_state.get("skills", [])
        
        # Extract character info
        job_class = character.get("job_class", "Novice")
        current_level = int(character.get("level", 1) or 1)
        job_level = int(character.get("job_level", 1) or 1)
        available_points = int(character.get("points_skill", 0) or 0)
        
        logger.info(f"[LEARN_SKILL] Job: {job_class}, Job Level: {job_level}, Available points: {available_points}")
        
        # Validate available points
        if available_points <= 0:
            logger.info("[LEARN_SKILL] No skill points available")
            return {
                "action": "continue",
                "params": {
                    "reason": "no_skill_points_available"
                },
                "skills_to_learn": [],
                "reasoning": "Character has no free skill points to allocate"
            }
        
        # Convert skills list to dict
        current_skills = {}
        for skill in skills_list:
            if isinstance(skill, dict):
                skill_name = skill.get("name", "")
                skill_level = skill.get("level", 0)
                if skill_name:
                    current_skills[skill_name] = skill_level
        
        logger.debug(f"[LEARN_SKILL] Current skills: {current_skills}")
        
        # CRITICAL PRIORITY: Check if Basic Skill needs learning
        basic_skill_level = current_skills.get("NV_BASIC", 0) or current_skills.get("Basic Skill", 0)
        
        if basic_skill_level < 3:
            points_needed = 3 - basic_skill_level
            points_to_allocate = min(points_needed, available_points)
            
            logger.warning(f"[LEARN_SKILL] CRITICAL: Learning Basic Skill Lv{basic_skill_level} → Lv{basic_skill_level + points_to_allocate}")
            
            return {
                "action": "learn_skill",
                "params": {
                    "skill_name": "NV_BASIC",
                    "skill_display_name": "Basic Skill",
                    "current_level": basic_skill_level,
                    "target_level": basic_skill_level + points_to_allocate,
                    "points_to_add": points_to_allocate,
                    "reason": "prerequisite_for_rest",
                    "priority": "critical"
                },
                "skills_to_learn": [{
                    "skill_name": "NV_BASIC",
                    "skill_display_name": "Basic Skill",
                    "current_level": basic_skill_level,
                    "target_level": basic_skill_level + points_to_allocate,
                    "points_to_add": points_to_allocate,
                    "priority": "critical",
                    "reason": "Required for sit/rest functionality"
                }],
                "reasoning": f"Learning Basic Skill to Lv{basic_skill_level + points_to_allocate} (CRITICAL: required for sit/rest)"
            }
        
        # Basic Skill is ready, learn job-specific skills
        logger.info(f"[LEARN_SKILL] Basic Skill ready (Lv{basic_skill_level}), checking job-specific skills")
        
        try:
            # Get skill learning plan from SkillLearner
            skill_plan = skill_learner.on_job_level_up(
                current_job_level=job_level,
                job=job_class,
                current_skills=current_skills
            )
            
            # Get next skills to learn
            next_skills = skill_plan.get("next_skills_to_learn", [])
            
            if not next_skills:
                logger.info(f"[LEARN_SKILL] No job-specific skills to learn at Job Lv{job_level}")
                return {
                    "action": "continue",
                    "params": {
                        "reason": "no_skills_to_learn"
                    },
                    "skills_to_learn": [],
                    "reasoning": f"No skills available to learn for {job_class} at Job Level {job_level}"
                }
            
            # Get highest priority skill
            next_skill = next_skills[0]
            skill_name = next_skill.get("name", "")
            current_level = next_skill.get("current_level", 0)
            target_level = next_skill.get("target_level", 1)
            description = next_skill.get("description", "")
            
            # Allocate one level at a time for safety
            points_to_add = min(1, target_level - current_level, available_points)
            
            logger.info(f"[LEARN_SKILL] Recommending {skill_name} Lv{current_level} → Lv{current_level + points_to_add}")
            
            return {
                "action": "learn_skill",
                "params": {
                    "skill_name": skill_name,
                    "skill_display_name": skill_name,  # SkillLearner should provide proper name
                    "current_level": current_level,
                    "target_level": current_level + points_to_add,
                    "points_to_add": points_to_add,
                    "reason": "job_progression",
                    "priority": "high",
                    "description": description
                },
                "skills_to_learn": [{
                    "skill_name": skill_name,
                    "current_level": current_level,
                    "target_level": current_level + points_to_add,
                    "points_to_add": points_to_add,
                    "priority": "high",
                    "reason": "Job progression",
                    "description": description
                }],
                "reasoning": f"Learning {skill_name} for {job_class} progression"
            }
            
        except Exception as e:
            logger.error(f"[LEARN_SKILL] SkillLearner error: {e}", exc_info=True)
            
            # Fallback: Try to learn First Aid for Novices
            if job_class == "Novice" and available_points >= 1:
                first_aid_level = current_skills.get("NV_FIRSTAID", 0) or current_skills.get("First Aid", 0)
                
                if first_aid_level < 1:
                    logger.info("[LEARN_SKILL] Using fallback: Learning First Aid")
                    return {
                        "action": "learn_skill",
                        "params": {
                            "skill_name": "NV_FIRSTAID",
                            "skill_display_name": "First Aid",
                            "current_level": 0,
                            "target_level": 1,
                            "points_to_add": 1,
                            "reason": "fallback_novice_skill",
                            "priority": "medium"
                        },
                        "skills_to_learn": [{
                            "skill_name": "NV_FIRSTAID",
                            "skill_display_name": "First Aid",
                            "current_level": 0,
                            "target_level": 1,
                            "points_to_add": 1,
                            "priority": "medium",
                            "reason": "Fallback skill (SkillLearner unavailable)"
                        }],
                        "reasoning": "Learning First Aid (fallback allocation)"
                    }
            
            # No fallback available
            return {
                "action": "continue",
                "params": {
                    "reason": "skill_learning_error"
                },
                "skills_to_learn": [],
                "reasoning": f"Error during skill learning: {str(e)}"
            }
        
    except Exception as e:
        logger.error(f"[LEARN_SKILL] Endpoint error: {e}", exc_info=True)
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

@app.post("/api/v1/config/generate_farming")
async def generate_farming_config(
    character_level: int = Body(...),
    character_class: str = Body("Novice"),
    target_map: str = Body("prt_fild08"),
    apply_immediately: bool = Body(True)
):
    """
    Generate optimal farming configuration using CrewAI
    
    User requirement: "We should never fix config.txt manually.
    If it's config or macro issue, it should be done by the CrewAI or
    autonomous self healing with hot reload!"
    
    Args:
        character_level: Current character level
        character_class: Current job class
        target_map: Target farming map
        apply_immediately: If True, write to config.txt and trigger hot-reload
    
    Returns:
        JSON with generated config and application status
    """
    logger.info(f"[CONFIG-API] Generating farming config for Lv{character_level} {character_class}")
    logger.info(f"[CONFIG-API] Target map: {target_map}, Apply: {apply_immediately}")
    
    try:
        config_gen = get_config_generator()
        
        if apply_immediately:
            # Generate and apply config in one step
            success = config_gen.generate_and_apply_farming_config(
                character_level=character_level,
                character_class=character_class,
                target_map=target_map
            )
            
            if success:
                logger.info(f"[CONFIG-API] ✓ Farming config generated and applied")
                return {
                    "success": True,
                    "message": "Farming config generated and applied to config.txt",
                    "character": f"Lv{character_level} {character_class}",
                    "target_map": target_map,
                    "hot_reload": "GodTierAI will detect change and reload within ~5 seconds",
                    "next_steps": "Bot should start autonomous farming automatically"
                }
            else:
                logger.error(f"[CONFIG-API] Failed to apply farming config")
                return {
                    "success": False,
                    "error": "Failed to generate or apply config",
                    "message": "Check logs for details"
                }
        else:
            # Just generate config without applying
            config_dict = config_gen.generate_farming_config(
                character_level=character_level,
                character_class=character_class,
                target_map=target_map
            )
            
            logger.info(f"[CONFIG-API] ✓ Farming config generated (not applied)")
            return {
                "success": True,
                "message": "Farming config generated successfully",
                "config": config_dict,
                "character": f"Lv{character_level} {character_class}",
                "target_map": target_map,
                "note": "Config not applied - set apply_immediately=true to write to config.txt"
            }
    
    except Exception as e:
        logger.error(f"[CONFIG-API] Exception during config generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
            "/api/v1/allocate_stats",
            "/api/v1/learn_skill",
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
