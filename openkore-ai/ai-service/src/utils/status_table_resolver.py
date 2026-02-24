"""
Status Table Resolver - Server-Configurable STATUS_id_handle.txt Loader

Different RO servers (bRO, kRO, iRO, etc.) use different status effect IDs.
This resolver loads server-specific status tables with graceful fallback.

Priority:
1. Server-specific: ../tables/{server}/STATUS_id_handle.txt
2. Generic: ../tables/STATUS_id_handle.txt
3. Fallback: Empty dict (log warning)
"""

from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class StatusTableResolver:
    """
    Resolves server-specific STATUS_id_handle.txt paths.
    Falls back gracefully if server-specific table not found.
    """
    
    def __init__(self, tables_base_path: str = "../tables"):
        """
        Initialize status table resolver.
        
        Args:
            tables_base_path: Base path to tables directory (relative to this file)
        """
        # Resolve path relative to this file
        current_dir = Path(__file__).parent
        self.tables_base = (current_dir / tables_base_path).resolve()
        self.status_cache: Dict[str, Dict[str, int]] = {}
        
        logger.info(f"StatusTableResolver initialized with base path: {self.tables_base}")
    
    def get_status_table(self, server_name: str) -> Dict[str, int]:
        """
        Get status effect name->ID mapping for server.
        
        Priority:
        1. Server-specific: tables/{server}/STATUS_id_handle.txt
        2. Generic: tables/STATUS_id_handle.txt
        3. Fallback: Empty dict (log warning)
        
        Args:
            server_name: Server identifier (e.g., 'bRO', 'kRO', 'iRO')
        
        Returns:
            Dictionary mapping status effect names to IDs
        """
        # Check cache
        if server_name in self.status_cache:
            logger.debug(f"Using cached status table for {server_name}")
            return self.status_cache[server_name]
        
        # Try server-specific
        server_specific = self.tables_base / server_name / "STATUS_id_handle.txt"
        if server_specific.exists():
            logger.info(f"[OK] Loading server-specific status table: {server_specific}")
            mapping = self._parse_status_file(server_specific)
            self.status_cache[server_name] = mapping
            logger.info(f"  Loaded {len(mapping)} status effects for {server_name}")
            return mapping
        
        # Try generic
        generic = self.tables_base / "STATUS_id_handle.txt"
        if generic.exists():
            logger.warning(
                f"[WARNING] Server-specific status table not found for {server_name}. "
                f"Using generic: {generic}"
            )
            mapping = self._parse_status_file(generic)
            self.status_cache[server_name] = mapping
            logger.info(f"  Loaded {len(mapping)} generic status effects")
            return mapping
        
        # Fallback
        logger.error(
            f"[ERROR] No status table found for server {server_name}. "
            f"Searched:\n"
            f"  1. {server_specific}\n"
            f"  2. {generic}\n"
            f"Status effect features may not work correctly."
        )
        self.status_cache[server_name] = {}
        return {}
    
    def _parse_status_file(self, filepath: Path) -> Dict[str, int]:
        """
        Parse STATUS_id_handle.txt format.
        
        Format:
            # Comment line
            <status_id> <status_name> [additional_info]
        
        Example:
            30 SC_BLESSING
            32 SC_INCREASEAGI
            # This is a comment
            309 SC_FEAR
        
        Args:
            filepath: Path to STATUS_id_handle.txt file
        
        Returns:
            Dictionary mapping status effect names to IDs
        """
        mapping = {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                line_num = 0
                for line in f:
                    line_num += 1
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse: <id> <name> [extra]
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            status_id = int(parts[0])
                            status_name = parts[1]
                            mapping[status_name] = status_id
                            
                            logger.debug(f"  {status_name} -> {status_id}")
                            
                        except ValueError:
                            logger.warning(
                                f"Invalid line {line_num} in {filepath}: {line}\n"
                                f"  Expected: <int> <name>, got: {parts}"
                            )
                    else:
                        logger.warning(
                            f"Malformed line {line_num} in {filepath}: {line}\n"
                            f"  Expected at least 2 fields, got {len(parts)}"
                        )
        
        except Exception as e:
            logger.error(f"Error parsing {filepath}: {e}", exc_info=True)
        
        return mapping
    
    def get_status_id(self, server_name: str, status_name: str) -> Optional[int]:
        """
        Get status ID by name for specific server.
        
        Args:
            server_name: Server identifier (e.g., 'bRO')
            status_name: Status effect name (e.g., 'SC_BLESSING')
        
        Returns:
            Status effect ID or None if not found
        """
        table = self.get_status_table(server_name)
        status_id = table.get(status_name)
        
        if status_id is None:
            logger.debug(
                f"Status effect '{status_name}' not found for server {server_name}"
            )
        
        return status_id
    
    def is_status_available(self, server_name: str, status_name: str) -> bool:
        """
        Check if status effect is available on server.
        
        Args:
            server_name: Server identifier
            status_name: Status effect name
        
        Returns:
            True if status effect exists on this server
        """
        return self.get_status_id(server_name, status_name) is not None
    
    def get_all_status_names(self, server_name: str) -> list[str]:
        """
        Get all available status effect names for server.
        
        Args:
            server_name: Server identifier
        
        Returns:
            List of status effect names
        """
        table = self.get_status_table(server_name)
        return sorted(table.keys())
    
    def get_status_count(self, server_name: str) -> int:
        """
        Get total number of status effects for server.
        
        Args:
            server_name: Server identifier
        
        Returns:
            Number of defined status effects
        """
        table = self.get_status_table(server_name)
        return len(table)
    
    def clear_cache(self):
        """Clear cached status tables (useful for testing)."""
        self.status_cache.clear()
        logger.info("Status table cache cleared")


# Global instance for convenience
_resolver_instance: Optional[StatusTableResolver] = None


def get_resolver(tables_base_path: str = "../tables") -> StatusTableResolver:
    """
    Get global StatusTableResolver instance (singleton pattern).
    
    Args:
        tables_base_path: Base path to tables directory
    
    Returns:
        Shared StatusTableResolver instance
    """
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = StatusTableResolver(tables_base_path)
    return _resolver_instance


# Example usage
if __name__ == "__main__":
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test resolver
    resolver = StatusTableResolver()
    
    # Test different servers
    for server in ["bRO", "kRO", "iRO", "generic"]:
        print(f"\n{'='*60}")
        print(f"Testing server: {server}")
        print('='*60)
        
        table = resolver.get_status_table(server)
        print(f"Loaded {len(table)} status effects")
        
        # Test specific status lookups
        test_statuses = ["SC_BLESSING", "SC_INCREASEAGI", "SC_FEAR", "SC_FREEZE"]
        for status in test_statuses:
            status_id = resolver.get_status_id(server, status)
            if status_id:
                print(f"  [OK] {status}: {status_id}")
            else:
                print(f"   {status}: NOT FOUND")
