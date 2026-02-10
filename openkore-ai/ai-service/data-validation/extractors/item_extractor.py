"""
Item data extractor from rAthena item_db_*.yml files.
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import json

from .yaml_parser import RathenaYAMLParser

logger = logging.getLogger(__name__)


class ItemExtractor:
    """
    Extract item data from rAthena item database files and transform to AI service format.
    """
    
    def __init__(self, config: Dict[str, Any], field_mappings: Dict[str, Any]):
        """
        Initialize the extractor.
        
        Args:
            config: Configuration dictionary
            field_mappings: Field mapping dictionary
        """
        self.config = config
        self.field_mappings = field_mappings.get('item_fields', {})
        self.type_mappings = field_mappings.get('type_mappings', {})
        
        # Initialize parser
        base_path = config['paths']['reference_base']
        self.parser = RathenaYAMLParser(base_path)
    
    def extract(self, progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        """
        Extract all item entries from multiple database files.
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of transformed item entries
        """
        all_items = []
        
        # Extract from each item database file
        item_sources = ['items_etc', 'items_equip', 'items_usable']
        
        for source_key in item_sources:
            if source_key not in self.config['sources']:
                continue
            
            source_path = self.config['sources'][source_key]['reference']
            logger.info(f"Extracting items from: {source_path}")
            
            try:
                # Parse the database
                raw_entries = self.parser.parse_database_with_progress(
                    source_path,
                    progress_callback=progress_callback,
                    batch_size=self.config['processing']['batch_size']
                )
                
                # Transform entries
                for entry in raw_entries:
                    try:
                        transformed_entry = self.transform_entry(entry, source_key)
                        all_items.append(transformed_entry)
                    except Exception as e:
                        logger.error(f"Error transforming item {entry.get('Id', 'UNKNOWN')}: {e}")
                
                logger.info(f"Extracted {len(raw_entries)} items from {source_path}")
            
            except Exception as e:
                logger.error(f"Error extracting from {source_path}: {e}")
        
        logger.info(f"Total items extracted: {len(all_items)}")
        return all_items
    
    def transform_entry(self, entry: Dict[str, Any], source: str) -> Dict[str, Any]:
        """
        Transform an item entry from rAthena format to AI service format.
        
        Args:
            entry: Raw item entry from YAML
            source: Source database identifier
            
        Returns:
            Transformed entry with snake_case fields
        """
        transformed = {}
        
        # Map basic fields
        for source_field, target_field in self.field_mappings.items():
            if source_field in entry:
                value = entry[source_field]
                
                # Apply value transformations
                if source_field == 'Type' and value in self.type_mappings:
                    value = self.type_mappings[value]
                
                transformed[target_field] = value
        
        # Add source metadata
        transformed['source_database'] = source
        transformed['source'] = 'rathena_item_db'
        transformed['extraction_version'] = '1.0'
        
        return transformed
    
    def extract_to_file(self, output_path: str, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        Extract items and save to JSON file.
        
        Args:
            output_path: Path to output JSON file
            progress_callback: Optional progress callback
            
        Returns:
            Statistics about the extraction
        """
        items = self.extract(progress_callback=progress_callback)
        
        # Calculate statistics
        type_counts = {}
        for item in items:
            item_type = item.get('type', 'unknown')
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
        
        # Prepare output data
        output_data = {
            'metadata': {
                'source': 'rathena-AI-world',
                'databases': ['item_db_etc.yml', 'item_db_equip.yml', 'item_db_usable.yml'],
                'total_entries': len(items),
                'type_distribution': type_counts,
                'extraction_version': '1.0'
            },
            'items': items
        }
        
        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(items)} items to {output_path}")
        
        # Return statistics
        stats = {
            'total_extracted': len(items),
            'type_distribution': type_counts,
            'output_file': str(output_file),
            'file_size_bytes': output_file.stat().st_size
        }
        
        return stats
    
    def get_item_by_id(self, item_id: int, items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find an item by ID.
        
        Args:
            item_id: Item ID to find
            items: List of item entries
            
        Returns:
            Item entry or None if not found
        """
        for item in items:
            if item.get('id') == item_id:
                return item
        return None
    
    def get_items_by_type(self, items: List[Dict[str, Any]], item_type: str) -> List[Dict[str, Any]]:
        """
        Get items of a specific type.
        
        Args:
            items: List of item entries
            item_type: Item type (in snake_case)
            
        Returns:
            Filtered list of items
        """
        return [item for item in items if item.get('type') == item_type]
    
    def get_equipable_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get all equipable items (weapons and armor).
        
        Args:
            items: List of item entries
            
        Returns:
            Filtered list of equipable items
        """
        return [
            item for item in items
            if item.get('type') in ['weapon', 'armor']
        ]
    
    def get_consumable_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get all consumable items.
        
        Args:
            items: List of item entries
            
        Returns:
            Filtered list of consumable items
        """
        return [
            item for item in items
            if item.get('type') in ['usable', 'consumable', 'healing']
        ]
    
    def get_items_by_weight_range(
        self,
        items: List[Dict[str, Any]],
        min_weight: int,
        max_weight: int
    ) -> List[Dict[str, Any]]:
        """
        Get items within a weight range.
        
        Args:
            items: List of item entries
            min_weight: Minimum weight (inclusive)
            max_weight: Maximum weight (inclusive)
            
        Returns:
            Filtered list of items
        """
        return [
            item for item in items
            if min_weight <= item.get('weight', 0) <= max_weight
        ]
    
    def get_items_by_price_range(
        self,
        items: List[Dict[str, Any]],
        min_price: int,
        max_price: int
    ) -> List[Dict[str, Any]]:
        """
        Get items within a price range.
        
        Args:
            items: List of item entries
            min_price: Minimum buy price (inclusive)
            max_price: Maximum buy price (inclusive)
            
        Returns:
            Filtered list of items
        """
        return [
            item for item in items
            if min_price <= item.get('buy_price', 0) <= max_price
        ]
