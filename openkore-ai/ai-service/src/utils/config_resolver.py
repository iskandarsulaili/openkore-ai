"""
Dynamic Configuration Path Resolver for OpenKore
Resolves paths like recvpackets.txt based on servers.txt configuration
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class ConfigPathResolver:
    """
    Resolves OpenKore configuration paths dynamically based on servers.txt and config.txt.
    
    This ensures that paths like recvpackets.txt are adaptive to the current server
    configuration rather than being hardcoded.
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize the resolver.
        
        Args:
            base_dir: Base directory for OpenKore (defaults to ../../../ from this file)
        """
        if base_dir is None:
            # Default to openkore-ai directory (3 levels up from src/utils/)
            self.base_dir = Path(__file__).parent.parent.parent.parent
        else:
            self.base_dir = Path(base_dir)
            
        self.config_file = self.base_dir / "control" / "config.txt"
        self.servers_file = self.base_dir / "tables" / "servers.txt"
        
        # Cache for parsed server configurations
        self._server_cache: Optional[Dict[str, Dict[str, str]]] = None
    
    def get_current_server_name(self) -> Optional[str]:
        """
        Extract the current server name from config.txt.
        
        Returns:
            Server name (e.g., "WoM", "Korea - kRO: Sara/Rangidis/Thanatos")
            or None if not found
        """
        try:
            if not self.config_file.exists():
                logger.warning(f"Config file not found: {self.config_file}")
                return None
            
            with open(self.config_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    # Remove comments and whitespace
                    line = line.split('#')[0].strip()
                    
                    # Look for "master <server_name>"
                    match = re.match(r'^master\s+(.+)$', line, re.IGNORECASE)
                    if match:
                        server_name = match.group(1).strip()
                        logger.info(f"Found current server: {server_name}")
                        return server_name
            
            logger.warning("No 'master' configuration found in config.txt")
            return None
            
        except Exception as e:
            logger.error(f"Error reading config.txt: {e}")
            return None
    
    def parse_servers_txt(self) -> Dict[str, Dict[str, str]]:
        """
        Parse servers.txt and extract all server configurations.
        
        Returns:
            Dictionary mapping server names to their configuration options
            Example: {
                "WoM": {
                    "ip": "172.86.126.116",
                    "port": "6900",
                    "addTableFolders": "kRO/Ragexe_2021_11_03;translated/kRO_english;kRO",
                    "recvpackets": "custom_recvpackets.txt"  # if specified
                },
                ...
            }
        """
        if self._server_cache is not None:
            return self._server_cache
        
        try:
            if not self.servers_file.exists():
                logger.error(f"Servers file not found: {self.servers_file}")
                return {}
            
            servers = {}
            current_server = None
            current_config = {}
            
            with open(self.servers_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    # Remove comments
                    line = line.split('#')[0].strip()
                    
                    if not line:
                        continue
                    
                    # Check for server block start [Server Name]
                    match = re.match(r'^\[(.+)\]$', line)
                    if match:
                        # Save previous server config if exists
                        if current_server:
                            servers[current_server] = current_config
                        
                        # Start new server config
                        current_server = match.group(1).strip()
                        current_config = {}
                        continue
                    
                    # Parse key-value pairs
                    if current_server:
                        parts = line.split(None, 1)  # Split on first whitespace
                        if len(parts) == 2:
                            key, value = parts
                            current_config[key] = value.strip()
                        elif len(parts) == 1:
                            # Handle boolean flags or empty values
                            current_config[parts[0]] = ''
            
            # Save last server config
            if current_server:
                servers[current_server] = current_config
            
            self._server_cache = servers
            logger.info(f"Parsed {len(servers)} server configurations from servers.txt")
            return servers
            
        except Exception as e:
            logger.error(f"Error parsing servers.txt: {e}")
            return {}
    
    def get_server_config(self, server_name: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
        Get configuration for a specific server.
        
        Args:
            server_name: Server name to look up (if None, uses current from config.txt)
        
        Returns:
            Server configuration dictionary or None if not found
        """
        if server_name is None:
            server_name = self.get_current_server_name()
        
        if server_name is None:
            logger.warning("Could not determine server name")
            return None
        
        servers = self.parse_servers_txt()
        config = servers.get(server_name)
        
        if config is None:
            logger.warning(f"Server configuration not found for: {server_name}")
        
        return config
    
    def get_recvpackets_path(self, server_name: Optional[str] = None, 
                            absolute: bool = False) -> Optional[str]:
        """
        Dynamically resolve the recvpackets.txt path for the current/specified server.
        
        This is the primary method to use for getting the correct recvpackets.txt path.
        
        Args:
            server_name: Server name to look up (if None, uses current from config.txt)
            absolute: If True, return absolute path; if False, return relative to base_dir
        
        Returns:
            Path to recvpackets.txt or None if cannot be resolved
            
        Examples:
            For WoM server: "../tables/kRO/Ragexe_2021_11_03/recvpackets.txt"
            For ROla: "../tables/ROla/recvpackets.txt"
        """
        config = self.get_server_config(server_name)
        
        if config is None:
            logger.error("Could not get server configuration")
            return None
        
        # Check if server has custom recvpackets filename
        custom_recvpackets = config.get('recvpackets', '').strip()
        
        # Get addTableFolders (semicolon-separated list)
        table_folders_str = config.get('addTableFolders', '').strip()
        
        if not table_folders_str:
            logger.warning(f"No addTableFolders defined for server")
            # Fallback to default
            recvpackets_filename = custom_recvpackets if custom_recvpackets else 'recvpackets.txt'
            recvpackets_path = self.base_dir / "tables" / recvpackets_filename
        else:
            # Split by semicolon and take the first folder (primary table folder)
            table_folders = [f.strip() for f in table_folders_str.split(';')]
            primary_folder = table_folders[0]
            
            # Construct path
            recvpackets_filename = custom_recvpackets if custom_recvpackets else 'recvpackets.txt'
            recvpackets_path = self.base_dir / "tables" / primary_folder / recvpackets_filename
        
        # Check if file exists
        if not recvpackets_path.exists():
            logger.warning(f"Recvpackets file does not exist: {recvpackets_path}")
            # Try to find it in alternative locations
            for folder in table_folders if table_folders_str else []:
                alt_path = self.base_dir / "tables" / folder / recvpackets_filename
                if alt_path.exists():
                    logger.info(f"Found recvpackets in alternative folder: {alt_path}")
                    recvpackets_path = alt_path
                    break
        
        # Return appropriate format
        if absolute:
            return str(recvpackets_path.resolve())
        else:
            # Return relative path from ai-service/src directory
            try:
                relative_path = recvpackets_path.relative_to(self.base_dir)
                return f"../{relative_path.as_posix()}"
            except ValueError:
                # If relative path fails, return absolute
                return str(recvpackets_path.resolve())
    
    def get_all_table_folders(self, server_name: Optional[str] = None) -> List[str]:
        """
        Get all table folders for the server (in priority order).
        
        Args:
            server_name: Server name to look up (if None, uses current from config.txt)
        
        Returns:
            List of table folder paths (relative to tables directory)
            Example: ["kRO/Ragexe_2021_11_03", "translated/kRO_english", "kRO"]
        """
        config = self.get_server_config(server_name)
        
        if config is None:
            return []
        
        table_folders_str = config.get('addTableFolders', '').strip()
        
        if not table_folders_str:
            return []
        
        return [f.strip() for f in table_folders_str.split(';') if f.strip()]
    
    def get_table_file_path(self, filename: str, server_name: Optional[str] = None,
                           absolute: bool = False) -> Optional[str]:
        """
        Dynamically resolve any table file path based on server configuration.
        
        Args:
            filename: Table filename (e.g., "monsters.txt", "npcs.txt")
            server_name: Server name to look up (if None, uses current from config.txt)
            absolute: If True, return absolute path; if False, return relative
        
        Returns:
            Path to the table file or None if not found
        """
        table_folders = self.get_all_table_folders(server_name)
        
        # Try each folder in priority order
        for folder in table_folders:
            file_path = self.base_dir / "tables" / folder / filename
            if file_path.exists():
                if absolute:
                    return str(file_path.resolve())
                else:
                    try:
                        relative_path = file_path.relative_to(self.base_dir)
                        return f"../{relative_path.as_posix()}"
                    except ValueError:
                        return str(file_path.resolve())
        
        # Fallback: check base tables directory
        file_path = self.base_dir / "tables" / filename
        if file_path.exists():
            if absolute:
                return str(file_path.resolve())
            else:
                return f"../tables/{filename}"
        
        logger.warning(f"Table file not found: {filename}")
        return None


