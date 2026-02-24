"""
Loot Decision Handler

Integrates loot prioritization system with main decision logic.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def handle_loot_decision(
    game_state: Dict[str, Any],
    loot_prioritizer,
    risk_calculator,
    tactical_retrieval,
    loot_learner
) -> Optional[Dict[str, Any]]:
    """
    Handle loot prioritization and retrieval decision.
    
    Args:
        game_state: Current game state
        loot_prioritizer: LootPrioritizer instance
        risk_calculator: RiskCalculator instance
        tactical_retrieval: TacticalLootRetrieval instance
        loot_learner: LootLearner instance
    
    Returns:
        Action dict if loot action should be taken, None otherwise
    """
    # Check if loot system is initialized
    if not all([loot_prioritizer, risk_calculator, tactical_retrieval, loot_learner]):
        return None
    
    try:
        # Get ground items from game state
        ground_items = game_state.get("ground_items", [])
        
        if not ground_items:
            return None
        
        logger.debug(f"[LOOT] Found {len(ground_items)} items on ground")
        
        # Prioritize visible loot
        prioritized_items = loot_prioritizer.prioritize_visible_loot(ground_items, game_state)
        
        if not prioritized_items:
            logger.debug("[LOOT] No valuable items found")
            return None
        
        # Get top priority item
        top_item = prioritized_items[0]
        
        # Check if item meets minimum priority threshold
        max_priority_threshold = 70  # Don't collect items with priority > 70
        if top_item.get("priority_level", 100) > max_priority_threshold:
            logger.debug(f"[LOOT] Top item priority {top_item.get('priority_level')} exceeds threshold {max_priority_threshold}")
            return None
        
        logger.info(f"[LOOT] Top priority item: {top_item.get('item_name')} (Priority: {top_item.get('priority_level')}, Value: {top_item.get('estimated_value')} zeny)")
        
        # Calculate risk for retrieving this item
        item_position = top_item.get("position", {})
        risk_level = risk_calculator.calculate_loot_risk(game_state, item_position)
        
        risk_category = risk_calculator.get_risk_category(risk_level)
        logger.info(f"[LOOT] Risk assessment: {risk_level}/100 ({risk_category})")
        
        # Check for repeated failures with current approach
        has_failures, alternative_tactic = loot_learner.detect_repeated_failures(
            item_id=top_item.get("item_id"),
            tactic=None  # Will check all tactics
        )
        
        # Get recommended tactic based on risk and history
        recommended_tactic, confidence = loot_learner.get_recommended_tactic(
            risk_level=risk_level,
            item_priority=top_item.get("priority_level", 50),
            context=game_state
        )
        
        # Override with alternative if repeated failures detected
        if has_failures and alternative_tactic:
            logger.warning(f"[LOOT] Repeated failures detected, switching to alternative tactic: {alternative_tactic}")
            recommended_tactic = alternative_tactic
        
        logger.info(f"[LOOT] Recommended tactic: {recommended_tactic} (Confidence: {confidence:.1%})")
        
        # Check if sacrifice is worth it for high-risk situations
        if risk_level > 80:
            is_sacrifice_worthy = loot_prioritizer.is_sacrifice_worthy(top_item)
            
            if not is_sacrifice_worthy:
                logger.warning(f"[LOOT] High risk ({risk_level}) but item not worth sacrifice. Skipping.")
                return None
            
            logger.warning(f"[LOOT] HIGH RISK but item worth sacrifice: {top_item.get('item_name')}")
        
        # Execute tactical retrieval
        action = tactical_retrieval.execute_tactic(
            tactic=recommended_tactic,
            target_item=top_item,
            all_items=prioritized_items,
            game_state=game_state
        )
        
        # Add metadata for tracking
        action["loot_metadata"] = {
            "item_id": top_item.get("item_id"),
            "item_name": top_item.get("item_name"),
            "priority": top_item.get("priority_level"),
            "category": top_item.get("category"),
            "risk_level": risk_level,
            "tactic": recommended_tactic,
            "confidence": confidence,
            "items_count": len(prioritized_items)
        }
        
        # Add layer info
        action["layer"] = "TACTICAL_LOOT"
        
        return action
        
    except Exception as e:
        logger.error(f"[LOOT] Error in loot decision handler: {e}", exc_info=True)
        return None


def track_loot_attempt_result(
    loot_metadata: Dict[str, Any],
    success: bool,
    died: bool,
    time_taken: float,
    loot_learner
):
    """
    Track the result of a loot attempt for learning.
    
    Args:
        loot_metadata: Metadata from loot decision
        success: Whether loot was successfully retrieved
        died: Whether character died during attempt
        time_taken: Time taken for attempt in seconds
        loot_learner: LootLearner instance
    """
    if not loot_learner or not loot_metadata:
        return
    
    try:
        item = {
            "item_id": loot_metadata.get("item_id"),
            "item_name": loot_metadata.get("item_name"),
            "priority_level": loot_metadata.get("priority"),
            "category": loot_metadata.get("category")
        }
        
        context = {
            "hp_percent": loot_metadata.get("hp_percent", 100),
            "nearby_enemies": loot_metadata.get("nearby_enemies", 0),
            "distance_to_item": loot_metadata.get("distance", 0),
            "time_taken": time_taken,
            "died": died
        }
        
        loot_learner.track_attempt(
            tactic=loot_metadata.get("tactic"),
            item=item,
            risk_level=loot_metadata.get("risk_level"),
            success=success,
            context=context
        )
        
        logger.info(f"[LOOT] Tracked attempt: {item.get('item_name')} - {'SUCCESS' if success else 'FAILED'}")
        
    except Exception as e:
        logger.error(f"[LOOT] Error tracking loot attempt: {e}", exc_info=True)
