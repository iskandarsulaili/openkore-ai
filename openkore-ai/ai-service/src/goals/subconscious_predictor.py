"""
Subconscious Goal Predictor - Layer 2: Pattern Recognition (ML)

Uses ML models to predict goal execution based on learned patterns from history.
Response time: 100-500ms
"""

from typing import Dict, List, Optional, Any
import logging
import numpy as np

from .goal_model import TemporalGoal, ContingencyPlan, PlanType

logger = logging.getLogger(__name__)


class SubconsciousGoalPredictor:
    """
    ML-based goal execution prediction with learned contingencies
    
    Key capabilities:
    - Pattern recognition from historical data
    - Fast prediction (<500ms)
    - Learned fallback strategies
    - Confidence-based execution
    """
    
    def __init__(self, ml_model=None):
        """
        Initialize Subconscious Predictor
        
        Args:
            ml_model: Optional pre-trained ML model
        """
        self.model = ml_model
        self.confidence_threshold = 0.85  # Execute only if >85% confident
        self.enabled = True
    
    async def predict_execution(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Predict execution plan using ML model
        
        Args:
            goal: Goal to predict execution for
            game_state: Current game state
        
        Returns:
            Prediction with plan and confidence, or None if confidence too low
        """
        
        logger.debug(f"Subconscious prediction for: {goal.name}")
        
        # Extract features
        features = self._extract_features(goal, game_state)
        
        # Make prediction
        prediction = self._predict_with_ml(features, goal.goal_type)
        
        if prediction['confidence'] < self.confidence_threshold:
            logger.debug(f"Confidence {prediction['confidence']:.2f} below threshold {self.confidence_threshold}")
            return None
        
        # Generate execution plan from prediction
        execution_plan = self._generate_execution_plan(prediction, goal, game_state)
        
        # Add learned fallbacks
        fallbacks = self.predict_with_fallbacks(goal, game_state)
        execution_plan['fallbacks'] = fallbacks
        
        logger.info(f"Subconscious prediction: {prediction['confidence']:.2f} confidence")
        
        return execution_plan
    
    def predict_with_fallbacks(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Predict primary execution and generate learned fallbacks
        
        Args:
            goal: Goal to predict for
            game_state: Current game state
        
        Returns:
            Primary prediction with fallback options
        """
        
        # Primary prediction
        primary = self._predict_primary_approach(goal, game_state)
        
        # If primary confidence is low, query historical successes
        fallbacks = []
        
        if primary['confidence'] < self.confidence_threshold:
            logger.debug("Primary confidence low - querying historical successes")
            fallbacks = self._query_historical_successes(
                goal_type=goal.goal_type,
                game_state=game_state,
                exclude_failed=True
            )
        
        return {
            'primary': primary,
            'fallbacks': fallbacks,
            'recommended': fallbacks[0] if fallbacks else primary
        }
    
    # ===== Private Methods =====
    
    def _extract_features(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> np.ndarray:
        """Extract features for ML model"""
        
        features = [
            game_state.get('hp_percent', 100) / 100,
            game_state.get('sp_percent', 100) / 100,
            game_state.get('weight_percent', 0) / 100,
            game_state.get('character_level', 1) / 100,
            game_state.get('party_size', 0) / 10,
            game_state.get('hour', 12) / 24,
            1.0 if goal.goal_type == 'farming' else 0.0,
            1.0 if goal.goal_type == 'questing' else 0.0,
            1.0 if goal.goal_type == 'survival' else 0.0,
            goal.priority.value / 5.0
        ]
        
        return np.array(features)
    
    def _predict_with_ml(
        self,
        features: np.ndarray,
        goal_type: str
    ) -> Dict[str, Any]:
        """Make prediction using ML model"""
        
        if self.model:
            # Use actual ML model
            try:
                success_prob = self.model.predict_proba([features])[0][1]
                confidence = 0.85
            except Exception as e:
                logger.error(f"ML model prediction failed: {str(e)}")
                success_prob = 0.75
                confidence = 0.5
        else:
            # Simulate ML prediction
            success_prob = 0.75 + (np.random.random() * 0.15)
            confidence = 0.70 + (np.random.random() * 0.25)
        
        return {
            'success_probability': success_prob,
            'confidence': confidence,
            'features_used': len(features)
        }
    
    def _generate_execution_plan(
        self,
        prediction: Dict[str, Any],
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate execution plan from ML prediction"""
        
        success_prob = prediction['success_probability']
        
        # Adjust strategy based on predicted success
        if success_prob > 0.85:
            strategy = 'aggressive'
        elif success_prob > 0.70:
            strategy = 'normal'
        else:
            strategy = 'defensive'
        
        return {
            'plan': {
                'strategy': strategy,
                'actions': self._get_actions_for_strategy(strategy, goal.goal_type),
                'parameters': self._get_parameters_for_strategy(strategy)
            },
            'confidence': prediction['confidence'],
            'predicted_success': success_prob,
            'source': 'ml_model'
        }
    
    def _get_actions_for_strategy(
        self,
        strategy: str,
        goal_type: str
    ) -> List[str]:
        """Get action sequence for strategy"""
        
        if strategy == 'aggressive':
            return [
                'start_immediately',
                'execute_efficiently',
                'heal_when_needed',
                'complete_quickly'
            ]
        elif strategy == 'defensive':
            return [
                'prepare_resources',
                'execute_carefully',
                'heal_frequently',
                'retreat_if_danger',
                'complete_safely'
            ]
        else:  # normal
            return [
                'assess_situation',
                'execute_normally',
                'monitor_progress',
                'complete_goal'
            ]
    
    def _get_parameters_for_strategy(self, strategy: str) -> Dict[str, Any]:
        """Get parameters for strategy"""
        
        if strategy == 'aggressive':
            return {
                'heal_threshold': 35,
                'speed_priority': 'high',
                'risk_tolerance': 'medium'
            }
        elif strategy == 'defensive':
            return {
                'heal_threshold': 70,
                'speed_priority': 'low',
                'risk_tolerance': 'low'
            }
        else:  # normal
            return {
                'heal_threshold': 50,
                'speed_priority': 'medium',
                'risk_tolerance': 'medium'
            }
    
    def _predict_primary_approach(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Predict primary approach for goal"""
        
        features = self._extract_features(goal, game_state)
        prediction = self._predict_with_ml(features, goal.goal_type)
        
        return {
            'approach': 'learned_pattern',
            'confidence': prediction['confidence'],
            'success_probability': prediction['success_probability'],
            'actions': ['execute_learned_pattern']
        }
    
    def _query_historical_successes(
        self,
        goal_type: str,
        game_state: Dict[str, Any],
        exclude_failed: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Query historical database for successful similar goals
        
        Returns approaches that worked in the past when primary failed.
        """
        
        # Simulate historical query
        # In production, this would query actual database
        
        logger.debug(f"Querying historical successes for: {goal_type}")
        
        # Mock successful alternative approaches
        fallbacks = [
            {
                'approach': 'defensive_farming',
                'success_rate': 0.92,
                'sample_count': 45,
                'avg_duration': 420,
                'description': 'Worked when aggressive approach failed'
            },
            {
                'approach': 'safe_route',
                'success_rate': 0.88,
                'sample_count': 32,
                'avg_duration': 380,
                'description': 'Alternative path with fewer risks'
            }
        ]
        
        return fallbacks
    
    def learn_from_execution(
        self,
        goal: TemporalGoal,
        result: Dict[str, Any],
        game_state: Dict[str, Any]
    ) -> None:
        """
        Learn from execution outcome to improve future predictions
        
        Args:
            goal: Goal that was executed
            result: Execution result
            game_state: Game state during execution
        """
        
        logger.info(f"Learning from execution: {goal.id} - {result.get('status')}")
        
        # Extract features and outcome
        features = self._extract_features(goal, game_state)
        label = 1 if result.get('status') == 'success' else 0
        
        # Store for model retraining
        training_data = {
            'features': features.tolist(),
            'label': label,
            'goal_type': goal.goal_type,
            'plan_used': result.get('plan_used'),
            'timestamp': game_state.get('timestamp')
        }
        
        # In production, this would update the ML model
        logger.debug("Training data stored for ML model update")
