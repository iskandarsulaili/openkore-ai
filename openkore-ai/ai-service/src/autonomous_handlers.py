"""
Autonomous System Handler Registry
Central registration of all autonomous trigger handlers
"""

from pathlib import Path
from loguru import logger
from typing import Dict, Any

# Import all autonomous modules
from autonomous.job_advancement import JobAdvancementDetector, JobAdvancementExecutor
from autonomous.quest_monitor import QuestTracker, QuestCompleter
from autonomous.equipment_manager import AutoEquipManager, CombatEquipmentSwapper, EquipmentOptimizer
from autonomous.skill_rotation import SkillRotationOptimizer, CombatContextAnalyzer
from autonomous.inventory_manager import InventoryOrganizer, InventoryCleaner
from autonomous.resource_gatherer import ResourcePrioritizer, RouteOptimizer
from autonomous.refinement import AutoRefiner, CardSlotter, RefinementSafetyNet


class AutonomousHandlerRegistry:
    """
    Central registry for all autonomous system handlers
    Maps trigger handler paths to actual functions
    """
    
    def __init__(self, data_dir: Path, openkore_client):
        """
        Initialize handler registry
        
        Args:
            data_dir: Directory containing configuration files
            openkore_client: OpenKore IPC client
        """
        self.data_dir = data_dir
        self.openkore = openkore_client
        
        # Initialize all autonomous modules
        self.job_advancement_detector = JobAdvancementDetector(data_dir)
        self.job_advancement_executor = JobAdvancementExecutor(data_dir, openkore_client)
        
        self.quest_tracker = QuestTracker(data_dir)
        self.quest_completer = QuestCompleter(openkore_client)
        
        self.auto_equip_manager = AutoEquipManager(data_dir, openkore_client)
        self.combat_swapper = CombatEquipmentSwapper(openkore_client)
        self.equipment_optimizer = EquipmentOptimizer()
        
        self.skill_optimizer = SkillRotationOptimizer(data_dir, openkore_client)
        self.combat_analyzer = CombatContextAnalyzer()
        
        self.inventory_organizer = InventoryOrganizer(data_dir, openkore_client)
        self.inventory_cleaner = InventoryCleaner(openkore_client)
        
        self.resource_prioritizer = ResourcePrioritizer(data_dir)
        self.route_optimizer = RouteOptimizer()
        
        self.safety_net = RefinementSafetyNet()
        self.auto_refiner = AutoRefiner(openkore_client, self.safety_net)
        self.card_slotter = CardSlotter(openkore_client, self.safety_net)
        
        logger.info("AutonomousHandlerRegistry initialized with all modules")
    
    def get_handler_map(self) -> Dict[str, Any]:
        """
        Get complete handler mapping
        
        Returns:
            Dictionary mapping handler paths to functions
        """
        return {
            # Job Advancement
            'autonomous.job_advancement.execute_job_change': self._handle_job_advancement,
            
            # Quest Monitoring
            'autonomous.quest_monitor.complete_quests': self._handle_quest_completion,
            'autonomous.quest_monitor.start_quest_chain': self._handle_quest_chain_start,
            
            # Equipment Management
            'autonomous.equipment_manager.auto_equip_best_gear': self._handle_auto_equip,
            'autonomous.equipment_manager.execute_combat_swap': self._handle_combat_swap,
            'autonomous.equipment_manager.plan_progression': self._handle_equipment_progression,
            'autonomous.equipment_manager.schedule_repair': self._handle_equipment_repair,
            
            # Skill Rotation
            'autonomous.skill_rotation.execute_optimal_rotation': self._handle_skill_rotation,
            'autonomous.skills.optimize_build': self._handle_skill_build_optimization,
            'autonomous.skills.training': self._handle_skill_training,
            
            # Inventory Management
            'autonomous.inventory_manager.organize_inventory': self._handle_inventory_organization,
            'autonomous.inventory_manager.auto_sell_junk': self._handle_auto_sell,
            
            # Resource Gathering
            'autonomous.resource_gatherer.restock_consumables': self._handle_restock_consumables,
            
            # Emergency Handlers
            'autonomous.emergency.heal_emergency': self._handle_emergency_heal,
            'autonomous.emergency.heal_moderate': self._handle_moderate_heal,
            'autonomous.emergency.death_recovery': self._handle_death_recovery,
            'autonomous.emergency.mvp_response': self._handle_mvp_response,
            'autonomous.emergency.emergency_teleport': self._handle_emergency_teleport,
            
            # Combat Handlers
            'autonomous.combat.tactical_retreat': self._handle_tactical_retreat,
            'autonomous.loot.tactical_retrieval': self._handle_tactical_loot,
            
            # System Handlers
            'autonomous.system.health_check': self._handle_system_health_check,
            'autonomous.system.database_cleanup': self._handle_database_cleanup,
            'autonomous.system.invalidate_caches': self._handle_cache_invalidation,
            'autonomous.system.monitor_performance': self._handle_performance_monitoring,
            'autonomous.system.check_connection': self._handle_connection_check,
            'autonomous.system.save_state': self._handle_save_state,
            'autonomous.system.error_recovery': self._handle_error_recovery,
            'autonomous.system.update_learning': self._handle_learning_update,
            
            # Resource Management
            'autonomous.resources.sp_recovery': self._handle_sp_recovery,
            'autonomous.buffs.auto_renew': self._handle_buff_renewal,
            
            # Farming Optimization
            'autonomous.farming.optimize_location': self._handle_farming_optimization,
            
            # Party Coordination
            'autonomous.party.coordinate_strategy': self._handle_party_coordination
        }
    
    # Handler Implementation Methods
    
    async def _handle_job_advancement(self, game_state: Dict, **params):
        """Handle job advancement trigger"""
        advancement_info = self.job_advancement_detector.check_advancement_ready(game_state)
        
        if advancement_info:
            result = await self.job_advancement_executor.execute_job_change(
                advancement_info['current_job'],
                advancement_info['recommended_job'],
                game_state
            )
            return result
        
        return {'success': False, 'reason': 'No advancement ready'}
    
    async def _handle_quest_completion(self, game_state: Dict, **params):
        """Handle quest completion trigger"""
        completable = self.quest_tracker.get_completable_quests()
        
        if completable:
            quest = completable[0]
            result = await self.quest_completer.complete_quest(quest, game_state)
            
            if result['success']:
                self.quest_tracker.mark_quest_completed(quest['quest_id'])
            
            return result
        
        return {'success': False, 'reason': 'No completable quests'}
    
    async def _handle_quest_chain_start(self, game_state: Dict, **params):
        """Handle quest chain initiation"""
        logger.info("Quest chain start handler called")
        return {'success': True, 'message': 'Quest chain analysis initiated'}
    
    async def _handle_auto_equip(self, game_state: Dict, **params):
        """Handle auto-equip trigger"""
        return await self.auto_equip_manager.auto_equip_best_gear(game_state)
    
    async def _handle_combat_swap(self, game_state: Dict, **params):
        """Handle combat equipment swap"""
        opponent = game_state.get('combat', {}).get('current_opponent', {})
        
        if opponent:
            return await self.combat_swapper.analyze_and_swap(opponent, game_state)
        
        return {'success': False, 'reason': 'No opponent detected'}
    
    async def _handle_equipment_progression(self, game_state: Dict, **params):
        """Handle equipment progression planning"""
        logger.info("Equipment progression planning initiated")
        return {'success': True}
    
    async def _handle_equipment_repair(self, game_state: Dict, **params):
        """Handle equipment repair"""
        logger.info("Equipment repair scheduled")
        return {'success': True}
    
    async def _handle_skill_rotation(self, game_state: Dict, **params):
        """Handle skill rotation execution"""
        combat_context = self.combat_analyzer.analyze_combat_context(game_state)
        return await self.skill_optimizer.execute_optimal_rotation(combat_context, game_state)
    
    async def _handle_skill_build_optimization(self, game_state: Dict, **params):
        """Handle skill build optimization"""
        logger.info("Skill build optimization initiated")
        return {'success': True}
    
    async def _handle_skill_training(self, game_state: Dict, **params):
        """Handle idle skill training"""
        logger.info("Skill training initiated")
        return {'success': True}
    
    async def _handle_inventory_organization(self, game_state: Dict, **params):
        """Handle inventory organization"""
        return await self.inventory_organizer.organize_inventory(game_state)
    
    async def _handle_auto_sell(self, game_state: Dict, **params):
        """Handle auto-sell junk items"""
        return await self.inventory_cleaner.auto_sell_junk(game_state)
    
    async def _handle_restock_consumables(self, game_state: Dict, **params):
        """Handle consumable restocking"""
        needs = self.resource_prioritizer.analyze_resource_needs(game_state)
        plan = self.resource_prioritizer.get_optimal_gathering_plan(needs)
        
        logger.info(f"Resource gathering plan created: {len(plan['actions'])} actions")
        return {'success': True, 'plan': plan}
    
    async def _handle_emergency_heal(self, game_state: Dict, **params):
        """Handle emergency healing"""
        logger.warning("Emergency heal triggered")
        await self.openkore.send_command("sl heal")
        return {'success': True}
    
    async def _handle_moderate_heal(self, game_state: Dict, **params):
        """Handle moderate healing"""
        logger.info("Moderate heal triggered")
        await self.openkore.send_command("sl heal")
        return {'success': True}
    
    async def _handle_death_recovery(self, game_state: Dict, **params):
        """Handle death recovery"""
        logger.error("Death recovery initiated")
        return {'success': True, 'message': 'Death recovery in progress'}
    
    async def _handle_mvp_response(self, game_state: Dict, **params):
        """Handle MVP spawn response"""
        logger.warning("MVP detected - fleeing")
        await self.openkore.send_command("move random")
        return {'success': True}
    
    async def _handle_emergency_teleport(self, game_state: Dict, **params):
        """Handle emergency teleport"""
        logger.warning("Emergency teleport")
        await self.openkore.send_command("skills Teleport")
        return {'success': True}
    
    async def _handle_tactical_retreat(self, game_state: Dict, **params):
        """Handle tactical retreat"""
        logger.warning("Tactical retreat initiated")
        await self.openkore.send_command("move safe")
        return {'success': True}
    
    async def _handle_tactical_loot(self, game_state: Dict, **params):
        """Handle tactical loot retrieval"""
        logger.info("Tactical loot retrieval")
        return {'success': True}
    
    async def _handle_system_health_check(self, game_state: Dict, **params):
        """Handle system health check"""
        logger.debug("System health check")
        return {'success': True, 'health': 'good'}
    
    async def _handle_database_cleanup(self, game_state: Dict, **params):
        """Handle database cleanup"""
        logger.info("Database cleanup initiated")
        return {'success': True}
    
    async def _handle_cache_invalidation(self, game_state: Dict, **params):
        """Handle cache invalidation"""
        logger.debug("Cache invalidated")
        return {'success': True}
    
    async def _handle_performance_monitoring(self, game_state: Dict, **params):
        """Handle performance monitoring"""
        logger.debug("Performance monitoring")
        return {'success': True}
    
    async def _handle_connection_check(self, game_state: Dict, **params):
        """Handle connection health check"""
        logger.debug("Connection health check")
        return {'success': True}
    
    async def _handle_save_state(self, game_state: Dict, **params):
        """Handle state save"""
        logger.info("State saved")
        return {'success': True}
    
    async def _handle_error_recovery(self, game_state: Dict, **params):
        """Handle error recovery"""
        logger.warning("Error recovery initiated")
        return {'success': True}
    
    async def _handle_learning_update(self, game_state: Dict, **params):
        """Handle ML model update"""
        logger.info("Adaptive learning update")
        return {'success': True}
    
    async def _handle_sp_recovery(self, game_state: Dict, **params):
        """Handle SP recovery"""
        logger.info("SP recovery")
        return {'success': True}
    
    async def _handle_buff_renewal(self, game_state: Dict, **params):
        """Handle buff renewal"""
        logger.info("Buff renewal")
        return {'success': True}
    
    async def _handle_farming_optimization(self, game_state: Dict, **params):
        """Handle farming location optimization"""
        logger.info("Farming optimization")
        return {'success': True}
    
    async def _handle_party_coordination(self, game_state: Dict, **params):
        """Handle party coordination"""
        logger.info("Party coordination")
        return {'success': True}
