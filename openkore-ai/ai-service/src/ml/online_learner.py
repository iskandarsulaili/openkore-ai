"""
Online Learning System
Continuously updates ML model with new data
"""

from typing import Dict, Any
import numpy as np
from loguru import logger
from utils.console_logger import console_logger, LayerType

class OnlineLearner:
    """Implements online learning for continuous model improvement"""
    
    def __init__(self, model_trainer_instance, data_collector_instance):
        self.trainer = model_trainer_instance
        self.collector = data_collector_instance
        self.update_threshold = 50  # Retrain after 50 new samples
        self.samples_since_update = 0
        logger.info("Online Learner initialized")
        
    async def add_experience(self, session_id: str, game_state: Dict[str, Any], 
                            action: Dict[str, Any], reward: float):
        """Add experience sample for online learning"""
        self.samples_since_update += 1
        
        # Log decision with reward for reinforcement learning
        from database import db
        
        try:
            async with db.conn.execute(
                "UPDATE decisions SET outcome = ?, outcome_reward = ? WHERE session_id = ? AND timestamp = (SELECT MAX(timestamp) FROM decisions WHERE session_id = ?)",
                ('success' if reward > 0 else 'failure', reward, session_id, session_id)
            ) as cursor:
                await db.conn.commit()
        except Exception as e:
            logger.error(f"Failed to update decision outcome: {e}")
            
        # Trigger retraining if threshold reached
        if self.samples_since_update >= self.update_threshold:
            await self.retrain_model(session_id)
            
    async def retrain_model(self, session_id: str):
        """Retrain model with accumulated data"""
        logger.info("Retraining model with new data...")
        
        print(f"\n🔮 [SUBCONSCIOUS] Model Retraining Started")
        print(f"   └─ Accumulated Samples: {self.samples_since_update}")
        print(f"   └─ Session: {session_id}")
        print(f"   └─ Status: Collecting training dataset...")
        
        # Collect updated dataset
        X, y = await self.collector.collect_training_dataset(session_id, min_samples=100)
        
        if X is None:
            logger.warning("Insufficient data for retraining")
            return
            
        # Retrain
        results = await self.trainer.train_model(X, y)
        
        # Export to ONNX
        await self.trainer.export_to_onnx()
        
        self.samples_since_update = 0
        logger.success(f"Model retrained with accuracy: {results['accuracy']:.3f}")
        
        # Log learning progress to console
        console_logger.log_learning_progress(
            samples_collected=len(X) if X is not None else 0,
            learning_rate=0.001,  # Adjust based on your actual learning rate
            patterns_learned=self.samples_since_update
        )
        
        print(f"   └─ ✓ Retraining Complete!")
        print(f"   └─ Accuracy: {results['accuracy']:.3f}")
        print(f"   └─ Model exported to ONNX")

online_learner = None  # Initialized in main.py