# Global instance for easy access
_resolver_instance: Optional[ConfigPathResolver] = None


def get_resolver(base_dir: Optional[str] = None) -> ConfigPathResolver:
    """
    Get or create the global ConfigPathResolver instance.
    
    Args:
        base_dir: Base directory (only used on first call)
    
    Returns:
        ConfigPathResolver instance
    """
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = ConfigPathResolver(base_dir)
    return _resolver_instance


def get_recvpackets_path(server_name: Optional[str] = None, 
                        absolute: bool = False) -> Optional[str]:
    """
    Convenience function to get recvpackets.txt path.
    
    Args:
        server_name: Server name (if None, uses current from config.txt)
        absolute: Return absolute path instead of relative
    
    Returns:
        Path to recvpackets.txt
    
    Example:
        >>> path = get_recvpackets_path()
        >>> print(path)
        '../tables/kRO/Ragexe_2021_11_03/recvpackets.txt'
    """
    resolver = get_resolver()
    return resolver.get_recvpackets_path(server_name, absolute)


def get_table_file_path(filename: str, server_name: Optional[str] = None,
                       absolute: bool = False) -> Optional[str]:
    """
    Convenience function to get any table file path.
    
    Args:
        filename: Table filename (e.g., "monsters.txt")
        server_name: Server name (if None, uses current from config.txt)
        absolute: Return absolute path instead of relative
    
    Returns:
        Path to the table file
    
    Example:
        >>> path = get_table_file_path("monsters.txt")
        >>> print(path)
        '../tables/kRO/Ragexe_2021_11_03/monsters.txt'
    """
    resolver = get_resolver()
    return resolver.get_table_file_path(filename, server_name, absolute)


