"""
Macro Prediction Engine
Real-time prediction of macro needs before conscious layer invocation
"""

import logging
import numpy as np
from typing import Dict, Optional
from pydantic import BaseModel, Field

from .model import MacroPredictionModel
from .data_collector import DataCollector

logger = logging.getLogger(__name__)


class MacroPrediction(BaseModel):
    """ML prediction result"""
    macro_type: int = Field(..., ge=0, le=4, description="Predicted macro type")
    macro_type_name: str = Field(..., description="Macro type name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence")
    pre_generated_macro: Optional[str] = Field(None, description="Pre-generated macro text")
    reasoning: str = Field(default="ML pattern recognition", description="Prediction reasoning")
    should_use: bool = Field(..., description="Whether to use this prediction")


class MacroPredictor:
    """
    Prediction engine for macro needs
    
    Predicts what macro is needed and pre-generates it
    Only used when confidence is high enough
    """
    
    MACRO_TYPE_NAMES = {
        0: 'farming',
        1: 'healing',
        2: 'resource_management',
        3: 'escape',
        4: 'skill_rotation'
    }
    
    def __init__(
        self,
        model: MacroPredictionModel,
        confidence_threshold: float = 0.7
    ):
        """
        Initialize predictor
        
        Args:
            model: Trained ML model
            confidence_threshold: Minimum confidence to use prediction
        """
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.prediction_cache = {}
        self._prediction_count = 0
        self._high_confidence_count = 0
        
        logger.info(
            f"MacroPredictor initialized "
            f"(confidence_threshold={confidence_threshold})"
        )
    
    async def predict_macro_need(self, game_state: Dict) -> Optional[MacroPrediction]:
        """
        Predict if macro is needed and what type
        
        Args:
            game_state: Complete game state dictionary
            
        Returns:
            Prediction if confidence is high enough, None otherwise
        """
        if not self.model.is_trained:
            logger.debug("Model not trained, skipping prediction")
            return None
        
        # Extract features from game state
        features = self._extract_features(game_state)
        feature_vector = np.array(features).reshape(1, -1)
        
        # Predict
        predicted_type, confidence = self.model.predict(feature_vector)
        
        self._prediction_count += 1
        
        # Check confidence threshold
        if confidence < self.confidence_threshold:
            logger.debug(
                f"Low confidence ({confidence:.2f} < {self.confidence_threshold}), "
                "deferring to conscious layer"
            )
            return None
        
        self._high_confidence_count += 1
        
        macro_type_name = self.MACRO_TYPE_NAMES.get(predicted_type, 'unknown')
        
        # Pre-generate macro using template
        pre_generated = self._generate_from_template(
            predicted_type,
            macro_type_name,
            game_state
        )
        
        prediction = MacroPrediction(
            macro_type=predicted_type,
            macro_type_name=macro_type_name,
            confidence=confidence,
            pre_generated_macro=pre_generated,
            reasoning=f"ML prediction with {confidence:.1%} confidence",
            should_use=True
        )
        
        logger.info(
            f"✓ ML prediction: {macro_type_name} "
            f"(confidence: {confidence:.2%})"
        )
        
        return prediction
    
    def _extract_features(self, game_state: Dict) -> list:
        """Extract 50-dimensional feature vector from game state"""
        # Reuse DataCollector's feature extraction
        collector = DataCollector()
        return collector._extract_features(game_state)
    
    def _generate_from_template(
        self,
        macro_type: int,
        macro_type_name: str,
        game_state: Dict
    ) -> str:
        """
        Generate macro from learned template
        
        Args:
            macro_type: Macro type (0-4)
            macro_type_name: Macro type name
            game_state: Game state
            
        Returns:
            Pre-generated macro text
        """
        char = game_state.get('character', {})
        position = game_state.get('position', {})
        nearby = game_state.get('nearby', {})
        
        # Simple template-based generation
        if macro_type == 0:  # Farming
            monsters = nearby.get('monsters', [])
            target_monster = monsters[0]['name'] if monsters else 'Monster'
            return f"""automacro ml_farm_{target_monster.lower()} {{
    exclusive 1
    monster {target_monster}
    hp > 50%
    priority 60
    timeout 5
    call ml_farm_sequence
}}

macro ml_farm_sequence {{
    log [ML-Farm] Engaging {target_monster}
    do attack "{target_monster}"
    pause 1
    do take
}}"""
        
        elif macro_type == 1:  # Healing
            hp_percent = (char.get('hp', 0) / max(char.get('max_hp', 1), 1)) * 100
            threshold = int(hp_percent + 10)  # Trigger slightly above current HP
            return f"""automacro ml_emergency_heal {{
    exclusive 1
    hp < {threshold}%
    priority 95
    timeout 2
    call ml_heal_sequence
}}

macro ml_heal_sequence {{
    log [ML-Heal] Emergency healing
    do is White Potion
    pause 0.5
    do is Orange Potion
}}"""
        
        elif macro_type == 2:  # Resource management
            weight_percent = (char.get('weight', 0) / max(char.get('max_weight', 1), 1)) * 100
            threshold = max(75, int(weight_percent - 5))
            return f"""automacro ml_weight_management {{
    exclusive 1
    weight > {threshold}%
    priority 85
    timeout 60
    call ml_weight_sequence
}}

macro ml_weight_sequence {{
    log [ML-Resource] Weight management
    do storage
    pause 2
}}"""
        
        elif macro_type == 3:  # Escape
            aggressive_count = sum(
                1 for m in nearby.get('monsters', [])
                if m.get('is_aggressive', False)
            )
            threshold = max(5, aggressive_count - 1)
            return f"""automacro ml_escape {{
    exclusive 1
    aggressives > {threshold}
    priority 90
    timeout 3
    call ml_escape_sequence
}}

macro ml_escape_sequence {{
    log [ML-Escape] Escaping from threats
    do is Fly Wing
    pause 1
}}"""
        
        else:  # Skill rotation (default fallback)
            return f"""automacro ml_skill_rotation {{
    exclusive 0
    sp > 30%
    priority 50
    timeout 5
    call ml_skill_sequence
}}

macro ml_skill_sequence {{
    log [ML-Skill] Executing skill rotation
    pause 1
}}"""
    
    def get_statistics(self) -> Dict:
        """Get predictor statistics"""
        return {
            'total_predictions': self._prediction_count,
            'high_confidence_predictions': self._high_confidence_count,
            'high_confidence_rate': (
                self._high_confidence_count / max(self._prediction_count, 1)
            ),
            'confidence_threshold': self.confidence_threshold,
            'model_trained': self.model.is_trained
        }
    
    def adjust_threshold(self, new_threshold: float):
        """Adjust confidence threshold dynamically"""
        if 0.0 <= new_threshold <= 1.0:
            old_threshold = self.confidence_threshold
            self.confidence_threshold = new_threshold
            logger.info(
                f"Confidence threshold adjusted: "
                f"{old_threshold:.2f} → {new_threshold:.2f}"
            )
        else:
            logger.warning(f"Invalid threshold: {new_threshold}")
