"""
ML Model Trainer
Trains macro prediction model from collected data
"""

import logging
import numpy as np
from typing import Dict, Optional
from sklearn.model_selection import train_test_split

from .model import MacroPredictionModel
from .data_collector import DataCollector

logger = logging.getLogger(__name__)


class MacroModelTrainer:
    """
    Trains ML model from collected training data
    Supports both offline and online learning
    """
    
    def __init__(
        self,
        model: MacroPredictionModel,
        data_collector: DataCollector
    ):
        """
        Initialize trainer
        
        Args:
            model: ML model to train
            data_collector: Data source
        """
        self.model = model
        self.data_collector = data_collector
        self.training_history = []
        
        logger.info("MacroModelTrainer initialized")
    
    async def train_from_database(
        self,
        min_samples: int = 100,
        test_size: float = 0.2
    ) -> Dict:
        """
        Train model from database samples
        
        Args:
            min_samples: Minimum samples required
            test_size: Proportion for validation split
            
        Returns:
            Training results
        """
        logger.info("Loading training data from database...")
        
        # Get successful samples only
        samples = self.data_collector.get_recent_samples(
            limit=10000,
            outcome_filter='success'
        )
        
        if len(samples) < min_samples:
            logger.warning(
                f"Insufficient training data: {len(samples)} < {min_samples}"
            )
            return {
                'status': 'insufficient_data',
                'samples_available': len(samples),
                'samples_required': min_samples
            }
        
        # Prepare features and labels
        X = np.array([s['game_state_vector'] for s in samples])
        y = np.array([s['macro_type'] for s in samples])
        
        logger.info(f"Loaded {len(X)} samples with {X.shape[1]} features")
        
        # Train/validation split
        X_train, X_val, y_train, y_val = train_test_split(
            X, y,
            test_size=test_size,
            random_state=42,
            stratify=y  # Ensure balanced splits
        )
        
        # Train model
        metrics = self.model.train(X_train, y_train, X_val, y_val)
        
        # Save trained model
        self.model.save_model()
        
        # Record training history
        self.training_history.append({
            'timestamp': samples[0]['timestamp'],
            'train_samples': len(X_train),
            'val_samples': len(X_val),
            'train_accuracy': metrics['train_accuracy'],
            'val_accuracy': metrics.get('val_accuracy', 0)
        })
        
        logger.info(
            f"[OK] Model trained successfully: "
            f"train_acc={metrics['train_accuracy']:.3f}, "
            f"val_acc={metrics.get('val_accuracy', 0):.3f}"
        )
        
        return {
            'status': 'success',
            **metrics,
            'model_saved': True
        }
    
    async def online_update(self, recent_samples: int = 50) -> Dict:
        """
        Perform incremental model update with recent samples
        
        Args:
            recent_samples: Number of recent samples to use
            
        Returns:
            Update results
        """
        logger.info(f"Performing online update with {recent_samples} samples...")
        
        # Get recent samples
        samples = self.data_collector.get_recent_samples(
            limit=recent_samples,
            outcome_filter='success'
        )
        
        if len(samples) < 10:
            logger.warning("Too few samples for online update")
            return {'status': 'insufficient_data'}
        
        # Prepare data
        X = np.array([s['game_state_vector'] for s in samples])
        y = np.array([s['macro_type'] for s in samples])
        
        # For RandomForest, we need to retrain (not incremental)
        # In production, consider using SGDClassifier for true online learning
        metrics = self.model.train(X, y)
        
        # Save updated model
        self.model.save_model()
        
        logger.info(f"[OK] Online update complete: acc={metrics['train_accuracy']:.3f}")
        
        return {
            'status': 'success',
            **metrics
        }
    
    def get_training_progress(self) -> Dict:
        """Get training progress information"""
        stats = self.data_collector.get_training_statistics()
        
        return {
            'total_samples_collected': stats['total_samples'],
            'samples_by_type': stats['samples_by_type'],
            'model_trained': self.model.is_trained,
            'training_sessions': len(self.training_history),
            'last_training': self.training_history[-1] if self.training_history else None
        }
