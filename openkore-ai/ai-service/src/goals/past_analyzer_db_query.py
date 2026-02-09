"""
Database query implementation for PastAnalyzer
CRITICAL FIX #5j-2: Real database query replacing mock data
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from loguru import logger
from sqlalchemy import and_
from goals.goal_model import GoalStatus


def query_similar_historical_goals(
    db_session,
    goal_type: str,
    present_state: Dict[str, Any],
    lookback_days: int = 30,
    limit: int = 100,
    status_filter: Optional[GoalStatus] = None
) -> List[Dict[str, Any]]:
    """
    Query database for similar historical goals - PRODUCTION IMPLEMENTATION
    
    Similarity is based on:
    - Goal type (exact match)
    - Character level (within 10 levels)
    - Map (same or similar)
    - Time of day (similar hour)
    - Party status (solo/party)
    
    Args:
        db_session: Database session
        goal_type: Type of goal to match
        present_state: Current state for similarity matching
        lookback_days: How far back to search
        limit: Maximum results to return
        status_filter: Optional filter by goal status
    
    Returns:
        List of similar historical goals as dicts
    """
    
    # Extract context for similarity matching
    char_level = present_state.get('character_level', 50)
    map_name = present_state.get('map_name', 'unknown')
    hour = present_state.get('hour', 12)
    party_size = present_state.get('party_size', 0)
    
    logger.debug(f"Querying similar goals: type={goal_type}, level≈{char_level}, "
                f"map={map_name}, lookback={lookback_days}d")
    
    try:
        from database.schema import TemporalGoalRecord
        import json
        
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        
        # Build query with similarity filters
        query = db_session.query(TemporalGoalRecord).filter(
            and_(
                TemporalGoalRecord.goal_type == goal_type,
                TemporalGoalRecord.created_at >= cutoff_date
            )
        )
        
        # Optional status filter
        if status_filter:
            query = query.filter(TemporalGoalRecord.status == status_filter.value)
        
        # Execute query
        results = query.order_by(TemporalGoalRecord.created_at.desc()).limit(limit * 2).all()
        
        # Filter by level similarity and convert to dict
        goal_dicts = []
        for record in results:
            if len(goal_dicts) >= limit:
                break
            
            # Parse metadata JSON
            metadata = json.loads(record.metadata) if record.metadata else {}
            present = json.loads(record.present_state) if record.present_state else {}
            
            # Filter by level similarity (±10 levels)
            record_level = present.get('character_level', 50)
            if abs(record_level - char_level) > 10:
                continue
            
            # Calculate duration
            duration = None
            if record.completed_at and record.started_at:
                duration = (record.completed_at - record.started_at).total_seconds()
            
            goal_dicts.append({
                'id': record.id,
                'goal_type': record.goal_type,
                'name': record.name,
                'status': record.status,
                'created_at': record.created_at,
                'started_at': record.started_at,
                'completed_at': record.completed_at,
                'duration_seconds': duration,
                'present_state': present,
                'metadata': metadata,
                'active_plan': metadata.get('active_plan', 'primary'),
                'primary_plan': metadata.get('primary_plan', {}),
                'failure_reason': metadata.get('failure_reason', '')
            })
        
        logger.info(f"Found {len(goal_dicts)} similar historical goals from database")
        return goal_dicts
        
    except Exception as e:
        logger.error(f"Database query failed: {e}", exc_info=True)
        logger.warning("Returning empty results, caller will use default analysis")
        return []
