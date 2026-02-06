"""
ML Model for Macro Prediction
Simplified classification model using scikit-learn
"""

import logging
import pickle
from pathlib import Path
from typing import Dict, Optional, Tuple
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class MacroPredictionModel:
    """
    Machine Learning model for predicting macro needs
    
    Uses Random Forest Classifier for fast, interpretable predictions
    Alternative to complex transformer models for initial implementation
    """
    
    MACRO_TYPE_NAMES = {
        0: 'farming',
        1: 'healing',
        2: 'resource_management',
        3: 'escape',
        4: 'skill_rotation'
    }
    
    def __init__(self, model_path: str = "models/macro_predictor.pkl"):
        """
        Initialize ML model
        
        Args:
            model_path: Path to save/load model
        """
        self.model_path = model_path
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
        # Initialize model
        self._initialize_model()
        
        # Try to load existing model
        if Path(model_path).exists():
            self.load_model(model_path)
        
        logger.info(f"MacroPredictionModel initialized (trained: {self.is_trained})")
    
    def _initialize_model(self):
        """Initialize the machine learning model"""
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1  # Use all available cores
        )
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ) -> Dict:
        """
        Train the model
        
        Args:
            X_train: Training features (N x 50)
            y_train: Training labels (N,) - macro types 0-4
            X_val: Validation features
            y_val: Validation labels
            
        Returns:
            Training metrics
        """
        logger.info(f"Training model on {len(X_train)} samples...")
        
        # Normalize features
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        # Train model
        self.model.fit(X_train_scaled, y_train)
        self.is_trained = True
        
        # Calculate training accuracy
        train_accuracy = self.model.score(X_train_scaled, y_train)
        
        metrics = {
            'train_accuracy': train_accuracy,
            'train_samples': len(X_train),
            'feature_dim': X_train.shape[1]
        }
        
        # Validation metrics if provided
        if X_val is not None and y_val is not None:
            X_val_scaled = self.scaler.transform(X_val)
            val_accuracy = self.model.score(X_val_scaled, y_val)
            metrics['val_accuracy'] = val_accuracy
            
            logger.info(
                f"Training complete: "
                f"train_acc={train_accuracy:.3f}, "
                f"val_acc={val_accuracy:.3f}"
            )
        else:
            logger.info(f"Training complete: train_acc={train_accuracy:.3f}")
        
        return metrics
    
    def predict(self, game_state_vector: np.ndarray) -> Tuple[int, float]:
        """
        Predict macro type from game state
        
        Args:
            game_state_vector: Feature vector (50 dimensions)
            
        Returns:
            Tuple of (predicted_macro_type, confidence)
        """
        if not self.is_trained:
            logger.warning("Model not trained, returning default prediction")
            return 0, 0.0  # Default to farming with 0 confidence
        
        # Ensure correct shape
        if len(game_state_vector.shape) == 1:
            game_state_vector = game_state_vector.reshape(1, -1)
        
        # Scale features
        X_scaled = self.scaler.transform(game_state_vector)
        
        # Predict
        predicted_type = self.model.predict(X_scaled)[0]
        
        # Get prediction probabilities for confidence
        probabilities = self.model.predict_proba(X_scaled)[0]
        confidence = float(probabilities[predicted_type])
        
        return int(predicted_type), confidence
    
    def predict_batch(self, game_state_vectors: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict macro types for multiple game states
        
        Args:
            game_state_vectors: Feature vectors (N x 50)
            
        Returns:
            Tuple of (predicted_types, confidences)
        """
        if not self.is_trained:
            logger.warning("Model not trained, returning default predictions")
            n = game_state_vectors.shape[0]
            return np.zeros(n, dtype=int), np.zeros(n)
        
        # Scale features
        X_scaled = self.scaler.transform(game_state_vectors)
        
        # Predict
        predicted_types = self.model.predict(X_scaled)
        probabilities = self.model.predict_proba(X_scaled)
        
        # Extract confidence for each prediction
        confidences = np.array([
            probabilities[i, predicted_types[i]]
            for i in range(len(predicted_types))
        ])
        
        return predicted_types, confidences
    
    def get_feature_importance(self) -> Dict[int, float]:
        """Get feature importance scores"""
        if not self.is_trained:
            return {}
        
        importances = self.model.feature_importances_
        return {i: float(imp) for i, imp in enumerate(importances)}
    
    def save_model(self, path: Optional[str] = None):
        """
        Save model to disk
        
        Args:
            path: Save path (uses self.model_path if None)
        """
        save_path = path or self.model_path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'is_trained': self.is_trained
        }
        
        with open(save_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Model saved to {save_path}")
    
    def load_model(self, path: Optional[str] = None):
        """
        Load model from disk
        
        Args:
            path: Load path (uses self.model_path if None)
        """
        load_path = path or self.model_path
        
        if not Path(load_path).exists():
            logger.warning(f"Model file not found: {load_path}")
            return False
        
        try:
            with open(load_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.is_trained = model_data['is_trained']
            
            logger.info(f"Model loaded from {load_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    def get_model_info(self) -> Dict:
        """Get model information"""
        return {
            'model_type': 'RandomForestClassifier',
            'is_trained': self.is_trained,
            'n_estimators': self.model.n_estimators if self.model else 0,
            'n_features': 50,
            'n_classes': 5
        }
