"""
SQLite database schema for OpenKore AI
8 tables for persistent game state and AI data
"""

import aiosqlite
import asyncio
from pathlib import Path
from loguru import logger

# Database schema with 8 tables
SCHEMA = """
-- Table 1: Sessions (game sessions tracking)
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    character_name TEXT NOT NULL,
    start_time INTEGER NOT NULL,
    end_time INTEGER,
    server TEXT,
    total_exp_gained INTEGER DEFAULT 0,
    total_zeny_gained INTEGER DEFAULT 0,
    total_deaths INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_character ON sessions(character_name);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);

-- Table 2: Memories (episodic game events)
CREATE TABLE IF NOT EXISTS memories (
    memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    memory_type TEXT NOT NULL,  -- episodic, semantic, procedural, emotional, reflective
    content TEXT NOT NULL,
    embedding_vector TEXT,  -- JSON array of floats (synthetic embeddings)
    importance REAL DEFAULT 0.5,
    timestamp INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp);

-- Table 3: Decisions (decision history with outcomes)
CREATE TABLE IF NOT EXISTS decisions (
    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    game_state TEXT NOT NULL,  -- JSON
    tier_used TEXT NOT NULL,   -- reflex, rules, ml, llm
    action_type TEXT NOT NULL,
    action_params TEXT,        -- JSON
    reason TEXT,
    confidence REAL,
    outcome TEXT,              -- success, failure, unknown
    outcome_reward REAL,       -- reward for reinforcement learning
    timestamp INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_decisions_session ON decisions(session_id);
CREATE INDEX IF NOT EXISTS idx_decisions_tier ON decisions(tier_used);
CREATE INDEX IF NOT EXISTS idx_decisions_outcome ON decisions(outcome);

-- Table 4: Metrics (performance metrics over time)
CREATE TABLE IF NOT EXISTS metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    metric_type TEXT NOT NULL,  -- exp_rate, death_rate, zeny_rate, efficiency
    metric_value REAL NOT NULL,
    window_start INTEGER NOT NULL,
    window_end INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_metrics_session ON metrics(session_id);
CREATE INDEX IF NOT EXISTS idx_metrics_type ON metrics(metric_type);

-- Table 5: Game Lifecycle (character progression states)
CREATE TABLE IF NOT EXISTS lifecycle_states (
    state_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    character_name TEXT NOT NULL,
    level INTEGER NOT NULL,
    job_class TEXT NOT NULL,
    lifecycle_stage TEXT NOT NULL,  -- novice, first_job, second_job, rebirth, endgame
    current_goal TEXT,              -- JSON
    goal_progress REAL DEFAULT 0.0,
    timestamp INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_lifecycle_character ON lifecycle_states(character_name);
CREATE INDEX IF NOT EXISTS idx_lifecycle_stage ON lifecycle_states(lifecycle_stage);

-- Table 6: Equipment Progression (gear optimization tracking)
CREATE TABLE IF NOT EXISTS equipment_history (
    equipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    character_name TEXT NOT NULL,
    slot TEXT NOT NULL,            -- head, armor, weapon, shield, etc.
    item_name TEXT NOT NULL,
    item_id TEXT,
    equipped_at INTEGER NOT NULL,
    unequipped_at INTEGER,
    upgrade_level INTEGER DEFAULT 0,
    cost_zeny INTEGER DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_equipment_character ON equipment_history(character_name);
CREATE INDEX IF NOT EXISTS idx_equipment_slot ON equipment_history(slot);

-- Table 7: Farming Efficiency (map and monster performance)
CREATE TABLE IF NOT EXISTS farming_efficiency (
    efficiency_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    map_name TEXT NOT NULL,
    monster_name TEXT,
    time_spent INTEGER NOT NULL,  -- seconds
    exp_gained INTEGER DEFAULT 0,
    zeny_gained INTEGER DEFAULT 0,
    items_looted INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0,
    efficiency_score REAL,
    timestamp INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_farming_map ON farming_efficiency(map_name);
CREATE INDEX IF NOT EXISTS idx_farming_monster ON farming_efficiency(monster_name);
CREATE INDEX IF NOT EXISTS idx_farming_efficiency ON farming_efficiency(efficiency_score);

-- Table 8: Player Reputation (social interaction tracking)
CREATE TABLE IF NOT EXISTS player_reputation (
    reputation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_name TEXT NOT NULL,
    player_name TEXT NOT NULL,
    reputation_score INTEGER DEFAULT 0,  -- -100 to 100
    interaction_count INTEGER DEFAULT 0,
    last_interaction INTEGER NOT NULL,
    notes TEXT,  -- JSON with interaction history
    UNIQUE(character_name, player_name)
);

CREATE INDEX IF NOT EXISTS idx_reputation_character ON player_reputation(character_name);
CREATE INDEX IF NOT EXISTS idx_reputation_player ON player_reputation(player_name);
CREATE INDEX IF NOT EXISTS idx_reputation_score ON player_reputation(reputation_score);
"""

class Database:
    """SQLite database manager with async support"""
    
    def __init__(self, db_path: str = "../data/openkore-ai.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        
    async def initialize(self):
        """Initialize database with schema"""
        logger.info(f"Initializing database at {self.db_path}")
        
        self.conn = await aiosqlite.connect(str(self.db_path))
        
        # Enable WAL mode for concurrent access
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.execute("PRAGMA synchronous=NORMAL")
        
        # Execute schema
        await self.conn.executescript(SCHEMA)
        await self.conn.commit()
        
        logger.success("Database initialized successfully with 8 tables")
        
    async def close(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
            logger.info("Database connection closed")
            
    async def create_session(self, session_id: str, character_name: str, server: str = "unknown"):
        """Create new game session"""
        import time
        async with self.conn.execute(
            "INSERT INTO sessions (session_id, character_name, start_time, server, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, character_name, int(time.time()), server, int(time.time()))
        ) as cursor:
            await self.conn.commit()
            logger.info(f"Created session {session_id} for {character_name}")
            
    async def add_memory(self, session_id: str, memory_type: str, content: str, embedding: list = None, importance: float = 0.5):
        """Add memory to database"""
        import time
        import json
        
        embedding_str = json.dumps(embedding) if embedding else None
        
        async with self.conn.execute(
            "INSERT INTO memories (session_id, memory_type, content, embedding_vector, importance, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, memory_type, content, embedding_str, importance, int(time.time()))
        ) as cursor:
            await self.conn.commit()
            
    async def log_decision(self, session_id: str, game_state: dict, tier_used: str, action_type: str, 
                          action_params: dict, reason: str, confidence: float):
        """Log decision to database"""
        import time
        import json
        
        async with self.conn.execute(
            "INSERT INTO decisions (session_id, game_state, tier_used, action_type, action_params, reason, confidence, outcome, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (session_id, json.dumps(game_state), tier_used, action_type, json.dumps(action_params), reason, confidence, "unknown", int(time.time()))
        ) as cursor:
            await self.conn.commit()
            
    async def get_recent_memories(self, session_id: str, memory_type: str = None, limit: int = 10):
        """Retrieve recent memories"""
        if memory_type:
            query = "SELECT * FROM memories WHERE session_id = ? AND memory_type = ? ORDER BY timestamp DESC LIMIT ?"
            params = (session_id, memory_type, limit)
        else:
            query = "SELECT * FROM memories WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?"
            params = (session_id, limit)
            
        async with self.conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return rows

# Global database instance
db = Database()
