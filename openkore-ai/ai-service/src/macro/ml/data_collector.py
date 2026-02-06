"""
Training Data Collector
Collects and stores macro generation data for ML training
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import sqlite3
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TrainingDataSample(BaseModel):
    """Single training data sample"""
    sample_id: Optional[str] = None
    session_id: str = Field(..., description="Session identifier")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # Input: Game state
    game_state_vector: List[float] = Field(..., description="50-dimensional feature vector")
    game_state_raw: Dict = Field(..., description="Raw game state for debugging")
    
    # Output: Generated macro
    macro_type: int = Field(..., ge=0, le=4, description="Macro category (0-4)")
    macro_definition: str = Field(..., description="Generated macro text")
    strategic_intent: Dict = Field(..., description="Strategic reasoning")
    
    # Outcome (for reinforcement learning)
    outcome: Optional[str] = Field(default=None, description="success|failure|pending")
    execution_time_ms: Optional[float] = None
    success_rate: Optional[float] = None
    performance_impact: Optional[float] = None
    
    # Metadata
    generated_by: str = Field(default="crewai", description="Generation source")


class DataCollector:
    """
    Collects training samples for ML model
    Stores data in SQLite database
    """
    
    # Macro type mapping
    MACRO_TYPES = {
        'farming': 0,
        'healing': 1,
        'resource_management': 2,
        'escape': 3,
        'skill_rotation': 4
    }
    
    def __init__(self, db_path: str = "data/openkore-ai.db"):
        """
        Initialize data collector
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._ensure_database()
        
        logger.info(f"DataCollector initialized with database: {db_path}")
    
    def _ensure_database(self):
        """Create database and tables if they don't exist"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create training data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ml_training_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sample_id TEXT UNIQUE,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                game_state_vector TEXT NOT NULL,
                game_state_raw TEXT NOT NULL,
                macro_type INTEGER NOT NULL,
                macro_definition TEXT NOT NULL,
                strategic_intent TEXT NOT NULL,
                outcome TEXT,
                execution_time_ms REAL,
                success_rate REAL,
                performance_impact REAL,
                generated_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_id 
            ON ml_training_data(session_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_macro_type 
            ON ml_training_data(macro_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON ml_training_data(timestamp DESC)
        """)
        
        conn.commit()
        conn.close()
        
        logger.debug("Database tables ensured")
    
    def collect_sample(
        self,
        session_id: str,
        game_state: Dict,
        macro: Dict,
        strategic_intent: Dict,
        outcome: str = "pending"
    ) -> str:
        """
        Store a training sample
        
        Args:
            session_id: Session identifier
            game_state: Complete game state
            macro: Generated macro information
            strategic_intent: Strategic reasoning
            outcome: Execution outcome
            
        Returns:
            Sample ID
        """
        # Extract features from game state
        features = self._extract_features(game_state)
        
        # Map macro type to integer
        macro_type_str = macro.get('type', 'farming')
        macro_type = self.MACRO_TYPES.get(macro_type_str, 0)
        
        sample = TrainingDataSample(
            sample_id=f"sample_{datetime.now().timestamp()}",
            session_id=session_id,
            game_state_vector=features,
            game_state_raw=game_state,
            macro_type=macro_type,
            macro_definition=macro.get('definition', ''),
            strategic_intent=strategic_intent,
            outcome=outcome,
            generated_by=macro.get('source', 'crewai')
        )
        
        # Insert into database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO ml_training_data (
                    sample_id, session_id, timestamp,
                    game_state_vector, game_state_raw,
                    macro_type, macro_definition, strategic_intent,
                    outcome, generated_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sample.sample_id,
                sample.session_id,
                sample.timestamp,
                json.dumps(sample.game_state_vector),
                json.dumps(sample.game_state_raw),
                sample.macro_type,
                sample.macro_definition,
                json.dumps(sample.strategic_intent),
                sample.outcome,
                sample.generated_by
            ))
            
            conn.commit()
            
            logger.debug(f"Collected training sample: {sample.sample_id}")
            
            return sample.sample_id
            
        except Exception as e:
            logger.error(f"Failed to collect sample: {e}")
            raise
        finally:
            conn.close()
    
    def update_outcome(
        self,
        sample_id: str,
        outcome: str,
        execution_time_ms: float = None,
        success_rate: float = None,
        performance_impact: float = None
    ):
        """
        Update sample with execution outcome
        
        Args:
            sample_id: Sample identifier
            outcome: Execution outcome
            execution_time_ms: Execution time
            success_rate: Success rate
            performance_impact: Performance impact score
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE ml_training_data
                SET outcome = ?,
                    execution_time_ms = ?,
                    success_rate = ?,
                    performance_impact = ?
                WHERE sample_id = ?
            """, (outcome, execution_time_ms, success_rate, performance_impact, sample_id))
            
            conn.commit()
            
            logger.debug(f"Updated outcome for sample: {sample_id}")
            
        finally:
            conn.close()
    
    def get_recent_samples(
        self,
        limit: int = 1000,
        macro_type: Optional[int] = None,
        outcome_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Retrieve recent training samples
        
        Args:
            limit: Maximum number of samples
            macro_type: Filter by macro type (0-4)
            outcome_filter: Filter by outcome
            
        Returns:
            List of training samples
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT 
                sample_id, session_id, timestamp,
                game_state_vector, macro_type, macro_definition,
                outcome, execution_time_ms, success_rate, performance_impact
            FROM ml_training_data
            WHERE 1=1
        """
        
        params = []
        
        if macro_type is not None:
            query += " AND macro_type = ?"
            params.append(macro_type)
        
        if outcome_filter:
            query += " AND outcome = ?"
            params.append(outcome_filter)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        samples = []
        for row in rows:
            samples.append({
                'sample_id': row[0],
                'session_id': row[1],
                'timestamp': row[2],
                'game_state_vector': json.loads(row[3]),
                'macro_type': row[4],
                'macro_definition': row[5],
                'outcome': row[6],
                'execution_time_ms': row[7],
                'success_rate': row[8],
                'performance_impact': row[9]
            })
        
        logger.debug(f"Retrieved {len(samples)} training samples")
        
        return samples
    
    def get_training_statistics(self) -> Dict:
        """Get statistics about collected training data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total samples
        cursor.execute("SELECT COUNT(*) FROM ml_training_data")
        total_samples = cursor.fetchone()[0]
        
        # Samples by type
        cursor.execute("""
            SELECT macro_type, COUNT(*) 
            FROM ml_training_data 
            GROUP BY macro_type
        """)
        samples_by_type = dict(cursor.fetchall())
        
        # Samples by outcome
        cursor.execute("""
            SELECT outcome, COUNT(*) 
            FROM ml_training_data 
            GROUP BY outcome
        """)
        samples_by_outcome = dict(cursor.fetchall())
        
        # Average success rate
        cursor.execute("""
            SELECT AVG(success_rate) 
            FROM ml_training_data 
            WHERE success_rate IS NOT NULL
        """)
        avg_success_rate = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_samples': total_samples,
            'samples_by_type': samples_by_type,
            'samples_by_outcome': samples_by_outcome,
            'average_success_rate': avg_success_rate
        }
    
    def _extract_features(self, game_state: Dict) -> List[float]:
        """
        Extract 50-dimensional feature vector from game state
        
        Args:
            game_state: Complete game state
            
        Returns:
            Feature vector (50 dimensions)
        """
        char = game_state.get('character', {})
        position = game_state.get('position', {})
        nearby = game_state.get('nearby', {})
        inventory = game_state.get('inventory', {})
        
        features = []
        
        # Character features (10 dimensions)
        features.append(char.get('level', 0) / 99.0)  # Normalized level
        features.append(char.get('hp', 0) / max(char.get('max_hp', 1), 1))
        features.append(char.get('sp', 0) / max(char.get('max_sp', 1), 1))
        features.append(char.get('weight', 0) / max(char.get('max_weight', 1), 1))
        features.append(char.get('zeny', 0) / 1000000.0)  # Normalized zeny
        
        # Job class one-hot encoding (5 dimensions)
        job_classes = ['Novice', 'Swordsman', 'Mage', 'Archer', 'Thief', 'Other']
        job = char.get('job_class', 'Other')
        for jc in job_classes[:5]:
            features.append(1.0 if job == jc else 0.0)
        
        # Environment features (15 dimensions)
        features.append(len(nearby.get('monsters', [])) / 10.0)  # Monster count
        features.append(
            sum(1 for m in nearby.get('monsters', []) if m.get('is_aggressive', False)) / 10.0
        )
        features.append(position.get('x', 0) / 400.0)  # Normalized coordinates
        features.append(position.get('y', 0) / 400.0)
        
        # Map one-hot encoding (10 dimensions) - simplified
        maps = ['prontera', 'prt_fild08', 'prt_fild01', 'prt_fild02', 'other']
        current_map = position.get('map', 'other')
        for map_name in maps[:10]:
            features.append(1.0 if current_map == map_name else 0.0)
        
        # Inventory features (10 dimensions)
        item_count = len(inventory.get('items', []))
        features.append(item_count / 100.0)
        
        # Pad remaining dimensions
        while len(features) < 50:
            features.append(0.0)
        
        # Ensure exactly 50 dimensions
        return features[:50]
