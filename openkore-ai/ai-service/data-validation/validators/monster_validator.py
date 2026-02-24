"""
Monster data validator.
"""

import logging
from typing import Dict, List, Any, Optional

from .base_validator import BaseValidator, ValidationResult

logger = logging.getLogger(__name__)


class MonsterValidator(BaseValidator):
    """
    Validator for monster data entries.
    """
    
    # Valid enum values
    VALID_SIZES = ['small', 'medium', 'large']
    VALID_RACES = [
        'formless', 'undead', 'brute', 'plant', 'insect',
        'fish', 'demon', 'demi_human', 'angel', 'dragon'
    ]
    VALID_ELEMENTS = [
        'neutral', 'water', 'earth', 'fire', 'wind',
        'poison', 'holy', 'dark', 'ghost', 'undead'
    ]
    
    def __init__(self, config: Dict[str, Any], item_references: Optional[List[int]] = None):
        """
        Initialize the validator.
        
        Args:
            config: Configuration dictionary
            item_references: Optional list of valid item IDs for drop validation
        """
        super().__init__(config)
        self.item_references = item_references or []
    
    def validate_entry(self, entry: Dict[str, Any], rules: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate a monster entry with monster-specific rules.
        
        Args:
            entry: Monster entry to validate
            rules: Optional specific rules
            
        Returns:
            ValidationResult object
        """
        # Get base validation
        result = super().validate_entry(entry, rules)
        
        # Monster-specific validations
        self._validate_monster_specifics(entry, result)
        
        return result
    
    def _validate_monster_specifics(self, entry: Dict[str, Any], result: ValidationResult):
        """
        Validate monster-specific fields.
        
        Args:
            entry: Monster entry
            result: ValidationResult to update
        """
        # Validate size enum
        if 'size' in entry:
            size = entry['size']
            if size not in self.VALID_SIZES:
                result.add_error(f"Invalid size: {size}")
        
        # Validate race enum
        if 'race' in entry:
            race = entry['race']
            if race not in self.VALID_RACES:
                result.add_error(f"Invalid race: {race}")
        
        # Validate element enum
        if 'element' in entry:
            element = entry['element']
            if element not in self.VALID_ELEMENTS:
                result.add_error(f"Invalid element: {element}")
        
        # Validate element level
        if 'element_level' in entry:
            level = entry['element_level']
            if not isinstance(level, int) or level < 1 or level > 4:
                result.add_error(f"Invalid element_level: {level} (must be 1-4)")
        
        # Validate drops if item references available
        if self.item_references and 'drops' in entry:
            self._validate_drops(entry['drops'], result)
        
        # Validate MVP drops if item references available
        if self.item_references and 'mvp_drops' in entry:
            self._validate_drops(entry['mvp_drops'], result)
        
        # Check logical consistency
        self._validate_logical_consistency(entry, result)
    
    def _validate_drops(self, drops: List[Dict[str, Any]], result: ValidationResult):
        """
        Validate drop entries.
        
        Args:
            drops: List of drop entries
            result: ValidationResult to update
        """
        if not isinstance(drops, list):
            result.add_error("Drops must be a list")
            return
        
        for i, drop in enumerate(drops):
            if not isinstance(drop, dict):
                result.add_error(f"Drop {i} is not a dictionary")
                continue
            
            # Check required drop fields
            if 'item' not in drop:
                result.add_error(f"Drop {i} missing item name")
            
            if 'rate' not in drop:
                result.add_error(f"Drop {i} missing rate")
            else:
                rate = drop['rate']
                if not isinstance(rate, (int, float)) or rate < 0 or rate > 10000:
                    result.add_error(f"Drop {i} invalid rate: {rate} (must be 0-10000)")
    
    def _validate_logical_consistency(self, entry: Dict[str, Any], result: ValidationResult):
        """
        Validate logical consistency of monster stats.
        
        Args:
            entry: Monster entry
            result: ValidationResult to update
        """
        # Check if boss monsters have MVP exp
        if entry.get('mvp_exp', 0) > 0 and not entry.get('mvp_drops'):
            result.add_warning("Monster has MVP exp but no MVP drops")
        
        # Check if high level monsters have reasonable exp
        level = entry.get('level', 0)
        base_exp = entry.get('base_exp', 0)
        
        if level > 50 and base_exp < 100:
            result.add_warning(f"High level monster (Lv{level}) has very low base exp ({base_exp})")
        
        # Check HP consistency with level
        hp = entry.get('hp', 0)
        if level > 0 and hp > 0:
            expected_min_hp = level * 5
            if hp < expected_min_hp:
                result.add_warning(f"HP ({hp}) seems low for level {level}")
        
        # Check if attack range is reasonable
        attack_range = entry.get('attack_range', 0)
        if attack_range > 14:
            result.add_warning(f"Unusually high attack range: {attack_range}")
    
    def validate(self, monsters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate all monster entries and generate report.
        
        Args:
            monsters: List of monster entries
            
        Returns:
            Validation report
        """
        logger.info(f"Validating {len(monsters)} monsters...")
        
        # Check ID uniqueness
        duplicate_ids = self.check_id_uniqueness(monsters)
        if duplicate_ids:
            logger.error(f"Found {len(duplicate_ids)} duplicate monster IDs: {duplicate_ids[:10]}")
        
        # Validate all entries
        results = self.validate_all(monsters)
        
        # Generate report
        report = self.generate_report(results)
        
        # Add monster-specific stats
        report['duplicate_ids'] = duplicate_ids
        report['duplicate_count'] = len(duplicate_ids)
        
        # Stats by category
        level_distribution = self._calculate_level_distribution(monsters)
        race_distribution = self._calculate_race_distribution(monsters)
        element_distribution = self._calculate_element_distribution(monsters)
        
        report['statistics'] = {
            'level_distribution': level_distribution,
            'race_distribution': race_distribution,
            'element_distribution': element_distribution
        }
        
        logger.info(f"Validation complete: {report['summary']['passed']}/{report['summary']['total_entries']} passed")
        
        return report
    
    def _calculate_level_distribution(self, monsters: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate distribution of monsters by level ranges."""
        distribution = {
            '1-10': 0,
            '11-20': 0,
            '21-30': 0,
            '31-40': 0,
            '41-50': 0,
            '51-60': 0,
            '61-70': 0,
            '71-80': 0,
            '81-90': 0,
            '91-100': 0,
            '100+': 0
        }
        
        for monster in monsters:
            level = monster.get('level', 0)
            if level <= 10:
                distribution['1-10'] += 1
            elif level <= 20:
                distribution['11-20'] += 1
            elif level <= 30:
                distribution['21-30'] += 1
            elif level <= 40:
                distribution['31-40'] += 1
            elif level <= 50:
                distribution['41-50'] += 1
            elif level <= 60:
                distribution['51-60'] += 1
            elif level <= 70:
                distribution['61-70'] += 1
            elif level <= 80:
                distribution['71-80'] += 1
            elif level <= 90:
                distribution['81-90'] += 1
            elif level <= 100:
                distribution['91-100'] += 1
            else:
                distribution['100+'] += 1
        
        return distribution
    
    def _calculate_race_distribution(self, monsters: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate distribution of monsters by race."""
        distribution = {}
        for monster in monsters:
            race = monster.get('race', 'unknown')
            distribution[race] = distribution.get(race, 0) + 1
        return distribution
    
    def _calculate_element_distribution(self, monsters: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate distribution of monsters by element."""
        distribution = {}
        for monster in monsters:
            element = monster.get('element', 'unknown')
            distribution[element] = distribution.get(element, 0) + 1
        return distribution
