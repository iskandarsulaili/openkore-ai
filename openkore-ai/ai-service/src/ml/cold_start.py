"""
ML Cold-Start Strategy Manager
Manages 4-phase transition from LLM to ML over 30 days
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import json

class ColdStartPhase:
    """Represents a cold-start phase"""
    PURE_LLM = 1
    SIMPLE_MODELS = 2
    HYBRID = 3
    ML_PRIMARY = 4

class ColdStartManager:
    """Manages cold-start transition from LLM to ML"""
    
    def __init__(self):
        self.start_date = None
        self.current_phase = ColdStartPhase.PURE_LLM
        self.training_samples_collected = 0
        self.model_trained = False
        self.db = None
        logger.info("Cold-Start Manager initialized")
        
    async def initialize(self, db_instance):
        """Initialize cold-start tracking"""
        self.db = db_instance
        
        # Check if we have existing cold-start state
        async with self.db.conn.execute(
            "SELECT content FROM memories WHERE memory_type = 'reflective' AND content LIKE 'Cold-start%' ORDER BY timestamp DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            
        if row:
            # Resume from saved state
            try:
                state = json.loads(row[0].split(': ', 1)[1])
                self.start_date = datetime.fromisoformat(state['start_date'])
                self.training_samples_collected = state['samples_collected']
                self.model_trained = state.get('model_trained', False)
                self._update_phase()
                logger.info(f"Resumed cold-start from saved state: Phase {self.current_phase}")
            except Exception as e:
                logger.warning(f"Failed to load cold-start state: {e}")
                self._start_fresh()
        else:
            self._start_fresh()
            
    def _start_fresh(self):
        """Start fresh cold-start process"""
        self.start_date = datetime.now()
        self.current_phase = ColdStartPhase.PURE_LLM
        self.training_samples_collected = 0
        self.model_trained = False
        logger.info(f"Starting cold-start Phase 1 (Pure LLM) on {self.start_date}")
        
    def _update_phase(self):
        """Update current phase based on elapsed time"""
        if not self.start_date:
            return
            
        days_elapsed = (datetime.now() - self.start_date).days
        
        if days_elapsed < 7:
            self.current_phase = ColdStartPhase.PURE_LLM
        elif days_elapsed < 14:
            self.current_phase = ColdStartPhase.SIMPLE_MODELS
        elif days_elapsed < 22:
            self.current_phase = ColdStartPhase.HYBRID
        else:
            self.current_phase = ColdStartPhase.ML_PRIMARY
            
        logger.debug(f"Cold-start day {days_elapsed}, Phase {self.current_phase}")
        
    async def save_state(self, session_id: str):
        """Save cold-start state to database"""
        if not self.db:
            logger.warning("Database not initialized, cannot save state")
            return
            
        state = {
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'current_phase': self.current_phase,
            'samples_collected': self.training_samples_collected,
            'model_trained': self.model_trained
        }
        
        await self.db.add_memory(
            session_id,
            'reflective',
            f'Cold-start state: {json.dumps(state)}',
            importance=0.9
        )
        logger.debug(f"Saved cold-start state for session {session_id}")
        
    def should_use_llm(self) -> bool:
        """Determine if LLM should be used based on current phase"""
        self._update_phase()
        
        if self.current_phase == ColdStartPhase.PURE_LLM:
            return True
        elif self.current_phase == ColdStartPhase.SIMPLE_MODELS:
            return self.training_samples_collected < 100  # Still collecting data
        elif self.current_phase == ColdStartPhase.HYBRID:
            return not self.model_trained  # Use LLM if model not ready
        else:  # ML_PRIMARY
            # Only use LLM for complex/novel situations
            import random
            return random.random() < 0.1  # 10% LLM consultation
            
    def should_collect_training_data(self) -> bool:
        """Should we collect this decision for training?"""
        return self.current_phase in [ColdStartPhase.PURE_LLM, ColdStartPhase.SIMPLE_MODELS]
        
    async def record_training_sample(self, session_id: str, game_state: Dict[str, Any], 
                                    action: Dict[str, Any], outcome: Optional[str] = None):
        """Record training sample for ML model"""
        if not self.should_collect_training_data():
            return
            
        if not self.db:
            logger.warning("Database not initialized, cannot record sample")
            return
            
        # Store in decisions table
        await self.db.log_decision(
            session_id,
            game_state,
            "llm_training",
            action['type'],
            action.get('parameters', {}),
            action.get('reason', ''),
            action.get('confidence', 0.5)
        )
        
        self.training_samples_collected += 1
        
        if self.training_samples_collected % 50 == 0:
            logger.info(f"Collected {self.training_samples_collected} training samples")

cold_start_manager = ColdStartManager()