if __name__ == "__main__":
    # Test the resolver
    logging.basicConfig(level=logging.INFO)
    
    print("=== Testing ConfigPathResolver ===\n")
    
    resolver = ConfigPathResolver()
    
    # Test 1: Get current server name
    print("1. Current server name:")
    server_name = resolver.get_current_server_name()
    print(f"   {server_name}\n")
    
    # Test 2: Get server configuration
    print("2. Server configuration:")
    config = resolver.get_server_config(server_name)
    if config:
        for key, value in sorted(config.items()):
            print(f"   {key}: {value}")
    print()
    
    # Test 3: Get recvpackets path
    print("3. Recvpackets path (relative):")
    path = resolver.get_recvpackets_path()
    print(f"   {path}\n")
    
    print("4. Recvpackets path (absolute):")
    path_abs = resolver.get_recvpackets_path(absolute=True)
    print(f"   {path_abs}\n")
    
    # Test 4: Get all table folders
    print("5. All table folders:")
    folders = resolver.get_all_table_folders()
    for folder in folders:
        print(f"   - {folder}")
    print()
    
    # Test 5: Get other table files
    print("6. Other table files:")
    for filename in ["monsters.txt", "npcs.txt", "maps.txt"]:
        path = resolver.get_table_file_path(filename)
        print(f"   {filename}: {path}")
