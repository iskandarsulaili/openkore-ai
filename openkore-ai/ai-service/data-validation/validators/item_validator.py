"""
Item data validator.
"""

import logging
from typing import Dict, List, Any, Optional

from .base_validator import BaseValidator, ValidationResult

logger = logging.getLogger(__name__)


class ItemValidator(BaseValidator):
    """
    Validator for item data entries.
    """
    
    # Valid enum values
    VALID_TYPES = [
        'etc', 'weapon', 'armor', 'usable', 'card',
        'ammo', 'consumable', 'healing', 'cash'
    ]
    VALID_GENDERS = ['Male', 'Female', 'Both']
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the validator.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
    
    def validate_entry(self, entry: Dict[str, Any], rules: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate an item entry with item-specific rules.
        
        Args:
            entry: Item entry to validate
            rules: Optional specific rules
            
        Returns:
            ValidationResult object
        """
        # Get base validation
        result = super().validate_entry(entry, rules)
        
        # Item-specific validations
        self._validate_item_specifics(entry, result)
        
        return result
    
    def _validate_item_specifics(self, entry: Dict[str, Any], result: ValidationResult):
        """
        Validate item-specific fields.
        
        Args:
            entry: Item entry
            result: ValidationResult to update
        """
        # Validate type enum
        if 'type' in entry:
            item_type = entry['type']
            if item_type not in self.VALID_TYPES:
                result.add_error(f"Invalid type: {item_type}")
        
        # Validate gender enum
        if 'gender' in entry:
            gender = entry['gender']
            if gender not in self.VALID_GENDERS:
                result.add_error(f"Invalid gender: {gender}")
        
        # Validate price consistency
        self._validate_prices(entry, result)
        
        # Validate equipment-specific fields
        item_type = entry.get('type', '')
        if item_type in ['weapon', 'armor']:
            self._validate_equipment_fields(entry, result)
        
        # Validate weight
        if 'weight' in entry:
            weight = entry['weight']
            if not isinstance(weight, (int, float)) or weight < 0:
                result.add_error(f"Invalid weight: {weight} (must be >= 0)")
        
        # Check logical consistency
        self._validate_logical_consistency(entry, result)
    
    def _validate_prices(self, entry: Dict[str, Any], result: ValidationResult):
        """
        Validate price fields.
        
        Args:
            entry: Item entry
            result: ValidationResult to update
        """
        buy_price = entry.get('buy_price', 0)
        sell_price = entry.get('sell_price', 0)
        
        # Validate price values
        if buy_price < 0:
            result.add_error(f"Invalid buy_price: {buy_price} (must be >= 0)")
        
        if sell_price < 0:
            result.add_error(f"Invalid sell_price: {sell_price} (must be >= 0)")
        
        # Check price relationship
        if buy_price > 0 and sell_price > 0:
            if sell_price > buy_price:
                result.add_error(f"Sell price ({sell_price}) higher than buy price ({buy_price})")
            
            # Typically sell price should be around 50% of buy price
            expected_sell = buy_price // 2
            if abs(sell_price - expected_sell) > buy_price * 0.1:
                result.add_warning(f"Unusual price ratio: buy={buy_price}, sell={sell_price}")
    
    def _validate_equipment_fields(self, entry: Dict[str, Any], result: ValidationResult):
        """
        Validate equipment-specific fields.
        
        Args:
            entry: Item entry
            result: ValidationResult to update
        """
        item_type = entry.get('type', '')
        
        # Weapons should have attack or magic_attack
        if item_type == 'weapon':
            if 'attack' not in entry and 'magic_attack' not in entry:
                result.add_warning("Weapon has no attack or magic_attack value")
            
            # Check weapon level
            if 'weapon_level' in entry:
                level = entry['weapon_level']
                if not isinstance(level, int) or level < 1 or level > 4:
                    result.add_error(f"Invalid weapon_level: {level} (must be 1-4)")
        
        # Armor should have defense
        if item_type == 'armor':
            if 'defense' not in entry:
                result.add_warning("Armor has no defense value")
            
            # Check armor level
            if 'armor_level' in entry:
                level = entry['armor_level']
                if not isinstance(level, int) or level < 1 or level > 2:
                    result.add_error(f"Invalid armor_level: {level} (must be 1-2)")
        
        # Check equip level requirements
        if 'equip_level_min' in entry:
            min_level = entry['equip_level_min']
            if not isinstance(min_level, int) or min_level < 0 or min_level > 999:
                result.add_error(f"Invalid equip_level_min: {min_level}")
            
            if 'equip_level_max' in entry:
                max_level = entry['equip_level_max']
                if max_level > 0 and min_level > max_level:
                    result.add_error(f"equip_level_min ({min_level}) > equip_level_max ({max_level})")
        
        # Check slots
        if 'slots' in entry:
            slots = entry['slots']
            if not isinstance(slots, int) or slots < 0 or slots > 4:
                result.add_error(f"Invalid slots: {slots} (must be 0-4)")
    
    def _validate_logical_consistency(self, entry: Dict[str, Any], result: ValidationResult):
        """
        Validate logical consistency of item data.
        
        Args:
            entry: Item entry
            result: ValidationResult to update
        """
        # Check if expensive items have reasonable weight
        buy_price = entry.get('buy_price', 0)
        weight = entry.get('weight', 0)
        
        if buy_price > 1000000 and weight > 5000:
            result.add_warning(f"Very expensive item is also very heavy: price={buy_price}, weight={weight}")
        
        # Check if consumables have reasonable prices
        item_type = entry.get('type', '')
        if item_type in ['usable', 'consumable', 'healing'] and buy_price > 10000000:
            result.add_warning(f"Consumable item has very high price: {buy_price}")
    
    def validate(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate all item entries and generate report.
        
        Args:
            items: List of item entries
            
        Returns:
            Validation report
        """
        logger.info(f"Validating {len(items)} items...")
        
        # Check ID uniqueness
        duplicate_ids = self.check_id_uniqueness(items)
        if duplicate_ids:
            logger.error(f"Found {len(duplicate_ids)} duplicate item IDs: {duplicate_ids[:10]}")
        
        # Validate all entries
        results = self.validate_all(items)
        
        # Generate report
        report = self.generate_report(results)
        
        # Add item-specific stats
        report['duplicate_ids'] = duplicate_ids
        report['duplicate_count'] = len(duplicate_ids)
        
        # Stats by category
        type_distribution = self._calculate_type_distribution(items)
        price_distribution = self._calculate_price_distribution(items)
        weight_distribution = self._calculate_weight_distribution(items)
        
        report['statistics'] = {
            'type_distribution': type_distribution,
            'price_distribution': price_distribution,
            'weight_distribution': weight_distribution
        }
        
        logger.info(f"Validation complete: {report['summary']['passed']}/{report['summary']['total_entries']} passed")
        
        return report
    
    def _calculate_type_distribution(self, items: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate distribution of items by type."""
        distribution = {}
        for item in items:
            item_type = item.get('type', 'unknown')
            distribution[item_type] = distribution.get(item_type, 0) + 1
        return distribution
    
    def _calculate_price_distribution(self, items: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate distribution of items by price ranges."""
        distribution = {
            '0-1000': 0,
            '1001-10000': 0,
            '10001-100000': 0,
            '100001-1000000': 0,
            '1000000+': 0
        }
        
        for item in items:
            price = item.get('buy_price', 0)
            if price <= 1000:
                distribution['0-1000'] += 1
            elif price <= 10000:
                distribution['1001-10000'] += 1
            elif price <= 100000:
                distribution['10001-100000'] += 1
            elif price <= 1000000:
                distribution['100001-1000000'] += 1
            else:
                distribution['1000000+'] += 1
        
        return distribution
    
    def _calculate_weight_distribution(self, items: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate distribution of items by weight ranges."""
        distribution = {
            '0-100': 0,
            '101-500': 0,
            '501-1000': 0,
            '1001-5000': 0,
            '5000+': 0
        }
        
        for item in items:
            weight = item.get('weight', 0)
            if weight <= 100:
                distribution['0-100'] += 1
            elif weight <= 500:
                distribution['101-500'] += 1
            elif weight <= 1000:
                distribution['501-1000'] += 1
            elif weight <= 5000:
                distribution['1001-5000'] += 1
            else:
                distribution['5000+'] += 1
        
        return distribution
