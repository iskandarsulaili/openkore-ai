"""
PDCA Check Phase: Monitor and evaluate performance metrics
"""

from typing import Dict, Any, List
from loguru import logger
import time

class PDCAChecker:
    """Monitors and evaluates performance against goals"""
    
    def __init__(self):
        self.metrics_buffer = []
        self.check_interval = 300  # Check every 5 minutes
        self.last_check_time = time.time()
        logger.info("PDCA Checker initialized")
        
    async def collect_metrics(self, session_id: str, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Collect current metrics from game state"""
        from database.schema import db
        
        metrics = {
            "timestamp": int(time.time()),
            "character_level": game_state['character'].get('level', 1),
            "hp_ratio": game_state['character'].get('hp', 0) / max(game_state['character'].get('max_hp', 1), 1),
            "sp_ratio": game_state['character'].get('sp', 0) / max(game_state['character'].get('max_sp', 1), 1),
            "weight_ratio": game_state['character'].get('weight', 0) / max(game_state['character'].get('max_weight', 1), 1),
            "zeny": game_state['character'].get('zeny', 0),
            "map": game_state['character'].get('position', {}).get('map', 'unknown'),
            "monster_count": len(game_state.get('monsters', [])),
            "aggressive_count": sum(1 for m in game_state.get('monsters', []) if m.get('is_aggressive', False))
        }
        
        self.metrics_buffer.append(metrics)
        
        # Store to database periodically
        if len(self.metrics_buffer) >= 10:
            await self._flush_metrics(session_id)
            
        return metrics
        
    async def _flush_metrics(self, session_id: str):
        """Flush buffered metrics to database"""
        from database.schema import db
        
        if not self.metrics_buffer:
            return
            
        # Calculate aggregated metrics
        window_start = self.metrics_buffer[0]['timestamp']
        window_end = self.metrics_buffer[-1]['timestamp']
        
        avg_hp_ratio = sum(m['hp_ratio'] for m in self.metrics_buffer) / len(self.metrics_buffer)
        
        async with db.conn.execute(
            "INSERT INTO metrics (session_id, metric_type, metric_value, window_start, window_end) VALUES (?, ?, ?, ?, ?)",
            (session_id, "avg_hp_ratio", avg_hp_ratio, window_start, window_end)
        ) as cursor:
            await db.conn.commit()
            
        logger.debug(f"Flushed {len(self.metrics_buffer)} metrics to database")
        self.metrics_buffer.clear()
        
    async def evaluate_performance(self, session_id: str, current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate if performance meets goals"""
        from database.schema import db
        
        # Query historical metrics for comparison
        async with db.conn.execute(
            "SELECT metric_value FROM metrics WHERE session_id = ? AND metric_type = ? ORDER BY window_end DESC LIMIT 10",
            (session_id, "avg_hp_ratio")
        ) as cursor:
            historical = await cursor.fetchall()
            
        evaluation = {
            "status": "good",
            "needs_improvement": False,
            "issues": []
        }
        
        # Check for performance issues
        if current_metrics.get('hp_ratio', 1.0) < 0.5:
            evaluation["issues"].append("HP consistently low - improve healing strategy")
            evaluation["needs_improvement"] = True
            
        if current_metrics.get('weight_ratio', 0) > 0.85:
            evaluation["issues"].append("Weight frequently high - improve inventory management")
            evaluation["needs_improvement"] = True
            
        if len(evaluation["issues"]) > 0:
            evaluation["status"] = "needs_improvement"
            
        logger.info(f"Performance evaluation: {evaluation['status']}")
        return evaluation

checker = PDCAChecker()
