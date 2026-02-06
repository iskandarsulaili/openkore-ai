"""
Macro Management Coordinator
Integrates all three layers: Conscious (CrewAI), Subconscious (ML), Reflex (Rules)
"""

import logging
import asyncio
from typing import Dict, Optional
from datetime import datetime

from .conscious import MacroStrategist, MacroGenerator, MacroOptimizer, PerformanceAnalyst
from .ml import DataCollector, MacroPredictionModel, MacroPredictor, MacroModelTrainer
from .deployment_service import MacroDeploymentService, MacroDefinition

logger = logging.getLogger(__name__)


class MacroManagementCoordinator:
    """
    Central coordinator for three-layer macro management system
    
    Layer 1 (Conscious): CrewAI strategic reasoning
    Layer 2 (Subconscious): ML pattern learning
    Layer 3 (Reflex): Rule-based emergency responses (hardcoded in OpenKore)
    """
    
    def __init__(
        self,
        openkore_url: str = "http://127.0.0.1:8765",
        db_path: str = "data/openkore-ai.db"
    ):
        """
        Initialize coordinator with all layers
        
        Args:
            openkore_url: OpenKore MacroHotReload plugin URL
            db_path: Database path
        """
        logger.info("Initializing MacroManagementCoordinator...")
        
        # Layer 1: CrewAI Conscious Layer
        self.strategist = MacroStrategist()
        self.generator = MacroGenerator()
        self.optimizer = MacroOptimizer()
        self.analyst = PerformanceAnalyst()
        
        # Layer 2: ML Subconscious Layer
        self.data_collector = DataCollector(db_path)
        self.ml_model = MacroPredictionModel()
        self.predictor = MacroPredictor(self.ml_model)
        self.trainer = MacroModelTrainer(self.ml_model, self.data_collector)
        
        # Deployment service
        self.deployment = MacroDeploymentService(openkore_url)
        
        # Statistics
        self._processing_stats = {
            'total_requests': 0,
            'layer1_used': 0,  # Conscious
            'layer2_used': 0,  # Subconscious
            'layer3_used': 0,  # Reflex (passive count)
            'macros_deployed': 0,
            'deployment_failures': 0
        }
        
        logger.info("✓ MacroManagementCoordinator initialized successfully")
    
    async def process_game_state(self, game_state: Dict, session_id: str = "default") -> Dict:
        """
        Main processing loop - routes game state through layers
        
        Args:
            game_state: Current game state from OpenKore
            session_id: Session identifier
            
        Returns:
            Processing result
        """
        self._processing_stats['total_requests'] += 1
        
        logger.info("=" * 60)
        logger.info(f"Processing game state (session: {session_id})")
        logger.info("=" * 60)
        
        # Layer 3: Reflex check (emergency conditions)
        if self._is_emergency(game_state):
            logger.warning("⚡ EMERGENCY: Reflex layer active (Layer 3)")
            self._processing_stats['layer3_used'] += 1
            return {
                'layer': 3,
                'action': 'reflex',
                'reason': 'Emergency condition detected',
                'handled_by': 'hardcoded_reflex_macros'
            }
        
        # Layer 2: ML Subconscious prediction
        ml_prediction = await self.predictor.predict_macro_need(game_state)
        
        if ml_prediction and ml_prediction.confidence > 0.85:
            logger.info(
                f"🧠 SUBCONSCIOUS: ML predicted '{ml_prediction.macro_type_name}' "
                f"with {ml_prediction.confidence:.1%} confidence (Layer 2)"
            )
            self._processing_stats['layer2_used'] += 1
            
            # Deploy ML-generated macro
            result = await self._deploy_ml_macro(
                ml_prediction,
                game_state,
                session_id
            )
            
            return {
                'layer': 2,
                'action': 'ml_prediction',
                'macro_type': ml_prediction.macro_type_name,
                'confidence': ml_prediction.confidence,
                'deployment': result
            }
        
        # Layer 1: CrewAI Conscious reasoning
        logger.info("💭 CONSCIOUS: Engaging CrewAI strategic analysis (Layer 1)")
        self._processing_stats['layer1_used'] += 1
        
        result = await self._process_conscious_layer(game_state, session_id)
        
        return {
            'layer': 1,
            'action': 'conscious_reasoning',
            **result
        }
    
    async def _process_conscious_layer(
        self,
        game_state: Dict,
        session_id: str
    ) -> Dict:
        """
        Process through CrewAI conscious layer
        
        Args:
            game_state: Game state
            session_id: Session ID
            
        Returns:
            Processing result
        """
        # Step 1: Strategic analysis
        logger.info("  Step 1: MacroStrategist analyzing situation...")
        strategic_decision = await self.strategist.analyze_and_decide(game_state)
        
        if not strategic_decision.needs_macro:
            logger.info("  → No new macro needed, existing macros sufficient")
            return {
                'needs_macro': False,
                'reason': strategic_decision.reason
            }
        
        logger.info(
            f"  → Macro needed: {strategic_decision.macro_type} "
            f"(priority: {strategic_decision.priority})"
        )
        
        # Step 2: Macro generation
        logger.info("  Step 2: MacroGenerator creating macro...")
        generated_macro = await self.generator.generate_macro({
            'macro_type': strategic_decision.macro_type,
            'priority': strategic_decision.priority,
            'parameters': strategic_decision.parameters,
            'reason': strategic_decision.reason
        })
        
        if not generated_macro.validation_result['valid']:
            logger.error(f"  → Generated macro failed validation!")
            return {
                'needs_macro': True,
                'generation_failed': True,
                'errors': generated_macro.validation_result['errors']
            }
        
        logger.info(f"  → Macro '{generated_macro.macro_name}' generated successfully")
        
        # Step 3: Deploy macro
        logger.info("  Step 3: Deploying macro to OpenKore...")
        deployment_result = await self._deploy_conscious_macro(
            generated_macro,
            strategic_decision,
            game_state,
            session_id
        )
        
        # Step 4: Collect training data
        logger.info("  Step 4: Collecting training data for ML...")
        await self._collect_training_data(
            session_id,
            game_state,
            generated_macro,
            strategic_decision
        )
        
        return {
            'needs_macro': True,
            'macro_name': generated_macro.macro_name,
            'macro_type': generated_macro.macro_type,
            'deployment': deployment_result
        }
    
    async def _deploy_conscious_macro(
        self,
        generated_macro,
        strategic_decision,
        game_state: Dict,
        session_id: str
    ) -> Dict:
        """Deploy macro from conscious layer"""
        try:
            macro_def = MacroDefinition(
                name=generated_macro.macro_name,
                definition=generated_macro.macro_text,
                priority=strategic_decision.priority
            )
            
            result = await self.deployment.inject_macro(macro_def)
            
            self._processing_stats['macros_deployed'] += 1
            
            logger.info(
                f"  ✓ Macro deployed successfully "
                f"(latency: {result.get('injection_time_ms', 0)}ms)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"  ✗ Deployment failed: {e}")
            self._processing_stats['deployment_failures'] += 1
            return {'status': 'failed', 'error': str(e)}
    
    async def _deploy_ml_macro(
        self,
        prediction,
        game_state: Dict,
        session_id: str
    ) -> Dict:
        """Deploy macro from ML layer"""
        try:
            macro_name = f"ml_{prediction.macro_type_name}_{int(datetime.now().timestamp())}"
            
            macro_def = MacroDefinition(
                name=macro_name,
                definition=prediction.pre_generated_macro,
                priority=80  # ML macros get high priority
            )
            
            result = await self.deployment.inject_macro(macro_def)
            
            self._processing_stats['macros_deployed'] += 1
            
            # Collect training data
            await self._collect_training_data(
                session_id,
                game_state,
                {
                    'name': macro_name,
                    'definition': prediction.pre_generated_macro,
                    'type': prediction.macro_type_name
                },
                {'macro_type': prediction.macro_type_name}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"ML macro deployment failed: {e}")
            self._processing_stats['deployment_failures'] += 1
            return {'status': 'failed', 'error': str(e)}
    
    async def _collect_training_data(
        self,
        session_id: str,
        game_state: Dict,
        macro: Dict,
        strategic_intent: Dict
    ):
        """Collect training sample for ML"""
        try:
            sample_id = self.data_collector.collect_sample(
                session_id=session_id,
                game_state=game_state,
                macro=macro,
                strategic_intent=strategic_intent,
                outcome='pending'
            )
            
            logger.debug(f"Training sample collected: {sample_id}")
            
        except Exception as e:
            logger.error(f"Failed to collect training data: {e}")
    
    def _is_emergency(self, game_state: Dict) -> bool:
        """
        Check for emergency conditions (Layer 3 reflex)
        
        These are handled by hardcoded reflex macros in OpenKore
        """
        char = game_state.get('character', {})
        nearby = game_state.get('nearby', {})
        
        hp_percent = (char.get('hp', 0) / max(char.get('max_hp', 1), 1)) * 100
        weight_percent = (char.get('weight', 0) / max(char.get('max_weight', 1), 1)) * 100
        
        aggressive_count = sum(
            1 for m in nearby.get('monsters', [])
            if m.get('is_aggressive', False)
        )
        
        # Emergency conditions
        if hp_percent < 15:  # Critical HP
            return True
        if weight_percent > 95:  # Overweight
            return True
        if aggressive_count > 8:  # Surrounded
            return True
        
        return False
    
    async def optimize_existing_macro(
        self,
        macro_name: str,
        macro_text: str,
        performance_data: Dict
    ) -> Dict:
        """
        Optimize existing macro using MacroOptimizer
        
        Args:
            macro_name: Macro name
            macro_text: Current macro definition
            performance_data: Performance metrics
            
        Returns:
            Optimization result
        """
        logger.info(f"Optimizing macro: {macro_name}")
        
        optimization = await self.optimizer.optimize_macro(
            macro_name,
            macro_text,
            performance_data
        )
        
        if optimization.expected_improvement > 0.1:  # 10% improvement threshold
            logger.info(
                f"Deploying optimized version "
                f"(expected improvement: {optimization.expected_improvement:.1%})"
            )
            
            # Deploy optimized version
            macro_def = MacroDefinition(
                name=f"{macro_name}_optimized",
                definition=optimization.optimized_macro_text,
                priority=performance_data.get('priority', 50)
            )
            
            result = await self.deployment.inject_macro(macro_def)
            
            return {
                'status': 'optimized',
                'optimization': optimization.dict(),
                'deployment': result
            }
        else:
            logger.info("Optimization gains too small, keeping current version")
            return {
                'status': 'no_change',
                'reason': 'Insufficient improvement'
            }
    
    async def generate_performance_report(
        self,
        session_id: str,
        session_data: Dict
    ) -> Dict:
        """
        Generate performance report using PerformanceAnalyst
        
        Args:
            session_id: Session identifier
            session_data: Session metrics
            
        Returns:
            Performance report
        """
        # Get macro statistics from deployment service
        macro_stats = await self.deployment.get_statistics()
        
        # Generate report
        report = await self.analyst.analyze_performance(
            session_id,
            session_data,
            macro_stats
        )
        
        return report.dict()
    
    async def train_ml_model(self, min_samples: int = 100) -> Dict:
        """
        Train ML model from collected data
        
        Args:
            min_samples: Minimum samples required
            
        Returns:
            Training result
        """
        logger.info("Starting ML model training...")
        
        result = await self.trainer.train_from_database(min_samples=min_samples)
        
        if result['status'] == 'success':
            logger.info("✓ ML model training complete")
        else:
            logger.warning(f"Training failed: {result.get('status')}")
        
        return result
    
    def get_system_statistics(self) -> Dict:
        """Get comprehensive system statistics"""
        return {
            'processing_stats': self._processing_stats,
            'ml_stats': self.predictor.get_statistics(),
            'training_progress': self.trainer.get_training_progress(),
            'deployment_history': self.deployment.get_injection_history()
        }
    
    async def health_check(self) -> Dict:
        """Check health of all components"""
        return {
            'deployment_service': await self.deployment.health_check(),
            'ml_model_trained': self.ml_model.is_trained,
            'training_samples': self.data_collector.get_training_statistics()['total_samples'],
            'coordinator_active': True
        }
    
    async def close(self):
        """Cleanup resources"""
        await self.deployment.close()
        logger.info("MacroManagementCoordinator closed")
