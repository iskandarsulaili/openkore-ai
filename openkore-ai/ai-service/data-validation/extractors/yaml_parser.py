"""
Generic YAML parser for rAthena database files.
Handles the specific Header/Body/Footer structure used in rAthena.
"""

import yaml
import os
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class RathenaYAMLParser:
    """
    Parser for rAthena YAML database files.
    
    Supports:
    - Header/Body/Footer structure
    - Import resolution (re/pre-re splits)
    - Nested structures and arrays
    - Error handling with line number reporting
    """
    
    def __init__(self, base_path: str):
        """
        Initialize the parser.
        
        Args:
            base_path: Base directory path for rAthena files
        """
        self.base_path = Path(base_path)
        if not self.base_path.exists():
            raise ValueError(f"Base path does not exist: {base_path}")
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a single YAML file.
        
        Args:
            file_path: Relative path to YAML file from base_path
            
        Returns:
            Parsed YAML content as dictionary
            
        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        full_path = self.base_path / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {full_path}")
        
        logger.info(f"Parsing YAML file: {full_path}")
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if data is None:
                logger.warning(f"Empty YAML file: {full_path}")
                return {}
            
            return data
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parse error in {full_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error reading {full_path}: {e}")
            raise
    
    def parse_database(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse a rAthena database file and extract Body entries.
        
        Args:
            file_path: Relative path to database YAML file
            
        Returns:
            List of entries from the Body section
        """
        data = self.parse_file(file_path)
        
        # Validate structure
        if not isinstance(data, dict):
            logger.error(f"Invalid database structure in {file_path}: expected dict, got {type(data)}")
            return []
        
        # Check for Header
        if 'Header' in data:
            header = data['Header']
            logger.info(f"Database type: {header.get('Type', 'UNKNOWN')}, Version: {header.get('Version', 'UNKNOWN')}")
        
        # Extract Body entries
        body = data.get('Body', [])
        if not isinstance(body, list):
            logger.error(f"Invalid Body structure in {file_path}: expected list, got {type(body)}")
            return []
        
        logger.info(f"Extracted {len(body)} entries from {file_path}")
        return body
    
    def validate_schema(self, data: Dict[str, Any], expected_type: str) -> bool:
        """
        Validate the schema of a database file.
        
        Args:
            data: Parsed YAML data
            expected_type: Expected database type (e.g., 'MOB_DB', 'ITEM_DB')
            
        Returns:
            True if schema is valid
        """
        if not isinstance(data, dict):
            logger.error("Invalid schema: root is not a dictionary")
            return False
        
        if 'Header' not in data:
            logger.error("Invalid schema: missing Header")
            return False
        
        header = data['Header']
        if not isinstance(header, dict):
            logger.error("Invalid schema: Header is not a dictionary")
            return False
        
        db_type = header.get('Type')
        if db_type != expected_type:
            logger.warning(f"Schema type mismatch: expected {expected_type}, got {db_type}")
            return False
        
        if 'Body' not in data:
            logger.error("Invalid schema: missing Body")
            return False
        
        if not isinstance(data['Body'], list):
            logger.error("Invalid schema: Body is not a list")
            return False
        
        logger.info(f"Schema validation passed for {expected_type}")
        return True
    
    def resolve_imports(self, file_path: str) -> List[str]:
        """
        Resolve import statements in database files.
        
        Some rAthena databases split content into re/pre-re modes.
        This method identifies if imports are used.
        
        Args:
            file_path: Path to database file
            
        Returns:
            List of file paths that should be parsed (including the main file)
        """
        # For now, we directly parse the specified file
        # In rAthena, the re/ and pre-re/ directories contain separate databases
        # No import resolution needed as we specify the exact file
        return [file_path]
    
    def parse_database_with_progress(
        self,
        file_path: str,
        progress_callback: Optional[callable] = None,
        batch_size: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Parse a database file with progress reporting.
        
        Args:
            file_path: Relative path to database file
            progress_callback: Optional callback function(current, total)
            batch_size: Number of entries to process before progress update
            
        Returns:
            List of parsed entries
        """
        entries = self.parse_database(file_path)
        total = len(entries)
        
        if progress_callback:
            progress_callback(0, total)
        
        # Process in batches
        processed = []
        for i, entry in enumerate(entries):
            processed.append(entry)
            
            if progress_callback and (i + 1) % batch_size == 0:
                progress_callback(i + 1, total)
        
        if progress_callback:
            progress_callback(total, total)
        
        return processed
    
    def get_database_stats(self, file_path: str) -> Dict[str, Any]:
        """
        Get statistics about a database file without fully parsing it.
        
        Args:
            file_path: Relative path to database file
            
        Returns:
            Dictionary containing statistics
        """
        full_path = self.base_path / file_path
        
        stats = {
            'file_path': str(full_path),
            'exists': full_path.exists(),
            'size_bytes': 0,
            'entry_count': 0,
            'database_type': None,
            'version': None
        }
        
        if not full_path.exists():
            return stats
        
        stats['size_bytes'] = full_path.stat().st_size
        
        try:
            data = self.parse_file(file_path)
            
            if 'Header' in data:
                header = data['Header']
                stats['database_type'] = header.get('Type')
                stats['version'] = header.get('Version')
            
            if 'Body' in data and isinstance(data['Body'], list):
                stats['entry_count'] = len(data['Body'])
        
        except Exception as e:
            logger.warning(f"Error getting stats for {file_path}: {e}")
        
        return stats
