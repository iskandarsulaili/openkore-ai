"""
Monster data extractor from rAthena mob_db.yml.
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import json

from .yaml_parser import RathenaYAMLParser

logger = logging.getLogger(__name__)


class MonsterExtractor:
    """
    Extract monster data from rAthena mob_db.yml and transform to AI service format.
    """
    
    def __init__(self, config: Dict[str, Any], field_mappings: Dict[str, Any]):
        """
        Initialize the extractor.
        
        Args:
            config: Configuration dictionary
            field_mappings: Field mapping dictionary
        """
        self.config = config
        self.field_mappings = field_mappings.get('monster_fields', {})
        self.size_mappings = field_mappings.get('size_mappings', {})
        self.race_mappings = field_mappings.get('race_mappings', {})
        self.element_mappings = field_mappings.get('element_mappings', {})
        
        # Initialize parser
        base_path = config['paths']['reference_base']
        self.parser = RathenaYAMLParser(base_path)
    
    def extract(self, progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        """
        Extract all monster entries from the database.
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of transformed monster entries
        """
        source_path = self.config['sources']['monsters']['reference']
        logger.info(f"Extracting monsters from: {source_path}")
        
        # Parse the database
        raw_entries = self.parser.parse_database_with_progress(
            source_path,
            progress_callback=progress_callback,
            batch_size=self.config['processing']['batch_size']
        )
        
        # Transform entries
        transformed = []
        for entry in raw_entries:
            try:
                transformed_entry = self.transform_entry(entry)
                transformed.append(transformed_entry)
            except Exception as e:
                logger.error(f"Error transforming monster {entry.get('Id', 'UNKNOWN')}: {e}")
        
        logger.info(f"Extracted {len(transformed)} monsters (from {len(raw_entries)} raw entries)")
        return transformed
    
    def transform_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a monster entry from rAthena format to AI service format.
        
        Args:
            entry: Raw monster entry from YAML
            
        Returns:
            Transformed entry with snake_case fields
        """
        transformed = {}
        
        # Map basic fields
        for source_field, target_field in self.field_mappings.items():
            if source_field in entry:
                value = entry[source_field]
                
                # Apply value transformations
                if source_field == 'Size' and value in self.size_mappings:
                    value = self.size_mappings[value]
                elif source_field == 'Race' and value in self.race_mappings:
                    value = self.race_mappings[value]
                elif source_field == 'Element' and value in self.element_mappings:
                    value = self.element_mappings[value]
                
                transformed[target_field] = value
        
        # Transform drops
        if 'Drops' in entry:
            transformed['drops'] = self.transform_drops(entry['Drops'])
        
        # Transform MVP drops
        if 'MvpDrops' in entry:
            transformed['mvp_drops'] = self.transform_drops(entry['MvpDrops'])
        
        # Add metadata
        transformed['source'] = 'rathena_mob_db'
        transformed['extraction_version'] = '1.0'
        
        return transformed
    
    def transform_drops(self, drops: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform drop list to AI service format.
        
        Args:
            drops: List of drop entries
            
        Returns:
            Transformed drop list
        """
        transformed = []
        
        for drop in drops:
            transformed_drop = {
                'item': drop.get('Item'),
                'rate': drop.get('Rate', 0),
            }
            
            if 'StealProtected' in drop:
                transformed_drop['steal_protected'] = drop['StealProtected']
            
            if 'RandomOptionGroup' in drop:
                transformed_drop['random_option_group'] = drop['RandomOptionGroup']
            
            transformed.append(transformed_drop)
        
        return transformed
    
    def extract_to_file(self, output_path: str, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        Extract monsters and save to JSON file.
        
        Args:
            output_path: Path to output JSON file
            progress_callback: Optional progress callback
            
        Returns:
            Statistics about the extraction
        """
        monsters = self.extract(progress_callback=progress_callback)
        
        # Prepare output data
        output_data = {
            'metadata': {
                'source': 'rathena-AI-world',
                'database': 'mob_db.yml',
                'total_entries': len(monsters),
                'extraction_version': '1.0'
            },
            'monsters': monsters
        }
        
        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(monsters)} monsters to {output_path}")
        
        # Return statistics
        stats = {
            'total_extracted': len(monsters),
            'output_file': str(output_file),
            'file_size_bytes': output_file.stat().st_size
        }
        
        return stats
    
    def get_monster_by_id(self, monster_id: int, monsters: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find a monster by ID.
        
        Args:
            monster_id: Monster ID to find
            monsters: List of monster entries
            
        Returns:
            Monster entry or None if not found
        """
        for monster in monsters:
            if monster.get('id') == monster_id:
                return monster
        return None
    
    def get_monsters_by_level_range(
        self,
        monsters: List[Dict[str, Any]],
        min_level: int,
        max_level: int
    ) -> List[Dict[str, Any]]:
        """
        Get monsters within a level range.
        
        Args:
            monsters: List of monster entries
            min_level: Minimum level (inclusive)
            max_level: Maximum level (inclusive)
            
        Returns:
            Filtered list of monsters
        """
        return [
            m for m in monsters
            if min_level <= m.get('level', 0) <= max_level
        ]
    
    def get_monsters_by_race(
        self,
        monsters: List[Dict[str, Any]],
        race: str
    ) -> List[Dict[str, Any]]:
        """
        Get monsters of a specific race.
        
        Args:
            monsters: List of monster entries
            race: Race name (in snake_case)
            
        Returns:
            Filtered list of monsters
        """
        return [m for m in monsters if m.get('race') == race]
    
    def get_monsters_by_element(
        self,
        monsters: List[Dict[str, Any]],
        element: str
    ) -> List[Dict[str, Any]]:
        """
        Get monsters of a specific element.
        
        Args:
            monsters: List of monster entries
            element: Element name (in snake_case)
            
        Returns:
            Filtered list of monsters
        """
        return [m for m in monsters if m.get('element') == element]
