"""
Combat Context Analyzer
Analyzes combat situation to determine optimal skill rotation type
"""

from typing import Dict, Any, List
from loguru import logger
import threading


class CombatContextAnalyzer:
    """
    Analyzes combat context to determine rotation strategy
    - Single target vs AOE
    - Boss vs regular mob
    - Enemy composition analysis
    """
    
    def __init__(self):
        """Initialize combat context analyzer"""
        self._lock = threading.RLock()
        self.context_history: List[Dict] = []
        
        logger.info("CombatContextAnalyzer initialized")
    
    def analyze_combat_context(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze current combat situation
        
        Args:
            game_state: Current game state
            
        Returns:
            Combat context dictionary
        """
        with self._lock:
            try:
                combat = game_state.get('combat', {})
                monsters = game_state.get('monsters', [])
                character = game_state.get('character', {})
                
                # Count enemies
                enemy_count = len(monsters)
                in_combat = combat.get('in_combat', False)
                
                # Detect boss
                is_boss = self._detect_boss(monsters)
                
                # Analyze enemy composition
                enemy_elements = self._analyze_enemy_elements(monsters)
                enemy_levels = self._analyze_enemy_levels(monsters, character.get('level', 1))
                
                # Determine context type
                if is_boss:
                    context_type = 'boss'
                elif enemy_count > 3:
                    context_type = 'aoe'
                elif enemy_count >= 1:
                    context_type = 'single_target'
                else:
                    context_type = 'idle'
                
                # Calculate threat level
                threat_level = self._calculate_threat_level(monsters, character)
                
                context = {
                    'type': context_type,
                    'in_combat': in_combat,
                    'enemy_count': enemy_count,
                    'is_boss': is_boss,
                    'enemy_elements': enemy_elements,
                    'threat_level': threat_level,
                    'recommended_strategy': self._recommend_strategy(
                        context_type,
                        threat_level,
                        enemy_elements
                    )
                }
                
                # Record context
                self.context_history.append({
                    'timestamp': datetime.now(),
                    'context': context
                })
                
                # Keep only recent history
                if len(self.context_history) > 100:
                    self.context_history = self.context_history[-100:]
                
                return context
                
            except Exception as e:
                logger.error(f"Context analysis error: {e}")
                return {
                    'type': 'unknown',
                    'error': str(e)
                }
    
    def _detect_boss(self, monsters: List[Dict]) -> bool:
        """
        Detect if any monster is a boss/MVP
        
        Args:
            monsters: List of monsters in vicinity
            
        Returns:
            True if boss detected
        """
        for monster in monsters:
            # Check for boss indicators
            if monster.get('is_boss', False):
                return True
            
            # High HP indicates boss
            if monster.get('hp', 0) > 100000:
                return True
            
            # MVP flag
            if 'MVP' in monster.get('name', ''):
                return True
        
        return False
    
    def _analyze_enemy_elements(self, monsters: List[Dict]) -> Dict[str, int]:
        """
        Analyze enemy elemental composition
        
        Args:
            monsters: List of monsters
            
        Returns:
            Dictionary of element counts
        """
        elements = {}
        
        for monster in monsters:
            element = monster.get('element', 'Neutral')
            elements[element] = elements.get(element, 0) + 1
        
        return elements
    
    def _analyze_enemy_levels(self, monsters: List[Dict], character_level: int) -> Dict[str, Any]:
        """
        Analyze enemy level distribution relative to character
        
        Args:
            monsters: List of monsters
            character_level: Character level
            
        Returns:
            Level analysis dictionary
        """
        if not monsters:
            return {'average': 0, 'relative_strength': 'unknown'}
        
        levels = [m.get('level', 1) for m in monsters]
        avg_level = sum(levels) / len(levels)
        
        # Determine relative strength
        level_diff = avg_level - character_level
        
        if level_diff > 10:
            strength = 'dangerous'
        elif level_diff > 5:
            strength = 'challenging'
        elif level_diff > -5:
            strength = 'appropriate'
        else:
            strength = 'easy'
        
        return {
            'average': round(avg_level, 1),
            'range': (min(levels), max(levels)),
            'relative_strength': strength
        }
    
    def _calculate_threat_level(self, monsters: List[Dict], character: Dict) -> str:
        """
        Calculate overall threat level
        
        Args:
            monsters: List of monsters
            character: Character information
            
        Returns:
            Threat level string
        """
        if not monsters:
            return 'none'
        
        character_hp_percent = character.get('hp_percent', 100)
        enemy_count = len(monsters)
        
        # Simple threat calculation
        if character_hp_percent < 30 and enemy_count > 2:
            return 'critical'
        elif character_hp_percent < 50 and enemy_count > 3:
            return 'high'
        elif enemy_count > 5:
            return 'moderate'
        else:
            return 'low'
    
    def _recommend_strategy(
        self,
        context_type: str,
        threat_level: str,
        enemy_elements: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Recommend combat strategy based on context
        
        Args:
            context_type: Type of combat (single, aoe, boss)
            threat_level: Threat level
            enemy_elements: Enemy elemental distribution
            
        Returns:
            Strategy recommendation
        """
        strategy = {
            'rotation_type': context_type,
            'priority': 'balanced'
        }
        
        # Adjust for threat
        if threat_level in ['critical', 'high']:
            strategy['priority'] = 'survival'
            strategy['notes'] = 'Focus on defensive skills and healing'
        
        # Adjust for enemy count
        if context_type == 'aoe':
            strategy['priority'] = 'aoe_damage'
            strategy['notes'] = 'Use area damage skills'
        
        # Adjust for elements
        if enemy_elements:
            dominant_element = max(enemy_elements.items(), key=lambda x: x[1])[0]
            strategy['enemy_element'] = dominant_element
            strategy['recommended_element'] = self._get_counter_element(dominant_element)
        
        return strategy
    
    def _get_counter_element(self, element: str) -> str:
        """Get counter element"""
        counters = {
            'Fire': 'Water',
            'Water': 'Wind',
            'Wind': 'Earth',
            'Earth': 'Fire',
            'Holy': 'Shadow',
            'Shadow': 'Holy',
            'Poison': 'Holy',
            'Undead': 'Holy'
        }
        
        return counters.get(element, 'Neutral')
    
    def get_context_statistics(self) -> Dict:
        """Get context analysis statistics"""
        with self._lock:
            if not self.context_history:
                return {
                    'total_analyzed': 0
                }
            
            # Count context types
            type_counts = {}
            for record in self.context_history:
                ctx_type = record['context'].get('type')
                type_counts[ctx_type] = type_counts.get(ctx_type, 0) + 1
            
            return {
                'total_analyzed': len(self.context_history),
                'context_distribution': type_counts,
                'recent_contexts': [r['context'] for r in self.context_history[-5:]]
            }
