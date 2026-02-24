"""
Equipment Optimizer
Learns and optimizes equipment loadouts based on performance
"""

from typing import Dict, List, Any, Optional
from loguru import logger
import threading
from datetime import datetime, timedelta


class EquipmentOptimizer:
    """
    Optimizes equipment loadouts through performance analysis
    Learns which combinations work best in different scenarios
    """
    
    def __init__(self):
        """Initialize equipment optimizer"""
        self._lock = threading.RLock()
        self.loadout_performance: Dict[str, Dict] = {}
        self.optimization_history: List[Dict] = []
        
        logger.info("EquipmentOptimizer initialized")
    
    def record_performance(
        self,
        loadout: Dict[str, str],
        performance_metrics: Dict[str, float],
        context: Dict[str, Any]
    ) -> None:
        """
        Record performance of an equipment loadout
        
        Args:
            loadout: Equipment configuration
            performance_metrics: Performance metrics (damage, survival, etc.)
            context: Combat context (opponent, map, etc.)
        """
        with self._lock:
            loadout_key = self._generate_loadout_key(loadout)
            
            if loadout_key not in self.loadout_performance:
                self.loadout_performance[loadout_key] = {
                    'loadout': loadout,
                    'total_uses': 0,
                    'total_damage': 0,
                    'total_survival_time': 0,
                    'contexts': []
                }
            
            # Update performance data
            perf = self.loadout_performance[loadout_key]
            perf['total_uses'] += 1
            perf['total_damage'] += performance_metrics.get('damage', 0)
            perf['total_survival_time'] += performance_metrics.get('survival_time', 0)
            perf['contexts'].append({
                'timestamp': datetime.now(),
                'context': context,
                'metrics': performance_metrics
            })
            
            # Keep only recent contexts
            if len(perf['contexts']) > 100:
                perf['contexts'] = perf['contexts'][-100:]
    
    def _generate_loadout_key(self, loadout: Dict[str, str]) -> str:
        """Generate unique key for loadout"""
        items = sorted([f"{k}:{v}" for k, v in loadout.items()])
        return "|".join(items)
    
    def get_optimal_loadout(
        self,
        context: Dict[str, Any],
        available_equipment: List[Dict]
    ) -> Optional[Dict[str, str]]:
        """
        Get optimal loadout for given context
        
        Args:
            context: Combat context
            available_equipment: Available equipment in inventory
            
        Returns:
            Optimal loadout configuration
        """
        with self._lock:
            # Find loadouts that performed well in similar contexts
            similar_loadouts = self._find_similar_context_loadouts(context)
            
            if not similar_loadouts:
                return None
            
            # Score loadouts by performance
            scored_loadouts = [
                (loadout, self._calculate_loadout_score(loadout))
                for loadout in similar_loadouts
            ]
            
            # Return highest scoring loadout
            if scored_loadouts:
                best_loadout = max(scored_loadouts, key=lambda x: x[1])[0]
                return best_loadout
            
            return None
    
    def _find_similar_context_loadouts(self, context: Dict[str, Any]) -> List[Dict]:
        """Find loadouts used in similar contexts"""
        similar = []
        
        target_element = context.get('opponent_element')
        target_race = context.get('opponent_race')
        
        for loadout_key, perf_data in self.loadout_performance.items():
            # Check if loadout was used in similar context
            for ctx_record in perf_data['contexts']:
                ctx = ctx_record['context']
                
                if ctx.get('opponent_element') == target_element or \
                   ctx.get('opponent_race') == target_race:
                    similar.append(perf_data['loadout'])
                    break
        
        return similar
    
    def _calculate_loadout_score(self, loadout_key: str) -> float:
        """Calculate performance score for loadout"""
        perf = self.loadout_performance.get(loadout_key, {})
        
        if not perf or perf.get('total_uses', 0) == 0:
            return 0.0
        
        uses = perf['total_uses']
        avg_damage = perf['total_damage'] / uses
        avg_survival = perf['total_survival_time'] / uses
        
        # Weighted score
        score = (avg_damage * 0.6) + (avg_survival * 0.4)
        
        return score
    
    def analyze_equipment_synergies(self) -> Dict[str, List[str]]:
        """
        Analyze which equipment pieces work well together
        
        Returns:
            Dictionary of equipment synergies
        """
        with self._lock:
            synergies = {}
            
            # Analyze top performing loadouts
            top_loadouts = sorted(
                self.loadout_performance.items(),
                key=lambda x: self._calculate_loadout_score(x[0]),
                reverse=True
            )[:10]
            
            for loadout_key, perf_data in top_loadouts:
                loadout = perf_data['loadout']
                
                # Track equipment combinations
                for slot, item in loadout.items():
                    if slot not in synergies:
                        synergies[slot] = []
                    
                    if item not in synergies[slot]:
                        synergies[slot].append(item)
            
            return synergies
    
    def get_optimization_statistics(self) -> Dict:
        """Get equipment optimization statistics"""
        with self._lock:
            if not self.loadout_performance:
                return {
                    'total_loadouts': 0,
                    'total_performance_records': 0
                }
            
            total_records = sum(
                perf['total_uses']
                for perf in self.loadout_performance.values()
            )
            
            # Find best performing loadout
            best_loadout_key = max(
                self.loadout_performance.keys(),
                key=self._calculate_loadout_score
            )
            best_score = self._calculate_loadout_score(best_loadout_key)
            
            return {
                'total_loadouts': len(self.loadout_performance),
                'total_performance_records': total_records,
                'best_loadout': self.loadout_performance[best_loadout_key]['loadout'],
                'best_loadout_score': round(best_score, 2)
            }
