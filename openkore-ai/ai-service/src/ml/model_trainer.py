"""
ML Model Training and ONNX Export
Trains decision models and exports to ONNX for C++ inference
"""

from typing import Optional, Tuple, Dict, Any
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from loguru import logger
import pickle
from pathlib import Path

class ModelTrainer:
    """Trains ML models for decision making"""
    
    def __init__(self, model_dir: str = "../models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.model = None
        logger.info(f"Model Trainer initialized (model dir: {self.model_dir})")
        
    async def train_model(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Train Random Forest classifier"""
        logger.info(f"Training model with {len(X)} samples...")
        
        # Split into train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Train Random Forest
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.success(f"Model trained with accuracy: {accuracy:.3f}")
        
        # Save model
        model_path = self.model_dir / "decision_model.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(self.model, f)
            
        logger.info(f"Model saved to {model_path}")
        
        return {
            "accuracy": accuracy,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "model_path": str(model_path)
        }
        
    async def export_to_onnx(self) -> Optional[str]:
        """Export model to ONNX format for C++ inference"""
        if not self.model:
            logger.error("No model to export")
            return None
            
        try:
            from skl2onnx import convert_sklearn
            from skl2onnx.common.data_types import FloatTensorType
            
            # Define input shape (28 features)
            initial_type = [('float_input', FloatTensorType([None, 28]))]
            
            # Convert to ONNX
            onnx_model = convert_sklearn(self.model, initial_types=initial_type)
            
            # Save ONNX model
            onnx_path = self.model_dir / "decision_model.onnx"
            with open(onnx_path, "wb") as f:
                f.write(onnx_model.SerializeToString())
                
            logger.success(f"ONNX model exported to {onnx_path}")
            return str(onnx_path)
            
        except ImportError:
            logger.warning("skl2onnx not installed - skipping ONNX export")
            logger.info("Install with: pip install skl2onnx")
            return None
        except Exception as e:
            logger.error(f"ONNX export failed: {e}")
            return None
            
    async def predict(self, features: np.ndarray) -> Tuple[int, float]:
        """Make prediction using trained model"""
        if not self.model:
            return 4, 0.0  # Default to 'none' action
            
        prediction = self.model.predict([features])[0]
        probabilities = self.model.predict_proba([features])[0]
        confidence = float(probabilities[prediction])
        
        return int(prediction), confidence

model_trainer = ModelTrainer()
