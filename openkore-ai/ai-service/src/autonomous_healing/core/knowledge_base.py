"""
Knowledge Base - Learning from fixes
Stores successful/failed fixes and improves over time
"""

import sqlite3
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json


class KnowledgeBase:
    """
    SQLite-based knowledge base for storing and retrieving fix patterns
    Implements incremental learning from successes and failures
    """
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Create database schema"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        
        # Fixes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fixes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_type TEXT NOT NULL,
                solution_action TEXT NOT NULL,
                context JSON,
                solution JSON,
                success BOOLEAN NOT NULL,
                confidence REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                character_level INTEGER,
                character_class TEXT,
                game_version TEXT
            )
        """)
        
        # Patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern_data JSON NOT NULL,
                frequency INTEGER DEFAULT 1,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                confidence REAL DEFAULT 0.5
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_issue_type ON fixes(issue_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_success ON fixes(success)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_type ON patterns(pattern_type)")
        
        self.conn.commit()
    
    async def record_fix(self, issue_type: str, context: Dict, solution: Dict, 
                        success: bool, confidence: float) -> int:
        """Record a fix attempt in the knowledge base"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO fixes (issue_type, solution_action, context, solution, success, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            issue_type,
            solution.get('action', 'unknown'),
            json.dumps(context),
            json.dumps(solution),
            success,
            confidence
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_similar_solutions(self, issue_type: str, limit: int = 5) -> List[Dict]:
        """Get successful solutions for similar issues"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT solution_action, confidence, success, COUNT(*) as usage_count
            FROM fixes
            WHERE issue_type = ? AND success = 1
            GROUP BY solution_action
            ORDER BY confidence DESC, usage_count DESC
            LIMIT ?
        """, (issue_type, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'action': row['solution_action'],
                'confidence': row['confidence'],
                'usage_count': row['usage_count']
            })
        
        return results
    
    def update_solution_confidence(self, issue_type: str, solution_action: str, 
                                   new_confidence: float, outcome: bool):
        """Update confidence score for a solution pattern"""
        cursor = self.conn.cursor()
        
        # Get current average confidence
        cursor.execute("""
            SELECT AVG(confidence) as avg_conf, COUNT(*) as count
            FROM fixes
            WHERE issue_type = ? AND solution_action = ?
        """, (issue_type, solution_action))
        
        row = cursor.fetchone()
        
        if row and row['count'] > 0:
            # Weighted average (favor recent results)
            weight_old = 0.7
            weight_new = 0.3
            updated_confidence = (row['avg_conf'] * weight_old + new_confidence * weight_new)
        else:
            updated_confidence = new_confidence
        
        # Store updated record
        cursor.execute("""
            INSERT INTO fixes (issue_type, solution_action, context, solution, success, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            issue_type,
            solution_action,
            json.dumps({'update': True}),
            json.dumps({'confidence_update': True}),
            outcome,
            updated_confidence
        ))
        
        self.conn.commit()
    
    def get_recurring_patterns(self, timeframe_days: int = 7) -> List[Dict]:
        """Get recurring issue patterns"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT issue_type, COUNT(*) as frequency, AVG(confidence) as avg_confidence
            FROM fixes
            WHERE datetime(timestamp) >= datetime('now', '-' || ? || ' days')
            GROUP BY issue_type
            HAVING frequency >= 3
            ORDER BY frequency DESC
        """, (timeframe_days,))
        
        patterns = []
        for row in cursor.fetchall():
            patterns.append({
                'issue_type': row['issue_type'],
                'frequency': row['frequency'],
                'avg_confidence': row['avg_confidence']
            })
        
        return patterns
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        cursor = self.conn.cursor()
        
        # Total fixes
        cursor.execute("SELECT COUNT(*) as total FROM fixes")
        total_fixes = cursor.fetchone()['total']
        
        # Success rate
        cursor.execute("SELECT AVG(CAST(success AS FLOAT)) as success_rate FROM fixes")
        success_rate = cursor.fetchone()['success_rate'] or 0.0
        
        # Most common issues
        cursor.execute("""
            SELECT issue_type, COUNT(*) as count
            FROM fixes
            GROUP BY issue_type
            ORDER BY count DESC
            LIMIT 5
        """)
        common_issues = [
            {'issue_type': row['issue_type'], 'count': row['count']}
            for row in cursor.fetchall()
        ]
        
        # Recent fixes (last 24 hours)
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM fixes
            WHERE datetime(timestamp) >= datetime('now', '-1 day')
        """)
        recent_fixes = cursor.fetchone()['count']
        
        # Average confidence
        cursor.execute("SELECT AVG(confidence) as avg_conf FROM fixes WHERE success = 1")
        avg_confidence = cursor.fetchone()['avg_conf'] or 0.0
        
        return {
            'total_fixes': total_fixes,
            'success_rate': round(success_rate * 100, 2),
            'recent_fixes_24h': recent_fixes,
            'average_confidence': round(avg_confidence, 2),
            'common_issues': common_issues
        }
    
    async def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
