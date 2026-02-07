"""
Status Effect Handler for OpenKore AI intelligent decision-making.

This module uses the status effect database to make smart decisions about
character actions based on current status effects.
"""

from typing import Dict, List, Set, Optional
from .status_effects import StatusEffectDatabase, StatusChange, StatusEffectInfo


class StatusEffectHandler:
    """
    Handles character status effects and provides intelligent decision-making.
    
    This is purely client-side logic for the OpenKore bot to understand
    what it can and cannot do based on observed status effects.
    """
    
    def __init__(self):
        self.db = StatusEffectDatabase()
        # Track active status effects per character
        # Key: char_id (int), Value: Set of active StatusChange
        self.active_effects: Dict[int, Set[StatusChange]] = {}
        
    def update_status(self, char_id: int, status_list: List[int]):
        """
        Update character's active status effects.
        
        Args:
            char_id: Character ID
            status_list: List of status change IDs currently active
        """
        try:
            self.active_effects[char_id] = set(
                StatusChange(sc) for sc in status_list 
                if sc >= StatusChange.SC_NONE.value
            )
        except ValueError as e:
            # Unknown status effect - log but don't crash
            print(f"Warning: Unknown status effect in list: {e}")
            self.active_effects[char_id] = set(
                StatusChange(sc) for sc in status_list 
                if sc >= StatusChange.SC_NONE.value and sc <= StatusChange.SC_MAX.value
            )
    
    def clear_status(self, char_id: int):
        """Clear all status effects for a character."""
        self.active_effects[char_id] = set()
    
    def add_status(self, char_id: int, sc_type: StatusChange):
        """Add a single status effect."""
        if char_id not in self.active_effects:
            self.active_effects[char_id] = set()
        self.active_effects[char_id].add(sc_type)
    
    def remove_status(self, char_id: int, sc_type: StatusChange):
        """Remove a single status effect."""
        if char_id in self.active_effects:
            self.active_effects[char_id].discard(sc_type)
    
    def has_status(self, char_id: int, sc_type: StatusChange) -> bool:
        """Check if character has specific status effect."""
        return sc_type in self.active_effects.get(char_id, set())
    
    def get_active_statuses(self, char_id: int) -> Set[StatusChange]:
        """Get all active status effects for character."""
        return self.active_effects.get(char_id, set()).copy()
    
    # ================================================================
    # ACTION CAPABILITY CHECKS
    # ================================================================
    
    def can_act(self, char_id: int, action: str) -> bool:
        """
        Check if character can perform a specific action.
        
        Args:
            char_id: Character ID
            action: Action type ("move", "attack", "cast", "item", "sit")
        
        Returns:
            True if action is possible, False if prevented by status
        """
        active = self.active_effects.get(char_id, set())
        
        for sc in active:
            if self.db.prevents_action(sc, action):
                return False
        
        return True
    
    def can_move(self, char_id: int) -> bool:
        """Check if character can move."""
        return self.can_act(char_id, "move")
    
    def can_attack(self, char_id: int) -> bool:
        """Check if character can attack."""
        return self.can_act(char_id, "attack")
    
    def can_cast(self, char_id: int) -> bool:
        """Check if character can cast skills."""
        return self.can_act(char_id, "cast")
    
    def can_use_item(self, char_id: int) -> bool:
        """Check if character can use items."""
        return self.can_act(char_id, "item")
    
    # ================================================================
    # STATUS CATEGORIZATION
    # ================================================================
    
    def get_active_buffs(self, char_id: int) -> List[StatusChange]:
        """Get list of active beneficial buffs."""
        active = self.active_effects.get(char_id, set())
        return [sc for sc in active if self.db.is_buff(sc)]
    
    def get_active_debuffs(self, char_id: int) -> List[StatusChange]:
        """Get list of active harmful debuffs."""
        active = self.active_effects.get(char_id, set())
        return [sc for sc in active if self.db.is_debuff(sc)]
    
    def get_active_ailments(self, char_id: int) -> List[StatusChange]:
        """Get list of active common ailments."""
        active = self.active_effects.get(char_id, set())
        return [sc for sc in active if self.db.is_ailment(sc)]
    
    # ================================================================
    # INTELLIGENT DECISION MAKING
    # ================================================================
    
    def should_cure(self, char_id: int) -> bool:
        """
        Determine if character urgently needs status cure.
        
        Returns True if character has high-priority negative effects
        that should be removed immediately.
        """
        active = self.active_effects.get(char_id, set())
        
        # Priority ailments that prevent action
        critical_ailments = [
            StatusChange.SC_STONE,
            StatusChange.SC_FREEZE,
            StatusChange.SC_STUN,
            StatusChange.SC_SLEEP,
        ]
        
        # Check for critical ailments
        if any(sc in active for sc in critical_ailments):
            return True
        
        # Check for important debuffs
        important_debuffs = [
            StatusChange.SC_SILENCE,  # Can't cast
            StatusChange.SC_CURSE,
            StatusChange.SC_BLIND,
            StatusChange.SC_DPOISON,  # Deadly poison
        ]
        
        if any(sc in active for sc in important_debuffs):
            return True
        
        return False
    
    def get_cure_priority(self, char_id: int) -> int:
        """
        Get urgency level for curing status effects.
        
        Returns:
            0: No cure needed
            1-100: Priority level (higher = more urgent)
        """
        active = self.active_effects.get(char_id, set())
        
        if not active:
            return 0
        
        max_priority = 0
        for sc in active:
            effect = self.db.get_effect(sc)
            if effect and effect.priority < 0:  # Negative = bad status
                # Convert negative priority to positive cure priority
                cure_priority = abs(effect.priority)
                max_priority = max(max_priority, cure_priority)
        
        return max_priority
    
    def should_buff(self, char_id: int, job: str) -> bool:
        """
        Check if character needs buffing.
        
        Args:
            char_id: Character ID
            job: Job class name
        
        Returns:
            True if important buffs are missing
        """
        missing = self.get_missing_buffs(char_id, job)
        return len(missing) > 0
    
    def get_missing_buffs(self, char_id: int, job: str) -> List[StatusChange]:
        """
        Get list of important buffs that are missing for this job.
        
        Args:
            char_id: Character ID
            job: Job class name (e.g., "swordsman", "knight", "mage")
        
        Returns:
            List of StatusChange that should be applied
        """
        active_buffs = set(self.get_active_buffs(char_id))
        
        # Essential buffs per job type
        essential_buffs = {
            "novice": [
                StatusChange.SC_BLESSING,
                StatusChange.SC_INCREASEAGI,
            ],
            "swordsman": [
                StatusChange.SC_BLESSING,
                StatusChange.SC_INCREASEAGI,
                StatusChange.SC_ANGELUS,
            ],
            "knight": [
                StatusChange.SC_BLESSING,
                StatusChange.SC_INCREASEAGI,
                StatusChange.SC_TWOHANDQUICKEN,
                StatusChange.SC_CONCENTRATION,
            ],
            "mage": [
                StatusChange.SC_BLESSING,
                StatusChange.SC_MAGNIFICAT,
            ],
            "wizard": [
                StatusChange.SC_BLESSING,
                StatusChange.SC_MAGNIFICAT,
                StatusChange.SC_MAGICPOWER,
            ],
            "archer": [
                StatusChange.SC_BLESSING,
                StatusChange.SC_INCREASEAGI,
                StatusChange.SC_GLORIA,
            ],
            "acolyte": [
                StatusChange.SC_BLESSING,
                StatusChange.SC_ANGELUS,
                StatusChange.SC_INCREASEAGI,
            ],
            "priest": [
                StatusChange.SC_BLESSING,
                StatusChange.SC_ANGELUS,
                StatusChange.SC_INCREASEAGI,
                StatusChange.SC_MAGNIFICAT,
            ],
            "thief": [
                StatusChange.SC_BLESSING,
                StatusChange.SC_INCREASEAGI,
            ],
            "assassin": [
                StatusChange.SC_BLESSING,
                StatusChange.SC_INCREASEAGI,
                StatusChange.SC_EDP,
            ],
            "merchant": [
                StatusChange.SC_BLESSING,
                StatusChange.SC_INCREASEAGI,
            ],
            "blacksmith": [
                StatusChange.SC_BLESSING,
                StatusChange.SC_INCREASEAGI,
                StatusChange.SC_ADRENALINE,
                StatusChange.SC_OVERTHRUST,
            ],
        }
        
        job_key = job.lower()
        job_buffs = essential_buffs.get(job_key, essential_buffs.get("novice", []))
        
        # Return buffs that are not active
        missing = [buff for buff in job_buffs if buff not in active_buffs]
        
        return missing
    
    def is_disabled(self, char_id: int) -> bool:
        """
        Check if character is completely disabled (can't do anything).
        
        Returns True if character is stunned, frozen, etc.
        """
        return not (
            self.can_move(char_id) and 
            self.can_attack(char_id) and 
            self.can_cast(char_id)
        )
    
    def get_status_summary(self, char_id: int) -> dict:
        """
        Get comprehensive status summary for character.
        
        Returns:
            Dictionary with status information for AI decision-making
        """
        active = self.active_effects.get(char_id, set())
        
        return {
            "total_effects": len(active),
            "buffs": len(self.get_active_buffs(char_id)),
            "debuffs": len(self.get_active_debuffs(char_id)),
            "ailments": len(self.get_active_ailments(char_id)),
            "can_move": self.can_move(char_id),
            "can_attack": self.can_attack(char_id),
            "can_cast": self.can_cast(char_id),
            "can_use_item": self.can_use_item(char_id),
            "is_disabled": self.is_disabled(char_id),
            "should_cure": self.should_cure(char_id),
            "cure_priority": self.get_cure_priority(char_id),
            "active_status_names": [
                self.db.get_effect(sc).name if self.db.get_effect(sc) else f"Unknown_{sc}"
                for sc in active
            ]
        }
    
    def recommend_action(self, char_id: int, job: str) -> Optional[str]:
        """
        Recommend next action based on status effects.
        
        Args:
            char_id: Character ID
            job: Job class
        
        Returns:
            Recommended action string or None
        """
        # Priority 1: If disabled, try to cure
        if self.is_disabled(char_id):
            return "wait_for_recovery"
        
        # Priority 2: If dangerous ailments, cure
        if self.should_cure(char_id):
            return "use_cure_item"
        
        # Priority 3: If missing important buffs, buff
        if self.should_buff(char_id, job):
            missing = self.get_missing_buffs(char_id, job)
            if missing:
                effect = self.db.get_effect(missing[0])
                if effect:
                    return f"request_buff_{effect.name}"
        
        # Priority 4: Normal operation
        return None
