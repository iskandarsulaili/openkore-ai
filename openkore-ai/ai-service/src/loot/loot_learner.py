"""
Adaptive Learning System for Loot Retrieval

Tracks success/failure rates and recommends optimal tactics based on history.
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class LootLearner:
    """
    Adaptive learning system that:
    - Tracks loot attempt outcomes
    - Calculates success rates per tactic per risk level
    - Recommends best tactics based on historical data
    - Detects repeated failures and suggests alternatives
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the loot learner.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.conn = None
        self._connect_db()
        self._initialize_tables()
        
        # Cache for success rates
        self.success_rate_cache = {}
        self.cache_timestamp = datetime.now()
        self.cache_duration = timedelta(minutes=5)
        
        logger.info("LootLearner initialized")
    
    def _connect_db(self):
        """Connect to the database."""
        try:
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"Connected to database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def _initialize_tables(self):
        """Create loot tracking table if it doesn't exist."""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS loot_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    item_id INTEGER,
                    item_name TEXT,
                    priority_level INTEGER,
                    category TEXT,
                    risk_level INTEGER,
                    tactic_used TEXT,
                    success BOOLEAN,
                    hp_percent REAL,
                    nearby_enemies INTEGER,
                    distance_to_item REAL,
                    time_taken REAL,
                    died BOOLEAN,
                    context_json TEXT
                )
            """)
            
            # Create indices for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_loot_item 
                ON loot_attempts(item_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_loot_tactic 
                ON loot_attempts(tactic_used, success)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_loot_timestamp 
                ON loot_attempts(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_loot_risk 
                ON loot_attempts(risk_level, tactic_used)
            """)
            
            self.conn.commit()
            logger.info("Loot tracking tables initialized")
        except Exception as e:
            logger.error(f"Failed to initialize tables: {e}")
            raise
    
    def track_attempt(
        self,
        tactic: str,
        item: Dict[str, Any],
        risk_level: int,
        success: bool,
        context: Dict[str, Any]
    ):
        """
        Record a loot attempt outcome.
        
        Args:
            tactic: Tactic used
            item: Item data
            risk_level: Risk level (0-100)
            success: Whether attempt succeeded
            context: Additional context (hp, enemies, etc.)
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                INSERT INTO loot_attempts (
                    item_id, item_name, priority_level, category,
                    risk_level, tactic_used, success,
                    hp_percent, nearby_enemies, distance_to_item,
                    time_taken, died, context_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.get("item_id"),
                item.get("item_name"),
                item.get("priority_level"),
                item.get("category"),
                risk_level,
                tactic,
                success,
                context.get("hp_percent"),
                context.get("nearby_enemies"),
                context.get("distance_to_item"),
                context.get("time_taken"),
                context.get("died", False),
                json.dumps(context)
            ))
            
            self.conn.commit()
            
            # Invalidate cache
            self.cache_timestamp = datetime.now() - self.cache_duration
            
            logger.info(
                f"Tracked loot attempt: {tactic} for {item.get('item_name')} - "
                f"{'SUCCESS' if success else 'FAILED'} (Risk: {risk_level})"
            )
        except Exception as e:
            logger.error(f"Failed to track loot attempt: {e}", exc_info=True)
    
    def get_recommended_tactic(
        self,
        risk_level: int,
        item_priority: int,
        context: Dict[str, Any]
    ) -> Tuple[str, float]:
        """
        Recommend best tactic based on historical success rates.
        
        Args:
            risk_level: Current risk level (0-100)
            item_priority: Item priority level
            context: Current context
        
        Returns:
            Tuple of (recommended_tactic, confidence)
        """
        # Check cache
        if datetime.now() - self.cache_timestamp < self.cache_duration:
            cached = self._get_cached_recommendation(risk_level)
            if cached:
                return cached
        
        # Calculate success rates for all tactics at this risk level
        success_rates = self._calculate_success_rates(risk_level)
        
        if not success_rates:
            # No historical data, use default recommendations
            return self._get_default_tactic(risk_level), 0.5
        
        # Find best tactic
        best_tactic = max(success_rates.items(), key=lambda x: (x[1]['success_rate'], x[1]['attempts']))
        
        tactic_name = best_tactic[0]
        success_rate = best_tactic[1]['success_rate']
        attempts = best_tactic[1]['attempts']
        
        # Confidence based on number of attempts and success rate
        confidence = min(1.0, (success_rate * 0.7) + (min(attempts, 20) / 20 * 0.3))
        
        logger.info(
            f"Recommended tactic: {tactic_name} (Success: {success_rate:.1%}, "
            f"Confidence: {confidence:.1%}, Attempts: {attempts})"
        )
        
        # Update cache
        self._update_cache(risk_level, tactic_name, confidence)
        
        return tactic_name, confidence
    
    def _calculate_success_rates(self, risk_level: int) -> Dict[str, Dict[str, Any]]:
        """
        Calculate success rates for all tactics at a given risk level.
        
        Args:
            risk_level: Risk level (0-100)
        
        Returns:
            Dict mapping tactic -> {success_rate, attempts, successes}
        """
        try:
            cursor = self.conn.cursor()
            
            # Group risk levels into buckets (0-30, 31-60, 61-100)
            risk_bucket = (risk_level // 10) * 10
            risk_min = max(0, risk_bucket - 10)
            risk_max = min(100, risk_bucket + 20)
            
            # Query recent attempts (last 7 days)
            seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
            
            cursor.execute("""
                SELECT 
                    tactic_used,
                    COUNT(*) as attempts,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes,
                    CAST(SUM(CASE WHEN success THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as success_rate
                FROM loot_attempts
                WHERE risk_level >= ? AND risk_level <= ?
                  AND timestamp > ?
                GROUP BY tactic_used
                HAVING attempts >= 3
                ORDER BY success_rate DESC
            """, (risk_min, risk_max, seven_days_ago))
            
            results = {}
            for row in cursor.fetchall():
                results[row['tactic_used']] = {
                    'attempts': row['attempts'],
                    'successes': row['successes'],
                    'success_rate': row['success_rate']
                }
            
            return results
        except Exception as e:
            logger.error(f"Failed to calculate success rates: {e}")
            return {}
    
    def detect_repeated_failures(
        self,
        item_id: Optional[int],
        tactic: str,
        lookback_hours: int = 1
    ) -> Tuple[bool, Optional[str]]:
        """
        Detect if the same tactic has failed multiple times recently.
        
        Args:
            item_id: Item ID to check
            tactic: Tactic being used
            lookback_hours: How far back to check
        
        Returns:
            Tuple of (has_repeated_failures, alternative_tactic)
        """
        try:
            cursor = self.conn.cursor()
            
            lookback_time = (datetime.now() - timedelta(hours=lookback_hours)).isoformat()
            
            # Query recent failures for this tactic
            if item_id:
                cursor.execute("""
                    SELECT success, risk_level
                    FROM loot_attempts
                    WHERE item_id = ?
                      AND tactic_used = ?
                      AND timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT 5
                """, (item_id, tactic, lookback_time))
            else:
                cursor.execute("""
                    SELECT success, risk_level
                    FROM loot_attempts
                    WHERE tactic_used = ?
                      AND timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT 5
                """, (tactic, lookback_time))
            
            results = cursor.fetchall()
            
            if len(results) < 3:
                return False, None
            
            # Check if last 3 attempts all failed
            recent_three = results[:3]
            all_failed = all(not row['success'] for row in recent_three)
            
            if all_failed:
                # Find alternative tactic
                avg_risk = sum(row['risk_level'] for row in recent_three) / 3
                success_rates = self._calculate_success_rates(int(avg_risk))
                
                # Remove the failing tactic
                success_rates.pop(tactic, None)
                
                if success_rates:
                    alternative = max(success_rates.items(), key=lambda x: x[1]['success_rate'])
                    logger.warning(
                        f"Repeated failures detected for tactic '{tactic}'. "
                        f"Suggesting alternative: {alternative[0]}"
                    )
                    return True, alternative[0]
                else:
                    return True, None
            
            return False, None
        except Exception as e:
            logger.error(f"Failed to detect repeated failures: {e}")
            return False, None
    
    def _get_default_tactic(self, risk_level: int) -> str:
        """Get default tactic based on risk level when no historical data."""
        if risk_level <= 30:
            return "systematic_collection"
        elif risk_level <= 45:
            return "kiting"
        elif risk_level <= 60:
            return "hit_and_run"
        elif risk_level <= 80:
            return "emergency_grab"
        else:
            return "sacrifice"
    
    def _get_cached_recommendation(self, risk_level: int) -> Optional[Tuple[str, float]]:
        """Get cached recommendation if available."""
        risk_bucket = (risk_level // 10) * 10
        return self.success_rate_cache.get(risk_bucket)
    
    def _update_cache(self, risk_level: int, tactic: str, confidence: float):
        """Update recommendation cache."""
        risk_bucket = (risk_level // 10) * 10
        self.success_rate_cache[risk_bucket] = (tactic, confidence)
        self.cache_timestamp = datetime.now()
    
    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get loot attempt statistics.
        
        Args:
            days: Number of days to look back
        
        Returns:
            Statistics dict
        """
        try:
            cursor = self.conn.cursor()
            lookback_time = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Overall stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as total_successes,
                    SUM(CASE WHEN died THEN 1 ELSE 0 END) as total_deaths,
                    AVG(risk_level) as avg_risk_level
                FROM loot_attempts
                WHERE timestamp > ?
            """, (lookback_time,))
            
            overall = dict(cursor.fetchone())
            
            # Per-tactic stats
            cursor.execute("""
                SELECT 
                    tactic_used,
                    COUNT(*) as attempts,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes,
                    SUM(CASE WHEN died THEN 1 ELSE 0 END) as deaths,
                    AVG(risk_level) as avg_risk
                FROM loot_attempts
                WHERE timestamp > ?
                GROUP BY tactic_used
                ORDER BY attempts DESC
            """, (lookback_time,))
            
            per_tactic = [dict(row) for row in cursor.fetchall()]
            
            # Most valuable items retrieved
            cursor.execute("""
                SELECT 
                    item_name,
                    category,
                    COUNT(*) as retrieval_count,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_retrievals
                FROM loot_attempts
                WHERE timestamp > ?
                  AND priority_level <= 20
                GROUP BY item_name, category
                ORDER BY priority_level ASC, retrieval_count DESC
                LIMIT 10
            """, (lookback_time,))
            
            valuable_items = [dict(row) for row in cursor.fetchall()]
            
            return {
                "overall": overall,
                "per_tactic": per_tactic,
                "valuable_items": valuable_items,
                "period_days": days
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def clear_old_data(self, days: int = 30):
        """
        Clear old loot attempt data.
        
        Args:
            days: Keep data newer than this many days
        """
        try:
            cursor = self.conn.cursor()
            cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute("""
                DELETE FROM loot_attempts
                WHERE timestamp < ?
            """, (cutoff_time,))
            
            deleted = cursor.rowcount
            self.conn.commit()
            
            logger.info(f"Cleared {deleted} old loot attempt records (older than {days} days)")
        except Exception as e:
            logger.error(f"Failed to clear old data: {e}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
